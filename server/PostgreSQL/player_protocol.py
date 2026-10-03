"""Protocol adapters for current state. No schema definitions are stored here in SQL."""
from mog_protocol.codec import decode


class InvalidPlayerData(ValueError):
    pass


# These two public-field models were omitted by the old property-only extractor.
# Verified in dump.cs: TutorialProgressInfo Key(0); CountWithResetTime Key(1), Key(2).
PUBLIC_FIELDS = {"TutorialProgressInfo": {"Progress": 0},
                 "CountWithResetTime": {"Count": 1, "LastResetAt": 2}}


def record(registry, model, value):
    fields = PUBLIC_FIELDS.get(model) or {f["name"]: f["index"] for f in registry.models[model]["fields"]}
    if not isinstance(value, list) or not fields or len(value) <= max(fields.values()):
        raise InvalidPlayerData("Incomplete " + model)
    return {name: value[index] for name, index in fields.items()}


def integer(value, label):
    if type(value) is not int or not -(2**63) <= value < 2**63:
        raise InvalidPlayerData("Invalid integer: " + label)
    return value


def string(value, label):
    if not isinstance(value, str) or "\x00" in value:
        raise InvalidPlayerData("Invalid text: " + label)
    return value


def boolean(value, label):
    if type(value) is not bool:
        raise InvalidPlayerData("Invalid boolean: " + label)
    return value


def collection(value, label):
    if not isinstance(value, list):
        raise InvalidPlayerData("Missing collection: " + label)
    return value


def character(registry, value):
    data = record(registry, "CharacterInfo", value)
    return {column: integer(data[field], field) for column, field in
            (("character_code", "Code"), ("level", "Level"), ("experience", "Exp"),
             ("rank", "Rank"), ("limit_break", "LimitBreak"), ("rarity", "Rarity"), ("closeness", "Closeness"))}


def home_state(registry, body):
    """Validate the player's home seed, preserving list order and event progress."""
    login = record(registry, "UserLoginResponse", decode(body))
    if login['HomeInfo'] in (None, []):
        return None
    home = record(registry, 'HomeInfo', login['HomeInfo'])
    integer(home['CharacterCostumeCode'], 'CharacterCostumeCode')
    for value in collection(home['Situations'], 'Situations'):
        situation = record(registry, 'HomeSituationInfo', value)
        integer(situation['SituationCode'], 'SituationCode')
        for code in collection(situation['EventCodes'], 'EventCodes'):
            integer(code, 'EventCode')
    characters = collection(login['HomeCharacters'], 'HomeCharacters')
    for value in characters:
        data = record(registry, 'HomeCharacterInfo', value)
        for name in ('HomeCharacterCode', 'ClosenessLevel', 'ClosenessExp'):
            integer(data[name], name)
        boolean(data['IsRandomCostume'], 'IsRandomCostume')
        for name in ('AvailableQuizzes', 'HomeCharacterCostumeCodes'):
            for code in collection(data[name], name):
                integer(code, name)
    answers = collection(login['QuizAnswers'], 'QuizAnswers')
    for value in answers:
        data = record(registry, 'QuizAnswerInfo', value)
        for field in registry.models['QuizAnswerInfo']['fields']:
            item = data[field['name']]
            if field['type'].startswith('List<'):
                for answer in collection(item, field['name']):
                    integer(answer, field['name'])
            else:
                integer(item, field['name'])
    return {'character_costume_code': home['CharacterCostumeCode'], 'situations': home['Situations'],
            'home_characters': characters, 'quiz_answers': answers}


def reset_count(registry, value, prefix):
    if value is None:
        return {prefix + "_count": None, prefix + "_last_reset_at": None}
    data = record(registry, "CountWithResetTime", value)
    return {prefix + "_count": integer(data["Count"], "Count"),
            prefix + "_last_reset_at": integer(data["LastResetAt"], "LastResetAt")}


def party_rows(registry, player_id, value):
    data = record(registry, "PartyInfo", value)
    if data["UserId"] != player_id:
        raise InvalidPlayerData("Party belongs to a different player")
    key = {"player_id": player_id, "party_type": integer(data["Type"], "Type"),
           "party_no": integer(data["No"], "No")}
    rows = {"parties": [{**key, "name": string(data["Name"], "Name"),
                          "is_active": boolean(data["IsActive"], "IsActive"),
                          "total_power": integer(data["TotalPower"], "TotalPower")}],
            "party_characters": [], "party_magic_items": [], "party_rentals": []}
    for position, item in enumerate(collection(data["CharacterInfos"], "CharacterInfos")):
        member = record(registry, "PartyCharacterInfo", item)
        code = character(registry, member["CharacterInfo"])["character_code"] if member["CharacterInfo"] is not None else None
        rows["party_characters"].append({**key, "position": position, "character_code": code,
            "switchable_character_index": integer(member["SwitchableCharacterIndex"], "SwitchableCharacterIndex")})
    for position, item in enumerate(collection(data["MagicItemEquipments"], "MagicItemEquipments")):
        equipment = record(registry, "MagicItemEquipmentInfo", item)
        magic = record(registry, "MagicItemInfo", equipment["MagicItem"]) if equipment["MagicItem"] is not None else None
        character_code = integer(equipment["CharacterCode"], "CharacterCode")
        if character_code == 0 and magic is not None:
            raise InvalidPlayerData("A magic item needs an owned character")
        rows["party_magic_items"].append({**key, "position": position,
            "character_code": character_code if character_code != 0 else None,
            "equip_slot": integer(equipment["EquipSlot"], "EquipSlot"),
            "magic_item_code": integer(magic["Code"], "Code") if magic is not None else None})
    for position, item in enumerate(collection(data["RentalCharacterInfos"], "RentalCharacterInfos")):
        rental = record(registry, "RentalCharacterInfo", item)
        rows["party_rentals"].append({**key, "position": position,
            "rental_character_code": integer(rental["RentalCharacterCode"], "RentalCharacterCode"),
            "switchable_character_index": integer(rental["SwitchableCharacterIndex"], "SwitchableCharacterIndex")})
    return rows


def login_rows(registry, body):
    """Extract only root-owned collections, never nested social/rental characters."""
    login = record(registry, "UserLoginResponse", decode(body))
    user = record(registry, "UserInfo", login["User"])
    player_id = string(user["Id"], "Id")
    if not player_id:
        raise InvalidPlayerData("Empty player ID")
    tutorial = record(registry, "TutorialProgressInfo", user["TutorialProgressInfo"]) if user["TutorialProgressInfo"] is not None else None
    player = {"player_id": player_id, "name": string(user["Name"], "Name"),
              "level": integer(user["Level"], "Level"), "experience": integer(user["Experience"], "Experience"),
              "profile_character_code": integer(user["ProfileCharacterCode"], "ProfileCharacterCode"),
              "tutorial_progress": integer(tutorial["Progress"], "Progress") if tutorial else None,
              "first_logged_in_at": integer(user["FirstLoggedInAt"], "FirstLoggedInAt"),
              "last_logged_in_at": integer(user["LastLoggedInAt"], "LastLoggedInAt"),
              "is_chat_banned": boolean(user["IsChatBanned"], "IsChatBanned"),
              "profile_illustration_index": integer(user["ProfileIllustrationIndex"], "ProfileIllustrationIndex")}
    rows = {name: [] for name in ("player_stamina", "characters", "items", "character_equipment", "magic_items",
            "magic_item_effects", "parties", "party_characters", "party_magic_items", "party_rentals",
            "quests", "quest_groups", "quest_clear_counts", "stories")}
    rows["players"] = [player]
    for key, kind in (("Stamina", "normal"), ("QuizStamina", "quiz")):
        if user[key] is not None:
            stamina = record(registry, "Stamina", user[key])
            rows["player_stamina"].append({"player_id": player_id, "kind": kind,
                "value": integer(stamina["Value"], "Value"), "updated_at": integer(stamina["UpdatedAt"], "UpdatedAt")})
    for value in collection(login["Characters"], "Characters"):
        rows["characters"].append({"player_id": player_id, **character(registry, value)})
    for value in collection(login["StackItems"], "StackItems"):
        item = record(registry, "StackItemInfo", value)
        rows["items"].append({"player_id": player_id, "item_code": integer(item["ItemCode"], "ItemCode"),
                             "quantity": integer(item["Count"], "Count"), "recovered_at": integer(item["RecoveredAt"], "RecoveredAt")})
    for value in collection(login["Equipments"], "Equipments"):
        equipment = record(registry, "EquipmentInfo", value)
        rows["character_equipment"].append({"player_id": player_id,
            "character_code": integer(equipment["CharacterCode"], "CharacterCode"), "slot": integer(equipment["Slot"], "Slot")})
    for value in collection(login["MagicItems"], "MagicItems"):
        magic = record(registry, "MagicItemInfo", value)
        code = integer(magic["Code"], "Code")
        rows["magic_items"].append({"player_id": player_id, "magic_item_code": code,
                                  "level": integer(magic["Level"], "Level"), "created_at": integer(magic["CreatedAt"], "CreatedAt")})
        for effect_value in collection(magic["MagicItemEffects"], "MagicItemEffects"):
            effect = record(registry, "MagicItemEffectInfo", effect_value)
            if effect["MagicItemCode"] != code:
                raise InvalidPlayerData("Effect belongs to a different magic item")
            rows["magic_item_effects"].append({"player_id": player_id, "magic_item_code": code,
                "effect_slot": integer(effect["EffectSlot"], "EffectSlot"), "effect_code": integer(effect["EffectCode"], "EffectCode")})
    for value in collection(login["Parties"], "Parties"):
        for table, party in party_rows(registry, player_id, value).items():
            rows[table].extend(party)
    for source, model, table, code_field, code_column in (
            ("ClearedQuests", "QuestInfo", "quests", "Code", "quest_code"),
            ("QuestGroups", "QuestGroupInfo", "quest_groups", "QuestGroupCode", "quest_group_code")):
        for value in collection(login[source], source):
            quest = record(registry, model, value)
            row = {"player_id": player_id, code_column: integer(quest[code_field], code_field),
                   "clear_count": integer(quest["ClearCount"], "ClearCount"),
                   **reset_count(registry, quest["RemainChallengeCount"], "challenge"),
                   **reset_count(registry, quest["RemainRecoverChallengeCount"], "recover")}
            if table == "quests":
                row["star_count"] = integer(quest["StarCount"], "StarCount")
            rows[table].append(row)
    for value in collection(login["QuestClearCounts"], "QuestClearCounts"):
        count = record(registry, "QuestClearCountInfo", value)
        rows["quest_clear_counts"].append({"player_id": player_id, "quest_code": integer(count["QuestCode"], "QuestCode"),
                                           "count": integer(count["Count"], "Count")})
    for value in collection(login["Stories"], "Stories"):
        story = record(registry, "StoryInfo", value)
        rows["stories"].append({"player_id": player_id, "story_code": integer(story["StoryCode"], "StoryCode"),
                               "status": integer(story["StoryStatus"], "StoryStatus")})
    return rows
