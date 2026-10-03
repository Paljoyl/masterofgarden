"""Player-owned home selection, read and written within one player transaction."""
from ..protocol import LocalError


class HomeService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def set_character(self, request, costume_code, is_random):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None:
            raise LocalError('player_storage_unavailable', 503)
        with repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            if 'HomeInfo' not in state or 'HomeCharacters' not in state:
                raise LocalError('local_home_seed_not_found', 503)
            owned = any(costume_code in self.protocol.fields('HomeCharacterInfo', value)['HomeCharacterCostumeCodes']
                        for value in state['HomeCharacters'])
            if not owned:
                raise LocalError('home_costume_not_owned', 403)
            changed = self.protocol.fields('HomeInfo', state['HomeInfo'])['CharacterCostumeCode'] != costume_code
            repository.set_home_character(session.player_id, costume_code, is_random)
            if changed and self.players.timing is not None:
                self.players.timing.event(session.player_id, 45, int(self.players.clock()))
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []), **{name: state[name] for name in
                    ('HomeInfo', 'HomeCharacters', 'QuizAnswers')}}
