"""Local character progression and equipment mutations under the owned-player lock."""
from collections import defaultdict
from uuid import uuid4

from PostgreSQL.players import InsufficientItems
from ..protocol import LocalError
from .character_catalog import CharacterCatalog, EquipmentPlan
from .inventory import inventory_update, total_battle_power


class CharacterService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None

    @property
    def catalog(self):
        if self._catalog is None:
            self._catalog = CharacterCatalog(self.repository.connection)
        return self._catalog

    @property
    def repository(self):
        if self.players.repository is None:
            raise LocalError('player_storage_unavailable', 503)
        return self.players.repository

    def character(self, state, code):
        value = next((r for r in state['Characters'] if r[0] == code), None)
        if value is None:
            raise LocalError('local_character_not_owned', 404)
        return self.protocol.fields('CharacterInfo', value)

    def favorite(self, request, changes):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            for code in changes:
                self.character(state, code)
            codes = self.repository.update_favorites(session.player_id, changes)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'FavoriteCharacterCodes': codes}

    def spend(self, player_id, changes):
        changes = {c: n for c, n in changes.items() if n}
        if changes:
            self.repository.apply_item_changes(player_id, 'character:' + uuid4().hex, changes)
            for code, delta in changes.items():
                if delta < 0:
                    self.progress_event(player_id, 57, values=(str(code),), amount=-delta)
        return set(changes)

    def progress_event(self, player_id, kind, *, values=(), amount=1):
        timing = self.players.timing
        if timing is not None and amount > 0:
            now = timing._effective_now(player_id, int(self.players.clock()))
            timing.event(player_id, kind, now, values=values, amount=amount)

    def response(self, session, changed, code=None, *, equipment=False):
        state = self.players._state(session.player_id)
        result = {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                  'StackItems': [r for r in state['StackItems'] if r[0] in changed],
                  'TotalBattlePower': total_battle_power(self.players, self.protocol, session)}
        if code is not None:
            result['CharacterInfo'] = next(r for r in state['Characters'] if r[0] == code)
        if equipment:
            result['Equipments'] = [r for r in state['Equipments'] if r[0] == code]
        return result

    def levelup(self, request, code, items):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            character = self.character(state, code)
            curve, exp_limit = self.catalog.curve(character, self.protocol.fields('UserInfo', state['User'])['Level'])
            if character['Level'] >= curve[-1]['Level'] or character['Exp'] >= curve[-1]['TotalExp']:
                raise LocalError('local_character_level_cap_reached', 409)
            gain = 0
            for item_code, count in items.items():
                if item_code not in self.catalog.exp_items:
                    raise LocalError('local_character_invalid_exp_item')
                gain += self.catalog.exp_items[item_code] * count
            experience = min(character['Exp'] + gain, exp_limit)
            level = max(r['Level'] for r in curve if r['TotalExp'] <= experience)
            changed = self.spend(session.player_id, {c: -n for c, n in items.items()})
            self.repository.update_character(session.player_id, code, level=level, experience=experience)
            self.progress_event(session.player_id, 9, amount=level - character['Level'])
            return self.response(session, changed, code)

    def levelup_selected(self, request, codes):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            stock = {r[0]: r[1] for r in state['StackItems']}
            used = defaultdict(int)
            user_level = self.protocol.fields('UserInfo', state['User'])['Level']
            for code in codes:
                character = self.character(state, code)
                curve, exp_limit = self.catalog.curve(character, user_level)
                needed = curve[-1]['TotalExp'] - character['Exp']
                if needed <= 0:
                    continue
                gain = 0
                # Largest items first without unnecessary waste, then one smallest
                # available item to finish the cap (same floor/ceiling client policy).
                options = sorted(self.catalog.exp_items.items(), key=lambda v: (-v[1], v[0]))
                for item, value in options:
                    count = min(stock.get(item, 0), (needed - gain) // value)
                    stock[item] = stock.get(item, 0) - count
                    used[item] += count
                    gain += count * value
                if gain < needed:
                    item = next((c for c, _ in reversed(options) if stock.get(c, 0)), None)
                    if item is not None:
                        stock[item] -= 1
                        used[item] += 1
                        gain += self.catalog.exp_items[item]
                if gain:
                    experience = min(character['Exp'] + gain, exp_limit)
                    level = max(r['Level'] for r in curve if r['TotalExp'] <= experience)
                    self.repository.update_character(session.player_id, code, level=level, experience=experience)
                    self.progress_event(session.player_id, 9, amount=level - character['Level'])
            changed = self.spend(session.player_id, {c: -n for c, n in used.items()})
            current = self.players._state(session.player_id)
            result = self.response(session, changed)
            result.pop('StackItems')
            result.update(Characters=[r for r in current['Characters'] if r[0] in codes],
                          InventoryUpdateInfo=inventory_update(self.protocol, current, changed))
            return result

    def rarityup(self, request, code):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            character = self.character(self.players._state(session.player_id), code)
            if character['Rarity'] >= self.catalog.max_rarity:
                raise LocalError('local_character_rarity_cap_reached', 409)
            master = self.catalog.definition(self.catalog.characters, code)
            target = character['Rarity'] + 1
            row = self.catalog.definition(self.catalog.rarities, (code, target))
            changes = defaultdict(int)
            changes[master['FragmentItemCode']] -= row['FragmentItemAmount']
            changes[self.catalog.currency] -= row['CurrencyAmount']
            changed = self.spend(session.player_id, changes)
            self.repository.update_character(session.player_id, code, rarity=target)
            self.progress_event(session.player_id, 12)
            self.progress_event(session.player_id, 13, values=(str(code),))
            return self.response(session, changed, code)

    def limitbreak(self, request, code, expected):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            character = self.character(state, code)
            if character['LimitBreak'] >= self.catalog.max_phase:
                raise LocalError('local_character_limit_break_cap_reached', 409)
            master = self.catalog.definition(self.catalog.characters, code)
            target = character['LimitBreak'] + 1
            row = self.catalog.definition(self.catalog.phases, (master['CharacterLimitBreakCode'], target))
            costs = defaultdict(int)
            costs[self.catalog.currency] += row['CurrencyAmount']
            for i in (2, 3):
                costs[row[f'Item{i}Code']] += row[f'Item{i}Amount']
            # The client may substitute common crystals for character-specific ones.
            specific, common = master['LimitBreakItemCode'], self.catalog.common_limit_item
            costs[specific] += expected.get(specific, 0)
            costs[common] += expected.get(common, 0)
            costs = {c: n for c, n in costs.items() if n}
            if (expected.get(specific, 0) + expected.get(common, 0) != row['ItemAmount'] or costs != expected):
                raise LocalError('local_character_consume_items_mismatch', 409)
            changed = self.spend(session.player_id, {c: -n for c, n in costs.items()})
            self.repository.update_character(session.player_id, code, limit_break=target)
            self.progress_event(session.player_id, 14)
            self.progress_event(session.player_id, 15, values=(str(code),))
            return self.response(session, changed, code)

    def equipment_codes(self, character):
        master = self.catalog.definition(self.catalog.characters, character['Code'])
        group = self.catalog.definition(self.catalog.groups, (master['EquipmentGroupCode'], character['Rank']))
        return {slot: group[f'EquipmentCode{slot}'] for slot in range(1, 7) if group[f'EquipmentCode{slot}']}

    def equip(self, request, code, slots=None):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            character = self.character(state, code)
            definitions = self.equipment_codes(character)
            occupied = {r[1] for r in state['Equipments'] if r[0] == code}
            plan = EquipmentPlan(self.catalog, state['StackItems'])
            selected = []
            for slot in (slots if slots is not None else sorted(definitions.keys() - occupied)):
                if slot in occupied:
                    raise LocalError('local_equipment_slot_occupied', 409)
                if slot not in definitions:
                    raise LocalError('local_equipment_slot_unavailable', 409)
                item = self.catalog.definition(self.catalog.equipment, definitions[slot])
                if character['Level'] < item['RequiredLevel']:
                    if slots is None:
                        continue
                    raise LocalError('local_equipment_level_required', 409)
                before = dict(plan.stock)
                try:
                    plan.consume(definitions[slot])
                except InsufficientItems:
                    if slots is not None:
                        raise
                    plan.stock = before
                    continue
                selected.append(slot)
            changed = self.spend(session.player_id, plan.changes())
            if selected:
                self.repository.set_character_equipment(session.player_id, code, sorted(occupied | set(selected)))
            result = self.response(session, changed, code if slots is None else None)
            result['Equipments'] = [[code, s] for s in sorted(occupied | set(selected))]
            return result

    def make_equipment(self, request, code):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            plan = EquipmentPlan(self.catalog, state['StackItems'])
            plan.craft(code)
            changed = self.spend(session.player_id, plan.changes())
            result = self.response(session, changed)
            result.pop('TotalBattlePower')
            return result

    def rankup(self, request, code, target):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            character = self.character(state, code)
            if not character['Rank'] < target <= self.catalog.max_rank:
                raise LocalError('local_character_rank_target_invalid', 409)
            rank_gain = target - character['Rank']
            plan = EquipmentPlan(self.catalog, state['StackItems'])
            occupied = {r[1] for r in state['Equipments'] if r[0] == code}
            while character['Rank'] < target:
                for slot, item_code in self.equipment_codes(character).items():
                    item = self.catalog.definition(self.catalog.equipment, item_code)
                    if character['Level'] < item['RequiredLevel']:
                        raise LocalError('local_equipment_level_required', 409)
                    if slot not in occupied:
                        plan.consume(item_code)
                character['Rank'] += 1
                self.equipment_codes(character)  # Target rank must exist too.
                occupied = set()
            changed = self.spend(session.player_id, plan.changes())
            self.repository.set_character_equipment(session.player_id, code, [])
            self.repository.update_character(session.player_id, code, rank=target)
            self.progress_event(session.player_id, 10, amount=rank_gain)
            self.progress_event(session.player_id, 11, values=(str(code),), amount=rank_gain)
            return self.response(session, changed, code)
