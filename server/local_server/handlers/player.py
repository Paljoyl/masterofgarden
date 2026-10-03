"""Request decoding and response encoding; no SQL or forwarding in handlers."""
from ..protocol import integer, sequence, text


class PlayerHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def login(self, request):
        fields = self.protocol.request(request)
        text(fields["loginid"], maximum=512)
        return self.protocol.response(request, value=self.service.login(request, fields["loginid"]))

    def association(self, request):
        self.protocol.request(request)
        return self.protocol.response(request, {"Result": self.service.associated(request)})

    def agreement(self, request):
        self.protocol.request(request)
        self.service.session(request)
        # Local terms do not require a remote account operation.
        return self.protocol.response(request, {"UpdateAccumulateInfos": []})

    def tutorial(self, request):
        fields = self.protocol.request(request)
        progress = self.protocol.fields("TutorialProgressInfo", fields["TutorialProgressInfo"], strict=True)
        self.service.set_tutorial(request, integer(progress["Progress"], maximum=2**31 - 1))
        return self.protocol.response(request, {"UpdateAccumulateInfos": []})

    def game_top(self, request):
        self.protocol.request(request)
        return self.protocol.response(request, value=self.service.game_top(request))

    def parties(self, request):
        fields = self.protocol.request(request)
        types = sequence(fields["Types"], maximum=100)
        types = [integer(kind, maximum=2**31 - 1) for kind in types]
        return self.protocol.response(request, {"Parties": self.service.parties(request, types)})

    def save_parties(self, request):
        fields = self.protocol.request(request)
        self.service.save_parties(request, sequence(fields["Party"], maximum=100))
        return self.protocol.response(request, {"UpdateAccumulateInfos": []})

    def party_name(self, request):
        fields = self.protocol.request(request)
        kind = integer(fields["Type"], maximum=2**31 - 1)
        number = integer(fields["No"], maximum=2**31 - 1)
        name = text(fields["Name"], maximum=50, empty=True)
        self.service.set_party_name(request, kind, number, name)
        return self.protocol.response(request, {"UpdateAccumulateInfos": [], "Type": kind, "No": number, "Name": name})

    def profile(self, request):
        fields = self.protocol.request(request)
        target = text(fields["TargetUserId"], maximum=512)
        return self.protocol.response(request, value=self.service.profile(request, target))

    def update_profile(self, request):
        fields = self.protocol.request(request)
        profile = self.service.update_profile(request, fields)
        return self.protocol.response(request, {
            "UpdateAccumulateInfos": self.service.state(request).get('UpdateAccumulateInfos', []),
            "ProfileInfo": profile})
