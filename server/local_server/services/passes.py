"""Local pass refreshes; purchases and reward settlement are separate operations."""
from copy import deepcopy

from PostgreSQL.battle_pass import BattlePassStore
from ..protocol import LocalError, sequence
from .inventory import inventory_update, total_battle_power


class PassService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def shop_notifications(self, request):
        session = self.players.session(request)
        state = self.players._state(session.player_id)
        if self.players.timing is not None:
            infos = self.players.timing.shop_notifications(session.player_id, int(self.players.clock()))
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'ShopPassInfos': infos}
        # No local shop subscriptions have been activated. Do not import an
        # official subscription or write a historical notification timestamp.
        return {"UpdateAccumulateInfos": [], "ShopPassInfos": []}

    def battle_passes(self, request):
        session = self.players.session(request)
        state = self.players._state(session.player_id)
        if self.players.timing is not None:
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'BattlePasses': state['BattlePasses']}
        template = self.players.templates.get((session.player_id, session.variant, "/gametop/getgametopinfo"))
        passes = []
        if template is not None:
            # Keep this query consistent with the same player's local home
            # initialization until local pass progression is implemented.
            home = self.protocol.fields("GetGameTopInfoResponse", template)
            passes = home["BattlePasses"]
            if passes is None:
                passes = []
        return {"UpdateAccumulateInfos": [], "BattlePasses": deepcopy(sequence(passes))}

    def settle(self, request, code, *, count=None):
        session = self.players.session(request)
        if self.players.repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        player_id = session.player_id
        with self.players.repository.transaction(player_id):
            store = BattlePassStore(self.players.repository, self.players.timing)
            now = int(self.players.clock())
            if count is None:
                changed, rewards = store.receive(player_id, code, now)
            else:
                changed = store.purchase_levels(player_id, code, count, now)
            state = self.players._state(player_id)
            battle_pass = next((r for r in state['BattlePasses'] if r[0] == code), None)
            if battle_pass is None:
                raise LocalError('local_battle_pass_state_invalid', 503)
            result = {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                      'BattlePass': battle_pass,
                      'InventoryUpdateInfo': inventory_update(self.protocol, state, changed)}
            if count is None:
                result.update(ReceivedRewards=[self.protocol.model('RewardInfo', {
                    'Type': r['Type'], 'Code': r['ItemCode'], 'Count': r['Count'],
                    'DisplayPriority': r['DisplayPriority']}) for r in rewards],
                    TotalBattlePower=total_battle_power(self.players, self.protocol, session))
            return result
