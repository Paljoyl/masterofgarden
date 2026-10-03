"""Decode World Tree requests and encode their installed response models."""


class ClimbingHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def top(self, request):
        self.protocol.empty_request(request)
        return self.protocol.response(request, self.service.top(request))

    def start(self, request):
        return self.protocol.response(request, self.service.start(request, self.protocol.request(request)))

    def result(self, request):
        return self.protocol.response(request, self.service.result(request, self.protocol.request(request)))

    def rematching(self, request):
        return self.protocol.response(request, self.service.rematching(request, self.protocol.request(request)))

    def reset(self, request):
        return self.protocol.response(request, self.service.reset(request, self.protocol.request(request)))

    def battle_reset(self, request):
        return self.protocol.response(request, self.service.battle_reset(request, self.protocol.request(request)))
