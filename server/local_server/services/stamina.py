"""Return the committed stamina and all consumed item balances."""
from ..protocol import LocalError
from .inventory import inventory_update


class StaminaService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def recover(self, request, item_code, count):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None:
            raise LocalError('player_storage_unavailable', 503)
        store = repository.timing.stamina_recovery
        if store is None:
            raise LocalError('local_stamina_configuration_missing', 503)
        with repository.transaction(session.player_id):
            changed = store.recover(session.player_id, item_code, count, int(self.players.clock()))
            state = self.players._state(session.player_id)
            return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                    'InventoryUpdateInfo': inventory_update(self.protocol, state, changed)}
