"""Owned character conversations settled under the existing player transaction."""
from collections import defaultdict
from hashlib import sha256
import json
import secrets

from psycopg.types.json import Jsonb

from .player_export import model
from .player_protocol import record
from .timed import TimeBusinessError


QUIZ_STAMINA_ITEM = 390000003  # GeneralItemMaster.ItemBehaviourType.QuizStamina = 20.
# Successful client login captures expose three ordinary conversation choices.
QUIZ_OPTION_COUNT = 3


class QuizStore:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection
        self.timing = repository.timing
        data = self.timing.data
        required = ('quiz_master', 'quiz_answer_option_master', 'closeness_exp_master',
                    'closeness_item_reward_master', 'quiz_settings')
        if any(name not in data for name in required):
            raise TimeBusinessError('local_quiz_configuration_missing', 503)
        self.quizzes = {row['Code']: row for row in data['quiz_master']}
        self.options = defaultdict(set)
        for row in data['quiz_answer_option_master']:
            self.options[row['QuizCode']].add(row['AnswerNumber'])
        self.by_character = defaultdict(list)
        for row in data['quiz_master']:
            if row['QuizType'] == 0:
                self.by_character[row['HomeCharacterCode']].append(row['Code'])
        self.curve = sorted(data['closeness_exp_master'], key=lambda row: row['Level'])
        settings = {r['Key']: int(r['Value'][0]) for r in data['quiz_settings']}
        self.exp_gain = settings['QUIZ_REWARD_CLOSENESS_EXP']
        self.rewards = defaultdict(list)
        for row in data['closeness_item_reward_master']:
            if row['RewardCode']:
                self.rewards[row['HomeCharacterCode']].append(row)

    def refresh_available(self, player_id, now):
        """Fill missing owned-character choices without resetting existing ones."""
        row = self.connection.execute(
            'SELECT home_characters FROM public.players WHERE player_id=%s', (player_id,)).fetchone()
        if row is None or row[0] is None:
            return
        characters = row[0]
        missing = []
        for index, value in enumerate(characters):
            character = record(self.repo.registry, 'HomeCharacterInfo', value)
            if not character['AvailableQuizzes']:
                missing.append((index, character))
        if not missing:
            return
        settled = {int(row[0].rsplit(':', 1)[1]) for row in self.connection.execute('''SELECT operation_key
            FROM public.operations WHERE player_id=%s AND operation_type='quiz' AND operation_key LIKE %s''',
            (player_id, f'quiz:{self.timing.clock.day(now)}:%')).fetchall()}
        changed = False
        for index, character in missing:
            candidates = [code for code in self.by_character[character['HomeCharacterCode']]
                          if code not in settled and self.options[code]]
            available = []
            for _ in range(min(QUIZ_OPTION_COUNT, len(candidates))):
                code = secrets.choice(candidates)
                candidates.remove(code)
                available.append(code)
            if available:
                character['AvailableQuizzes'] = available
                characters[index] = model(self.repo.registry, 'HomeCharacterInfo', character)
                changed = True
        if changed:
            self.connection.execute('UPDATE public.players SET home_characters=%s WHERE player_id=%s',
                                    (Jsonb(characters), player_id))
            self.repo._touch(player_id)

    def answer(self, player_id, quiz_code, answer_option, now, tutorial_progress):
        with self.repo.transaction(player_id):
            self.timing.refresh(player_id, now)
            now = self.timing._effective_now(player_id, now)
            quiz = self.quizzes.get(quiz_code)
            if quiz is None or quiz['QuizType'] != 0:
                raise TimeBusinessError('local_quiz_not_found', 404)
            if answer_option not in self.options[quiz_code]:
                raise TimeBusinessError('local_quiz_answer_invalid', 400)
            character_code = quiz['HomeCharacterCode']
            costume, characters, answers, situations, progress = self.connection.execute('''SELECT
                home_character_costume_code,home_characters,home_quiz_answers,home_situations,tutorial_progress
                FROM public.players WHERE player_id=%s''', (player_id,)).fetchone()
            if costume is None or characters is None or answers is None:
                raise TimeBusinessError('local_home_seed_not_found', 503)
            target_index = next((i for i, row in enumerate(characters)
                if record(self.repo.registry, 'HomeCharacterInfo', row)['HomeCharacterCode'] == character_code), None)
            if target_index is None:
                raise TimeBusinessError('local_quiz_character_not_owned', 403)

            # A consumed question leaves the available list. Its retry must not
            # consume another point or award another closeness level reward.
            key = f'quiz:{self.timing.clock.day(now)}:{quiz_code}'
            digest = sha256(json.dumps([quiz_code, answer_option], separators=(',', ':')).encode()).hexdigest()
            previous = self.connection.execute('''SELECT operation_type,request_hash,result
                FROM public.operations WHERE player_id=%s AND operation_key=%s''', (player_id, key)).fetchone()
            if previous:
                if previous[0] != 'quiz' or previous[1] != digest:
                    raise TimeBusinessError('local_quiz_already_answered')
                return previous[2]

            target = record(self.repo.registry, 'HomeCharacterInfo', characters[target_index])
            if quiz_code not in target['AvailableQuizzes']:
                raise TimeBusinessError('local_quiz_not_available')
            points = self.connection.execute('''SELECT quantity FROM public.items
                WHERE player_id=%s AND item_code=%s''', (player_id, QUIZ_STAMINA_ITEM)).fetchone()
            if points is None or points[0] <= 0:
                raise TimeBusinessError('local_quiz_insufficient_stamina')
            self.repo.apply_item_changes(player_id, key + ':stamina', {QUIZ_STAMINA_ITEM: -1})
            self.connection.execute('''UPDATE public.items SET recovered_at=%s
                WHERE player_id=%s AND item_code=%s''', (now, player_id, QUIZ_STAMINA_ITEM))
            self.connection.execute('''UPDATE public.player_stamina SET value=%s,updated_at=%s
                WHERE player_id=%s AND kind='quiz' ''', (points[0] - 1, now, player_id))

            before_level = target['ClosenessLevel']
            experience = min(target['ClosenessExp'] + self.exp_gain, self.curve[-1]['TotalExp'])
            level = max(row['Level'] for row in self.curve if row['TotalExp'] <= experience)
            target['ClosenessExp'], target['ClosenessLevel'] = experience, level
            available = list(target['AvailableQuizzes'])
            candidates = [code for code in self.by_character[character_code] if code not in available]
            settled = {int(row[0].rsplit(':', 1)[1]) for row in self.connection.execute('''SELECT operation_key
                FROM public.operations WHERE player_id=%s AND operation_type='quiz' AND operation_key LIKE %s''',
                (player_id, f'quiz:{self.timing.clock.day(now)}:%')).fetchall()}
            candidates = [code for code in candidates if code not in settled]
            position = available.index(quiz_code)
            if candidates:
                available[position] = secrets.choice(candidates)
            else:
                available.pop(position)
            target['AvailableQuizzes'] = available
            characters[target_index] = model(self.repo.registry, 'HomeCharacterInfo', target)

            answer_index = next((i for i, row in enumerate(answers)
                if record(self.repo.registry, 'QuizAnswerInfo', row)['QuizCode'] == quiz_code), None)
            answered = [] if answer_index is None else list(
                record(self.repo.registry, 'QuizAnswerInfo', answers[answer_index])['AnsweredOptions'])
            if answer_option not in answered:
                answered.append(answer_option)
            answer = model(self.repo.registry, 'QuizAnswerInfo',
                           {'QuizCode': quiz_code, 'AnsweredOptions': answered})
            if answer_index is None:
                answers.append(answer)
            else:
                answers[answer_index] = answer

            # Include scenes unlocked by the new level for the selected costume.
            if costume in target['HomeCharacterCostumeCodes']:
                unlocked = self.repo._home_scenes(costume, characters[target_index], None)
                owned_scenes = {row[0] for row in situations}
                situations += [row for row in unlocked if row[0] not in owned_scenes]
            self.connection.execute('''UPDATE public.players SET home_characters=%s,home_quiz_answers=%s,
                home_situations=%s,tutorial_progress=%s WHERE player_id=%s''',
                (Jsonb(characters), Jsonb(answers), Jsonb(situations),
                 max(progress or 0, tutorial_progress), player_id))
            changed = {QUIZ_STAMINA_ITEM}
            for reward in self.rewards[character_code]:
                if before_level < reward['Level'] <= level:
                    changed |= self.timing._grant(player_id,
                        f'quiz-closeness:{character_code}:{reward["Level"]}', [reward['RewardCode']], now)
            self.timing.event(player_id, 46, now)
            self.timing.event(player_id, 47, now, values=(str(character_code),))
            self.timing.event(player_id, 52, now)
            self.timing.event(player_id, 53, now, values=(str(character_code),))
            if costume in target['HomeCharacterCostumeCodes']:
                self.timing.event(player_id, 48, now, values=(str(costume),))
                self.timing.event(player_id, 54, now, values=(str(costume),))
            result = {'home_character_code': character_code, 'changed_codes': sorted(changed)}
            self.connection.execute('''INSERT INTO public.operations
                (player_id,operation_key,operation_type,request_hash,result) VALUES (%s,%s,'quiz',%s,%s)''',
                (player_id, key, digest, Jsonb(result)))
            self.repo._touch(player_id)
            return result
