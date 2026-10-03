"""Tower progress and receipts; callers hold the repository player transaction."""
from collections import defaultdict

from psycopg.types.json import Jsonb

from local_server.protocol import LocalError, integer


class TowerStore:
    def __init__(self, repository):
        self.repo, self.connection = repository, repository.connection
        data = dict(self.connection.execute('SELECT name,data FROM public.tower_definitions').fetchall())
        if any(not data.get(name) for name in ('tower_master', 'tower_floor_master', 'tower_reward_master')):
            raise LocalError('local_tower_configuration_missing', 503)
        self.codes = {r['Code'] for r in data['tower_master']}
        self.floors = {(r['TowerCode'], r['Floor']): r for r in data['tower_floor_master']}
        self.rewards = defaultdict(list)
        for row in data['tower_reward_master']:
            self.rewards[row['Code']].append(row)

    def require(self, code, floor=None):
        if code not in self.codes:
            raise LocalError('local_tower_not_found', 404)
        if floor is not None:
            definition = self.floors.get((code, floor))
            if definition is None:
                raise LocalError('local_tower_floor_not_found', 404)
            return definition

    def initialize(self, player, code, seed, protocol, now):
        self.require(code)
        inserted = self.connection.execute('''INSERT INTO public.player_tower_states
            (player_id,tower_code) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING tower_code''', (player, code)).fetchone()
        if inserted:
            seen = set()
            for value in seed:
                row = protocol.fields('TowerFloorInfo', value, strict=True)
                if row['TowerCode'] != code:
                    continue
                floor = integer(row['Floor'], minimum=1, maximum=2**31 - 1)
                definition = self.require(code, floor)
                count = integer(row['ClearCount'], maximum=2**31 - 1)
                index = integer(row['ContinueRoundIndex'], maximum=len(definition['QuestCodes']) - 1)
                if floor in seen:
                    raise LocalError('local_tower_seed_floor_duplicate', 503)
                seen.add(floor)
                self.connection.execute('''INSERT INTO public.player_tower_floors
                    (player_id,tower_code,floor,clear_count,continue_round_index) VALUES (%s,%s,%s,%s,%s)''',
                    (player, code, floor, count, index))
                if count:
                    self.receipt(player, code, 'first', floor, floor, now)
        checked = self.connection.execute('''UPDATE public.player_tower_states SET checked_at=GREATEST(checked_at,%s)
            WHERE player_id=%s AND tower_code=%s RETURNING checked_at''', (now, player, code)).fetchone()[0]
        return checked

    def progress(self, player, code, floor):
        row = self.connection.execute('''SELECT clear_count,continue_round_index,first_cleared_at,
            used_characters,used_magic_items FROM public.player_tower_floors
            WHERE player_id=%s AND tower_code=%s AND floor=%s''', (player, code, floor)).fetchone()
        return dict(zip(('count', 'index', 'first_at', 'characters', 'magic'), row or (0, 0, None, [], [])))

    def save(self, player, code, floor, progress):
        self.connection.execute('''INSERT INTO public.player_tower_floors
            (player_id,tower_code,floor,clear_count,continue_round_index,first_cleared_at,used_characters,used_magic_items)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(player_id,tower_code,floor) DO UPDATE SET
            clear_count=EXCLUDED.clear_count,continue_round_index=EXCLUDED.continue_round_index,
            first_cleared_at=EXCLUDED.first_cleared_at,used_characters=EXCLUDED.used_characters,
            used_magic_items=EXCLUDED.used_magic_items''', (player, code, floor, progress['count'], progress['index'],
            progress['first_at'], Jsonb(progress['characters']), Jsonb(progress['magic'])))
        self.repo._touch(player)

    def view(self, player, code):
        rows = {r[0]: r[1:] for r in self.connection.execute('''SELECT floor,clear_count,continue_round_index
            FROM public.player_tower_floors WHERE player_id=%s AND tower_code=%s''', (player, code)).fetchall()}
        return [[code, floor, *rows.get(floor, (0, 0))] for tower, floor in sorted(self.floors) if tower == code]

    def unlocked(self, player, code, floor):
        self.require(code, floor)
        if floor > 1 and not self.progress(player, code, floor - 1)['count']:
            raise LocalError('local_tower_floor_locked', 409)

    def receipt(self, player, code, kind, period, floor, now):
        return self.connection.execute('''INSERT INTO public.player_tower_rewards
            VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING floor''',
            (player, code, kind, period, floor, now)).fetchone() is not None

    def grant(self, player, code, kind, period, floor, reward_code, now):
        rewards = sorted(self.rewards.get(reward_code, []), key=lambda r: r['DisplayPriority'])
        if not rewards:
            raise LocalError('local_tower_reward_configuration_missing', 503)
        if not self.receipt(player, code, kind, period, floor, now):
            return [], set()
        changes = defaultdict(int)
        for reward in rewards:
            if reward['Type'] != 2:
                raise LocalError('local_tower_reward_type_not_implemented', 501)
            changes[integer(reward['ItemCode'], minimum=1)] += integer(reward['Count'], minimum=1)
        self.repo.apply_item_changes(player, f'tower:{code}:{kind}:{period}', dict(changes))
        for item, count in changes.items():
            self.repo.timing.event(player, 56, now, values=(str(item),), amount=count)
        return rewards, set(changes)

    def battle(self, player, unique):
        return self.connection.execute('''SELECT tower_code,floor,starting_round_index,start_hash,
            parties,state,result_hash,response FROM public.player_tower_battles
            WHERE player_id=%s AND unique_id=%s''', (player, unique)).fetchone()

    def abandon(self, player, code=None, floor=None):
        self.connection.execute('''UPDATE public.player_tower_battles SET state='abandoned'
            WHERE player_id=%s AND state='active' AND (%s::bigint IS NULL OR tower_code=%s)
            AND (%s::integer IS NULL OR floor=%s)''', (player, code, code, floor, floor))
