"""Map business rows to positional MessagePack models; no replay bytes involved."""
from .player_protocol import PUBLIC_FIELDS


def model(registry, name, fields):
    indices = PUBLIC_FIELDS.get(name) or {f["name"]: f["index"] for f in registry.models[name]["fields"]}
    result = [None] * (max(indices.values()) + 1)
    for field, index in indices.items():
        result[index] = fields[field]
    return result


def protocol_state(registry, state):
    def pack(name, **fields):
        return model(registry, name, fields)

    player = state["player"]
    stamina = {row["kind"]: pack("Stamina", Value=row["value"], UpdatedAt=row["updated_at"]) for row in state["player_stamina"]}
    user = pack("UserInfo", Id=player["player_id"], Name=player["name"], Level=player["level"], Experience=player["experience"],
        Stamina=stamina.get("normal"), QuizStamina=stamina.get("quiz"), ProfileCharacterCode=player["profile_character_code"],
        TutorialProgressInfo=pack("TutorialProgressInfo", Progress=player["tutorial_progress"]) if player["tutorial_progress"] is not None else None,
        FirstLoggedInAt=player["first_logged_in_at"], LastLoggedInAt=player["last_logged_in_at"],
        IsChatBanned=player["is_chat_banned"], ProfileIllustrationIndex=player["profile_illustration_index"])
    characters = {row["character_code"]: pack("CharacterInfo", Code=row["character_code"], Level=row["level"], Exp=row["experience"],
        Rank=row["rank"], LimitBreak=row["limit_break"], Rarity=row["rarity"], Closeness=row["closeness"]) for row in state["characters"]}
    effects = {}
    for row in state["magic_item_effects"]:
        effects.setdefault(row["magic_item_code"], []).append(pack("MagicItemEffectInfo", MagicItemCode=row["magic_item_code"],
            EffectSlot=row["effect_slot"], EffectCode=row["effect_code"]))
    magic = {row["magic_item_code"]: pack("MagicItemInfo", Code=row["magic_item_code"], Level=row["level"],
        MagicItemEffects=effects.get(row["magic_item_code"], []), CreatedAt=row["created_at"]) for row in state["magic_items"]}
    party_members, party_equipment, party_rentals = {}, {}, {}
    for row in state["party_characters"]:
        key = (row["party_type"], row["party_no"])
        party_members.setdefault(key, []).append(pack("PartyCharacterInfo", CharacterInfo=characters.get(row["character_code"]),
            SwitchableCharacterIndex=row["switchable_character_index"]))
    for row in state["party_magic_items"]:
        key = (row["party_type"], row["party_no"])
        party_equipment.setdefault(key, []).append(pack("MagicItemEquipmentInfo", CharacterCode=row["character_code"] if row["character_code"] is not None else 0,
            EquipSlot=row["equip_slot"], MagicItem=magic.get(row["magic_item_code"])))
    for row in state["party_rentals"]:
        key = (row["party_type"], row["party_no"])
        party_rentals.setdefault(key, []).append(pack("RentalCharacterInfo", RentalCharacterCode=row["rental_character_code"],
            SwitchableCharacterIndex=row["switchable_character_index"]))
    parties = []
    for row in state["parties"]:
        key = (row["party_type"], row["party_no"])
        parties.append(pack("PartyInfo", Type=row["party_type"], UserId=player["player_id"], No=row["party_no"], Name=row["name"],
            IsActive=row["is_active"], CharacterInfos=party_members.get(key, []), MagicItemEquipments=party_equipment.get(key, []),
            TotalPower=row["total_power"], RentalCharacterInfos=party_rentals.get(key, [])))

    def counter(row, prefix):
        return pack("CountWithResetTime", Count=row[prefix + "_count"], LastResetAt=row[prefix + "_last_reset_at"]) if row[prefix + "_count"] is not None else None

    quests = [pack("QuestInfo", Code=row["quest_code"], ClearCount=row["clear_count"], StarCount=row["star_count"],
        RemainChallengeCount=counter(row, "challenge"), RemainRecoverChallengeCount=counter(row, "recover")) for row in state["quests"]]
    groups = [pack("QuestGroupInfo", QuestGroupCode=row["quest_group_code"], ClearCount=row["clear_count"],
        RemainChallengeCount=counter(row, "challenge"), RemainRecoverChallengeCount=counter(row, "recover")) for row in state["quest_groups"]]
    result = {"User": user, "ProfileHonorCode": player.get('profile_honor_code'),
        "FavoriteCharacterCodes": list(player.get('favorite_character_codes') or []),
        "Characters": list(characters.values()),
        "Equipments": [pack("EquipmentInfo", CharacterCode=row["character_code"], Slot=row["slot"]) for row in state["character_equipment"]],
        "StackItems": [pack("StackItemInfo", ItemCode=row["item_code"], Count=row["quantity"], RecoveredAt=row["recovered_at"]) for row in state["items"]],
        "MagicItems": list(magic.values()), "Parties": parties, "ClearedQuests": quests, "QuestGroups": groups,
        "QuestClearCounts": [pack("QuestClearCountInfo", QuestCode=row["quest_code"], Count=row["count"]) for row in state["quest_clear_counts"]],
        "Stories": [pack("StoryInfo", StoryCode=row["story_code"], StoryStatus=row["status"]) for row in state["stories"]]}
    home = state.get('home')
    if player.get('box_lotteries') is not None:
        result['BoxLotteries'] = player['box_lotteries']
    if state.get('skill_tree') is not None:
        result['SkillTree'] = state['skill_tree']
    if home is not None:
        result.update(HomeInfo=pack('HomeInfo', Situations=home['situations'], CharacterCostumeCode=home['character_costume_code']),
                      HomeCharacters=home['home_characters'], QuizAnswers=home['quiz_answers'])
    return result
