"""Daily login and active subscription rewards, settled exactly once per game day."""
from .inventory import inventory_update, total_battle_power


class LoginBonusService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def get(self, request):
        session = self.players.session(request)
        bonuses, changed = [], set()
        if self.players.timing is not None:
            bonuses, changed = self.players.timing.login_bonus(session.player_id, int(self.players.clock()))
        state = self.players._state(session.player_id)
        inventory = inventory_update(self.protocol, state, changed)
        power = total_battle_power(self.players, self.protocol, session)
        return {"UpdateAccumulateInfos": state.get('UpdateAccumulateInfos', []), "LoginBonusInfos": bonuses,
                "InventoryUpdateInfo": inventory, "TotalBattlePower": power}
