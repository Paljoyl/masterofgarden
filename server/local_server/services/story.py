"""Story API response assembled inside the player's settlement transaction."""
from PostgreSQL.story import StoryStore
from ..protocol import LocalError
from .inventory import inventory_update


class StoryService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._store = None

    def store(self):
        repository = self.players.repository
        if repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        if self._store is None:
            self._store = StoryStore(repository)
        return self._store

    def open(self, request, code):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            result = store.open(session.player_id, code, int(self.players.clock()))
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'StoryInfo': result['StoryInfo'],
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, result['changed_codes'])}

    def read(self, request, code, flags, tutorial_progress):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            result = store.read(session.player_id, code, flags,
                                int(self.players.clock()), tutorial_progress)
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], **result}
