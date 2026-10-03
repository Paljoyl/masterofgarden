"""Validate the installed client's nine Sanctuary request models."""
from functools import partial

from ..protocol import integer


class Dungeon2Handlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol
        for kind in ('info', 'hierarchy', 'square', 'characters', 'enemies', 'items', 'status', 'reset', 'complete'):
            setattr(self, kind, partial(self.handle, kind))

    def handle(self, kind, request):
        fields = self.protocol.request(request)
        for name in ('Dungeon2Code', 'HierarchyIndex'):
            if name in fields:
                integer(fields[name], minimum=1)
        if 'SquareIndex' in fields:
            integer(fields['SquareIndex'])
        if kind == 'complete':
            integer(fields['ArtifactSelectIndex'], minimum=-1, maximum=100)
            integer(fields['ChoiceType'], maximum=2)
            integer(fields['RewardIndex'], maximum=2)
        return self.protocol.response(request, self.service.query(request, kind, fields))
