"""Garden response assembly shares the player's transaction with settlement."""
from PostgreSQL.players import InsufficientItems, OperationConflict
from PostgreSQL.player_protocol import InvalidPlayerData
from ..protocol import LocalError
from .inventory import inventory_update


class GardenService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol

    def run(self, request, action, *params):
        session = self.players.session(request)
        timing = self.players.timing
        store = timing.garden() if timing is not None else None
        if store is None:
            raise LocalError('local_garden_configuration_missing', 503)
        try:
            with store.repo.transaction(session.player_id):
                home = self.players.templates.get((session.player_id, session.variant, '/gametop/getgametopinfo'))
                store.initialize(session.player_id, int(self.players.clock()),
                                 self.protocol.fields('GetGameTopInfoResponse', home) if home is not None else None)
                now = store.prepare(session.player_id, int(self.players.clock()))
                if action == 'top':
                    store.timing.event(session.player_id, 74, now)
                    products, changed = [], set()
                elif action == 'room':
                    result = store.room(session.player_id, *params, now)
                    state = self.players._state(session.player_id)
                    return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], **result}
                else:
                    products, changed = store.mutation(session.player_id, action, params, now)
                state = self.players._state(session.player_id)
                garden = store.view(session.player_id, now)
                endpoint = self.protocol.registry.endpoint(request.method, request.path)
                supported = self.protocol.indices(endpoint['response'])
                fields = {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'], **garden,
                          'GardenProductItems': products,
                          'InventoryUpdateInfo': inventory_update(self.protocol, state, changed)}
                return {name: value for name, value in fields.items() if name in supported}
        except InsufficientItems as exc:
            raise LocalError('local_garden_insufficient_items', 409) from exc
        except (InvalidPlayerData, OperationConflict) as exc:
            raise LocalError('local_garden_state_invalid', 503) from exc
