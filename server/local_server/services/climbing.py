"""Player-owned World Tree battles, checkpoints and weekly reward receipts."""
from copy import deepcopy
from hashlib import sha256
import logging

from mog_protocol.codec import encode, decode
from PostgreSQL.climbing import ClimbingStore
from ..protocol import LocalError, integer, sequence
from .climbing_catalog import ClimbingCatalog
from .inventory import inventory_update

log = logging.getLogger('mog.climbing')


class ClimbingService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None

    def _repository(self):
        if self.players.repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        return self.players.repository

    def _load(self, session):
        repository = self._repository()
        state = self.players._state(session.player_id)
        store = ClimbingStore(repository, self.protocol)
        if self._catalog is None:
            self._catalog = ClimbingCatalog(repository.connection)
        now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
        fields = store.get(session.player_id)
        if fields is None:
            initial = store.fresh()
            template = self.players.templates.get((session.player_id, session.variant, '/climbing/climbingtop'))
            if template is not None:
                try:
                    captured = self.protocol.fields('ClimbingTopResponse', template, strict=True)
                    initial = store.validate({name: captured[name] for name in store.FIELDS})
                except LocalError:
                    log.warning('Skipped invalid player-bound climbing top seed')
            fields = store.seed(session.player_id, initial)
        code, saved_week, checked_at, runtime = store.runtime(session.player_id)
        now = max(now, checked_at)
        week, master = self._catalog.current(self.players.timing, now)
        if saved_week is None:
            # Captured rewards are already owned; seed receipts without granting again.
            for floor in range(1, min(fields['ReceivedRewardFloor'], self._catalog.max_floor) + 1):
                repository.connection.execute('''INSERT INTO public.player_climbing_rewards
                    (player_id,week_number,floor_number,received_at) VALUES (%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING''', (session.player_id, week, floor, now))
        elif saved_week != week or code != master['Code']:
            before = max(fields['BeforeClearFloor'], fields['ClearFloor'], fields['ReceivedRewardFloor'])
            fields = store.fresh()
            fields['BeforeClearFloor'] = before
            runtime = {}
            store.abandon(session.player_id)
        if fields['ClearFloor'] > self._catalog.max_floor or fields['FloorBattleIndex'] > 2:
            raise LocalError('local_climbing_saved_progress_invalid', 503)
        matching = fields['ClimbingMatchingEnemyInfos']
        if store.matching_period(session.player_id)[0] != master['Code'] or not self._complete(matching):
            matching = [self._catalog.matching(self.protocol, master, state, n)
                        for n in range(1, self._catalog.max_floor + 1)]
            fields['ClimbingMatchingEnemyInfos'] = matching
        store.save_matching(session.player_id, matching, master['Code'], week)
        store.save(session.player_id, fields, master['Code'], week, now, runtime)
        return repository, store, state, fields, runtime, master, week, now

    def _complete(self, matching):
        try:
            rows = [self.protocol.fields('ClimbingMatchingInfo', r, strict=True) for r in sequence(matching)]
            if sorted(r['FloorNumber'] for r in rows) != list(range(1, self._catalog.max_floor + 1)):
                return False
            for row in rows:
                integer(row['SyncLevel'], minimum=1)
                parties = [self.protocol.fields('ClimbingPartyInfo', p, strict=True)
                           for p in sequence(row['ClimbingPartyInfos'], maximum=2)]
                if sorted(p['No'] for p in parties) != [1, 2]:
                    return False
                if any(len(sequence(p['ClimbingPartyCharacterInfos'], maximum=5)) != 5 for p in parties):
                    return False
            return True
        except (LocalError, TypeError):
            return False

    def _target(self, supplied, master, fields, *, battle=True):
        if integer(supplied['ClimbingCode'], minimum=1) != master['Code']:
            raise LocalError('local_climbing_rotation_changed', 409)
        if 'FloorNumber' in supplied:
            floor = integer(supplied['FloorNumber'], minimum=1, maximum=self._catalog.max_floor)
            self._catalog.floor(master, floor)
            if battle and floor != fields['ClearFloor'] + 1:
                raise LocalError('local_climbing_floor_locked', 409)
        if 'FloorBattleIndex' in supplied:
            index = integer(supplied['FloorBattleIndex'], maximum=1)
            unique_id = supplied['ClimbingBattleUniqueId']
            if not isinstance(unique_id, bytes) or len(unique_id) != 16:
                raise LocalError('invalid_climbing_battle_id')
            return floor, index, unique_id

    def _parties(self, player_id, values, state, master):
        parties = []
        for value in sequence(values, maximum=2):
            row = self.protocol.fields('PartyInfo', value, strict=True)
            if row['Type'] != master['UserAttribute'] + 15 or row['No'] not in (1, 2):
                raise LocalError('local_climbing_party_invalid')
            party = self.players._canonical_party(player_id, value, state)
            sequence(party[5], maximum=5)
            party[8] = self._catalog.canonical_rentals(self.protocol, party[8], master)
            if sum(m[0] is not None for m in party[5]) + len(party[8]) > 5:
                raise LocalError('local_climbing_party_too_large')
            parties.append(party)
        if sorted(p[2] for p in parties) != [1, 2]:
            raise LocalError('local_climbing_two_parties_required')
        return sorted(parties, key=lambda p: p[2])

    @staticmethod
    def _party_signature(parties):
        return [(p[0], p[1], p[2], [(m[0][0] if m[0] else None, m[1]) for m in p[5]],
                 [(e[0], e[1], e[2][0] if e[2] else None) for e in p[6]], p[8]) for p in parties]

    @staticmethod
    def _snapshot(fields):
        return deepcopy([fields['ClimbingCharacterStatusInfos'], fields['ClimbingRentalCharacterStatusInfos']])

    @staticmethod
    def _battle(repository, player_id, unique_id, index):
        return repository.connection.execute('''SELECT week_number,climbing_code,floor_number,
            start_hash,party,state,result_hash,response FROM public.player_climbing_battles
            WHERE player_id=%s AND unique_id=%s AND round_index=%s''', (player_id, unique_id, index)).fetchone()

    def top(self, request):
        session = self.players.session(request)
        with self._repository().transaction(session.player_id):
            _, _, state, fields, _, _, _, _ = self._load(session)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], **fields}

    def start(self, request, supplied):
        session = self.players.session(request)
        fingerprint = sha256(encode(self.protocol.model('ClimbingStartRequest', supplied))).hexdigest()
        with self._repository().transaction(session.player_id):
            repository, store, state, fields, runtime, master, week, now = self._load(session)
            floor, index, unique_id = self._target(supplied, master, fields, battle=False)
            prior = self._battle(repository, session.player_id, unique_id, index)
            if prior is not None:
                if prior[:4] != (week, master['Code'], floor, fingerprint) or prior[5] == 'abandoned':
                    raise LocalError('local_climbing_battle_id_conflict', 409)
                return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos']}
            self._target(supplied, master, fields)
            if index != fields['FloorBattleIndex']:
                raise LocalError('local_climbing_battle_index_mismatch', 409)
            parties = self._parties(session.player_id, supplied['PartyInfos'], state, master)
            active = parties[index]
            codes = {m[0][0] for m in active[5] if m[0] is not None}
            rentals = {r[0] for r in active[8]}
            if not codes and not rentals:
                raise LocalError('local_climbing_party_empty')
            if any(self._catalog.attributes.get(code) != master['UserAttribute'] for code in codes):
                raise LocalError('local_climbing_character_attribute_mismatch')
            for selected, statuses in ((codes, fields['ClimbingCharacterStatusInfos']),
                                       (rentals, fields['ClimbingRentalCharacterStatusInfos'])):
                if any(s[0] in selected and s[1] == 0 for s in statuses):
                    raise LocalError('local_climbing_character_dead', 409)
            if index == 0:
                runtime.setdefault('checkpoints', {}).setdefault(str(floor), self._snapshot(fields))
                runtime['results'] = []
            elif len(runtime.get('results', [])) != 1:
                raise LocalError('local_climbing_previous_round_missing', 409)
            for party in parties:
                repository.save_party(session.player_id, party)
            # A fresh start ID replaces an unfinished attempt after a disconnect.
            # Its late result can no longer settle the replacement battle.
            store.abandon(session.player_id)
            repository.connection.execute('''INSERT INTO public.player_climbing_battles
                (player_id,unique_id,round_index,week_number,climbing_code,floor_number,start_hash,party,state)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'active')''',
                (session.player_id, unique_id, index, week, master['Code'], floor, fingerprint, encode(parties)))
            store.save(session.player_id, fields, master['Code'], week, now, runtime)
            self.players.timing.event(session.player_id, 90, now)
            return {'UpdateAccumulateInfos': self.players._state(session.player_id)['UpdateAccumulateInfos']}

    def _statuses(self, model, submitted, previous, participating, available):
        old = {s[0]: s for s in previous}
        received = {}
        for value in sequence(submitted, maximum=1000):
            row = self.protocol.fields(model, value, strict=True)
            code = integer(row['Code'], minimum=1)
            status = [code, integer(row['Hp'], maximum=1000), integer(row['Sp'], maximum=2**31 - 1)]
            if code in received or code not in available:
                raise LocalError('local_climbing_character_status_invalid')
            if code not in participating and status != old.get(code, [code, 1000, 0]):
                raise LocalError('local_climbing_nonparticipant_status_changed')
            received[code] = status
        if not participating <= received.keys():
            raise LocalError('local_climbing_character_status_missing')
        old.update(received)
        return sorted(old.values(), key=lambda s: s[0])

    def result(self, request, supplied):
        session = self.players.session(request)
        fingerprint = sha256(encode(self.protocol.model('ClimbingResultRequest', supplied))).hexdigest()
        outcome = integer(supplied['Result'], minimum=1, maximum=5)
        with self._repository().transaction(session.player_id):
            repository, store, state, fields, runtime, master, week, now = self._load(session)
            floor, index, unique_id = self._target(supplied, master, fields, battle=False)
            battle = self._battle(repository, session.player_id, unique_id, index)
            if battle is None or battle[:3] != (week, master['Code'], floor):
                raise LocalError('local_climbing_battle_not_started', 409)
            if battle[5] == 'settled':
                if battle[6] != fingerprint:
                    raise LocalError('local_climbing_result_conflict', 409)
                response = self.protocol.fields('ClimbingResultResponse', decode(bytes(battle[7])), strict=True)
                response['UpdateAccumulateInfos'] = state['UpdateAccumulateInfos']
                response['InventoryUpdateInfo'] = inventory_update(self.protocol, state,
                    [r[1] for r in response['RewardInfos']])
                return response
            self._target(supplied, master, fields)
            if battle[5] != 'active' or fields['FloorBattleIndex'] != index:
                raise LocalError('local_climbing_battle_not_active', 409)
            parties = decode(bytes(battle[4]))
            submitted = self._parties(session.player_id, supplied['PartyInfos'], state, master)
            if self._party_signature(submitted) != self._party_signature(parties):
                raise LocalError('local_climbing_party_changed_during_battle', 409)
            active = parties[index]
            codes = {m[0][0] for m in active[5] if m[0] is not None}
            rentals = {r[0] for r in active[8]}
            fields['ClimbingCharacterStatusInfos'] = self._statuses('ClimbingCharacterStatusInfo',
                supplied['ClimbingCharacterStatusInfos'], fields['ClimbingCharacterStatusInfos'],
                codes, {r[0] for r in state['Characters']})
            fields['ClimbingRentalCharacterStatusInfos'] = self._statuses('ClimbingRentalCharacterStatusInfo',
                supplied['ClimbingRentalCharacterStatusInfos'], fields['ClimbingRentalCharacterStatusInfos'],
                rentals, self._catalog.rental_codes(master))
            outcomes = runtime.setdefault('results', [])
            if len(outcomes) != index:
                raise LocalError('local_climbing_previous_round_missing', 409)
            # Native lose/retire sequences return to top without IncreaseBattleRound.
            # Keep the current round available for another party or a floor reset.
            if outcome == 1:
                outcomes.append(outcome)
                fields['FloorBattleIndex'] = index + 1
            rewards, changed = [], set()
            if index == 1 and outcomes == [1, 1]:
                fields['ClearFloor'], fields['FloorBattleIndex'] = floor, 0
                row = repository.connection.execute('''INSERT INTO public.player_climbing_rewards
                    (player_id,week_number,floor_number,received_at) VALUES (%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING RETURNING floor_number''', (session.player_id, week, floor, now)).fetchone()
                if row is not None:
                    reward_code = self._catalog.floor(master, floor)['RewardCode']
                    changed = self.players.timing._grant(session.player_id,
                        f'climbing:{week}:floor:{floor}', [reward_code], now)
                    for reward in self.players.timing.rewards[reward_code]:
                        for expanded in self.players.timing._expand_reward(reward):
                            rewards.append(self.protocol.model('RewardInfo', {
                                'Type': expanded['Type'], 'Code': expanded['ItemCode'], 'Count': expanded['Count'],
                                'DisplayPriority': reward.get('DisplayPriority', 0)}))
                self.players.timing.event(session.player_id, 91, now, values=(str(master['Code']), str(floor)))
                fields['ReceivedRewardFloor'] = max(fields['ReceivedRewardFloor'], floor)
                runtime['results'] = []
            store.save(session.player_id, fields, master['Code'], week, now, runtime)
            repository._touch(session.player_id)
            state = self.players._state(session.player_id)
            response = {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], 'RewardInfos': rewards,
                        'FloorNumber': fields['ClearFloor'], 'FloorBattleIndex': fields['FloorBattleIndex'],
                        'InventoryUpdateInfo': inventory_update(self.protocol, state, changed)}
            repository.connection.execute('''UPDATE public.player_climbing_battles
                SET state='settled',result_hash=%s,response=%s
                WHERE player_id=%s AND unique_id=%s AND round_index=%s''',
                (fingerprint, encode(self.protocol.model('ClimbingResultResponse', response)),
                 session.player_id, unique_id, index))
            return response

    def rematching(self, request, supplied):
        session = self.players.session(request)
        with self._repository().transaction(session.player_id):
            repository, store, state, fields, runtime, master, week, now = self._load(session)
            self._target(supplied, master, fields)
            if fields['FloorBattleIndex'] != 0 or repository.connection.execute(
                    "SELECT 1 FROM public.player_climbing_battles WHERE player_id=%s AND state='active'",
                    (session.player_id,)).fetchone():
                raise LocalError('local_climbing_reset_battle_before_rematching', 409)
            if fields['RematchingCount'] >= self._catalog.max_rematch:
                raise LocalError('local_climbing_rematching_limit', 409)
            floor = supplied['FloorNumber']
            matching = fields['ClimbingMatchingEnemyInfos']
            position = next(i for i, row in enumerate(matching) if row[1] == floor)
            matching[position] = self._catalog.matching(self.protocol, master, state, floor, matching[position][0])
            fields['RematchingCount'] += 1
            store.save(session.player_id, fields, master['Code'], week, now, runtime)
            repository._touch(session.player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    'ClimbingMatchingEnemyInfos': matching, 'RematchingCount': fields['RematchingCount']}

    def reset(self, request, supplied):
        session = self.players.session(request)
        with self._repository().transaction(session.player_id):
            repository, store, state, fields, runtime, master, week, now = self._load(session)
            self._target(supplied, master, fields)
            fields.update(ClearFloor=0, FloorBattleIndex=0, ClimbingCharacterStatusInfos=[],
                          ClimbingRentalCharacterStatusInfos=[])
            store.abandon(session.player_id)
            store.save(session.player_id, fields, master['Code'], week, now, {})
            repository._touch(session.player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], **{
                name: fields[name] for name in ('ClearFloor', 'FloorBattleIndex', 'ClimbingCharacterStatusInfos',
                'ClimbingRentalCharacterStatusInfos', 'RematchingCount', 'ReceivedRewardFloor')}}

    def battle_reset(self, request, supplied):
        session = self.players.session(request)
        with self._repository().transaction(session.player_id):
            repository, store, state, fields, runtime, master, week, now = self._load(session)
            self._target(supplied, master, fields, battle=False)
            floor = supplied['FloorNumber']
            if floor > fields['ClearFloor'] + 1:
                raise LocalError('local_climbing_floor_locked', 409)
            checkpoints = runtime.get('checkpoints', {})
            snapshot = checkpoints.get(str(floor))
            if snapshot is None:
                if floor == 1:
                    snapshot = [[], []]
                elif floor == fields['ClearFloor'] + 1 and fields['FloorBattleIndex'] == 0:
                    snapshot = self._snapshot(fields)
                else:
                    raise LocalError('local_climbing_floor_checkpoint_missing', 409)
            fields.update(ClearFloor=floor - 1, FloorBattleIndex=0,
                          ClimbingCharacterStatusInfos=deepcopy(snapshot[0]),
                          ClimbingRentalCharacterStatusInfos=deepcopy(snapshot[1]))
            runtime = {'checkpoints': {k: v for k, v in checkpoints.items() if int(k) <= floor}, 'results': []}
            store.abandon(session.player_id)
            store.save(session.player_id, fields, master['Code'], week, now, runtime)
            repository._touch(session.player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], **{
                name: fields[name] for name in ('ClearFloor', 'FloorBattleIndex',
                'ClimbingCharacterStatusInfos', 'ClimbingRentalCharacterStatusInfos')}}
