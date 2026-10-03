"""Player-owned arena entry state; callers hold the existing player transaction."""
from local_server.protocol import LocalError, integer
from .game_time import unix


class ArenaStore:
    def __init__(self, repository):
        self.repo, self.connection = repository, repository.connection
        self.timing = repository.timing

    def require(self, code):
        row = next((r for r in self.timing.data.get('arena_master', []) if r['Code'] == code), None)
        if row is None:
            raise LocalError('local_arena_not_found', 404)
        return row

    def initial_rank(self):
        settings = {r['Key']: r['Value'] for r in self.timing.data.get('arena_entry_settings', [])}
        values = settings.get('ARENA_RANKING_SIZE')
        try:
            if not isinstance(values, list) or len(values) != 1:
                raise ValueError()
            return integer(int(values[0]), minimum=1, maximum=2**31 - 1)
        except (ValueError, TypeError, LocalError) as exc:
            raise LocalError('local_arena_initial_rank_invalid', 503) from exc

    def current(self, category, now):
        data = self.timing.data
        required = ('arena_master', 'arena_schedule_master', 'arena_settings')
        if any(name not in data for name in required):
            raise LocalError('local_arena_configuration_missing', 503)
        schedules = {r['Code']: r for r in data['arena_schedule_master']}
        candidates = []
        for row in data['arena_master']:
            if row['Category'] != category:
                continue
            code = row['ScheduleCode']
            schedule = schedules.get(code)
            if code and (schedule is None or schedule['Type'] != 0):
                raise LocalError('local_arena_schedule_invalid', 503)
            if not code or unix(schedule['StartAt']) <= now < unix(schedule['EndAt']):
                candidates.append(row['Code'])
        if not candidates:
            raise LocalError('local_arena_not_open', 409)
        if len(candidates) != 1:
            raise LocalError('local_arena_season_ambiguous', 503)
        return candidates[0]

    def info(self, player_id, code, now):
        settings = {row['Key']: row['Value'] for row in self.timing.data['arena_settings']}
        values = settings.get('ARENA_MAX_CHALLENGE_COUNT')
        if not isinstance(values, list) or len(values) != 1:
            raise LocalError('local_arena_challenge_limit_invalid', 503)
        try:
            maximum = integer(int(values[0]), minimum=1)
        except (ValueError, TypeError, LocalError) as exc:
            raise LocalError('local_arena_challenge_limit_invalid', 503) from exc
        day = self.timing.clock.day(now)
        initial_rank = self.initial_rank()
        inserted = self.connection.execute('''INSERT INTO public.player_arena_states
            (player_id,arena_code,rank,challenge_count,challenge_day) VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING RETURNING arena_code''', (player_id, code, initial_rank, maximum, day)).fetchone()
        # Rank=0 came from the old local initializer. The client cannot resolve
        # its Type.Time reward range and aborts before loading the arena page.
        repaired = self.connection.execute('''UPDATE public.player_arena_states SET rank=%s
            WHERE player_id=%s AND arena_code=%s AND rank=0 RETURNING arena_code''',
            (initial_rank, player_id, code)).fetchone()
        refreshed = self.connection.execute('''UPDATE public.player_arena_states
            SET challenge_count=%s,challenge_day=%s WHERE player_id=%s AND arena_code=%s
            AND challenge_day<%s RETURNING arena_code''', (maximum, day, player_id, code, day)).fetchone()
        if inserted or refreshed or repaired:
            self.repo._touch(player_id)
        row = self.connection.execute('''SELECT rank,challenge_count,cool_time_end_at,time_reward_count
            FROM public.player_arena_states WHERE player_id=%s AND arena_code=%s''', (player_id, code)).fetchone()
        return dict(zip(('Rank', 'ChallengeCount', 'CoolTimeEndAt', 'TimeRewardCount'), row))
