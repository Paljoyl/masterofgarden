from ..protocol import integer, sequence, LocalError


class TimedHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def receive_missions(self, request):
        fields = self.protocol.request(request)
        codes = [integer(code) for code in sequence(fields['MissionCodes'], maximum=100)]
        if not codes or len(set(codes)) != len(codes):
            raise LocalError('invalid_mission_codes')
        return self.protocol.response(request, self.service.receive_missions(request, codes))

    def lotteries(self, request):
        self.protocol.request(request)
        return self.protocol.response(request, self.service.lotteries(request))
