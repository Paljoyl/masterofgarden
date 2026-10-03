"""Blackjack rules matched to the installed client, with atomic coin settlement."""
from secrets import SystemRandom

from PostgreSQL.blackjack import BlackjackStore
from .blackjack_catalog import BlackjackCatalog
from .inventory import inventory_update
from ..protocol import LocalError, integer


WIN, LOSE, DRAW = 1, 2, 3


def score(cards):
    # CardModel: Num=(CardId-1)%13+1. Face cards count ten; one ace can
    # count eleven when the sum with every ace counting one allows it.
    ranks = [(card - 1) % 13 + 1 for card in cards]
    total = sum(min(rank, 10) for rank in ranks)
    return total + 10 if 1 in ranks and total + 10 <= 21 else total


def outcome(cards, hits):
    # StartGameAsync deals player/dealer/player/dealer, then the player
    # consumes HitNum cards and the dealer draws until reaching 17.
    player, dealer = [cards[0], cards[2]], [cards[1], cards[3]]
    cursor = 4
    for _ in range(hits):
        if score(player) >= 21 or cursor >= len(cards):
            raise LocalError('local_blackjack_invalid_hit_count', 409)
        player.append(cards[cursor])
        cursor += 1
    player_score = score(player)
    while score(dealer) < 17:
        if cursor >= len(cards):
            raise LocalError('local_blackjack_deck_exhausted', 409)
        dealer.append(cards[cursor])
        cursor += 1
    dealer_score = score(dealer)
    natural = len(player) == 2 and player_score == 21
    dealer_natural = len(dealer) == 2 and dealer_score == 21
    if player_score > 21:
        result = LOSE
    elif natural or dealer_natural:
        result = DRAW if natural and dealer_natural else WIN if natural else LOSE
    elif dealer_score > 21 or player_score > dealer_score:
        result = WIN
    elif player_score < dealer_score:
        result = LOSE
    else:
        result = DRAW
    return result, natural


class BlackjackService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self._catalog = None
        self._store = None

    def resources(self):
        repository = self.players.repository
        if repository is None or not hasattr(repository, 'connection'):
            raise LocalError('player_storage_unavailable', 503)
        if self._catalog is None:
            self._catalog = BlackjackCatalog(self.players.timing)
        if self._store is None:
            self._store = BlackjackStore(repository)
        return repository, self._catalog, self._store

    @staticmethod
    def check_round(round_, session, code):
        if round_['game_code'] != code or round_['variant'] != session.variant:
            raise LocalError('local_blackjack_round_identity_conflict', 409)
        if round_['state'] == 'abandoned':
            raise LocalError('local_blackjack_round_abandoned', 409)

    def response(self, player_id, coin, **fields):
        # Retry responses use today's absolute inventory, never an old balance
        # from before a later round or a shop purchase.
        state = self.players._state(player_id)
        return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
                'InventoryUpdateInfo': inventory_update(self.protocol, state, {coin}), **fields}

    def consume(self, repository, player_id, key, coin, amount, code, now):
        repository.apply_item_changes(player_id, key, {coin: -amount})
        timing = self.players.timing
        timing.event(player_id, 71, now, values=(str(code),), amount=amount)
        timing.event(player_id, 57, now, values=(str(coin),), amount=amount)

    def deal(self, request, code, bet, unique_id):
        session = self.players.session(request)
        repository, catalog, store = self.resources()
        with repository.transaction(session.player_id):
            round_ = store.get(session.player_id, unique_id)
            if round_ is not None:
                self.check_round(round_, session, code)
                if round_['bet'] != bet:
                    raise LocalError('local_blackjack_bet_conflict', 409)
                return self.response(session.player_id, round_['coin_item_code'], Cards=round_['cards'])
            if bet > catalog.bet_limit:
                raise LocalError('local_blackjack_bet_limit_exceeded')
            self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            game = catalog.game(code)
            cards = list(range(1, 53))
            SystemRandom().shuffle(cards)
            coin = game['CoinItemCode']
            self.consume(repository, session.player_id, 'blackjack:deal:' + unique_id,
                         coin, bet, code, now)
            store.create(session.player_id, unique_id, code, session.variant, bet,
                         coin, catalog.profit_rate, cards, now)
            self.players.timing.event(session.player_id, 70, now)
            return self.response(session.player_id, coin, Cards=cards)

    def settle(self, request, code, unique_id, *, hits=0, double=False):
        session = self.players.session(request)
        repository, _, store = self.resources()
        with repository.transaction(session.player_id):
            round_ = store.get(session.player_id, unique_id)
            if round_ is None:
                raise LocalError('local_blackjack_round_not_found', 404)
            self.check_round(round_, session, code)
            action, effective_hits = ('double', 1) if double else ('result', hits)
            if round_['state'] == 'settled':
                if round_['action'] != action or round_['hit_num'] != effective_hits:
                    raise LocalError('local_blackjack_settlement_conflict', 409)
                return self.response(session.player_id, round_['coin_item_code'], Result=round_['result'])
            # Coin, bet, deck and payout rate are immutable values saved at deal.
            self.players._state(session.player_id)
            now = self.players.timing._effective_now(session.player_id, int(self.players.clock()))
            cards, bet, coin = round_['cards'], round_['bet'], round_['coin_item_code']
            if double and score([cards[0], cards[2]]) >= 21:
                raise LocalError('local_blackjack_double_unavailable', 409)
            result, natural = outcome(cards, effective_hits)
            stake = bet * (2 if double else 1)
            if result == WIN:
                payout = bet + int(bet * round_['profit_rate']) if natural else stake * 2
            elif result == DRAW:
                payout = stake
            else:
                payout = 0
            integer(payout)
            if double:
                self.consume(repository, session.player_id, 'blackjack:double:' + unique_id,
                             coin, bet, code, now)
            if payout:
                repository.apply_item_changes(session.player_id, 'blackjack:payout:' + unique_id, {coin: payout})
                self.players.timing.event(session.player_id, 56, now, values=(str(coin),), amount=payout)
            store.finish(session.player_id, unique_id, action, effective_hits, result, payout, now)
            return self.response(session.player_id, coin, Result=result)
