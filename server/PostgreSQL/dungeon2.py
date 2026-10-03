"""Player-owned Sanctuary runs. Call every operation under a player transaction."""
from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
from math import floor, isfinite
from secrets import randbelow

from psycopg.types.json import Jsonb
from mog_protocol.codec import encode
from local_server.protocol import LocalError, integer, sequence


def weighted(rows, weight='Rate'):
    total = sum(r[weight] for r in rows)
    if not rows or total <= 0 or any(type(r[weight]) is not int or r[weight] < 0 for r in rows):
        raise LocalError('local_dungeon2_lottery_configuration_invalid', 503)
    draw = randbelow(total)
    for row in rows:
        draw -= row[weight]
        if draw < 0:
            return row


class Dungeon2Store:
    def __init__(self, repository, protocol):
        self.repo, self.protocol = repository, protocol
        self.connection, self.timing = repository.connection, repository.timing
        data = self.timing.data
        if not data.get('dungeon2_master'):
            raise LocalError('local_dungeon2_configuration_missing', 503)
        self.masters = {r['Code']: r for r in data['dungeon2_master']}
        self.hierarchies = defaultdict(dict)
        for row in data['dungeon2_hierarchy_map_master']:
            self.hierarchies[row['Code']][row['Index']] = row
        self.routes = defaultdict(dict)
        for row in data['dungeon2_route_map_master']:
            self.routes[row['Code']][row['Index']] = row
        self.battles = defaultdict(list)
        for row in data['dungeon2_battle_master']:
            self.battles[row['Dungeon2SquareCode']].append(row)
        self.scripts = {r['Dungeon2SquareCode']: r for r in data['dungeon2_story_script_master']}
        self.artifacts = {r['Code'] for r in data['dungeon2_artifact_master']}
        self.groups = defaultdict(list)
        for row in data['dungeon2_artifact_group_master']:
            self.groups[row['LotteryGroup']].append(row)
        self.lineups = {r['Code']: r for r in data['dungeon2_artifact_lottery_lineup_master']}
        self.bonus = defaultdict(list)
        for row in data['dungeon2_bonus_artifact_lottery_lineup_master']:
            self.bonus[row['Dungeon2Code'], row['Code']].append(row)
        self.settings = {r['Key']: r['Value'] for r in data['dungeon2_settings']}
        self.origin = int(datetime.strptime(self.settings['DUNGEON2_START_TIME'][0],
                                           '%Y/%m/%d %H:%M:%S %z').timestamp())
        self.score_limit = int(self.settings['DUNGEON2_SCORE_LIMIT_VALUE'][0])
        self.battle_seconds = int(self.settings['DUNGEON_BATTLE_TIME_LIMIT'][0])
        definitions = dict(self.connection.execute('SELECT name,data FROM public.quest_definitions').fetchall())
        self.quests = {r['Code']: r for r in definitions['quest_master']}
        self.waves = defaultdict(list)
        for row in definitions['battle_wave_master']:
            self.waves[row['QuestCode']].append(row)

    @staticmethod
    def fresh(clears=None):
        return {'hierarchy': 0, 'square': -1, 'maps': {}, 'clears': clears or {},
                'characters': [], 'rentals': [], 'enemies': [], 'items': {}, 'battle': None}

    def require(self, player_id, now, code=None, seed_scores=()):
        row = self.connection.execute('''SELECT dungeon_code,week_number,generation,total_score,state,checked_at
            FROM public.player_dungeon2_runs WHERE player_id=%s''', (player_id,)).fetchone()
        now = max(now, row[5] if row else now)
        week = (now - self.origin) // 604800 + 1
        if week < 1:
            raise LocalError('local_dungeon2_outside_schedule', 409)
        # Match the client catalog's closest installed week when no newer
        # configuration is present, retaining a separate real week receipt key.
        available = [r for r in self.masters.values() if r['WeekNumber'] <= week]
        master = max(available, key=lambda r: r['WeekNumber']) if available else min(
            self.masters.values(), key=lambda r: r['WeekNumber'])
        if row is None:
            run = {'code': master['Code'], 'week': week, 'generation': 0, 'score': 0,
                   'state': self.fresh(), 'now': now}
            self.connection.execute('''INSERT INTO public.player_dungeon2_runs
                (player_id,dungeon_code,week_number,state,checked_at) VALUES (%s,%s,%s,%s,%s)''',
                (player_id, run['code'], week, Jsonb(run['state']), now))
            known_groups = {r['DungeonGroupCode'] for r in self.masters.values()}
            for group, score in seed_scores:
                if type(group) is int and group in known_groups and type(score) is int and 0 <= score <= self.score_limit:
                    self.connection.execute('''INSERT INTO public.player_dungeon2_records VALUES (%s,%s,%s)
                        ON CONFLICT DO NOTHING''', (player_id, group, score))
        else:
            run = dict(zip(('code', 'week', 'generation', 'score', 'state', 'now'), row))
            run['now'] = now
            if week > run['week']:
                run.update(code=master['Code'], week=week, generation=run['generation'] + 1,
                           score=0, state=self.fresh())
                self.save(player_id, run)
        if code is not None and code != run['code']:
            raise LocalError('local_dungeon2_season_mismatch', 409)
        self.save(player_id, run)
        return run

    def save(self, player_id, run):
        self.connection.execute('''UPDATE public.player_dungeon2_runs SET dungeon_code=%s,
            week_number=%s,generation=%s,total_score=%s,state=%s,checked_at=%s WHERE player_id=%s''',
            (run['code'], run['week'], run['generation'], run['score'], Jsonb(run['state']), run['now'], player_id))

    def layers(self, run):
        return self.hierarchies[self.masters[run['code']]['Dungeon2HierarchyMapCode']]

    def receipts(self, player_id, run):
        return {r[0] for r in self.connection.execute('''SELECT hierarchy_index FROM public.player_dungeon2_reward_receipts
            WHERE player_id=%s AND week_number=%s AND dungeon_code=%s''', (player_id, run['week'], run['code']))}

    def info(self, player_id, run):
        claimed = self.receipts(player_id, run)
        state = run['state']
        group = self.masters[run['code']]['DungeonGroupCode']
        highest = self.connection.execute('''SELECT highest_score FROM public.player_dungeon2_records
            WHERE player_id=%s AND dungeon_group_code=%s''', (player_id, group)).fetchone()
        return {'Dungeon2Code': run['code'], 'Dungeon2Hierarchies': [[i,
            state['hierarchy'] == i and bool(state['maps'].get(str(i))) and
                not self.layer_complete(run, i), int(i in claimed), state['clears'].get(str(i), 0)]
            for i in sorted(self.layers(run))], 'Dungeon2GroupScore': [group, highest[0] if highest else 0],
            'TotalScore': run['score']}

    def draw_artifacts(self, run, hierarchy, route):
        result = []
        for choice_type, key in ((1, 'Choice1'), (2, 'Choice2')):
            choice = route[key]
            if not choice:
                continue
            for reward_index, field in ((1, 'ArtifactLotteryGroup1'), (2, 'ArtifactLotteryGroup2')):
                if not choice[field]:
                    continue
                group = weighted(self.groups[choice[field]])
                for index, lineup in enumerate(group['ArtifactLotteryLineupCodes']):
                    definition = self.lineups.get(lineup)
                    if definition is None:
                        raise LocalError('local_dungeon2_artifact_configuration_missing', 503)
                    # Installed weekly lineups replace the corresponding base
                    # candidate; group weights and results are persisted once.
                    code = (weighted(self.bonus[run['code'], lineup])['Dungeon2ArtifactCode']
                            if self.bonus[run['code'], lineup] else definition['Dungeon2ArtifactCode'])
                    if code not in self.artifacts:
                        raise LocalError('local_dungeon2_artifact_configuration_missing', 503)
                    result.append([hierarchy, route['Index'], choice_type, reward_index, index, code])
        return result

    def enter(self, player_id, run, index):
        layer = self.layers(run).get(index)
        if layer is None:
            raise LocalError('local_dungeon2_hierarchy_not_found', 404)
        if layer['UnlockIndex'] and not run['state']['clears'].get(str(layer['UnlockIndex']), 0):
            raise LocalError('local_dungeon2_hierarchy_locked', 409)
        state = run['state']
        if state['hierarchy'] not in (0, index) and not self.layer_complete(run, state['hierarchy']):
            raise LocalError('local_dungeon2_run_requires_reset', 409)
        if str(index) not in state['maps']:
            squares = {}
            candidates = defaultdict(list)
            for route in self.routes[layer['RouteMapCode']].values():
                candidates[route['ColumnNumber'], route['Position']].append(route)
            for key in sorted(candidates):
                choices = candidates[key]
                route = choices[randbelow(len(choices))]
                script = self.scripts.get(route['Dungeon2SquareCode'])
                winning = [True, True]
                if script:
                    for n, option in enumerate(script['Options'][:2]):
                        winning[n] = randbelow(1000000) < int(option['SuccessRate']['Percent'] * 10000)
                squares[str(route['Index'])] = [route['Index'], route['Position'] or randbelow(3) + 1,
                    0, *winning, self.draw_artifacts(run, index, route)]
            state['maps'][str(index)] = squares
        if state['hierarchy'] != index:
            state.update(hierarchy=index, square=-1, enemies=[], battle=None)
        self.save(player_id, run)
        return [state['maps'][str(index)][str(i)] for i in sorted(map(int, state['maps'][str(index)]))]

    def active_routes(self, run, index):
        rows = self.routes[self.layers(run)[index]['RouteMapCode']]
        return {int(i): rows[int(i)] for i in run['state']['maps'].get(str(index), {})}

    def layer_complete(self, run, index):
        if not index or str(index) not in run['state']['maps']:
            return False
        rows = self.active_routes(run, index)
        last = max(r['ColumnNumber'] for r in rows.values())
        return any(run['state']['maps'][str(index)][str(r['Index'])][2] == 4
                   for r in rows.values() if r['ColumnNumber'] == last)

    def square(self, player_id, run, hierarchy, index, *, select=True):
        self.enter(player_id, run, hierarchy)
        rows = self.active_routes(run, hierarchy)
        route = rows.get(index)
        if route is None:
            raise LocalError('local_dungeon2_square_not_found', 404)
        squares = run['state']['maps'][str(hierarchy)]
        square = squares[str(index)]
        if square[2] == 4 or not select:
            return route, square
        column = route['ColumnNumber']
        if any(squares[str(r['Index'])][2] == 4 for r in rows.values()
               if r['ColumnNumber'] == column and r['Index'] != index):
            raise LocalError('local_dungeon2_branch_already_completed', 409)
        previous_columns = [r['ColumnNumber'] for r in rows.values() if r['ColumnNumber'] < column]
        if previous_columns and not any(squares[str(r['Index'])][2] == 4 for r in rows.values()
                                       if r['ColumnNumber'] == max(previous_columns)):
            raise LocalError('local_dungeon2_square_locked', 409)
        if run['state']['square'] != index:
            old = squares.get(str(run['state']['square']))
            if old and old[2] in (2, 3):
                raise LocalError('local_dungeon2_battle_unfinished', 409)
            if old and old[2] == 1:
                old[2] = 0
            run['state'].update(square=index, enemies=[], battle=None)
        if square[2] == 0:
            square[2] = 1
        self.save(player_id, run)
        return route, square

    def quest(self, player_id, route):
        level = self.connection.execute('SELECT level FROM public.players WHERE player_id=%s', (player_id,)).fetchone()[0]
        candidates = [r for r in self.battles[route['Dungeon2SquareCode']]
                      if (not r['PlayerLevelMin'] or r['PlayerLevelMin'] <= level) and
                         (not r['PlayerLevelMax'] or level <= r['PlayerLevelMax'])]
        if len(candidates) != 1 or candidates[0]['QuestCode'] not in self.quests:
            raise LocalError('local_dungeon2_battle_configuration_missing', 503)
        return candidates[0]['QuestCode']

    def vectors(self, player_id, run, characters, enemies, rentals, quest_code=None):
        owned = {r[0] for r in self.repo.protocol_state(player_id)['Characters']}
        master = self.masters[run['code']]
        blocked = {r['CharacterCode'] for r in self.timing.data['dungeon2_remove_character_group_master']
                   if r['Code'] == master['Dungeon2RemoveCharacterGroupCode']}
        def actors(values, model, key, allowed):
            seen, result = set(), []
            for value in sequence([] if values is None else values, maximum=1000):
                row = self.protocol.fields(model, value, strict=True)
                code = integer(row[key], minimum=1)
                if code not in allowed or code in seen:
                    raise LocalError('local_dungeon2_character_not_available', 403)
                seen.add(code)
                result.append([code, integer(row['Hp'], maximum=1000), integer(row['Sp'], maximum=1000)])
            return result
        characters = actors(characters, 'Dungeon2CharacterInfo', 'CharacterCode', owned - blocked)
        rentals = actors(rentals, 'Dungeon2RentalCharacterInfo', 'RentalCharacterCode', set(master['RentalCharacterCodes']))
        allowed, known_codes, seen, enemy_rows = set(), set(), set(), []
        if quest_code:
            for wave in self.waves[quest_code]:
                for index in range(1, 6):
                    code = wave['Enemy' + str(index) + 'Code']
                    if code:
                        known_codes.add(code)
                        allowed.update((wave['WaveIndex'], n, quest_code, code) for n in (index - 1, index))
        for value in sequence([] if enemies is None else enemies, maximum=100):
            row = self.protocol.fields('Dungeon2EnemyInfo', value, strict=True)
            packed = [integer(row['Wave']), integer(row['Index'], maximum=2**31 - 1),
                      integer(row['QuestCode'], minimum=1), integer(row['EnemyCode'], minimum=1),
                      integer(row['Hp'])]
            # Native CreateDungeonEnemyInfo uses Wave=0 and the battle object
            # identifier as Index. Enemy HP is absolute, unlike actor HP/SP.
            valid = (packed[2] == quest_code and packed[3] in known_codes
                     if packed[0] == 0 else tuple(packed[:4]) in allowed)
            if not valid or tuple(packed[:2]) in seen:
                raise LocalError('local_dungeon2_enemy_mismatch', 400)
            seen.add(tuple(packed[:2]))
            enemy_rows.append(packed)
        return characters, enemy_rows, rentals

    def battle_status(self, player_id, run, fields):
        state = run['state']
        quest_code, square = None, None
        if state['hierarchy'] and state['square'] >= 0:
            route, square = self.square(player_id, run, state['hierarchy'], state['square'], select=False)
            if route['Dungeon2SquareCode'] // 100000000 in (2, 3, 4):
                quest_code = self.quest(player_id, route)
        characters, enemies, rentals = self.vectors(player_id, run, fields['Dungeon2Characters'],
            fields['Dungeon2Enemies'], fields['Dungeon2RentalCharacters'], quest_code)
        # Preserve actors used in earlier encounters, not just this party.
        for name, rows in (('characters', characters), ('rentals', rentals)):
            previous = {r[0]: r for r in state[name]}
            previous.update({r[0]: r for r in rows})
            state[name] = list(previous.values())
        state['enemies'] = enemies
        if quest_code and square[2] in (1, 2):
            if not characters and not rentals:
                raise LocalError('local_dungeon2_battle_party_empty', 400)
            if square[2] == 1:
                state['battle'] = {'quest': quest_code, 'characters': [r[0] for r in characters],
                    'rentals': [r[0] for r in rentals], 'digest': None, 'response': None}
            square[2] = 2
        self.save(player_id, run)
        return {'Dungeon2CharactersResult': len(characters), 'Dungeon2EnemiesResult': len(enemies),
                'Dungeon2RentalCharactersResult': len(rentals)}

    def battle_result(self, player_id, run, fields):
        info = self.protocol.fields('Dungeon2BattleResultInfo', fields['Dungeon2'], strict=True)
        hierarchy = integer(info['HierarchyIndex'], minimum=1)
        index = integer(info['SquareIndex'])
        if info['Dungeon2Code'] != run['code'] or (hierarchy, index) != (run['state']['hierarchy'], run['state']['square']):
            raise LocalError('local_dungeon2_battle_context_mismatch', 409)
        route, square = self.square(player_id, run, hierarchy, index, select=False)
        battle = run['state']['battle']
        if not battle or fields['QuestCode'] != battle['quest'] or self.quest(player_id, route) != fields['QuestCode']:
            raise LocalError('local_dungeon2_battle_not_started', 409)
        digest = sha256(encode(fields)).hexdigest()
        if battle['digest']:
            if battle['digest'] != digest:
                raise LocalError('local_dungeon2_result_conflict', 409)
            return {'retry': True, 'response': battle['response']}
        characters, enemies, rentals = self.vectors(player_id, run, info['Dungeon2Characters'],
            info['Dungeon2Enemies'], info['Dungeon2RentalCharacters'], fields['QuestCode'])
        # SaveBattleStatusAsync sends every previously used actor; the battle
        # result describes just the active party. Keep inactive actors intact.
        if any(r[0] not in battle['characters'] for r in characters) or any(
                r[0] not in battle['rentals'] for r in rentals):
            raise LocalError('local_dungeon2_result_party_mismatch', 400)
        hp, seconds = info['RemainingHealth'], info['RemainingSeconds']
        if any(type(value) not in (int, float) or not isfinite(value) for value in (hp, seconds)) or not (
                0 <= hp <= 1 and 0 <= seconds <= self.battle_seconds):
            raise LocalError('local_dungeon2_result_score_invalid', 400)
        if fields['Result'] not in (1, 2, 3):
            raise LocalError('local_dungeon2_result_type_invalid', 400)
        expected = Counter(w['Enemy' + str(i) + 'Code'] for w in self.waves[fields['QuestCode']]
                           for i in range(1, 6) if w['Enemy' + str(i) + 'Code'])
        if fields['Result'] == 1 and (Counter(r[3] for r in enemies) != expected or
                any(r[4] for r in enemies) or not any(r[1] for r in characters + rentals)):
            raise LocalError('local_dungeon2_result_not_won', 400)
        state = run['state']
        for name, rows in (('characters', characters), ('rentals', rentals)):
            previous = {r[0]: r for r in state[name]}
            previous.update({r[0]: r for r in rows})
            state[name] = list(previous.values())
        state['enemies'] = enemies
        layer = self.layers(run)[hierarchy]
        score = 0
        if fields['Result'] != 3:
            score = (layer['ScoreByWin'] if fields['Result'] == 1 else layer['ScoreByLose']) + floor(layer['ScoreByRemainHp'] * hp)
            if fields['Result'] == 1:
                score += floor(layer['ScoreByRemainSeconds'] * seconds / self.battle_seconds)
        run['score'] = max(0, min(self.score_limit, run['score'] + score))
        square[2] = 3 if fields['Result'] == 1 else 1
        battle['digest'] = digest
        group = self.masters[run['code']]['DungeonGroupCode']
        self.connection.execute('''INSERT INTO public.player_dungeon2_records VALUES (%s,%s,%s)
            ON CONFLICT(player_id,dungeon_group_code) DO UPDATE SET
            highest_score=GREATEST(player_dungeon2_records.highest_score,EXCLUDED.highest_score)''',
            (player_id, group, run['score']))
        self.save(player_id, run)
        return {'retry': False}

    def complete(self, player_id, run, fields):
        hierarchy, index = fields['HierarchyIndex'], fields['SquareIndex']
        route, square = self.square(player_id, run, hierarchy, index)
        digest = sha256(encode(fields)).hexdigest()
        receipts = run['state'].setdefault('completions', {})
        key = str(hierarchy) + ':' + str(index)
        if square[2] == 4:
            if receipts.get(key) != digest:
                raise LocalError('local_dungeon2_complete_conflict', 409)
            return set()
        kind = route['Dungeon2SquareCode'] // 100000000
        if kind in (2, 3, 4) and square[2] != 3:
            raise LocalError('local_dungeon2_battle_not_finished', 409)
        choice, reward, selection = fields['ChoiceType'], fields['RewardIndex'], fields['ArtifactSelectIndex']
        if kind == 1:
            if (choice, reward, selection) != (0, 0, -1):
                raise LocalError('local_dungeon2_selection_invalid', 400)
        elif kind == 6:
            script = self.scripts.get(route['Dungeon2SquareCode'])
            if not script or choice not in (1, 2) or choice > len(script['Options']) or reward != (1 if square[2 + choice] else 2):
                raise LocalError('local_dungeon2_event_selection_invalid', 400)
        elif choice != 1 or reward != 1:
            raise LocalError('local_dungeon2_selection_invalid', 400)
        candidates = [r for r in square[5] if (r[2], r[3]) == (choice, reward)]
        if candidates and selection != -1:
            selected = next((r for r in candidates if r[4] == selection), None)
            if selected is None:
                raise LocalError('local_dungeon2_artifact_selection_invalid', 400)
            code = str(selected[5])
            run['state']['items'][code] = run['state']['items'].get(code, 0) + 1
        elif selection != -1:
            raise LocalError('local_dungeon2_artifact_selection_invalid', 400)
        square[2] = 4
        receipts[key] = digest
        changed = set()
        if self.layer_complete(run, hierarchy):
            run['state']['clears'][str(hierarchy)] = run['state']['clears'].get(str(hierarchy), 0) + 1
            first = self.connection.execute('''INSERT INTO public.player_dungeon2_reward_receipts VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING RETURNING hierarchy_index''',
                (player_id, run['week'], run['code'], hierarchy, run['now'])).fetchone()
            if first:
                reward_code = self.layers(run)[hierarchy]['FirstRewardCode']
                if reward_code:
                    changed = self.timing._grant(player_id, f'dungeon2-first:{run["week"]}:{run["code"]}:{hierarchy}',
                                                [reward_code], run['now'])
            self.timing.event(player_id, 81, run['now'], values=(str(self.masters[run['code']]['DungeonGroupCode']),))
            if hierarchy == max(self.layers(run)):
                self.timing.event(player_id, 82, run['now'])
        self.save(player_id, run)
        return changed

    def reset(self, player_id, run):
        run.update(generation=run['generation'] + 1, score=0, state=self.fresh(run['state']['clears']))
        self.save(player_id, run)
