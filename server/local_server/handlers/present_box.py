"""Present-box request validation and response encoding."""
from ..protocol import LocalError, sequence


class PresentBoxHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def get(self, request):
        fields = self.protocol.request(request)
        if type(fields["IsHistory"]) is not bool:
            raise LocalError("invalid_history_flag")
        return self.protocol.response(request, self.service.get(request, fields["IsHistory"]))

    def receive(self, request):
        fields = self.protocol.request(request)
        ids = sequence(fields['PresentIds'])
        if any(type(value) is not bytes or len(value) != 16 for value in ids):
            raise LocalError('invalid_present_id')
        if len(set(ids)) != len(ids):
            raise LocalError('duplicate_present_id')
        return self.protocol.response(request, self.service.receive(request, ids))
