"""Ordinary quest start responses from owned parties and TW master rules."""
from hashlib import sha256

from mog_protocol.codec import encode
from PostgreSQL.quest import QuestStore
from PostgreSQL.quest_challenges import QuestChallenges
from ..protocol import LocalError, integer, sequence
from .character_catalog import CharacterCatalog


class QuestService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._definitions = None
        self._training_catalog = None

    @property
    def repository(self):
        if self.players.repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        return self.players.repository

    @property
    def definitions(self):
        if self._definitions is None:
            data = dict(self.repository.connection.execute('SELECT name,data FROM public.quest_definitions').fetchall())
            if any(not isinstance(data.get(name), list) or not data[name] for name in
                   ('quest_master', 'quest_group_master', 'battle_wave_master')):
                raise LocalError('local_quest_configuration_missing', 503)
            self._definitions = {'quests': {r['Code']: r for r in data['quest_master']},
                                 'groups': {r['Code']: r for r in data['quest_group_master']},
                                 'waves': {r['QuestCode'] for r in data['battle_wave_master']},
                                 'training_parties': {r['QuestCode']: r['Characters'] for r in
                                     data.get('training_quest_party_master', [])}}
        return self._definitions

    def training_rows(self, quest):
        """Lesson actors are master presets, not the owned start-request party."""
        rows = self.definitions['training_parties'].get(quest['Code'])
        if not isinstance(rows, list) or not 1 <= len(rows) <= 5:
            raise LocalError('local_quest_training_party_configuration_missing', 503)
        members = [r.get('CharacterCode') for r in rows]
        if (any(type(c) is not int or c <= 0 for c in members)
                or len(set(members)) != len(members)
                or any(type(r.get(key)) is not int or r[key] <= 0
                       for r in rows for key in ('Level', 'CharacterRank'))):
            raise LocalError('local_quest_training_party_configuration_invalid', 503)
        return rows

    def training_members(self, quest):
        return {r['CharacterCode'] for r in self.training_rows(quest)}

    def training_suspension(self, player_id, fields, quest):
        """Build a temporary lesson party; no actors or parties enter player storage."""
        info = self.protocol.fields('QuestSuspensionPartyInfo', fields['QuestSuspensionParty'], strict=True)
        if info['CurrentWaveCount'] != 1:
            raise LocalError('local_quest_resume_not_implemented', 501)
        if info['Support'] is not None or info['SupportQuestSuspensionCharacter'] is not None:
            raise LocalError('local_quest_support_not_implemented', 501)
        # Both saved parties and client-created placeholders are valid envelopes
        # for lessons. Their contents do not define the scripted battle actors.
        for value in [*sequence(fields['Party'], maximum=5), info['Party']]:
            if value is None:
                continue
            party = self.protocol.fields('PartyInfo', value, strict=True)
            if party['UserId'] not in (None, '', player_id):
                raise LocalError('party_owner_mismatch', 403)
        for value in sequence(info['SelfQuestSuspensionCharacters'], maximum=5):
            row = self.protocol.fields('QuestSuspensionCharacterInfo', value, strict=True)
            integer(row['CharacterCode'], minimum=1)
            for key in ('Hp', 'Sp'):
                if row[key] is not None:
                    integer(row[key])
                    if row[key]:
                        raise LocalError('local_quest_resume_not_implemented', 501)
        if self._training_catalog is None:
            self._training_catalog = CharacterCatalog(self.repository.connection)
        catalog = self._training_catalog
        members, characters = [], []
        for row in self.training_rows(quest):
            code = row['CharacterCode']
            master = catalog.characters.get(code)
            curve = catalog.curves.get(master['CharacterExpCode'], []) if master is not None else []
            level = next((r for r in curve if r['Level'] == row['Level']), None)
            if master is None or level is None:
                raise LocalError('local_quest_training_character_configuration_missing', 503)
            # Preset level/rank are independent of the player's level and owned
            # characters. Use the character master's rarity and XP curve only.
            character = self.protocol.model('CharacterInfo', {
                'Code': code, 'Level': row['Level'], 'Exp': level['TotalExp'],
                'Rank': row['CharacterRank'], 'LimitBreak': 0,
                'Rarity': master['DefaultRarity'], 'Closeness': 0})
            members.append(self.protocol.model('PartyCharacterInfo', {
                'CharacterInfo': character, 'SwitchableCharacterIndex': 0}))
            characters.append(self.protocol.model('QuestSuspensionCharacterInfo', {
                'CharacterCode': code, 'Hp': 0, 'Sp': 0}))
        party = self.protocol.model('PartyInfo', {
            'Type': 1, 'UserId': player_id, 'No': 0, 'Name': '', 'IsActive': True,
            'CharacterInfos': members, 'MagicItemEquipments': [], 'TotalPower': 0,
            'RentalCharacterInfos': []})
        return self.protocol.model('QuestSuspensionPartyInfo', {
            'CurrentWaveCount': 1, 'SelfQuestSuspensionCharacters': characters,
            'Party': party, 'Support': None, 'SupportQuestSuspensionCharacter': None})

    def check_quest(self, state, code, *, count=1):
        quest = self.definitions['quests'].get(code)
        if quest is None:
            raise LocalError('local_quest_not_found', 404)
        group = self.definitions['groups'].get(quest['QuestGroupCode'])
        if group is None or code not in self.definitions['waves']:
            raise LocalError('local_quest_configuration_missing', 503)
        # QuestType.Battle=0 and Training=1 use the same start/result models.
        # The client owns Training's lesson scripts and battle presentation.
        # Normal EventQuest/SubEventQuest stages share this battle protocol.
        # Boss/guild/dungeon categories need their own settlement state.
        training = quest['QuestType'] == 1
        if not training and (quest['QuestType'] != 0 or quest['BossType'] or quest['RegulationCode']
                             or not QuestChallenges.ordinary(group)):
            raise LocalError('local_quest_type_not_implemented', 501)
        # Keep locally installed event stages available regardless of the
        # official season, while rejecting orphaned/mismatched definitions.
        for name, key in (('event_master', 'EventCode'), ('sub_event_master', 'SubEventCode')):
            if group[key] and group[key] not in self.players.timing.index.get(name, {}):
                raise LocalError('local_quest_event_configuration_missing', 503)
        if training:
            # Reject a missing preset before a battle starts, rather than
            # admitting it only to fail when the client submits lesson actors.
            self.training_members(quest)
        cleared = {r[0]: r[1] for r in state['ClearedQuests']}
        if any(c and not cleared.get(c, 0) for c in quest['QuestCodeForUnlock']):
            raise LocalError('local_quest_locked', 409)
        stories = {r[0]: r[1] for r in state['Stories']}
        if quest['StoryCodeForUnlock'] and stories.get(quest['StoryCodeForUnlock']) != 2:
            raise LocalError('local_quest_story_locked', 409)
        user = self.protocol.fields('UserInfo', state['User'])
        if user['Stamina'] is None:
            raise LocalError('local_stamina_state_missing', 503)
        cost = integer(quest['Stamina'], maximum=2**31 - 1) * count
        if self.protocol.fields('Stamina', user['Stamina'])['Value'] < cost:
            raise LocalError('local_quest_insufficient_stamina', 409)
        return quest

    def check_day(self, quest, now):
        # Scripted lessons are not daily battles. The raid lesson's group has
        # EnabledDaysOfWeek=0, which must not make its tutorial inaccessible.
        if quest['QuestType'] == 1:
            return
        # DaysOfWeek uses Sunday=1 through Saturday=64. Use the game's
        # configured reset boundary rather than the host's midnight.
        group = self.definitions['groups'][quest['QuestGroupCode']]
        weekday = (self.players.timing.clock.day(now) + 4) % 7
        if not group['EnabledDaysOfWeek'] & (1 << weekday):
            raise LocalError('local_quest_unavailable_today', 409)

    def parties(self, player_id, values, state):
        parties = [self.players._canonical_party(player_id, value, state)
                   for value in sequence(values, maximum=5)]
        keys = [(r[0], r[2]) for r in parties]
        if len(set(keys)) != len(keys):
            raise LocalError('duplicate_party')
        if any(r[0] != 1 or r[8] for r in parties):
            raise LocalError('local_quest_party_type_not_implemented', 501)
        active = [r for r in parties if r[4]]
        if len(active) != 1:
            raise LocalError('local_quest_active_party_invalid')
        selected = active[0]
        members = [r[0][0] for r in selected[5] if r[0] is not None]
        if not 1 <= len(members) <= 5:
            raise LocalError('local_quest_party_size_invalid')
        if any(r[1] for r in selected[5]):
            raise LocalError('local_quest_switch_character_not_implemented', 501)
        for equipment in selected[6]:
            if equipment[2] is not None and equipment[0] not in members:
                raise LocalError('local_quest_magic_character_mismatch')
        return parties, selected, set(members)

    def suspension(self, player_id, value, selected, members, state):
        info = self.protocol.fields('QuestSuspensionPartyInfo', value, strict=True)
        if info['CurrentWaveCount'] != 1:
            raise LocalError('local_quest_resume_not_implemented', 501)
        if info['Support'] is not None or info['SupportQuestSuspensionCharacter'] is not None:
            raise LocalError('local_quest_support_not_implemented', 501)
        canonical = self.players._canonical_party(player_id, info['Party'], state)
        if canonical != selected:
            raise LocalError('local_quest_suspension_party_mismatch')
        characters, seen = [], set()
        for row in sequence(info['SelfQuestSuspensionCharacters'], maximum=5):
            fields = self.protocol.fields('QuestSuspensionCharacterInfo', row, strict=True)
            code = integer(fields['CharacterCode'], minimum=1)
            if code not in members or code in seen:
                raise LocalError('local_quest_suspension_character_mismatch')
            seen.add(code)
            # The recorded fresh start sends HP/SP zero. Preserve the client's
            # initial placeholders, as the client's MockResponseService does.
            for name in ('Hp', 'Sp'):
                if fields[name] is not None:
                    integer(fields[name])
                    if fields[name]:
                        raise LocalError('local_quest_resume_not_implemented', 501)
            characters.append(self.protocol.model('QuestSuspensionCharacterInfo', fields))
        if seen != members:
            raise LocalError('local_quest_suspension_character_mismatch')
        return self.protocol.model('QuestSuspensionPartyInfo', {
            'CurrentWaveCount': 1, 'SelfQuestSuspensionCharacters': characters,
            'Party': selected, 'Support': None, 'SupportQuestSuspensionCharacter': None})

    def start(self, request, fields):
        session = self.players.session(request)
        digest = sha256(encode(fields)).hexdigest()
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            store = QuestStore(self.repository)
            previous = store.previous(session.player_id, fields['QuestUniqueId'], digest)
            if previous is not None:
                return self.protocol.fields('QuestStartResponse', self.protocol.model('QuestStartResponse',
                    {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', [])}, previous))
            if (fields['GuildBattleBossCode'] or fields['GuildBattleLoopCount']
                    or fields['FreeChallengeCount'] or fields['EventBossBoostCount'] not in (0, 1)):
                raise LocalError('local_quest_special_battle_not_implemented', 501)
            quest = self.check_quest(state, fields['QuestCode'])
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            self.check_day(quest, now)
            if self.players.timing.quest_challenges is None:
                raise LocalError('local_quest_configuration_missing', 503)
            self.players.timing.quest_challenges.require(session.player_id, quest, now)
            if quest['QuestType'] == 1:
                parties = []
                suspension = self.training_suspension(session.player_id, fields, quest)
            else:
                parties, selected, members = self.parties(session.player_id, fields['Party'], state)
                suspension = self.suspension(session.player_id, fields['QuestSuspensionParty'], selected, members, state)
            status = self.protocol.model('QuestStatusInfo', {
                'UserId': session.player_id, 'QuestCode': fields['QuestCode'],
                'QuestSuspensionParty': suspension, 'QuestUniqueId': fields['QuestUniqueId']})
            result = {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []), 'QuestStatus': status,
                      'GuildBossHp': 0, 'IsGuildBossHpZero': False, 'GuildBattleTotalBuffWinCount': 0,
                      'GuildBattleLoopCount': 0, 'EventCurrentDefeatCount': 0}
            for party in parties:
                self.repository.save_party(session.player_id, party)
            # The start model has no stamina/inventory settlement fields. Record
            # the master cost for result settlement; starting grants no rewards.
            store.start(session.player_id, fields['QuestUniqueId'], fields['QuestCode'], digest,
                        suspension, self.protocol.model('QuestStartResponse', result), quest['Stamina'], now)
            return result
