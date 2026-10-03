"""Local empty-room queries, independent of official presence/history snapshots."""


class ChatService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def member_counts(self, request):
        self.players.session(request)
        # ChatSharedLogic.GetRoomName uses '<ChatTabType>_<id>'; Open=0
        # formats as 'Open'. Keep one room because ChatModel auto-assignment
        # selects a room from the returned list. No local chat transport has
        # registered members, so this local room has zero members. Logged-in
        # player sessions do not establish chat-room presence.
        info = self.protocol.model('OpenChatRoomMemberCountInfo', {
            'RoomName': 'Open_1', 'Count': 0})
        # GetOpenChatRoomMemberCountResponse.Infos is Key(1), not Key(0).
        return {'Infos': [info]}

    def log_count(self, request, room):
        self.players.session(request)
        # No local transport has stored messages. Historical official captures
        # cannot establish this room's current log count or private membership.
        return {'Count': 0}

    def room_logs(self, request, room, begin, end):
        self.players.session(request)
        return {'Logs': []}

    def room_logs_from_bottom(self, request, room, begin, count):
        self.players.session(request)
        return {'Logs': []}
