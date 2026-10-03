"""Release nodes with client master costs and client predecessor rules."""
from collections import defaultdict
from uuid import uuid4

from PostgreSQL.skill_tree import SkillTreeStore
from ..protocol import LocalError


class SkillTreeCatalog:
    def __init__(self, connection):
        data = dict(connection.execute('SELECT name,data FROM public.skill_tree_definitions').fetchall())
        try:
            self.nodes = {row['Code']: row for row in data['skill_tree_node_master']}
            self.floors = {row['Code']: row for row in data['skill_tree_floor_master']}
            self.levels = {(row['Code'], row['Level']): row for row in data['skill_tree_level_master']}
            self.costs = {row['Code']: row for row in data['skill_tree_cost_master']}
            settings = {row['Key']: row['Value'] for row in data['skill_tree_settings']}
            self.items = {attribute: [int(code) for code in settings[f'SKILL_TREE_{color}_ATTRIBUTE_ITEM_CODE']]
                          for attribute, color in ((1, 'RED'), (2, 'GREEN'), (3, 'YELLOW'), (4, 'BLUE'))}
            self.currency, = [row['ItemCode'] for row in data['skill_tree_currency_items']]
            self.limit_break_item, = [row['ItemCode'] for row in data['skill_tree_limit_break_items']]
            self.max_level = int(settings['SKILL_TREE_MAX_LEVEL'][0])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise LocalError('local_skill_tree_configuration_invalid', 503) from exc
        self.floor_nodes = defaultdict(dict)
        for row in self.nodes.values():
            self.floor_nodes[row['SkillTreeFloorCode']][row['NodeIndex']] = row['Code']
        self.floor_indices = {(row['Attribute'], row['FloorIndex']): row['Code']
                              for row in self.floors.values()}

    @staticmethod
    def previous_indices(index):
        # CharacterSharedLogic's client graph (RVA 0x12A9BA0): three branches
        # (2,3,4), (5,6,7), (8,9,10), reached from 1 and joined at 11.
        if index == 1:
            return ()
        if index == 11:
            return (4, 7, 10)
        if 2 <= index <= 10:
            return (1,) if index % 3 == 2 else (index - 1,)
        raise LocalError('local_skill_tree_node_configuration_invalid', 503)

    def require(self, code, levels):
        node = self.nodes.get(code)
        if node is None:
            raise LocalError('local_skill_tree_node_not_found', 404)
        floor = self.floors.get(node['SkillTreeFloorCode'])
        if floor is None:
            raise LocalError('local_skill_tree_configuration_invalid', 503)
        if floor['FloorIndex'] > 1:
            previous = self.floor_indices.get((floor['Attribute'], floor['FloorIndex'] - 1))
            last = self.floor_nodes.get(previous, {}).get(11)
            if last is None:
                raise LocalError('local_skill_tree_configuration_invalid', 503)
            if levels.get(last, 0) <= 0:
                raise LocalError('local_skill_tree_floor_locked', 409)
        predecessors = self.previous_indices(node['NodeIndex'])
        if predecessors:
            siblings = self.floor_nodes[floor['Code']]
            if any(index not in siblings for index in predecessors):
                raise LocalError('local_skill_tree_configuration_invalid', 503)
            # SkillTreeNodeData.IsUnlocked (RVA 0xAC0EF0) accepts any released predecessor.
            if not any(levels.get(siblings[index], 0) > 0 for index in predecessors):
                raise LocalError('local_skill_tree_node_locked', 409)
        return node, floor

    def release_cost(self, floor, use_limit_break):
        try:
            level = self.levels[(floor['SkillTreeLevelMasterCode'], 1)]
            cost = self.costs[level['CostMasterCode']]
            material_codes = self.items[floor['Attribute']]
            if len(material_codes) != 3:
                raise ValueError()
            changes = defaultdict(int)
            for code, field in zip(material_codes, ('LowGradeItemCost', 'MidGradeItemCost', 'HighGradeItemCost')):
                changes[code] -= cost[field]
            changes[self.currency] -= cost['CurrencyCost']
            if use_limit_break:
                # The installed level-1 release has zero optional awakening cost.
                # Keep its normal material/currency cost when this flag is set.
                changes[self.limit_break_item] -= cost['LimitBreakItemCost']
            if any(type(count) is not int or count > 0 for count in changes.values()):
                raise ValueError()
        except (KeyError, TypeError, ValueError) as exc:
            raise LocalError('local_skill_tree_configuration_invalid', 503) from exc
        return {code: count for code, count in changes.items() if count}


class SkillTreeService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None

    @property
    def repository(self):
        if self.players.repository is None:
            raise LocalError('player_storage_unavailable', 503)
        return self.players.repository

    @property
    def catalog(self):
        if self._catalog is None:
            self._catalog = SkillTreeCatalog(self.repository.connection)
        return self._catalog

    def release(self, request, code, use_limit_break):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            self.players._state(session.player_id)
            store = SkillTreeStore(self.repository)
            home = self.players.templates.get((session.player_id, session.variant, '/gametop/getgametopinfo'))
            seed = self.protocol.fields('GetGameTopInfoResponse', home)['SkillTree'] if home is not None else None
            tree = store.seed(session.player_id, seed)
            nodes, floors = dict(tree[0]), dict(tree[1])
            if code not in self.catalog.nodes:
                raise LocalError('local_skill_tree_node_not_found', 404)
            changed = {}
            if nodes.get(code, 0) == 0:
                node, floor = self.catalog.require(code, nodes)
                changed = self.catalog.release_cost(floor, use_limit_break)
                if changed:
                    self.repository.apply_item_changes(session.player_id, 'skill-tree-release:' + uuid4().hex, changed)
                nodes[code] = 1
                complete = min(nodes.get(member, 0) for member in self.catalog.floor_nodes[floor['Code']].values())
                if complete:
                    floors[floor['Code']] = max(floors.get(floor['Code'], 0), complete)
                store.save(session.player_id, nodes, floors)
                if self.players.timing is not None:
                    now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
                    for item, count in changed.items():
                        self.players.timing.event(session.player_id, 57, now, values=(str(item),), amount=-count)
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'SkillTree': store.get(session.player_id),
                    'StackItems': [row for row in state['StackItems'] if row[0] in changed]}
