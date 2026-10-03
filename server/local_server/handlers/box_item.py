"""Validate the client box-opening request before settlement."""
from ..protocol import integer
from ..services.box_item_catalog import MAX_OPEN_COUNT


class BoxItemHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def open(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['BoxCode'], minimum=1)
        count = integer(fields['OpenCount'], minimum=1, maximum=MAX_OPEN_COUNT)
        return self.protocol.response(request, self.service.open(request, code, count))
