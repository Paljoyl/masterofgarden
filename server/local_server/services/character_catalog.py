"""Cultivation rules from verified TW master data stored in public."""
from collections import defaultdict

from ..protocol import LocalError


class CharacterCatalog:
    def __init__(self, connection):
        data = dict(connection.execute('SELECT name,data FROM public.character_definitions').fetchall())
        def rows(name):
            value = data.get(name)
            if not isinstance(value, list) or not value:
                raise LocalError('local_character_master_unavailable', 503)
            return value
        for name, values in data.items():
            if name not in {'character_master', 'character_exp_master', 'character_rarity_master',
                            'character_limit_break_master', 'equipment_group_master',
                            'equipment_master', 'equipment_composition_master'}:
                continue
            if not isinstance(values, list) or any(not isinstance(r, dict) or
                    any(type(v) is not int or v < 0 for v in r.values()) for r in values):
                raise LocalError('local_character_definition_invalid', 503)
        self.characters = {r['Code']: r for r in rows('character_master')}
        self.curves = defaultdict(list)
        for row in rows('character_exp_master'):
            self.curves[row['Code']].append(row)
        for curve in self.curves.values():
            curve.sort(key=lambda r: r['Level'])
            if (curve[0]['TotalExp'] != 0 or [r['Level'] for r in curve] != list(range(1, len(curve) + 1))
                    or any(a['TotalExp'] >= b['TotalExp'] for a, b in zip(curve, curve[1:]))):
                raise LocalError('local_character_exp_definition_invalid', 503)
        self.rarities = {(r['CharacterCode'], r['Rarity']): r for r in rows('character_rarity_master')}
        self.phases = {(r['Code'], r['Phase']): r for r in rows('character_limit_break_master')}
        self.groups = {(r['Code'], r['Rank']): r for r in rows('equipment_group_master')}
        self.equipment = {r['ItemCode']: r for r in rows('equipment_master')}
        self.recipes = {r['ItemCode']: r for r in rows('equipment_composition_master')}
        self.exp_items = {r['ItemCode']: r['Param1'] for r in rows('general_item_master') if r['ItemBehaviourType'] == 2}
        currencies = [r['ItemCode'] for r in rows('money_item_master') if r['ItemBehaviourType'] == 4]
        common = [r['ItemCode'] for r in rows('character_enhancement_item_master') if r['ItemBehaviourType'] == 11]
        if len(currencies) != 1 or len(common) != 1 or any(type(v) is not int or v <= 0 for v in self.exp_items.values()):
            raise LocalError('local_character_item_definition_invalid', 503)
        self.currency, self.common_limit_item = currencies[0], common[0]
        settings = {r['Key']: r['Value'] for r in rows('game_setting_master')}
        try:
            self.max_level = int(settings['CHARACTER_MAX_LEVEL'][0])
            self.max_rank = int(settings['CHARACTER_MAX_RANK'][0])
            self.max_rarity = int(settings['CHARACTER_MAX_RARITY'][0])
            self.max_phase = int(settings['CHARACTER_MAX_LIMIT_BREAK'][0])
            self.exchange_count = int(settings['LIMIT_BREAK_ITEM_EXCHANGE_COUNT'][0])
            if min(self.max_level, self.max_rank, self.max_rarity, self.max_phase, self.exchange_count) <= 0:
                raise ValueError()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LocalError('local_character_setting_invalid', 503) from exc

    def definition(self, table, key):
        row = table.get(key)
        if row is None:
            raise LocalError('local_character_definition_not_found', 503)
        return row

    def curve(self, character, user_level):
        master = self.definition(self.characters, character['Code'])
        curve = self.curves.get(master['CharacterExpCode'])
        if not curve:
            raise LocalError('local_character_exp_definition_invalid', 503)
        # Verified CharacterSharedLogic.GetCharacterLevelCap at RVA 0x12A9100.
        cap = min(user_level + character['Rarity'] - 1, self.max_level, curve[-1]['Level'])
        eligible = [r for r in curve if r['Level'] <= cap]
        if not eligible:
            raise LocalError('local_character_level_state_invalid', 409)
        # GetExpAndLevel (RVA 0x12A9720) retains partial exp at the cap,
        # limited to the next level's threshold minus one.
        next_level = next((r for r in curve if r['Level'] == cap + 1), None)
        limit = next_level['TotalExp'] - 1 if next_level else curve[-1]['TotalExp']
        return eligible, limit


class EquipmentPlan:
    """Plan recursive crafting against one shared inventory, without writing partial costs."""
    def __init__(self, catalog, items):
        self.catalog = catalog
        self.initial = {r[0]: r[1] for r in items}
        self.stock = dict(self.initial)

    def consume(self, code, amount=1, trail=()):
        from PostgreSQL.players import InsufficientItems
        available = min(self.stock.get(code, 0), amount)
        self.stock[code] = self.stock.get(code, 0) - available
        missing = amount - available
        if not missing:
            return
        if code not in self.catalog.recipes:
            raise InsufficientItems('Insufficient equipment materials')
        self.craft(code, missing, trail)
        self.stock[code] -= missing

    def craft(self, code, amount=1, trail=()):
        if code in trail or len(trail) >= 16:
            raise LocalError('local_equipment_recipe_invalid', 503)
        row = self.catalog.recipes.get(code)
        if row is None:
            raise LocalError('local_equipment_recipe_not_found', 404)
        self.catalog.definition(self.catalog.equipment, code)
        materials = [(row[f'MaterialEquipmentCode{i}'], row[f'MaterialAmount{i}']) for i in range(1, 5)]
        if not any(c and n > 0 for c, n in materials) or row['CurrencyAmount'] < 0:
            raise LocalError('local_equipment_recipe_invalid', 503)
        for material, count in materials:
            if material or count:
                if material <= 0 or count <= 0:
                    raise LocalError('local_equipment_recipe_invalid', 503)
                self.consume(material, count * amount, (*trail, code))
        if row['CurrencyAmount']:
            self.consume(self.catalog.currency, row['CurrencyAmount'] * amount, (*trail, code))
        self.stock[code] = self.stock.get(code, 0) + amount

    def changes(self):
        return {c: self.stock[c] - self.initial.get(c, 0) for c in self.stock
                if self.stock[c] != self.initial.get(c, 0)}
