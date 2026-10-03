"""Local lottery execution; prices, lineup and rewards are chosen by server definitions."""
from collections import defaultdict
from hashlib import sha256
import logging
from uuid import uuid4

from PostgreSQL.game_time import timestamp
from PostgreSQL.lottery import LotteryStore
from PostgreSQL.players import InsufficientItems
from PostgreSQL.shop import ShopStore
from mog_protocol.codec import encode
from ..protocol import LocalError, integer
from .inventory import (inventory_update, total_battle_power, FREE_STONE,
                        PAID_STONE, SUPPLEMENT_PAID_STONE)
from .lottery_catalog import LotteryCatalog, LotteryProbability

log = logging.getLogger('mog.lottery')


class LotteryService:
    def __init__(self, players, protocol, probability_source=None):
        self.players, self.protocol = players, protocol
        self.probability_source = probability_source
        self._catalog = None

    @property
    def repository(self):
        if self.players.repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        return self.players.repository

    @property
    def catalog(self):
        if self._catalog is None:
            self._catalog = LotteryCatalog(self.repository.connection, self.players.timing.clock)
        return self._catalog

    def initialize(self, session, store, now):
        key = (session.player_id, session.variant, '/lottery/getlotteries')
        template = self.players.templates.get(key)
        displays = self.protocol.fields('GetLotteriesResponse', template)['LotteryDisplays'] if template else []
        history = self.players.templates.get((session.player_id, session.variant, '/lottery/getlotteryhistories'))
        histories = self.protocol.fields('GetLotteryHistoriesResponse', history)['LotteryHistories'] if history else []
        at = getattr(self.players, 'template_times', {}).get(key, now)
        store.initialize(session.player_id, displays, int(at), histories, self.catalog, now)

    def remaining(self, store, player_id, pool, button, now):
        period = self.catalog.period(self.catalog.setting(pool)['ResetType'], now)
        used, total = store.count(player_id, pool['Code'], button['ButtonIndex'], period)
        limit = button['LimittedTime']
        return max(0, limit - used) if limit else -1, total

    def group_available(self, store, player_id, pool, now):
        group = pool['LotteryGroupCode']
        if not group:
            return True
        if self.catalog.require(self.catalog.groups, group)['GroupType'] != 1:
            raise LocalError('local_lottery_group_not_implemented', 501)
        steps = [r for r in self.catalog.pools.values() if r['LotteryGroupCode'] == group]
        steps.sort(key=lambda r: self.catalog.require(self.catalog.steps, r['Code'])['StepCount'])
        for candidate in steps:
            buttons = self.catalog.setting(candidate)['ButtonSettings']
            if not buttons or any(not b['LimittedTime'] for b in buttons):
                raise LocalError('local_lottery_step_definition_invalid', 503)
            if any(self.remaining(store, player_id, candidate, b, now)[0] != 0 for b in buttons):
                return candidate['Code'] == pool['Code']
        return False

    def available(self, store, player_id, pool, now):
        if pool['LimitLotteryCode'] or pool['LimitType'] not in (0, 2):
            raise LocalError('local_lottery_limit_not_implemented', 501)
        active, expiry = self.players.timing.lottery_expiry(player_id, pool['Code'], now)
        return active and self.group_available(store, player_id, pool, now), expiry

    def displays(self, request, existing=None):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            store = LotteryStore(self.repository)
            self.initialize(session, store, now)
            result = []
            allowed = None if existing is None else {self.protocol.fields('LotteryDisplayInfo', r)['LotteryCode']
                                                     for r in existing}
            for pool in self.catalog.pools.values():
                if allowed is not None and pool['Code'] not in allowed:
                    continue
                active, expiry = self.available(store, session.player_id, pool, now)
                if not active:
                    continue
                buttons = [[b['ButtonIndex'], *self.remaining(store, session.player_id, pool, b, now)]
                           for b in self.catalog.setting(pool)['ButtonSettings']]
                if not buttons or all(b[1] == 0 for b in buttons):
                    continue
                result.append(self.protocol.model('LotteryDisplayInfo', {
                    'LotteryCode': pool['Code'], 'ButtonInfos': buttons, 'ShowPriority': pool['ShowPriority'],
                    'ExpiredAt': timestamp(expiry) if expiry is not None else None,
                    'LotterySelectCharacters': (self.catalog.validate_selection(pool,
                        store.selection(session.player_id, pool['Code'])) if pool['LotteryType'] == 1 else [])}))
            result.sort(key=lambda r: (r[2], r[0]))
            return result

    def get(self, request):
        displays = self.displays(request)
        return {'UpdateAccumulateInfos': self.players.state(request).get('UpdateAccumulateInfos', []),
                'LotteryDisplays': displays}

    def histories(self, request):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            store = LotteryStore(self.repository)
            self.initialize(session, store, now)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'LotteryHistories': store.histories(session.player_id, now, self.catalog)}

    def probability(self, request, code, lineup, times, button=None):
        response = self.catalog.local_probability(self.protocol, code, lineup)
        if response is not None:
            return response, LotteryProbability(self.protocol, response, lineup, self.catalog.characters, times)
        # A selection is player state. A cache keyed only by pool and version
        # cannot prove that it describes this player's current selection.
        if self.catalog.pools[code]['LotteryType'] != 1 and self.probability_source is not None:
            try:
                response = self.probability_source(request, code)
                if response is not None:
                    return response, LotteryProbability(self.protocol, response, lineup, self.catalog.characters, times)
            except LocalError as exc:
                if not self.catalog.fallback_enabled:
                    raise
                log.warning('Lottery cached/source odds rejected: pool=%s, reason=%s', code, exc.code)
        response = self.catalog.fallback_probability(self.protocol, code, lineup, button)
        if response is None:
            raise LocalError('local_lottery_probability_missing', 503)
        log.info('Using configured local lottery probability policy: pool=%s', code)
        return response, LotteryProbability(self.protocol, response, lineup, self.catalog.characters, times)

    def set_selection(self, request, code, characters):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            store = LotteryStore(self.repository)
            self.initialize(session, store, now)
            pool = self.catalog.require(self.catalog.pools, code)
            if not self.available(store, session.player_id, pool, now)[0]:
                raise LocalError('local_lottery_unavailable', 409)
            selected = self.catalog.validate_selection(pool, characters)
            store.save_selection(session.player_id, code, selected, now)

    def execution_rules(self, store, session, code, button_index, now):
        pool = self.catalog.pools.get(code)
        if pool is None:
            raise LocalError('local_lottery_not_found', 404)
        if not self.available(store, session.player_id, pool, now)[0]:
            raise LocalError('local_lottery_unavailable', 409)
        button = self.catalog.button(pool, button_index)
        if self.remaining(store, session.player_id, pool, button, now)[0] == 0:
            raise LocalError('local_lottery_limit_reached', 409)
        return pool, button, self.catalog.lineup(pool, store.selection(session.player_id, code))

    def chances(self, request, code):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            pool = self.catalog.pools.get(code)
            if pool is None:
                raise LocalError('local_lottery_not_found', 404)
            self.players._state(session.player_id)
            store = LotteryStore(self.repository)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            self.initialize(session, store, now)
            if not self.available(store, session.player_id, pool, now)[0]:
                raise LocalError('local_lottery_unavailable', 409)
            times = {kind for b in self.catalog.setting(pool)['ButtonSettings']
                     for kind, amount in ((0, b['TimesA']), (1, b['TimesB'])) if amount}
            lineup = self.catalog.lineup(pool, store.selection(session.player_id, code), preview=True)
        # Never hold the shared repository connection lock across network I/O.
        response, _ = self.probability(request, code, lineup, times)
        fields = self.protocol.fields('GetLotteryWinningChanceResponse', response)
        with self.repository.transaction(session.player_id):
            fields['UpdateAccumulateInfos'] = self.players._state(session.player_id).get('UpdateAccumulateInfos', [])
            return fields

    def cost(self, stock, button):
        # LotteryButtonModel .ctor RVA 0xFBC9F0 chooses a fully funded substitute,
        # then a common ticket, then the main price. The request has no cost-choice field.
        code, amount = button['ConsumeItemCode'], button['ConsumeCount']
        alternative, needed = button['SubConsumeItemCode'], button['SubConsumeCount']
        if alternative and needed and stock.get(alternative, 0) >= needed:
            code, amount = alternative, needed
        elif button['CommonTicketCount'] and stock.get(self.catalog.common_ticket, 0) >= button['CommonTicketCount']:
            code, amount = self.catalog.common_ticket, button['CommonTicketCount']
        pools = {FREE_STONE: (FREE_STONE, PAID_STONE, SUPPLEMENT_PAID_STONE),
                 SUPPLEMENT_PAID_STONE: (PAID_STONE, SUPPLEMENT_PAID_STONE),
                 PAID_STONE: (PAID_STONE, SUPPLEMENT_PAID_STONE),
                 990000004: (FREE_STONE, PAID_STONE, SUPPLEMENT_PAID_STONE)}
        # Ordinary stone draws use free stones first, then paid stones for the shortfall.
        # Paid-only draws use the two paid pools; 004 is virtual mixed currency.
        changes = defaultdict(int)
        remaining = amount
        for actual in pools.get(code, (code,)):
            spent = min(stock.get(actual, 0), remaining)
            changes[actual] -= spent
            remaining -= spent
            if not remaining:
                break
        if remaining:
            raise InsufficientItems('Insufficient lottery currency')
        return code, amount, {c: n for c, n in changes.items() if n}

    def grant_result(self, store, player_id, code, entry, items, affected):
        master = self.catalog.require(self.catalog.characters, code)
        rarity = master['DefaultRarity']
        integer(rarity, minimum=1, maximum=3)
        new = store.grant_character(player_id, master)
        if new:
            store.unlock_costume(player_id, master, self.catalog)
        crystal = 0 if new else self.catalog.duplicate_crystals[rarity - 1]
        limit = (0 if new else self.catalog.duplicate_limit[rarity - 1]) + entry['AddItemLimitbreak']
        fragments = entry['AddItemFragment']
        for value in (crystal, limit, fragments):
            integer(value, maximum=2**31 - 1)
        items[self.catalog.crystal] += crystal
        items[master['FragmentItemCode']] += fragments
        items[master['LimitBreakItemCode']] += limit
        additions = []
        for item in entry.get('AddItems', []):
            item_code = integer(item['ItemCode'], minimum=1)
            count = integer(item['Count'], minimum=1)
            items[item_code] += count
            additions.append(self.protocol.model('LotteryPickupAddItemInfo', {'ItemCode': item_code, 'Count': count}))
        affected.add(code)
        return self.protocol.model('LotteryResultCharacterInfo', {
            'CharacterCode': code, 'IsNew': new, 'CrystalCount': crystal, 'FragmentCount': fragments,
            'LimitBreakItemCount': limit, 'LotteryPickupAddItems': additions})

    def rewards(self, reward_code, items, result):
        rows = self.catalog.require(self.catalog.rewards, reward_code)
        for row in rows:
            # All lottery button/milestone rewards in this verified master are items.
            # A future reward kind cannot silently disappear after payment.
            if row['Type'] != 2:
                raise LocalError('local_lottery_bonus_reward_not_implemented', 501)
            code = integer(row['ItemCode'], minimum=1)
            count = integer(row['Count'], minimum=1)
            items[code] += count
            result.append(self.protocol.model('RewardInfo', {
                'Type': 2, 'Code': code, 'Count': count, 'DisplayPriority': row['DisplayPriority']}))

    def bonuses(self, store, player_id, pool, button, draws, stock, items, now):
        rewards = []
        if pool['ExchangeShopCode']:
            shop = self.catalog.require(self.catalog.shops, pool['ExchangeShopCode'])
            if shop['ConsumeInventoryType'] != 2:
                raise LocalError('local_lottery_exchange_definition_invalid', 503)
            # Exchange-point UI promises one point per draw; the point item is
            # linked by ExchangeShopCode, never derived from the lottery number.
            items[integer(shop['ConsumeInventoryCode'], minimum=1)] += draws
        for bonus in pool['BonusRewards']:
            if bonus['ButtonIndex'] == button['ButtonIndex']:
                self.rewards(bonus['RewardCode'], items, rewards)
        code = pool['LotteryBonusCode']
        if not code:
            return rewards
        bonus = self.catalog.require(self.catalog.bonuses, code)
        point_item = integer(bonus['BonusPointItemCode'], minimum=1)
        before = stock.get(point_item, 0)
        after = before + draws
        items[point_item] += draws
        for index, setting in enumerate(bonus['BonusSettings']):
            rows = self.catalog.require(self.catalog.bonus_rewards, setting['BonusRewardCode'])
            cycle_length = max(integer(r['BonusPoint'], minimum=1) for r in rows)
            start = integer(setting['StartPoint'])
            first = max(0, (before - start) // cycle_length - 1)
            last = max(0, (after - start) // cycle_length)
            if not setting['IsLoop']:
                first = last = 0
            elif setting['LoopLimit']:
                last = min(last, setting['LoopLimit'] - 1)
            for cycle in range(first, last + 1):
                for row in rows:
                    point = start + cycle * cycle_length + row['BonusPoint']
                    if before < point <= after and store.receipt(player_id, code, index, cycle, row['BonusPoint'], now):
                        self.rewards(row['RewardCode'], items, rewards)
        return rewards

    def execute(self, request, code, button_index, tutorial_progress):
        session = self.players.session(request)
        with self.repository.transaction(session.player_id):
            store = LotteryStore(self.repository)
            state = self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            self.initialize(session, store, now)
            pool, button, lineup = self.execution_rules(store, session, code, button_index, now)
            ShopStore(self.repository).repair_paid_stones(session.player_id)
            state = self.players._state(session.player_id)
            self.cost({r[0]: r[1] for r in state['StackItems']}, button)
            times = {kind for kind, count in ((0, button['TimesA']), (1, button['TimesB'])) if count}
        response, probability = self.probability(request, code, lineup, times, button)
        with self.repository.transaction(session.player_id):
            store = LotteryStore(self.repository)
            self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            # Concurrent draws or expiry during the query may change eligibility.
            # Recheck all limits and funds while holding the player lock.
            pool, button, current_lineup = self.execution_rules(store, session, code, button_index, now)
            if current_lineup != lineup:
                raise LocalError('local_lottery_selection_changed', 409)
            ShopStore(self.repository).repair_paid_stones(session.player_id)
            state = self.players._state(session.player_id)
            stock = {r[0]: r[1] for r in state['StackItems']}
            consume_code, consume_count, costs = self.cost(stock, button)
            key = 'lottery:' + uuid4().hex
            if costs:
                self.repository.apply_item_changes(session.player_id, key + ':cost', costs)
            results, items, affected = [], defaultdict(int), set()
            for kind, count in ((0, button['TimesA']), (1, button['TimesB'])):
                for _ in range(count):
                    character = probability.draw(kind)
                    results.append(self.grant_result(store, session.player_id, character, lineup[character], items, affected))
            bonuses = self.bonuses(store, session.player_id, pool, button, len(results), stock, items, now)
            grants = {c: n for c, n in items.items() if n}
            if grants:
                self.repository.apply_item_changes(session.player_id, key + ':reward', grants)
            period = self.catalog.period(self.catalog.setting(pool)['ResetType'], now)
            store.increment(session.player_id, code, button_index, period)
            details = [[row[0], *row[2:]] for row in results]
            store.history(session.player_id, key, code, button_index, now, consume_code, consume_count,
                          details, sha256(encode(response)).hexdigest())
            # AccumulateType.LotteryPlayCount=38, LotteryPlayCountWithLottery=39;
            # counts describe individual draws, not the number of HTTP requests.
            self.players.timing.event(session.player_id, 38, now, amount=len(results))
            self.players.timing.event(session.player_id, 39, now, values=(str(code),), amount=len(results))
            self.repository._touch(session.player_id)
            current = self.players._state(session.player_id)
            inventory = inventory_update(self.protocol, current, set(costs) | set(grants))
            inventory = self.protocol.model('InventoryUpdateInfo', {
                'Characters': [c for c in current['Characters'] if c[0] in affected]}, inventory)
            # TutorialProgress is client context, never permission to jump stored
            # tutorial stages. Tutorial transitions remain with their own handler.
            return {'UpdateAccumulateInfos': current.get('UpdateAccumulateInfos', []),
                    'LotteryResultCharacters': results, 'InventoryUpdateInfo': inventory,
                    'HomeInfo': current.get('HomeInfo'), 'HomeCharacters': current.get('HomeCharacters', []),
                    'BonusRewardInfos': bonuses, 'TotalBattlePower': total_battle_power(self.players, self.protocol, session)}
