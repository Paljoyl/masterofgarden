"""Validate event home queries before reading local player state."""
from ..protocol import integer


class EventHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def top(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['EventCode'], minimum=1)
        return self.protocol.response(request, self.service.top(request, code))

    def damage_ranking(self, request):
        code = integer(self.protocol.request(request)['EventCode'], minimum=1)
        return self.protocol.response(request, self.service.damage_ranking(request, code))

    def sub_top(self, request):
        code = integer(self.protocol.request(request)['SubEventCode'], minimum=1)
        return self.protocol.response(request, self.service.sub_top(request, code))
