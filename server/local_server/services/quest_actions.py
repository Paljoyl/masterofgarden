"""Ordinary quest skips and purchased daily challenge recovery."""
from collections import defaultdict
from uuid import uuid4

from ..protocol import LocalError, integer
from .inventory import inventory_update, FREE_STONE, PAID_STONE, SUPPLEMENT_PAID_STONE


class QuestActions:
    def __init__(self, quests, results):
        self.quests, self.results = quests, results
        self.players, self.protocol = quests.players, quests.protocol

    @property
    def challenges(self):
        store = self.players.timing.quest_challenges
        if store is None:
            raise LocalError('local_quest_configuration_missing', 503)
        return store

    def skip(self, request, fields):
        session = self.players.session(request)
        player_id = session.player_id
        with self.quests.repository.transaction(player_id):
            state = self.players._state(player_id)
            quest = self.quests.check_quest(state, fields['QuestCode'], count=fields['SkipCount'])
            now = self.players.timing._effective_now(player_id, int(self.players.clock()))
            self.quests.check_day(quest, now)
            old = next((r for r in state['ClearedQuests'] if r[0] == quest['Code']), None)
            if quest['SkipType'] != 0:
                raise LocalError('local_quest_skip_unavailable', 409)
            if old is None or not old[1] or old[2] < 3:
                raise LocalError('local_quest_skip_requires_three_stars', 409)
            if quest['RewardCloseness']:
                raise LocalError('local_quest_closeness_reward_not_implemented', 501)
            self.challenges.require(player_id, quest, now, fields['SkipCount'])
            self.results.configuration()
            # Nullable ItemCode/RequiredCount belong to the client's desired-item
            # skip button, not a ticket or a client-declared price. Ordinary
            # skipping spends the master stamina cost and daily allowance only.
            if fields['ItemCode'] is not None:
                raise LocalError('local_quest_desired_item_skip_not_implemented', 501)
            items = defaultdict(int)
            for _ in range(fields['SkipCount']):
                for item, count, _ in self.results.drop(quest['QuestDropCodeForEverytime'])[0]:
                    items[item] += count
            drop = self.protocol.model('QuestDropInfo', {'DropItems': [
                self.protocol.model('DropItemResultViewInfo', {'ItemCode': code, 'Count': count, 'BoxItemCode': None})
                for code, count in items.items()]})
            self.challenges.consume(player_id, quest, now, fields['SkipCount'])
            user = self.protocol.fields('UserInfo', state['User'])
            key = 'quest-skip:' + uuid4().hex
            xp, changes = self.results.grant(player_id, quest, quest['Stamina'] * fields['SkipCount'],
                fields['SkipCount'], [drop], user, now, key)
            self.results.progress(player_id, quest, old[2], False, now, amount=fields['SkipCount'])
            state = self.players._state(player_id)
            user = self.protocol.fields('UserInfo', state['User'])
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    'QuestSkipInfo': self.protocol.model('QuestSkipInfo', {
                        'DropInfo': drop, 'Experience': xp['gained_experience']}),
                    'Stamina': user['Stamina'], 'Experience': user['Experience'],
                    'QuestInfo': next(r for r in state['ClearedQuests'] if r[0] == quest['Code']),
                    'QuestGroupInfo': next(r for r in state['QuestGroups'] if r[0] == quest['QuestGroupCode']),
                    'QuestClearCountInfo': next(r for r in state['QuestClearCounts'] if r[0] == quest['Code']),
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, set(changes) | {390000001}),
                    'QuestSkipCount': fields['SkipCount']}

    def recover(self, request, code, *, group=False):
        session = self.players.session(request)
        player_id = session.player_id
        with self.quests.repository.transaction(player_id):
            state = self.players._state(player_id)
            now = self.players.timing._effective_now(player_id, int(self.players.clock()))
            if group:
                definition = self.quests.definitions['groups'].get(code)
                if definition is None:
                    raise LocalError('local_quest_group_not_found', 404)
                if not self.challenges.ordinary(definition):
                    raise LocalError('local_quest_type_not_implemented', 501)
                if definition['ChallengeCountType'] != 1 or not definition['MaxChallengeCount']:
                    raise LocalError('local_quest_group_challenge_recovery_unavailable', 409)
                target = ('quest_groups', 'quest_group_code', code, definition)
                collection, response_field = 'QuestGroups', 'QuestGroupInfo'
            else:
                quest = self.quests.check_quest(state, code, count=0)
                self.quests.check_day(quest, now)
                target = self.challenges.target(quest)
                if target is not None and target[0] != 'quests':
                    raise LocalError('local_quest_requires_group_challenge_recovery', 409)
                collection, response_field = 'ClearedQuests', 'QuestInfo'
            price = self.challenges.recovery_stones
            if price is None or price <= 0:
                raise LocalError('local_quest_recovery_configuration_missing', 503)
            # Recovery is allowed only after exhaustion. A repeated request
            # then fails before payment, since the allowance is already full.
            self.challenges.recover(player_id, target, now)
            pools = (FREE_STONE, PAID_STONE, SUPPLEMENT_PAID_STONE)
            balances = dict(self.quests.repository.connection.execute('''SELECT item_code,quantity FROM public.items
                WHERE player_id=%s AND item_code=ANY(%s)''', (player_id, list(pools))).fetchall())
            remaining, changes = price, {}
            for item in pools:
                amount = min(balances.get(item, 0), remaining)
                if amount:
                    changes[item] = -amount
                    remaining -= amount
            if remaining:
                raise LocalError('local_quest_recovery_insufficient_stones', 409)
            self.quests.repository.apply_item_changes(player_id, 'quest-recover:' + uuid4().hex, changes)
            state = self.players._state(player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    response_field: next(r for r in state[collection] if r[0] == code),
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, changes)}
