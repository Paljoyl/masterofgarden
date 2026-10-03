"""Validate the selected conversation and answer; progression is server-derived."""
from ..protocol import integer


class QuizHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def answer(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['QuizCode'], minimum=1)
        option = integer(fields['AnswerOption'], minimum=1, maximum=2**31 - 1)
        progress = integer(fields['TutorialProgress'], maximum=2**31 - 1)
        return self.protocol.response(request, self.service.answer(request, code, option, progress))
