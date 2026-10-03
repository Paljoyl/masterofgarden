"""Player ownership and party rules on top of the database agent's repository."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import logging
import time
from urllib.parse import urlsplit

from PostgreSQL.db import variant
from mog_protocol.capture import CaptureError, field, headers, message_body, read_flows
from mog_protocol.codec import CodecError, decode, encode
from ..protocol import LocalError, integer, sequence, text
from .sessions import Sessions
from .trial_battle import TrialBattleService, TRIAL_PARTY_TYPE, TRIAL_PARTY_COUNT
from .climbing_catalog import CLIMBING_PARTY_COUNT
from .tower import TOWER_PARTY_TYPE, TOWER_PARTY_COUNT

log = logging.getLogger("mog.player")


def identity(path, login_id, client_variant):
    return sha256(encode([path, login_id, client_variant])).hexdigest()


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value or "")


@dataclass
class LoginSeed:
    player_id: str
    variant: str
    body: list
    upstream_key: str | None
    captured_at: float


class PlayerService:
    def __init__(self, repository, protocol, captures=(), api_hosts=(), sessions=None, clock=time.time):
        self.repository, self.protocol = repository, protocol
        from PostgreSQL.sessions import SessionStore
        store = SessionStore(repository) if repository is not None and hasattr(repository, 'connection') else None
        self.sessions = sessions or Sessions(clock=clock, store=store, upstream_key_provider=self._upstream_key)
        self.clock = clock
        self.trial_battle = TrialBattleService(self, protocol)
        self.timing = getattr(repository, 'timing', None)
        self.accounts = {}
        self.templates = {}
        self.template_times = {}
        self.present_seeds = {}
        self.associations = set()
        self.load_captures(captures, api_hosts)

    def _upstream_key(self, player_id, client_variant):
        # Relay metadata remains in memory and comes only from identity-bound
        # official login seeds; it is not a credential persisted with sessions.
        return next((seed.upstream_key for seed in self.accounts.values()
                     if seed.player_id == player_id and seed.variant == client_variant and seed.upstream_key), None)

    def load_captures(self, paths, api_hosts):
        """Keep identity-bound auxiliary fields; never write captures into player tables."""
        flows = []
        for path in paths:
            if not path.exists():
                continue
            try:
                for flow in read_flows(path):
                    req, res = field(flow, "request"), field(flow, "response")
                    if not isinstance(req, dict) or not isinstance(res, dict) or field(res, "status_code") != 200:
                        continue
                    req_headers = headers(req)
                    server = field(flow, "server_conn", {}) or {}
                    host = _text(req_headers.get("x-mog-original-host") or field(server, "sni")
                                 or req_headers.get("host") or field(req, "host")).split(":", 1)[0]
                    if host not in api_hosts or not headers(res).get("content-type", "").startswith("application/x-msgpack"):
                        continue
                    flows.append((float(field(res, "timestamp_end") or field(res, "timestamp_start") or 0), req, res))
            except (CaptureError, OSError):
                log.warning("Incomplete player seed capture: %s", path.name)
        key_owners = {}
        upstream_keys = {}
        ambiguous = set()
        # First identify sessions. Requests from other endpoints never establish identity.
        for timestamp, req, res in sorted(flows, key=lambda item: item[0]):
            path = urlsplit(_text(field(req, "path"))).path
            endpoint = self.protocol.registry.endpoint(_text(field(req, "method")), path)
            if not endpoint or endpoint["response"] != "UserLoginResponse":
                continue
            try:
                request = self.protocol.fields("UserLoginRequest", decode(message_body(req)), strict=True)
                body = decode(message_body(res))
                login = self.protocol.fields("UserLoginResponse", body)
                user = self.protocol.fields("UserInfo", login["User"])
                player_id = text(user["Id"], maximum=512)
                login_id = text(request["loginid"], maximum=512)
                upstream_key = text(login["LoginKey"], maximum=1024)
                client_variant = variant(headers(req))
                if not upstream_key.startswith('mog-local-'):
                    upstream_keys[(player_id, client_variant)] = upstream_key
                account = identity(path, login_id, client_variant)
                previous = self.accounts.get(account)
                if previous and previous.player_id != player_id:
                    ambiguous.add(account)
                    continue
                seed = LoginSeed(player_id, client_variant, deepcopy(body), upstream_key, timestamp)
                # Tokens remain in volatile session metadata, not response templates.
                seed.body[self.protocol.indices("UserLoginResponse")["LoginKey"]] = None
                self.accounts[account] = seed
                owner_key = (upstream_key, client_variant)
                if owner_key in key_owners and key_owners[owner_key] != player_id:
                    key_owners[owner_key] = None
                else:
                    key_owners[owner_key] = player_id
                guid = headers(req).get("x-caravanwa-ssg-guid")
                if guid:
                    self.associations.add(sha256(encode([guid, client_variant])).hexdigest())
            except (CodecError, LocalError, TypeError, ValueError):
                log.warning("Skipped invalid login seed")
        for account in ambiguous:
            self.accounts.pop(account, None)
        # A newer local login capture must not replace the official relay key.
        for seed in self.accounts.values():
            seed.upstream_key = upstream_keys.get((seed.player_id, seed.variant))
        for timestamp, req, res in sorted(flows, key=lambda item: item[0]):
            path = urlsplit(_text(field(req, "path"))).path
            if path not in ("/gametop/getgametopinfo", "/profile/getprofileinfo",
                            "/presentbox/getpresentboxinfo", "/presentbox/receivepresents",
                            "/lottery/getlotteries", "/lottery/getlotteryhistories",
                            "/boxlottery/getboxlotteries",
                            "/climbing/climbingtop", "/tower/towertop"):
                continue
            req_headers = headers(req)
            client_variant = variant(req_headers)
            owner = key_owners.get((req_headers.get("x-polka-loginkey"), client_variant))
            if not owner:
                continue
            try:
                body = decode(message_body(res))
                if path.startswith('/presentbox/'):
                    # Ignore local empty boxes and replayed responses. A successful
                    # official claim's remaining list supersedes an earlier box.
                    if headers(res).get('x-mog-route', '') not in ('', 'forward'):
                        continue
                    model = ('GetPresentBoxInfoResponse' if path.endswith('getpresentboxinfo')
                             else 'ReceivePresentsResponse')
                    box = self.protocol.fields(model, body)
                    presents = [self.protocol.fields('PresentInfo', value) for value in box['Presents']]
                    if any(row['ReceivedAt'] is not None for row in presents):
                        raise LocalError('invalid_captured_present_box')
                    self.present_seeds[owner] = (timestamp, presents)
                    continue
                if path.startswith(('/lottery/', '/boxlottery/', '/climbing/', '/tower/')) and headers(res).get('x-mog-route', '') not in ('', 'forward'):
                    continue
                model = {'/gametop/getgametopinfo': 'GetGameTopInfoResponse',
                         '/profile/getprofileinfo': 'GetProfileInfoResponse',
                         '/lottery/getlotteries': 'GetLotteriesResponse',
                         '/lottery/getlotteryhistories': 'GetLotteryHistoriesResponse',
                         '/boxlottery/getboxlotteries': 'GetBoxLotteriesResponse',
                         '/climbing/climbingtop': 'ClimbingTopResponse',
                         '/tower/towertop': 'TowerTopResponse'}[path]
                self.protocol.fields(model, body)
                if path.startswith("/profile/"):
                    target = self.protocol.fields("GetProfileInfoRequest", decode(message_body(req)), strict=True)
                    if target["TargetUserId"] != owner:
                        continue
                self.templates[(owner, client_variant, path)] = deepcopy(body)
                self.template_times[(owner, client_variant, path)] = timestamp
            except (CodecError, LocalError):
                log.warning("Skipped invalid player auxiliary seed")

    def seed_present_boxes(self):
        """Fill missing presents once; never replace current inventory or receipts."""
        if self.repository is None:
            return 0
        from PostgreSQL.present_seed import seed_present_box
        from PostgreSQL.player_protocol import InvalidPlayerData
        from PostgreSQL.players import OperationConflict
        known_players = {account.player_id for account in self.accounts.values()}
        imported = 0
        for player_id, (timestamp, presents) in self.present_seeds.items():
            if player_id not in known_players:
                continue
            try:
                imported += seed_present_box(self.repository, player_id, presents, int(timestamp))
            except (LookupError, InvalidPlayerData, OperationConflict):
                log.warning('Skipped invalid captured present seed')
        return imported

    def session(self, request):
        return self.sessions.resolve(request.headers, variant(request.headers))

    def state(self, request):
        return self._state(self.session(request).player_id)

    def initialize_box_lotteries(self, player_id, client_variant):
        """Use only the newest same-player/version seed; never replace saved progress."""
        if self.repository is None or not hasattr(self.repository, 'seed_box_lotteries'):
            return
        candidates = []
        for path, model in (('/gametop/getgametopinfo', 'GetGameTopInfoResponse'),
                            ('/boxlottery/getboxlotteries', 'GetBoxLotteriesResponse')):
            key = (player_id, client_variant, path)
            template = self.templates.get(key)
            if template is not None:
                values = self.protocol.fields(model, template)['BoxLotteries']
                if values is not None:
                    candidates.append((self.template_times.get(key, 0), values))
        if candidates:
            values = max(candidates, key=lambda item: item[0])[1]
            self.repository.seed_box_lotteries(player_id, values)

    def _state(self, player_id):
        if self.repository is None:
            raise LocalError("player_storage_unavailable", 503)
        try:
            if self.timing is not None:
                with self.repository.transaction(player_id):
                    now = int(self.clock())
                    self.timing.refresh(player_id, now)
                    return {**self.repository.protocol_state(player_id), **self.timing.view(player_id, now)}
            return self.repository.protocol_state(player_id)
        except LookupError as exc:
            raise LocalError("local_player_not_initialized", 503) from exc

    def login(self, request, login_id):
        client_variant = variant(request.headers)
        seed = self.accounts.get(identity(request.path, login_id, client_variant))
        if seed is None:
            raise LocalError("local_login_seed_not_found", 503)
        if self.repository is None:
            raise LocalError("player_storage_unavailable", 503)
        with self.repository.transaction(seed.player_id):
            self.repository.seed_home(seed.player_id, encode(seed.body))
            self.initialize_box_lotteries(seed.player_id, client_variant)
            home = self.templates.get((seed.player_id, client_variant, '/gametop/getgametopinfo'))
            if home is not None:
                self.repository.seed_favorites(seed.player_id,
                    self.protocol.fields('GetGameTopInfoResponse', home)['FavoriteCharacterCodes'] or [])
                if hasattr(self.repository, 'connection'):
                    from PostgreSQL.skill_tree import SkillTreeStore
                    SkillTreeStore(self.repository).seed(seed.player_id,
                        self.protocol.fields('GetGameTopInfoResponse', home)['SkillTree'])
            now = int(self.clock())
            if self.timing is not None:
                self.timing.initialize(seed.player_id, seed.body, home, now)
                self.timing.refresh(seed.player_id, now, login=True)
            self.repository.update_player(seed.player_id, last_logged_in_at=now)
            state = self._state(seed.player_id)
        supported = self.protocol.indices('UserLoginResponse')
        fields = {**{name: value for name, value in state.items() if name in supported},
                  "LoginKey": self.sessions.issue(seed.player_id, client_variant, seed.upstream_key),
                  "RequireAgreementToTermsOfService": False}
        fields.setdefault('UpdateAccumulateInfos', [])
        return self.protocol.model("UserLoginResponse", fields, seed.body)

    def associated(self, request):
        lower = {k.lower(): v for k, v in request.headers.items()}
        guid = lower.get("x-caravanwa-ssg-guid", "")
        return sha256(encode([guid, variant(request.headers)])).hexdigest() in self.associations

    def game_top(self, request):
        session = self.session(request)
        template = self.templates.get((session.player_id, session.variant, request.path))
        if template is None:
            raise LocalError("local_game_top_seed_not_found", 503)
        if self.repository is None:
            raise LocalError('player_storage_unavailable', 503)
        with self.repository.transaction(session.player_id):
            self.initialize_box_lotteries(session.player_id, session.variant)
            self.repository.seed_favorites(session.player_id,
                self.protocol.fields('GetGameTopInfoResponse', template)['FavoriteCharacterCodes'] or [])
            if self.timing is not None and self.timing.garden() is not None:
                self.timing.garden().initialize(session.player_id, int(self.clock()),
                    self.protocol.fields('GetGameTopInfoResponse', template))
        state = self._state(session.player_id)
        supported = self.protocol.indices("GetGameTopInfoResponse")
        fields = {name: value for name, value in state.items() if name in supported}
        fields.setdefault("UpdateAccumulateInfos", [])
        fields['IsPresentBadge'] = bool(self.repository.present_box(session.player_id,
            now=int(self.clock()), include_history=False)['presents'])
        if self.timing is not None:
            now = self.timing._effective_now(session.player_id, int(self.clock()))
            captured = self.protocol.fields('GetGameTopInfoResponse', template)
            honors = {self.protocol.fields('HonorInfo', value)['HonorCode']
                      for value in (captured['Honors'] or []) + state.get('Honors', [])}
            fields['Honors'] = [self.protocol.model('HonorInfo', {'HonorCode': code}) for code in sorted(honors)]
            for name in ('LotteryCodes', 'IconBadgeLotteryCodes'):
                fields[name] = [code for code in captured[name] or []
                                if self.timing.lottery_expiry(session.player_id, code, now)[0]]
        return self.protocol.model("GetGameTopInfoResponse", fields, template)

    def parties(self, request, types):
        session = self.session(request)
        requested = set(types)
        party_counts = {TOWER_PARTY_TYPE: TOWER_PARTY_COUNT,
                        **{kind: CLIMBING_PARTY_COUNT for kind in range(16, 20)}}
        if requested.intersection(party_counts) and self.repository is not None:
            with self.repository.transaction(session.player_id):
                state = self._state(session.player_id)
                existing = {(p[0], p[2]) for p in state['Parties']}
                for kind in sorted(requested.intersection(party_counts)):
                    for number in range(1, party_counts[kind] + 1):
                        if (kind, number) in existing:
                            continue
                        party = self.protocol.model('PartyInfo', {
                            'Type': kind, 'UserId': session.player_id, 'No': number, 'Name': '',
                            'IsActive': False, 'CharacterInfos': [], 'MagicItemEquipments': [],
                            'TotalPower': 0, 'RentalCharacterInfos': []})
                        self.repository.save_party(session.player_id, party)
                        state['Parties'].append(party)
        else:
            state = self._state(session.player_id)
        return [p for p in state["Parties"] if self.protocol.fields("PartyInfo", p)["Type"] in requested]

    def _canonical_party(self, player_id, value, state):
        fields = self.protocol.fields("PartyInfo", value, strict=True)
        if fields["UserId"] != player_id:
            raise LocalError("party_owner_mismatch", 403)
        kind = integer(fields["Type"], maximum=2**31 - 1)
        number = integer(fields["No"], maximum=2**31 - 1)
        existing = next((p for p in state["Parties"] if (p[0], p[2]) == (kind, number)), None)
        if existing is None:
            # Training and World Tree parties are created by the client on first use.
            # Limit new rows to the installed modes' legal party numbers.
            if not ((kind == TRIAL_PARTY_TYPE and 1 <= number <= TRIAL_PARTY_COUNT)
                    or (kind == TOWER_PARTY_TYPE and 1 <= number <= TOWER_PARTY_COUNT)
                    or (16 <= kind <= 19 and 1 <= number <= CLIMBING_PARTY_COUNT)):
                raise LocalError("unknown_party", 404)
            existing = self.protocol.model('PartyInfo', {
                'Type': kind, 'UserId': player_id, 'No': number, 'Name': '',
                'IsActive': False, 'CharacterInfos': [], 'MagicItemEquipments': [],
                'TotalPower': 0, 'RentalCharacterInfos': []})
        text(fields["Name"], maximum=50, empty=True)
        if type(fields["IsActive"]) is not bool:
            raise LocalError("invalid_party_active")
        integer(fields["TotalPower"])
        characters = {p[0]: p for p in state["Characters"]}
        magic_items = {p[0]: p for p in state["MagicItems"]}
        members, codes = [], set()
        for value in sequence(fields["CharacterInfos"], maximum=100):
            member = self.protocol.fields("PartyCharacterInfo", value, strict=True)
            switch = integer(member["SwitchableCharacterIndex"], maximum=2**31 - 1)
            character = member["CharacterInfo"]
            if character is not None:
                code = integer(self.protocol.fields("CharacterInfo", character, strict=True)["Code"])
                if code not in characters:
                    raise LocalError("character_not_owned", 403)
                if code in codes:
                    raise LocalError("duplicate_party_character")
                codes.add(code)
                character = characters[code]
            members.append(self.protocol.model("PartyCharacterInfo", {"CharacterInfo": character,
                                                                       "SwitchableCharacterIndex": switch}))
        equipment, equipped, slots = [], set(), set()
        for value in sequence(fields["MagicItemEquipments"], maximum=100):
            item = self.protocol.fields("MagicItemEquipmentInfo", value, strict=True)
            code, slot = integer(item["CharacterCode"]), integer(item["EquipSlot"], maximum=2**31 - 1)
            magic = item["MagicItem"]
            if code not in characters and not (code == 0 and magic is None):
                raise LocalError("character_not_owned", 403)
            if (code, slot) in slots:
                raise LocalError("duplicate_equipment_slot")
            slots.add((code, slot))
            if magic is not None:
                magic_code = integer(self.protocol.fields("MagicItemInfo", magic, strict=True)["Code"])
                if magic_code not in magic_items:
                    raise LocalError("magic_item_not_owned", 403)
                if magic_code in equipped:
                    raise LocalError("duplicate_party_magic_item")
                equipped.add(magic_code)
                magic = magic_items[magic_code]
            equipment.append(self.protocol.model("MagicItemEquipmentInfo", {"CharacterCode": code,
                                "EquipSlot": slot, "MagicItem": magic}))
        old = self.protocol.fields("PartyInfo", existing)
        if fields["RentalCharacterInfos"] != old["RentalCharacterInfos"]:
            if 16 <= kind <= 19:
                from .climbing_catalog import ClimbingCatalog
                catalog = ClimbingCatalog(self.repository.connection)
                master = next(r for r in catalog.masters.values() if r['UserAttribute'] == kind - 15)
                fields['RentalCharacterInfos'] = catalog.canonical_rentals(
                    self.protocol, fields['RentalCharacterInfos'], master)
            elif kind == TRIAL_PARTY_TYPE:
                fields['RentalCharacterInfos'] = self.trial_battle.canonical_rentals(fields['RentalCharacterInfos'])
            else:
                raise LocalError("local_rental_changes_not_implemented", 501)
        fields["CharacterInfos"], fields["MagicItemEquipments"] = members, equipment
        # Power formulas need master data; never persist a fabricated client power.
        fields["TotalPower"] = old["TotalPower"] if (
            members, equipment, fields['RentalCharacterInfos']) == (
            old["CharacterInfos"], old["MagicItemEquipments"], old['RentalCharacterInfos']) else 0
        return self.protocol.model("PartyInfo", fields)

    def save_parties(self, request, values):
        session = self.session(request)
        if self.repository is None:
            raise LocalError("player_storage_unavailable", 503)
        with self.repository.transaction(session.player_id):
            state = self._state(session.player_id)
            canonical = [self._canonical_party(session.player_id, value, state) for value in values]
            keys = [(p[0], p[2]) for p in canonical]
            if len(set(keys)) != len(keys):
                raise LocalError("duplicate_party")
            for value in canonical:
                self.repository.save_party(session.player_id, value)

    def set_party_name(self, request, kind, number, name):
        session = self.session(request)
        if self.repository is None:
            raise LocalError("player_storage_unavailable", 503)
        with self.repository.transaction(session.player_id):
            state = self._state(session.player_id)
            party = next((p for p in state["Parties"] if (p[0], p[2]) == (kind, number)), None)
            if party is None:
                raise LocalError("unknown_party", 404)
            self.repository.save_party(session.player_id, self.protocol.model("PartyInfo", {"Name": name}, party))

    def set_tutorial(self, request, progress):
        session = self.session(request)
        if self.repository is None or not hasattr(self.repository, "update_player"):
            raise LocalError("local_tutorial_not_implemented", 501)
        self.repository.update_player(session.player_id, tutorial_progress=progress)

    def profile(self, request, target):
        session = self.session(request)
        if target != session.player_id:
            raise LocalError("local_external_profile_not_implemented", 501)
        template = self.templates.get((session.player_id, session.variant, "/profile/getprofileinfo"))
        if template is None:
            raise LocalError("local_profile_seed_not_found", 503)
        state = self._state(session.player_id)
        user = self.protocol.fields("UserInfo", state["User"])
        captured = self.protocol.fields("GetProfileInfoResponse", template)
        profile = self.protocol.fields("UserProfileInfo", captured["ProfileInfo"])
        personal = self.protocol.fields("UserPersonalInfo", profile["UserPersonalInfo"])
        if personal["Id"] != session.player_id:
            raise LocalError("profile_owner_mismatch", 503)
        fields = {"Name": user["Name"], "CharacterCode": user["ProfileCharacterCode"], "Level": user["Level"],
                  "LastLoggedInAt": user["LastLoggedInAt"], "IllustrationIndex": user["ProfileIllustrationIndex"]}
        selected_honor = state.get('ProfileHonorCode')
        if selected_honor is not None:
            fields['HonorCode'] = selected_honor or None
        character = next((c for c in state["Characters"] if c[0] == user["ProfileCharacterCode"]), None)
        if character is not None:
            fields.update(Rank=character[3], Rarity=character[5])
        personal = self.protocol.model("UserPersonalInfo", fields, profile["UserPersonalInfo"])
        profile = self.protocol.model("UserProfileInfo", {"UserPersonalInfo": personal}, captured["ProfileInfo"])
        return self.protocol.model("GetProfileInfoResponse", {"UpdateAccumulateInfos": state.get('UpdateAccumulateInfos', []),
                                                               "ProfileInfo": profile}, template)

    def update_profile(self, request, fields):
        session = self.session(request)
        if self.repository is None:
            raise LocalError("player_storage_unavailable", 503)
        with self.repository.transaction(session.player_id):
            return self._update_profile(request, fields, session)

    def _update_profile(self, request, fields, session):
        flag = integer(fields["UpdateFlag"], maximum=63)
        # Verified ProfileUpdateFlag bits in dump.cs; unsupported fields must stay unchanged.
        current = self.profile(request, session.player_id)
        profile = self.protocol.fields("GetProfileInfoResponse", current)["ProfileInfo"]
        personal = self.protocol.fields("UserProfileInfo", profile)["UserPersonalInfo"]
        existing = self.protocol.fields("UserPersonalInfo", personal)
        for bit, name in ((2, "Introduction"), (16, "SwitchableCharacterIndex")):
            if flag & bit and fields[name] != existing[name]:
                raise LocalError("local_profile_field_not_implemented", 501)
        changes = {}
        if flag & 1:
            changes["name"] = text(fields["Name"], maximum=50)
        if flag & 4:
            code = integer(fields['HonorCode'])
            if code and code != existing['HonorCode']:
                state = self._state(session.player_id)
                owned = {self.protocol.fields('HonorInfo', value)['HonorCode']
                         for value in state.get('Honors', [])}
                home = self.templates.get((session.player_id, session.variant, '/gametop/getgametopinfo'))
                if home is not None:
                    # Existing honors in this player's initialization remain owned;
                    # honors are permanent and cannot be supplied by the update request.
                    captured = self.protocol.fields('GetGameTopInfoResponse', home)
                    owned.update(self.protocol.fields('HonorInfo', value)['HonorCode']
                                 for value in captured['Honors'] or [])
                if code not in owned:
                    raise LocalError('honor_not_owned', 403)
            changes['profile_honor_code'] = code
        if flag & 8:
            code = integer(fields["CharacterCode"])
            state = self._state(session.player_id)
            if code not in {c[0] for c in state["Characters"]}:
                raise LocalError("character_not_owned", 403)
            changes["profile_character_code"] = code
        if flag & 32:
            # No master-data proof of unlocked alternate illustrations yet.
            index = integer(fields["IllustrationIndex"], maximum=2**31 - 1)
            if index != existing["IllustrationIndex"]:
                raise LocalError("local_illustration_unlock_not_implemented", 501)
        if changes:
            self.repository.update_player(session.player_id, **changes)
            if self.timing is not None and 'name' in changes and changes['name'] != existing['Name']:
                self.timing.event(session.player_id, 3, self.timing._effective_now(session.player_id, int(self.clock())))
        return self.protocol.fields("GetProfileInfoResponse", self.profile(request, session.player_id))["ProfileInfo"]
