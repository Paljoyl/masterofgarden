"""Owned local presents; claims compose receipt and inventory in one transaction."""
import time

from PostgreSQL.player_protocol import InvalidPlayerData
from PostgreSQL.players import OperationConflict
from ..protocol import LocalError
from .inventory import inventory_update, total_battle_power


class PresentBoxService:
    def __init__(self, players, protocol, clock=time.time):
        self.players, self.protocol = players, protocol
        self.clock = clock

    def _present(self, row):
        return self.protocol.model('PresentInfo', {name: row[column] for name, column in (
            ('PresentId', 'present_id'), ('Title', 'title'), ('InventoryType', 'inventory_type'),
            ('InventoryCode', 'inventory_code'), ('Amount', 'amount'), ('SenderIconCode', 'sender_icon_code'),
            ('ArrivedAt', 'arrived_at'), ('LimitDate', 'limit_date'), ('ReceivedAt', 'received_at'))})

    def _reward(self, row):
        return self.protocol.model('RewardInfo', {'Type': row['inventory_type'], 'Code': row['inventory_code'],
            'Count': row['amount'], 'DisplayPriority': 0})

    def get(self, request, is_history):
        session = self.players.session(request)
        self.players._state(session.player_id)
        box = self.players.repository.present_box(session.player_id,
            now=int(self.clock()), include_history=is_history)
        return {
            "UpdateAccumulateInfos": [],
            "Presents": [self._present(row) for row in box['presents']],
            "Histories": [self._present(row) for row in box['histories']],
        }

    def receive(self, request, present_ids):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None:
            raise LocalError('player_storage_unavailable', 503)
        with repository.transaction(session.player_id):
            # Read time after acquiring the player lock, including concurrent claims.
            now = int(self.clock())
            rows = {row['present_id']: row for row in repository.present_rows(session.player_id, present_ids)}
            received, expired, changed_codes = [], [], set()
            for present_id in present_ids:
                row = rows.get(present_id)
                if row is None:
                    raise LocalError('local_present_not_found', 404)
                if row['received_at'] is not None:
                    continue
                if row['arrived_at'] > now:
                    raise LocalError('local_present_not_arrived', 409)
                if row['limit_date'] is not None and row['limit_date'] <= now:
                    expired.append(self._reward(row))
                    continue
                # InventoryType.Item = 2, verified in dump.cs. Other reward rules need master data.
                if row['inventory_type'] != 2:
                    raise LocalError('local_present_reward_not_implemented', 501)
                try:
                    repository.apply_item_changes(session.player_id, 'present:' + present_id.hex(),
                                                  {row['inventory_code']: row['amount']})
                    repository.mark_present_received(session.player_id, present_id, now)
                except (InvalidPlayerData, OperationConflict) as exc:
                    raise LocalError('local_present_state_conflict', 409) from exc
                received.append(self._reward(row))
                changed_codes.add(row['inventory_code'])
            state = self.players._state(session.player_id)
            inventory = inventory_update(self.protocol, state, changed_codes)
            box = repository.present_box(session.player_id, now=now, include_history=False)
            return {'UpdateAccumulateInfos': [], 'InventoryUpdateInfo': inventory,
                'ReceivedPresents': received, 'ExpiredPresents': expired, 'ExcessPresents': [],
                'Presents': [self._present(row) for row in box['presents']],
                'HomeInfo': state.get('HomeInfo'), 'HomeCharacters': state.get('HomeCharacters', []),
                'TotalBattlePower': total_battle_power(self.players, self.protocol, session)}
