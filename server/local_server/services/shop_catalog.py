"""Verified TW client shop definitions, independent of official player purchase state."""
from collections import defaultdict
from datetime import datetime, timezone

from PostgreSQL.game_time import GameTime, unix
from ..protocol import LocalError


class ShopCatalog:
    def __init__(self, connection):
        self.data = dict(connection.execute('SELECT name,data FROM public.shop_definitions').fetchall())
        self.shops = self.index('shop_master')
        self.packages = self.index('shop_package_master')
        self.payments = self.index('shop_payment_master')
        self.lineups = self.index('shop_lineup_master')
        self.options = self.group('shop_lineup_lottery_master', 'ShopLineupCode')
        self.extras = self.group('shop_additional_content_master', 'Code')
        self.packs = self.group('pack_item_content_master', 'PackItemCode')
        self.links = {r['ProductId']: r for r in self.load('shop_link_product_master')}
        self.characters = self.index('character_master')
        self.honors = self.index('honor_master')
        self.passes = self.index('shop_pass_master')
        self.battle_passes = self.index('battle_pass_master')
        self.schedules = {str(r['Code']): r for r in self.load('schedule_master')}
        try:
            self.clock = GameTime(self.load('game_setting_master'))
        except ValueError as exc:
            raise LocalError('local_shop_time_configuration_invalid', 503) from exc
        self.levels = self.load('player_exp_master')
        self.specific_levels = self.index('specific_user_level_master')
        self.update_costs = self.group('shop_lineup_update_cost_master', 'ShopCode')

    def load(self, name):
        rows = self.data.get(name)
        if not isinstance(rows, list):
            raise LocalError('local_shop_master_unavailable', 503)
        return rows

    def index(self, name):
        return {r['Code']: r for r in self.load(name)}

    def group(self, name, key):
        result = defaultdict(list)
        for row in self.load(name):
            result[row[key]].append(row)
        return result

    def active(self, row, now):
        code = str(row.get('ScheduleCode') or '')
        if not code:
            return True
        schedule = self.schedules.get(code)
        return bool(schedule and schedule['Type'] == 0
                    and unix(schedule['StartAt']) <= now < unix(schedule['EndAt']))

    def period(self, reset, now):
        if reset == 1:
            return self.clock.day(now)
        if reset == 2:
            return self.clock.week(now)
        if reset == 3:
            dt = datetime.fromtimestamp(now - self.clock.day_offset, timezone.utc)
            return dt.year * 12 + dt.month
        return 0

    def expiry(self, row):
        from msgpack import Timestamp
        schedule = self.schedules.get(str(row.get('ScheduleCode') or ''))
        return Timestamp(unix(schedule['EndAt']), 0) if schedule and schedule['Type'] == 0 else None

    def rewards(self, additional_code):
        if additional_code and additional_code not in self.extras:
            raise LocalError('local_shop_reward_definition_not_found', 503)
        return [[r['InventoryType'], r['InventoryCode'], r['Amount'], r['SortOrder']]
                for r in self.extras.get(additional_code, ())]

    def expand(self, rewards, depth=0):
        if depth > 8:
            raise LocalError('local_shop_reward_definition_invalid', 503)
        result = []
        for kind, code, amount, priority in rewards:
            if kind == 9:
                contents = self.packs.get(code)
                if not contents:
                    raise LocalError('local_shop_pack_definition_not_found', 503)
                result.extend(self.expand([[r['InventoryType'], r['InventoryCode'], r['Count'] * amount, priority]
                                           for r in contents], depth + 1))
            else:
                result.append([kind, code, amount, priority])
        return result
