"""Validate the owned box-lottery progress without granting captured rewards."""
from .player_protocol import InvalidPlayerData, collection, integer, record
from psycopg.types.json import Jsonb


def box_lotteries(registry, values):
    result, codes = [], set()
    for value in collection(values, 'BoxLotteries'):
        row = record(registry, 'BoxLotteryInfo', value)
        code = integer(row['BoxLotteryCode'], 'BoxLotteryCode')
        current = integer(row['CurrentSheetNo'], 'CurrentSheetNo')
        if code <= 0 or code in codes or not 0 <= current <= 2**31 - 1:
            raise InvalidPlayerData('Invalid box lottery code or current sheet')
        codes.add(code)
        sheets, keys = [], set()
        for value in collection(row['BoxLotterySheets'], 'BoxLotterySheets'):
            sheet = record(registry, 'BoxLotterySheetInfo', value)
            number = integer(sheet['SheetNo'], 'SheetNo')
            index = integer(sheet['LineupIndex'], 'LineupIndex')
            count = integer(sheet['GetCount'], 'GetCount')
            if any(not 0 <= n <= 2**31 - 1 for n in (number, index, count)):
                raise InvalidPlayerData('Invalid box lottery sheet progress')
            if (number, index) in keys:
                raise InvalidPlayerData('Duplicate box lottery sheet lineup')
            keys.add((number, index))
            sheets.append([number, index, count])
        result.append([code, current, sorted(sheets)])
    return sorted(result, key=lambda row: row[0])


class BoxLotteryStore:
    """The caller holds the player's transaction/row lock across draw and grants."""
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection

    def load(self, player_id):
        row = self.connection.execute('SELECT box_lotteries FROM public.players WHERE player_id=%s',
                                      (player_id,)).fetchone()
        if row is None:
            raise LookupError('Player not initialized')
        return box_lotteries(self.repo.registry, row[0] if row[0] is not None else [])

    def save(self, player_id, values):
        values = box_lotteries(self.repo.registry, values)
        self.connection.execute('UPDATE public.players SET box_lotteries=%s WHERE player_id=%s',
                                (Jsonb(values), player_id))
        self.repo._touch(player_id)

    def initialize(self, player_id, catalog):
        values = self.load(player_id)
        known, changed = {r[0] for r in values}, False
        for row in values:
            if row[0] in catalog.pools:
                if row[1] == 0 and not row[2]:
                    row[1], changed = 1, True
                catalog.progress(row)
        for code in sorted(catalog.pools.keys() - known):
            values.append([code, 1, []])
            changed = True
        values.sort(key=lambda row: row[0])
        if changed:
            self.save(player_id, values)
        return values
