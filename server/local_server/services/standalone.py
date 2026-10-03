"""Local account creation and wire responses built from definitions and saved state."""
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

from mog_protocol.codec import encode
from PostgreSQL.db import variant
from PostgreSQL.stamina import STAMINA_ITEM
from ..protocol import LocalError, text
from ..resources import installed_resource_hashes
from .player import PlayerService
from .starter_presents import grant_starter_presents

RESOURCE_TOKEN = "local-installed-v1"


def empty_model(protocol, name, **fields):
    """Fill collection/value fields explicitly; optional reference models stay null."""
    values = {}
    for field in protocol.registry.models[name]["fields"]:
        kind = field["type"]
        if kind.startswith(("List<", "IEnumerable<", "IReadOnlyList<")):
            value = []
        elif kind.startswith("Dictionary<"):
            value = {}
        elif kind == "bool":
            value = False
        elif kind == "string":
            value = ""
        elif kind in ("long", "int", "short", "byte", "float", "double"):
            value = 0
        else:
            value = None
        values[field["name"]] = value
    return protocol.model(name, {**values, **fields})


class StandalonePlayerService(PlayerService):
    def __init__(self, repository, protocol, *, clock=None):
        options = {"clock": clock} if clock is not None else {}
        super().__init__(repository, protocol, captures=(), api_hosts=(), **options)

    def _starter_catalog(self):
        if self.timing is None:
            raise LocalError("local_player_definitions_unavailable", 503)
        data = dict(self.repository.connection.execute(
            "SELECT name,data FROM public.character_definitions").fetchall())
        full = self.repository.connection.execute(
            "SELECT data FROM public.lottery_definitions WHERE name='character_master'").fetchone()[0]
        homes = {code: (home_code, scenes) for code, home_code, scenes in self.repository.connection.execute(
            "SELECT costume_code,home_character_code,scenes FROM public.home_costume_scenes").fetchall()}
        settings = self.repository.connection.execute(
            "SELECT data FROM public.shop_definitions WHERE name='game_setting_master'").fetchone()
        try:
            values = {row['Key']: row['Value'] for row in settings[0]}
            initial_codes = [int(code) for code in values['INITIAL_CHARACTER_CODE']]
            required = int(values['TUTORIAL_EQUIPMENT_CHARACTER_ID'][0])
            initial_home = int(values['INITIAL_HOME_CHARACTER_COSTUME_CODE'][0])
            if (not initial_codes or len(initial_codes) > 5 or len(set(initial_codes)) != len(initial_codes)
                    or any(code <= 0 for code in initial_codes) or required not in initial_codes
                    or initial_home not in homes):
                raise ValueError()
        except (TypeError, ValueError, IndexError, KeyError, StopIteration) as exc:
            raise LocalError('local_starter_tutorial_definition_unavailable', 503) from exc
        cultivation = {row["Code"]: row for row in data["character_master"]}
        masters = {row['Code']: row for row in full}
        candidates = []
        # EnhancementTutorial.UpdateTutorialFlag / NeedsLevelupTutorial dereference
        # this fixed character even at player level 1 and after main tutorial skip.
        for code in initial_codes:
            row = masters.get(code)
            if row is None or not row['IsPlayableCharacter'] or code not in cultivation or row['DefaultRarity'] <= 0:
                raise LocalError('local_starter_characters_unavailable', 503)
            candidates.append(row)
        if initial_home not in {row['HomeCharacterCostumeCode'] for row in candidates}:
            raise LocalError('local_starter_home_definition_unavailable', 503)
        return candidates, homes, initial_home

    def _ensure_initial_characters(self, player_id):
        candidates, homes, _ = self._starter_catalog()
        # Repair earlier standalone saves additively; existing heroes, parties,
        # balances and starter presents retain their current values.
        from PostgreSQL.lottery import LotteryStore
        store = LotteryStore(self.repository)
        for master in candidates:
            if store.grant_character(player_id, master):
                costume = master['HomeCharacterCostumeCode']
                if costume in homes:
                    home_code, _ = homes[costume]
                    store.unlock_costume(player_id, master, SimpleNamespace(
                        costumes={costume: {'HomeCharacterCode': home_code}}))
                self.repository.update_character(player_id, master['Code'], closeness=1)

    def _new_login(self, player_id, now):
        candidates, homes, initial_home = self._starter_catalog()
        characters = [self.protocol.model("CharacterInfo", {
            "Code": row["Code"], "Level": 1, "Exp": 0, "Rank": 1,
            "LimitBreak": 0, "Rarity": row["DefaultRarity"], "Closeness": 1}) for row in candidates]
        home_characters = []
        for row in candidates:
            costume = row["HomeCharacterCostumeCode"]
            # Some battle characters (including initial Cid) have no home scenes.
            if costume not in homes:
                continue
            home_code, scenes = homes[costume]
            home_characters.append(self.protocol.model("HomeCharacterInfo", {
                "HomeCharacterCode": home_code, "ClosenessLevel": 1, "ClosenessExp": 0,
                "AvailableQuizzes": [], "HomeCharacterCostumeCodes": [costume], "IsRandomCostume": False}))
        costume = initial_home
        home_code, scenes = homes[costume]
        home_info = self.protocol.model("HomeInfo", {
            "Situations": [[code, events] for code, level, events in scenes if level <= 1],
            "CharacterCostumeCode": costume})
        stamina_cap = self.timing.level_caps[1]
        user = self.protocol.model("UserInfo", {
            "Id": player_id, "Name": "本地玩家", "Level": 1, "Experience": 0,
            "Stamina": [stamina_cap, now], "QuizStamina": [3, now],
            "ProfileCharacterCode": characters[0][0], "TutorialProgressInfo": [99999],
            "FirstLoggedInAt": now, "LastLoggedInAt": now - 86400,
            "IsChatBanned": False, "ProfileIllustrationIndex": 0})
        party = self.protocol.model("PartyInfo", {
            "Type": 1, "UserId": player_id, "No": 1, "Name": "本地队伍", "IsActive": True,
            "CharacterInfos": [[character, 0] for character in characters],
            "MagicItemEquipments": [[character[0], 0, None] for character in characters],
            "TotalPower": 0, "RentalCharacterInfos": []})
        return empty_model(self.protocol, "UserLoginResponse", User=user,
            CurrentResourceUpdateToken=RESOURCE_TOKEN, LatestAssetBundleHashes=installed_resource_hashes(),
            Characters=characters, HomeInfo=home_info, HomeCharacters=home_characters,
            Parties=[party], StackItems=[[STAMINA_ITEM, stamina_cap, now]])

    def login(self, request, login_id):
        text(login_id, maximum=512)
        if self.repository is None:
            raise LocalError("player_storage_unavailable", 503)
        account = sha256(encode(["mog-local-account-v1", login_id])).hexdigest()
        now = int(self.clock())
        # A database lock serializes creation across processes; the save and mapping
        # commit together. Raw login IDs are never stored or sent upstream.
        with self.repository.lock, self.repository.connection.transaction():
            self.repository.connection.execute("SELECT pg_advisory_xact_lock(%s)",
                (int.from_bytes(bytes.fromhex(account[:16]), "big", signed=True),))
            row = self.repository.connection.execute(
                "SELECT player_id FROM public.local_accounts WHERE account_hash=%s", (account,)).fetchone()
            if row is None:
                player_id = "local-" + uuid4().hex
                initial = self._new_login(player_id, now)
                self.repository.seed_login(encode(initial), captured_at=0)
                self.repository.connection.execute(
                    "INSERT INTO public.local_accounts(account_hash,player_id) VALUES (%s,%s)", (account, player_id))
                self.repository.seed_favorites(player_id, [])
                self.timing.initialize(player_id, initial, None, now)
                grant_starter_presents(self.repository, player_id, now)
            else:
                player_id = row[0]
            with self.repository.transaction(player_id):
                self._ensure_initial_characters(player_id)
                self.timing.refresh(player_id, now, login=True)
                self.repository.update_player(player_id, last_logged_in_at=now)
                state = self._state(player_id)
            body = empty_model(self.protocol, "UserLoginResponse",
                CurrentResourceUpdateToken=RESOURCE_TOKEN, LatestAssetBundleHashes=installed_resource_hashes(),
                **{name: value for name, value in state.items()
                   if name in self.protocol.indices("UserLoginResponse")})
        token = self.sessions.issue(player_id, variant(request.headers))
        body[self.protocol.indices("UserLoginResponse")["LoginKey"]] = token
        return body

    def associated(self, request):
        # The standalone server accepts a local identifier without remote linking.
        return True

    def game_top(self, request):
        state = self.state(request)
        session = self.session(request)
        supported = self.protocol.indices("GetGameTopInfoResponse")
        fields = {name: value for name, value in state.items() if name in supported}
        fields["IsPresentBadge"] = bool(self.repository.present_box(session.player_id,
            now=int(self.clock()), include_history=False)["presents"])
        fields.setdefault("SkillTree", [[], []])
        return empty_model(self.protocol, "GetGameTopInfoResponse", GuildBattleInfo=[False],
            ActivatedAt=self.protocol.fields("UserInfo", state["User"])["FirstLoggedInAt"], **fields)

    def profile(self, request, target):
        session = self.session(request)
        if target != session.player_id:
            raise LocalError("local_external_profile_not_implemented", 501)
        state = self._state(target)
        user = self.protocol.fields("UserInfo", state["User"])
        selected = next(self.protocol.fields("CharacterInfo", row) for row in state["Characters"]
                        if row[0] == user["ProfileCharacterCode"])
        personal = empty_model(self.protocol, "UserPersonalInfo", Id=target, Name=user["Name"],
            CharacterCode=user["ProfileCharacterCode"], Level=user["Level"],
            LastLoggedInAt=user["LastLoggedInAt"], HonorCode=state.get("ProfileHonorCode") or None,
            Rank=selected["Rank"], Rarity=selected["Rarity"], IllustrationIndex=user["ProfileIllustrationIndex"])
        profile = empty_model(self.protocol, "UserProfileInfo", UserPersonalInfo=personal)
        record = empty_model(self.protocol, "UserRecordInfo", OwnedCharacterCount=len(state["Characters"]),
            UnlockedStoryCount=len(state["Stories"]), OwnedMagicItemCount=len(state["MagicItems"]),
            OwnedHonorCount=len(state.get("Honors", [])))
        return empty_model(self.protocol, "GetProfileInfoResponse", UserExists=True,
            ProfileInfo=profile, RecordInfo=record, UpdateAccumulateInfos=state.get("UpdateAccumulateInfos", []))
