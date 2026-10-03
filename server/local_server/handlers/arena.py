"""ArenaCategory.SingleParty=0, TripleParty=1 in the installed TW client."""
from ..protocol import integer


class ArenaHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def info(self, request):
        fields = self.protocol.request(request)
        category = integer(fields['Category'], maximum=1)
        return self.protocol.response(request, self.service.info(request, category))

    def _code(self, request):
        return integer(self.protocol.request(request)['ArenaCode'], minimum=1)

    def enemies(self, request):
        return self.protocol.response(request, self.service.enemies(request, self._code(request)))

    def rankings(self, request):
        return self.protocol.response(request, self.service.rankings(request, self._code(request)))

    def histories(self, request):
        return self.protocol.response(request, self.service.histories(request, self._code(request)))
