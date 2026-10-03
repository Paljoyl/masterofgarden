"""Consumable recovery and daily allowances under the existing player lock."""
from uuid import uuid4

from .timed import TimeBusinessError


STAMINA_ITEM = 390000002


class StaminaStore:
    def __init__(self, repository, timing):
        self.repo = repository
        self.connection = repository.connection
        self.timing = timing
        data = self.timing.data
        self.items = {row['ItemCode']: row for row in data['stamina_recovery_items']}
        self.settings = {row['Key']: int(row['Value'][0])
                         for row in data['stamina_recovery_settings']}
        self.unlocks = data['stamina_recovery_daily_feed_limit_unlock_master']
        self.campaigns = data['stamina_recovery_campaigns']
        self.counter = next(row['ItemCode'] for row in self.items.values()
                            if row['ItemBehaviourType'] == 24)
        self.stones = {row['ItemCode'] for row in data.get('stamina_recovery_stones', [])}
        self.stone_prices = {row['RecoveryCount']: row['ConsumeStoneAmount']
                             for row in data.get('stamina_recovery_count_master', [])}
        self.stone_item = next((row for row in self.items.values()
                                if row['ItemBehaviourType'] == 25), None)
        if self.stone_prices and (sorted(self.stone_prices) != list(range(1, len(self.stone_prices) + 1))
                                 or any(type(p) is not int or p <= 0 for p in self.stone_prices.values())):
            raise TimeBusinessError('local_stamina_stone_configuration_invalid', 503)

    def refresh(self, player_id, now):
        # Old login captures retain normal stamina in StackItems only. Seed the
        # missing server row once, then use that row for regeneration and rewards.
        self.connection.execute('''INSERT INTO public.player_stamina(player_id,kind,value,updated_at)
            SELECT player_id,'normal',quantity,recovered_at FROM public.items
            WHERE player_id=%s AND item_code=%s ON CONFLICT(player_id,kind) DO NOTHING''',
            (player_id, STAMINA_ITEM))
        cleared = {row[0] for row in self.connection.execute('''SELECT quest_code FROM public.quests
            WHERE player_id=%s AND clear_count>0''', (player_id,)).fetchall()}
        daily = self.settings['STAMINA_RECOVERY_DAILY_FEED_LIMIT'] + sum(
            row['Count'] for row in self.unlocks if row['QuestCode'] in cleared)
        # The client takes the first active StaminaItemUsageBoost campaign.
        campaign = next((row for row in self.campaigns
                         if row['StartAt'] is None or row['StartAt'] <= now <= row['EndAt']), None)
        ordinary = self.settings['REMAIN_RECOVER_STAMINA_COUNT_WITH_ITEM_LIMIT'] + (
            campaign['ExtraCount'] if campaign else 0)
        for item in self.items.values():
            kind = item['ItemBehaviourType']
            if kind not in (22, 24, 25):
                continue  # Owned consumables are never replenished by a daily reset.
            if kind == 25:
                if not self.stone_prices:
                    continue
                cap = max(self.stone_prices)
            else:
                cap = daily if kind == 22 else ordinary
            row = self.connection.execute('''SELECT quantity,recovered_at FROM public.items
                WHERE player_id=%s AND item_code=%s''', (player_id, item['ItemCode'])).fetchone()
            if row is not None and self.timing.clock.day(now) <= self.timing.clock.day(row[1]):
                continue  # Preserve today's saved allowance, including captured larger balances.
            self.connection.execute('''INSERT INTO public.items(player_id,item_code,quantity,recovered_at)
                VALUES (%s,%s,%s,%s) ON CONFLICT(player_id,item_code) DO UPDATE
                SET quantity=EXCLUDED.quantity,recovered_at=EXCLUDED.recovered_at''',
                (player_id, item['ItemCode'], cap, now))

    def mirror(self, player_id):
        self.connection.execute('''INSERT INTO public.items(player_id,item_code,quantity,recovered_at)
            SELECT player_id,%s,value,updated_at FROM public.player_stamina
            WHERE player_id=%s AND kind='normal'
            ON CONFLICT(player_id,item_code) DO UPDATE
            SET quantity=EXCLUDED.quantity,recovered_at=EXCLUDED.recovered_at
            WHERE (items.quantity,items.recovered_at) IS DISTINCT FROM
                  (EXCLUDED.quantity,EXCLUDED.recovered_at)''', (STAMINA_ITEM, player_id))

    def recover(self, player_id, item_code, count, now):
        with self.repo.transaction(player_id):
            if item_code in self.stones:
                return self.recover_stone(player_id, item_code, count, now)
            item = self.items.get(item_code)
            if item is None or item['ItemBehaviourType'] not in (22, 23) or item['Param1'] <= 0:
                raise TimeBusinessError('local_stamina_recovery_item_invalid', 400)
            self.timing.refresh(player_id, now)
            now = self.timing._effective_now(player_id, now)
            row = self.connection.execute('''SELECT value,updated_at FROM public.player_stamina
                WHERE player_id=%s AND kind='normal' ''', (player_id,)).fetchone()
            if row is None:
                raise TimeBusinessError('local_stamina_state_missing', 503)
            value, updated_at = row
            gain = item['Param1'] * count
            if value + gain > self.timing.clock.stamina_limit:
                raise TimeBusinessError('local_stamina_limit_exceeded')
            changes = {item_code: -count, STAMINA_ITEM: gain}
            if item['ItemBehaviourType'] == 23:
                changes[self.counter] = -count
            for code in changes:
                if changes[code] > 0:
                    continue
                balance = self.connection.execute('''SELECT quantity FROM public.items
                    WHERE player_id=%s AND item_code=%s''', (player_id, code)).fetchone()
                if balance is None or balance[0] < count:
                    error = ('local_stamina_daily_limit_exceeded' if code == self.counter
                             else 'local_stamina_insufficient_items')
                    raise TimeBusinessError(error)
            # The protocol has no request ID; identical bodies can be deliberate
            # consecutive uses. Give each accepted operation its own ledger key.
            self.repo.apply_item_changes(player_id, 'stamina:' + uuid4().hex, changes)
            level = self.connection.execute('SELECT level FROM public.players WHERE player_id=%s',
                                            (player_id,)).fetchone()[0]
            if value + gain >= self.timing.level_caps[level]:
                updated_at = now
            self.connection.execute('''UPDATE public.player_stamina SET value=%s,updated_at=%s
                WHERE player_id=%s AND kind='normal' ''', (value + gain, updated_at, player_id))
            self.mirror(player_id)
            # RecoveredAt is the reset anchor for free food and the shared quota.
            counters = [code for code in changes if self.items[code]['ItemBehaviourType'] in (22, 24)]
            self.connection.execute('''UPDATE public.items SET recovered_at=%s
                WHERE player_id=%s AND item_code=ANY(%s)''', (now, player_id, counters))
            self.timing.event(player_id, 57, now, values=(str(item_code),), amount=count)
            return set(changes)

    def recover_stone(self, player_id, item_code, amount, now):
        # Caller already holds the player lock. Count is the quoted stone price,
        # unlike food requests where Count is the number of consumables.
        if self.stone_item is None or not self.stone_prices or self.stone_item['Param1'] <= 0:
            raise TimeBusinessError('local_stamina_stone_configuration_missing', 503)
        self.timing.refresh(player_id, now)
        now = self.timing._effective_now(player_id, now)
        counter = self.stone_item['ItemCode']
        quota = self.connection.execute('''SELECT quantity FROM public.items
            WHERE player_id=%s AND item_code=%s''', (player_id, counter)).fetchone()
        if quota is None:
            raise TimeBusinessError('local_stamina_stone_state_missing', 503)
        limit = max(self.stone_prices)
        remaining = quota[0]
        if not 0 <= remaining <= limit:
            raise TimeBusinessError('local_stamina_stone_state_invalid', 503)
        if remaining == 0:
            raise TimeBusinessError('local_stamina_daily_limit_exceeded')
        expected = self.stone_prices[limit - remaining + 1]
        if amount != expected:
            raise TimeBusinessError('local_stamina_stone_price_mismatch')
        row = self.connection.execute('''SELECT value,updated_at FROM public.player_stamina
            WHERE player_id=%s AND kind='normal' ''', (player_id,)).fetchone()
        if row is None:
            raise TimeBusinessError('local_stamina_state_missing', 503)
        value, updated_at = row
        gain = self.stone_item['Param1']  # One stone purchase always restores one configured batch.
        if value + gain > self.timing.clock.stamina_limit:
            raise TimeBusinessError('local_stamina_limit_exceeded')
        balance = self.connection.execute('''SELECT quantity FROM public.items
            WHERE player_id=%s AND item_code=%s''', (player_id, item_code)).fetchone()
        if balance is None or balance[0] < expected:
            raise TimeBusinessError('local_stamina_insufficient_items')
        changes = {item_code: -expected, counter: -1, STAMINA_ITEM: gain}
        self.repo.apply_item_changes(player_id, 'stamina:' + uuid4().hex, changes)
        level = self.connection.execute('SELECT level FROM public.players WHERE player_id=%s',
                                        (player_id,)).fetchone()[0]
        if value + gain >= self.timing.level_caps[level]:
            updated_at = now
        self.connection.execute('''UPDATE public.player_stamina SET value=%s,updated_at=%s
            WHERE player_id=%s AND kind='normal' ''', (value + gain, updated_at, player_id))
        self.mirror(player_id)
        self.connection.execute('''UPDATE public.items SET recovered_at=%s
            WHERE player_id=%s AND item_code=%s''', (now, player_id, counter))
        self.timing.event(player_id, 57, now, values=(str(item_code),), amount=expected)
        return set(changes)
