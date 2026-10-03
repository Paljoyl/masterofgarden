"""Story read settlement using current player progress and exported master rules."""
from collections import defaultdict

from .game_time import unix
from .timed import TimeBusinessError
from .player_protocol import record, integer


class StoryStore:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection
        self.timing = repository.timing
        data = self.timing.data
        required = ('story_master', 'story_unlock_master', 'chapter_master', 'adventure_flag_master',
                    'story_tree_master', 'story_event_chapters', 'adventure_conditions_master')
        if any(name not in data for name in required):
            raise TimeBusinessError('local_story_configuration_missing', 503)
        self.stories = {row['Code']: row for row in data['story_master']}
        self.unlocks = {row['StoryCode']: row for row in data['story_unlock_master']}
        self.chapters = {row['Code']: row for row in data['chapter_master']}
        self.first_play_adventures = {row['AdventureCode'] for row in
                                      data.get('story_first_play_adventures', [])}
        self.flag_codes = {row['Code'] for row in data['adventure_flag_master']}
        self.allowed_flags = defaultdict(set)
        for edge in data['story_tree_master']:
            # Some branches refer back to the story where a choice is made.
            for code in (edge['StoryCodeFrom'], edge['StoryCodeForUnlock']):
                self.allowed_flags[code].update(edge['AdventureFlagCodesForUnlock'])
        self.events = defaultdict(list)
        for row in data['story_event_chapters']:
            self.events[row['ChapterCode']].append(row)
        self.conditions = defaultdict(list)
        for row in data['adventure_conditions_master']:
            self.conditions[row['AdventureCode']].append(row)

    def seed_flags(self, player_id, values, now):
        """Seed only identity-bound home observations; never overwrite local flags."""
        for value in values or []:
            row = record(self.repo.registry, 'AdventureFlagInfo', value)
            code = integer(row['AdventureFlagCode'], 'AdventureFlagCode')
            flag_value = integer(row['FlagValue'], 'FlagValue')
            if code in self.flag_codes and flag_value >= 0:
                self.connection.execute('''INSERT INTO public.player_adventure_flags
                    (player_id,flag_code,flag_value,updated_at) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                    (player_id, code, flag_value, now))

    def _story(self, story_code):
        story = self.stories.get(story_code)
        if story is None:
            raise TimeBusinessError('local_story_not_found', 404)
        chapter = self.chapters.get(story['ChapterCode'])
        if chapter is None:
            raise TimeBusinessError('local_story_configuration_missing', 503)
        # All chapter categories present in this TW catalog, including the
        # unclassified introductions (0) and Apocrypha (5).
        if chapter['Category'] not in (0, 1, 2, 3, 4, 5):
            raise TimeBusinessError('local_story_category_not_implemented', 501)
        return story, chapter

    def _status(self, player_id, story_code):
        row = self.connection.execute('''SELECT status FROM public.stories
            WHERE player_id=%s AND story_code=%s''', (player_id, story_code)).fetchone()
        return row[0] if row else 0

    def _check_schedule(self, story, chapter, now):
        if chapter['Category'] == 3:
            refs = self.events.get(chapter['Code'])
            if refs:
                # Local catalog events remain playable after their official
                # dates/IsClose flag. Validate the binding, not a live season.
                for ref in refs:
                    if (ref['MasterTable'] not in ('event_master', 'sub_event_master') or
                            ref['EventCode'] not in self.timing.index.get(ref['MasterTable'], {})):
                        raise TimeBusinessError('local_story_event_configuration_missing', 503)
                return
        conditions = self.conditions.get(story['AdventureCode'], [])
        if conditions and not any(self.timing.active(row['ScheduleCode'], now) for row in conditions):
            raise TimeBusinessError('local_story_outside_schedule')
        if chapter['Category'] == 3:
            refs = self.events.get(chapter['Code'])
            if not refs:
                # Contents introductions share the event category, but their
                # FIRST_PLAY_ADV_CODE settings do not reference a timed event.
                if story['AdventureCode'] in self.first_play_adventures:
                    return
                raise TimeBusinessError('local_story_event_configuration_missing', 503)

    def _check_unlock(self, player_id, story_code, now):
        unlock = self.unlocks.get(story_code)
        if unlock is None:
            raise TimeBusinessError('local_story_configuration_missing', 503)
        if unlock['Time'] is not None and now < unix(unlock['Time']):
            raise TimeBusinessError('local_story_locked')
        flags = unlock['AdventureFlagCodeForUnlock']
        if flags and not self.connection.execute('''SELECT 1 FROM public.player_adventure_flags
            WHERE player_id=%s AND flag_code=ANY(%s) AND flag_value=1 LIMIT 1''', (player_id, flags)).fetchone():
            raise TimeBusinessError('local_story_locked')
        character_code = unlock['HomeCharacterCode']
        closeness = unlock['CharacterClosenessLevel']
        costume_code = unlock['HomeCharacterCostumeCode']
        if closeness and not character_code:
            raise TimeBusinessError('local_story_configuration_missing', 503)
        if character_code or costume_code:
            values = self.connection.execute('SELECT home_characters FROM public.players WHERE player_id=%s',
                                             (player_id,)).fetchone()[0]
            characters = [record(self.repo.registry, 'HomeCharacterInfo', value) for value in (values or [])]
            if character_code:
                character = next((row for row in characters if row['HomeCharacterCode'] == character_code), None)
                if character is None or character['ClosenessLevel'] < closeness:
                    raise TimeBusinessError('local_story_locked')
            if costume_code and not any(costume_code in (row['HomeCharacterCostumeCodes'] or [])
                                        for row in characters):
                raise TimeBusinessError('local_story_locked')
        predecessor = unlock['StoryCodeForUnlock']
        if predecessor:
            status = self.connection.execute('''SELECT status FROM public.stories
                WHERE player_id=%s AND story_code=%s''', (player_id, predecessor)).fetchone()
            if status is None or status[0] != 2:
                raise TimeBusinessError('local_story_locked')
        for code in unlock['QuestCodeForUnlock']:
            if not code:
                continue
            quest = self.connection.execute('''SELECT clear_count FROM public.quests
                WHERE player_id=%s AND quest_code=%s''', (player_id, code)).fetchone()
            if quest is None or quest[0] <= 0:
                raise TimeBusinessError('local_story_locked')
        if unlock['PlayerLevel']:
            level = self.connection.execute('SELECT level FROM public.players WHERE player_id=%s',
                                            (player_id,)).fetchone()[0]
            if level < unlock['PlayerLevel']:
                raise TimeBusinessError('local_story_locked')

    def open(self, player_id, story_code, now):
        with self.repo.transaction(player_id):
            story, chapter = self._story(story_code)
            self.timing.refresh(player_id, now)
            now = self.timing._effective_now(player_id, now)
            status = self._status(player_id, story_code)
            if status in (1, 2):
                return {'StoryInfo': [story_code, status], 'changed_codes': set()}
            self._check_schedule(story, chapter, now)
            self._check_unlock(player_id, story_code, now)
            changed = set()
            cost = integer(story['CostItemCount'], 'CostItemCount')
            if cost:
                code = integer(chapter['CostItemCode'], 'CostItemCode')
                if not code:
                    raise TimeBusinessError('local_story_cost_configuration_missing', 503)
                self.repo.apply_item_changes(player_id, f'story-open:{story_code}', {code: -cost})
                self.timing.event(player_id, 57, now, values=(str(code),), amount=cost)
                changed.add(code)
            self.connection.execute('''INSERT INTO public.stories(player_id,story_code,status)
                VALUES (%s,%s,1) ON CONFLICT(player_id,story_code) DO UPDATE SET status=1''', (player_id, story_code))
            self.repo._touch(player_id)
            return {'StoryInfo': [story_code, 1], 'changed_codes': changed}

    def read(self, player_id, story_code, flags, now, tutorial_progress):
        with self.repo.transaction(player_id):
            story, chapter = self._story(story_code)
            existing_flags = {code for code, in self.connection.execute('''SELECT flag_code
                FROM public.player_adventure_flags WHERE player_id=%s AND flag_value=1''', (player_id,)).fetchall()}
            # Accept an existing player's flags repeated in a full client list;
            # only newly acquired flags must belong to this story's branch edges.
            if any(code not in self.flag_codes or
                   (code not in existing_flags and code not in self.allowed_flags[story_code]) for code in flags):
                raise TimeBusinessError('local_story_adventure_flag_invalid', 400)
            self.timing.refresh(player_id, now)
            now = self.timing._effective_now(player_id, now)
            status = self._status(player_id, story_code)
            already_read = status == 2
            rewards = []
            if not already_read:
                # Paid stories are charged by OpenStory, whose response includes
                # InventoryUpdateInfo. Reading never introduces a hidden charge.
                if story['CostItemCount'] and status == 0:
                    raise TimeBusinessError('local_story_requires_open')
                if status == 0:
                    self._check_schedule(story, chapter, now)
                if chapter['Category'] == 2 or status == 0:
                    self._check_unlock(player_id, story_code, now)
                if story['RewardCode']:
                    definitions = self.timing.rewards.get(story['RewardCode'])
                    if not definitions or any(r['Type'] != 2 for r in definitions):
                        raise TimeBusinessError('local_story_reward_configuration_invalid', 503)
                    changed = self.timing._grant(player_id, f'story-read:{story_code}', [story['RewardCode']], now)
                    rewards = [value for value in self.repo.protocol_state(player_id)['StackItems'] if value[0] in changed]
                self.connection.execute('''INSERT INTO public.stories (player_id,story_code,status)
                    VALUES (%s,%s,2) ON CONFLICT(player_id,story_code) DO UPDATE SET status=2''',
                    (player_id, story_code))
                self.timing.event(player_id, 40, now)
                self.timing.event(player_id, 41, now, values=(str(story_code),))
                self.repo._touch(player_id)
            for code in flags:
                # Client StoryModel.IsAdventureFlagOn checks FlagValue == 1.
                # Choices can accumulate on a replay, without repeating rewards.
                self.connection.execute('''INSERT INTO public.player_adventure_flags
                    (player_id,flag_code,flag_value,updated_at) VALUES (%s,%s,1,%s)
                    ON CONFLICT(player_id,flag_code) DO UPDATE SET flag_value=1,updated_at=EXCLUDED.updated_at''',
                    (player_id, code, now))
            if flags:
                self.repo._touch(player_id)
            progress = self.connection.execute('SELECT tutorial_progress FROM public.players WHERE player_id=%s',
                                               (player_id,)).fetchone()[0]
            if tutorial_progress > (progress or 0):
                self.repo.update_player(player_id, tutorial_progress=tutorial_progress)
            return {'StoryRewards': rewards, 'StoryInfo': [story_code, 2],
                    'AdventureFlags': [[code, 1] for code in flags]}
