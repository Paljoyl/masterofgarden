"""Battle-pass rewards and paid level purchases under the existing player lock."""
from collections import defaultdict

from .timed import TimeBusinessError


class BattlePassStore:
    def __init__(self, repository, timing):
        self.repo, self.timing = repository, timing
        self.connection = repository.connection
        self.levels = defaultdict(list)
        for row in timing.data.get('battle_pass_level_master', []):
            self.levels[row['BattlePassCode']].append(row)
        settings = {r['Key']: r['Value'] for r in timing.data['game_setting_master']}
        values = settings.get('BATTLE_PASS_LEVEL_UP_POINT')
        self.level_points = int(values[0]) if values else 0
        if self.level_points <= 0:
            raise TimeBusinessError('local_battle_pass_configuration_invalid', 503)

    def prepare(self, player_id, code, now):
        self.timing.refresh(player_id, now)
        now = self.timing._effective_now(player_id, now)
        definition = self.timing.index['battle_pass_master'].get(code)
        if definition is None:
            raise TimeBusinessError('local_battle_pass_not_found', 404)
        if not self.timing.active(definition['ScheduleCode'], now):
            raise TimeBusinessError('local_battle_pass_not_active')
        levels = sorted(self.levels.get(code, []), key=lambda r: r['Level'])
        if not levels or [r['Level'] for r in levels] != list(range(1, len(levels) + 1)):
            raise TimeBusinessError('local_battle_pass_level_configuration_invalid', 503)
        row = self.connection.execute('''SELECT total_point,normal_received_level,
            special_received_level,is_purchased FROM public.player_battle_passes
            WHERE player_id=%s AND code=%s''', (player_id, code)).fetchone()
        if row is None or any(n < 0 for n in row[:3]) or any(n > len(levels) for n in row[1:3]):
            raise TimeBusinessError('local_battle_pass_state_invalid', 503)
        # BattlePassSharedLogic.CalculateLevel (client RVA 0x12A2080):
        # TotalPoint / BattlePassLevelUpPoint + 1. Level one is free.
        level = min(row[0] // self.level_points + 1, len(levels))
        return now, levels, row, level

    def receive(self, player_id, code, now):
        now, levels, (total, normal, special, purchased), level = self.prepare(player_id, code, now)
        changed, rewards = set(), []
        for track, received, enabled in (('Normal', normal, True), ('Special', special, purchased)):
            if not enabled or received >= level:
                continue
            reward_codes = [r[track + 'RewardCode'] for r in levels
                            if received < r['Level'] <= level and r[track + 'RewardCode']]
            if reward_codes:
                changed |= self.timing._grant(player_id,
                    f'battle-pass:{code}:{track}:{received}:{level}', reward_codes, now)
                # Keep pack icons as configured in RewardInfo; _grant expands
                # their contents into the actual inventory in this transaction.
                for reward_code in reward_codes:
                    rewards.extend(sorted(self.timing.rewards[reward_code],
                                          key=lambda r: r['DisplayPriority']))
        self.connection.execute('''UPDATE public.player_battle_passes
            SET normal_received_level=GREATEST(normal_received_level,%s),
                special_received_level=GREATEST(special_received_level,%s)
            WHERE player_id=%s AND code=%s''', (level, level if purchased else special, player_id, code))
        self.repo._touch(player_id)
        return changed, rewards

    def purchase_levels(self, player_id, code, count, now):
        now, levels, (total, normal, special, purchased), level = self.prepare(player_id, code, now)
        if count > len(levels) - level:
            raise TimeBusinessError('local_battle_pass_level_limit')
        # The timed configuration intentionally contains only time settings;
        # use the full existing shop settings for the client's paid-stone price.
        data = self.connection.execute("SELECT data FROM public.shop_definitions WHERE name='game_setting_master'").fetchone()
        settings = {r['Key']: r['Value'] for r in data[0]} if data else {}
        price = settings.get('BATTLE_PASS_LEVEL_UP_STONE_COUNT')
        price = int(price[0]) if price else 0
        if price <= 0:
            raise TimeBusinessError('local_battle_pass_purchase_configuration_invalid', 503)
        remaining = price * count
        # BattlePassLevelPurchaseView reads UserModel.PaidStone (offset 0xB0),
        # not TotalStone. TW PC paid inventory includes both paid pools.
        paid_codes = (990000003, 990000002)
        balances = dict(self.connection.execute('''SELECT item_code,quantity FROM public.items
            WHERE player_id=%s AND item_code=ANY(%s)''', (player_id, list(paid_codes))).fetchall())
        changes = {}
        for item in paid_codes:
            amount = min(balances.get(item, 0), remaining)
            if amount:
                changes[item] = -amount
                remaining -= amount
        if remaining:
            raise TimeBusinessError('local_battle_pass_insufficient_paid_stones')
        points = total + count * self.level_points
        if points > 2**31 - 1:
            raise TimeBusinessError('local_battle_pass_state_invalid', 503)
        self.repo.apply_item_changes(player_id, f'battle-pass-level:{code}:{total}:{count}', changes)
        # Purchased levels preserve partial progress, do not spend the weekly
        # mission-point allowance, and do not unlock premium entitlement.
        self.connection.execute('''UPDATE public.player_battle_passes SET total_point=%s
            WHERE player_id=%s AND code=%s''', (points, player_id, code))
        for item, amount in changes.items():
            self.timing.event(player_id, 57, now, values=(str(item),), amount=-amount)
        self.repo._touch(player_id)
        return set(changes)
