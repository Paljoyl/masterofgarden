"""Sanctuary responses from the current player's persisted run."""
from contextlib import contextmanager

from mog_protocol.codec import decode, encode
from PostgreSQL.dungeon2 import Dungeon2Store
from ..protocol import LocalError
from .inventory import inventory_update


class Dungeon2Service:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._store = None

    def store(self):
        if self.players.repository is None or self.players.timing is None:
            raise LocalError('player_storage_unavailable', 503)
        if self._store is None:
            self._store = Dungeon2Store(self.players.repository, self.protocol)
        return self._store

    @contextmanager
    def context(self, request, fields):
        session = self.players.session(request)
        store = self.store()
        with store.repo.transaction(session.player_id):
            state = self.players._state(session.player_id)
            template = self.players.templates.get((session.player_id, session.variant, '/gametop/getgametopinfo'))
            scores = (self.protocol.fields('GetGameTopInfoResponse', template)['Dungeon2GroupScores'] or []) if template else []
            now = store.timing._effective_now(session.player_id, int(self.players.clock()))
            run = store.require(session.player_id, now, fields.get('Dungeon2Code'), scores)
            yield session.player_id, store, run, state

    def query(self, request, kind, fields):
        with self.context(request, fields) as (player, store, run, state):
            result = {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', [])}
            if kind == 'info':
                result.update(store.info(player, run))
            elif kind == 'hierarchy':
                result['Dungeon2HierarchySquares'] = store.enter(player, run, fields['HierarchyIndex'])
            elif kind == 'square':
                result['Dungeon2HierarchySquare'] = store.square(player, run,
                    fields['HierarchyIndex'], fields['SquareIndex'])[1]
            elif kind == 'characters':
                result.update(Dungeon2Characters=run['state']['characters'], Dungeon2RentalCharacters=run['state']['rentals'])
            elif kind == 'enemies':
                result['Dungeon2Enemies'] = run['state']['enemies']
            elif kind == 'items':
                result['Dungeon2StackItems'] = [[int(code), count] for code, count in sorted(run['state']['items'].items())]
            elif kind == 'status':
                return store.battle_status(player, run, fields)
            elif kind == 'reset':
                store.reset(player, run)
            elif kind == 'complete':
                changed = store.complete(player, run, fields)
                state = self.players._state(player)
                result.update(UpdateAccumulateInfos=state.get('UpdateAccumulateInfos', []),
                    InventoryUpdateInfo=inventory_update(self.protocol, state, changed), TotalScore=run['score'])
            return result

    def result(self, request, fields):
        if (any(fields[name] is not None for name in ('EventBoss', 'GuildBattleBoss', 'StoryRaidResult')) or
                fields['EventBossBoostCount'] not in (0, 1) or fields['FreeChallengeCount']):
            raise LocalError('local_dungeon2_result_context_invalid', 400)
        info = self.protocol.fields('Dungeon2BattleResultInfo', fields['Dungeon2'], strict=True)
        with self.context(request, {'Dungeon2Code': info['Dungeon2Code']}) as (player, store, run, state):
            outcome = store.battle_result(player, run, fields)
            if outcome['retry']:
                result = self.protocol.fields('SetQuestResultResponse', decode(bytes.fromhex(outcome['response'])), strict=True)
            else:
                # Sanctuary rewards are claimed when completing a layer. This
                # battle response must not run ordinary stamina/XP/drop rules.
                result = {name: None for name in self.protocol.indices('SetQuestResultResponse')}
                result.update(Experience=0, StarCount=0, GuildBattleScore=0,
                    GuildBattleDamageMultiplier=0.0, UserEventPoint=0, AddEventGuildPoint=0)
            state = self.players._state(player)
            result['UpdateAccumulateInfos'] = state.get('UpdateAccumulateInfos', [])
            if not outcome['retry']:
                run['state']['battle']['response'] = encode(self.protocol.model('SetQuestResultResponse', result)).hex()
                store.save(player, run)
            return result
