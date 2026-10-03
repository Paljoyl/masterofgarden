"""Local shop purchases and simulated TW payment, never an upstream settlement."""
from collections import defaultdict
import secrets
from uuid import uuid4

from PostgreSQL.shop import ShopStore
from PostgreSQL.players import InsufficientItems
from mog_protocol.codec import decode, encode
from ..protocol import LocalError
from .inventory import (inventory_update, total_battle_power, stone_items,
                        PAID_STONE, SUPPLEMENT_PAID_STONE, FREE_STONE, STONE_CODES)
from .shop_catalog import ShopCatalog


class ShopService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None

    @property
    def catalog(self):
        if self._catalog is None:
            self._catalog = ShopCatalog(self.store().connection)
        return self._catalog

    def store(self):
        if self.players.repository is None:
            raise LocalError('player_storage_unavailable', 503)
        return ShopStore(self.players.repository)

    def _available(self, row, now):
        if row is None:
            raise LocalError('local_shop_product_not_found', 404)
        shop = self.catalog.shops.get(row['ShopCode'])
        if not shop or not self.catalog.active(shop, now) or not self.catalog.active(row, now):
            raise LocalError('local_shop_product_unavailable', 409)
        return shop

    def _selection(self, store, player_id, row, now, *, refresh=False):
        options = self.catalog.options.get(row['Code'], ())
        if not options or sum(max(0, o['Rate']) for o in options) <= 0:
            raise LocalError('local_shop_lineup_definition_not_found', 503)
        def choose():
            target = secrets.randbelow(sum(max(0, o['Rate']) for o in options))
            for option in options:
                target -= max(0, option['Rate'])
                if target < 0:
                    return option['Code']
        shop = self.catalog.shops[row['ShopCode']]
        period = self.catalog.period(shop['ResetCycleType'], now)
        selected = store.selection(player_id, row['Code'], period, choose, refresh=refresh)
        option = next((o for o in options if o['Code'] == selected), None)
        if option is None:
            raise LocalError('local_shop_lineup_definition_changed', 409)
        return option, period

    def get(self, request, categories, event_code):
        session = self.players.session(request)
        store = self.store()
        now = int(self.players.clock())
        with store.repo.transaction(session.player_id):
            store.repair_paid_stones(session.player_id)
            state = self.players._state(session.player_id)
            user = self.protocol.fields('UserInfo', state['User'])
            shops = {code: r for code, r in self.catalog.shops.items()
                if r['Category'] in categories and self.catalog.active(r, now)
                and (not r['RelatedEventCode'] or r['RelatedEventCode'] == event_code)}
            payments, packages, lineups = defaultdict(list), defaultdict(list), defaultdict(list)
            for row in self.catalog.payments.values():
                if row['ShopCode'] in shops and self.catalog.active(row, now):
                    link = self.catalog.links.get(row['ProductId'], {})
                    period = self.catalog.period(link.get('ResetCycleType', 0), now)
                    count = store.count(session.player_id, 'payment', row['Code'], period)
                    payments[row['ShopCode']].append([row['Code'], count, self.catalog.expiry(row)])
            for row in self.catalog.packages.values():
                if row['ShopCode'] in shops and self.catalog.active(row, now):
                    period = self.catalog.period(row['ResetCycleType'], now)
                    count = store.count(session.player_id, 'package', row['Code'], period)
                    packages[row['ShopCode']].append([row['Code'], [None, count, now], self.catalog.expiry(row)])
            for row in self.catalog.lineups.values():
                if (row['ShopCode'] not in shops or not self.catalog.active(row, now)
                        or not row['UnlockLevelLowerLimit'] <= user['Level'] <= row['UnlockLevelUpperLimit']):
                    continue
                ref = row.get('UserDataForUnlock')
                if ref and ref['Type'] == 9 and not set(ref['Params']).issubset({c[0] for c in state['Characters']}):
                    continue
                option, period = self._selection(store, session.player_id, row, now)
                count = store.count(session.player_id, 'lineup', row['Code'], period)
                lineups[row['ShopCode']].append([row['Code'], option['Code'], count])
            displays = [[code, values, store.count(session.player_id, 'refresh', code,
                self.catalog.period(shops[code]['ResetCycleType'], now)), self.catalog.expiry(shops[code])]
                for code, values in lineups.items()]
            return {'UpdateAccumulateInfos': [], 'ShopPaymentDisplays': dict(payments),
                    'ShopPackageDisplays': dict(packages), 'ShopDisplays': displays}

    def _cost(self, store, player_id, key, shop, price, extras=()):
        costs = defaultdict(int)
        if price:
            if shop['ConsumeInventoryType'] != 2:
                raise LocalError('local_shop_cost_not_implemented', 501)
            costs[shop['ConsumeInventoryCode']] += price
        for info in extras:
            number = info['Number'] - 1
            definitions = shop['AdditionalConsumes']
            if not 0 <= number < len(definitions) or definitions[number]['InventoryType'] != 2:
                raise LocalError('local_shop_cost_definition_invalid', 503)
            costs[definitions[number]['InventoryCode']] += info['Price']
        costs = {code: amount for code, amount in costs.items() if amount}
        if not costs:
            return set()

        # Shop master code 990000002 means paid stones. The TW PC client
        # displays the sum of its main (003) and supplement (002) balances.
        # Code 004 is a virtual total, never a separately stocked/spent item.
        pools = {SUPPLEMENT_PAID_STONE: (PAID_STONE, SUPPLEMENT_PAID_STONE),
                 PAID_STONE: (PAID_STONE, SUPPLEMENT_PAID_STONE),
                 990000004: (FREE_STONE, PAID_STONE, SUPPLEMENT_PAID_STONE)}
        if set(costs).intersection(pools):
            store.repair_paid_stones(player_id)
        codes = sorted({actual for code in costs for actual in pools.get(code, (code,))})
        balances = dict(store.connection.execute('''SELECT item_code,quantity FROM public.items
            WHERE player_id=%s AND item_code=ANY(%s)''', (player_id, codes)).fetchall())
        changes = defaultdict(int)
        # Reserve free-only and paid-only costs before any total-stone cost.
        # Additional prices can share the same pools, so debit the working balances.
        for code in sorted(costs, key=lambda value: (value == 990000004, value)):
            remaining = costs[code]
            for actual in pools.get(code, (code,)):
                spent = min(balances.get(actual, 0), remaining)
                if spent:
                    balances[actual] -= spent
                    changes[actual] -= spent
                    remaining -= spent
                if remaining == 0:
                    break
            if remaining:
                raise InsufficientItems('Insufficient shop currency')
        if changes:
            store.repo.apply_item_changes(player_id, 'shop-cost:' + key, dict(changes))
        return set(changes)

    def _inventory(self, session, store, changed):
        items, characters, honors, passes = changed
        state = self.players._state(session.player_id)
        result = inventory_update(self.protocol, state, items)
        fields = {'Characters': [c for c in state['Characters'] if c[0] in characters],
                  'Honors': [self.protocol.model('HonorInfo', {'HonorCode': code}) for code in sorted(honors)],
                  'ShopPassInfos': []}
        for code in passes:
            row = store.connection.execute('SELECT end_at,notified_at FROM public.player_shop_passes WHERE player_id=%s AND code=%s',
                                           (session.player_id, code)).fetchone()
            fields['ShopPassInfos'].append([code, row[0], row[1]])
        return self.protocol.model('InventoryUpdateInfo', fields, result), state

    def _package_inventory(self, inventory, before, after, price):
        # TW PC ShopModel's package callback passes Price to ModifyInventory
        # (RVA 0x1363D00). It subtracts that price from the main paid row, then
        # offsets the reductions in free/supplement balances before applying it.
        # Supply its pre-adjustment main row so the client lands on the persisted
        # balance; all other inventory responses use normal absolute balances.
        previous = {row[0]: row[1] for row in before}
        stones = stone_items(self.protocol, after)
        current = {row[0]: row[1] for row in stones}
        paid = current[PAID_STONE] + price - sum(
            previous.get(code, 0) - current[code] for code in (FREE_STONE, SUPPLEMENT_PAID_STONE))
        fields = self.protocol.fields('InventoryUpdateInfo', inventory)
        items = [row for row in fields['StackItems'] if row[0] != PAID_STONE]
        items.append(self.protocol.model('StackItemInfo', {'Count': paid},
                                        next(row for row in stones if row[0] == PAID_STONE)))
        return self.protocol.model('InventoryUpdateInfo', {'StackItems': items}, inventory)

    def package(self, request, code):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            now = int(self.players.clock())
            row = self.catalog.packages.get(code)
            shop = self._available(row, now)
            period = self.catalog.period(row['ResetCycleType'], now)
            count = store.count(session.player_id, 'package', code, period)
            if row['PurchaseLimit'] > 0 and count >= row['PurchaseLimit']:
                raise LocalError('local_shop_purchase_limit_reached', 409)
            consume_stones = (row['Price'] if shop['ConsumeInventoryType'] == 2
                and shop['ConsumeInventoryCode'] in (*STONE_CODES, 990000004) else 0)
            before = stone_items(self.protocol, self.players._state(session.player_id)) if consume_stones else []
            key = uuid4().hex
            costs = self._cost(store, session.player_id, key, shop, row['Price'])
            rewards = self.catalog.expand(self.catalog.rewards(row['AdditionalContentCode']))
            changed = store.grant(session.player_id, 'shop-reward:' + key, rewards, self.catalog, now)
            changed[0].update(costs)
            store.increment(session.player_id, 'package', code, period, 1, now)
            inventory, state = self._inventory(session, store, changed)
            if consume_stones:
                inventory = self._package_inventory(inventory, before, state, consume_stones)
            return {'UpdateAccumulateInfos': [], 'ReceivedRewards': rewards, 'InventoryUpdateInfo': inventory}

    def lineups(self, request, purchases):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            now, key = int(self.players.clock()), uuid4().hex
            rewards, changed = [], (set(), set(), set(), set())
            level = self.protocol.fields('UserInfo', self.players._state(session.player_id)['User'])['Level']
            for code, amount in purchases:
                row = self.catalog.lineups.get(code)
                shop = self._available(row, now)
                if not row['UnlockLevelLowerLimit'] <= level <= row['UnlockLevelUpperLimit']:
                    raise LocalError('local_shop_level_required', 403)
                option, period = self._selection(store, session.player_id, row, now)
                count = store.count(session.player_id, 'lineup', code, period)
                if row['PurchaseLimit'] > 0 and count + amount > row['PurchaseLimit']:
                    raise LocalError('local_shop_purchase_limit_reached', 409)
                costs = self._cost(store, session.player_id, key + ':' + str(code), shop, option['Price'] * amount,
                    [dict(Number=e['Number'], Price=e['Price'] * amount) for e in option['AdditionalConsumePrices']])
                batch = [[option['InventoryType'], option['InventoryCode'], option['Amount'] * amount, 0]]
                batch += [[r[0], r[1], r[2] * amount, r[3]] for r in self.catalog.rewards(option['AdditionalContentCode'])]
                batch = self.catalog.expand(batch)
                added = store.grant(session.player_id, 'shop-reward:' + key + ':' + str(code), batch, self.catalog, now)
                for i in range(4):
                    changed[i].update(added[i])
                changed[0].update(costs)
                rewards.extend(batch)
                store.increment(session.player_id, 'lineup', code, period, amount, now)
            inventory, state = self._inventory(session, store, changed)
            return {'UpdateAccumulateInfos': [], 'ReceivedRewards': rewards, 'InventoryUpdateInfo': inventory,
                'HomeCharacters': state.get('HomeCharacters', []), 'TotalBattlePower': total_battle_power(self.players, self.protocol, session)}

    def verify(self, request, codes):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            now = int(self.players.clock())
            for code in codes:
                row = self.catalog.payments.get(code)
                self._available(row, now)
                link = self.catalog.links.get(row['ProductId'], {})
                period = self.catalog.period(link.get('ResetCycleType', 0), now)
                count = store.count(session.player_id, 'payment', code, period)
                if link.get('PurchaseLimit', 0) > 0 and count >= link['PurchaseLimit']:
                    raise LocalError('local_shop_purchase_limit_reached', 409)
                store.prepare(session.player_id, code, session.variant, now)

    def payment(self, request, code):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            store.repair_paid_stones(session.player_id)
            now = int(self.players.clock())
            order = store.order(session.player_id, code, session.variant, pending=True)
            if order is None:
                previous = store.order(session.player_id, code, session.variant)
                if previous and previous['status'] == 'complete':
                    original = decode(bytes(previous['response']))
                    fields = self.protocol.fields('UpdateInventoryAfterPurchaseResponse', original)
                    old = self.protocol.fields('InventoryUpdateInfo', fields['InventoryUpdateInfo'])
                    changed = ({i[0] for i in old['StackItems']}, {c[0] for c in old['Characters']},
                               {h[0] for h in old['Honors']}, {p[0] for p in old['ShopPassInfos']})
                    inventory, _ = self._inventory(session, store, changed)
                    return self.protocol.model('UpdateInventoryAfterPurchaseResponse', {'InventoryUpdateInfo': inventory}, original)
                raise LocalError('local_payment_verification_required', 409)
            row = self.catalog.payments.get(code)
            self._available(row, now)
            link = self.catalog.links.get(row['ProductId'], {})
            period = self.catalog.period(link.get('ResetCycleType', 0), now)
            count = store.count(session.player_id, 'payment', code, period)
            if link.get('PurchaseLimit', 0) > 0 and count >= link['PurchaseLimit']:
                raise LocalError('local_shop_purchase_limit_reached', 409)
            rewards = []
            if row['PaidPoint']:
                rewards.append([2, PAID_STONE, row['PaidPoint'], 0])
            if row['FreePoint']:
                rewards.append([2, FREE_STONE, row['FreePoint'], 0])
            rewards += self.catalog.rewards(row['AdditionalContentCode'])
            rewards = self.catalog.expand(rewards)
            changed = store.grant(session.player_id, 'local-payment:' + order['order_id'], rewards, self.catalog, now)
            store.increment(session.player_id, 'payment', code, period, 1, now)
            inventory, _ = self._inventory(session, store, changed)
            response = self.protocol.model('UpdateInventoryAfterPurchaseResponse', {
                'UpdateAccumulateInfos': [], 'InventoryUpdateInfo': inventory, 'RewardShopPaymentCode': code})
            store.complete(session.player_id, order['order_id'], now, encode(response))
            return response

    def external_refresh(self, request):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            store.repair_paid_stones(session.player_id)
            state = self.players._state(session.player_id)
            inventory = inventory_update(self.protocol, state, {r[0] for r in state['StackItems']})
            return {'UpdateAccumulateInfos': [], 'InventoryUpdateInfo': inventory}

    def user_stone(self, request):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            store.repair_paid_stones(session.player_id)
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'StackItemInfos': stone_items(self.protocol, state)}

    def update_lineup(self, request, code):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            now = int(self.players.clock())
            shop = self.catalog.shops.get(code)
            if shop is None or not self.catalog.active(shop, now):
                raise LocalError('local_shop_product_not_found', 404)
            definitions = self.catalog.update_costs.get(code)
            if not definitions or not shop['ItemCodeForUpdate']:
                raise LocalError('local_shop_refresh_not_available', 409)
            period = self.catalog.period(shop['ResetCycleType'], now)
            count = store.count(session.player_id, 'refresh', code, period)
            step = min(count + 1, max(r['Step'] for r in definitions))
            price = next(r['Cost'] for r in definitions if r['Step'] == step)
            key = uuid4().hex
            if price:
                store.repo.apply_item_changes(session.player_id, 'shop-refresh:' + key, {shop['ItemCodeForUpdate']: -price})
            for row in self.catalog.lineups.values():
                if row['ShopCode'] == code and self.catalog.active(row, now):
                    self._selection(store, session.player_id, row, now, refresh=True)
            store.increment(session.player_id, 'refresh', code, period, 1, now)
            catalog = self.get(request, {shop['Category']}, shop['RelatedEventCode'])
            updated = next((r for r in catalog['ShopDisplays'] if r[0] == code), [code, [], count + 1, self.catalog.expiry(shop)])
            inventory = inventory_update(self.protocol, self.players._state(session.player_id), {shop['ItemCodeForUpdate']})
            return {'UpdateAccumulateInfos': [], 'UpdatedShopDisplay': updated, 'InventoryUpdateInfo': inventory}

    def game_top(self, request):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            store.repair_paid_stones(session.player_id)
            value = self.players.game_top(request)
            fields = self.protocol.fields('GetGameTopInfoResponse', value)
            honors = list(fields['Honors'] or [])
            known = {self.protocol.fields('HonorInfo', h)['HonorCode'] for h in honors}
            honors.extend(self.protocol.model('HonorInfo', {'HonorCode': code}) for code in store.honors(session.player_id) if code not in known)
            catalog = self.get(request, set(range(11)), 0)
            catalog.pop('UpdateAccumulateInfos')
            catalog['Honors'] = honors
            return self.protocol.model('GetGameTopInfoResponse', catalog, value)
