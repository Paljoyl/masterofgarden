"""Home request validation and protocol encoding."""
from ..protocol import LocalError, integer


class HomeHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def set_character(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['CharacterCostumeCode'])
        is_random = fields['IsRandomCostume']
        if type(is_random) is not bool:
            raise LocalError('invalid_home_random_costume')
        return self.protocol.response(request, self.service.set_character(request, code, is_random))
