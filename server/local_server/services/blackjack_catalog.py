"""Installed TW blackjack sessions, coin items and payout settings."""
from decimal import Decimal, InvalidOperation

from PostgreSQL.game_time import unix
from ..protocol import LocalError, integer


class BlackjackCatalog:
    def __init__(self, timing):
        try:
            data = timing.data
            self.games = {row['Code']: row for row in data['mini_game_master']
                          if row['MiniGameType'] == 0}
            self.events = {row['Code']: row for row in data['blackjack_event_master']}
            self.schedules = {row['Code']: row for row in data['blackjack_schedule_master']}
            settings = {row['Key']: row['Value'] for row in data['blackjack_settings']}
            self.bet_limit = integer(int(settings['BLACKJACK_BET_LIMIT'][0]), minimum=1)
            self.profit_rate = Decimal(settings['BLACKJACK_RATE'][0])
            if not self.games or not self.profit_rate.is_finite() or not 0 < self.profit_rate <= 100:
                raise ValueError()
            for game in self.games.values():
                integer(game['CoinItemCode'], minimum=1)
                code = self.schedule_code(game)
                schedule = self.schedules[code]
                if schedule['Type'] != 0 or unix(schedule['StartAt']) >= unix(schedule['EndAt']):
                    raise ValueError()
        except (AttributeError, KeyError, IndexError, TypeError, ValueError, InvalidOperation, LocalError) as exc:
            raise LocalError('local_blackjack_configuration_invalid', 503) from exc

    def schedule_code(self, game):
        if game['IsNotEvent']:
            return game['ScheduleCode']
        return self.events[game['EventCode']]['ScheduleCodeInSession']

    def game(self, code):
        game = self.games.get(code)
        if game is None:
            raise LocalError('local_blackjack_game_not_found', 404)
        # Match the local historical event/box-lottery catalog: installed games
        # remain playable after official dates. Mission counters still obey their
        # own schedules in TimedState.event; opening a game never extends those.
        return game
