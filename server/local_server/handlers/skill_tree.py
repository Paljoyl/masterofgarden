"""Validate the exact two-field skill tree release request."""
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import InsufficientItems
from ..protocol import LocalError, integer


class SkillTreeHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def release(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['NodeCode'], minimum=1)
        use_limit_break = fields['UseLimitBreakItem']
        if type(use_limit_break) is not bool:
            raise LocalError('invalid_skill_tree_limit_break_flag')
        try:
            result = self.service.release(request, code, use_limit_break)
        except InsufficientItems as exc:
            raise LocalError('local_skill_tree_insufficient_items', 409) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_skill_tree_state_invalid', 503) from exc
        return self.protocol.response(request, result)
