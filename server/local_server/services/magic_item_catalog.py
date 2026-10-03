"""Validated magic item pools from installed client master data."""
from collections import defaultdict

from ..protocol import LocalError


class MagicItemCatalog:
    def __init__(self, data):
        try:
            def rows(name):
                value = data[name]
                if not isinstance(value, list) or not value:
                    raise ValueError()
                return value

            def index(name, key, fields):
                result = {}
                for row in rows(name):
                    if any(type(row[f]) is not int or row[f] <= 0 for f in fields):
                        raise ValueError()
                    code = row[key]
                    if code in result:
                        raise ValueError()
                    result[code] = row
                return result

            self.items = index('magic_item_master', 'Code', ('Code', 'Rarity', 'AlternativeItemCode'))
            materials = index('magic_item_create_items', 'ItemCode', ('ItemCode',))
            effects = index('magic_item_effect_item_master', 'ItemCode', ('ItemCode',))
            recipes = index('magic_item_create_master', 'MagicItemCreateItemCode',
                            ('Code', 'MagicItemCreateItemCode', 'LotteryCode'))
            self.pools = defaultdict(list)
            seen = set()
            for row in rows('magic_item_create_lottery_master'):
                code, item, rate = (row[k] for k in ('Code', 'MagicItemCode', 'Rate'))
                if (any(type(v) is not int or v < 0 for v in (code, item, rate))
                        or code == 0 or item not in self.items or (code, item) in seen):
                    raise ValueError()
                seen.add((code, item))
                if rate:
                    self.pools[code].append((item, rate))
            self.recipes = {}
            for material, row in recipes.items():
                if material not in materials or not self.pools.get(row['LotteryCode']):
                    raise ValueError()
                self.recipes[material] = row['LotteryCode']
            if any(r['AlternativeItemCode'] not in effects or r['Rarity'] not in range(1, 6)
                   for r in self.items.values()):
                raise ValueError()
            settings = {r['Key']: r['Value'] for r in rows('magic_item_settings')}
            self.limit = int(settings['MAGIC_ITEM_LOTTERY_LIMIT'][0])
            if not 1 <= self.limit <= 1000:
                raise ValueError()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LocalError('local_magic_item_definition_invalid', 503) from exc

    def pool(self, material):
        code = self.recipes.get(material)
        if code is None:
            raise LocalError('local_magic_item_invalid_material')
        return self.pools[code]

    def draw(self, pool, randbelow):
        ticket = randbelow(sum(rate for _, rate in pool))
        for code, rate in pool:
            if ticket < rate:
                return self.items[code]
            ticket -= rate
        raise LocalError('local_magic_item_definition_invalid', 503)
