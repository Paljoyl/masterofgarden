"""Player levels derived from the client's cumulative experience curve."""
from bisect import bisect_right

from .player_protocol import InvalidPlayerData, integer


# TW general_item_master: ItemBehaviourType.PlayerExp (0).
PLAYER_EXPERIENCE_ITEM = 390000001


class PlayerProgression:
    def __init__(self, rows):
        rows = sorted(rows, key=lambda row: row['Level'])
        self.levels = [integer(row['Level'], 'player level') for row in rows]
        self.thresholds = [integer(row['TotalExp'], 'player experience threshold') for row in rows]
        if (not rows or self.levels[0] != 1 or self.thresholds[0] != 0
                or any(b <= a for a, b in zip(self.levels, self.levels[1:]))
                or any(b <= a for a, b in zip(self.thresholds, self.thresholds[1:]))):
            raise InvalidPlayerData('Invalid player experience curve')

    def level(self, experience):
        experience = integer(experience, 'player experience')
        if experience < 0:
            raise InvalidPlayerData('Negative player experience')
        return self.levels[bisect_right(self.thresholds, experience) - 1]
