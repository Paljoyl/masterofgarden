"""Atomic magic item creation, enhancement and inventory/mission updates."""
from collections import defaultdict
from secrets import randbelow
from uuid import uuid4

from PostgreSQL.magic_item import MagicItemStore
from PostgreSQL.players import InsufficientItems
from ..protocol import LocalError
from .inventory import inventory_update
from .magic_item_catalog import MagicItemCatalog
from .magic_item_levelup_catalog import MagicItemLevelUpCatalog


class MagicItemService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None
        self._levelup_catalog = None
        self.randbelow = randbelow

    @property
    def repository(self):
        if self.players.repository is None:
            raise LocalError('player_storage_unavailable', 503)
        return self.players.repository

    @property
    def catalog(self):
        if self._catalog is None:
            data = dict(self.repository.connection.execute(
                'SELECT name,data FROM public.magic_item_definitions').fetchall())
            self._catalog = MagicItemCatalog(data)
        return self._catalog

    def create(self, request, materials):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            catalog = self.catalog
            if sum(materials.values()) > catalog.limit:
                raise LocalError('local_magic_item_creation_limit')
            pools = {code: catalog.pool(code) for code in materials}
            state = self.players._state(session.player_id)
            stock = {r[0]: r[1] for r in state['StackItems']}
            if any(stock.get(code, 0) < count for code, count in materials.items()):
                raise InsufficientItems('Insufficient creation materials')
            now = int(self.players.clock())
            timing = self.players.timing
            if timing is not None:
                now = timing._effective_now(session.player_id, now)
            store = MagicItemStore(self.repository)
            changes = defaultdict(int, {code: -count for code, count in materials.items()})
            created, results = set(), []
            for material, count in materials.items():
                for _ in range(count):
                    item = catalog.draw(pools[material], self.randbelow)
                    code, rarity = item['Code'], item['Rarity']
                    if store.grant(session.player_id, code, now):
                        created.add(code)
                        results.append([5, code, 1, rarity, True, 0])
                    else:
                        alternative = item['AlternativeItemCode']
                        changes[alternative] += 1
                        results.append([2, alternative, 1, rarity, False, code])
            self.repository.apply_item_changes(session.player_id, 'magic-create:' + uuid4().hex, dict(changes))
            if timing is not None:
                timing.event(session.player_id, 19, now, amount=sum(materials.values()))
                for code, count in materials.items():
                    timing.event(session.player_id, 57, now, values=(str(code),), amount=count)
                for code, delta in changes.items():
                    if delta > 0:
                        timing.event(session.player_id, 56, now, values=(str(code),), amount=delta)
            state = self.players._state(session.player_id)
            update = inventory_update(self.protocol, state, changes)
            update[self.protocol.indices('InventoryUpdateInfo')['MagicItems']] = [
                r for r in state['MagicItems'] if r[0] in created]
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'InventoryUpdateInfo': update, 'MagicItemCreateResults': results}

    @property
    def levelup_catalog(self):
        if self._levelup_catalog is None:
            data = dict(self.repository.connection.execute(
                'SELECT name,data FROM public.magic_item_definitions').fetchall())
            self._levelup_catalog = MagicItemLevelUpCatalog(data)
        return self._levelup_catalog

    def levelup(self, request, code, add_level):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            item = next((r for r in state['MagicItems'] if r[0] == code), None)
            if item is None:
                raise LocalError('local_magic_item_not_owned', 404)
            costs = self.levelup_catalog.costs(code, item[1], add_level)
            self.repository.apply_item_changes(session.player_id, 'magic-levelup:' + uuid4().hex,
                                               {c: -n for c, n in costs.items()})
            MagicItemStore(self.repository).levelup(session.player_id, code, item[1], item[1] + add_level)
            timing = self.players.timing
            if timing is not None:
                now = timing._effective_now(session.player_id, int(self.players.clock()))
                for material, amount in costs.items():
                    timing.event(session.player_id, 57, now, values=(str(material),), amount=amount)
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'MagicItem': next(r for r in state['MagicItems'] if r[0] == code),
                    'StackItems': [r for r in state['StackItems'] if r[0] in costs]}
