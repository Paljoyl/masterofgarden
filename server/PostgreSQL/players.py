"""Transactional current player state in public, independent of response replay."""
from hashlib import sha256
import json

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from mog_protocol.codec import CodecError, decode
from .player_protocol import (InvalidPlayerData, integer, collection, login_rows,
                              party_rows, string, boolean, home_state, record)
from .player_progression import PLAYER_EXPERIENCE_ITEM, PlayerProgression


class PlayerNotFound(LookupError):
    pass


class InsufficientItems(ValueError):
    pass


class OperationConflict(ValueError):
    pass


class PlayerRepository:
    # Dependency order matters for owned characters, equipment and party foreign keys.
    TABLES = ("player_stamina", "characters", "items", "character_equipment", "magic_items",
              "magic_item_effects", "parties", "party_characters", "party_magic_items", "party_rentals",
              "quests", "quest_groups", "quest_clear_counts", "stories")
    ORDER = {"player_stamina": "kind", "characters": "character_code", "items": "item_code",
             "character_equipment": "character_code,slot", "magic_items": "magic_item_code",
             "magic_item_effects": "magic_item_code,effect_slot", "parties": "party_type,party_no",
             "party_characters": "party_type,party_no,position", "party_magic_items": "party_type,party_no,position",
             "party_rentals": "party_type,party_no,position", "quests": "quest_code",
             "quest_groups": "quest_group_code", "quest_clear_counts": "quest_code", "stories": "story_code"}

    def __init__(self, database):
        self.database = database
        self.connection = database.connection
        self.lock = database.lock
        self.registry = database.registry
        from .timed import TimedState
        self.timing = TimedState(self)
        self.progression = PlayerProgression(self.timing.data['player_exp_master'])

    def _insert(self, table, rows, conflict=False):
        if not rows:
            return
        columns = list(rows[0])
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}){}").format(
            sql.Identifier("public", table), sql.SQL(",").join(map(sql.Identifier, columns)),
            sql.SQL(",").join(sql.Placeholder() for _ in columns),
            sql.SQL(" ON CONFLICT(player_id) DO NOTHING RETURNING player_id" if conflict else ""))
        if conflict:
            return self.connection.execute(query, [rows[0][key] for key in columns]).fetchone()
        with self.connection.cursor() as cursor:
            cursor.executemany(query, [[row[key] for key in columns] for row in rows])

    def seed_login(self, body, *, response_id=None, captured_at=0):
        """Bootstrap a missing player atomically; existing local state is never reset."""
        rows = login_rows(self.registry, body)
        player_id = rows["players"][0]["player_id"]
        with self.lock, self.connection.transaction():
            if not self._insert("players", rows["players"], conflict=True):
                return False
            for table in self.TABLES:
                self._insert(table, rows[table])
            self.seed_home(player_id, body)
            self.connection.execute("INSERT INTO mog_local.player_state_imports(player_id,source_response_id,captured_at) VALUES (%s,%s,%s)",
                                    (player_id, response_id, captured_at))
        return True

    def seed_favorites(self, player_id, values):
        """Seed from the session-owned game top once; explicit empty lists survive."""
        with self.transaction(player_id):
            current = self.connection.execute('SELECT favorite_character_codes FROM public.players WHERE player_id=%s',
                                              (player_id,)).fetchone()[0]
            if current is not None:
                return False
            codes = {integer(code, 'FavoriteCharacterCode') for code in
                     collection(values, 'FavoriteCharacterCodes')}
            if any(code <= 0 for code in codes):
                raise InvalidPlayerData('Invalid favorite character code')
            # Historical seed codes cannot create ownership in the current save.
            owned = {row[0] for row in self.connection.execute(
                'SELECT character_code FROM public.characters WHERE player_id=%s', (player_id,)).fetchall()}
            self.connection.execute('UPDATE public.players SET favorite_character_codes=%s WHERE player_id=%s',
                                    (sorted(codes & owned), player_id))
            return True

    def seed_box_lotteries(self, player_id, values):
        """Import missing box progress once; saved empty collections are authoritative."""
        from .box_lottery import box_lotteries
        with self.transaction(player_id):
            current = self.connection.execute(
                'SELECT box_lotteries FROM public.players WHERE player_id=%s',
                (player_id,)).fetchone()[0]
            if current is not None:
                return False
            progress = box_lotteries(self.registry, values)
            self.connection.execute('UPDATE public.players SET box_lotteries=%s WHERE player_id=%s',
                                    (Jsonb(progress), player_id))
            self._touch(player_id)
            return True

    def update_favorites(self, player_id, changes):
        if not isinstance(changes, dict):
            raise InvalidPlayerData('Invalid favorite changes')
        for code, favorite in changes.items():
            if integer(code, 'FavoriteCharacterCode') <= 0:
                raise InvalidPlayerData('Invalid favorite character code')
            boolean(favorite, 'IsFavorite')
        with self.transaction(player_id):
            owned = {row[0] for row in self.connection.execute(
                'SELECT character_code FROM public.characters WHERE player_id=%s AND character_code=ANY(%s)',
                (player_id, list(changes))).fetchall()}
            if set(changes) - owned:
                raise InvalidPlayerData('Favorite character is not owned')
            current = self.connection.execute('SELECT favorite_character_codes FROM public.players WHERE player_id=%s',
                                              (player_id,)).fetchone()[0]
            favorites = set(current or [])
            for code, favorite in changes.items():
                if favorite:
                    favorites.add(code)
                else:
                    favorites.discard(code)
            result = sorted(favorites)
            if current != result:
                self.connection.execute('UPDATE public.players SET favorite_character_codes=%s WHERE player_id=%s',
                                        (result, player_id))
                self._touch(player_id)
            return result

    def seed_home(self, player_id, body):
        """Fill a missing home aggregate once, including players created before migration 005."""
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            if self.connection.execute('SELECT home_character_costume_code FROM public.players WHERE player_id=%s', (player_id,)).fetchone()[0] is not None:
                self.repair_home_scenes(player_id)
                return False
            login = record(self.registry, 'UserLoginResponse', decode(body))
            if record(self.registry, 'UserInfo', login['User'])['Id'] != player_id:
                raise InvalidPlayerData('Home seed belongs to a different player')
            home = home_state(self.registry, body)
            if home is None:
                return False
            self.connection.execute('''UPDATE public.players SET
                home_character_costume_code=%s, home_situations=%s,
                home_characters=%s, home_quiz_answers=%s
                WHERE player_id=%s AND home_character_costume_code IS NULL''',
                (home['character_costume_code'], Jsonb(home['situations']),
                 Jsonb(home['home_characters']), Jsonb(home['quiz_answers']), player_id))
            return True

    def _home_scenes(self, costume_code, target, current):
        catalog = self.connection.execute('''SELECT home_character_code, scenes
            FROM public.home_costume_scenes WHERE costume_code=%s''', (costume_code,)).fetchone()
        if catalog is None:
            raise InvalidPlayerData('Home costume has no playable scene configuration')
        character = record(self.registry, 'HomeCharacterInfo', target)
        if character['HomeCharacterCode'] != catalog[0]:
            raise InvalidPlayerData('Home costume character mismatch')
        available = [[code, events] for code, level, events in catalog[1]
                     if level <= character['ClosenessLevel']]
        by_code = {code: set(events) for code, events in available}
        # Keep a valid seed's scene/event order. A different costume needs its own scenes.
        if current and len({scene[0] for scene in current}) == len(current) and all(
                scene[0] in by_code and scene[1] and set(scene[1]) <= by_code[scene[0]]
                for scene in current):
            return current
        return available

    def repair_home_scenes(self, player_id):
        """Repair old costume-only writes without resetting selection or player progress."""
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            costume, characters, current = self.connection.execute('''SELECT
                home_character_costume_code, home_characters, home_situations
                FROM public.players WHERE player_id=%s''', (player_id,)).fetchone()
            if costume is None:
                return False
            target = next((value for value in characters if costume in
                record(self.registry, 'HomeCharacterInfo', value)['HomeCharacterCostumeCodes']), None)
            if target is None:
                raise InvalidPlayerData('Selected home costume is not owned')
            scenes = self._home_scenes(costume, target, current)
            if scenes == current:
                return False
            self.connection.execute('UPDATE public.players SET home_situations=%s WHERE player_id=%s',
                                    (Jsonb(scenes), player_id))
            self._touch(player_id)
            return True

    def set_home_character(self, player_id, costume_code, is_random):
        integer(costume_code, 'CharacterCostumeCode')
        boolean(is_random, 'IsRandomCostume')
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            row = self.connection.execute('SELECT home_characters, home_situations FROM public.players WHERE player_id=%s', (player_id,)).fetchone()
            if row is None:
                raise PlayerNotFound('Home state does not exist')
            characters = row[0]
            target = next((value for value in characters if costume_code in
                           record(self.registry, 'HomeCharacterInfo', value)['HomeCharacterCostumeCodes']), None)
            if target is None:
                raise InvalidPlayerData('Home costume is not owned')
            scenes = self._home_scenes(costume_code, target, row[1])
            random_index = next(field['index'] for field in self.registry.models['HomeCharacterInfo']['fields']
                                if field['name'] == 'IsRandomCostume')
            target[random_index] = is_random
            self.connection.execute('''UPDATE public.players SET
                home_character_costume_code=%s, home_characters=%s, home_situations=%s WHERE player_id=%s''',
                (costume_code, Jsonb(characters), Jsonb(scenes), player_id))
            self._touch(player_id)

    def seed_from_snapshots(self):
        """Use the newest complete login for each identity, with no upstream requests."""
        paths = [key.split(" ", 1)[1] for key, endpoint in self.registry.data["endpoints"].items()
                 if endpoint["response"] == "UserLoginResponse"]
        with self.lock:
            rows = self.connection.execute("SELECT id,method,target,body,captured_at FROM mog_local.responses WHERE status BETWEEN 200 AND 299 AND split_part(target,'?',1)=ANY(%s) ORDER BY captured_at DESC,id DESC", (paths,)).fetchall()
        imported = existing = invalid = 0
        seen = set()
        for response_id, method, target, body, captured_at in rows:
            endpoint = self.registry.endpoint(method, target.split("?", 1)[0])
            if not endpoint or endpoint["response"] != "UserLoginResponse":
                continue
            try:
                data = login_rows(self.registry, bytes(body))
                player_id = data["players"][0]["player_id"]
                if player_id in seen:
                    continue
                seen.add(player_id)
                if self.seed_login(bytes(body), response_id=response_id, captured_at=captured_at):
                    imported += 1
                else:
                    existing += 1
            except (InvalidPlayerData, CodecError, psycopg.IntegrityError, psycopg.DataError):
                invalid += 1
        return {"players_imported": imported, "players_already_present": existing, "invalid_logins": invalid}

    def _lock_player(self, player_id, *, shared=False):
        row = self.connection.execute("SELECT player_id FROM public.players WHERE player_id=%s FOR " + ("SHARE" if shared else "UPDATE"),
                                      (player_id,)).fetchone()
        if row is None:
            raise PlayerNotFound("Player does not exist")

    def _touch(self, player_id):
        self.connection.execute("UPDATE public.players SET revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE player_id=%s", (player_id,))

    def get(self, player_id):
        """Return a consistent business aggregate, with no captured response dependency."""
        with self.lock, self.connection.transaction():
            self._lock_player(player_id, shared=True)
            with self.connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT * FROM public.players WHERE player_id=%s", (player_id,))
                state = {"player": cursor.fetchone()}
                cursor.execute('SELECT node_infos,floor_complete_infos FROM public.player_skill_trees WHERE player_id=%s',
                               (player_id,))
                tree = cursor.fetchone()
                state['skill_tree'] = [tree['node_infos'], tree['floor_complete_infos']] if tree else None
                home = {"character_costume_code": state["player"].get("home_character_costume_code"),
                        "situations": state["player"].get("home_situations"),
                        "home_characters": state["player"].get("home_characters"),
                        "quiz_answers": state["player"].get("home_quiz_answers")}
                state['home'] = home if home["character_costume_code"] is not None else None
                for table in self.TABLES:
                    query = sql.SQL("SELECT * FROM {} WHERE player_id=%s ORDER BY {}").format(
                        sql.Identifier("public", table), sql.SQL(self.ORDER[table]))
                    cursor.execute(query, (player_id,))
                    state[table] = cursor.fetchall()
        return state

    def summary(self):
        with self.lock:
            row = self.connection.execute("SELECT (SELECT count(*) FROM public.players),(SELECT count(*) FROM public.characters),(SELECT count(*) FROM public.items),(SELECT count(*) FROM public.parties),(SELECT count(*) FROM public.quests),(SELECT count(*) FROM public.operations)").fetchone()
        return dict(zip(("players", "characters", "items", "parties", "quests", "operations"), row))

    def apply_item_changes(self, player_id, operation_key, changes):
        """Atomic grant/spend with retry identity, nonnegative balances and item ledger."""
        string(operation_key, "operation_key")
        if not operation_key or not isinstance(changes, dict) or not changes:
            raise InvalidPlayerData("An operation key and item changes are required")
        changes = {integer(code, "item_code"): integer(delta, "delta") for code, delta in changes.items()}
        if any(delta == 0 for delta in changes.values()):
            raise InvalidPlayerData("Item deltas must be nonzero")
        digest = sha256(json.dumps(sorted(changes.items()), separators=(",", ":")).encode()).hexdigest()
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            previous = self.connection.execute("SELECT request_hash,result FROM public.operations WHERE player_id=%s AND operation_key=%s", (player_id, operation_key)).fetchone()
            if previous:
                if previous[0] != digest:
                    raise OperationConflict("Operation key already has different item changes")
                return previous[1]
            balances = {}
            for code, delta in sorted(changes.items()):
                if code == 390000002:
                    # A preceding direct stamina reward in this transaction may
                    # have changed the normal row before its response mirror runs.
                    self.connection.execute('''INSERT INTO public.items(player_id,item_code,quantity,recovered_at)
                        SELECT player_id,390000002,value,updated_at FROM public.player_stamina
                        WHERE player_id=%s AND kind='normal'
                        ON CONFLICT(player_id,item_code) DO UPDATE
                        SET quantity=EXCLUDED.quantity,recovered_at=EXCLUDED.recovered_at''', (player_id,))
                row = self.connection.execute("SELECT quantity FROM public.items WHERE player_id=%s AND item_code=%s", (player_id, code)).fetchone()
                balance = (row[0] if row else 0) + delta
                if balance < 0:
                    raise InsufficientItems("Insufficient inventory")
                integer(balance, "balance")
                self.connection.execute("INSERT INTO public.items(player_id,item_code,quantity,recovered_at) VALUES (%s,%s,%s,0) ON CONFLICT(player_id,item_code) DO UPDATE SET quantity=EXCLUDED.quantity", (player_id, code, balance))
                balances[str(code)] = balance
            if PLAYER_EXPERIENCE_ITEM in changes:
                # Mission XP is a stack-item reward. Persist its absolute balance
                # as player experience and level in this same reward transaction.
                self.update_player(player_id, experience=balances[str(PLAYER_EXPERIENCE_ITEM)])
            if 390000002 in changes:
                # Stack-item stamina rewards/spending must also update the row
                # used by offline regeneration; otherwise refresh overwrites them.
                self.connection.execute('''INSERT INTO public.player_stamina(player_id,kind,value,updated_at)
                    SELECT player_id,'normal',quantity,recovered_at FROM public.items
                    WHERE player_id=%s AND item_code=390000002
                    ON CONFLICT(player_id,kind) DO UPDATE SET value=EXCLUDED.value''', (player_id,))
            result = {"balances": balances}
            self.connection.execute("INSERT INTO public.operations(player_id,operation_key,operation_type,request_hash,result) VALUES (%s,%s,'items',%s,%s)",
                                    (player_id, operation_key, digest, Jsonb(result)))
            with self.connection.cursor() as cursor:
                cursor.executemany("INSERT INTO public.item_ledger(player_id,operation_key,item_code,delta,balance) VALUES (%s,%s,%s,%s,%s)",
                    [(player_id, operation_key, code, delta, balances[str(code)]) for code, delta in changes.items()])
            self._touch(player_id)
            return result

    def update_player(self, player_id, **changes):
        numeric = {"level", "experience", "profile_character_code", "tutorial_progress",
                   "first_logged_in_at", "last_logged_in_at", "profile_illustration_index", "profile_honor_code"}
        if not changes or set(changes) - numeric - {"name", "is_chat_banned"}:
            raise InvalidPlayerData("Unknown or empty player changes")
        values = {}
        for name, value in changes.items():
            if name == "name":
                value = string(value, name)
            elif name == "is_chat_banned":
                value = boolean(value, name)
            elif name != "tutorial_progress" or value is not None:
                value = integer(value, name)
            values[name] = value
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            if 'experience' in values:
                # Experience and its derived level always change in one write.
                values['level'] = self.progression.level(values['experience'])
            query = sql.SQL("UPDATE public.players SET {} WHERE player_id=%s").format(
                sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(name)) for name in values))
            self.connection.execute(query, (*values.values(), player_id))
            if 'experience' in values:
                self.connection.execute('''INSERT INTO public.items
                    (player_id,item_code,quantity,recovered_at) VALUES (%s,%s,%s,0)
                    ON CONFLICT(player_id,item_code) DO UPDATE SET quantity=EXCLUDED.quantity''',
                    (player_id, PLAYER_EXPERIENCE_ITEM, values['experience']))
            self._touch(player_id)

    def synchronize_player_level(self, player_id):
        """Persist the level implied by saved experience before state reads or mission checks."""
        with self.transaction(player_id):
            level, experience = self.connection.execute(
                'SELECT level,experience FROM public.players WHERE player_id=%s', (player_id,)).fetchone()
            derived = self.progression.level(experience)
            if derived != level:
                self.connection.execute('UPDATE public.players SET level=%s WHERE player_id=%s',
                                        (derived, player_id))
                self._touch(player_id)
            return derived

    def apply_player_experience(self, player_id, operation_key, amount):
        """Settle trusted earned experience once, preserving it and level in the player transaction."""
        string(operation_key, 'operation_key')
        amount = integer(amount, 'player experience gain')
        if not operation_key or amount < 0:
            raise InvalidPlayerData('Invalid player experience operation')
        digest = sha256(json.dumps({'type': 'player_experience', 'amount': amount},
                                  sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.transaction(player_id):
            previous = self.connection.execute('''SELECT operation_type,request_hash,result
                FROM public.operations WHERE player_id=%s AND operation_key=%s''',
                (player_id, operation_key)).fetchone()
            if previous:
                if previous[0] != 'player_experience' or previous[1] != digest:
                    raise OperationConflict('Operation key already has different experience changes')
                return previous[2]
            before_level, before_experience = self.connection.execute(
                'SELECT level,experience FROM public.players WHERE player_id=%s', (player_id,)).fetchone()
            experience = integer(before_experience + amount, 'player experience')
            level = self.progression.level(experience)
            self.update_player(player_id, experience=experience)
            result = {'level': level, 'experience': experience, 'previous_level': before_level,
                      'previous_experience': before_experience, 'gained_experience': amount}
            self.connection.execute('''INSERT INTO public.operations
                (player_id,operation_key,operation_type,request_hash,result)
                VALUES (%s,%s,'player_experience',%s,%s)''',
                (player_id, operation_key, digest, Jsonb(result)))
            return result

    def add_present(self, player_id, present_id, *, title, inventory_type, inventory_code,
                    amount, sender_icon_code=0, arrived_at, limit_date=None):
        """Trusted local reward generation. A stable ID cannot change or reset a grant."""
        if type(present_id) is not bytes or len(present_id) != 16:
            raise InvalidPlayerData('Present ID must be a 16-byte ULID')
        data = dict(title=string(title, 'title'), inventory_type=integer(inventory_type, 'inventory_type'),
                    inventory_code=integer(inventory_code, 'inventory_code'), amount=integer(amount, 'amount'),
                    sender_icon_code=integer(sender_icon_code, 'sender_icon_code'),
                    arrived_at=integer(arrived_at, 'arrived_at'),
                    limit_date=integer(limit_date, 'limit_date') if limit_date is not None else None)
        if (not 0 < inventory_type <= 2**31 - 1 or not 0 < amount <= 2**31 - 1
                or min(inventory_code, sender_icon_code, arrived_at) < 0
                or (limit_date is not None and limit_date <= arrived_at)):
            raise InvalidPlayerData('Invalid present reward or lifetime')
        with self.transaction(player_id):
            previous = self.present_rows(player_id, [present_id])
            if previous:
                if any(previous[0][name] != value for name, value in data.items()):
                    raise OperationConflict('Present ID already has a different reward')
                return False
            self.connection.execute('''INSERT INTO public.presents
                (player_id,present_id,title,inventory_type,inventory_code,amount,sender_icon_code,arrived_at,limit_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)''', (player_id, present_id, *data.values()))
            self._touch(player_id)
            return True

    def present_rows(self, player_id, present_ids):
        """Look up only the authenticated player's IDs, including expired/received rows."""
        with self.lock, self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute('SELECT * FROM public.presents WHERE player_id=%s AND present_id=ANY(%s)',
                           (player_id, present_ids))
            return cursor.fetchall()

    def present_box(self, player_id, *, now, include_history):
        with self.transaction(player_id):
            with self.connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute('''SELECT * FROM public.presents WHERE player_id=%s AND arrived_at<=%s
                    AND received_at IS NULL AND (limit_date IS NULL OR limit_date>%s)
                    ORDER BY arrived_at,present_id''', (player_id, now, now))
                pending = cursor.fetchall()
                history = []
                if include_history:
                    cursor.execute('''SELECT * FROM public.presents WHERE player_id=%s AND received_at<=%s
                        ORDER BY received_at DESC,present_id''', (player_id, now))
                    history = cursor.fetchall()
            return {'presents': pending, 'histories': history}

    def mark_present_received(self, player_id, present_id, now):
        """Compose with the inventory grant under transaction(player_id)."""
        with self.transaction(player_id):
            row = self.connection.execute('''UPDATE public.presents SET received_at=%s
                WHERE player_id=%s AND present_id=%s AND received_at IS NULL
                  AND arrived_at<=%s AND (limit_date IS NULL OR limit_date>%s)
                RETURNING present_id''', (now, player_id, present_id, now, now)).fetchone()
            if not row:
                raise OperationConflict('Present is no longer receivable')
            self._touch(player_id)

    def update_character(self, player_id, character_code, **changes):
        """Persist validated state; recipe costs and progression rules belong to handlers."""
        allowed = {"level", "experience", "rank", "limit_break", "rarity", "closeness"}
        if not changes or set(changes) - allowed:
            raise InvalidPlayerData("Unknown or empty character changes")
        integer(character_code, "character_code")
        changes = {name: integer(value, name) for name, value in changes.items()}
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            query = sql.SQL("UPDATE public.characters SET {} WHERE player_id=%s AND character_code=%s RETURNING character_code").format(
                sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(name)) for name in changes))
            if not self.connection.execute(query, (*changes.values(), player_id, character_code)).fetchone():
                raise PlayerNotFound("Owned character does not exist")
            self._touch(player_id)

    def set_character_equipment(self, player_id, character_code, slots):
        """Replace occupied slots atomically; item costs are composed by the service."""
        integer(character_code, 'character_code')
        if (not isinstance(slots, list) or any(type(s) is not int or not 1 <= s <= 6 for s in slots)
                or len(set(slots)) != len(slots)):
            raise InvalidPlayerData('Invalid occupied equipment slots')
        with self.transaction(player_id):
            if not self.connection.execute('SELECT 1 FROM public.characters WHERE player_id=%s AND character_code=%s',
                                           (player_id, character_code)).fetchone():
                raise PlayerNotFound('Owned character does not exist')
            self.connection.execute('DELETE FROM public.character_equipment WHERE player_id=%s AND character_code=%s',
                                    (player_id, character_code))
            self._insert('character_equipment', [dict(player_id=player_id, character_code=character_code, slot=s) for s in slots])
            self._touch(player_id)

    def save_party(self, player_id, value):
        rows = party_rows(self.registry, player_id, value)
        party = rows["parties"][0]
        key = (player_id, party["party_type"], party["party_no"])
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            self.connection.execute("INSERT INTO public.parties(player_id,party_type,party_no,name,is_active,total_power) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(player_id,party_type,party_no) DO UPDATE SET name=EXCLUDED.name,is_active=EXCLUDED.is_active,total_power=EXCLUDED.total_power", (*key, party["name"], party["is_active"], party["total_power"]))
            for table in ("party_characters", "party_magic_items", "party_rentals"):
                self.connection.execute(sql.SQL("DELETE FROM {} WHERE player_id=%s AND party_type=%s AND party_no=%s").format(sql.Identifier("public", table)), key)
                self._insert(table, rows[table])
            self._touch(player_id)

    def transaction(self, player_id):
        """Compose costs, character changes and party changes under one player lock."""
        from contextlib import contextmanager

        @contextmanager
        def atomic():
            with self.lock, self.connection.transaction():
                self._lock_player(player_id)
                yield self
        return atomic()

    def delete_player(self, player_id):
        """Delete one aggregate in foreign-key order, including its dependent ledger."""
        with self.lock, self.connection.transaction():
            self._lock_player(player_id)
            self.connection.execute("DELETE FROM public.parties WHERE player_id=%s", (player_id,))
            self.connection.execute("DELETE FROM public.operations WHERE player_id=%s", (player_id,))
            self.connection.execute("DELETE FROM public.players WHERE player_id=%s", (player_id,))

    def protocol_state(self, player_id):
        """Build supported login collections from live tables, including direct SQL edits."""
        from .player_export import protocol_state
        return protocol_state(self.registry, self.get(player_id))
