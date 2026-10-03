"""Player-owned timed state. All settlement runs under the existing player lock."""
from collections import defaultdict

from psycopg.types.json import Jsonb

from .game_time import GameTime, recover_stamina, unix, timestamp, inside_daily_window
from .player_protocol import record


class TimeBusinessError(ValueError):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


MISSION_CATEGORIES = ('Permanent', 'Event', 'SubEvent', 'Beginner', 'Comeback', 'Collaboration',
                      'GuildBattle', 'Campaign', 'Garden', 'Duel', 'StoryRaid', 'BattlePass',
                      'SubCampaign', 'InviteHost', 'InviteGuest', 'BeginnerCharacter', 'BingoReward')
MISSION_SUBCATEGORIES = ('Daily', 'Weekly', 'Normal', 'Honor', 'Special', 'Score', 'Apocrypha',
                         'Season', 'InviteBeginner', 'InviteComeBack', 'Bingo')


class TimedState:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection
        self.registry = repository.registry
        self.data = dict(self.connection.execute('SELECT name,data FROM public.game_time_definitions').fetchall())
        self.clock = GameTime(self.data['game_setting_master'])
        self.index = {name: {row['Code']: row for row in rows if 'Code' in row}
                      for name, rows in self.data.items()}
        self.level_caps = {r['Level']: r['MaxStamina'] for r in self.data['player_exp_master']}
        self.quiz_store = None
        self.garden_store = None
        self.quest_groups = defaultdict(list)
        for row in self.data.get('quest_master', []):
            self.quest_groups[row['QuestGroupCode']].append(row['Code'])
        self.rewards = defaultdict(list)
        for row in self.data['reward_master']:
            self.rewards[row['Code']].append(row)
        self.bonus_rewards = defaultdict(dict)
        for row in self.data['login_bonus_reward_master']:
            self.bonus_rewards[row['LoginBonusCode']][row['Index']] = row['RewardCodes']
        self.pack_rewards = defaultdict(list)
        for row in self.data.get('pack_item_content_master', []):
            self.pack_rewards[row['PackItemCode']].append(row)
        from .stamina import StaminaStore
        required = ('stamina_recovery_items', 'stamina_recovery_settings',
                    'stamina_recovery_daily_feed_limit_unlock_master', 'stamina_recovery_campaigns')
        self.stamina_recovery = StaminaStore(repository, self) if all(
            name in self.data for name in required) else None
        from .quest_challenges import QuestChallenges
        self.quest_challenges = QuestChallenges(repository, self.clock) if self.connection.execute(
            "SELECT to_regclass('public.quest_definitions')").fetchone()[0] else None

    def active(self, code, now):
        if not code:
            return True
        schedule = self.index['schedule_master'].get(code)
        # Identity-relative invitation schedules need separate entitlement logic.
        return bool(schedule and schedule['Type'] == 0 and
                    unix(schedule['StartAt']) <= now < unix(schedule['EndAt']))

    def garden(self):
        if 'garden_building_master' not in self.data:
            return None
        if self.garden_store is None:
            from .garden import GardenStore
            self.garden_store = GardenStore(self.repo)
        return self.garden_store

    def _period(self, code, now):
        definition = self.index['accumulate_master'].get(code, {})
        return self.clock.period(definition.get('ResetType', 0), now)

    def _group_unlocked(self, group, now):
        kind = group['UnlockType']
        if kind == 0:
            return True
        table = {1: 'event_master', 3: 'guild_battle_master', 4: 'duel_master',
                 5: 'story_raid_master', 6: 'battle_pass_master', 7: 'sub_event_master'}.get(kind)
        if table is None:
            raise TimeBusinessError('local_mission_group_unlock_not_implemented', 501)
        definition = self.index.get(table, {}).get(group['UnlockValue'])
        if definition is None:
            raise TimeBusinessError('local_mission_group_configuration_missing', 503)
        if kind in (1, 7):
            return any(self.active(definition[key], now) for key in
                       ('ScheduleCodeBefore', 'ScheduleCodeInSession', 'ScheduleCodeEnd')
                       if definition[key])
        return self.active(definition['ScheduleCode'], now)

    def _mission_period(self, mission, now):
        group = self.index['mission_group_master'][mission['GroupCode']]
        if group['SubCategory'] == 0:
            return self.clock.day(now)
        if group['SubCategory'] == 1:
            return self.clock.week(now, battle_pass=group['Category'] == 11)
        return 0

    def initialize(self, player_id, login, home, now):
        inserted = self.connection.execute('''INSERT INTO public.player_time_state(player_id)
            VALUES (%s) ON CONFLICT DO NOTHING RETURNING player_id''', (player_id,)).fetchone()
        if inserted:
            fields = record(self.registry, 'UserLoginResponse', login)
            user = record(self.registry, 'UserInfo', fields['User'])
            # A seed captured today already includes today's login counters.
            if self.clock.day(user['LastLoggedInAt']) == self.clock.day(now):
                self.connection.execute('UPDATE public.player_time_state SET last_login_day=%s WHERE player_id=%s',
                                        (self.clock.day(now), player_id))
            for value in fields['AccumulateInfos'] or []:
                row = record(self.registry, 'AccumulateInfo', value)
                self.connection.execute('''INSERT INTO public.player_accumulates
                    (player_id,code,count,count_up_at,period) VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING''', (player_id, row['Code'], row['Count'],
                    row['CountUpAt'], self._period(row['Code'], row['CountUpAt'])))
            for value in fields['MissionRewardReceivedInfos'] or []:
                # Older local captures omitted Key(1); retain compatibility when
                # initializing them, while preserving the actual timestamp in full seeds.
                receipt = record(self.registry, 'MissionRewardReceivedInfo',
                                 value + [user['LastLoggedInAt']] if len(value) == 1 else value)
                code, received_at = receipt['MissionCode'], receipt['RewardReceivedAt']
                mission = self.index['mission_master'].get(code)
                period = self._mission_period(mission, received_at) if mission else 0
                self.connection.execute('''INSERT INTO public.mission_receipts
                    VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                    (player_id, code, period, received_at))
        garden = self.garden()
        if garden is not None:
            garden.initialize(player_id, now, record(self.registry, 'GetGameTopInfoResponse', home)
                              if home is not None else None)
        if home is not None:
            home_fields = record(self.registry, 'GetGameTopInfoResponse', home)
            if 'adventure_flag_master' in self.data:
                from .story import StoryStore
                StoryStore(self.repo).seed_flags(player_id, home_fields['AdventureFlags'], now)
            for value in home_fields['BattlePasses'] or []:
                row = record(self.registry, 'BattlePassInfo', value)
                self.connection.execute('''INSERT INTO public.player_battle_passes
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                    (player_id, row['BattlePassCode'], row['TotalPoint'], row['NormalRewardReceivedLevel'],
                     row['SpecialRewardReceivedLevel'], row['WeeklyPoint'],
                     unix(row['WeeklyPointReceivedAt']), row['IsPurchased']))

    def refresh(self, player_id, now, *, login=False):
        with self.repo.transaction(player_id):
            state = self.connection.execute('SELECT checked_at,last_login_day FROM public.player_time_state WHERE player_id=%s',
                                            (player_id,)).fetchone()
            if state is None:
                return
            now = max(int(now), state[0])  # A backward clock never reopens a settled period.
            if self.quest_challenges is not None:
                self.quest_challenges.refresh(player_id, now)
            level = self.repo.synchronize_player_level(player_id)
            if self.garden() is not None:
                self.garden().refresh_closeness(player_id)
            self.refresh_quiz_stamina(player_id, now)
            if 'quiz_master' in self.data:
                if self.quiz_store is None:
                    from .quiz import QuizStore
                    self.quiz_store = QuizStore(self.repo)
                self.quiz_store.refresh_available(player_id, now)
            if self.stamina_recovery is not None:
                self.stamina_recovery.refresh(player_id, now)
            stamina = self.connection.execute('SELECT kind,value,updated_at FROM public.player_stamina WHERE player_id=%s',
                                              (player_id,)).fetchall()
            for kind, value, updated_at in stamina:
                if kind == 'normal':
                    if level not in self.level_caps:
                        raise TimeBusinessError('local_stamina_level_configuration_missing', 503)
                    new_value, new_time = recover_stamina(value, updated_at, now,
                        self.level_caps[level], self.clock.stamina_interval)
                else:
                    continue
                if (value, updated_at) != (new_value, new_time):
                    self.connection.execute('''UPDATE public.player_stamina SET value=%s,updated_at=%s
                        WHERE player_id=%s AND kind=%s''', (new_value, new_time, player_id, kind))
            if self.stamina_recovery is not None:
                self.stamina_recovery.mirror(player_id)
            for code, period in self.connection.execute('SELECT code,period FROM public.player_accumulates WHERE player_id=%s',
                                                       (player_id,)).fetchall():
                current = self._period(code, now)
                if current > period:
                    self.connection.execute('''UPDATE public.player_accumulates SET count=0,period=%s,count_up_at=%s
                        WHERE player_id=%s AND code=%s''', (current, now, player_id, code))
            self.reconcile_mission_counts(player_id, now)
            for code, received_at in self.connection.execute('SELECT code,weekly_received_at FROM public.player_battle_passes WHERE player_id=%s',
                                                             (player_id,)).fetchall():
                if self.clock.week(now, battle_pass=True) > self.clock.week(received_at, battle_pass=True):
                    self.connection.execute('''UPDATE public.player_battle_passes SET weekly_point=0,weekly_received_at=%s
                        WHERE player_id=%s AND code=%s''', (now, player_id, code))
            for definition in self.data['battle_pass_master']:
                if self.active(definition['ScheduleCode'], now):
                    self.connection.execute('''INSERT INTO public.player_battle_passes
                        (player_id,code,weekly_received_at) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING''',
                        (player_id, definition['Code'], now))
            if state[1] is None or self.clock.day(now) > state[1]:
                self.event(player_id, 0, now)
                self.event(player_id, 2, now)
                self.connection.execute('UPDATE public.player_time_state SET last_login_day=%s WHERE player_id=%s',
                                        (self.clock.day(now), player_id))
            self.event(player_id, 1, now)
            self.connection.execute('UPDATE public.player_time_state SET checked_at=%s WHERE player_id=%s', (now, player_id))

    def refresh_quiz_stamina(self, player_id, now):
        settings = self.data.get('quiz_settings')
        if settings is None:
            return
        values = {row['Key']: int(row['Value'][0]) for row in settings}
        cap, recovery = values['MAX_CLOSENESS_POINT'], values['RECOVERY_CLOSENESS_POINT']
        # QuizModel reads the StackItemInfo of behaviour type 20. Older login seeds
        # can omit UserInfo.QuizStamina while retaining this authoritative balance.
        item_code = 390000003
        row = self.connection.execute('''SELECT quantity,recovered_at FROM public.items
            WHERE player_id=%s AND item_code=%s''', (player_id, item_code)).fetchone()
        if row is None:
            row = self.connection.execute('''SELECT value,updated_at FROM public.player_stamina
                WHERE player_id=%s AND kind='quiz' ''', (player_id,)).fetchone()
        value, updated_at = row if row else (cap, now)
        days = max(0, self.clock.day(now) - self.clock.day(updated_at))
        # QuizSharedLogic.CalculateCurrentQuizStamina: add the elapsed daily
        # recovery, cap natural recovery, and preserve purchased over-cap points.
        if value < cap and days:
            value, updated_at = min(cap, value + min(cap, days * recovery)), now
        self.connection.execute('''INSERT INTO public.items (player_id,item_code,quantity,recovered_at)
            VALUES (%s,%s,%s,%s) ON CONFLICT(player_id,item_code) DO UPDATE
            SET quantity=EXCLUDED.quantity,recovered_at=EXCLUDED.recovered_at
            WHERE (items.quantity,items.recovered_at) IS DISTINCT FROM
                  (EXCLUDED.quantity,EXCLUDED.recovered_at)''', (player_id, item_code, value, updated_at))
        self.connection.execute('''INSERT INTO public.player_stamina (player_id,kind,value,updated_at)
            VALUES (%s,'quiz',%s,%s) ON CONFLICT(player_id,kind) DO UPDATE
            SET value=EXCLUDED.value,updated_at=EXCLUDED.updated_at
            WHERE (player_stamina.value,player_stamina.updated_at) IS DISTINCT FROM
                  (EXCLUDED.value,EXCLUDED.updated_at)''', (player_id, value, updated_at))

    def _effective_now(self, player_id, now):
        row = self.connection.execute('SELECT checked_at FROM public.player_time_state WHERE player_id=%s', (player_id,)).fetchone()
        return max(int(now), row[0]) if row else int(now)

    def _counts(self, player_id):
        return dict(self.connection.execute('SELECT code,count FROM public.player_accumulates WHERE player_id=%s',
                                            (player_id,)).fetchall())

    def reference(self, player_id, ref, counts=None, *, total_power=None):
        if ref is None or ref['Type'] == 0:
            return 0
        args = ref['Params']
        if ref['Type'] == 1:
            counts = self._counts(player_id) if counts is None else counts
            return counts.get(args[0], 0)
        if ref['Type'] == 2:
            return self.connection.execute('SELECT level FROM public.players WHERE player_id=%s', (player_id,)).fetchone()[0]
        if ref['Type'] == 26:
            return self.connection.execute('SELECT first_logged_in_at FROM public.players WHERE player_id=%s',
                                           (player_id,)).fetchone()[0]
        if ref['Type'] == 27:
            row = self.connection.execute('''SELECT clear_count FROM public.player_tower_floors
                WHERE player_id=%s AND tower_code=%s AND floor=%s''', (player_id, args[0], args[1])).fetchone()
            return row[0] if row else 0
        if ref['Type'] in (3, 4):
            if ref['Type'] == 4 and args[0] == 0:
                return self.connection.execute('SELECT COALESCE(sum(star_count),0) FROM public.quests WHERE player_id=%s',
                                               (player_id,)).fetchone()[0]
            row = self.connection.execute('SELECT clear_count,star_count FROM public.quests WHERE player_id=%s AND quest_code=%s',
                                          (player_id, args[0])).fetchone()
            return (row[0] if ref['Type'] == 3 else row[1]) if row else 0
        if ref['Type'] == 5:
            row = self.connection.execute('SELECT clear_count FROM public.quest_groups WHERE player_id=%s AND quest_group_code=%s',
                                          (player_id, args[0])).fetchone()
            return row[0] if row else 0
        if ref['Type'] == 6:
            quests = self.quest_groups.get(args[0])
            if quests is None:
                raise TimeBusinessError('local_mission_quest_group_configuration_missing', 503)
            return self.connection.execute('''SELECT COALESCE(sum(star_count),0) FROM public.quests
                WHERE player_id=%s AND quest_code=ANY(%s)''', (player_id, quests)).fetchone()[0]
        if ref['Type'] == 9:
            return self.connection.execute('SELECT count(*) FROM public.characters WHERE player_id=%s',
                                           (player_id,)).fetchone()[0]
        if ref['Type'] == 10:
            # UserDataReference.CharacterCountWithLevel counts owned characters
            # at or above Params[0], rather than accumulated level-up actions.
            return self.connection.execute('''SELECT count(*) FROM public.characters
                WHERE player_id=%s AND level >= %s''', (player_id, args[0])).fetchone()[0]
        if ref['Type'] == 12:
            # CharacterCountWithRarity: the client predicate at RVA 0x13711C0
            # compares CharacterInfo.Rarity >= the requested threshold.
            return self.connection.execute('''SELECT count(*) FROM public.characters
                WHERE player_id=%s AND rarity >= %s''', (player_id, args[0])).fetchone()[0]
        if ref['Type'] == 14:
            return self.connection.execute('''SELECT count(*) FROM public.players,
                jsonb_array_elements(home_characters) AS home_character
                WHERE player_id=%s AND (home_character->>1)::integer >= %s''',
                                           (player_id, args[0])).fetchone()[0]
        if ref['Type'] in (11, 13):
            column = {11: 'rank', 13: 'limit_break'}[ref['Type']]
            # Both conditions count owned characters at or above the threshold.
            return self.connection.execute(f'''SELECT count(*) FROM public.characters
                WHERE player_id=%s AND {column}>=%s''', (player_id, args[0])).fetchone()[0]
        if ref['Type'] in (15, 16, 17, 18):
            # Specific-character references return the actual saved value,
            # rather than treating ownership as completion of every threshold.
            column = {15: 'rarity', 16: 'rank', 17: 'level', 18: 'limit_break'}[ref['Type']]
            row = self.connection.execute(f'''SELECT {column} FROM public.characters
                WHERE player_id=%s AND character_code=%s''', (player_id, args[0])).fetchone()
            return row[0] if row else 0
        if ref['Type'] == 19:
            row = self.connection.execute('SELECT home_characters FROM public.players WHERE player_id=%s',
                                          (player_id,)).fetchone()
            for value in row[0] or []:
                character = record(self.registry, 'HomeCharacterInfo', value)
                if character['HomeCharacterCode'] == args[0]:
                    return character['ClosenessLevel']
            return 0
        if ref['Type'] in (20, 21, 22) and 'garden_character_group_master' in self.data:
            groups = args[1:] if ref['Type'] == 22 else args
            codes = sorted({r['CharacterCode'] for r in self.data['garden_character_group_master']
                            if r['CharacterGroupSettingCode'] in groups and r['CharacterType'] == 0})
            if ref['Type'] == 22:
                return self.connection.execute('''SELECT count(*) FROM public.characters
                    WHERE player_id=%s AND character_code=ANY(%s) AND rarity=%s''',
                    (player_id, codes, args[0])).fetchone()[0]
            column = 'level' if ref['Type'] == 20 else 'limit_break'
            return self.connection.execute(f'''SELECT COALESCE(sum({column}),0) FROM public.characters
                WHERE player_id=%s AND character_code=ANY(%s)''', (player_id, codes)).fetchone()[0]
        if ref['Type'] == 23:
            return self.connection.execute('SELECT count(*) FROM public.shop_owned_honors WHERE player_id=%s',
                                           (player_id,)).fetchone()[0]
        if ref['Type'] == 24:
            # UserDataReference.ReadStory and StoryStatus.Read=2 in the client dump.
            row = self.connection.execute('SELECT status FROM public.stories WHERE player_id=%s AND story_code=%s',
                                          (player_id, args[0])).fetchone()
            return int(row is not None and row[0] == 2)
        if ref['Type'] == 25:
            return self.connection.execute('SELECT count(*) FROM public.magic_items WHERE player_id=%s',
                                           (player_id,)).fetchone()[0]
        if ref['Type'] in (28, 29, 30) and self.garden() is not None:
            if ref['Type'] == 28:
                row = self.connection.execute('SELECT holding_worker_count FROM public.player_gardens WHERE player_id=%s',
                                              (player_id,)).fetchone()
            elif ref['Type'] == 29:
                row = self.connection.execute('''SELECT level FROM public.player_garden_buildings
                    WHERE player_id=%s AND building_code=%s''', (player_id, args[0])).fetchone()
            else:
                row = self.connection.execute('SELECT count(*) FROM public.player_room_situations WHERE player_id=%s AND room_code=%s',
                                              (player_id, args[0])).fetchone()
            return row[0] if row else 0
        if ref['Type'] == 33:
            return self.connection.execute('SELECT last_logged_in_at FROM public.players WHERE player_id=%s',
                                           (player_id,)).fetchone()[0]
        if ref['Type'] == 44:
            row = self.connection.execute('SELECT quantity FROM public.items WHERE player_id=%s AND item_code=%s',
                                          (player_id, args[0])).fetchone()
            return row[0] if row else 0
        if ref['Type'] == 42:
            if total_power is None:
                raise TimeBusinessError('local_mission_battle_power_unavailable', 503)
            # Use the same trusted server value displayed in the local home response.
            return total_power
        raise TimeBusinessError('local_mission_reference_not_implemented', 501)

    def reconcile_mission_counts(self, player_id, now):
        """Repair missing receive counters from receipts, never invent completions."""
        definitions = defaultdict(list)
        for row in self.data['accumulate_master']:
            if row['Type'] in (36, 37) and not row['CountUpCondition']:
                definitions[(row['Type'], tuple(row['Values']))].append(row)
        totals = defaultdict(int)
        timestamps = {}
        for code, received_at in self.connection.execute('''SELECT mission_code,received_at
            FROM public.mission_receipts WHERE player_id=%s''', (player_id,)).fetchall():
            mission = self.index['mission_master'].get(code)
            if mission is None:
                continue
            group = self.index['mission_group_master'].get(mission['GroupCode'])
            if group is None:
                continue
            values = [(37, (str(group['Code']),)),
                      (36, (MISSION_CATEGORIES[group['Category']],
                            MISSION_SUBCATEGORIES[group['SubCategory']]))]
            for key in values:
                for definition in definitions.get(key, ()):
                    code = definition['Code']
                    if (self._period(code, received_at) != self._period(code, now)
                            or not self.active(definition['ScheduleCode'], received_at)):
                        continue
                    totals[code] += 1
                    timestamps[code] = max(timestamps.get(code, 0), received_at)
        for code, count in totals.items():
            self.connection.execute('''INSERT INTO public.player_accumulates
                (player_id,code,count,count_up_at,period) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(player_id,code) DO UPDATE SET
                count=GREATEST(player_accumulates.count,EXCLUDED.count),
                count_up_at=GREATEST(player_accumulates.count_up_at,EXCLUDED.count_up_at)
                WHERE player_accumulates.count<EXCLUDED.count''',
                (player_id, code, count, timestamps[code], self._period(code, now)))

    def eligible(self, player_id, code, counts=None):
        if not code:
            return True
        category = self.index['user_category_master'].get(code)
        if category is None:
            raise TimeBusinessError('local_mission_user_category_configuration_missing', 503)
        count = self.reference(player_id, category['UserDataReference'], counts)
        return count >= category['TargetCount'] and (not category['TargetCountTo'] or count <= category['TargetCountTo'])

    def event(self, player_id, kind, now, *, values=(), amount=1):
        counts = self._counts(player_id)
        for definition in self.data['accumulate_master']:
            if definition['Type'] != kind:
                continue
            if kind == 1:
                if not inside_daily_window(now, definition['Values']) or counts.get(definition['Code'], 0):
                    continue
            elif tuple(definition['Values']) != tuple(values):
                continue
            if not self.active(definition['ScheduleCode'], now):
                continue
            condition = definition['CountUpCondition']
            if condition:
                count = counts.get(condition['AccumulateCode'], 0)
                if count < condition['TargetCount'] or (condition['TargetCountTo'] and count > condition['TargetCountTo']):
                    continue
            period = self._period(definition['Code'], now)
            self.connection.execute('''INSERT INTO public.player_accumulates
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT(player_id,code) DO UPDATE SET
                count=CASE WHEN player_accumulates.period=EXCLUDED.period
                    THEN player_accumulates.count+EXCLUDED.count ELSE EXCLUDED.count END,
                count_up_at=EXCLUDED.count_up_at,period=EXCLUDED.period''',
                (player_id, definition['Code'], amount, now, period))

    def view(self, player_id, now):
        now = self._effective_now(player_id, now)
        accumulates = [[code, count, at] for code, count, at in self.connection.execute('''SELECT code,count,count_up_at
            FROM public.player_accumulates WHERE player_id=%s ORDER BY code''', (player_id,)).fetchall()]
        receipts = []
        for code, period, received_at in self.connection.execute('''SELECT mission_code,period,received_at
            FROM public.mission_receipts WHERE player_id=%s''', (player_id,)).fetchall():
            mission = self.index['mission_master'].get(code)
            if mission is None or period == self._mission_period(mission, now):
                receipts.append([code, received_at])
        passes = []
        for code, total, normal, special, weekly, at, purchased in self.connection.execute('''SELECT code,total_point,
            normal_received_level,special_received_level,weekly_point,weekly_received_at,is_purchased
            FROM public.player_battle_passes WHERE player_id=%s ORDER BY code''', (player_id,)).fetchall():
            definition = self.index['battle_pass_master'].get(code)
            if definition and self.active(definition['ScheduleCode'], now):
                passes.append([code, total, normal, special, weekly, timestamp(at), purchased])
        shops = [[code, end, notified] for code, end, notified in self.connection.execute('''SELECT code,end_at,notified_at
            FROM public.player_shop_passes WHERE player_id=%s AND activated_at<=%s AND end_at>%s ORDER BY code''',
            (player_id, now, now)).fetchall()]
        honors = [[code] for code, in self.connection.execute('''SELECT honor_code
            FROM public.shop_owned_honors WHERE player_id=%s ORDER BY honor_code''', (player_id,)).fetchall()]
        flags = None
        if 'adventure_flag_master' in self.data:
            flags = [[code, value] for code, value in self.connection.execute('''SELECT flag_code,flag_value
                FROM public.player_adventure_flags WHERE player_id=%s ORDER BY flag_code''', (player_id,)).fetchall()]
        dungeon_scores = {}
        if 'dungeon2_master' in self.data and self.connection.execute(
                'SELECT 1 FROM public.player_dungeon2_runs WHERE player_id=%s', (player_id,)).fetchone():
            dungeon_scores['Dungeon2GroupScores'] = [list(row) for row in self.connection.execute('''SELECT
                dungeon_group_code,highest_score FROM public.player_dungeon2_records
                WHERE player_id=%s ORDER BY dungeon_group_code''', (player_id,)).fetchall()]
        tower_progress = {}
        if self.connection.execute('SELECT 1 FROM public.player_tower_states WHERE player_id=%s',
                                   (player_id,)).fetchone():
            tower_progress['TowerFloors'] = [list(row) for row in self.connection.execute('''SELECT
                tower_code,floor,clear_count,continue_round_index FROM public.player_tower_floors
                WHERE player_id=%s ORDER BY tower_code,floor''', (player_id,)).fetchall()]
        return {'AccumulateInfos': accumulates, 'UpdateAccumulateInfos': accumulates,
                **dungeon_scores,
                **tower_progress,
                'MissionRewardReceivedInfos': sorted(receipts), 'BattlePasses': passes,
                **({'AdventureFlags': flags} if flags is not None else {}),
                'ShopPassInfos': shops, 'Honors': honors,
                **(self.garden().view(player_id, now) if self.garden() is not None else {})}

    def _expand_reward(self, reward, trail=()):
        if reward['Type'] != 9:
            return [reward]
        code = reward['ItemCode']
        if code in trail or len(trail) >= 8:
            raise TimeBusinessError('local_reward_pack_cycle', 503)
        contents = self.pack_rewards.get(code)
        if not contents:
            raise TimeBusinessError('local_reward_pack_configuration_missing', 503)
        result = []
        for row in contents:
            result.extend(self._expand_reward({'Type': row['InventoryType'],
                'ItemCode': row['InventoryCode'], 'Count': row['Count'] * reward['Count']}, trail + (code,)))
        return result

    def _grant(self, player_id, key, reward_codes, now):
        items = defaultdict(int)
        characters = set()
        rewards = []
        for code in reward_codes:
            if code not in self.rewards:
                raise TimeBusinessError('local_reward_configuration_missing', 503)
            for reward in self.rewards[code]:
                rewards.extend(self._expand_reward(reward))
        for reward in rewards:
            if reward['Type'] == 2:
                items[reward['ItemCode']] += reward['Count']
            elif reward['Type'] == 1:
                from types import SimpleNamespace
                from .lottery import LotteryStore
                code = reward['ItemCode']
                master = self.index.get('mission_character_master', {}).get(code)
                if master is None or reward['Count'] != 1:
                    raise TimeBusinessError('local_reward_character_configuration_missing', 503)
                store = LotteryStore(self.repo)
                if store.grant_character(player_id, master):
                    catalog = SimpleNamespace(costumes=self.index.get('mission_home_character_costume_master', {}))
                    store.unlock_costume(player_id, master, catalog)
                characters.add(code)
            elif reward['Type'] == 3:
                code = reward['ItemCode']
                if not self.connection.execute('''SELECT 1 FROM public.shop_definitions
                    WHERE name='honor_master' AND data @> %s''', (Jsonb([{'Code': code}]),)).fetchone():
                    raise TimeBusinessError('local_honor_configuration_missing', 503)
                # Share the existing ownership table with shop rewards. The mission
                # receipt and this insert commit or roll back in the same player transaction.
                self.connection.execute('''INSERT INTO public.shop_owned_honors
                    (player_id,honor_code,acquired_at) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING''',
                    (player_id, code, now))
            elif reward['Type'] == 12:
                self.add_pass_points(player_id, reward['ItemCode'], reward['Count'], now)
            elif reward['Type'] == 10 and self.garden() is not None:
                self.garden().unlock_room(player_id, reward['ItemCode'], now)
            elif reward['Type'] == 8 and self.garden() is not None:
                self.garden().grant_closeness_floor(player_id, reward['ItemCode'], reward['Count'])
            elif reward['Type'] == 4:
                self.connection.execute('''INSERT INTO public.player_stamina(player_id,kind,value,updated_at)
                    VALUES (%s,'normal',%s,%s) ON CONFLICT(player_id,kind) DO UPDATE
                    SET value=player_stamina.value+EXCLUDED.value,updated_at=EXCLUDED.updated_at''',
                    (player_id, reward['Count'], now))
            else:
                raise TimeBusinessError('local_timed_reward_type_not_implemented', 501)
        if items:
            self.repo.apply_item_changes(player_id, key, dict(items))
            for code, count in items.items():
                if count > 0:
                    self.event(player_id, 56, now, values=(str(code),), amount=count)
        return set(items) | characters

    def add_pass_points(self, player_id, code, amount, now):
        definition = self.index['battle_pass_master'].get(code)
        if not definition or not self.active(definition['ScheduleCode'], now):
            raise TimeBusinessError('local_battle_pass_not_active')
        self.connection.execute('''INSERT INTO public.player_battle_passes
            (player_id,code,weekly_received_at) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING''', (player_id, code, now))
        schedule = self.index['schedule_master'][definition['ScheduleCode']]
        week = max(0, self.clock.week(now, battle_pass=True) - self.clock.week(unix(schedule['StartAt']), battle_pass=True))
        caps = definition['WeekMaxPoints']
        cap = caps[min(week, len(caps) - 1)]
        current = self.connection.execute('SELECT weekly_point FROM public.player_battle_passes WHERE player_id=%s AND code=%s',
                                         (player_id, code)).fetchone()[0]
        delta = min(amount, max(0, cap - current))
        self.connection.execute('''UPDATE public.player_battle_passes SET total_point=total_point+%s,
            weekly_point=weekly_point+%s,weekly_received_at=%s WHERE player_id=%s AND code=%s''',
            (delta, delta, now, player_id, code))

    def login_bonus(self, player_id, now):
        with self.repo.transaction(player_id):
            self.refresh(player_id, now)
            now = self._effective_now(player_id, now)
            day = self.clock.day(now)
            changed, bonuses = set(), []
            for bonus in sorted(self.data['login_bonus_master'], key=lambda x: x['Priority']):
                if not self.active(bonus['ScheduleCode'], now) or not self.eligible(player_id, bonus['UserCategoryCode']):
                    continue
                code = bonus['Code']
                self.connection.execute('''INSERT INTO public.login_bonus_progress(player_id,bonus_code)
                    VALUES (%s,%s) ON CONFLICT DO NOTHING''', (player_id, code))
                index, last = self.connection.execute('''SELECT next_index,last_day FROM public.login_bonus_progress
                    WHERE player_id=%s AND bonus_code=%s''', (player_id, code)).fetchone()
                if last is not None and last >= day:
                    continue
                rewards = self.bonus_rewards[code]
                if index not in rewards:
                    if not bonus['IsRepeat']:
                        continue
                    index = min(rewards)
                changed |= self._grant(player_id, f'login-bonus:{code}:{day}', rewards[index], now)
                self.connection.execute('''UPDATE public.login_bonus_progress SET next_index=%s,last_day=%s
                    WHERE player_id=%s AND bonus_code=%s''', (index + 1, day, player_id, code))
                bonuses.append([code, index])
            for code, last_day in self.connection.execute('''SELECT code,last_reward_day FROM public.player_shop_passes
                WHERE player_id=%s AND activated_at<=%s AND end_at>%s''', (player_id, now, now)).fetchall():
                if last_day is not None and last_day >= day:
                    continue
                definition = self.index['shop_pass_master'].get(code)
                if definition is None:
                    raise TimeBusinessError('local_shop_pass_configuration_missing', 503)
                changed |= self._grant(player_id, f'shop-pass:{code}:{day}', definition['RewardCodes'], now)
                self.connection.execute('''UPDATE public.player_shop_passes SET last_reward_day=%s
                    WHERE player_id=%s AND code=%s''', (day, player_id, code))
            return bonuses, changed

    def receive_missions(self, player_id, codes, now, *, total_power=None):
        with self.repo.transaction(player_id):
            self.refresh(player_id, now)
            now = self._effective_now(player_id, now)
            changed = set()
            remaining = list(codes)
            deferred_errors = {'local_mission_locked', 'local_mission_not_complete',
                               'local_mission_receive_condition_not_met'}
            while remaining:
                deferred, first_error = [], None
                for code in remaining:
                    try:
                        changed |= self._receive_mission(player_id, code, now, total_power)
                    except TimeBusinessError as exc:
                        if exc.code not in deferred_errors:
                            raise
                        deferred.append(code)
                        if first_error is None:
                            first_error = exc
                if len(deferred) == len(remaining):
                    # No same-batch grant can satisfy the outstanding conditions.
                    # Roll back the whole request, including rewards already staged.
                    raise first_error
                remaining = deferred
            self.repo._touch(player_id)
            return changed

    def _receive_mission(self, player_id, code, now, total_power):
        mission = self.index['mission_master'].get(code)
        if mission is None or mission['IsObsoleted']:
            raise TimeBusinessError('local_mission_not_found', 404)
        group = self.index['mission_group_master'].get(mission['GroupCode'])
        if group is None:
            raise TimeBusinessError('local_mission_group_configuration_missing', 503)
        period = self._mission_period(mission, now)
        if self.connection.execute('''SELECT 1 FROM public.mission_receipts WHERE player_id=%s
            AND mission_code=%s AND period=%s''', (player_id, code, period)).fetchone():
            return set()
        if not self.active(group['ScheduleCodeForReceiveReward'], now):
            raise TimeBusinessError('local_mission_period_closed')
        if not self.eligible(player_id, group['UserCategoryCode']) or not self._group_unlocked(group, now):
            raise TimeBusinessError('local_mission_locked')
        unlock = mission['MissionCodeForUnlock']
        if unlock:
            predecessor = self.index['mission_master'].get(unlock)
            if predecessor is None:
                raise TimeBusinessError('local_mission_unlock_configuration_missing', 503)
            if not self.connection.execute('''SELECT 1 FROM public.mission_receipts
                WHERE player_id=%s AND mission_code=%s AND period=%s''',
                (player_id, unlock, self._mission_period(predecessor, now))).fetchone():
                raise TimeBusinessError('local_mission_locked')
        if (self.reference(player_id, mission['UserDataReferenceForUnlock'], total_power=total_power)
                < mission['UserDataReferenceCountForUnlock']
                or self.reference(player_id, mission['UserDataReference'], total_power=total_power)
                < mission['TargetCount']):
            raise TimeBusinessError('local_mission_not_complete')
        if (mission['UserDataReferenceToReceive'] is not None
                and self.reference(player_id, mission['UserDataReferenceToReceive'], total_power=total_power)
                < mission['UserDataReferenceCountToReceive']):
            raise TimeBusinessError('local_mission_receive_condition_not_met')
        changed = self._grant(player_id, f'mission:{code}:{period}', [mission['RewardCode']], now)
        self.connection.execute('INSERT INTO public.mission_receipts VALUES (%s,%s,%s,%s)',
                                (player_id, code, period, now))
        self.event(player_id, 36, now, values=(MISSION_CATEGORIES[group['Category']],
                   MISSION_SUBCATEGORIES[group['SubCategory']]))
        self.event(player_id, 37, now, values=(str(group['Code']),))
        return changed

    def shop_notifications(self, player_id, now):
        with self.repo.transaction(player_id):
            now = self._effective_now(player_id, now)
            for code, end, notified in self.connection.execute('''SELECT code,end_at,notified_at FROM public.player_shop_passes
                WHERE player_id=%s AND activated_at<=%s AND end_at>%s''', (player_id, now, now)).fetchall():
                definition = self.index['shop_pass_master'].get(code)
                if definition and end - now <= definition['RepurchaseDays'] * 86400 and notified is None:
                    self.connection.execute('UPDATE public.player_shop_passes SET notified_at=%s WHERE player_id=%s AND code=%s',
                                            (now, player_id, code))
            return self.view(player_id, now)['ShopPassInfos']

    def lottery_expiry(self, player_id, code, now):
        definition = self.index['lottery_master'].get(code)
        if definition is None or not self.active(definition['ScheduleCode'], now):
            return False, None
        for condition in definition['Unlocks']:
            value = self.reference(player_id, condition['UserDataReference'])
            if value < condition['TargetCount'] or (condition['TargetCountTo'] and value > condition['TargetCountTo']):
                return False, None
        expiry = None
        if definition['ScheduleCode']:
            expiry = unix(self.index['schedule_master'][definition['ScheduleCode']]['EndAt'])
        if definition['LimitExpired'] is not None:
            absolute = unix(definition['LimitExpired'])
            expiry = absolute if expiry is None else min(expiry, absolute)
        if definition['LimitType'] == 2:
            first = self.connection.execute('SELECT first_logged_in_at FROM public.players WHERE player_id=%s',
                                            (player_id,)).fetchone()[0]
            personal = first + definition['LimitTime']
            expiry = personal if expiry is None else min(expiry, personal)
        return expiry is None or now < expiry, expiry

    def lottery_displays(self, player_id, now, existing=None):
        with self.repo.transaction(player_id):
            now = self._effective_now(player_id, now)
            if existing is None:
                existing = []
                for definition in self.data['lottery_master']:
                    settings = self.index['lottery_settings_master'].get(definition['LotterySettingsCode'])
                    if settings is None:
                        continue
                    buttons = [[r['ButtonIndex'], r['LimittedTime'], 0] for r in settings['ButtonSettings']]
                    existing.append([definition['Code'], buttons, definition['ShowPriority'], None, []])
            result = []
            for value in existing:
                active, expiry = self.lottery_expiry(player_id, value[0], now)
                if not active:
                    continue
                if value[3] is not None and unix(value[3]) <= now:
                    continue
                value = list(value)
                if expiry is not None:
                    expiry = min(expiry, unix(value[3])) if value[3] is not None else expiry
                    value[3] = timestamp(expiry)
                result.append(value)
            return result
