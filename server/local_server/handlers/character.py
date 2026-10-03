"""Character/equipment wire validation; clients cannot specify resulting player state."""
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import InsufficientItems, OperationConflict
from ..protocol import LocalError, integer, sequence


class CharacterHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def _call(self, request, callback):
        try:
            result = callback()
        except InsufficientItems as exc:
            raise LocalError('local_character_insufficient_items', 409) from exc
        except OperationConflict as exc:
            raise LocalError('local_character_state_conflict', 409) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_character_definition_invalid', 503) from exc
        return self.protocol.response(request, result)

    def items(self, values, *, empty=False, allow_zero=False):
        result = {}
        for value in sequence(values, maximum=100):
            row = self.protocol.fields('StackItemInfo', value, strict=True)
            code = integer(row['ItemCode'], minimum=1)
            count = integer(row['Count'], minimum=0 if allow_zero else 1, maximum=2**31 - 1)
            integer(row['RecoveredAt'])
            if code in result:
                raise LocalError('duplicate_character_item')
            result[code] = count
        # Awakening sends both crystal choices, including the unused choice with
        # Count=0. Validate every row and duplicates before removing zero costs.
        result = {code: count for code, count in result.items() if count}
        if not result and not empty:
            raise LocalError('empty_character_items')
        return result

    def levelup(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['CharacterCode'], minimum=1)
        items = self.items(fields['StackItems'])
        return self._call(request, lambda: self.service.levelup(request, code, items))

    def favorite(self, request):
        fields = self.protocol.request(request)
        changes = fields['CharacterCodes']
        if not isinstance(changes, dict) or len(changes) > 1000:
            raise LocalError('invalid_favorite_characters')
        for code, favorite in changes.items():
            integer(code, minimum=1)
            if type(favorite) is not bool:
                raise LocalError('invalid_favorite_flag')
        return self._call(request, lambda: self.service.favorite(request, changes))

    def levelup_selected(self, request):
        fields = self.protocol.request(request)
        codes = [integer(c, minimum=1) for c in sequence(fields['CharacterCodes'], maximum=100)]
        if not codes or len(codes) != len(set(codes)):
            raise LocalError('invalid_character_selection')
        return self._call(request, lambda: self.service.levelup_selected(request, codes))

    def rarityup(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['CharacterCode'], minimum=1)
        return self._call(request, lambda: self.service.rarityup(request, code))

    def limitbreak(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['CharacterCode'], minimum=1)
        items = self.items(fields['ExpectedConsumeItems'], empty=True, allow_zero=True)
        return self._call(request, lambda: self.service.limitbreak(request, code, items))

    def rankup(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['CharacterCode'], minimum=1)
        rank = integer(fields['AfterRank'], minimum=1, maximum=100)
        return self._call(request, lambda: self.service.rankup(request, code, rank))

    def equip(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['CharacterCode'], minimum=1)
        slots = [integer(s, minimum=1, maximum=6) for s in sequence(fields['Slots'], maximum=6)]
        if not slots or len(slots) != len(set(slots)):
            raise LocalError('invalid_equipment_slots')
        return self._call(request, lambda: self.service.equip(request, code, slots))

    def equip_auto(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['CharacterCode'], minimum=1)
        return self._call(request, lambda: self.service.equip(request, code))

    def make_equipment(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['ItemCode'], minimum=1)
        return self._call(request, lambda: self.service.make_equipment(request, code))
