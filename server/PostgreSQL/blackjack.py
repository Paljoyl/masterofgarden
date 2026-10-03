"""Durable player-owned decks; callers hold the existing player transaction lock."""


class BlackjackStore:
    FIELDS = ('game_code', 'variant', 'bet', 'coin_item_code', 'profit_rate',
              'cards', 'state', 'action', 'hit_num', 'result', 'payout')

    def __init__(self, repository):
        self.connection = repository.connection

    def get(self, player_id, unique_id):
        row = self.connection.execute('''SELECT game_code,client_variant,bet,coin_item_code,
            profit_rate,cards,state,settlement_action,hit_num,result,payout
            FROM public.player_blackjack_rounds WHERE player_id=%s AND unique_id=%s''',
            (player_id, unique_id)).fetchone()
        return dict(zip(self.FIELDS, row)) if row is not None else None

    def create(self, player_id, unique_id, code, variant, bet, coin, rate, cards, now):
        # A client restarted during a round has no resume endpoint. Starting a new
        # round forfeits the previous stake, without refunding or reusing its deck.
        self.connection.execute('''UPDATE public.player_blackjack_rounds
            SET state='abandoned',finished_at=%s WHERE player_id=%s AND state='active' ''',
            (now, player_id))
        self.connection.execute('''INSERT INTO public.player_blackjack_rounds
            (player_id,unique_id,game_code,client_variant,bet,coin_item_code,profit_rate,cards,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (player_id, unique_id, code, variant, bet, coin, rate, cards, now))

    def finish(self, player_id, unique_id, action, hits, result, payout, now):
        self.connection.execute('''UPDATE public.player_blackjack_rounds SET state='settled',
            settlement_action=%s,hit_num=%s,result=%s,payout=%s,finished_at=%s
            WHERE player_id=%s AND unique_id=%s AND state='active' ''',
            (action, hits, result, payout, now, player_id, unique_id))
