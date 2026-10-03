"""Pass request validation and typed MessagePack responses."""
from PostgreSQL.player_protocol import InvalidPlayerData
from ..protocol import LocalError, integer


class PassHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def shop_notifications(self, request):
        self.protocol.empty_request(request)
        return self.protocol.response(request, self.service.shop_notifications(request))

    def battle_passes(self, request):
        self.protocol.request(request)
        return self.protocol.response(request, self.service.battle_passes(request))

    def receive_rewards(self, request):
        return self._settle(request, purchase=False)

    def purchase_levels(self, request):
        return self._settle(request, purchase=True)

    def _settle(self, request, *, purchase):
        fields = self.protocol.request(request)
        code = integer(fields['BattlePassCode'], minimum=1, maximum=2**63 - 1)
        count = integer(fields['Count'], minimum=1, maximum=2**31 - 1) if purchase else None
        try:
            result = self.service.settle(request, code, count=count)
        except InvalidPlayerData as exc:
            raise LocalError('local_battle_pass_state_invalid', 503) from exc
        return self.protocol.response(request, result)
