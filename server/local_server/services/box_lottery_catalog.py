"""Finite box stocks and repeatable final sheets from the installed TW catalog."""
from collections import defaultdict

from ..protocol import LocalError


def configuration_error():
    return LocalError('local_box_lottery_configuration_invalid', 503)


def number(value, minimum=1, maximum=2**63 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise configuration_error()
    return value


class BoxLotteryCatalog:
    def __init__(self, data):
        required = ('box_lottery_master', 'box_lottery_sheet_master',
                    'box_lottery_sheet_lineup_master', 'box_lottery_settings', 'box_lottery_events')
        if any(not isinstance(data.get(name), list) or not data[name] for name in required):
            raise LocalError('local_box_lottery_configuration_missing', 503)
        try:
            self.pools = {number(r['Code']): r for r in data['box_lottery_master']}
            if len(self.pools) != len(data['box_lottery_master']):
                raise configuration_error()
            settings = {r['Key']: r['Value'] for r in data['box_lottery_settings']}
            self.max_count = number(int(settings['BOX_LOTTERY_MULTIPLE_EXECUTE_MAX_COUNT'][0]),
                                    maximum=2**31 - 1)
            bindings = {number(r['BoxLotteryCode']) for r in data['box_lottery_events']}
            self.sheets, self.lineups = defaultdict(dict), defaultdict(dict)
            for row in data['box_lottery_sheet_lineup_master']:
                code = number(row['Code'])
                index = number(row['Index'], maximum=2**31 - 1)
                if index in self.lineups[code] or type(row['IsFeatured']) is not bool:
                    raise configuration_error()
                if row['RewardInventoryType'] != 2:
                    raise configuration_error()
                number(row['StockCount'], minimum=0, maximum=2**31 - 1)
                number(row['RewardInventoryCode'])
                number(row['RewardCount'])
                self.lineups[code][index] = row
            for row in data['box_lottery_sheet_master']:
                code = number(row['BoxLotteryCode'])
                sheet = number(row['SheetNo'], maximum=2**31 - 1)
                lineup = number(row['BoxLotterySheetLineupCode'])
                if code not in self.pools or sheet in self.sheets[code] or not self.lineups.get(lineup):
                    raise configuration_error()
                self.sheets[code][sheet] = lineup
            for code, pool in self.pools.items():
                if code not in bindings or pool['ConsumeInventoryType'] != 2:
                    raise configuration_error()
                number(pool['ConsumeInventoryCode'])
                number(pool['ConsumeInventoryCount'])
                sheets = self.sheets.get(code, {})
                if not sheets or sorted(sheets) != list(range(1, max(sheets) + 1)):
                    raise configuration_error()
                if any(not sum(r['StockCount'] for r in self.lineups[lineup].values())
                       for lineup in sheets.values()):
                    raise configuration_error()
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
            raise configuration_error() from exc

    def require(self, code):
        pool = self.pools.get(code)
        if pool is None:
            raise LocalError('local_box_lottery_not_found', 404)
        # Match the project's archived-event access policy: installed pools
        # remain usable after official dates, with their original ticket costs.
        return pool

    def lineup(self, code, number):
        self.require(code)
        sheets = self.sheets[code]
        # EventLotteryData uses the last configured sheet for later rounds.
        return self.lineups[sheets[min(number, max(sheets))]]

    def progress(self, box):
        code, current, sheets = box
        if current < 1:
            raise LocalError('local_box_lottery_state_invalid', 503)
        for sheet, index, count in sheets:
            if sheet < 1 or sheet > current:
                raise LocalError('local_box_lottery_state_invalid', 503)
            lineup = self.lineup(code, sheet)
            if index not in lineup or count > lineup[index]['StockCount']:
                raise LocalError('local_box_lottery_state_invalid', 503)
        return {index: count for sheet, index, count in sheets if sheet == current}
