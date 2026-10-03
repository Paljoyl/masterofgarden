"""TW box lineups, level thresholds and expiry switches from public master data."""
from collections import defaultdict

from PostgreSQL.game_time import unix
from ..protocol import LocalError

# OpenItemBoxController.UpdateData (TW PC RVA 0xCC7E30) clamps to 100.
# ContinuousOpen controls inclusion in the client's bulk-opening UI; it does
# not restrict the quantity accepted by its individual box dialog.
MAX_OPEN_COUNT = 100


def configuration_error():
    return LocalError('local_box_configuration_invalid', 503)


def number(value, minimum=1):
    if type(value) is not int or not minimum <= value < 2**63:
        raise configuration_error()
    return value


class BoxItemCatalog:
    def __init__(self, data):
        required = ('box_item_master', 'box_item_level_lineup_master',
                    'box_item_lottery_master', 'box_item_schedule_master', 'box_item_reward_items')
        if any(not isinstance(data.get(name), list) for name in required):
            raise LocalError('local_box_configuration_missing', 503)
        try:
            self.boxes = {number(row['ItemCode']): row for row in data['box_item_master']}
            if not self.boxes or len(self.boxes) != len(data['box_item_master']):
                raise configuration_error()
            self.schedules = {row['Code']: row for row in data['box_item_schedule_master']}
            self.items = {number(row['ItemCode']) for row in data['box_item_reward_items']}
            self.levels = defaultdict(dict)
            self.lotteries = defaultdict(list)
            for row in data['box_item_level_lineup_master']:
                code, level = number(row['Code']), number(row['LowerLimitUserLevel'])
                if level in self.levels[code]:
                    raise configuration_error()
                self.levels[code][level] = number(row['BoxItemLotteryCode'])
            for row in data['box_item_lottery_master']:
                code, item = number(row['Code']), number(row['ItemCode'])
                amount, weight = number(row['Amount']), number(row['Rate'], 0)
                if item not in self.items:
                    raise configuration_error()
                self.lotteries[code].append((item, amount, weight))
            for box in self.boxes.values():
                if type(box['ItemBehaviourType']) is not int or box['ItemBehaviourType'] not in (34, 35):
                    raise configuration_error()
                self._require_lineup(number(box['LineupCode']))
                if box['LineupSwitchedScheduleCode']:
                    schedule = self.schedules.get(box['LineupSwitchedScheduleCode'])
                    if (schedule is None or schedule['Type'] != 0
                            or unix(schedule['StartAt']) >= unix(schedule['EndAt'])):
                        raise configuration_error()
                    self._require_lineup(number(box['SwitchedLineupCode']))
            for levels in self.levels.values():
                for lottery in levels.values():
                    if not self.lotteries.get(lottery) or not sum(r[2] for r in self.lotteries[lottery]):
                        raise configuration_error()
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
            raise configuration_error() from exc

    def _require_lineup(self, code):
        if not self.levels.get(code):
            raise configuration_error()

    def lineup(self, code, level, now):
        box = self.boxes.get(code)
        if box is None:
            raise LocalError('local_box_not_found', 404)
        if box['ItemBehaviourType'] != 34:
            raise LocalError('local_box_not_manually_openable', 409)
        lineup = box['LineupCode']
        schedule = self.schedules.get(box['LineupSwitchedScheduleCode'])
        # SwitchedLineupCode is the event lineup while its schedule is active.
        # Outside that window the normal lineup provides the fallback reward
        # (e.g. apple candy becomes coins after its stamina event expires).
        if schedule and unix(schedule['StartAt']) <= now < unix(schedule['EndAt']):
            lineup = box['SwitchedLineupCode']
        eligible = [threshold for threshold in self.levels[lineup] if threshold <= level]
        if not eligible:
            raise LocalError('local_box_player_level_too_low', 409)
        return self.lotteries[self.levels[lineup][max(eligible)]]
