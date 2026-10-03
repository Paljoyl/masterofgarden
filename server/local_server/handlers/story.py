"""Decode and validate the three ReadStoryRequest fields."""
from ..protocol import integer, sequence, LocalError
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import InsufficientItems, OperationConflict


class StoryHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def open(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['StoryCode'], minimum=1)
        try:
            result = self.service.open(request, code)
        except InsufficientItems as exc:
            raise LocalError('local_story_insufficient_items', 409,
                             client_message='缺少开启剧情所需的道具。') from exc
        except (InvalidPlayerData, OperationConflict) as exc:
            raise LocalError('local_story_state_invalid', 503) from exc
        return self.protocol.response(request, result)

    def read(self, request):
        fields = self.protocol.request(request)
        progress = integer(fields['TutorialProgress'], maximum=2**31 - 1)
        code = integer(fields['StoryCode'], minimum=1)
        flags = [integer(value, minimum=1) for value in sequence(fields['AdventureFlagCodes'], maximum=100)]
        if len(flags) != len(set(flags)):
            raise LocalError('invalid_adventure_flags')
        try:
            result = self.service.read(request, code, flags, progress)
        except (InvalidPlayerData, OperationConflict) as exc:
            raise LocalError('local_story_state_invalid', 503) from exc
        return self.protocol.response(request, result)
