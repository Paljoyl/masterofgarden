"""Arena entry information assembled from the authenticated player's current state."""
from PostgreSQL.arena import ArenaStore
from ..protocol import LocalError
from .inventory import total_battle_power


class ArenaService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def personal(self, session, state):
        user = self.protocol.fields('UserInfo', state['User'])
        character = next((self.protocol.fields('CharacterInfo', row) for row in state['Characters']
                          if row[0] == user['ProfileCharacterCode']), None)
        auxiliary = {}
        template = self.players.templates.get((session.player_id, session.variant, '/profile/getprofileinfo'))
        if template is not None:
            profile = self.protocol.fields('GetProfileInfoResponse', template)['ProfileInfo']
            captured = self.protocol.fields('UserPersonalInfo',
                self.protocol.fields('UserProfileInfo', profile)['UserPersonalInfo'])
            if captured['Id'] != session.player_id:
                raise LocalError('profile_owner_mismatch', 503)
            auxiliary = {name: captured[name] for name in ('Introduction', 'SwitchableCharacterIndex', 'HonorCode')}
        return self.protocol.model('UserPersonalInfo', {
            'Id': session.player_id, 'Name': user['Name'], 'CharacterCode': user['ProfileCharacterCode'],
            'Level': user['Level'], 'LastLoggedInAt': user['LastLoggedInAt'],
            'Introduction': auxiliary.get('Introduction', ''),
            'HonorCode': state.get('ProfileHonorCode', auxiliary.get('HonorCode')) or None,
            'TotalBattlePower': total_battle_power(self.players, self.protocol, session), 'IsFollower': False,
            'Rank': character['Rank'] if character else 0, 'Rarity': character['Rarity'] if character else 0,
            'SwitchableCharacterIndex': auxiliary.get('SwitchableCharacterIndex', 0),
            'IllustrationIndex': user['ProfileIllustrationIndex'],
        })

    def info(self, request, category):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        with repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            store = ArenaStore(repository)
            code = store.current(category, now)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'ArenaCode': code, 'PersonalInfo': self.personal(session, state),
                    **store.info(session.player_id, code, now)}

    def _query(self, request, code, build):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        with repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            store = ArenaStore(repository)
            definition = store.require(code)
            info = store.info(session.player_id, code, now)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    **build(session, state, store, definition, info, now)}

    def _npc(self, store, code, rank, grade):
        data = store.timing.data
        required = ('arena_npc_master', 'arena_npc_name_master', 'arena_npc_party_group_master', 'arena_npc_party_master')
        if any(not data.get(name) for name in required):
            raise LocalError('local_arena_npc_configuration_missing', 503)
        definitions = [r for r in data['arena_npc_master'] if r['ArenaCode'] == code
                       and r['RankRangeMin'] <= rank <= r['RankRangeMax']]
        if not definitions:
            raise LocalError('local_arena_npc_rank_configuration_invalid', 503)
        # The highest rank band intentionally has several NPC strength presets.
        definition = definitions[(rank + grade) % len(definitions)]
        groups = sorted(r['NpcPartyCode'] for r in data['arena_npc_party_group_master']
                        if r['Code'] == definition['NpcPartyGroupCode'])
        if not groups:
            raise LocalError('local_arena_npc_party_configuration_missing', 503)
        group = groups[(rank + grade) % len(groups)]
        parties = []
        for row in sorted((r for r in data['arena_npc_party_master'] if r['Code'] == group), key=lambda r: r['No']):
            characters = [self.protocol.model('CharacterInfo', {
                'Code': character, 'Level': definition['PlayerAndCharacterLevel'], 'Exp': 0,
                'Rank': definition['CharacterRank'], 'LimitBreak': definition['CharacterLimitBreak'],
                'Rarity': definition['CharacterRarity'], 'Closeness': 0,
            }) for character in row['CharacterCodes']]
            parties.append(self.protocol.model('ArenaPartyInfo', {
                'CharacterInfos': characters, 'EquipmentInfos': [], 'MagicItemEquipments': [],
                'PartyCharacterInfos': [self.protocol.model('PartyCharacterInfo', {
                    'CharacterInfo': character, 'SwitchableCharacterIndex': 0}) for character in characters],
            }))
        expected = 1 if store.require(code)['Category'] == 0 else 3
        if len(parties) != expected or any(len(party[0]) != 5 for party in parties):
            raise LocalError('local_arena_npc_party_configuration_invalid', 503)
        personal = self.protocol.model('UserPersonalInfo', {
            'Id': f'local-arena-npc:{code}:{rank}:{grade}',
            'Name': data['arena_npc_name_master'][rank % len(data['arena_npc_name_master'])]['Name'],
            'CharacterCode': parties[0][0][0][0], 'Level': definition['PlayerAndCharacterLevel'],
            'LastLoggedInAt': 0, 'Introduction': '', 'HonorCode': None, 'TotalBattlePower': 0,
            'IsFollower': False, 'Rank': definition['CharacterRank'], 'Rarity': definition['CharacterRarity'],
            'SwitchableCharacterIndex': 0, 'IllustrationIndex': 0,
        })
        return self.protocol.model('ArenaUserInfo', {
            'PersonalInfo': personal, 'PartyInfos': parties, 'Rank': rank,
            'SkillTreeInfo': self.protocol.model('SkillTreeInfo', {'NodeInfos': [], 'FloorCompleteInfos': []}),
            'SkillTreeBattlePower': [0] * expected,
        })

    def _enemy_infos(self, store, code, rank):
        matching = [r for r in store.timing.data.get('arena_matching_master', [])
                    if r['ArenaCode'] == code and r['RankRangeMin'] <= rank <= r['RankRangeMax']]
        if len(matching) != 1:
            raise LocalError('local_arena_matching_configuration_invalid', 503)
        row = matching[0]
        # Stable local NPC selection within the client's matching rank window.
        # These are installed NPC rosters, never another player's saved party.
        offsets = (row['RankDiffHigh'], (row['RankDiffLow'] + row['RankDiffHigh']) // 2, row['RankDiffLow'])
        return {grade: self._npc(store, code, max(1, min(store.initial_rank(), rank - offset)), grade)
                for grade, offset in enumerate(offsets, 1)}

    def enemies(self, request, code):
        def build(session, state, store, definition, info, now):
            if store.current(definition['Category'], now) != code:
                raise LocalError('local_arena_not_open', 409)
            return {'EnemyInfos': self._enemy_infos(store, code, info['Rank'])}
        return self._query(request, code, build)

    def _self_user(self, session, state, definition, rank):
        defense_type = 3 if definition['Category'] == 0 else 5
        parties = []
        for value in state['Parties']:
            party = self.protocol.fields('PartyInfo', value)
            if party['Type'] != defense_type or not party['IsActive']:
                continue
            characters = [self.protocol.fields('PartyCharacterInfo', r)['CharacterInfo'] for r in party['CharacterInfos']]
            codes = {character[0] for character in characters}
            parties.append(self.protocol.model('ArenaPartyInfo', {
                'CharacterInfos': characters, 'EquipmentInfos': [r for r in state['Equipments'] if r[0] in codes],
                'MagicItemEquipments': party['MagicItemEquipments'], 'PartyCharacterInfos': party['CharacterInfos'],
            }))
        return self.protocol.model('ArenaUserInfo', {
            'PersonalInfo': self.personal(session, state), 'PartyInfos': parties, 'Rank': rank,
            'SkillTreeInfo': self.protocol.model('SkillTreeInfo', {'NodeInfos': [], 'FloorCompleteInfos': []}),
            'SkillTreeBattlePower': [0] * len(parties),
        })

    def rankings(self, request, code):
        def build(session, state, store, definition, info, now):
            rank = info['Rank']
            entries = list(self._enemy_infos(store, code, rank).values())
            entries.append(self._self_user(session, state, definition, rank))
            category_codes = [r['Code'] for r in store.timing.data['arena_master']
                              if r['Category'] == definition['Category']]
            best = store.connection.execute('''SELECT min(rank) FROM public.player_arena_states
                WHERE player_id=%s AND arena_code=ANY(%s) AND rank>0''', (session.player_id, category_codes)).fetchone()[0]
            return {'RankingInfos': sorted(entries, key=lambda row: row[2]), 'Rank': rank,
                    'HighestRankOnSeason': rank, 'HighestRankOnCategory': best or rank}
        return self._query(request, code, build)

    def histories(self, request, code):
        # No local arena battles have been settled yet.
        return self._query(request, code, lambda *args: {'HistoryInfos': []})
