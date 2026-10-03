"""Player-owned garden production and mutations under the aggregate transaction."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
import json
import secrets
import struct

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .game_time import timestamp, unix
from .player_protocol import record
from .timed import TimeBusinessError


class GardenStore:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection
        self.timing = repository.timing
        data = self.timing.data
        required = ('garden_building_master', 'garden_building_level_master', 'garden_settings',
                    'garden_product_setting_master', 'garden_inventory_product_master',
                    'garden_point_product_master', 'garden_point_conversion_master',
                    'garden_lottery_product_master', 'garden_search_lineup_master',
                    'garden_general_items', 'garden_item_behaviours', 'garden_unlock_rule')
        if any(name not in data for name in required):
            raise TimeBusinessError('local_garden_configuration_missing', 503)
        self.buildings = {r['Code']: r for r in data['garden_building_master']}
        self.levels = {(r['BuildingCode'], r['Level']): r for r in data['garden_building_level_master']}
        self.products = {r['Code']: r for r in data['garden_product_setting_master']}
        self.inventory_products = {r['Code']: r for r in data['garden_inventory_product_master']}
        self.point_products = {r['Code']: r for r in data['garden_point_product_master']}
        self.conversions = defaultdict(list)
        for r in data['garden_point_conversion_master']:
            self.conversions[r['Code']].append(r)
        self.settings = {r['Key']: r['Value'] for r in data['garden_settings']}
        self.items = {r['ItemCode']: r for r in data['garden_general_items']}
        self.behaviours = {r['ItemCode']: r['ItemBehaviourType'] for r in data['garden_item_behaviours']}
        self.resource_codes = {r['ItemBehaviourType']: r['ItemCode'] for r in self.items.values()}

    def initialize(self, player_id, now, home=None):
        """Import only the identity-bound home on first initialization."""
        inserted = self.connection.execute('''INSERT INTO public.player_gardens(player_id,checked_at)
            VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING player_id''', (player_id, now)).fetchone()
        if not inserted:
            return
        observed = {}
        if home and home.get('Garden'):
            info = record(self.repo.registry, 'GardenInfo', home['Garden'])
            count = info['HoldingWorkerCount']
            if type(count) is not int or not 0 <= count <= 2**31 - 1:
                raise TimeBusinessError('local_garden_seed_invalid', 503)
            self.connection.execute('UPDATE public.player_gardens SET holding_worker_count=%s WHERE player_id=%s',
                                    (count, player_id))
            for value in home.get('GardenBuildings') or []:
                r = record(self.repo.registry, 'GardenBuildingInfo', value)
                code, level, workers = r['GardenBuildingCode'], r['Level'], r['WorkerCount']
                if (code not in self.buildings or type(level) is not int or type(workers) is not int
                        or level < 0 or workers < 0 or (level and (code, level) not in self.levels)
                        or type(r['RoomUnlocked']) is not bool):
                    raise TimeBusinessError('local_garden_seed_invalid', 503)
                observed[code] = r
        for code, master in self.buildings.items():
            r = observed.get(code)
            level = r['Level'] if r else int(master['IsInitialInstalled'])
            at = min(now, unix(r['ReceivedAt'])) if r and r['ReceivedAt'] is not None else now
            self.connection.execute('''INSERT INTO public.player_garden_buildings
                (player_id,building_code,level,worker_count,received_at,lottery_checked_at,room_unlocked)
                VALUES (%s,%s,%s,%s,%s,%s,%s)''',
                (player_id, code, level, r['WorkerCount'] if r else 0,
                 at if level and master['ProductSettingCode'] else None,
                 at if level and master['ProductSettingCode'] else None, r['RoomUnlocked'] if r else False))
        if home:
            for room, codes in (home.get('RoomPlayedSituationCodes') or {}).items():
                for code in codes:
                    if any(r['RoomCode'] == int(room) and r['RoomSituationCode'] == code
                           for r in self.timing.data['room_schedule_master']):
                        self.connection.execute('''INSERT INTO public.player_room_situations
                            VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING''', (player_id, int(room), code, now))
        self._normalize_search(player_id)

    def _rows(self, player_id):
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute('SELECT * FROM public.player_garden_buildings WHERE player_id=%s ORDER BY building_code',
                           (player_id,))
            return {r['building_code']: r for r in cursor.fetchall()}

    def _eligible_search(self, player_id, row):
        master = self.buildings[row['building_code']]
        if not row['level'] or not master['SearchLineupCode']:
            return {}
        level = self.connection.execute('SELECT level FROM public.players WHERE player_id=%s', (player_id,)).fetchone()[0]
        return {code: r['InventoryType'] for r in self.timing.data['garden_search_lineup_master']
                if r['Code'] == master['SearchLineupCode'] and r['BuildingLevel'] <= row['level']
                and r['PlayerLevel'] <= level for code in r['InventoryCodes']}

    def _normalize_search(self, player_id):
        for row in self._rows(player_id).values():
            choices = self._eligible_search(player_id, row)
            if choices and row['search_inventory_code'] not in choices:
                code = min(choices)
                self.connection.execute('''UPDATE public.player_garden_buildings SET
                    search_inventory_type=%s,search_inventory_code=%s WHERE player_id=%s AND building_code=%s''',
                    (choices[code], code, player_id, row['building_code']))

    def _rate(self, row):
        setting = self.products.get(self.buildings[row['building_code']]['ProductSettingCode'])
        if setting is None or not row['level']:
            return None, None, Decimal(0)
        if setting['ProductionType'] == 0:
            product = self.inventory_products[setting['ProductCode']]
            rate = product['BaseCount'] * row['worker_count'] + product['AssuranceCount']
        else:
            product = self.point_products[setting['ProductCode']]
            # Mirror the client's float32 multiply/add at RVA 0x133E190.
            f32 = lambda value: struct.unpack('<f', struct.pack('<f', value))[0]
            rate = f32(f32(product['BasePoint'] * row['worker_count']) + product['AssurancePoint'])
        return setting, product, Decimal(str(rate))

    def _volume(self, row, now):
        setting, product, rate = self._rate(row)
        if setting is None:
            return Decimal(0)
        elapsed = max(0, now - (row['received_at'] if row['received_at'] is not None else now))
        return min(Decimal(product['ReceiveLimit']), row['stored_volume'] + Decimal(elapsed) * rate / 3600)

    def view(self, player_id, now):
        existing = self.connection.execute('SELECT holding_worker_count FROM public.player_gardens WHERE player_id=%s',
                                           (player_id,)).fetchone()
        if existing is None:
            # An unrelated state query must not consume the one-time home seed.
            return {'Garden': [0], 'GardenBuildings': [[code, int(master['IsInitialInstalled']), 0, None, False]
                    for code, master in sorted(self.buildings.items())], 'GardenSearchInventories': [],
                    'RoomPlayedSituationCodes': {}}
        rows = self._rows(player_id)
        buildings, searches = [], []
        for code, row in rows.items():
            _, _, rate = self._rate(row)
            at = row['received_at']
            if at is not None and rate:
                at -= int((row['stored_volume'] * 3600 / rate).to_integral_value(rounding=ROUND_CEILING))
            buildings.append([code, row['level'], row['worker_count'], timestamp(at) if at is not None else None,
                              row['room_unlocked']])
            if row['search_inventory_code']:
                searches.append([code, row['search_inventory_type'], row['search_inventory_code']])
        rooms = defaultdict(list)
        for room, code in self.connection.execute('''SELECT room_code,situation_code FROM public.player_room_situations
            WHERE player_id=%s ORDER BY room_code,situation_code''', (player_id,)).fetchall():
            rooms[room].append(code)
        return {'Garden': [existing[0]], 'GardenBuildings': buildings, 'GardenSearchInventories': searches,
                'RoomPlayedSituationCodes': dict(rooms)}

    def prepare(self, player_id, now):
        self.timing.refresh(player_id, now)
        now = self.timing._effective_now(player_id, now)
        self.initialize(player_id, now)
        checked = self.connection.execute('SELECT checked_at FROM public.player_gardens WHERE player_id=%s',
                                          (player_id,)).fetchone()[0]
        now = max(now, checked)
        if self.settings['PERMISSION_ACCESS_GARDEN'] != ['True']:
            raise TimeBusinessError('local_garden_disabled')
        for rule in self.timing.data['garden_unlock_rule']:
            if rule['Rule'] != 3:
                raise TimeBusinessError('local_garden_unlock_configuration_invalid', 503)
            if not self.timing.reference(player_id, {'Type': 24, 'Params': [rule['Value']]}):
                raise TimeBusinessError('local_garden_locked')
        self.connection.execute('UPDATE public.player_gardens SET checked_at=%s WHERE player_id=%s', (now, player_id))
        self._normalize_search(player_id)
        return now

    def _building(self, player_id, code, *, built=True):
        row = self._rows(player_id).get(code)
        if row is None:
            raise TimeBusinessError('local_garden_building_not_found', 404)
        if built and not row['level']:
            raise TimeBusinessError('local_garden_building_not_built')
        return row

    def _effect(self, rows, kind):
        return sum(self.levels[(code, r['level'])]['PermanentEffectValue'] *
                   (r['worker_count'] + int(self.settings['GARDEN_FOOD_SUPPLY_BASE_COUNT'][0]) if kind == 1 else 1)
                   for code, r in rows.items() if r['level'] and
                   self.levels[(code, r['level'])]['PermanentEffectType'] == kind)

    def _item(self, products, changes, building, kind, code, count):
        if not count:
            return
        if kind != 2 or code not in self.behaviours:
            raise TimeBusinessError('local_garden_product_configuration_invalid', 503)
        changes[code] += count
        products.append([building, self.behaviours[code], kind, code, count])

    def receive(self, player_id, codes, now, *, modify=False):
        rows = self._rows(player_id)
        for code in codes:
            self._building(player_id, code)
        changes, products = defaultdict(int), []
        for code in codes:
            row = rows[code]
            setting, product, rate = self._rate(row)
            if setting is None:
                continue
            elapsed = max(0, now - (row['received_at'] if row['received_at'] is not None else now))
            delay = setting['RequiredTimeToReceiveOnModify' if modify else 'RequiredTimeToReceive'] * 60
            if not modify and elapsed < delay:
                continue
            volume = self._volume(row, now)
            used = 0
            if setting['ProductionType'] == 0:
                used = int(volume)
                self._item(products, changes, code, product['InventoryType'], product['InventoryCode'], used)
            else:
                for conversion in sorted(self.conversions[product['PointConversionCode']],
                                         key=lambda r: r['RequiredPoint'], reverse=True):
                    count = int((volume - used) // conversion['RequiredPoint'])
                    if not count:
                        continue
                    if conversion['RewardType'] == 1:
                        target = row['search_inventory_code']
                        if not target:
                            continue
                        self._item(products, changes, code, row['search_inventory_type'], target,
                                   count * conversion['Count'])
                    else:
                        self._item(products, changes, code, conversion['InventoryType'], conversion['InventoryCode'],
                                   count * conversion['Count'])
                    used += count * conversion['RequiredPoint']
            # Preserve fractional production and unconverted points across changes.
            self.connection.execute('''UPDATE public.player_garden_buildings SET stored_volume=%s,received_at=%s
                WHERE player_id=%s AND building_code=%s''', (volume - used, now, player_id, code))
            lottery_code = setting['LotteryProductCode']
            candidates = [r for r in self.timing.data['garden_lottery_product_master']
                          if r['Code'] == lottery_code and r['MinBuildingLevel'] <= row['level']]
            if not candidates:
                continue
            lottery = max(candidates, key=lambda r: r['MinBuildingLevel'])
            interval = lottery['LotteryCycleTime'] * 60
            lottery_at = row['lottery_checked_at'] if row['lottery_checked_at'] is not None else now
            cycles = max(0, now - lottery_at) // interval
            draws = min(cycles, lottery['StockLimit'])
            hits = sum(secrets.randbelow(1000000) < round(lottery['Probability']['Percent'] * 10000)
                       for _ in range(draws))
            if cycles:
                self.connection.execute('''UPDATE public.player_garden_buildings SET lottery_checked_at=%s
                    WHERE player_id=%s AND building_code=%s''', (lottery_at + cycles * interval, player_id, code))
            if hits and lottery['RewardType'] == 0:
                current = self.connection.execute('SELECT holding_worker_count FROM public.player_gardens WHERE player_id=%s',
                                                  (player_id,)).fetchone()[0]
                lower, upper = map(int, self.settings['GARDEN_ADD_WORKER_LOWER_UPPER_LIMIT'])
                recruited = sum(lower + secrets.randbelow(upper - lower + 1) for _ in range(hits))
                recruited = min(recruited, max(0, self._effect(rows, 2) - current))
                if recruited:
                    self.connection.execute('UPDATE public.player_gardens SET holding_worker_count=holding_worker_count+%s WHERE player_id=%s',
                                            (recruited, player_id))
                    products.append([code, 0, 0, 0, recruited])
            elif hits:
                self._item(products, changes, code, lottery['InventoryType'], lottery['InventoryCode'], hits * lottery['Count'])
        if changes:
            self.repo.apply_item_changes(player_id, 'garden-receive:' + secrets.token_hex(16), dict(changes))
            for code, count in changes.items():
                self.timing.event(player_id, 56, now, values=(str(code),), amount=count)
        self.repo._touch(player_id)
        return products, set(changes)

    def levelup(self, player_id, code, now):
        row = self._building(player_id, code, built=False)
        next_level = row['level'] + 1
        master = self.levels.get((code, next_level))
        if master is None:
            raise TimeBusinessError('local_garden_max_level')
        level = self.connection.execute('SELECT level FROM public.players WHERE player_id=%s', (player_id,)).fetchone()[0]
        rows = self._rows(player_id)
        if level < master['PlayerLevelForUnlock'] or any(rows[r['Code']]['level'] < r['Level'] for r in master['Unlocks']):
            raise TimeBusinessError('local_garden_building_locked')
        products, changed = self.receive(player_id, [code], now, modify=True) if row['level'] else ([], set())
        costs = {self.resource_codes[kind]: -master[field] for kind, field in
                 ((36, 'RequiredRockCount'), (38, 'RequiredWoodCount'), (37, 'RequiredCoinCount')) if master[field]}
        if costs:
            self.repo.apply_item_changes(player_id, f'garden-levelup:{code}:{next_level}', costs)
            changed.update(costs)
            for item, count in costs.items():
                self.timing.event(player_id, 57, now, values=(str(item),), amount=-count)
        self.connection.execute('''UPDATE public.player_garden_buildings SET level=%s,
            received_at=COALESCE(received_at,%s),lottery_checked_at=COALESCE(lottery_checked_at,%s)
            WHERE player_id=%s AND building_code=%s''', (next_level, now, now, player_id, code))
        self._normalize_search(player_id)
        self.repo._touch(player_id)
        return products, changed

    def workers(self, player_id, code, count, now):
        row = self._building(player_id, code)
        capacity = self.levels[(code, row['level'])]['WorkerCapacity']
        if capacity is None or count > capacity:
            raise TimeBusinessError('local_garden_worker_capacity')
        if row['worker_count'] == count:
            return [], set()
        rows = self._rows(player_id)
        rows[code]['worker_count'] = count
        total = sum(r['worker_count'] for r in rows.values())
        owned = self.connection.execute('SELECT holding_worker_count FROM public.player_gardens WHERE player_id=%s',
                                       (player_id,)).fetchone()[0]
        if total > owned:
            raise TimeBusinessError('local_garden_insufficient_workers')
        food = self._effect(rows, 1)
        if total > food:
            raise TimeBusinessError('local_garden_insufficient_food')
        result = self.receive(player_id, [code], now, modify=True)
        self.connection.execute('UPDATE public.player_garden_buildings SET worker_count=%s WHERE player_id=%s AND building_code=%s',
                                (count, player_id, code))
        self.repo._touch(player_id)
        return result

    def search(self, player_id, code, target, now):
        row = self._building(player_id, code)
        choices = self._eligible_search(player_id, row)
        if target not in choices:
            raise TimeBusinessError('local_garden_search_target_locked')
        if row['search_inventory_code'] == target:
            return [], set()
        result = self.receive(player_id, [code], now, modify=True)
        self.connection.execute('''UPDATE public.player_garden_buildings SET search_inventory_code=%s,
            search_inventory_type=%s WHERE player_id=%s AND building_code=%s''', (target, choices[target], player_id, code))
        self.repo._touch(player_id)
        return result

    def accelerate(self, player_id, items, now):
        minutes = 0
        for code, count in items.items():
            master = self.items.get(code)
            if master is None or master['ItemBehaviourType'] != 39 or master['Param1'] <= 0:
                raise TimeBusinessError('local_garden_acceleration_item_invalid', 400)
            minutes += master['Param1'] * count
        if not minutes or minutes > int(self.settings['GARDEN_TIME_ITEM_LIMIT_HOUR'][0]) * 60:
            raise TimeBusinessError('local_garden_acceleration_limit', 400)
        producers = [code for code, row in self._rows(player_id).items() if row['level'] and self._rate(row)[0]]
        if not producers:
            raise TimeBusinessError('local_garden_no_production')
        self.repo.apply_item_changes(player_id, 'garden-accelerate:' + secrets.token_hex(16),
                                     {code: -count for code, count in items.items()})
        self.connection.execute('''UPDATE public.player_garden_buildings SET received_at=received_at-%s,
            lottery_checked_at=lottery_checked_at-%s WHERE player_id=%s AND building_code=ANY(%s)''',
            (minutes * 60, minutes * 60, player_id, producers))
        for code, count in items.items():
            self.timing.event(player_id, 57, now, values=(str(code),), amount=count)
        self.repo._touch(player_id)
        return [], set(items)

    def mutation(self, player_id, action, params, now):
        # This client has no request ID or expected level. Debounce identical
        # upgrades/time-item requests within one server second; absolute worker
        # and search settings and production watermarks are naturally idempotent.
        digest = sha256(json.dumps([action, params], sort_keys=True).encode()).hexdigest()
        key = f'garden-request:{now}:{digest}'
        retry = action in ('levelup', 'accelerate')
        if retry:
            previous = self.connection.execute('SELECT result FROM public.operations WHERE player_id=%s AND operation_key=%s',
                                               (player_id, key)).fetchone()
            if previous:
                return previous[0]['products'], set(previous[0]['changed'])
        products, changed = getattr(self, action)(player_id, *params, now)
        if retry:
            self.connection.execute('''INSERT INTO public.operations
                (player_id,operation_key,operation_type,request_hash,result) VALUES (%s,%s,'garden',%s,%s)''',
                (player_id, key, digest, Jsonb({'products': products, 'changed': sorted(changed)})))
        return products, changed

    def unlock_room(self, player_id, code, now):
        self.initialize(player_id, now)
        if code not in self.buildings or not self.buildings[code]['RoomCode']:
            raise TimeBusinessError('local_garden_room_not_found', 404)
        self.connection.execute('UPDATE public.player_garden_buildings SET room_unlocked=TRUE WHERE player_id=%s AND building_code=%s',
                                (player_id, code))
        self.repo._touch(player_id)

    def grant_closeness_floor(self, player_id, code, level):
        if not any(r['Level'] == level for r in self.timing.data['closeness_exp_master']):
            raise TimeBusinessError('local_garden_closeness_configuration_invalid', 503)
        self.connection.execute('''INSERT INTO public.player_garden_closeness_floors VALUES (%s,%s,%s)
            ON CONFLICT(player_id,home_character_code) DO UPDATE
            SET level=GREATEST(player_garden_closeness_floors.level,EXCLUDED.level)''', (player_id, code, level))
        self.refresh_closeness(player_id)

    def refresh_closeness(self, player_id):
        from .player_export import model
        floors = dict(self.connection.execute('''SELECT home_character_code,level
            FROM public.player_garden_closeness_floors WHERE player_id=%s''', (player_id,)).fetchall())
        if not floors:
            return
        characters = self.connection.execute('SELECT home_characters FROM public.players WHERE player_id=%s',
                                            (player_id,)).fetchone()[0] or []
        curve = {r['Level']: r['TotalExp'] for r in self.timing.data['closeness_exp_master']}
        changed = False
        for index, value in enumerate(characters):
            character = record(self.repo.registry, 'HomeCharacterInfo', value)
            level = floors.get(character['HomeCharacterCode'], 0)
            if character['ClosenessLevel'] < level:
                character['ClosenessLevel'] = level
                character['ClosenessExp'] = max(character['ClosenessExp'], curve[level])
                characters[index] = model(self.repo.registry, 'HomeCharacterInfo', character)
                changed = True
        if changed:
            self.connection.execute('UPDATE public.players SET home_characters=%s WHERE player_id=%s',
                                    (Jsonb(characters), player_id))
            costume, scenes = self.connection.execute('''SELECT home_character_costume_code,home_situations
                FROM public.players WHERE player_id=%s''', (player_id,)).fetchone()
            target = next((r for r in characters if costume in r[4]), None)
            if target is not None:
                unlocked = self.repo._home_scenes(costume, target, None)
                owned = {r[0] for r in scenes or []}
                scenes = (scenes or []) + [r for r in unlocked if r[0] not in owned]
                self.connection.execute('UPDATE public.players SET home_situations=%s WHERE player_id=%s',
                                        (Jsonb(scenes), player_id))
            self.repo._touch(player_id)

    def room(self, player_id, code, mode, now):
        master = next((r for r in self.timing.data['room_master'] if r['Code'] == code), None)
        building = next((r for r in self._rows(player_id).values()
                         if self.buildings[r['building_code']]['RoomCode'] == code), None)
        if master is None or building is None:
            raise TimeBusinessError('local_garden_room_not_found', 404)
        if not building['level'] or not building['room_unlocked']:
            raise TimeBusinessError('local_garden_room_locked')
        multipliers = list(map(int, self.settings['GARDEN_ROOM_TIME_MULTIPLIER']))
        standard = datetime.strptime(self.settings['GARDEN_ROOM_STANDARD_TIME'][0], '%Y/%m/%d %H:%M:%S %z')
        offset = int(standard.utcoffset().total_seconds())
        # RoomModel.GetMultipliedTime (RVA 0x1374B00) scales the local
        # time-of-day, then wraps at 24h; schedules retain their master offset.
        second = ((now + offset) * multipliers[mode] - offset) % 86400
        candidates = []
        for row in self.timing.data['room_schedule_master']:
            if row['RoomCode'] != code:
                continue
            start, end = unix(row['StartTime']) % 86400, unix(row['EndTime']) % 86400
            active = start <= second < end if start < end else second >= start or second < end
            if active and self.timing.reference(player_id, row['UserDataForUnlock']) >= row['TargetCountForUnlock']:
                candidates.append(row)
        if not candidates:
            raise TimeBusinessError('local_garden_room_schedule_missing', 503)
        situation = max(candidates, key=lambda r: r['Priority'])['RoomSituationCode']
        self.connection.execute('INSERT INTO public.player_room_situations VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                                (player_id, code, situation, now))
        self.repo._touch(player_id)
        played = [r[0] for r in self.connection.execute('''SELECT situation_code FROM public.player_room_situations
            WHERE player_id=%s AND room_code=%s ORDER BY situation_code''', (player_id, code)).fetchall()]
        return {'RoomSituationCode': situation, 'PlayedSituationCodes': played}
