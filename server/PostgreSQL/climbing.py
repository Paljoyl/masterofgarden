"""Persist World Tree progress and runtime state under the player transaction."""
from psycopg.types.json import Jsonb

from local_server.protocol import integer, sequence, text


class ClimbingStore:
    FIELDS = ('ClimbingMatchingEnemyInfos', 'ClearFloor', 'FloorBattleIndex',
              'ClimbingCharacterStatusInfos', 'RematchingCount',
              'ClimbingRentalCharacterStatusInfos', 'ReceivedRewardFloor', 'BeforeClearFloor')
    SELECT = '''SELECT matching_enemies,clear_floor,floor_battle_index,character_statuses,
        rematching_count,rental_character_statuses,received_reward_floor,before_clear_floor
        FROM public.player_climbing_state WHERE player_id=%s'''

    def __init__(self, repository, protocol):
        self.connection, self.protocol = repository.connection, protocol

    @staticmethod
    def fresh():
        # No battle or reward claim exists in a new local climbing run.
        return dict(ClimbingMatchingEnemyInfos=[], ClearFloor=0, FloorBattleIndex=0,
                    ClimbingCharacterStatusInfos=[], RematchingCount=0,
                    ClimbingRentalCharacterStatusInfos=[], ReceivedRewardFloor=0, BeforeClearFloor=0)

    def validate(self, fields):
        for name in ('ClearFloor', 'FloorBattleIndex', 'RematchingCount',
                     'ReceivedRewardFloor', 'BeforeClearFloor'):
            integer(fields[name], maximum=2**31 - 1)
        for name, model in (('ClimbingCharacterStatusInfos', 'ClimbingCharacterStatusInfo'),
                            ('ClimbingRentalCharacterStatusInfos', 'ClimbingRentalCharacterStatusInfo')):
            for value in sequence(fields[name]):
                row = self.protocol.fields(model, value, strict=True)
                integer(row['Code'], minimum=1)
                integer(row['Hp'], maximum=2**31 - 1)
                integer(row['Sp'], maximum=2**31 - 1)
        for value in sequence(fields['ClimbingMatchingEnemyInfos']):
            enemy = self.protocol.fields('ClimbingMatchingInfo', value, strict=True)
            text(enemy['UserId'], maximum=512)
            integer(enemy['FloorNumber'], minimum=1, maximum=2**31 - 1)
            integer(enemy['SyncLevel'], maximum=2**31 - 1)
            for value in sequence(enemy['ClimbingPartyInfos']):
                party = self.protocol.fields('ClimbingPartyInfo', value, strict=True)
                integer(party['No'], maximum=2**31 - 1)
                sequence(party['MagicItemEquipments'])
                for value in sequence(party['ClimbingPartyCharacterInfos']):
                    member = self.protocol.fields('ClimbingPartyCharacterInfo', value, strict=True)
                    character = self.protocol.fields('ClimbingCharacterInfo', member['ClimbingCharacterInfo'], strict=True)
                    integer(character['Code'], minimum=1)
                    integer(character['Rarity'], minimum=1, maximum=255)
                    integer(member['SwitchableCharacterIndex'], maximum=2**31 - 1)
        return fields

    def get(self, player_id):
        row = self.connection.execute(self.SELECT, (player_id,)).fetchone()
        return dict(zip(self.FIELDS, row)) if row is not None else None

    def seed(self, player_id, fields):
        self.validate(fields)
        values = [fields[name] for name in self.FIELDS]
        for index in (0, 3, 5):
            values[index] = Jsonb(values[index])
        self.connection.execute('''INSERT INTO public.player_climbing_state
            (player_id,matching_enemies,clear_floor,floor_battle_index,character_statuses,
             rematching_count,rental_character_statuses,received_reward_floor,before_clear_floor)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (player_id) DO NOTHING''', (player_id, *values))
        return self.get(player_id)

    def runtime(self, player_id):
        return self.connection.execute('''SELECT climbing_code,week_number,checked_at,run_state
            FROM public.player_climbing_state WHERE player_id=%s''', (player_id,)).fetchone()

    def save(self, player_id, fields, code, week, now, runtime):
        self.validate(fields)
        values = [fields[name] for name in self.FIELDS]
        for index in (0, 3, 5):
            values[index] = Jsonb(values[index])
        self.connection.execute('''UPDATE public.player_climbing_state SET matching_enemies=%s,
            clear_floor=%s,floor_battle_index=%s,character_statuses=%s,rematching_count=%s,
            rental_character_statuses=%s,received_reward_floor=%s,before_clear_floor=%s,
            climbing_code=%s,week_number=%s,checked_at=%s,run_state=%s WHERE player_id=%s''',
            (*values, code, week, now, Jsonb(runtime), player_id))

    def abandon(self, player_id):
        self.connection.execute("UPDATE public.player_climbing_battles SET state='abandoned' "
                                "WHERE player_id=%s AND state='active'", (player_id,))

    def matching_period(self, player_id):
        return self.connection.execute('''SELECT matching_climbing_code,matching_week_number
            FROM public.player_climbing_state WHERE player_id=%s''', (player_id,)).fetchone()

    def save_matching(self, player_id, matching, code, week):
        self.connection.execute('''UPDATE public.player_climbing_state SET matching_enemies=%s,
            matching_climbing_code=%s,matching_week_number=%s WHERE player_id=%s''',
            (Jsonb(matching), code, week, player_id))
