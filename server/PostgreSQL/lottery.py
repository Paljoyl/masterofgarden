"""Owned lottery counters, receipts and history inside the caller's player transaction."""
from hashlib import sha256

from psycopg.types.json import Jsonb

from .player_protocol import integer, record


class LotteryStore:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection

    def initialize(self, player_id, displays, captured_at, histories, catalog, now):
        # Selection import also works for accounts initialized before this table
        # existed. A locally saved empty or partial selection is never overwritten.
        from local_server.protocol import LocalError
        for value in displays or []:
            display = record(self.repo.registry, 'LotteryDisplayInfo', value)
            pool = catalog.pools.get(display['LotteryCode'])
            if pool is None or pool['LotteryType'] != 1 or not display['LotterySelectCharacters']:
                continue
            try:
                selected = catalog.validate_selection(pool, display['LotterySelectCharacters'])
            except LocalError:
                continue
            self.connection.execute('''INSERT INTO public.player_lottery_selections
                (player_id,lottery_code,characters,updated_at) VALUES (%s,%s,%s,%s)
                ON CONFLICT DO NOTHING''', (player_id, pool['Code'], Jsonb(selected), captured_at or now))
        inserted = self.connection.execute('''INSERT INTO public.player_lottery_state VALUES (%s,%s)
            ON CONFLICT DO NOTHING RETURNING player_id''', (player_id, now)).fetchone()
        if not inserted:
            return
        for value in displays or []:
            display = record(self.repo.registry, 'LotteryDisplayInfo', value)
            pool = catalog.pools.get(display['LotteryCode'])
            if pool is None:
                continue
            settings = catalog.setting(pool)
            buttons = {r['ButtonIndex']: r for r in settings['ButtonSettings']}
            for info in display['ButtonInfos']:
                row = record(self.repo.registry, 'LotteryButtonInfo', info)
                button = buttons.get(row['ButtonIndex'])
                if button is None:
                    continue
                total = integer(row['TotalCount'], 'TotalCount')
                remain = integer(row['RemainCount'], 'RemainCount')
                if total < 0 or remain < -1:
                    continue
                if button['LimittedTime'] and not 0 <= remain <= button['LimittedTime']:
                    continue
                used = max(0, button['LimittedTime'] - remain) if button['LimittedTime'] else 0
                self.connection.execute('''INSERT INTO public.lottery_button_counts VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING''', (player_id, pool['Code'], row['ButtonIndex'],
                    catalog.period(settings['ResetType'], captured_at or now), used, max(total, used)))
        # Historical results establish no rewards and never overwrite owned inventory.
        for index, value in enumerate(histories or []):
            row = record(self.repo.registry, 'LotteryHistoryInfo', value)
            self.history(player_id, 'lottery-seed:' + sha256(repr(value).encode()).hexdigest(),
                         row['LotteryCode'], None, row['ExecAt'], row['ConsumeItemCode'],
                         row['ConsumeCount'], row['LotteryHistoryDetails'], None)
        self.repo._touch(player_id)

    def selection(self, player_id, code):
        row = self.connection.execute('''SELECT characters FROM public.player_lottery_selections
            WHERE player_id=%s AND lottery_code=%s''', (player_id, code)).fetchone()
        return list(row[0]) if row else []

    def save_selection(self, player_id, code, characters, now):
        self.connection.execute('''INSERT INTO public.player_lottery_selections
            (player_id,lottery_code,characters,updated_at) VALUES (%s,%s,%s,%s)
            ON CONFLICT(player_id,lottery_code) DO UPDATE SET
            characters=EXCLUDED.characters,updated_at=EXCLUDED.updated_at''',
            (player_id, code, Jsonb(characters), now))
        self.repo._touch(player_id)

    def count(self, player_id, code, button, period):
        row = self.connection.execute('''SELECT period,used_count,total_count FROM public.lottery_button_counts
            WHERE player_id=%s AND lottery_code=%s AND button_index=%s''', (player_id, code, button)).fetchone()
        if row is None:
            return 0, 0
        # A backward clock never grants fresh daily/monthly/weekly uses.
        return (row[1] if period <= row[0] else 0), row[2]

    def increment(self, player_id, code, button, period):
        self.connection.execute('''INSERT INTO public.lottery_button_counts VALUES (%s,%s,%s,%s,1,1)
            ON CONFLICT(player_id,lottery_code,button_index) DO UPDATE SET
            used_count=CASE WHEN EXCLUDED.period>public.lottery_button_counts.period THEN 1
                ELSE public.lottery_button_counts.used_count+1 END,
            period=GREATEST(public.lottery_button_counts.period,EXCLUDED.period),
            total_count=public.lottery_button_counts.total_count+1''', (player_id, code, button, period))

    def receipt(self, player_id, bonus, setting, cycle, point, now):
        return bool(self.connection.execute('''INSERT INTO public.lottery_bonus_receipts VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING RETURNING reward_point''', (player_id, bonus, setting, cycle, point, now)).fetchone())

    def history(self, player_id, key, code, button, now, consume_code, consume_count, details, probability_hash):
        self.connection.execute('''INSERT INTO public.lottery_histories
            (player_id,operation_key,lottery_code,button_index,exec_at,consume_item_code,consume_count,details,probability_hash)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(player_id,operation_key) DO NOTHING''',
            (player_id, key, code, button, now, consume_code, consume_count, Jsonb(details), probability_hash))

    def histories(self, player_id, now, catalog):
        return [list(row) for row in self.connection.execute('''SELECT lottery_code,exec_at,consume_item_code,
            consume_count,details FROM public.lottery_histories WHERE player_id=%s AND exec_at>=%s
            ORDER BY exec_at DESC,id DESC LIMIT %s''',
            (player_id, now - catalog.history_days * 86400, catalog.history_count)).fetchall()]

    def grant_character(self, player_id, master):
        return bool(self.connection.execute('''INSERT INTO public.characters
            (player_id,character_code,level,experience,rank,limit_break,rarity,closeness)
            VALUES (%s,%s,1,0,1,0,%s,0) ON CONFLICT DO NOTHING RETURNING character_code''',
            (player_id, master['Code'], master['DefaultRarity'])).fetchone())

    def unlock_costume(self, player_id, master, catalog):
        costume = master['HomeCharacterCostumeCode']
        definition = catalog.costumes.get(costume)
        if definition is None:
            from local_server.protocol import LocalError
            raise LocalError('local_lottery_home_definition_missing', 503)
        row = self.connection.execute('SELECT home_characters FROM public.players WHERE player_id=%s',
                                      (player_id,)).fetchone()
        if row[0] is None:
            from local_server.protocol import LocalError
            raise LocalError('local_home_seed_not_found', 503)
        characters = row[0]
        owner = definition['HomeCharacterCode']
        target = next((c for c in characters if c[0] == owner), None)
        if target is None:
            # Newly seen home characters in successful captures start at closeness 1.
            # Timed player refresh fills ordinary quiz choices from the master data.
            characters.append([owner, 1, 0, [], [costume], False])
        elif costume not in target[4]:
            target[4].append(costume)
        self.connection.execute('UPDATE public.players SET home_characters=%s WHERE player_id=%s',
                                (Jsonb(characters), player_id))
