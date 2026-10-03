"""Validate guild membership and directory queries."""
from ..protocol import LocalError, integer, sequence


class GuildHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def get(self, request):
        self.protocol.empty_request(request)
        return self.protocol.response(request, self.service.get(request))

    @staticmethod
    def guild_id(value):
        if not isinstance(value, bytes) or len(value) != 16:
            raise LocalError('invalid_guild_id')
        return value

    def search(self, request):
        fields = self.protocol.request(request)
        if fields['GuildId'] is not None:
            self.guild_id(fields['GuildId'])
        for name in ('MemberRangeMin', 'MemberRangeMax'):
            if fields[name] is not None:
                integer(fields[name], maximum=2**31 - 1)
        minimum, maximum = fields['MemberRangeMin'], fields['MemberRangeMax']
        if minimum is not None and maximum is not None and minimum > maximum:
            raise LocalError('invalid_guild_member_range')
        for name in ('ChatFrequency', 'PlayStyle', 'BattleTimeRange', 'AdmissionType'):
            integer(fields[name], minimum=-(2**31), maximum=2**31 - 1)
        # A first-page query can omit previously searched IDs.
        for value in sequence(fields['SearchedGuildIds'] if fields['SearchedGuildIds'] is not None else []):
            self.guild_id(value)
        return self.protocol.response(request, self.service.search(request))
