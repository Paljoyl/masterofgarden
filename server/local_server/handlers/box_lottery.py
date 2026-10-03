"""Typed box-lottery requests and positional MessagePack responses."""
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import InsufficientItems, OperationConflict
from ..protocol import LocalError, integer


class BoxLotteryHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def get(self, request):
        self.protocol.request(request)
        return self._call(request, lambda: self.service.get(request))

    def execute(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['BoxLotteryCode'], minimum=1, maximum=2**63 - 1)
        count = integer(fields['Count'], minimum=1, maximum=2**31 - 1)
        return self._call(request, lambda: self.service.execute(request, code, count))

    def next_sheet(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['BoxLotteryCode'], minimum=1, maximum=2**63 - 1)
        return self._call(request, lambda: self.service.next_sheet(request, code))

    def _call(self, request, callback):
        try:
            result = callback()
        except InvalidPlayerData as exc:
            raise LocalError('local_box_lottery_state_invalid', 503) from exc
        except InsufficientItems as exc:
            raise LocalError('local_box_lottery_insufficient_items', 409,
                             client_message='箱式抽奖所需的票券不足。') from exc
        except OperationConflict as exc:
            raise LocalError('local_box_lottery_state_conflict', 409) from exc
        return self.protocol.response(request, result)
