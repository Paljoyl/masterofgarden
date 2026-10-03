"""Atomic finite-stock draws, ticket consumption, reward grants and sheet changes."""
from collections import defaultdict
from secrets import randbelow
from uuid import uuid4

from PostgreSQL.box_lottery import BoxLotteryStore
from ..protocol import LocalError
from .box_lottery_catalog import BoxLotteryCatalog
from .inventory import inventory_update, total_battle_power


class BoxLotteryService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None

    @property
    def repository(self):
        repository = self.players.repository
        if repository is None or not hasattr(repository, 'connection') or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        return repository

    @property
    def catalog(self):
        if self._catalog is None:
            if self.players.timing is None:
                raise LocalError('local_box_lottery_configuration_missing', 503)
            self._catalog = BoxLotteryCatalog(self.players.timing.data)
        return self._catalog

    def initialize(self, session, store):
        self.players.initialize_box_lotteries(session.player_id, session.variant)
        return store.initialize(session.player_id, self.catalog)

    def get(self, request):
        session = self.players.session(request)
        repository = self.repository
        with repository.transaction(session.player_id):
            values = self.initialize(session, BoxLotteryStore(repository))
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                    'BoxLotteries': values}

    def execute(self, request, code, count):
        session = self.players.session(request)
        repository, catalog = self.repository, self.catalog
        pool = catalog.require(code)
        if count > catalog.max_count:
            raise LocalError('local_box_lottery_count_exceeded', 400)
        with repository.transaction(session.player_id):
            store = BoxLotteryStore(repository)
            values = self.initialize(session, store)
            box = next(row for row in values if row[0] == code)
            counts = catalog.progress(box)
            lineup = catalog.lineup(code, box[1])
            remaining = {index: row['StockCount'] - counts.get(index, 0)
                         for index, row in lineup.items()}
            total = sum(remaining.values())
            if not total:
                raise LocalError('local_box_lottery_sold_out', 409,
                                 client_message='当前奖池已抽完，请切换到下一箱。')
            # A batch stays in this sheet. Only actual draws consume tickets.
            actual = min(count, total)
            cost = pool['ConsumeInventoryCount'] * actual
            if cost >= 2**63:
                raise LocalError('local_box_lottery_inventory_overflow', 409)
            ticket = pool['ConsumeInventoryCode']
            state = self.players._state(session.player_id)
            stock = {row[0]: row[1] for row in state['StackItems']}
            if stock.get(ticket, 0) < cost:
                raise LocalError('local_box_lottery_insufficient_items', 409,
                                 client_message='箱式抽奖所需的票券不足。')
            results, rewards = [], defaultdict(int)
            for _ in range(actual):
                pick = randbelow(total)
                for index, available in remaining.items():
                    if pick < available:
                        break
                    pick -= available
                remaining[index] -= 1
                total -= 1
                counts[index] = counts.get(index, 0) + 1
                results.append(index)
                reward = lineup[index]
                rewards[reward['RewardInventoryCode']] += reward['RewardCount']
            if any(stock.get(item, 0) - (cost if item == ticket else 0) + amount >= 2**63
                   for item, amount in rewards.items()):
                raise LocalError('local_box_lottery_inventory_overflow', 409)
            key = 'box-lottery:' + uuid4().hex
            repository.apply_item_changes(session.player_id, key + ':cost', {ticket: -cost})
            repository.apply_item_changes(session.player_id, key + ':rewards', dict(rewards))
            box[2] = [row for row in box[2] if row[0] != box[1]] + [
                [box[1], index, obtained] for index, obtained in sorted(counts.items())]
            box[2].sort()
            store.save(session.player_id, values)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            # dump.cs: BoxLotteryCount=86, Values=[BoxLotteryCode]; ItemGet=56,
            # ItemConsume=57. Count draws rather than HTTP requests/reward amounts.
            self.players.timing.event(session.player_id, 86, now, values=(str(code),), amount=actual)
            self.players.timing.event(session.player_id, 57, now, values=(str(ticket),), amount=cost)
            for item, amount in rewards.items():
                self.players.timing.event(session.player_id, 56, now, values=(str(item),), amount=amount)
            current = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': current.get('UpdateAccumulateInfos', []),
                    'BoxLottery': box, 'ResultLineupIndexes': results,
                    'InventoryUpdateInfo': inventory_update(self.protocol, current, set(rewards) | {ticket}),
                    'TotalBattlePower': total_battle_power(self.players, self.protocol, session),
                    'LotteryCount': actual}

    def next_sheet(self, request, code):
        session = self.players.session(request)
        repository, catalog = self.repository, self.catalog
        catalog.require(code)
        with repository.transaction(session.player_id):
            store = BoxLotteryStore(repository)
            values = self.initialize(session, store)
            box = next(row for row in values if row[0] == code)
            counts = catalog.progress(box)
            lineup = catalog.lineup(code, box[1])
            featured = [r for r in lineup.values() if r['IsFeatured']]
            required = featured or list(lineup.values())
            if any(counts.get(r['Index'], 0) < r['StockCount'] for r in required):
                raise LocalError('local_box_lottery_next_sheet_unavailable', 409,
                                 client_message='请先抽完当前箱的重点奖品；无重点奖品的箱子须全部抽完。')
            if box[1] == 2**31 - 1:
                raise LocalError('local_box_lottery_sheet_limit', 409)
            # Keep previous sheet counts for the client history and start a fresh
            # stock for the new sheet; beyond the master limit reuse its last lineup.
            box[1] += 1
            store.save(session.player_id, values)
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []), 'BoxLottery': box}
