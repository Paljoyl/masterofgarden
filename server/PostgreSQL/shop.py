"""Shop state composed under PlayerRepository.transaction, using public only."""
from uuid import uuid4
from hashlib import sha256

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class ShopStore:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection

    def count(self, player_id, kind, code, period):
        row = self.connection.execute('''SELECT purchased_count FROM public.shop_purchase_counts
            WHERE player_id=%s AND kind=%s AND code=%s AND period=%s''', (player_id, kind, code, period)).fetchone()
        return row[0] if row else 0

    def increment(self, player_id, kind, code, period, amount, now):
        self.connection.execute('''INSERT INTO public.shop_purchase_counts VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT(player_id,kind,code,period) DO UPDATE SET
            purchased_count=public.shop_purchase_counts.purchased_count+EXCLUDED.purchased_count,
            updated_at=EXCLUDED.updated_at''', (player_id, kind, code, period, amount, now))
        self.repo._touch(player_id)

    def selection(self, player_id, code, period, choose, *, refresh=False):
        row = self.connection.execute('''SELECT lottery_code FROM public.shop_lineup_selections
            WHERE player_id=%s AND code=%s AND period=%s''', (player_id, code, period)).fetchone()
        if row and not refresh:
            return row[0]
        selected = choose()
        self.connection.execute('''INSERT INTO public.shop_lineup_selections
            (player_id,code,period,lottery_code) VALUES (%s,%s,%s,%s)
            ON CONFLICT(player_id,code,period) DO UPDATE SET lottery_code=EXCLUDED.lottery_code,
            generation=public.shop_lineup_selections.generation+1''', (player_id, code, period, selected))
        if refresh:
            self.connection.execute('''UPDATE public.shop_purchase_counts SET purchased_count=0
                WHERE player_id=%s AND kind='lineup' AND code=%s AND period=%s''', (player_id, code, period))
        return selected

    def order(self, player_id, code, variant, *, pending=False):
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute('''SELECT * FROM public.local_payment_orders
                WHERE player_id=%s AND payment_code=%s AND variant=%s''' +
                (" AND status='pending'" if pending else '') + ' ORDER BY created_at DESC,order_id DESC LIMIT 1',
                (player_id, code, variant))
            return cursor.fetchone()

    def prepare(self, player_id, code, variant, now):
        previous = self.order(player_id, code, variant, pending=True)
        if previous:
            return previous
        order_id = uuid4().hex
        self.connection.execute('''INSERT INTO public.local_payment_orders
            (player_id,order_id,payment_code,variant,status,created_at) VALUES (%s,%s,%s,%s,'pending',%s)''',
            (player_id, order_id, code, variant, now))
        return self.order(player_id, code, variant, pending=True)

    def complete(self, player_id, order_id, now, response):
        self.connection.execute('''UPDATE public.local_payment_orders SET status='complete',completed_at=%s,response=%s
            WHERE player_id=%s AND order_id=%s AND status='pending' ''', (now, response, player_id, order_id))

    def repair_paid_stones(self, player_id):
        """Move old local payment grants to the TW PC pool once, preserving total stones.

        Only completed local-payment ledger entries qualify. Consumed stones are
        not reissued, and seed/official balances have no independent repair entry.
        """
        moved = 0
        with self.repo.transaction(player_id):
            rows = self.connection.execute('''SELECT orders.order_id,ledger.delta
                FROM public.local_payment_orders AS orders
                JOIN public.item_ledger AS ledger ON ledger.player_id=orders.player_id
                    AND ledger.operation_key='local-payment:' || orders.order_id
                    AND ledger.item_code=990000002 AND ledger.delta>0
                WHERE orders.player_id=%s AND orders.status='complete'
                    AND NOT EXISTS (SELECT 1 FROM public.item_ledger AS main
                        WHERE main.player_id=orders.player_id
                            AND main.operation_key=ledger.operation_key AND main.item_code=990000003)
                    AND NOT EXISTS (SELECT 1 FROM public.operations AS repair
                        WHERE repair.player_id=orders.player_id
                            AND repair.operation_key='local-payment-stone-pc:' || orders.order_id)
                ORDER BY orders.created_at,orders.order_id''', (player_id,)).fetchall()
            for order_id, original_amount in rows:
                key = 'local-payment-stone-pc:' + order_id
                row = self.connection.execute('SELECT quantity FROM public.items WHERE player_id=%s AND item_code=990000002',
                                              (player_id,)).fetchone()
                amount = min(original_amount, row[0] if row else 0)
                if amount:
                    self.repo.apply_item_changes(player_id, key, {990000002: -amount, 990000003: amount})
                    moved += amount
                else:
                    # A spent award still needs a durable marker, so later credits
                    # cannot be mistaken for the residue of this historical order.
                    self.connection.execute('''INSERT INTO public.operations
                        (player_id,operation_key,operation_type,request_hash,result)
                        VALUES (%s,%s,'payment-stone-repair',%s,%s)''',
                        (player_id, key, sha256(str(original_amount).encode('ascii')).hexdigest(),
                         Jsonb({'moved': 0, 'original_amount': original_amount})))
        return moved

    def honor(self, player_id, code, now):
        self.connection.execute('INSERT INTO public.shop_owned_honors VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                                (player_id, code, now))

    def honors(self, player_id):
        return [r[0] for r in self.connection.execute(
            'SELECT honor_code FROM public.shop_owned_honors WHERE player_id=%s ORDER BY honor_code', (player_id,))]

    def grant(self, player_id, key, rewards, catalog, now):
        from collections import defaultdict
        from .player_protocol import InvalidPlayerData
        from .players import OperationConflict
        items = defaultdict(int)
        character_codes, honor_codes, pass_codes = set(), set(), set()
        for kind, code, amount, _ in rewards:
            if type(amount) is not int or not 0 < amount < 2**63:
                raise InvalidPlayerData('Invalid shop reward quantity')
            if kind == 2:
                items[code] += amount
            elif kind == 1:
                character = catalog.characters.get(code)
                if character is None:
                    raise InvalidPlayerData('Unknown shop character')
                self.connection.execute('''INSERT INTO public.characters
                    (player_id,character_code,level,experience,rank,limit_break,rarity,closeness)
                    VALUES (%s,%s,1,0,1,0,%s,0) ON CONFLICT DO NOTHING''',
                    (player_id, code, character['DefaultRarity']))
                character_codes.add(code)
            elif kind == 3:
                if code not in catalog.honors:
                    raise InvalidPlayerData('Unknown shop honor')
                self.honor(player_id, code, now)
                honor_codes.add(code)
            elif kind == 4:
                self.connection.execute('''INSERT INTO public.player_stamina VALUES (%s,'normal',%s,%s)
                    ON CONFLICT(player_id,kind) DO UPDATE SET value=public.player_stamina.value+EXCLUDED.value,
                    updated_at=EXCLUDED.updated_at''', (player_id, amount, now))
            elif kind == 6:
                definition = catalog.passes.get(code)
                if definition is None:
                    raise InvalidPlayerData('Unknown shop pass')
                previous = self.connection.execute('SELECT end_at FROM public.player_shop_passes WHERE player_id=%s AND code=%s',
                                                   (player_id, code)).fetchone()
                end = max(now, previous[0] if previous else now)
                if end > now + definition['RepurchaseDays'] * 86400:
                    raise OperationConflict('Shop pass cannot yet be renewed')
                end += definition['ContinueDays'] * 86400 * amount
                self.connection.execute('''INSERT INTO public.player_shop_passes
                    (player_id,code,activated_at,end_at) VALUES (%s,%s,%s,%s)
                    ON CONFLICT(player_id,code) DO UPDATE SET end_at=EXCLUDED.end_at,notified_at=NULL''',
                    (player_id, code, now, end))
                pass_codes.add(code)
            elif kind == 7:
                definition = catalog.specific_levels.get(code)
                if definition is None:
                    raise InvalidPlayerData('Unknown player-level reward')
                target = max(r['Level'] for r in catalog.levels) - definition['DiffFromMaxLevel']
                row = next(r for r in catalog.levels if r['Level'] == target)
                current = self.connection.execute('SELECT level FROM public.players WHERE player_id=%s', (player_id,)).fetchone()[0]
                if current < target:
                    self.repo.update_player(player_id, level=target, experience=row['TotalExp'])
            elif kind == 11:
                definition = catalog.battle_passes.get(code)
                if definition is None or not catalog.active(definition, now):
                    raise InvalidPlayerData('Unknown or expired battle pass')
                self.connection.execute('''INSERT INTO public.player_battle_passes
                    (player_id,code,weekly_received_at,is_purchased) VALUES (%s,%s,%s,TRUE)
                    ON CONFLICT(player_id,code) DO UPDATE SET is_purchased=TRUE''', (player_id, code, now))
            else:
                raise InvalidPlayerData('Unsupported shop reward type')
        if items:
            self.repo.apply_item_changes(player_id, key, dict(items))
        self.repo._touch(player_id)
        return set(items), character_codes, honor_codes, pass_codes
