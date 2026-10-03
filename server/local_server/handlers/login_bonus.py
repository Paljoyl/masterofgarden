"""Login bonus endpoint with the client's exact response model."""


class LoginBonusHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def get(self, request):
        self.protocol.request(request)
        return self.protocol.response(request, self.service.get(request))
