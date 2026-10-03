"""Installed World Tree rotation, rental groups and local NPC opponents."""
from datetime import datetime
from secrets import choice

from ..protocol import LocalError, integer, sequence


CLIMBING_PARTY_COUNT = 5  # Installed PARTY_COUNT; battles select party numbers 1 and 2.


class ClimbingCatalog:
    def __init__(self, connection):
        data = dict(connection.execute('SELECT name,data FROM public.climbing_definitions').fetchall())
        try:
            self.masters = {r['Code']: r for r in data['climbing_master']}
            self.floors = {(r['GroupCode'], r['FloorNumber']): r for r in data['climbing_floor_master']}
            self.dummies = {r['Code']: r for r in data['climbing_dummy_character_master']}
            self.parties = data['climbing_dummy_party_master']
            self.rentals = data['climbing_rental_character_group_master']
            self.attributes = {r['Code']: r['Attribute'] for r in data['climbing_character_attributes']}
            self.settings = {r['Key']: r['Value'] for r in data['climbing_settings']}
            self.start_at = int(datetime.strptime(self.settings['CLIMBING_START_TIME'][0],
                '%Y/%m/%d %H:%M:%S %z').timestamp())
            self.max_floor = int(self.settings['CLIMBING_MAX_FLOOR'][0])
            self.max_rematch = int(self.settings['CLIMBING_CONTINUE_MAX_COUNT'][0])
            self.sync_count = int(self.settings['CLIMBING_LEVEL_SYNC_TARGET_CHARACTER_COUNT'][0])
            if self.sync_count <= 0 or not self.masters:
                raise ValueError()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LocalError('local_climbing_configuration_invalid', 503) from exc

    def current(self, timing, now):
        if now < self.start_at:
            raise LocalError('local_climbing_outside_schedule', 409)
        # Native ConvertToClimbingWeekNumber uses EndOfWeekCount, then +1 modulo 4.
        week = timing.clock.week(now)
        rotation = (week - timing.clock.week(self.start_at) + 1) % 4
        master = next((r for r in self.masters.values() if r['WeekNumber'] == rotation), None)
        if master is None:
            raise LocalError('local_climbing_rotation_invalid', 503)
        return week, master

    def floor(self, master, number):
        row = self.floors.get((master['FloorGroupCode'], number))
        if row is None:
            raise LocalError('local_climbing_floor_not_found', 404)
        return row

    def rental_codes(self, master):
        return {r['RentalCharacterCode'] for r in self.rentals
                if r['Code'] == master['ClimbingRentalCharacterGroupCode']}

    def canonical_rentals(self, protocol, values, master):
        seen, result = set(), []
        for value in sequence(values, maximum=5):
            row = protocol.fields('RentalCharacterInfo', value, strict=True)
            code = integer(row['RentalCharacterCode'], minimum=1)
            if code not in self.rental_codes(master):
                raise LocalError('local_climbing_rental_unavailable', 409)
            if code in seen:
                raise LocalError('duplicate_party_rental')
            seen.add(code)
            result.append([code, integer(row['SwitchableCharacterIndex'], maximum=2**31 - 1)])
        return result

    def matching(self, protocol, master, state, number, previous=None):
        candidates = [r for r in self.parties if r['FloorStart'] <= number <= r['FloorEnd']
                      and r['Attribute'] == master['Attribute']]
        alternatives = [r for r in candidates if 'local-climbing-npc:' + str(r['Code']) != previous]
        if not candidates:
            raise LocalError('local_climbing_enemy_configuration_missing', 503)
        selected = choice(alternatives or candidates)
        parties = []
        for index, key in enumerate(('DummyCharacterCodes', 'DummyCharacterCodes2'), 1):
            members, equipment = [], []
            for code in selected[key]:
                character = self.dummies[code]
                members.append([[character['CharacterCode'], character['Rarity']], 0])
                for slot, magic in enumerate(character['MagicItems']):
                    effects = [[magic['Code'], n + 1, effect['Code']] for n, effect in enumerate(magic['Effects'])]
                    equipment.append([character['CharacterCode'], slot, [magic['Code'], magic['Level'], effects, 0]])
            parties.append([index, members, equipment])
        levels = sorted((r[1] for r in state['Characters']), reverse=True)
        sync_level = levels[min(self.sync_count, len(levels)) - 1] if levels else 1
        return ['local-climbing-npc:' + str(selected['Code']), number, sync_level, parties]
