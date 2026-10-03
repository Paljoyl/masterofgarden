"""Membership queries for the current local installation without guild storage."""


class GuildService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def get(self, request):
        state = self.players.state(request)
        # No guild membership or pending applications have been created locally.
        # Guild is a nullable reference; an empty GuildInfo with a fabricated
        # ULID would incorrectly tell the client that this player joined a guild.
        return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                'Guild': None, 'JoinRequestedGuildId': None,
                'CanBecomeGuildMaster': False, 'ExistJoinRequests': False,
                'MessageFlag': 0}  # GuildMessageFlag.None.

    def search(self, request):
        state = self.players.state(request)
        return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []), 'Guilds': []}
