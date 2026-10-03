"""Atomic backpack box consumption, weighted rewards and inventory updates."""
from bisect import bisect_right
from collections import defaultdict
from itertools import accumulate
from secrets import randbelow
from uuid import uuid4

from PostgreSQL.players import InsufficientItems
from ..protocol import LocalError
from .box_item_catalog import BoxItemCatalog
from .inventory import inventory_update


class BoxItemService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None

    @property
    def catalog(self):
        if self._catalog is None:
            timing = self.players.timing
            if timing is None:
                raise LocalError('local_box_configuration_missing', 503)
            self._catalog = BoxItemCatalog(timing.data)
        return self._catalog

    def open(self, request, code, count):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None:
            raise LocalError('player_storage_unavailable', 503)
        catalog = self.catalog
        with repository.transaction(session.player_id):
            state = self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            level = self.protocol.fields('UserInfo', state['User'])['Level']
            lineup = catalog.lineup(code, level, now)
            owned = {row[0]: row[1] for row in state['StackItems']}
            if owned.get(code, 0) < count:
                raise LocalError('local_box_insufficient_items', 409)
            weights = list(accumulate(row[2] for row in lineup))
            rewards = defaultdict(int)
            for _ in range(count):
                item, amount, _ = lineup[bisect_right(weights, randbelow(weights[-1]))]
                rewards[item] += amount
            changes = dict(rewards)
            changes[code] = changes.get(code, 0) - count
            changes = {item: delta for item, delta in changes.items() if delta}
            if any(not 0 <= owned.get(item, 0) + delta < 2**63 for item, delta in changes.items()):
                raise LocalError('local_box_inventory_overflow', 409)
            key = 'box-open:' + uuid4().hex
            try:
                if changes:
                    repository.apply_item_changes(session.player_id, key, changes)
            except InsufficientItems as exc:
                raise LocalError('local_box_insufficient_items', 409) from exc
            # Item-acquisition missions receive the actual drawn amount, not
            # the net balance change or the number of boxes consumed.
            for item, amount in rewards.items():
                self.players.timing.event(session.player_id, 56, now, values=(str(item),), amount=amount)
            state = self.players._state(session.player_id)
            return {'BoxItems': [self.protocol.model('OpenBoxItemViewInfo', {
                        'ItemCode': item, 'Count': amount}) for item, amount in sorted(rewards.items())],
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, set(rewards) | {code}),
                    'UpdateAccumulateInfos': state['UpdateAccumulateInfos']}
