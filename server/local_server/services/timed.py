"""Timed local endpoint operations; request clocks always come from the server."""
from ..protocol import LocalError
from .inventory import inventory_update, total_battle_power


class TimedService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def receive_missions(self, request, codes):
        session = self.players.session(request)
        if self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        power = total_battle_power(self.players, self.protocol, session)
        with self.players.repository.transaction(session.player_id):
            changed = self.players.timing.receive_missions(session.player_id, codes, int(self.players.clock()),
                                                          total_power=power)
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, changed),
                    'MissionRewardReceivedInfos': state['MissionRewardReceivedInfos'],
                    'HomeCharacters': state.get('HomeCharacters', []), 'GardenBuildings': state.get('GardenBuildings', []),
                    'BattlePasses': state['BattlePasses'],
                    'TotalBattlePower': power}

    def lotteries(self, request):
        session = self.players.session(request)
        if self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        state = self.players._state(session.player_id)
        return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                'LotteryDisplays': self.players.timing.lottery_displays(session.player_id, int(self.players.clock()))}
