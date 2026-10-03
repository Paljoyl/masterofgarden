"""The client's eight-field quest-start request and seven-field response."""
from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.quest_challenges import QuestChallengeError
from ..protocol import LocalError, integer
from ..services.quest_result import QuestResultService
from ..services.quest_actions import QuestActions


class QuestHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol
        self.results = QuestResultService(service)
        self.actions = QuestActions(service, self.results)

    def skip(self, request):
        fields = self.protocol.request(request)
        integer(fields['QuestCode'], minimum=1)
        integer(fields['SkipCount'], minimum=1, maximum=1000)
        if (fields['ItemCode'] is None) != (fields['RequiredCount'] is None):
            raise LocalError('local_quest_skip_target_invalid')
        if fields['ItemCode'] is not None:
            integer(fields['ItemCode'], minimum=1)
            integer(fields['RequiredCount'], minimum=1)
        try:
            result = self.actions.skip(request, fields)
        except QuestChallengeError as exc:
            raise LocalError(exc.code, exc.status) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_quest_state_invalid', 503) from exc
        return self.protocol.response(request, result)

    def recover_quest(self, request):
        return self._recover(request, 'QuestCode', False)

    def recover_group(self, request):
        return self._recover(request, 'QuestGroupCode', True)

    def _recover(self, request, name, group):
        fields = self.protocol.request(request)
        code = integer(fields[name], minimum=1)
        try:
            result = self.actions.recover(request, code, group=group)
        except QuestChallengeError as exc:
            raise LocalError(exc.code, exc.status) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_quest_state_invalid', 503) from exc
        return self.protocol.response(request, result)

    def result(self, request):
        fields = self.protocol.request(request)
        integer(fields['QuestCode'], minimum=1)
        for name in ('TutorialProgress', 'ClearSeconds', 'EventBossBoostCount', 'FreeChallengeCount'):
            integer(fields[name], maximum=2**31 - 1)
        integer(fields['Result'], maximum=5)
        unique_id = fields['QuestUniqueId']
        sanctuary = fields['Dungeon2'] is not None
        if not isinstance(unique_id, bytes) or len(unique_id) != 16 or (not sanctuary and not any(unique_id)):
            raise LocalError('local_quest_unique_id_invalid')
        if sanctuary:
            return self.protocol.response(request, self.dungeon2.result(request, fields))
        try:
            result = self.results.result(request, fields)
        except QuestChallengeError as exc:
            raise LocalError(exc.code, exc.status) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_quest_state_invalid', 503) from exc
        return self.protocol.response(request, result)

    def start(self, request):
        fields = self.protocol.request(request)
        integer(fields['QuestCode'], minimum=1)
        for name in ('GuildBattleBossCode', 'GuildBattleLoopCount', 'EventBossBoostCount', 'FreeChallengeCount'):
            integer(fields[name], maximum=2**63 - 1 if name == 'GuildBattleBossCode' else 2**31 - 1)
        unique_id = fields['QuestUniqueId']
        if not isinstance(unique_id, bytes) or len(unique_id) != 16 or not any(unique_id):
            raise LocalError('local_quest_unique_id_invalid')
        try:
            result = self.service.start(request, fields)
        except QuestChallengeError as exc:
            raise LocalError(exc.code, exc.status) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_quest_state_invalid', 503) from exc
        return self.protocol.response(request, result)
