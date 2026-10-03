"""Daily quest allowances in the existing player quest/group records.

Call under the repository's player transaction. Counts are remaining allowances,
and LastResetAt changes only on initialization or a new game day.
"""


class QuestChallengeError(ValueError):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


class QuestChallenges:
    def __init__(self, repository, clock):
        self.repo, self.clock = repository, clock
        self.connection = repository.connection
        data = dict(self.connection.execute('SELECT name,data FROM public.quest_definitions').fetchall())
        self.quests = {r['Code']: r for r in data.get('quest_master', [])}
        self.groups = {r['Code']: r for r in data.get('quest_group_master', [])}
        settings = {r['Key']: r['Value'] for r in data.get('game_setting_master', [])}
        value = settings.get('QUEST_RECOVERY_STONE_COUNT')
        self.recovery_stones = int(value[0]) if value else None

    @staticmethod
    def ordinary(group):
        if group['GuildBattleCode']:
            return False
        if group['Category'] == 3:
            return bool(group['EventCode']) and not group['SubEventCode']
        if group['Category'] == 16:
            return bool(group['SubEventCode']) and not group['EventCode']
        return group['Category'] in (1, 2, 4, 5) and not (group['EventCode'] or group['SubEventCode'])

    def target(self, quest):
        group = self.groups.get(quest['QuestGroupCode'])
        if group is None:
            raise QuestChallengeError('local_quest_configuration_missing', 503)
        if not group['MaxChallengeCount']:
            return None
        if group['ChallengeCountType'] == 0:
            return 'quests', 'quest_code', quest['Code'], group
        if group['ChallengeCountType'] == 1:
            return 'quest_groups', 'quest_group_code', group['Code'], group
        raise QuestChallengeError('local_quest_challenge_type_not_implemented', 501)

    def _ensure(self, player_id, target, now):
        table, column, code, group = target
        if table == 'quests':
            self.connection.execute('''INSERT INTO public.quests(player_id,quest_code,clear_count,star_count)
                VALUES (%s,%s,0,0) ON CONFLICT DO NOTHING''', (player_id, code))
        else:
            self.connection.execute('''INSERT INTO public.quest_groups(player_id,quest_group_code,clear_count)
                VALUES (%s,%s,0) ON CONFLICT DO NOTHING''', (player_id, code))
        row = self.connection.execute(f'''SELECT challenge_count,challenge_last_reset_at,
            recover_count,recover_last_reset_at FROM public.{table} WHERE player_id=%s AND {column}=%s''',
            (player_id, code)).fetchone()
        # Retain a current-day allowance, including an already purchased refill.
        # A backward clock never restores a previously spent allowance.
        for index, prefix, maximum in ((0, 'challenge', group['MaxChallengeCount']),
                                       (2, 'recover', group['MaxRecoveryChallengeCount'])):
            if row[index] is None or self.clock.day(now) > self.clock.day(row[index + 1]):
                self.connection.execute(f'''UPDATE public.{table} SET {prefix}_count=%s,
                    {prefix}_last_reset_at=%s WHERE player_id=%s AND {column}=%s''',
                    (maximum, now, player_id, code))
        return self.connection.execute(f'''SELECT challenge_count,recover_count FROM public.{table}
            WHERE player_id=%s AND {column}=%s''', (player_id, code)).fetchone()

    def refresh(self, player_id, now):
        # Group-wide training allowances must be present even before a first clear.
        for group in self.groups.values():
            if self.ordinary(group) and group['MaxChallengeCount'] and group['ChallengeCountType'] == 1:
                self._ensure(player_id, ('quest_groups', 'quest_group_code', group['Code'], group), now)
        # Initialize/reset per-stage allowances only for existing player progress.
        # This avoids adding thousands of uncleared stages to a player's login data.
        rows = self.connection.execute('SELECT quest_code FROM public.quests WHERE player_id=%s',
                                       (player_id,)).fetchall()
        for (code,) in rows:
            quest = self.quests.get(code)
            group = self.groups.get(quest['QuestGroupCode']) if quest else None
            if group and self.ordinary(group) and group['MaxChallengeCount'] and group['ChallengeCountType'] == 0:
                self._ensure(player_id, ('quests', 'quest_code', code, group), now)

    def require(self, player_id, quest, now, amount=1):
        target = self.target(quest)
        if target and self._ensure(player_id, target, now)[0] < amount:
            raise QuestChallengeError('local_quest_challenge_limit_reached')
        return target

    def consume(self, player_id, quest, now, amount=1):
        target = self.require(player_id, quest, now, amount)
        if target:
            table, column, code, _ = target
            self.connection.execute(f'''UPDATE public.{table} SET challenge_count=challenge_count-%s
                WHERE player_id=%s AND {column}=%s''', (amount, player_id, code))
            self.repo._touch(player_id)

    def recover(self, player_id, target, now):
        if target is None:
            raise QuestChallengeError('local_quest_challenge_recovery_unavailable')
        table, column, code, group = target
        remaining, recovery = self._ensure(player_id, target, now)
        if recovery <= 0:
            raise QuestChallengeError('local_quest_challenge_recovery_limit_reached')
        if remaining != 0:
            raise QuestChallengeError('local_quest_challenges_not_exhausted')
        self.connection.execute(f'''UPDATE public.{table} SET challenge_count=%s,recover_count=recover_count-1
            WHERE player_id=%s AND {column}=%s''', (group['MaxChallengeCount'], player_id, code))
        self.repo._touch(player_id)
