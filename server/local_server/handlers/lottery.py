"""Exact client positional request models, including the three-field ExecLotteryRequest."""
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import InsufficientItems, OperationConflict
from mog_protocol.codec import EMPTY
from ..protocol import LocalError, integer, sequence


class LotteryHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def _call(self, request, callback, *, empty=False):
        try:
            result = callback()
        except InsufficientItems as exc:
            raise LocalError('local_lottery_insufficient_items', 409) from exc
        except OperationConflict as exc:
            raise LocalError('local_lottery_state_conflict', 409) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_lottery_definition_invalid', 503) from exc
        return self.protocol.response(request, value=EMPTY) if empty else self.protocol.response(request, result)

    def select(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['LotteryCode'], minimum=1)
        characters = [integer(value, minimum=1) for value in sequence(fields['Characters'], maximum=100)]
        return self._call(request, lambda: self.service.set_selection(request, code, characters), empty=True)

    def execute(self, request):
        fields = self.protocol.request(request)
        progress = integer(fields['TutorialProgress'], maximum=2**31 - 1)
        code = integer(fields['LotteryCode'], minimum=1)
        button = integer(fields['ButtonIndex'], minimum=1, maximum=2**31 - 1)
        return self._call(request, lambda: self.service.execute(request, code, button, progress))

    def get(self, request):
        self.protocol.request(request)
        return self._call(request, lambda: self.service.get(request))

    def histories(self, request):
        self.protocol.request(request)
        return self._call(request, lambda: self.service.histories(request))

    def chances(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['LotteryCode'], minimum=1)
        return self._call(request, lambda: self.service.chances(request, code))
