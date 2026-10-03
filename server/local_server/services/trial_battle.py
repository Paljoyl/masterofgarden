"""Remove out-of-schedule training rentals from current player parties."""
from ..protocol import LocalError, integer, sequence


TRIAL_PARTY_TYPE = 15  # PartyType.TrialBattle in the installed client dump.
TRIAL_PARTY_COUNT = 5  # Installed game_setting_master.PARTY_COUNT.


class TrialBattleCatalog:
    def __init__(self, data):
        self.windows = {}
        try:
            rentals = data['trial_battle_rental_character_master']
            schedules = data['trial_battle_rental_schedules']
            if not isinstance(rentals, list) or not rentals or not isinstance(schedules, list) or not schedules:
                raise ValueError()
            windows = {}
            for row in schedules:
                code, start, end = row['Code'], row['StartAt'], row['EndAt']
                if not isinstance(code, str) or not code or code in windows or (
                        type(start) is not int or type(end) is not int or start > end):
                    raise ValueError()
                windows[code] = (start, end)
            for row in rentals:
                code = row['RentalCharacterCode']
                if type(code) is not int or code <= 0:
                    raise ValueError()
                self.windows.setdefault(code, []).append(windows[row['ScheduleCode']])
        except (KeyError, TypeError, ValueError) as exc:
            raise LocalError('local_trial_battle_definitions_invalid', 503) from exc

    def available(self, now):
        return {code for code, windows in self.windows.items()
                if any(start <= now <= end for start, end in windows)}


class TrialBattleService:
    def __init__(self, players, protocol):
        self.players, self.protocol = players, protocol
        self.catalog = None

    def _catalog(self):
        if self.catalog is None:
            db = getattr(self.players.repository, 'database', None)
            if db is None:
                raise LocalError('local_trial_battle_definitions_unavailable', 503)
            with db.lock:
                data = dict(db.connection.execute('''SELECT name,data FROM public.quest_definitions
                    WHERE name IN ('trial_battle_rental_character_master',
                                   'trial_battle_rental_schedules')''').fetchall())
            self.catalog = TrialBattleCatalog(data)
        return self.catalog

    def canonical_rentals(self, values):
        rentals = []
        codes = set()
        for value in sequence(values, maximum=5):
            fields = self.protocol.fields('RentalCharacterInfo', value, strict=True)
            code = integer(fields['RentalCharacterCode'], minimum=1)
            integer(fields['SwitchableCharacterIndex'], maximum=2**31 - 1)
            if code in codes:
                raise LocalError('duplicate_party_rental')
            codes.add(code)
            rentals.append(self.protocol.model('RentalCharacterInfo', fields))
        if codes and not codes <= self._catalog().available(int(self.players.clock())):
            raise LocalError('trial_rental_unavailable', 409)
        return rentals

    def cleanup(self, request):
        session = self.players.session(request)
        repository = self.players.repository
        if repository is None:
            raise LocalError('player_storage_unavailable', 503)
        with repository.transaction(session.player_id):
            state = self.players.state(request)
            parties = [party for party in state['Parties']
                       if self.protocol.fields('PartyInfo', party)['Type'] == TRIAL_PARTY_TYPE]
            # No configured rentals means no schedule data is needed to succeed.
            if not any(self.protocol.fields('PartyInfo', party)['RentalCharacterInfos'] for party in parties):
                return parties
            available = self._catalog().available(int(self.players.clock()))
            result = []
            for party in parties:
                fields = self.protocol.fields('PartyInfo', party)
                rentals = fields['RentalCharacterInfos']
                kept = [rental for rental in rentals
                        if self.protocol.fields('RentalCharacterInfo', rental)['RentalCharacterCode'] in available]
                if kept != rentals:
                    # Existing power includes removed rentals. The local server has
                    # no full power formula, so use the same invalidation as party edits.
                    party = self.protocol.model('PartyInfo', {'RentalCharacterInfos': kept, 'TotalPower': 0}, party)
                    repository.save_party(session.player_id, party)
                result.append(party)
            return result
