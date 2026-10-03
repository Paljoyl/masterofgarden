"""Chat answer responses built from the player's committed current state."""
from PostgreSQL.quiz import QuizStore
from ..protocol import LocalError
from .inventory import inventory_update, total_battle_power


class QuizService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._store = None

    def answer(self, request, quiz_code, option, tutorial_progress):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None:
            raise LocalError('player_storage_unavailable', 503)
        if self._store is None:
            self._store = QuizStore(repository)
        with repository.transaction(session.player_id):
            result = self._store.answer(session.player_id, quiz_code, option,
                                        int(self.players.clock()), tutorial_progress)
            state = self.players._state(session.player_id)
            home = next(row for row in state['HomeCharacters'] if self.protocol.fields(
                'HomeCharacterInfo', row)['HomeCharacterCode'] == result['home_character_code'])
            answer = next(row for row in state['QuizAnswers'] if self.protocol.fields(
                'QuizAnswerInfo', row)['QuizCode'] == quiz_code)
            user = self.protocol.fields('UserInfo', state['User'])
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    'HomeCharacterInfo': home, 'QuizAnswerInfo': answer, 'QuizStamina': user['QuizStamina'],
                    'HomeSituationInfos': self.protocol.fields('HomeInfo', state['HomeInfo'])['Situations'],
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, result['changed_codes']),
                    'TotalBattlePower': total_battle_power(self.players, self.protocol, session)}
