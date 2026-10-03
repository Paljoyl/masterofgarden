"""Validate the item code and count (food quantity or quoted stone price)."""
from ..protocol import integer


class StaminaHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def recover(self, request):
        fields = self.protocol.request(request)
        item_code = integer(fields['ItemCode'], minimum=1)
        count = integer(fields['Count'], minimum=1, maximum=2**31 - 1)
        return self.protocol.response(request, self.service.recover(request, item_code, count))
