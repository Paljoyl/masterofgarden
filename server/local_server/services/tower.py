"""Player-owned Tower entry, whole-floor battle summaries and reward receipts."""
from contextlib import contextmanager
from hashlib import sha256

from mog_protocol.codec import decode, encode
from PostgreSQL.game_time import timestamp
from PostgreSQL.tower import TowerStore
from ..protocol import LocalError, sequence
from .inventory import inventory_update

TOWER_PARTY_TYPE = 11
TOWER_PARTY_COUNT = 5


class TowerService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    @contextmanager
    def context(self, request, code):
        session = self.players.session(request)
        repo = self.players.repository
        if repo is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        with repo.transaction(session.player_id):
            state = self.players._state(session.player_id)
            store = TowerStore(repo)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            key = (session.player_id, session.variant, '/tower/towertop')
            captured = self.players.templates.get(key)
            seed, top = [], None
            if captured is not None:
                top = self.protocol.fields('TowerTopResponse', captured, strict=True)
                seed = sequence(top['TowerFloors'] or [])
            else:
                home = self.players.templates.get((session.player_id, session.variant, '/gametop/getgametopinfo'))
                if home is not None:
                    seed = self.protocol.fields('GetGameTopInfoResponse', home)['TowerFloors'] or []
            now = store.initialize(session.player_id, code, seed, self.protocol, now)
            # A captured same-day receipt is already owned inventory. Older
            # observations cannot claim today's reward on the player's behalf.
            captured_at = self.players.template_times.get(key)
            if top is not None and top['HasDailyRewardReceived'] and captured_at is not None:
                if self.players.timing.clock.day(int(captured_at)) == self.players.timing.clock.day(now):
                    cleared = [r[1] for r in store.view(session.player_id, code) if r[2]]
                    if cleared:
                        store.receipt(session.player_id, code, 'daily', self.players.timing.clock.day(now), max(cleared), now)
            yield session.player_id, store, state, now

    def top(self, request, code):
        with self.context(request, code) as (player, store, _, now):
            floors = store.view(player, code)
            cleared = [r[1] for r in floors if r[2]]
            rewards, changed = [], set()
            if cleared:
                floor = max(cleared)
                rewards, changed = store.grant(player, code, 'daily', self.players.timing.clock.day(now),
                    floor, store.require(code, floor)['DailyRewardCode'], now)
            self.players.timing.event(player, 68, now)
            state = self.players._state(player)
            receipt = store.connection.execute('''SELECT floor FROM public.player_tower_rewards
                WHERE player_id=%s AND tower_code=%s AND kind='daily' AND period=%s''',
                (player, code, self.players.timing.clock.day(now))).fetchone()
            if receipt is not None:
                # A lost response must still synchronize the already-granted
                # balances, including rewards from a lower floor cleared today.
                reward_code = store.require(code, receipt[0])['DailyRewardCode']
                changed.update(r['ItemCode'] for r in store.rewards[reward_code])
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'TowerFloors': floors,
                    'TowerGuildMemberRankInfos': [], 'HasDailyRewardReceived': receipt is not None,
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, changed),
                    'DailyRewardViewInfo': [[r['ItemCode'], r['Count'], None] for r in rewards]}

    @staticmethod
    def unique(value):
        if not isinstance(value, bytes) or len(value) != 16 or not any(value):
            raise LocalError('local_tower_unique_id_invalid')
        return value

    def parties(self, player, supplied, state, progress, total):
        parties = [self.players._canonical_party(player, value, state)
                   for value in sequence(supplied, maximum=TOWER_PARTY_COUNT)]
        start = progress['index']
        if len(parties) not in (total, total - start):
            raise LocalError('local_tower_party_round_count_invalid')
        offset = 0 if len(parties) == total else start
        rounds = [(offset + index, party) for index, party in enumerate(parties)]
        numbers, seen, magic_seen = set(), {r[0] for r in progress['characters']}, {r[2] for r in progress['magic']}
        if start and not progress['characters']:
            raise LocalError('local_tower_continue_state_missing_reset_required', 409)
        for index, party in rounds:
            if party[0] != TOWER_PARTY_TYPE or not 1 <= party[2] <= TOWER_PARTY_COUNT or party[2] in numbers:
                raise LocalError('local_tower_party_invalid')
            numbers.add(party[2])
            if party[8]:
                raise LocalError('local_tower_rental_not_supported')
            if index < start:
                continue
            codes = {r[0][0] for r in party[5] if r[0] is not None}
            if not 1 <= len(codes) <= 5 or codes.intersection(seen):
                raise LocalError('local_tower_party_character_used')
            for equipment in party[6]:
                if equipment[2] is not None:
                    if equipment[0] not in codes or equipment[2][0] in magic_seen:
                        raise LocalError('local_tower_party_magic_item_used')
                    magic_seen.add(equipment[2][0])
            seen.update(codes)
        return rounds

    def start(self, request, fields):
        unique = self.unique(fields['QuestUniqueId'])
        digest = sha256(encode(self.protocol.model('TowerStartRequest', fields))).hexdigest()
        code, floor = fields['TowerCode'], fields['Floor']
        with self.context(request, code) as (player, store, state, now):
            previous = store.battle(player, unique)
            if previous is not None:
                if previous[0:2] != (code, floor) or previous[3] != digest or previous[5] == 'abandoned':
                    raise LocalError('local_tower_start_id_conflict', 409)
                return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'QuestUniqueId': unique}
            store.unlocked(player, code, floor)
            definition = store.require(code, floor)
            progress = store.progress(player, code, floor)
            if fields['QuestCode'] != definition['QuestCodes'][progress['index']]:
                raise LocalError('local_tower_start_quest_mismatch', 409)
            rounds = self.parties(player, fields['Parties'], state, progress, len(definition['QuestCodes']))
            # A reconnect replaces the unfinished attempt. Its delayed result
            # cannot settle the new attempt, and completed rounds remain saved.
            store.abandon(player)
            store.connection.execute('''INSERT INTO public.player_tower_battles
                (player_id,unique_id,tower_code,floor,starting_round_index,start_hash,parties,state)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'active')''',
                (player, unique, code, floor, progress['index'], digest, encode(rounds)))
            for _, party in rounds:
                store.repo.save_party(player, party)
            self.players.timing.event(player, 69, now)
            state = self.players._state(player)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'QuestUniqueId': unique}

    def result(self, request, fields):
        unique = self.unique(fields['QuestUniqueId'])
        digest = sha256(encode(self.protocol.model('TowerSetResultRequest', fields))).hexdigest()
        code, floor = fields['TowerCode'], fields['Floor']
        with self.context(request, code) as (player, store, state, now):
            battle = store.battle(player, unique)
            if battle is None or battle[:2] != (code, floor):
                raise LocalError('local_tower_battle_not_started', 409)
            if battle[5] == 'settled':
                if battle[6] != digest:
                    raise LocalError('local_tower_result_id_conflict', 409)
                result = self.protocol.fields('TowerSetResultResponse', decode(bytes(battle[7])), strict=True)
                result['UpdateAccumulateInfos'] = state['UpdateAccumulateInfos']
                result['InventoryUpdateInfo'] = inventory_update(self.protocol, state, [r[1] for r in result['FirstClearRewardInfos']])
                return result
            if battle[5] != 'active':
                raise LocalError('local_tower_battle_closed', 409)
            definition = store.require(code, floor)
            total, index = len(definition['QuestCodes']), fields['ContinueRoundIndex']
            starting = battle[2]
            progress = store.progress(player, code, floor)
            if progress['index'] != starting or not starting <= index <= total:
                raise LocalError('local_tower_result_round_invalid')
            won = fields['Result'] == 1
            if won != (index == total):
                raise LocalError('local_tower_result_round_invalid')
            # Native SendBattleResultAsync sends one whole-floor summary:
            # ContinueRoundIndex counts all wins, including saved prior rounds.
            quest_index = total - 1 if won else index
            if fields['QuestCode'] != definition['QuestCodes'][quest_index]:
                raise LocalError('local_tower_result_quest_mismatch')
            rounds = dict(decode(bytes(battle[4])))
            characters = {r[0]: r for r in progress['characters']}
            magic = {(r[0], r[1]): r for r in progress['magic']}
            for round_index in range(starting, index):
                party = rounds[round_index]
                for member in party[5]:
                    if member[0] is not None:
                        characters[member[0][0]] = [member[0][0], round_index]
                for equipment in party[6]:
                    if equipment[2] is not None:
                        magic[(equipment[0], equipment[1])] = [equipment[0], equipment[1], equipment[2][0]]
            rewards, changed = [], set()
            if won:
                rewards, changed = store.grant(player, code, 'first', floor, floor,
                    definition['FirstClearRewardCode'], now)
                progress.update(count=progress['count'] + 1, index=0, characters=[], magic=[],
                                first_at=progress['first_at'] if progress['count'] else now)
            else:
                progress.update(index=index, characters=list(characters.values()), magic=list(magic.values()))
            store.save(player, code, floor, progress)
            state = self.players._state(player)
            result = {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                      'FirstClearRewardInfos': [[r['Type'], r['ItemCode'], r['Count'], r['DisplayPriority']] for r in rewards],
                      'InventoryUpdateInfo': inventory_update(self.protocol, state, changed)}
            store.connection.execute('''UPDATE public.player_tower_battles SET state='settled',result_hash=%s,response=%s
                WHERE player_id=%s AND unique_id=%s''',
                (digest, encode(self.protocol.model('TowerSetResultResponse', result)), player, unique))
            return result

    def continue_info(self, request, code, floor, *, reset=False):
        with self.context(request, code) as (player, store, state, _):
            store.require(code, floor)
            progress = store.progress(player, code, floor)
            if reset:
                progress.update(index=0, characters=[], magic=[])
                store.abandon(player, code, floor)
                store.save(player, code, floor, progress)
                return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos']}
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    'TowerCharacterInfos': progress['characters'], 'TowerMagicItemInfos': progress['magic']}

    def guild_rank(self, request, code, guild_id):
        with self.context(request, code) as (_, _, state, _):
            if not isinstance(guild_id, bytes) or len(guild_id) != 16:
                raise LocalError('local_tower_guild_id_invalid')
            if any(guild_id):
                raise LocalError('local_tower_guild_membership_not_found', 404)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'GuildId': guild_id,
                    'EmblemCode': 0, 'GuildName': None, 'TowerGuildMemberRankInfos': []}

    def clear_rate(self, request, code):
        with self.context(request, code) as (player, store, state, now):
            count = store.connection.execute('''SELECT count(*) FROM public.player_tower_states
                WHERE tower_code=%s''', (code,)).fetchone()[0]
            clears = dict(store.connection.execute('''SELECT floor,count(*) FROM public.player_tower_floors
                WHERE tower_code=%s AND clear_count>0 GROUP BY floor''', (code,)).fetchall())
            floors = [r[1] for r in store.view(player, code) if r[2]]
            highest = max(floors, default=0)
            first_at = store.progress(player, code, highest)['first_at'] if highest else None
            user = self.protocol.fields('UserInfo', state['User'])
            character = next((r for r in state['Characters'] if r[0] == user['ProfileCharacterCode']), None)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    'TowerFloorClearRates': [[floor, f'{clears.get(floor, 0) * 100 / count:.2f}']
                        for tower, floor in sorted(store.floors) if tower == code],
                    'TowerFloorClearRatesUpdateAt': timestamp(now),
                    'ClearFloorInfo': [highest, timestamp(first_at or 0)],
                    'TowerMyProfile': [player, user['Name'], user['ProfileCharacterCode'], state.get('ProfileHonorCode') or None,
                        character[3] if character else 1, character[5] if character else 1, user['ProfileIllustrationIndex']]}
