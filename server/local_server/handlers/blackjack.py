"""The client draws locally; only deal, double and result are network actions."""
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import InsufficientItems, OperationConflict

from ..protocol import LocalError, integer


def round_id(value):
    # UlidMessagePackFormatter.Serialize writes a 16-byte MessagePack bin value.
    if not isinstance(value, bytes) or len(value) != 16 or not any(value):
        raise LocalError('invalid_blackjack_unique_id')
    return value.hex()


class BlackjackHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def _call(self, request, callback):
        try:
            fields = callback()
        except InsufficientItems as exc:
            raise LocalError('local_blackjack_insufficient_items', 409,
                             client_message='21 点下注所需的筹码不足。') from exc
        except OperationConflict as exc:
            raise LocalError('local_blackjack_state_conflict', 409) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_blackjack_configuration_invalid', 503) from exc
        return self.protocol.response(request, fields)

    def deal(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['MiniGameCode'], minimum=1)
        bet = integer(fields['BetNum'], minimum=1)
        unique_id = round_id(fields['UniqueId'])
        return self._call(request, lambda: self.service.deal(request, code, bet, unique_id))

    def double(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['MiniGameCode'], minimum=1)
        unique_id = round_id(fields['UniqueId'])
        return self._call(request, lambda: self.service.settle(request, code, unique_id, double=True))

    def result(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['MiniGameCode'], minimum=1)
        hits = integer(fields['HitNum'], maximum=48)
        unique_id = round_id(fields['UniqueId'])
        return self._call(request, lambda: self.service.settle(request, code, unique_id, hits=hits))
