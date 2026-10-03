"""Validate client requests for magic item creation and enhancement."""
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import InsufficientItems, OperationConflict
from ..protocol import LocalError, integer


class MagicItemHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def _call(self, request, callback):
        try:
            result = callback()
        except InsufficientItems as exc:
            raise LocalError('local_magic_item_insufficient_items', 409) from exc
        except OperationConflict as exc:
            raise LocalError('local_magic_item_state_conflict', 409) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_magic_item_definition_invalid', 503) from exc
        return self.protocol.response(request, result)

    def create(self, request):
        fields = self.protocol.request(request)
        values = fields['MagicItemCreateItemDic']
        if not isinstance(values, dict) or not 1 <= len(values) <= 1000:
            raise LocalError('invalid_magic_item_materials')
        materials = {integer(code, minimum=1): integer(count, minimum=1, maximum=2**31 - 1)
                     for code, count in values.items()}
        return self._call(request, lambda: self.service.create(request, materials))

    def levelup(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['MagicItemCode'], minimum=1)
        add_level = integer(fields['AddLevel'], minimum=1, maximum=2**31 - 1)
        return self._call(request, lambda: self.service.levelup(request, code, add_level))
