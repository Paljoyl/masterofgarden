"""Validate the four read-only chat directory/history endpoints."""
from ..protocol import integer, text


class ChatHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def member_counts(self, request):
        self.protocol.empty_request(request)
        return self.protocol.response(request, self.service.member_counts(request))

    def log_count(self, request):
        fields = self.protocol.request(request)
        room = text(fields['Room'], maximum=256)
        return self.protocol.response(request, self.service.log_count(request, room))

    def room_logs(self, request):
        fields = self.protocol.request(request)
        room = text(fields['RoomName'], maximum=256)
        # C# positions are signed Int32; an empty room can yield EndPosition=-1.
        begin = integer(fields['BeginPosition'], minimum=-(2**31), maximum=2**31 - 1)
        end = integer(fields['EndPosition'], minimum=-(2**31), maximum=2**31 - 1)
        return self.protocol.response(request, self.service.room_logs(request, room, begin, end))

    def room_logs_from_bottom(self, request):
        fields = self.protocol.request(request)
        room = text(fields['RoomName'], maximum=256)
        begin = integer(fields['BeginPositionFromBottom'], minimum=-(2**31), maximum=2**31 - 1)
        count = integer(fields['Count'], maximum=2**31 - 1)
        return self.protocol.response(request, self.service.room_logs_from_bottom(request, room, begin, count))
