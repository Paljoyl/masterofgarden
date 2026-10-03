"""Enhancement costs and per-item level caps verified against the TW client."""
from collections import defaultdict

from ..protocol import LocalError


class MagicItemLevelUpCatalog:
    def __init__(self, data):
        try:
            def rows(name):
                value = data[name]
                if not isinstance(value, list) or not value or any(not isinstance(r, dict) for r in value):
                    raise ValueError()
                return value

            def number(row, field):
                value = row[field]
                if type(value) is not int or not 1 <= value < 2**63:
                    raise ValueError()
                return value

            materials = {number(r, 'ItemCode') for r in rows('magic_item_level_up_materials')}
            self.items, statuses = {}, defaultdict(set)
            for row in rows('magic_item_level_up_items'):
                code, rarity, status = (number(row, k) for k in ('Code', 'Rarity', 'MagicItemStatusCode'))
                if code in self.items or rarity not in range(1, 6):
                    raise ValueError()
                self.items[code] = (rarity, status)
            for row in rows('magic_item_level_up_status'):
                code, level = (number(row, k) for k in ('Code', 'Level'))
                if level in statuses[code]:
                    raise ValueError()
                statuses[code].add(level)
            self.caps = {}
            for code, levels in statuses.items():
                cap = max(levels)
                if cap > 1000 or levels != set(range(1, cap + 1)):
                    raise ValueError()
                self.caps[code] = cap
            self.steps = defaultdict(dict)
            for row in rows('magic_item_level_up_master'):
                rarity, level, item, count = (number(row, k) for k in ('Rarity', 'Level', 'ItemCode', 'Count'))
                if rarity not in range(1, 6) or level > 1000 or item not in materials or item in self.steps[rarity, level]:
                    raise ValueError()
                self.steps[rarity, level][item] = count
            for rarity, status in self.items.values():
                if status not in self.caps or any((rarity, level) not in self.steps
                        for level in range(1, self.caps[status])):
                    raise ValueError()
        except (KeyError, TypeError, ValueError) as exc:
            raise LocalError('local_magic_item_levelup_definition_invalid', 503) from exc

    def costs(self, code, current_level, add_level):
        definition = self.items.get(code)
        if definition is None:
            raise LocalError('local_magic_item_levelup_definition_missing', 503)
        rarity, status = definition
        cap = self.caps[status]
        if not 1 <= current_level < cap or current_level + add_level > cap:
            raise LocalError('local_magic_item_level_cap_reached', 409)
        # Client MagicItemEnhancementData (.ctor RVA 0x14511A0) accumulates costs
        # starting at the current level; max level comes from MagicItemStatusCode.
        result = defaultdict(int)
        for level in range(current_level, current_level + add_level):
            for item, amount in self.steps[rarity, level].items():
                result[item] += amount
        return dict(result)
