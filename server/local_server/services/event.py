"""Event home assembled from current local state and the existing shop service."""
from ..protocol import LocalError
from .inventory import inventory_update
from PostgreSQL.game_time import timestamp


class EventService:
    def __init__(self, players, protocol, shop):
        self.players, self.protocol, self.shop = players, protocol, shop

    def _event(self, code, *, sub=False):
        timing = self.players.timing
        table = 'sub_event_master' if sub else 'event_master'
        if timing is None or table not in timing.index:
            raise LocalError('local_event_configuration_missing', 503)
        if code not in timing.index[table]:
            raise LocalError('local_event_not_found', 404)
        return timing.index[table][code]

    def sub_top(self, request, code):
        session = self.players.session(request)
        self._event(code, sub=True)
        state = self.players._state(session.player_id)
        return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []), 'PromotionUrl': ''}

    def top(self, request, code):
        session = self.players.session(request)
        self._event(code)
        with self.players.repository.transaction(session.player_id):
            # TW PC ShopCategory.Event = 4. Reuse local selections and purchase
            # counts, while keeping unrelated exchange shops out of this page.
            shops = [row for row in self.shop.get(request, {4}, code)['ShopDisplays']
                     if self.shop.catalog.shops[row[0]]['RelatedEventCode'] == code]
            state = self.players._state(session.player_id)
            fields = {name: state[name] for name in ('Characters', 'StackItems', 'Equipments',
                'Parties', 'HomeInfo', 'HomeCharacters', 'ClearedQuests')}
            fields.update(UpdateAccumulateInfos=state.get('UpdateAccumulateInfos', []),
                Missions=state.get('MissionRewardReceivedInfos', []), ShopDisplays=shops,
                # Event battle points/score-reward settlement have no local store yet.
                # Opening the page must not grant rewards or import historical totals.
                UserEventPoint=0, PromotionUrl='',
                # A non-null reward with even an empty StackItems list triggers
                # the client's obtained-rewards popup. No settlement means nil.
                ScorePointReward=None,
                InventoryUpdateInfo=inventory_update(self.protocol, state))
            return fields

    def damage_ranking(self, request, code):
        session = self.players.session(request)
        self._event(code)
        state = self.players._state(session.player_id)
        user = self.protocol.fields('UserInfo', state['User'])
        character = next((self.protocol.fields('CharacterInfo', r) for r in state['Characters']
                          if r[0] == user['ProfileCharacterCode']), None)
        # AccumulateType.EventDamageRankingScore=64, Values=[EventCode].
        score_codes = {r['Code'] for r in self.players.timing.data.get('accumulate_master', [])
                       if r['Type'] == 64 and r['Values'] == [str(code)]}
        scores = [r for r in state.get('AccumulateInfos', []) if r[0] in score_codes]
        score = max(scores, key=lambda r: r[1], default=[0, 0, 0])
        return {'UpdateAccumulateInfos': state.get('UpdateAccumulateInfos', []),
            'DamageRankingScore': score[1], 'DamageRankingScoreUpdatedAt': timestamp(score[2]) if score[1] else None,
            # No shared competition results exist locally; do not invent a percentile.
            'RankPercent': None, 'DamageToNextGrade': None,
            'EventDamageRankingProfileInfo': self.protocol.model('EventDamageRankingProfileInfo', {
                'UserId': session.player_id, 'UserName': user['Name'],
                'ProfileCharacterCode': user['ProfileCharacterCode'], 'HonorCode': state.get('ProfileHonorCode') or None,
                'ProfileCharacterRank': character['Rank'] if character else 0,
                'ProfileCharacterRarity': character['Rarity'] if character else 0,
                'ProfileIllustrationIndex': user['ProfileIllustrationIndex'],
            })}
