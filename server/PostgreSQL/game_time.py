"""Game periods and offline recovery using verified client master settings."""
from datetime import datetime

import msgpack


WEEKDAYS = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6}


def utc_time_of_day(value):
    dt = datetime.strptime(value, '%Y/%m/%d %H:%M:%S %z')
    return (dt.hour * 3600 + dt.minute * 60 + dt.second -
            int(dt.utcoffset().total_seconds())) % 86400


def inside_daily_window(now, values):
    start, end = map(utc_time_of_day, values)
    second = now % 86400
    return start <= second <= end if start <= end else second >= start or second <= end


def unix(value):
    if isinstance(value, msgpack.Timestamp):
        return value.seconds
    if isinstance(value, dict) and 'unix' in value:
        return int(value['unix'])
    if isinstance(value, list):
        # MessagePack-CSharp DateTimeOffset stores local wall time as a Timestamp,
        # followed by the offset in minutes. The Timestamp alone is not UTC.
        return unix(value[0]) - int(value[1]) * 60
    return int(value)


def timestamp(value):
    return msgpack.Timestamp(int(value), 0)


class GameTime:
    def __init__(self, settings):
        required = {'TIME_FOR_END_OF_DAY', 'WEEK_FOR_END_OF_WEEK',
                    'BATTLE_PASS_TIME_FOR_END_OF_DAY', 'BATTLE_PASS_WEEK_FOR_END_OF_WEEK',
                    'STAMINA_AUTO_HEAL_INTERVAL', 'STAMINA_LIMIT',
                    'QUIZZES_PER_CHARACTER', 'BATTLE_PASS_LEVEL_UP_POINT'}
        # Full master settings also contain legitimate empty item-code/count lists.
        # Read scalar values only for the time settings this module consumes.
        values = {row['Key']: row['Value'][0] for row in settings
                  if row['Key'] in required and row['Value']}
        if required - values.keys():
            raise ValueError('Incomplete game time settings')
        def boundary(key):
            # Master time strings include their UTC offset; never use host local time.
            dt = datetime.strptime(values[key], '%Y/%m/%d %H:%M:%S %z')
            return dt.hour * 3600 + dt.minute * 60 - int(dt.utcoffset().total_seconds())
        self.day_offset = boundary('TIME_FOR_END_OF_DAY')
        self.weekday = WEEKDAYS[values['WEEK_FOR_END_OF_WEEK']]
        self.pass_day_offset = boundary('BATTLE_PASS_TIME_FOR_END_OF_DAY')
        self.pass_weekday = WEEKDAYS[values['BATTLE_PASS_WEEK_FOR_END_OF_WEEK']]
        self.stamina_interval = int(values['STAMINA_AUTO_HEAL_INTERVAL']) * 60
        self.stamina_limit = int(values['STAMINA_LIMIT'])
        self.quiz_limit = int(values['QUIZZES_PER_CHARACTER'])
        self.pass_level_point = int(values['BATTLE_PASS_LEVEL_UP_POINT'])

    def day(self, now):
        return (now - self.day_offset) // 86400

    def week(self, now, *, battle_pass=False):
        offset = self.pass_day_offset if battle_pass else self.day_offset
        weekday = self.pass_weekday if battle_pass else self.weekday
        # Unix epoch is Thursday; shifted date retains the configured local weekday.
        anchor = (weekday - 3) % 7
        return ((now - offset) // 86400 - anchor) // 7

    def period(self, reset_type, now):
        return {0: lambda: 0, 1: lambda: self.day(now), 2: lambda: self.week(now),
                3: lambda: self.week(now, battle_pass=True)}[reset_type]()


def recover_stamina(value, updated_at, now, cap, interval):
    """Keep partial ticks, cap natural recovery, and never reduce over-cap stamina."""
    if now < updated_at:
        return value, updated_at
    if value >= cap:
        return value, now
    ticks = (now - updated_at) // interval
    recovered = min(ticks, cap - value)
    value += recovered
    return value, now if value >= cap else updated_at + recovered * interval
