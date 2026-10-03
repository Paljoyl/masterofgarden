"""Master lineups, explicit local odds and validated pool-specific probabilities."""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from fractions import Fraction
from math import lcm
import secrets

from ..protocol import LocalError, integer


class LotteryCatalog:
    def __init__(self, connection, clock):
        data = dict(connection.execute('SELECT name,data FROM public.lottery_definitions').fetchall())
        def load(name):
            rows = data.get(name)
            if not isinstance(rows, list) or not rows:
                raise LocalError('local_lottery_master_unavailable', 503)
            return rows
        self.clock = clock
        self.local_probabilities = {r['Code']: r for r in data.get('local_lottery_probability_master', [])}
        policies = data.get('local_lottery_probability_policy', [])
        self.probability_policy = policies[0] if policies else {}
        self.pools = {r['Code']: r for r in load('lottery_master')}
        self.settings = {r['Code']: r for r in load('lottery_settings_master')}
        self.characters = {r['Code']: r for r in load('character_master')}
        self.costumes = {r['Code']: r for r in load('home_character_costume_master')}
        self.shops = {r['Code']: r for r in load('shop_master')}
        self.bonuses = {r['Code']: r for r in load('lottery_bonus_master')}
        self.groups = {r['Code']: r for r in load('lottery_group_master')}
        self.steps = {r['LotteryCode']: r for r in load('lottery_step_master')}
        self.regular = {r['CharacterCode']: r for r in load('lottery_character_master')}
        self.pickups, self.special, self.bonus_rewards, self.rewards = (defaultdict(dict), defaultdict(dict),
                                                                      defaultdict(list), defaultdict(list))
        for row in load('lottery_pickup_master'):
            self.pickups[row['LotteryCode']][row['CharacterCode']] = row
        for row in load('lottery_special_lineup_master'):
            self.special[row['LotteryCode']][row['CharacterCode']] = row
        for row in load('lottery_bonus_reward_master'):
            self.bonus_rewards[row['Code']].append(row)
        for row in load('reward_master'):
            self.rewards[row['Code']].append(row)
        crystals = [r['ItemCode'] for r in load('character_enhancement_item_master') if r['ItemBehaviourType'] == 14]
        tickets = [r['ItemCode'] for r in load('money_item_master') if r['ItemBehaviourType'] == 12]
        if len(crystals) != 1 or len(tickets) != 1:
            raise LocalError('local_lottery_item_definition_invalid', 503)
        self.crystal, self.common_ticket = crystals[0], tickets[0]
        settings = {r['Key']: r['Value'] for r in load('game_setting_master')}
        try:
            self.duplicate_crystals = [int(v) for v in settings['CHARACTER_GET_CRYSTAL_ITEM_COUNT']]
            self.duplicate_limit = [int(v) for v in settings['CHARACTER_GET_LIMIT_BREAK_ITEM_COUNT']]
            self.history_count = int(settings['LOTTERY_HISTORY_COUNT'][0])
            self.history_days = int(settings['LOTTERY_HISTORY_DAY'][0])
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            raise LocalError('local_lottery_setting_invalid', 503) from exc

    def require(self, table, key):
        row = table.get(key)
        if row is None:
            raise LocalError('local_lottery_definition_missing', 503)
        return row

    def setting(self, pool):
        return self.require(self.settings, pool['LotterySettingsCode'])

    def selection_candidates(self, pool):
        return {code: row for code, row in self.pickups[pool['Code']].items()
                if row['PickupType'] == pool['SelectTargetPickup']}

    def validate_selection(self, pool, selected, *, complete=False):
        if pool['LotteryType'] != 1:
            raise LocalError('local_lottery_not_selectable', 409)
        candidates = self.selection_candidates(pool)
        if len(selected) != len(set(selected)) or any(code not in candidates for code in selected):
            raise LocalError('local_lottery_selection_invalid', 400)
        locked = {code for code, row in candidates.items() if row['IsSelectLock']}
        result = sorted(set(selected) | locked)
        if len(result) > pool['MaxSelectCount']:
            raise LocalError('local_lottery_selection_invalid', 400)
        if complete and len(result) != pool['MaxSelectCount']:
            raise LocalError('local_lottery_selection_required', 409)
        return result

    def lineup(self, pool, selected=None, *, preview=False):
        if pool['LotteryType'] == 1:
            selected = self.validate_selection(pool, selected or [], complete=not preview)
            if preview and len(selected) < pool['MaxSelectCount']:
                selected = list(self.selection_candidates(pool))
            # Selecting SS candidates must not remove the regular A/S draw slots.
            # The exclusion flag controls unselected regular SS characters.
            result = {code: row for code, row in self.regular.items()
                      if pool['SelectIncludeRegularLineup'] or row['Rarity'] < 3}
            result.update({code: row for code, row in self.pickups[pool['Code']].items()
                           if row['PickupType'] != pool['SelectTargetPickup'] or code in selected})
            return result
        if pool['LotteryType'] != 0:
            raise LocalError('local_lottery_type_not_implemented', 501)
        result = dict(self.special[pool['Code']]) if pool['SpecialLineup'] else dict(self.regular)
        if not pool['SpecialLineup']:
            result.update(self.pickups[pool['Code']])
        if not result:
            raise LocalError('local_lottery_lineup_missing', 503)
        return result

    def local_probability(self, protocol, code, lineup=None):
        """Build per-pool configured odds for the caller's actual lineup."""
        rule = self.local_probabilities.get(code)
        if rule is None:
            return None
        pool = self.require(self.pools, code)
        lineup_kind = ('selection' if pool['LotteryType'] == 1 else
                       'special' if pool['SpecialLineup'] else 'regular')
        if (rule.get('Distribution') not in ('uniform-within-rarity', 'weighted-pickup')
                or rule.get('Lineup', 'regular') != lineup_kind or pool['LotteryType'] not in (0, 1)):
            raise LocalError('local_lottery_probability_invalid', 503)
        lineup = lineup if lineup is not None else self.lineup(pool)
        if rule['Distribution'] == 'uniform-within-rarity' and any(
                row.get('PickupType', 0) != 0 for row in lineup.values()):
            raise LocalError('local_lottery_probability_invalid', 503)
        return self._probability_model(protocol, lineup,
            {0: rule.get('RarityChanceA'), 1: rule.get('RarityChanceB')}, rule.get('PickupShares', {}))

    @property
    def fallback_enabled(self):
        return self.probability_policy.get('Enabled') is True

    def fallback_probability(self, protocol, code, lineup=None, button=None):
        """Explicit simulation policy; do not pretend these are official rates."""
        if not self.fallback_enabled:
            return None
        pool = self.require(self.pools, code)
        lineup = lineup if lineup is not None else self.lineup(pool)
        rates = {0: self.probability_policy.get('RarityChanceA'),
                 1: self.probability_policy.get('RarityChanceB')}
        buttons = [button] if button is not None else self.setting(pool)['ButtonSettings']
        for kind, field in ((0, 'TimesA'), (1, 'TimesB')):
            guarantees = []
            for current in buttons:
                if not current[field]:
                    continue
                target = 1 if current['TimesB'] else 0
                rank = {4: 2, 5: 3}.get(current['AnnotationType'])
                if current['AnnotationType'] == 6:
                    rank = self.steps.get(code, {}).get('AppealRarity')
                guarantees.append(rank if target == kind and rank in (2, 3) else None)
            if guarantees and all(rank is not None for rank in guarantees):
                rank = min(guarantees)
                rates[kind] = ['0', '0', '100'] if rank == 3 else ['0', '97', '3']
        return self._probability_model(protocol, lineup, rates,
            self.probability_policy.get('PickupShares', {}), project=pool['LotteryType'] != 1)

    def _probability_model(self, protocol, lineup, rates_by_kind, pickup_shares, *, project=False):
        groups = defaultdict(list)
        for character in sorted(lineup):
            rank = self.require(self.characters, character)['DefaultRarity']
            if rank not in (1, 2, 3) or lineup[character].get('Rarity', rank) != rank:
                raise LocalError('local_lottery_probability_lineup_mismatch', 503)
            pickup = lineup[character].get('PickupType', 0)
            if pickup not in (0, 1, 2):
                raise LocalError('local_lottery_probability_invalid', 503)
            groups[(rank, pickup)].append(character)
        chances = {}
        for kind, values in rates_by_kind.items():
            if not isinstance(values, list) or len(values) != 3:
                raise LocalError('local_lottery_probability_invalid', 503)
            rates = [decimal_rate(value) for value in values]
            if sum(rates) != Decimal(100):
                raise LocalError('local_lottery_probability_invalid', 503)
            if project:
                available = [rank for rank in (1, 2, 3)
                             if rates[rank - 1] and any(groups[(rank, pickup)] for pickup in (0, 1, 2))]
                total = sum((rates[rank - 1] for rank in available), Decimal(0))
                if not total:
                    raise LocalError('local_lottery_probability_lineup_mismatch', 503)
                projected = [Decimal(0)] * 3
                for rank in available[:-1]:
                    projected[rank - 1] = (rates[rank - 1] * 100 / total).quantize(
                        Decimal('0.000000000001'), rounding=ROUND_DOWN)
                projected[available[-1] - 1] = 100 - sum(projected)
                rates = projected
            entries = []
            for rank, rate in enumerate(rates, 1):
                buckets = {pickup: groups[(rank, pickup)] for pickup in (0, 1, 2) if groups[(rank, pickup)]}
                if rate and not buckets:
                    raise LocalError('local_lottery_probability_lineup_mismatch', 503)
                if not buckets:
                    continue
                shares = {pickup: decimal_rate(pickup_shares.get(str(pickup), '0'))
                          for pickup in buckets if pickup}
                if sum(shares.values()) > 1:
                    raise LocalError('local_lottery_probability_invalid', 503)
                if 0 in buckets:
                    shares[0] = 1 - sum(shares.values())
                total_share = sum(shares.values())
                if rate and not total_share:
                    raise LocalError('local_lottery_probability_invalid', 503)
                for pickup, characters in buckets.items():
                    bucket_rate = rate * shares.get(pickup, 0) / total_share if total_share else Decimal(0)
                    per_character = (bucket_rate / len(characters)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
                    for character in characters:
                        entries.append(protocol.model('LotteryCharacterWinningChanceInfo', {
                            'CharacterCode': character, 'Rarity': rank,
                            'WinningChance': format(per_character, 'f'), 'IsPickUp': pickup != 0}))
            chances[kind] = protocol.model('LotteryWinningChanceInfo', {
                'RarityChance': [format(rate, 'f') for rate in rates], 'LotteryCharacterWinningChances': entries})
        return protocol.model('GetLotteryWinningChanceResponse', {
            'UpdateAccumulateInfos': [], 'LotteryWinningChances': chances})

    def period(self, reset, now):
        if reset == 0:
            return 0
        if reset == 1:
            return self.clock.day(now)
        if reset == 2:
            dt = datetime.fromtimestamp(now - self.clock.day_offset, timezone.utc)
            return dt.year * 12 + dt.month
        if reset == 3:
            return self.clock.week(now)
        raise LocalError('local_lottery_reset_not_implemented', 501)

    def button(self, pool, index):
        row = next((r for r in self.setting(pool)['ButtonSettings'] if r['ButtonIndex'] == index), None)
        if row is None:
            raise LocalError('local_lottery_button_not_found', 404)
        for key in ('ConsumeItemCode', 'ConsumeCount', 'SubConsumeItemCode', 'SubConsumeCount',
                    'CommonTicketCount', 'TimesA', 'TimesB', 'LimittedTime'):
            integer(row[key], maximum=2**31 - 1 if key != 'ConsumeItemCode' and key != 'SubConsumeItemCode' else 2**63 - 1)
        if not 1 <= row['TimesA'] + row['TimesB'] <= 100:
            raise LocalError('local_lottery_draw_count_invalid', 503)
        return row


def decimal_rate(value):
    # MessagePack-CSharp DecimalFormatter serializes decimals as strings;
    # do not put float64 values into the client's Decimal fields.
    if not isinstance(value, str) or len(value) > 40:
        raise LocalError('local_lottery_probability_invalid', 503)
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise LocalError('local_lottery_probability_invalid', 503) from exc
    if not result.is_finite() or result < 0 or result > 100 or result.as_tuple().exponent < -12:
        raise LocalError('local_lottery_probability_invalid', 503)
    return result


def weights(values):
    fractions = [Fraction(v) for v in values]
    denominator = lcm(*(v.denominator for v in fractions))
    result = [v.numerator * (denominator // v.denominator) for v in fractions]
    if not result or sum(result) <= 0:
        raise LocalError('local_lottery_probability_invalid', 503)
    return result


def choose(entries, rates):
    target = secrets.randbelow(sum(rates))
    for entry, rate in zip(entries, rates):
        target -= rate
        if target < 0:
            return entry
    raise LocalError('local_lottery_probability_invalid', 503)


def probability_fields(protocol, model, value):
    try:
        return protocol.fields(model, value, strict=True)
    except LocalError as exc:
        raise LocalError('local_lottery_probability_invalid', 503) from exc


class LotteryProbability:
    def __init__(self, protocol, response, lineup, characters, times):
        self.distributions = {}
        fields = probability_fields(protocol, 'GetLotteryWinningChanceResponse', response)
        chances = fields['LotteryWinningChances']
        if not isinstance(chances, dict):
            raise LocalError('local_lottery_probability_invalid', 503)
        for kind in times:
            value = chances.get(kind)
            if value is None:
                raise LocalError('local_lottery_probability_missing', 503)
            info = probability_fields(protocol, 'LotteryWinningChanceInfo', value)
            rarity = info['RarityChance']
            if not isinstance(rarity, list) or len(rarity) != 3:
                raise LocalError('local_lottery_probability_invalid', 503)
            rarity_rates = [decimal_rate(v) for v in rarity]
            if sum(rarity_rates) != Decimal(100):
                raise LocalError('local_lottery_probability_invalid', 503)
            groups = defaultdict(list)
            group_sizes = defaultdict(int)
            seen = set()
            entries = info['LotteryCharacterWinningChances']
            if not isinstance(entries, list):
                raise LocalError('local_lottery_probability_invalid', 503)
            for value in entries:
                row = probability_fields(protocol, 'LotteryCharacterWinningChanceInfo', value)
                code, rank = row['CharacterCode'], row['Rarity']
                if (type(code) is not int or type(rank) is not int or code in seen
                        or code not in lineup or code not in characters or rank not in (1, 2, 3)
                        or characters[code]['DefaultRarity'] != rank or type(row['IsPickUp']) is not bool):
                    raise LocalError('local_lottery_probability_lineup_mismatch', 503)
                seen.add(code)
                group_sizes[rank] += 1
                rate = decimal_rate(row['WinningChance'])
                if rate:
                    groups[rank].append((code, rate))
            if seen != set(lineup):
                raise LocalError('local_lottery_probability_lineup_mismatch', 503)
            character_rates = {}
            for rank, rate in enumerate(rarity_rates, 1):
                # Official character percentages can be truncated to four places:
                # pool 13002005 advertises 4.5% SS, while 61 displayed entries
                # sum to 4.4957%. Each entry may lose less than 0.0001 percentage
                # points. Also accept nearest rounding used in other responses.
                # Rarity weights remain the exact advertised totals.
                advertised = sum((r for _, r in groups[rank]), Decimal(0))
                loss = rate - advertised
                if (loss > Decimal('0.0001') * group_sizes[rank]
                        or loss < -Decimal('0.00005') * group_sizes[rank]):
                    raise LocalError('local_lottery_probability_invalid', 503)
                if rate and not groups[rank]:
                    raise LocalError('local_lottery_probability_invalid', 503)
                if not rate and groups[rank]:
                    raise LocalError('local_lottery_probability_invalid', 503)
                if rate:
                    codes, rates = zip(*groups[rank])
                    character_rates[rank] = (codes, weights(rates))
            self.distributions[kind] = (weights(rarity_rates), character_rates)

    def draw(self, kind):
        rarity_weights, groups = self.distributions[kind]
        rank = choose((1, 2, 3), rarity_weights)
        codes, rates = groups[rank]
        return choose(codes, rates)
