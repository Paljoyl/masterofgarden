"""Ordinary battle settlement tied to the player's saved quest-start session."""
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
from secrets import randbelow

from mog_protocol.codec import encode
from PostgreSQL.quest import QuestStore
from ..protocol import LocalError, integer, sequence
from .character_catalog import CharacterCatalog
from .inventory import inventory_update


class QuestResultService:
    def __init__(self, quests):
        self.quests = quests
        self.players, self.protocol = quests.players, quests.protocol
        self._drops = None
        self._catalog = None

    @property
    def repository(self):
        return self.quests.repository

    def configuration(self):
        if self._drops is None:
            data = dict(self.repository.connection.execute('SELECT name,data FROM public.quest_definitions').fetchall())
            if not data.get('quest_drop_master') or not data.get('game_setting_master'):
                raise LocalError('local_quest_result_configuration_missing', 503)
            self._drops = defaultdict(list)
            for row in data['quest_drop_master']:
                self._drops[row['Code']].append(row)
            settings = {r['Key']: r['Value'] for r in data['game_setting_master']}
            self.star_seconds = int(settings['QUEST_GET_STAR_TIME'][0])
            self.level_stamina = int(settings['STAMINA_RECOVERY_VALUE_BY_LEVEL_UP'][0])
        if self._catalog is None:
            self._catalog = CharacterCatalog(self.repository.connection)
        return self._catalog

    def drop(self, code):
        if not code:
            return [[]]
        rows = self._drops.get(code)
        if not rows:
            raise LocalError('local_quest_drop_configuration_missing', 503)
        items = defaultdict(int)
        for row in sorted(rows, key=lambda r: r['DisplayPriority']):
            if row['GuildBattleBossCode']:
                raise LocalError('local_quest_drop_type_not_implemented', 501)
            item = integer(row['ItemCode'], minimum=1)
            amount = integer(row['DropAmount'], minimum=1)
            chance = Decimal(str(row['DropChance']['Percent']))
            if not chance.is_finite() or not 0 <= chance <= 100:
                raise LocalError('local_quest_drop_configuration_invalid', 503)
            # Quest drop percentages are independent item rolls, not a gacha
            # distribution. Preserve the master decimal precision exactly.
            scale = 10 ** max(0, -chance.as_tuple().exponent)
            if randbelow(100 * scale) < int(chance * scale):
                items[item] += amount
        return self.protocol.model('QuestDropInfo', {'DropItems': [
            self.protocol.model('DropItemResultViewInfo', {'ItemCode': c, 'Count': n, 'BoxItemCode': None})
            for c, n in items.items()]})

    def party(self, fields, suspension, quest):
        training = quest['QuestType'] == 1
        expected = (self.quests.training_members(quest) if training else
                    {r[0] for r in suspension[1]})
        health = {}
        for value in sequence(fields['Party'], maximum=5):
            row = self.protocol.fields('QuestPartyCharacterInfo', value, strict=True)
            code = integer(row['CharacterCode'], minimum=1)
            if code not in expected or code in health:
                raise LocalError('local_quest_result_party_mismatch')
            health[code] = integer(row['Health'])
        if set(health) != expected:
            # Retire may omit the party because no result screen is presented.
            if fields['Result'] != 3 or health:
                raise LocalError('local_quest_result_party_mismatch')
        if fields['Result'] == 1 and not any(health.values()):
            raise LocalError('local_quest_result_health_invalid')
        # Scripted lesson actors never become owned characters or receive
        # owned-character XP. HP still determines the lesson's clear stars.
        return health, set() if training else expected

    def response(self, player_id, code, group_code, members, changed, drops, stars):
        state = self.players._state(player_id)
        user = self.protocol.fields('UserInfo', state['User'])
        quest = next((r for r in state['ClearedQuests'] if r[0] == code), [code, 0, 0, None, None])
        group = next((r for r in state['QuestGroups'] if r[0] == group_code), [group_code, 0, None, None])
        count = next((r for r in state['QuestClearCounts'] if r[0] == code), [code, 0])
        return {'UpdateAccumulateInfos': state['UpdateAccumulateInfos'],
                'DropEverytime': drops[0], 'DropFirstClear': drops[1], 'DropComplete': drops[2],
                'Characters': [r for r in state['Characters'] if r[0] in members],
                'Stamina': user['Stamina'], 'Experience': user['Experience'], 'StarCount': stars,
                'QuestInfo': quest, 'QuestGroupInfo': group, 'QuestClearCountInfo': count,
                'InventoryUpdateInfo': inventory_update(self.protocol, state, changed),
                'GuildBattleScore': 0, 'GuildBattleDamageMultiplier': 0.0, 'UserEventPoint': 0,
                'QuestEventDamageRankingInfo': None, 'AddEventGuildPoint': 0}

    def defeat_response(self, player_id):
        # Official TW capture 20261002-000848: Result=Lose returns nullable
        # settlement objects as null, not hydrated current balances/progress.
        state = self.players._state(player_id)
        result = {name: None for name in self.protocol.indices('SetQuestResultResponse')}
        result.update(UpdateAccumulateInfos=state['UpdateAccumulateInfos'], Experience=0, StarCount=0,
                      GuildBattleScore=0, GuildBattleDamageMultiplier=0.0, UserEventPoint=0,
                      AddEventGuildPoint=0)
        return result

    def result(self, request, fields):
        session = self.players.session(request)
        player_id, unique_id, code = session.player_id, fields['QuestUniqueId'], fields['QuestCode']
        digest = sha256(encode(fields)).hexdigest()
        with self.repository.transaction(player_id):
            store = QuestStore(self.repository)
            suspension, cost, previous = store.result_session(player_id, unique_id, code, digest)
            quest = self.quests.definitions['quests'].get(code)
            if quest is None:
                raise LocalError('local_quest_configuration_missing', 503)
            group_code = quest['QuestGroupCode']
            health, members = self.party(fields, suspension, quest)
            if previous is not None:
                if fields['Result'] == 2:
                    return self.defeat_response(player_id)
                saved = self.protocol.fields('SetQuestResultResponse', previous)
                changed = {r[0] for r in self.protocol.fields('InventoryUpdateInfo', saved['InventoryUpdateInfo'])['StackItems']}
                return self.response(player_id, code, group_code, members, changed,
                    [saved['DropEverytime'], saved['DropFirstClear'], saved['DropComplete']], saved['StarCount'])
            training_raid = (quest['QuestType'] == 1
                             and self.quests.definitions['groups'][group_code]['Category'] == 14)
            if (any(fields[name] is not None for name in ('Dungeon2', 'EventBoss', 'GuildBattleBoss'))
                    or (fields['StoryRaidResult'] is not None and not training_raid)
                    or fields['EventBossBoostCount'] not in (0, 1) or fields['FreeChallengeCount']):
                raise LocalError('local_quest_special_battle_not_implemented', 501)
            if fields['StoryRaidResult'] is not None:
                # The scripted raid lesson can report damage, but it settles
                # only lesson completion, never shared raid HP, points or rank.
                raid = self.protocol.fields('StoryRaidResultInfo', fields['StoryRaidResult'], strict=True)
                if raid['BossDamage'] is not None:
                    self.protocol.fields('BossDamageInfo', raid['BossDamage'], strict=True)
            if fields['Result'] not in (1, 2, 3):
                raise LocalError('local_quest_result_type_not_implemented', 501)
            if fields['Result'] == 2:
                result = self.defeat_response(player_id)
                now = self.players.timing._effective_now(player_id, int(self.players.clock()))
                # Start did not spend stamina. Losing grants no rewards and
                # closes the session without introducing a new charge/refund.
                store.finish(player_id, unique_id, digest,
                             self.protocol.model('SetQuestResultResponse', result), now)
                return result
            catalog = self.configuration()
            state = self.players._state(player_id)
            now = self.players.timing._effective_now(player_id, int(self.players.clock()))
            user = self.protocol.fields('UserInfo', state['User'])
            stars, changed, drops = 0, set(), [[[]], [[]], [[]]]
            key = 'quest-result:' + unique_id.hex()
            if fields['Result'] == 1:
                if quest['RewardCloseness']:
                    raise LocalError('local_quest_closeness_reward_not_implemented', 501)
                if user['Stamina'] is None or self.players.timing.stamina_recovery is None:
                    raise LocalError('local_stamina_state_missing', 503)
                stamina = self.protocol.fields('Stamina', user['Stamina'])
                if stamina['Value'] < cost:
                    raise LocalError('local_quest_insufficient_stamina', 409)
                challenges = self.players.timing.quest_challenges
                if challenges is None:
                    raise LocalError('local_quest_configuration_missing', 503)
                # The same transaction settles the allowance and all rewards;
                # rejected results roll both back. Retry responses bypass this.
                challenges.consume(player_id, quest, now)
                old = next((r for r in state['ClearedQuests'] if r[0] == code), [code, 0, 0, None, None])
                stars = 1 + int(all(health.values())) + int(fields['ClearSeconds'] <= self.star_seconds)
                drops[0] = self.drop(quest['QuestDropCodeForEverytime'])
                if not old[1]:
                    drops[1] = self.drop(quest['QuestDropCodeForFirstClear'])
                if stars == 3 and old[2] < 3:
                    drops[2] = self.drop(quest['QuestDropCodeForComplete'])
                xp, changes = self.grant(player_id, quest, cost, 1, drops, user, now, key)
                changed = set(changes)
                changed.add(390000001)  # XP and its mirrored stack balance change together.
                for value in state['Characters']:
                    if value[0] not in members:
                        continue
                    character = self.protocol.fields('CharacterInfo', value)
                    curve, limit = catalog.curve(character, xp['level'])
                    experience = max(character['Exp'], min(character['Exp'] + integer(quest['RewardCharacterExp']), limit))
                    level = max(character['Level'], max(r['Level'] for r in curve if r['TotalExp'] <= experience))
                    self.repository.update_character(player_id, value[0], experience=experience, level=level)
                    if level > character['Level']:
                        self.players.timing.event(player_id, 9, now, amount=level - character['Level'])
                self.progress(player_id, quest, stars, old[1] == 0, now)
            progress = user['TutorialProgressInfo']
            if fields['TutorialProgress'] > (progress[0] if progress else 0):
                self.repository.update_player(player_id, tutorial_progress=fields['TutorialProgress'])
            result = self.response(player_id, code, group_code, members, changed, drops, stars)
            store.finish(player_id, unique_id, digest, self.protocol.model('SetQuestResultResponse', result), now)
            return result

    def grant(self, player_id, quest, cost, count, drops, user, now, key):
        """Shared ordinary battle/skip inventory and player-level settlement."""
        catalog = self.configuration()
        if user['Stamina'] is None or self.players.timing.stamina_recovery is None:
            raise LocalError('local_stamina_state_missing', 503)
        stamina = self.protocol.fields('Stamina', user['Stamina'])
        if stamina['Value'] < cost:
            raise LocalError('local_quest_insufficient_stamina', 409)
        changes = defaultdict(int)
        changes[catalog.currency] += integer(quest['RewardCurrency']) * count
        for drop in drops:
            for item, amount, _ in drop[0]:
                changes[item] += amount
        xp = self.repository.apply_player_experience(player_id, key + ':xp', integer(quest['RewardUserExp']) * count)
        level_gain = xp['level'] - xp['previous_level']
        recovered = min(level_gain * self.level_stamina,
            max(0, self.players.timing.clock.stamina_limit - (stamina['Value'] - cost)))
        changes[390000002] += recovered - cost
        changes = {c: n for c, n in changes.items() if n}
        if changes:
            self.repository.apply_item_changes(player_id, key + ':items', changes)
        if cost or recovered:
            # Preserve an existing partial recovery tick unless a level-up
            # refills stamina or spending brings over-cap stamina below the cap.
            if recovered or stamina['Value'] >= self.players.timing.level_caps[user['Level']]:
                self.repository.connection.execute('''UPDATE public.player_stamina SET updated_at=%s
                    WHERE player_id=%s AND kind='normal' ''', (now, player_id))
            self.players.timing.stamina_recovery.mirror(player_id)
        if cost:
            self.players.timing.event(player_id, 55, now, amount=cost)
        for item, amount in changes.items():
            if amount > 0:
                self.players.timing.event(player_id, 56, now, values=(str(item),), amount=amount)
        return xp, changes

    def progress(self, player_id, quest, stars, first_clear, now, *, amount=1):
        connection = self.repository.connection
        code, group_code = quest['Code'], quest['QuestGroupCode']
        connection.execute('''INSERT INTO public.quests(player_id,quest_code,clear_count,star_count)
            VALUES (%s,%s,%s,%s) ON CONFLICT(player_id,quest_code) DO UPDATE
            SET clear_count=quests.clear_count+EXCLUDED.clear_count,star_count=GREATEST(quests.star_count,EXCLUDED.star_count)''',
            (player_id, code, amount, stars))
        connection.execute('''INSERT INTO public.quest_groups(player_id,quest_group_code,clear_count)
            VALUES (%s,%s,%s) ON CONFLICT(player_id,quest_group_code) DO UPDATE
            SET clear_count=quest_groups.clear_count+EXCLUDED.clear_count''',
            (player_id, group_code, int(first_clear)))
        connection.execute('''INSERT INTO public.quest_clear_counts(player_id,quest_code,count)
            VALUES (%s,%s,%s) ON CONFLICT(player_id,quest_code) DO UPDATE SET count=quest_clear_counts.count+EXCLUDED.count''',
            (player_id, code, amount))
        group = self.quests.definitions['groups'][group_code]
        for kind, values in ((25, ()), (26, (str(code),)), (27, (str(group_code),)),
                             (28, (str(group['Difficulty']),)), (29, (str(group['Category']),))):
            self.players.timing.event(player_id, kind, now, values=values, amount=amount)
        if first_clear:
            self.players.timing.event(player_id, 21, now)
            self.players.timing.event(player_id, 23, now, values=(str(code),))
