"""Empty training cleanup request and GetPartiesResponse wire contract."""


class TrialBattleHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def delete_unavailable_rentals(self, request):
        self.protocol.empty_request(request)
        return self.protocol.response(request, {'Parties': self.service.cleanup(request)})
