"""Decode the seven dedicated Tower requests and encode their client models."""
from ..protocol import integer


class TowerHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def fields(self, request):
        fields = self.protocol.request(request)
        integer(fields['TowerCode'], minimum=1)
        if 'Floor' in fields:
            integer(fields['Floor'], minimum=1, maximum=2**31 - 1)
        if 'QuestCode' in fields:
            integer(fields['QuestCode'], minimum=1)
        return fields

    def top(self, request):
        fields = self.fields(request)
        return self.protocol.response(request, self.service.top(request, fields['TowerCode']))

    def start(self, request):
        return self.protocol.response(request, self.service.start(request, self.fields(request)))

    def result(self, request):
        fields = self.fields(request)
        integer(fields['Result'], minimum=1, maximum=5)
        integer(fields['ContinueRoundIndex'], maximum=2**31 - 1)
        return self.protocol.response(request, self.service.result(request, fields))

    def continue_info(self, request):
        fields = self.fields(request)
        return self.protocol.response(request, self.service.continue_info(request, fields['TowerCode'], fields['Floor']))

    def reset(self, request):
        fields = self.fields(request)
        return self.protocol.response(request, self.service.continue_info(request, fields['TowerCode'], fields['Floor'], reset=True))

    def guild_rank(self, request):
        fields = self.fields(request)
        return self.protocol.response(request, self.service.guild_rank(request, fields['TowerCode'], fields['GuildId']))

    def clear_rate(self, request):
        fields = self.fields(request)
        return self.protocol.response(request, self.service.clear_rate(request, fields['TowerCode']))
