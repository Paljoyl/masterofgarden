-- Generated from mog_protocol/schemas.json; regenerate with database_cli.py generate.
-- Nullable fields preserve partial messages; node_path identifies nested records.
CREATE TABLE IF NOT EXISTS protocol_data."AccumulateInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Count" BIGINT,
    "CountUpAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_34f9cab4c9da5a39 ON protocol_data."AccumulateInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."AccumulateInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."AccumulateInfo"."Count" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."AccumulateInfo"."CountUpAt" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."AdventureFlagInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "AdventureFlagCode" BIGINT,
    "FlagValue" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ba0e80fa95f39c1a ON protocol_data."AdventureFlagInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."AdventureFlagInfo"."AdventureFlagCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."AdventureFlagInfo"."FlagValue" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."ApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e3c06a73ca225d6f ON protocol_data."ApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."ArenaApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e21a24725e9b514a ON protocol_data."ArenaApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."ArenaHistoryInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "PersonalInfo" JSONB,
    "Result" JSONB,
    "BattleWinCount" INTEGER,
    "EnemyPartyBattlePower" BIGINT,
    "HistoryId" JSONB,
    "HistoryAt" BIGINT,
    "OpenHistoryDetail" BOOLEAN,
    "EnemyPartySkillTreeBattlePower" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_7ff77aa77044e634 ON protocol_data."ArenaHistoryInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."PersonalInfo" IS 'Key(0); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."Result" IS 'Key(1); C# BattleResult';
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."BattleWinCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."EnemyPartyBattlePower" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."HistoryId" IS 'Key(4); C# Ulid';
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."HistoryAt" IS 'Key(5); C# long';
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."OpenHistoryDetail" IS 'Key(6); C# bool';
COMMENT ON COLUMN protocol_data."ArenaHistoryInfo"."EnemyPartySkillTreeBattlePower" IS 'Key(7); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."ArenaPartyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterInfos" JSONB,
    "EquipmentInfos" JSONB,
    "MagicItemEquipments" JSONB,
    "PartyCharacterInfos" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3f7c3213c259b840 ON protocol_data."ArenaPartyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ArenaPartyInfo"."CharacterInfos" IS 'Key(0); C# List<CharacterInfo>';
COMMENT ON COLUMN protocol_data."ArenaPartyInfo"."EquipmentInfos" IS 'Key(1); C# List<EquipmentInfo>';
COMMENT ON COLUMN protocol_data."ArenaPartyInfo"."MagicItemEquipments" IS 'Key(2); C# List<MagicItemEquipmentInfo>';
COMMENT ON COLUMN protocol_data."ArenaPartyInfo"."PartyCharacterInfos" IS 'Key(3); C# List<PartyCharacterInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."ArenaUserInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "PersonalInfo" JSONB,
    "PartyInfos" JSONB,
    "Rank" INTEGER,
    "SkillTreeInfo" JSONB,
    "SkillTreeBattlePower" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_0b210697bc0dcded ON protocol_data."ArenaUserInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ArenaUserInfo"."PersonalInfo" IS 'Key(0); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."ArenaUserInfo"."PartyInfos" IS 'Key(1); C# List<ArenaPartyInfo>';
COMMENT ON COLUMN protocol_data."ArenaUserInfo"."Rank" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."ArenaUserInfo"."SkillTreeInfo" IS 'Key(3); C# SkillTreeInfo';
COMMENT ON COLUMN protocol_data."ArenaUserInfo"."SkillTreeBattlePower" IS 'Key(4); C# List<long>';
CREATE TABLE IF NOT EXISTS protocol_data."BattlePassInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "BattlePassCode" BIGINT,
    "TotalPoint" INTEGER,
    "NormalRewardReceivedLevel" INTEGER,
    "SpecialRewardReceivedLevel" INTEGER,
    "WeeklyPoint" INTEGER,
    "WeeklyPointReceivedAt" JSONB,
    "IsPurchased" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_2aca07c6239dad40 ON protocol_data."BattlePassInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."BattlePassInfo"."BattlePassCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."BattlePassInfo"."TotalPoint" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."BattlePassInfo"."NormalRewardReceivedLevel" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."BattlePassInfo"."SpecialRewardReceivedLevel" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."BattlePassInfo"."WeeklyPoint" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."BattlePassInfo"."WeeklyPointReceivedAt" IS 'Key(5); C# DateTime';
COMMENT ON COLUMN protocol_data."BattlePassInfo"."IsPurchased" IS 'Key(6); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."BattleResultInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "BattleResultPartyMemberInfo" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_2c413816020bc7ac ON protocol_data."BattleResultInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."BattleResultInfo"."BattleResultPartyMemberInfo" IS 'Key(0); C# BattleResultPartyMemberInfo';
CREATE TABLE IF NOT EXISTS protocol_data."BattleResultPartyMemberInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MemberIndex" INTEGER,
    "CharacterCode" BIGINT,
    "LastHp" INTEGER,
    "SpecialSkillCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b2a9d21bb55bbd95 ON protocol_data."BattleResultPartyMemberInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."BattleResultPartyMemberInfo"."MemberIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."BattleResultPartyMemberInfo"."CharacterCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."BattleResultPartyMemberInfo"."LastHp" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."BattleResultPartyMemberInfo"."SpecialSkillCount" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."BossDamageInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "EnemyIndex" INTEGER,
    "GiveDamage" BIGINT,
    "OverKillDamage" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b03936a76f893ef1 ON protocol_data."BossDamageInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."BossDamageInfo"."EnemyIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."BossDamageInfo"."GiveDamage" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."BossDamageInfo"."OverKillDamage" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."BossHpInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "EnemyIndex" INTEGER,
    "Hp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_fcd1066993bfb8df ON protocol_data."BossHpInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."BossHpInfo"."EnemyIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."BossHpInfo"."Hp" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."BoxItemLineupCodesResponce" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Lineups" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_fa9d08bc8b479478 ON protocol_data."BoxItemLineupCodesResponce" (owner_user_id);
COMMENT ON COLUMN protocol_data."BoxItemLineupCodesResponce"."Lineups" IS 'Key(0); C# List<BoxItemLineupCodesResult>';
CREATE TABLE IF NOT EXISTS protocol_data."BoxItemLineupCodesResult" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "LowerLimitUserLevel" BIGINT,
    "BoxItemLotteryCode" BIGINT,
    "IsSwitchedLineup" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3fa5cd60132a481f ON protocol_data."BoxItemLineupCodesResult" (owner_user_id);
COMMENT ON COLUMN protocol_data."BoxItemLineupCodesResult"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."BoxItemLineupCodesResult"."LowerLimitUserLevel" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."BoxItemLineupCodesResult"."BoxItemLotteryCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."BoxItemLineupCodesResult"."IsSwitchedLineup" IS 'Key(3); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."BoxItemLotterySimulationResult" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Name" TEXT,
    "Amount" BIGINT,
    "Count" BIGINT,
    "SettingRate" JSONB,
    "AppearRate" JSONB,
    "ExpectedValue" JSONB,
    "Difference" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_7334526fa5900953 ON protocol_data."BoxItemLotterySimulationResult" (owner_user_id);
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."Name" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."Amount" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."Count" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."SettingRate" IS 'Key(4); C# Decimal';
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."AppearRate" IS 'Key(5); C# Decimal';
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."ExpectedValue" IS 'Key(6); C# Decimal';
COMMENT ON COLUMN protocol_data."BoxItemLotterySimulationResult"."Difference" IS 'Key(7); C# Decimal';
CREATE TABLE IF NOT EXISTS protocol_data."BoxLotteryApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9b762adb27d3736a ON protocol_data."BoxLotteryApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."BoxLotteryInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "BoxLotteryCode" BIGINT,
    "CurrentSheetNo" INTEGER,
    "BoxLotterySheets" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_4586ff9ad1af786e ON protocol_data."BoxLotteryInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."BoxLotteryInfo"."BoxLotteryCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."BoxLotteryInfo"."CurrentSheetNo" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."BoxLotteryInfo"."BoxLotterySheets" IS 'Key(2); C# List<BoxLotterySheetInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."BoxLotterySheetInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "SheetNo" INTEGER,
    "LineupIndex" INTEGER,
    "GetCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_25cdbd11440f39b7 ON protocol_data."BoxLotterySheetInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."BoxLotterySheetInfo"."SheetNo" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."BoxLotterySheetInfo"."LineupIndex" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."BoxLotterySheetInfo"."GetCount" IS 'Key(2); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."CharacterIllustrationInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "IllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_08e25386c59d14c9 ON protocol_data."CharacterIllustrationInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."CharacterIllustrationInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."CharacterIllustrationInfo"."IllustrationIndex" IS 'Key(1); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."CharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Level" INTEGER,
    "Exp" BIGINT,
    "Rank" INTEGER,
    "LimitBreak" INTEGER,
    "Rarity" INTEGER,
    "Closeness" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9f33197a981e93af ON protocol_data."CharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."CharacterInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."CharacterInfo"."Level" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."CharacterInfo"."Exp" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."CharacterInfo"."Rank" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."CharacterInfo"."LimitBreak" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."CharacterInfo"."Rarity" IS 'Key(5); C# int';
COMMENT ON COLUMN protocol_data."CharacterInfo"."Closeness" IS 'Key(6); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."ChatLogInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Id" TEXT,
    "Gamedata" TEXT,
    "Timestamp" JSONB,
    "Message" TEXT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_6d7bd605adeddd5c ON protocol_data."ChatLogInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ChatLogInfo"."Id" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."ChatLogInfo"."Gamedata" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."ChatLogInfo"."Timestamp" IS 'Key(2); C# DateTime';
COMMENT ON COLUMN protocol_data."ChatLogInfo"."Message" IS 'Key(3); C# string';
CREATE TABLE IF NOT EXISTS protocol_data."ClearFloorInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Floor" INTEGER,
    "FirstClearedAt" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_1208b6e4808f8857 ON protocol_data."ClearFloorInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ClearFloorInfo"."Floor" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."ClearFloorInfo"."FirstClearedAt" IS 'Key(1); C# DateTime';
CREATE TABLE IF NOT EXISTS protocol_data."ClimbingApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b25cc76b047091cf ON protocol_data."ClimbingApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."ClimbingCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Rarity" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e1aaa18bf15753d8 ON protocol_data."ClimbingCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ClimbingCharacterInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ClimbingCharacterInfo"."Rarity" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."ClimbingCharacterStatusInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Hp" INTEGER,
    "Sp" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_02eda831e8014740 ON protocol_data."ClimbingCharacterStatusInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ClimbingCharacterStatusInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ClimbingCharacterStatusInfo"."Hp" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."ClimbingCharacterStatusInfo"."Sp" IS 'Key(2); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."ClimbingMatchingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserId" TEXT,
    "FloorNumber" INTEGER,
    "SyncLevel" INTEGER,
    "ClimbingPartyInfos" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e1a30c5ed86e59af ON protocol_data."ClimbingMatchingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ClimbingMatchingInfo"."UserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."ClimbingMatchingInfo"."FloorNumber" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."ClimbingMatchingInfo"."SyncLevel" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."ClimbingMatchingInfo"."ClimbingPartyInfos" IS 'Key(3); C# List<ClimbingPartyInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."ClimbingPartyCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ClimbingCharacterInfo" JSONB,
    "SwitchableCharacterIndex" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_a1062efca8da76c4 ON protocol_data."ClimbingPartyCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ClimbingPartyCharacterInfo"."ClimbingCharacterInfo" IS 'Key(0); C# ClimbingCharacterInfo';
COMMENT ON COLUMN protocol_data."ClimbingPartyCharacterInfo"."SwitchableCharacterIndex" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."ClimbingPartyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "No" INTEGER,
    "ClimbingPartyCharacterInfos" JSONB,
    "MagicItemEquipments" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_4d16b88c0e81280c ON protocol_data."ClimbingPartyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ClimbingPartyInfo"."No" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."ClimbingPartyInfo"."ClimbingPartyCharacterInfos" IS 'Key(1); C# List<ClimbingPartyCharacterInfo>';
COMMENT ON COLUMN protocol_data."ClimbingPartyInfo"."MagicItemEquipments" IS 'Key(2); C# List<MagicItemEquipmentInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."ClimbingRentalCharacterStatusInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Hp" INTEGER,
    "Sp" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_4f7b7dcbb59038e7 ON protocol_data."ClimbingRentalCharacterStatusInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ClimbingRentalCharacterStatusInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ClimbingRentalCharacterStatusInfo"."Hp" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."ClimbingRentalCharacterStatusInfo"."Sp" IS 'Key(2); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."CommonApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9155709eb7a30cf6 ON protocol_data."CommonApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."CountWithResetTime" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_8143df5ac1c9f9d7 ON protocol_data."CountWithResetTime" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."DebugSetCharacterStatus" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Info" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e4344f41c9ceb212 ON protocol_data."DebugSetCharacterStatus" (owner_user_id);
COMMENT ON COLUMN protocol_data."DebugSetCharacterStatus"."Info" IS 'Key(0); C# CharacterInfo';
CREATE TABLE IF NOT EXISTS protocol_data."DropItemResultViewInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Count" BIGINT,
    "BoxItemCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_1ca6ea57547f3af3 ON protocol_data."DropItemResultViewInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DropItemResultViewInfo"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."DropItemResultViewInfo"."Count" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."DropItemResultViewInfo"."BoxItemCode" IS 'Key(2); C# Nullable<long>';
CREATE TABLE IF NOT EXISTS protocol_data."DuelApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b9bcc4597419302d ON protocol_data."DuelApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."DuelBattleInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Day" INTEGER,
    "Stage" INTEGER,
    "BattleNumber" INTEGER,
    "IsSyncLevel" BOOLEAN,
    "TargetUserId" TEXT,
    "DuelUserInfo" JSONB,
    "BattleResult" JSONB,
    "Position" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3b433fe6ad036f94 ON protocol_data."DuelBattleInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."Day" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."Stage" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."BattleNumber" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."IsSyncLevel" IS 'Key(3); C# bool';
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."TargetUserId" IS 'Key(4); C# string';
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."DuelUserInfo" IS 'Key(5); C# DuelUserInfo';
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."BattleResult" IS 'Key(6); C# DuelBattleResultForBattle';
COMMENT ON COLUMN protocol_data."DuelBattleInfo"."Position" IS 'Key(7); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."DuelMyProfileInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserId" TEXT,
    "UserName" TEXT,
    "ProfileCharacterCode" BIGINT,
    "HonorCode" BIGINT,
    "ProfileCharacterRank" INTEGER,
    "ProfileCharacterRarity" INTEGER,
    "ProfileIllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_48d76fa8dfb9d6c7 ON protocol_data."DuelMyProfileInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DuelMyProfileInfo"."UserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."DuelMyProfileInfo"."UserName" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."DuelMyProfileInfo"."ProfileCharacterCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."DuelMyProfileInfo"."HonorCode" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."DuelMyProfileInfo"."ProfileCharacterRank" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."DuelMyProfileInfo"."ProfileCharacterRarity" IS 'Key(5); C# int';
COMMENT ON COLUMN protocol_data."DuelMyProfileInfo"."ProfileIllustrationIndex" IS 'Key(6); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."DuelMyRankingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DuelCode" BIGINT,
    "Rank" BIGINT,
    "Score" BIGINT,
    "ScoreUpdatedAt" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_5754429c6cab5883 ON protocol_data."DuelMyRankingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DuelMyRankingInfo"."DuelCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."DuelMyRankingInfo"."Rank" IS 'Key(1); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."DuelMyRankingInfo"."Score" IS 'Key(2); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."DuelMyRankingInfo"."ScoreUpdatedAt" IS 'Key(3); C# Nullable<DateTimeOffset>';
CREATE TABLE IF NOT EXISTS protocol_data."DuelRoundInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "RemainingHealth" REAL,
    "RemainingSeconds" INTEGER,
    "BattleResult" JSONB,
    "BattleNumber" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_69112275ffffaf3a ON protocol_data."DuelRoundInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DuelRoundInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."DuelRoundInfo"."RemainingHealth" IS 'Key(1); C# float';
COMMENT ON COLUMN protocol_data."DuelRoundInfo"."RemainingSeconds" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."DuelRoundInfo"."BattleResult" IS 'Key(3); C# DuelBattleResultForBattle';
COMMENT ON COLUMN protocol_data."DuelRoundInfo"."BattleNumber" IS 'Key(4); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."DuelRoundResultInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "BattleScore" BIGINT,
    "RemainHpScore" INTEGER,
    "RemainSecondsScore" INTEGER,
    "TotalScore" INTEGER,
    "BattleResult" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_177ad300207fdf97 ON protocol_data."DuelRoundResultInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DuelRoundResultInfo"."BattleScore" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."DuelRoundResultInfo"."RemainHpScore" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."DuelRoundResultInfo"."RemainSecondsScore" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."DuelRoundResultInfo"."TotalScore" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."DuelRoundResultInfo"."BattleResult" IS 'Key(5); C# DuelBattleResultForBattle';
CREATE TABLE IF NOT EXISTS protocol_data."DuelUserInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "PersonalInfo" JSONB,
    "PartyInfo" JSONB,
    "ClosenessDic" JSONB,
    "ClosenessLevelMapByHomeCharacterCode" JSONB,
    "SkillTreeInfo" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_0179d2f3bd6eedb5 ON protocol_data."DuelUserInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DuelUserInfo"."PersonalInfo" IS 'Key(0); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."DuelUserInfo"."PartyInfo" IS 'Key(1); C# ArenaPartyInfo';
COMMENT ON COLUMN protocol_data."DuelUserInfo"."ClosenessDic" IS 'Key(2); C# Dictionary<long, int>';
COMMENT ON COLUMN protocol_data."DuelUserInfo"."ClosenessLevelMapByHomeCharacterCode" IS 'Key(3); C# Dictionary<long, int>';
COMMENT ON COLUMN protocol_data."DuelUserInfo"."SkillTreeInfo" IS 'Key(4); C# SkillTreeInfo';
CREATE TABLE IF NOT EXISTS protocol_data."DuelUserRankingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DuelCode" BIGINT,
    "UserId" TEXT,
    "Rank" BIGINT,
    "Score" BIGINT,
    "UserName" TEXT,
    "ProfileCharacterCode" BIGINT,
    "HonorCode" BIGINT,
    "ProfileCharacterRank" INTEGER,
    "ProfileCharacterRarity" INTEGER,
    "ScoreUpdatedAt" JSONB,
    "ProfileIllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_93433b3c44d11f18 ON protocol_data."DuelUserRankingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."DuelCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."UserId" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."Rank" IS 'Key(2); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."Score" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."UserName" IS 'Key(4); C# string';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."ProfileCharacterCode" IS 'Key(5); C# long';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."HonorCode" IS 'Key(6); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."ProfileCharacterRank" IS 'Key(7); C# int';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."ProfileCharacterRarity" IS 'Key(8); C# int';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."ScoreUpdatedAt" IS 'Key(9); C# Nullable<DateTimeOffset>';
COMMENT ON COLUMN protocol_data."DuelUserRankingInfo"."ProfileIllustrationIndex" IS 'Key(10); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2ApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_53e28944266cde97 ON protocol_data."Dungeon2ApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2BattleResultInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Dungeon2Code" BIGINT,
    "HierarchyIndex" INTEGER,
    "SquareIndex" INTEGER,
    "Dungeon2Characters" JSONB,
    "Dungeon2Enemies" JSONB,
    "Dungeon2RentalCharacters" JSONB,
    "RemainingHealth" DOUBLE PRECISION,
    "RemainingSeconds" DOUBLE PRECISION,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_0a4254f2ee6e78eb ON protocol_data."Dungeon2BattleResultInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."Dungeon2Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."HierarchyIndex" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."SquareIndex" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."Dungeon2Characters" IS 'Key(3); C# List<Dungeon2CharacterInfo>';
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."Dungeon2Enemies" IS 'Key(4); C# List<Dungeon2EnemyInfo>';
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."Dungeon2RentalCharacters" IS 'Key(5); C# List<Dungeon2RentalCharacterInfo>';
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."RemainingHealth" IS 'Key(6); C# double';
COMMENT ON COLUMN protocol_data."Dungeon2BattleResultInfo"."RemainingSeconds" IS 'Key(7); C# double';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2CharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "Hp" BIGINT,
    "Sp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ca363720bfc5bd0e ON protocol_data."Dungeon2CharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2CharacterInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2CharacterInfo"."Hp" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2CharacterInfo"."Sp" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2EnemyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Wave" INTEGER,
    "Index" INTEGER,
    "QuestCode" BIGINT,
    "EnemyCode" BIGINT,
    "Hp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_43557d5702244e17 ON protocol_data."Dungeon2EnemyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2EnemyInfo"."Wave" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2EnemyInfo"."Index" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2EnemyInfo"."QuestCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2EnemyInfo"."EnemyCode" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2EnemyInfo"."Hp" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2GroupScoreInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DungeonGroupCode" BIGINT,
    "HighestScore" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9824ecbb1f89cfc1 ON protocol_data."Dungeon2GroupScoreInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2GroupScoreInfo"."DungeonGroupCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2GroupScoreInfo"."HighestScore" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2HierarchyArtifactInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "HierarchyIndex" INTEGER,
    "SquareIndex" INTEGER,
    "ChoiceType" INTEGER,
    "RewardIndex" INTEGER,
    "ArtifactIndex" INTEGER,
    "ArtifactCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_a9bc69db53bcc8fa ON protocol_data."Dungeon2HierarchyArtifactInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyArtifactInfo"."HierarchyIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyArtifactInfo"."SquareIndex" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyArtifactInfo"."ChoiceType" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyArtifactInfo"."RewardIndex" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyArtifactInfo"."ArtifactIndex" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyArtifactInfo"."ArtifactCode" IS 'Key(5); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2HierarchyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "HierarchyIndex" INTEGER,
    "IsPlaying" BOOLEAN,
    "IsFirstRewardObtained" SMALLINT,
    "ClearCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_d2d13d08da7d66d3 ON protocol_data."Dungeon2HierarchyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyInfo"."HierarchyIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyInfo"."IsPlaying" IS 'Key(1); C# bool';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyInfo"."IsFirstRewardObtained" IS 'Key(2); C# byte';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchyInfo"."ClearCount" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2HierarchySquareInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "SquareIndex" INTEGER,
    "Position" INTEGER,
    "PlayStatus" JSONB,
    "LeftChoiceWinning" BOOLEAN,
    "RightChoiceWinning" BOOLEAN,
    "HierarchyArtifacts" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_417e2492791bbf4e ON protocol_data."Dungeon2HierarchySquareInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2HierarchySquareInfo"."SquareIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchySquareInfo"."Position" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchySquareInfo"."PlayStatus" IS 'Key(2); C# DungeonPlayStatus';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchySquareInfo"."LeftChoiceWinning" IS 'Key(3); C# bool';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchySquareInfo"."RightChoiceWinning" IS 'Key(4); C# bool';
COMMENT ON COLUMN protocol_data."Dungeon2HierarchySquareInfo"."HierarchyArtifacts" IS 'Key(5); C# List<Dungeon2HierarchyArtifactInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2RentalCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "RentalCharacterCode" BIGINT,
    "Hp" BIGINT,
    "Sp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_da6141e232a7f255 ON protocol_data."Dungeon2RentalCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2RentalCharacterInfo"."RentalCharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2RentalCharacterInfo"."Hp" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2RentalCharacterInfo"."Sp" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."Dungeon2StackItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Count" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_8fab07468d305408 ON protocol_data."Dungeon2StackItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."Dungeon2StackItemInfo"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."Dungeon2StackItemInfo"."Count" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."DungeonApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_d606d003535ed9d2 ON protocol_data."DungeonApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."DungeonCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "SupportHierarchy" INTEGER,
    "SupportUserId" TEXT,
    "Hp" BIGINT,
    "Sp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3b074e8e5a1b57b9 ON protocol_data."DungeonCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DungeonCharacterInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."DungeonCharacterInfo"."SupportHierarchy" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."DungeonCharacterInfo"."SupportUserId" IS 'Key(2); C# string';
COMMENT ON COLUMN protocol_data."DungeonCharacterInfo"."Hp" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."DungeonCharacterInfo"."Sp" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."DungeonEnemyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Wave" INTEGER,
    "Index" INTEGER,
    "QuestCode" BIGINT,
    "EnemyCode" BIGINT,
    "Hp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_93487567ae657460 ON protocol_data."DungeonEnemyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DungeonEnemyInfo"."Wave" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."DungeonEnemyInfo"."Index" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."DungeonEnemyInfo"."QuestCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."DungeonEnemyInfo"."EnemyCode" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."DungeonEnemyInfo"."Hp" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."DungeonHierarchyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Hierarchy" INTEGER,
    "StartLevel" INTEGER,
    "IsPlaying" BOOLEAN,
    "IsFirstRewardObtained" SMALLINT,
    "ClearCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_1177c86b697140da ON protocol_data."DungeonHierarchyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DungeonHierarchyInfo"."Hierarchy" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."DungeonHierarchyInfo"."StartLevel" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."DungeonHierarchyInfo"."IsPlaying" IS 'Key(2); C# bool';
COMMENT ON COLUMN protocol_data."DungeonHierarchyInfo"."IsFirstRewardObtained" IS 'Key(3); C# byte';
COMMENT ON COLUMN protocol_data."DungeonHierarchyInfo"."ClearCount" IS 'Key(4); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."DungeonHierarchySquareInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "SquareIndex" INTEGER,
    "Position" INTEGER,
    "PlayStatus" JSONB,
    "ArtifactGroupCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_0a3dfe1b063cecb2 ON protocol_data."DungeonHierarchySquareInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DungeonHierarchySquareInfo"."SquareIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."DungeonHierarchySquareInfo"."Position" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."DungeonHierarchySquareInfo"."PlayStatus" IS 'Key(2); C# DungeonPlayStatus';
COMMENT ON COLUMN protocol_data."DungeonHierarchySquareInfo"."ArtifactGroupCode" IS 'Key(3); C# Nullable<long>';
CREATE TABLE IF NOT EXISTS protocol_data."DungeonRentalCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "RentalCharacterCode" BIGINT,
    "Hp" BIGINT,
    "Sp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_7d25ccb25918f83e ON protocol_data."DungeonRentalCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DungeonRentalCharacterInfo"."RentalCharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."DungeonRentalCharacterInfo"."Hp" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."DungeonRentalCharacterInfo"."Sp" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."DungeonStackItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Count" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9b20d6f557b27509 ON protocol_data."DungeonStackItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."DungeonStackItemInfo"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."DungeonStackItemInfo"."Count" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."EditSupportInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "MagicItems" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ade69cbf0f61a49d ON protocol_data."EditSupportInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EditSupportInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."EditSupportInfo"."MagicItems" IS 'Key(1); C# List<EditSupportMagicItemInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."EditSupportMagicItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "EquipSlot" INTEGER,
    "MagicItemCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_6c977dd5b4ecd594 ON protocol_data."EditSupportMagicItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EditSupportMagicItemInfo"."EquipSlot" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."EditSupportMagicItemInfo"."MagicItemCode" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."EquipmentInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "Slot" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b73b85cdf8154b1d ON protocol_data."EquipmentInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EquipmentInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."EquipmentInfo"."Slot" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."EventApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_2bc716c0805cf486 ON protocol_data."EventApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."EventBossInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildId" JSONB,
    "EventCode" BIGINT,
    "QuestCode" BIGINT,
    "BossDamages" JSONB,
    "CurrentDefeatCount" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_d417c43451092e77 ON protocol_data."EventBossInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EventBossInfo"."GuildId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."EventBossInfo"."EventCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."EventBossInfo"."QuestCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."EventBossInfo"."BossDamages" IS 'Key(3); C# List<BossDamageInfo>';
COMMENT ON COLUMN protocol_data."EventBossInfo"."CurrentDefeatCount" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."EventDamageRankingProfileInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserId" TEXT,
    "UserName" TEXT,
    "ProfileCharacterCode" BIGINT,
    "HonorCode" BIGINT,
    "ProfileCharacterRank" INTEGER,
    "ProfileCharacterRarity" INTEGER,
    "ProfileIllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_1582941b7cc20300 ON protocol_data."EventDamageRankingProfileInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EventDamageRankingProfileInfo"."UserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."EventDamageRankingProfileInfo"."UserName" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."EventDamageRankingProfileInfo"."ProfileCharacterCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."EventDamageRankingProfileInfo"."HonorCode" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."EventDamageRankingProfileInfo"."ProfileCharacterRank" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."EventDamageRankingProfileInfo"."ProfileCharacterRarity" IS 'Key(5); C# int';
COMMENT ON COLUMN protocol_data."EventDamageRankingProfileInfo"."ProfileIllustrationIndex" IS 'Key(6); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."EventDamageRankingRecordInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "LatestEventCode" BIGINT,
    "LatestRankPercent" REAL,
    "HighestEventCodeInHistory" BIGINT,
    "HighestRankPercentInHistory" REAL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_2963d84b63fa2343 ON protocol_data."EventDamageRankingRecordInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EventDamageRankingRecordInfo"."LatestEventCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."EventDamageRankingRecordInfo"."LatestRankPercent" IS 'Key(1); C# float';
COMMENT ON COLUMN protocol_data."EventDamageRankingRecordInfo"."HighestEventCodeInHistory" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."EventDamageRankingRecordInfo"."HighestRankPercentInHistory" IS 'Key(3); C# float';
CREATE TABLE IF NOT EXISTS protocol_data."EventGuildMemberRankInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "User" JSONB,
    "Rank" BIGINT,
    "Point" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_a435786c9db5966f ON protocol_data."EventGuildMemberRankInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EventGuildMemberRankInfo"."User" IS 'Key(0); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."EventGuildMemberRankInfo"."Rank" IS 'Key(1); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."EventGuildMemberRankInfo"."Point" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."EventQuestLogInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserName" TEXT,
    "EnemyIndex" INTEGER,
    "Damage" BIGINT,
    "ProcessedAt" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_058dd228ecae8365 ON protocol_data."EventQuestLogInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EventQuestLogInfo"."UserName" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."EventQuestLogInfo"."EnemyIndex" IS 'Key(1); C# Nullable<int>';
COMMENT ON COLUMN protocol_data."EventQuestLogInfo"."Damage" IS 'Key(2); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."EventQuestLogInfo"."ProcessedAt" IS 'Key(3); C# DateTime';
CREATE TABLE IF NOT EXISTS protocol_data."EventRankInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildId" JSONB,
    "EmblemCode" BIGINT,
    "GuildName" JSONB,
    "GuildMemberCount" INTEGER,
    "Point" BIGINT,
    "Rank" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_d0110cf5629e53c8 ON protocol_data."EventRankInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."EventRankInfo"."GuildId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."EventRankInfo"."EmblemCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."EventRankInfo"."GuildName" IS 'Key(2); C# GuildName';
COMMENT ON COLUMN protocol_data."EventRankInfo"."GuildMemberCount" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."EventRankInfo"."Point" IS 'Key(4); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."EventRankInfo"."Rank" IS 'Key(5); C# Nullable<long>';
CREATE TABLE IF NOT EXISTS protocol_data."GardenBuildingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GardenBuildingCode" BIGINT,
    "Level" INTEGER,
    "WorkerCount" INTEGER,
    "ReceivedAt" JSONB,
    "RoomUnlocked" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_12877a6d67626fa8 ON protocol_data."GardenBuildingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GardenBuildingInfo"."GardenBuildingCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GardenBuildingInfo"."Level" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."GardenBuildingInfo"."WorkerCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."GardenBuildingInfo"."ReceivedAt" IS 'Key(3); C# Nullable<DateTime>';
COMMENT ON COLUMN protocol_data."GardenBuildingInfo"."RoomUnlocked" IS 'Key(4); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."GardenInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "HoldingWorkerCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ddb3c35b781899f6 ON protocol_data."GardenInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GardenInfo"."HoldingWorkerCount" IS 'Key(0); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."GardenProductItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "BuildingCode" BIGINT,
    "ItemBehaviourType" JSONB,
    "Type" JSONB,
    "ItemCode" BIGINT,
    "Count" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e16de53d6e2130fb ON protocol_data."GardenProductItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GardenProductItemInfo"."BuildingCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GardenProductItemInfo"."ItemBehaviourType" IS 'Key(1); C# ItemBehaviourType';
COMMENT ON COLUMN protocol_data."GardenProductItemInfo"."Type" IS 'Key(2); C# InventoryType';
COMMENT ON COLUMN protocol_data."GardenProductItemInfo"."ItemCode" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."GardenProductItemInfo"."Count" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."GardenSearchInventoryInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GardenBuildingCode" BIGINT,
    "SearchInventoryType" JSONB,
    "SearchInventoryCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_8fa033416dd16770 ON protocol_data."GardenSearchInventoryInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GardenSearchInventoryInfo"."GardenBuildingCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GardenSearchInventoryInfo"."SearchInventoryType" IS 'Key(1); C# InventoryType';
COMMENT ON COLUMN protocol_data."GardenSearchInventoryInfo"."SearchInventoryCode" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."GuildApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_16245fa9bd7cc0ff ON protocol_data."GuildApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ba423a6ed1f312f3 ON protocol_data."GuildBattleApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleBattleStatusInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DefenseUserId" TEXT,
    "OffenseGuildId" TEXT,
    "Status" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_340a0da6ae4c6b07 ON protocol_data."GuildBattleBattleStatusInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleBattleStatusInfo"."DefenseUserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleBattleStatusInfo"."OffenseGuildId" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleBattleStatusInfo"."Status" IS 'Key(2); C# GuildBattleStatus';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleBossInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildId" JSONB,
    "GuildBattleCode" BIGINT,
    "GuildBattleBossCode" BIGINT,
    "BattleStartedAt" JSONB,
    "LoopCount" INTEGER,
    "BossDamages" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_1d30e9abd3f05f04 ON protocol_data."GuildBattleBossInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleBossInfo"."GuildId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildBattleBossInfo"."GuildBattleCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleBossInfo"."GuildBattleBossCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleBossInfo"."BattleStartedAt" IS 'Key(3); C# DateTime';
COMMENT ON COLUMN protocol_data."GuildBattleBossInfo"."LoopCount" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."GuildBattleBossInfo"."BossDamages" IS 'Key(5); C# List<BossDamageInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleGuildRankingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildBattleCode" BIGINT,
    "GuildId" JSONB,
    "Rank" BIGINT,
    "Score" BIGINT,
    "EmblemCode" BIGINT,
    "GuildName" JSONB,
    "GuildMemberCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_bfef446090362c70 ON protocol_data."GuildBattleGuildRankingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleGuildRankingInfo"."GuildBattleCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleGuildRankingInfo"."GuildId" IS 'Key(1); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildBattleGuildRankingInfo"."Rank" IS 'Key(2); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleGuildRankingInfo"."Score" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleGuildRankingInfo"."EmblemCode" IS 'Key(4); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleGuildRankingInfo"."GuildName" IS 'Key(5); C# GuildName';
COMMENT ON COLUMN protocol_data."GuildBattleGuildRankingInfo"."GuildMemberCount" IS 'Key(6); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "IsEntry" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ea908b12a5f93c6e ON protocol_data."GuildBattleInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleInfo"."IsEntry" IS 'Key(0); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleLogInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "LogId" JSONB,
    "UserId" TEXT,
    "UserName" TEXT,
    "DefenseUserName" TEXT,
    "EnemyCode" BIGINT,
    "QuestCode" BIGINT,
    "ItemCode" BIGINT,
    "ItemCount" INTEGER,
    "BattleResult" INTEGER,
    "Damage" BIGINT,
    "ProcessedAt" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b22b16e52202704b ON protocol_data."GuildBattleLogInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."LogId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."UserId" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."UserName" IS 'Key(2); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."DefenseUserName" IS 'Key(3); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."EnemyCode" IS 'Key(4); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."QuestCode" IS 'Key(5); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."ItemCode" IS 'Key(6); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."ItemCount" IS 'Key(7); C# Nullable<int>';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."BattleResult" IS 'Key(8); C# Nullable<int>';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."Damage" IS 'Key(9); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleLogInfo"."ProcessedAt" IS 'Key(10); C# DateTime';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleQuestInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildBattleBossCode" BIGINT,
    "QuestCode" BIGINT,
    "LoopCount" INTEGER,
    "BossHpInfos" JSONB,
    "LockStatus" JSONB,
    "GuildBattleItemStackCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_6f3fe93608ae8e03 ON protocol_data."GuildBattleQuestInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleQuestInfo"."GuildBattleBossCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleQuestInfo"."QuestCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleQuestInfo"."LoopCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."GuildBattleQuestInfo"."BossHpInfos" IS 'Key(3); C# List<BossHpInfo>';
COMMENT ON COLUMN protocol_data."GuildBattleQuestInfo"."LockStatus" IS 'Key(4); C# LockStatus';
COMMENT ON COLUMN protocol_data."GuildBattleQuestInfo"."GuildBattleItemStackCount" IS 'Key(5); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleResultInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Day" INTEGER,
    "TargetGuildId" JSONB,
    "TotalScore" BIGINT,
    "TotalBuffWinCount" INTEGER,
    "BattleResult" INTEGER,
    "OpponentEmblemCode" BIGINT,
    "OpponentGuildName" JSONB,
    "OpponentTotalScore" BIGINT,
    "MyScore" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_af38ccc0178be9d4 ON protocol_data."GuildBattleResultInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."Day" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."TargetGuildId" IS 'Key(1); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."TotalScore" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."TotalBuffWinCount" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."BattleResult" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."OpponentEmblemCode" IS 'Key(5); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."OpponentGuildName" IS 'Key(6); C# GuildName';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."OpponentTotalScore" IS 'Key(7); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleResultInfo"."MyScore" IS 'Key(8); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleShareRewardInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "QuestCode" BIGINT,
    "LoopCount" INTEGER,
    "Presents" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3ef061f8e41cd506 ON protocol_data."GuildBattleShareRewardInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleShareRewardInfo"."QuestCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleShareRewardInfo"."LoopCount" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."GuildBattleShareRewardInfo"."Presents" IS 'Key(2); C# List<PresentInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleTargetMemberInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Score" BIGINT,
    "User" JSONB,
    "PartyInfo" JSONB,
    "Permission" JSONB,
    "SkillTreeInfo" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_d2b280521c70d7d1 ON protocol_data."GuildBattleTargetMemberInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleTargetMemberInfo"."Score" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleTargetMemberInfo"."User" IS 'Key(1); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."GuildBattleTargetMemberInfo"."PartyInfo" IS 'Key(2); C# ArenaPartyInfo';
COMMENT ON COLUMN protocol_data."GuildBattleTargetMemberInfo"."Permission" IS 'Key(3); C# GuildMemberPermission';
COMMENT ON COLUMN protocol_data."GuildBattleTargetMemberInfo"."SkillTreeInfo" IS 'Key(4); C# SkillTreeInfo';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleUserDayRankingGuildMemberInfos" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CurrentUserInfo" JSONB,
    "GuildMemberInfos" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_4d54d5b7ef8b119a ON protocol_data."GuildBattleUserDayRankingGuildMemberInfos" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingGuildMemberInfos"."CurrentUserInfo" IS 'Key(0); C# GuildBattleUserDayRankingInfo';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingGuildMemberInfos"."GuildMemberInfos" IS 'Key(1); C# List<GuildBattleUserDayRankingInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleUserDayRankingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildBattleCode" BIGINT,
    "GuildId" JSONB,
    "UserId" TEXT,
    "Rank" BIGINT,
    "Score" BIGINT,
    "UserName" TEXT,
    "ProfileCharacterCode" BIGINT,
    "HonorCode" BIGINT,
    "ProfileIllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_67ba221dfd84bc00 ON protocol_data."GuildBattleUserDayRankingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."GuildBattleCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."GuildId" IS 'Key(1); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."UserId" IS 'Key(2); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."Rank" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."Score" IS 'Key(4); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."UserName" IS 'Key(5); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."ProfileCharacterCode" IS 'Key(6); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."HonorCode" IS 'Key(7); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleUserDayRankingInfo"."ProfileIllustrationIndex" IS 'Key(8); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleUserTotalRankingGuildMemberInfos" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CurrentInfo" JSONB,
    "GuildMemberInfos" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_8c9f1ac6e05be7a7 ON protocol_data."GuildBattleUserTotalRankingGuildMemberInfos" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingGuildMemberInfos"."CurrentInfo" IS 'Key(0); C# GuildBattleUserTotalRankingInfo';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingGuildMemberInfos"."GuildMemberInfos" IS 'Key(1); C# List<GuildBattleUserTotalRankingInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."GuildBattleUserTotalRankingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildBattleCode" BIGINT,
    "GuildId" JSONB,
    "UserId" TEXT,
    "TotalScore" BIGINT,
    "Rank" BIGINT,
    "UserName" TEXT,
    "ProfileCharacterCode" BIGINT,
    "HonorCode" BIGINT,
    "ProfileIllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_64bff35d4a6fdb04 ON protocol_data."GuildBattleUserTotalRankingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."GuildBattleCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."GuildId" IS 'Key(1); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."UserId" IS 'Key(2); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."TotalScore" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."Rank" IS 'Key(4); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."UserName" IS 'Key(5); C# string';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."ProfileCharacterCode" IS 'Key(6); C# long';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."HonorCode" IS 'Key(7); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildBattleUserTotalRankingInfo"."ProfileIllustrationIndex" IS 'Key(8); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."GuildButtleRankingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Ranking" INTEGER,
    "GuildRanking" INTEGER,
    "GuildResultWin" INTEGER,
    "GuildResultLose" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_bac1398420c76912 ON protocol_data."GuildButtleRankingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildButtleRankingInfo"."Ranking" IS 'Key(0); C# Nullable<int>';
COMMENT ON COLUMN protocol_data."GuildButtleRankingInfo"."GuildRanking" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."GuildButtleRankingInfo"."GuildResultWin" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."GuildButtleRankingInfo"."GuildResultLose" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."GuildHistoryInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "HistoryId" JSONB,
    "User" JSONB,
    "Category" JSONB,
    "Value" BIGINT,
    "HistoryAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ad8fecdf4edb92ee ON protocol_data."GuildHistoryInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildHistoryInfo"."HistoryId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildHistoryInfo"."User" IS 'Key(1); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."GuildHistoryInfo"."Category" IS 'Key(2); C# GuildHistoryCategory';
COMMENT ON COLUMN protocol_data."GuildHistoryInfo"."Value" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."GuildHistoryInfo"."HistoryAt" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."GuildInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildId" JSONB,
    "EmblemCode" BIGINT,
    "Name" JSONB,
    "Description" TEXT,
    "Comment" TEXT,
    "MemberCount" INTEGER,
    "ChatFrequency" JSONB,
    "PlayStyle" JSONB,
    "AdmissionType" JSONB,
    "PermissionPolicy" JSONB,
    "BattleTimeRange" JSONB,
    "BattleRank" INTEGER,
    "GuildMembers" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_f9d678d3ab43310a ON protocol_data."GuildInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildInfo"."GuildId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildInfo"."EmblemCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."GuildInfo"."Name" IS 'Key(2); C# GuildName';
COMMENT ON COLUMN protocol_data."GuildInfo"."Description" IS 'Key(3); C# string';
COMMENT ON COLUMN protocol_data."GuildInfo"."Comment" IS 'Key(4); C# string';
COMMENT ON COLUMN protocol_data."GuildInfo"."MemberCount" IS 'Key(5); C# int';
COMMENT ON COLUMN protocol_data."GuildInfo"."ChatFrequency" IS 'Key(6); C# GuildChatFrequency';
COMMENT ON COLUMN protocol_data."GuildInfo"."PlayStyle" IS 'Key(7); C# GuildPlayStyle';
COMMENT ON COLUMN protocol_data."GuildInfo"."AdmissionType" IS 'Key(8); C# GuildAdmissionType';
COMMENT ON COLUMN protocol_data."GuildInfo"."PermissionPolicy" IS 'Key(9); C# GuildPermissionPolicy';
COMMENT ON COLUMN protocol_data."GuildInfo"."BattleTimeRange" IS 'Key(10); C# GuildBattleTimeRange';
COMMENT ON COLUMN protocol_data."GuildInfo"."BattleRank" IS 'Key(11); C# int';
COMMENT ON COLUMN protocol_data."GuildInfo"."GuildMembers" IS 'Key(12); C# List<GuildMemberInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."GuildMemberInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "GuildId" JSONB,
    "User" JSONB,
    "Permission" JSONB,
    "AdmissionState" JSONB,
    "EntryGuildBattleCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_27ffce04db97a11c ON protocol_data."GuildMemberInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildMemberInfo"."GuildId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."GuildMemberInfo"."User" IS 'Key(1); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."GuildMemberInfo"."Permission" IS 'Key(2); C# GuildMemberPermission';
COMMENT ON COLUMN protocol_data."GuildMemberInfo"."AdmissionState" IS 'Key(3); C# GuildMemberAdmissionState';
COMMENT ON COLUMN protocol_data."GuildMemberInfo"."EntryGuildBattleCode" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."GuildName" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Value" TEXT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_45499d0fb30cc9c2 ON protocol_data."GuildName" (owner_user_id);
COMMENT ON COLUMN protocol_data."GuildName"."Value" IS 'Key(0); C# string';
CREATE TABLE IF NOT EXISTS protocol_data."HomeCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "HomeCharacterCode" BIGINT,
    "ClosenessLevel" INTEGER,
    "ClosenessExp" BIGINT,
    "AvailableQuizzes" JSONB,
    "HomeCharacterCostumeCodes" JSONB,
    "IsRandomCostume" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_08ebab97a6278d41 ON protocol_data."HomeCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."HomeCharacterInfo"."HomeCharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."HomeCharacterInfo"."ClosenessLevel" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."HomeCharacterInfo"."ClosenessExp" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."HomeCharacterInfo"."AvailableQuizzes" IS 'Key(3); C# List<long>';
COMMENT ON COLUMN protocol_data."HomeCharacterInfo"."HomeCharacterCostumeCodes" IS 'Key(4); C# List<long>';
COMMENT ON COLUMN protocol_data."HomeCharacterInfo"."IsRandomCostume" IS 'Key(5); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."HomeInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Situations" JSONB,
    "CharacterCostumeCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_bf0cec45af1ae1c1 ON protocol_data."HomeInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."HomeInfo"."Situations" IS 'Key(0); C# List<HomeSituationInfo>';
COMMENT ON COLUMN protocol_data."HomeInfo"."CharacterCostumeCode" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."HomeSituationInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "SituationCode" BIGINT,
    "EventCodes" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_bf4394405299e5d9 ON protocol_data."HomeSituationInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."HomeSituationInfo"."SituationCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."HomeSituationInfo"."EventCodes" IS 'Key(1); C# List<long>';
CREATE TABLE IF NOT EXISTS protocol_data."HonorInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "HonorCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e1a5b1425fe5ced7 ON protocol_data."HonorInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."HonorInfo"."HonorCode" IS 'Key(0); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."InventoryUpdateInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Characters" JSONB,
    "MagicItems" JSONB,
    "StackItems" JSONB,
    "Honors" JSONB,
    "ShopPassInfos" JSONB,
    "Stamina" JSONB,
    "SomeItemsAreSendToPresentBox" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_42db5708554e4985 ON protocol_data."InventoryUpdateInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."InventoryUpdateInfo"."Characters" IS 'Key(0); C# List<CharacterInfo>';
COMMENT ON COLUMN protocol_data."InventoryUpdateInfo"."MagicItems" IS 'Key(1); C# List<MagicItemInfo>';
COMMENT ON COLUMN protocol_data."InventoryUpdateInfo"."StackItems" IS 'Key(2); C# List<StackItemInfo>';
COMMENT ON COLUMN protocol_data."InventoryUpdateInfo"."Honors" IS 'Key(3); C# List<HonorInfo>';
COMMENT ON COLUMN protocol_data."InventoryUpdateInfo"."ShopPassInfos" IS 'Key(4); C# List<ShopPassInfo>';
COMMENT ON COLUMN protocol_data."InventoryUpdateInfo"."Stamina" IS 'Key(5); C# Stamina';
COMMENT ON COLUMN protocol_data."InventoryUpdateInfo"."SomeItemsAreSendToPresentBox" IS 'Key(6); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."InviteAccumulateInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Count" BIGINT,
    "CountUpAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_948eee5340153e06 ON protocol_data."InviteAccumulateInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."InviteAccumulateInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."InviteAccumulateInfo"."Count" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."InviteAccumulateInfo"."CountUpAt" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."InviteApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_6f42ddd72db982f8 ON protocol_data."InviteApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."InviteInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "InviteId" TEXT,
    "UnlockedAt" JSONB,
    "Used" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_48030640126e4bee ON protocol_data."InviteInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."InviteInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."InviteInfo"."InviteId" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."InviteInfo"."UnlockedAt" IS 'Key(2); C# Nullable<DateTime>';
COMMENT ON COLUMN protocol_data."InviteInfo"."Used" IS 'Key(3); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."LoginBonusInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Index" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_00268f394c359a78 ON protocol_data."LoginBonusInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LoginBonusInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LoginBonusInfo"."Index" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9475306900cb4643 ON protocol_data."LotteryApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."LotteryButtonInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ButtonIndex" INTEGER,
    "RemainCount" INTEGER,
    "TotalCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_acd717e66c3d7617 ON protocol_data."LotteryButtonInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryButtonInfo"."ButtonIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."LotteryButtonInfo"."RemainCount" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."LotteryButtonInfo"."TotalCount" IS 'Key(2); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryCharacterWinningChanceInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "Rarity" INTEGER,
    "WinningChance" JSONB,
    "IsPickUp" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_405fffa5b13d9b68 ON protocol_data."LotteryCharacterWinningChanceInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryCharacterWinningChanceInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotteryCharacterWinningChanceInfo"."Rarity" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."LotteryCharacterWinningChanceInfo"."WinningChance" IS 'Key(2); C# Decimal';
COMMENT ON COLUMN protocol_data."LotteryCharacterWinningChanceInfo"."IsPickUp" IS 'Key(3); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryDisplayInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "LotteryCode" BIGINT,
    "ButtonInfos" JSONB,
    "ShowPriority" BIGINT,
    "ExpiredAt" JSONB,
    "LotterySelectCharacters" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_364dc3d2b78d66ab ON protocol_data."LotteryDisplayInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryDisplayInfo"."LotteryCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotteryDisplayInfo"."ButtonInfos" IS 'Key(1); C# List<LotteryButtonInfo>';
COMMENT ON COLUMN protocol_data."LotteryDisplayInfo"."ShowPriority" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."LotteryDisplayInfo"."ExpiredAt" IS 'Key(3); C# Nullable<DateTime>';
COMMENT ON COLUMN protocol_data."LotteryDisplayInfo"."LotterySelectCharacters" IS 'Key(4); C# List<long>';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryHistoryDetailInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "CrystalCount" INTEGER,
    "FragmentCount" INTEGER,
    "LimitBreakItemCount" INTEGER,
    "LotteryPickupAddItems" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_cfea8a5574801917 ON protocol_data."LotteryHistoryDetailInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryHistoryDetailInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotteryHistoryDetailInfo"."CrystalCount" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."LotteryHistoryDetailInfo"."FragmentCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."LotteryHistoryDetailInfo"."LimitBreakItemCount" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."LotteryHistoryDetailInfo"."LotteryPickupAddItems" IS 'Key(4); C# List<LotteryPickupAddItemInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryHistoryInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "LotteryCode" BIGINT,
    "ExecAt" BIGINT,
    "ConsumeItemCode" BIGINT,
    "ConsumeCount" INTEGER,
    "LotteryHistoryDetails" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_7acb083acf187fbd ON protocol_data."LotteryHistoryInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryHistoryInfo"."LotteryCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotteryHistoryInfo"."ExecAt" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."LotteryHistoryInfo"."ConsumeItemCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."LotteryHistoryInfo"."ConsumeCount" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."LotteryHistoryInfo"."LotteryHistoryDetails" IS 'Key(4); C# List<LotteryHistoryDetailInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryPickupAddItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Count" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_992926883905b503 ON protocol_data."LotteryPickupAddItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryPickupAddItemInfo"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotteryPickupAddItemInfo"."Count" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryResultCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "IsNew" BOOLEAN,
    "CrystalCount" INTEGER,
    "FragmentCount" INTEGER,
    "LimitBreakItemCount" INTEGER,
    "LotteryPickupAddItems" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_c3a70a60869172c0 ON protocol_data."LotteryResultCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryResultCharacterInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotteryResultCharacterInfo"."IsNew" IS 'Key(1); C# bool';
COMMENT ON COLUMN protocol_data."LotteryResultCharacterInfo"."CrystalCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."LotteryResultCharacterInfo"."FragmentCount" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."LotteryResultCharacterInfo"."LimitBreakItemCount" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."LotteryResultCharacterInfo"."LotteryPickupAddItems" IS 'Key(5); C# List<LotteryPickupAddItemInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."LotterySelectCharacter" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "LotteryCode" BIGINT,
    "SelectCharacters" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_65515ca6280e8801 ON protocol_data."LotterySelectCharacter" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotterySelectCharacter"."LotteryCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotterySelectCharacter"."SelectCharacters" IS 'Key(1); C# List<long>';
CREATE TABLE IF NOT EXISTS protocol_data."LotterySimulationCharacterResult" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "CharacterName" TEXT,
    "Rarity" INTEGER,
    "MasterRate" JSONB,
    "ResultRate" JSONB,
    "MasterCount" JSONB,
    "ResultCount" INTEGER,
    "Diff" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3c5d25aee0597ed9 ON protocol_data."LotterySimulationCharacterResult" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."CharacterName" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."Rarity" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."MasterRate" IS 'Key(3); C# Decimal';
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."ResultRate" IS 'Key(4); C# Decimal';
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."MasterCount" IS 'Key(5); C# Decimal';
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."ResultCount" IS 'Key(6); C# int';
COMMENT ON COLUMN protocol_data."LotterySimulationCharacterResult"."Diff" IS 'Key(7); C# Decimal';
CREATE TABLE IF NOT EXISTS protocol_data."LotterySimulationRarityResult" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Rarity" INTEGER,
    "RarityMasterRate" JSONB,
    "RarityResultRate" JSONB,
    "RarityMasterCount" JSONB,
    "RarityResultCount" INTEGER,
    "RarityDiff" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_49cecf38fe854163 ON protocol_data."LotterySimulationRarityResult" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotterySimulationRarityResult"."Rarity" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."LotterySimulationRarityResult"."RarityMasterRate" IS 'Key(1); C# Decimal';
COMMENT ON COLUMN protocol_data."LotterySimulationRarityResult"."RarityResultRate" IS 'Key(2); C# Decimal';
COMMENT ON COLUMN protocol_data."LotterySimulationRarityResult"."RarityMasterCount" IS 'Key(3); C# Decimal';
COMMENT ON COLUMN protocol_data."LotterySimulationRarityResult"."RarityResultCount" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."LotterySimulationRarityResult"."RarityDiff" IS 'Key(5); C# Decimal';
CREATE TABLE IF NOT EXISTS protocol_data."LotterySimulationResult" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Index" INTEGER,
    "Rarity" INTEGER,
    "CharacterCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_4900783d84ca387d ON protocol_data."LotterySimulationResult" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotterySimulationResult"."Index" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."LotterySimulationResult"."Rarity" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."LotterySimulationResult"."CharacterCode" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."LotterySimulationResultGroup" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "RarityResults" JSONB,
    "CharacterResults" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_a6949e0f664e24fc ON protocol_data."LotterySimulationResultGroup" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotterySimulationResultGroup"."RarityResults" IS 'Key(0); C# List<LotterySimulationRarityResult>';
COMMENT ON COLUMN protocol_data."LotterySimulationResultGroup"."CharacterResults" IS 'Key(1); C# List<LotterySimulationCharacterResult>';
CREATE TABLE IF NOT EXISTS protocol_data."LotteryWinningChanceInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "RarityChance" JSONB,
    "LotteryCharacterWinningChances" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_739e83d37c509ffb ON protocol_data."LotteryWinningChanceInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."LotteryWinningChanceInfo"."RarityChance" IS 'Key(0); C# List<Decimal>';
COMMENT ON COLUMN protocol_data."LotteryWinningChanceInfo"."LotteryCharacterWinningChances" IS 'Key(1); C# List<LotteryCharacterWinningChanceInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemCreateResult" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Rarity" JSONB,
    "Name" TEXT,
    "Count" INTEGER,
    "SettingRate" JSONB,
    "AppearRate" JSONB,
    "ExpectedValue" JSONB,
    "Difference" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_cf0b7f01efc3ff9a ON protocol_data."MagicItemCreateResult" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."Rarity" IS 'Key(1); C# MagicItemRarity';
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."Name" IS 'Key(2); C# string';
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."Count" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."SettingRate" IS 'Key(4); C# Decimal';
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."AppearRate" IS 'Key(5); C# Decimal';
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."ExpectedValue" IS 'Key(6); C# Decimal';
COMMENT ON COLUMN protocol_data."MagicItemCreateResult"."Difference" IS 'Key(7); C# Decimal';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemCreateResultInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "InventoryType" JSONB,
    "Code" BIGINT,
    "Count" BIGINT,
    "Rarity" JSONB,
    "IsNew" BOOLEAN,
    "DuplicatedMagicItemCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_1bc36aa3ef487c04 ON protocol_data."MagicItemCreateResultInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemCreateResultInfo"."InventoryType" IS 'Key(0); C# InventoryType';
COMMENT ON COLUMN protocol_data."MagicItemCreateResultInfo"."Code" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."MagicItemCreateResultInfo"."Count" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."MagicItemCreateResultInfo"."Rarity" IS 'Key(3); C# MagicItemRarity';
COMMENT ON COLUMN protocol_data."MagicItemCreateResultInfo"."IsNew" IS 'Key(4); C# bool';
COMMENT ON COLUMN protocol_data."MagicItemCreateResultInfo"."DuplicatedMagicItemCode" IS 'Key(5); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemEffectInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MagicItemCode" BIGINT,
    "EffectSlot" INTEGER,
    "EffectCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_0810b22dd3dfaf4c ON protocol_data."MagicItemEffectInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemEffectInfo"."MagicItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."MagicItemEffectInfo"."EffectSlot" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."MagicItemEffectInfo"."EffectCode" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemEffectLotteryInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ResultIndex" INTEGER,
    "MagicItemCode" BIGINT,
    "EffectSlot" INTEGER,
    "EffectCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9cf1e6897eab8312 ON protocol_data."MagicItemEffectLotteryInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemEffectLotteryInfo"."ResultIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotteryInfo"."MagicItemCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotteryInfo"."EffectSlot" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotteryInfo"."EffectCode" IS 'Key(3); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemEffectLotterySimulationViewMaster" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Description" TEXT,
    "Rarity" JSONB,
    "SettingProbability" JSONB,
    "AppearProbability" JSONB,
    "ExpectedValue" JSONB,
    "AppearCount" INTEGER,
    "Difference" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_17d397f2c89daae0 ON protocol_data."MagicItemEffectLotterySimulationViewMaster" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."Description" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."Rarity" IS 'Key(2); C# MagicItemRarity';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."SettingProbability" IS 'Key(3); C# Decimal';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."AppearProbability" IS 'Key(4); C# Decimal';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."ExpectedValue" IS 'Key(5); C# Decimal';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."AppearCount" IS 'Key(6); C# int';
COMMENT ON COLUMN protocol_data."MagicItemEffectLotterySimulationViewMaster"."Difference" IS 'Key(7); C# Decimal';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemEffectResult" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ResultIndex" INTEGER,
    "EffectCodes" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_6c6ebc85f504140c ON protocol_data."MagicItemEffectResult" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemEffectResult"."ResultIndex" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."MagicItemEffectResult"."EffectCodes" IS 'Key(1); C# List<long>';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemEquipmentInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "EquipSlot" INTEGER,
    "MagicItem" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_43946a77c4165d39 ON protocol_data."MagicItemEquipmentInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemEquipmentInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."MagicItemEquipmentInfo"."EquipSlot" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."MagicItemEquipmentInfo"."MagicItem" IS 'Key(2); C# MagicItemInfo';
CREATE TABLE IF NOT EXISTS protocol_data."MagicItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "Level" INTEGER,
    "MagicItemEffects" JSONB,
    "CreatedAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_75057a4e10802c86 ON protocol_data."MagicItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MagicItemInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."MagicItemInfo"."Level" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."MagicItemInfo"."MagicItemEffects" IS 'Key(2); C# List<MagicItemEffectInfo>';
COMMENT ON COLUMN protocol_data."MagicItemInfo"."CreatedAt" IS 'Key(3); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."MinesweeperGameInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MiniGameCode" BIGINT,
    "StageNumber" INTEGER,
    "HighestScore" BIGINT,
    "ClearCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_992ba8c7b92e7879 ON protocol_data."MinesweeperGameInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MinesweeperGameInfo"."MiniGameCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."MinesweeperGameInfo"."StageNumber" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."MinesweeperGameInfo"."HighestScore" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."MinesweeperGameInfo"."ClearCount" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."MiniGameApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_04a989589a25fa34 ON protocol_data."MiniGameApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."MissionApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_7387c356052973d2 ON protocol_data."MissionApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."MissionInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MissionCode" BIGINT,
    "Status" JSONB,
    "Count" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ae2e36f9642bb8ba ON protocol_data."MissionInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MissionInfo"."MissionCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."MissionInfo"."Status" IS 'Key(1); C# MissionStatus';
COMMENT ON COLUMN protocol_data."MissionInfo"."Count" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."MissionRewardReceivedInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MissionCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_4c91b594a0684f7c ON protocol_data."MissionRewardReceivedInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."MissionRewardReceivedInfo"."MissionCode" IS 'Key(0); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."OpenBoxItemViewInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Count" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e4dfbd5b33e48423 ON protocol_data."OpenBoxItemViewInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."OpenBoxItemViewInfo"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."OpenBoxItemViewInfo"."Count" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."OpenChatRoomMemberCountInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "RoomName" TEXT,
    "Count" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_29d089b5a8a0211d ON protocol_data."OpenChatRoomMemberCountInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."OpenChatRoomMemberCountInfo"."RoomName" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."OpenChatRoomMemberCountInfo"."Count" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."PartyCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterInfo" JSONB,
    "SwitchableCharacterIndex" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_cf6313de5814f2b9 ON protocol_data."PartyCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."PartyCharacterInfo"."CharacterInfo" IS 'Key(0); C# CharacterInfo';
COMMENT ON COLUMN protocol_data."PartyCharacterInfo"."SwitchableCharacterIndex" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."PartyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Type" JSONB,
    "UserId" TEXT,
    "No" INTEGER,
    "Name" TEXT,
    "IsActive" BOOLEAN,
    "CharacterInfos" JSONB,
    "MagicItemEquipments" JSONB,
    "TotalPower" BIGINT,
    "RentalCharacterInfos" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_a21382391b7e1846 ON protocol_data."PartyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."PartyInfo"."Type" IS 'Key(0); C# PartyType';
COMMENT ON COLUMN protocol_data."PartyInfo"."UserId" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."PartyInfo"."No" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."PartyInfo"."Name" IS 'Key(3); C# string';
COMMENT ON COLUMN protocol_data."PartyInfo"."IsActive" IS 'Key(4); C# bool';
COMMENT ON COLUMN protocol_data."PartyInfo"."CharacterInfos" IS 'Key(5); C# List<PartyCharacterInfo>';
COMMENT ON COLUMN protocol_data."PartyInfo"."MagicItemEquipments" IS 'Key(6); C# List<MagicItemEquipmentInfo>';
COMMENT ON COLUMN protocol_data."PartyInfo"."TotalPower" IS 'Key(7); C# long';
COMMENT ON COLUMN protocol_data."PartyInfo"."RentalCharacterInfos" IS 'Key(8); C# List<RentalCharacterInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."PresentInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "PresentId" JSONB,
    "Title" TEXT,
    "InventoryType" JSONB,
    "InventoryCode" BIGINT,
    "Amount" INTEGER,
    "SenderIconCode" BIGINT,
    "ArrivedAt" BIGINT,
    "LimitDate" BIGINT,
    "ReceivedAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_38baa4aecaabb985 ON protocol_data."PresentInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."PresentInfo"."PresentId" IS 'Key(0); C# Ulid';
COMMENT ON COLUMN protocol_data."PresentInfo"."Title" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."PresentInfo"."InventoryType" IS 'Key(2); C# InventoryType';
COMMENT ON COLUMN protocol_data."PresentInfo"."InventoryCode" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."PresentInfo"."Amount" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."PresentInfo"."SenderIconCode" IS 'Key(5); C# long';
COMMENT ON COLUMN protocol_data."PresentInfo"."ArrivedAt" IS 'Key(6); C# long';
COMMENT ON COLUMN protocol_data."PresentInfo"."LimitDate" IS 'Key(7); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."PresentInfo"."ReceivedAt" IS 'Key(8); C# Nullable<long>';
CREATE TABLE IF NOT EXISTS protocol_data."PurchaseShopLineupInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ShopLineupCode" BIGINT,
    "Count" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_33108d0470f1ece5 ON protocol_data."PurchaseShopLineupInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."PurchaseShopLineupInfo"."ShopLineupCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."PurchaseShopLineupInfo"."Count" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."QuestApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9fd58f772191f084 ON protocol_data."QuestApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."QuestClearCountInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "QuestCode" BIGINT,
    "Count" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b1ab3c80ffa095bc ON protocol_data."QuestClearCountInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestClearCountInfo"."QuestCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."QuestClearCountInfo"."Count" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."QuestDropInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DropItems" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_abf6780793c11e24 ON protocol_data."QuestDropInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestDropInfo"."DropItems" IS 'Key(0); C# List<DropItemResultViewInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."QuestEventDamageRankingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DamageRankingScore" BIGINT,
    "RankPercent" REAL,
    "DamageToNextGrade" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ee93cedf5cca7925 ON protocol_data."QuestEventDamageRankingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestEventDamageRankingInfo"."DamageRankingScore" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."QuestEventDamageRankingInfo"."RankPercent" IS 'Key(1); C# Nullable<float>';
COMMENT ON COLUMN protocol_data."QuestEventDamageRankingInfo"."DamageToNextGrade" IS 'Key(2); C# Nullable<long>';
CREATE TABLE IF NOT EXISTS protocol_data."QuestGroupInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "QuestGroupCode" BIGINT,
    "ClearCount" INTEGER,
    "RemainChallengeCount" JSONB,
    "RemainRecoverChallengeCount" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_916876a3f2fd6acb ON protocol_data."QuestGroupInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestGroupInfo"."QuestGroupCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."QuestGroupInfo"."ClearCount" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."QuestGroupInfo"."RemainChallengeCount" IS 'Key(2); C# CountWithResetTime';
COMMENT ON COLUMN protocol_data."QuestGroupInfo"."RemainRecoverChallengeCount" IS 'Key(3); C# CountWithResetTime';
CREATE TABLE IF NOT EXISTS protocol_data."QuestInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "ClearCount" INTEGER,
    "StarCount" SMALLINT,
    "RemainChallengeCount" JSONB,
    "RemainRecoverChallengeCount" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_05abc206329e1cf6 ON protocol_data."QuestInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."QuestInfo"."ClearCount" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."QuestInfo"."StarCount" IS 'Key(2); C# byte';
COMMENT ON COLUMN protocol_data."QuestInfo"."RemainChallengeCount" IS 'Key(3); C# CountWithResetTime';
COMMENT ON COLUMN protocol_data."QuestInfo"."RemainRecoverChallengeCount" IS 'Key(4); C# CountWithResetTime';
CREATE TABLE IF NOT EXISTS protocol_data."QuestPartyCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "Health" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_76a92ddb49efa92d ON protocol_data."QuestPartyCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestPartyCharacterInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."QuestPartyCharacterInfo"."Health" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."QuestSkipInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DropInfo" JSONB,
    "Experience" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_0efd673e7090c994 ON protocol_data."QuestSkipInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestSkipInfo"."DropInfo" IS 'Key(0); C# QuestDropInfo';
COMMENT ON COLUMN protocol_data."QuestSkipInfo"."Experience" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."QuestStatusInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserId" TEXT,
    "QuestCode" BIGINT,
    "QuestSuspensionParty" JSONB,
    "QuestUniqueId" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_559e062415239484 ON protocol_data."QuestStatusInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestStatusInfo"."UserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."QuestStatusInfo"."QuestCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."QuestStatusInfo"."QuestSuspensionParty" IS 'Key(2); C# QuestSuspensionPartyInfo';
COMMENT ON COLUMN protocol_data."QuestStatusInfo"."QuestUniqueId" IS 'Key(3); C# Ulid';
CREATE TABLE IF NOT EXISTS protocol_data."QuestSuspensionCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "Hp" BIGINT,
    "Sp" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b2269a988bb1e0c3 ON protocol_data."QuestSuspensionCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestSuspensionCharacterInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."QuestSuspensionCharacterInfo"."Hp" IS 'Key(1); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."QuestSuspensionCharacterInfo"."Sp" IS 'Key(2); C# Nullable<long>';
CREATE TABLE IF NOT EXISTS protocol_data."QuestSuspensionPartyInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CurrentWaveCount" INTEGER,
    "SelfQuestSuspensionCharacters" JSONB,
    "Party" JSONB,
    "Support" JSONB,
    "SupportQuestSuspensionCharacter" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_5f69bc39caaef3c6 ON protocol_data."QuestSuspensionPartyInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuestSuspensionPartyInfo"."CurrentWaveCount" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."QuestSuspensionPartyInfo"."SelfQuestSuspensionCharacters" IS 'Key(1); C# List<QuestSuspensionCharacterInfo>';
COMMENT ON COLUMN protocol_data."QuestSuspensionPartyInfo"."Party" IS 'Key(2); C# PartyInfo';
COMMENT ON COLUMN protocol_data."QuestSuspensionPartyInfo"."Support" IS 'Key(3); C# SupportInfo';
COMMENT ON COLUMN protocol_data."QuestSuspensionPartyInfo"."SupportQuestSuspensionCharacter" IS 'Key(4); C# QuestSuspensionCharacterInfo';
CREATE TABLE IF NOT EXISTS protocol_data."QuizAnswerInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "QuizCode" BIGINT,
    "AnsweredOptions" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_94de10bc412a3a29 ON protocol_data."QuizAnswerInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."QuizAnswerInfo"."QuizCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."QuizAnswerInfo"."AnsweredOptions" IS 'Key(1); C# List<int>';
CREATE TABLE IF NOT EXISTS protocol_data."QuizApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ce9af0c05c5fa575 ON protocol_data."QuizApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."RentalCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "RentalCharacterCode" BIGINT,
    "SwitchableCharacterIndex" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b500d160d5140577 ON protocol_data."RentalCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."RentalCharacterInfo"."RentalCharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."RentalCharacterInfo"."SwitchableCharacterIndex" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."RewardInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Type" JSONB,
    "Code" BIGINT,
    "Count" BIGINT,
    "DisplayPriority" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_bb0efdfd61e489e8 ON protocol_data."RewardInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."RewardInfo"."Type" IS 'Key(0); C# InventoryType';
COMMENT ON COLUMN protocol_data."RewardInfo"."Code" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."RewardInfo"."Count" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."RewardInfo"."DisplayPriority" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."RhythmGameInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MiniGameCode" BIGINT,
    "Stage" INTEGER,
    "HighestScore" BIGINT,
    "ClearCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_91f422368ac403d1 ON protocol_data."RhythmGameInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."RhythmGameInfo"."MiniGameCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."RhythmGameInfo"."Stage" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."RhythmGameInfo"."HighestScore" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."RhythmGameInfo"."ClearCount" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."RhythmGameTapResultInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Great" INTEGER,
    "Good" INTEGER,
    "Bad" INTEGER,
    "Miss" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_f548dc3b95725ac0 ON protocol_data."RhythmGameTapResultInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."RhythmGameTapResultInfo"."Great" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."RhythmGameTapResultInfo"."Good" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."RhythmGameTapResultInfo"."Bad" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."RhythmGameTapResultInfo"."Miss" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."RunGameInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MiniGameCode" BIGINT,
    "Stage" INTEGER,
    "HighestScore" BIGINT,
    "ClearCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_7da9464e4b762b98 ON protocol_data."RunGameInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."RunGameInfo"."MiniGameCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."RunGameInfo"."Stage" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."RunGameInfo"."HighestScore" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."RunGameInfo"."ClearCount" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."ScorePointRewardInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Point" BIGINT,
    "StackItems" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_01eb9dcdf36791dd ON protocol_data."ScorePointRewardInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ScorePointRewardInfo"."Point" IS 'Key(0); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."ScorePointRewardInfo"."StackItems" IS 'Key(1); C# List<StackItemInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."SerialCodeApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9fbd639172300ef4 ON protocol_data."SerialCodeApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."ShopApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_55255d4ab8b09318 ON protocol_data."ShopApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."ShopDisplayInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ShopCode" BIGINT,
    "ShopLineupDisplays" JSONB,
    "LineupUpdatedCount" INTEGER,
    "ShopExpiredAt" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_8effcec57a9dcda6 ON protocol_data."ShopDisplayInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ShopDisplayInfo"."ShopCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ShopDisplayInfo"."ShopLineupDisplays" IS 'Key(1); C# List<ShopLineupDisplayInfo>';
COMMENT ON COLUMN protocol_data."ShopDisplayInfo"."LineupUpdatedCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."ShopDisplayInfo"."ShopExpiredAt" IS 'Key(3); C# Nullable<DateTime>';
CREATE TABLE IF NOT EXISTS protocol_data."ShopLineupDisplayInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ShopLineupCode" BIGINT,
    "ShopLineupLotteryCode" BIGINT,
    "PurchasedCount" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_58670345ead50915 ON protocol_data."ShopLineupDisplayInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ShopLineupDisplayInfo"."ShopLineupCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ShopLineupDisplayInfo"."ShopLineupLotteryCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."ShopLineupDisplayInfo"."PurchasedCount" IS 'Key(2); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."ShopPackageDisplayInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "PurchasedCount" JSONB,
    "ExpiredAt" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_f66c456b0cd8b7a2 ON protocol_data."ShopPackageDisplayInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ShopPackageDisplayInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ShopPackageDisplayInfo"."PurchasedCount" IS 'Key(1); C# CountWithResetTime';
COMMENT ON COLUMN protocol_data."ShopPackageDisplayInfo"."ExpiredAt" IS 'Key(2); C# Nullable<DateTime>';
CREATE TABLE IF NOT EXISTS protocol_data."ShopPassInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ShopPassCode" BIGINT,
    "EndAt" BIGINT,
    "NotifiedAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_6c5ec6ae5a036eb6 ON protocol_data."ShopPassInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ShopPassInfo"."ShopPassCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ShopPassInfo"."EndAt" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."ShopPassInfo"."NotifiedAt" IS 'Key(2); C# Nullable<long>';
CREATE TABLE IF NOT EXISTS protocol_data."ShopPaymentDisplayInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Code" BIGINT,
    "PurchasedCount" BIGINT,
    "ExpiredAt" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_88ee775a7a1bd773 ON protocol_data."ShopPaymentDisplayInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."ShopPaymentDisplayInfo"."Code" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."ShopPaymentDisplayInfo"."PurchasedCount" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."ShopPaymentDisplayInfo"."ExpiredAt" IS 'Key(2); C# Nullable<DateTime>';
CREATE TABLE IF NOT EXISTS protocol_data."SkillTreeFloorCompleteInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "FloorCode" BIGINT,
    "Level" SMALLINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_039bcff6f108848d ON protocol_data."SkillTreeFloorCompleteInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."SkillTreeFloorCompleteInfo"."FloorCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."SkillTreeFloorCompleteInfo"."Level" IS 'Key(1); C# byte';
CREATE TABLE IF NOT EXISTS protocol_data."SkillTreeInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "NodeInfos" JSONB,
    "FloorCompleteInfos" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_60f5e5227cb210dd ON protocol_data."SkillTreeInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."SkillTreeInfo"."NodeInfos" IS 'Key(0); C# List<SkillTreeNodeInfo>';
COMMENT ON COLUMN protocol_data."SkillTreeInfo"."FloorCompleteInfos" IS 'Key(1); C# List<SkillTreeFloorCompleteInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."SkillTreeNodeInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "NodeCode" BIGINT,
    "Level" SMALLINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ff47149642f13a62 ON protocol_data."SkillTreeNodeInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."SkillTreeNodeInfo"."NodeCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."SkillTreeNodeInfo"."Level" IS 'Key(1); C# byte';
CREATE TABLE IF NOT EXISTS protocol_data."StackItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "ItemCode" BIGINT,
    "Count" BIGINT,
    "RecoveredAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_ea3eea746ee7a319 ON protocol_data."StackItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."StackItemInfo"."ItemCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."StackItemInfo"."Count" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."StackItemInfo"."RecoveredAt" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."Stamina" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Value" BIGINT,
    "UpdatedAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_cc350ea3393968f7 ON protocol_data."Stamina" (owner_user_id);
COMMENT ON COLUMN protocol_data."Stamina"."Value" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."Stamina"."UpdatedAt" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."Stone" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Free" BIGINT,
    "Paid" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_6ffa6b8b1c9fa11c ON protocol_data."Stone" (owner_user_id);
COMMENT ON COLUMN protocol_data."Stone"."Free" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."Stone"."Paid" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."StoryInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "StoryCode" BIGINT,
    "StoryStatus" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_f47850accc3b86eb ON protocol_data."StoryInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."StoryInfo"."StoryCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."StoryInfo"."StoryStatus" IS 'Key(1); C# StoryStatus';
CREATE TABLE IF NOT EXISTS protocol_data."StoryRaidBossHpInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "StoryRaidBossCode" BIGINT,
    "HpRatePercent" REAL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_7f2aec8a4adb3b15 ON protocol_data."StoryRaidBossHpInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."StoryRaidBossHpInfo"."StoryRaidBossCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."StoryRaidBossHpInfo"."HpRatePercent" IS 'Key(1); C# float';
CREATE TABLE IF NOT EXISTS protocol_data."StoryRaidBossInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "StoryRaidCode" BIGINT,
    "StoryRaidBossCode" BIGINT,
    "ChallengingDifficulty" JSONB,
    "ChallengingRemainHp" BIGINT,
    "TotalDamage" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_068655272c4b1ccb ON protocol_data."StoryRaidBossInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."StoryRaidBossInfo"."StoryRaidCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."StoryRaidBossInfo"."StoryRaidBossCode" IS 'Key(1); C# long';
COMMENT ON COLUMN protocol_data."StoryRaidBossInfo"."ChallengingDifficulty" IS 'Key(2); C# Nullable<Difficulty>';
COMMENT ON COLUMN protocol_data."StoryRaidBossInfo"."ChallengingRemainHp" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."StoryRaidBossInfo"."TotalDamage" IS 'Key(4); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."StoryRaidResultInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "BossDamage" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_aeb397709fd0c544 ON protocol_data."StoryRaidResultInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."StoryRaidResultInfo"."BossDamage" IS 'Key(0); C# BossDamageInfo';
CREATE TABLE IF NOT EXISTS protocol_data."SubEventApiError" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_a9256894e16de0ba ON protocol_data."SubEventApiError" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."SupportInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserId" TEXT,
    "Attribute" JSONB,
    "Role" JSONB,
    "Character" JSONB,
    "MagicItemEquipments" JSONB,
    "SupportEquipmentSlots" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_67f337a0786337bd ON protocol_data."SupportInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."SupportInfo"."UserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."SupportInfo"."Attribute" IS 'Key(1); C# Attribute';
COMMENT ON COLUMN protocol_data."SupportInfo"."Role" IS 'Key(2); C# Role';
COMMENT ON COLUMN protocol_data."SupportInfo"."Character" IS 'Key(3); C# CharacterInfo';
COMMENT ON COLUMN protocol_data."SupportInfo"."MagicItemEquipments" IS 'Key(4); C# List<MagicItemEquipmentInfo>';
COMMENT ON COLUMN protocol_data."SupportInfo"."SupportEquipmentSlots" IS 'Key(5); C# List<int>';
CREATE TABLE IF NOT EXISTS protocol_data."SupportUserInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserId" TEXT,
    "Name" TEXT,
    "Level" INTEGER,
    "LastLoginAt" JSONB,
    "IsGuildMember" BOOLEAN,
    "IsFollow" BOOLEAN,
    "IsFollowed" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_761dc93c443b57de ON protocol_data."SupportUserInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."SupportUserInfo"."UserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."SupportUserInfo"."Name" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."SupportUserInfo"."Level" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."SupportUserInfo"."LastLoginAt" IS 'Key(3); C# DateTime';
COMMENT ON COLUMN protocol_data."SupportUserInfo"."IsGuildMember" IS 'Key(4); C# bool';
COMMENT ON COLUMN protocol_data."SupportUserInfo"."IsFollow" IS 'Key(5); C# bool';
COMMENT ON COLUMN protocol_data."SupportUserInfo"."IsFollowed" IS 'Key(6); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."TargetShootingInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "MiniGameCode" BIGINT,
    "HighestCombo" INTEGER,
    "HighestScore" BIGINT,
    "TargetShootingObjects" JSONB,
    "TargetShootingSetBonuses" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_a42fd93760666926 ON protocol_data."TargetShootingInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TargetShootingInfo"."MiniGameCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."TargetShootingInfo"."HighestCombo" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."TargetShootingInfo"."HighestScore" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."TargetShootingInfo"."TargetShootingObjects" IS 'Key(3); C# List<TargetShootingObjectInfo>';
COMMENT ON COLUMN protocol_data."TargetShootingInfo"."TargetShootingSetBonuses" IS 'Key(4); C# List<TargetShootingSetBonusInfo>';
CREATE TABLE IF NOT EXISTS protocol_data."TargetShootingObjectInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "TargetShootingObjectCode" BIGINT,
    "Count" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_62f70edafcd5ba21 ON protocol_data."TargetShootingObjectInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TargetShootingObjectInfo"."TargetShootingObjectCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."TargetShootingObjectInfo"."Count" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."TargetShootingSetBonusInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "TargetShootingSetBonusCode" BIGINT,
    "Count" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_9b09fe285c7864cd ON protocol_data."TargetShootingSetBonusInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TargetShootingSetBonusInfo"."TargetShootingSetBonusCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."TargetShootingSetBonusInfo"."Count" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."TowerCharacterInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "UsedRoundIndex" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_91f4a17517e3b904 ON protocol_data."TowerCharacterInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TowerCharacterInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."TowerCharacterInfo"."UsedRoundIndex" IS 'Key(1); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."TowerFloorClearRateInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Floor" INTEGER,
    "ClearRate" TEXT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b3f1a865f4a46c0a ON protocol_data."TowerFloorClearRateInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TowerFloorClearRateInfo"."Floor" IS 'Key(0); C# int';
COMMENT ON COLUMN protocol_data."TowerFloorClearRateInfo"."ClearRate" IS 'Key(1); C# string';
CREATE TABLE IF NOT EXISTS protocol_data."TowerFloorInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "TowerCode" BIGINT,
    "Floor" INTEGER,
    "ClearCount" INTEGER,
    "ContinueRoundIndex" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_910a720236f5517b ON protocol_data."TowerFloorInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TowerFloorInfo"."TowerCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."TowerFloorInfo"."Floor" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."TowerFloorInfo"."ClearCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."TowerFloorInfo"."ContinueRoundIndex" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."TowerGuildMemberRankInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "User" JSONB,
    "Rank" BIGINT,
    "Floor" INTEGER,
    "FirstClearedAt" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_166550dda87c24bf ON protocol_data."TowerGuildMemberRankInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TowerGuildMemberRankInfo"."User" IS 'Key(0); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."TowerGuildMemberRankInfo"."Rank" IS 'Key(1); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."TowerGuildMemberRankInfo"."Floor" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."TowerGuildMemberRankInfo"."FirstClearedAt" IS 'Key(3); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."TowerMagicItemInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "CharacterCode" BIGINT,
    "EquipSlot" INTEGER,
    "MagicItemCode" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3f4c82c35e0eeec1 ON protocol_data."TowerMagicItemInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TowerMagicItemInfo"."CharacterCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."TowerMagicItemInfo"."EquipSlot" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."TowerMagicItemInfo"."MagicItemCode" IS 'Key(2); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."TowerMyProfileInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserId" TEXT,
    "UserName" TEXT,
    "ProfileCharacterCode" BIGINT,
    "HonorCode" BIGINT,
    "ProfileCharacterRank" INTEGER,
    "ProfileCharacterRarity" INTEGER,
    "ProfileIllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_461f3ebdf5eefd7f ON protocol_data."TowerMyProfileInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."TowerMyProfileInfo"."UserId" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."TowerMyProfileInfo"."UserName" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."TowerMyProfileInfo"."ProfileCharacterCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."TowerMyProfileInfo"."HonorCode" IS 'Key(3); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."TowerMyProfileInfo"."ProfileCharacterRank" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."TowerMyProfileInfo"."ProfileCharacterRarity" IS 'Key(5); C# int';
COMMENT ON COLUMN protocol_data."TowerMyProfileInfo"."ProfileIllustrationIndex" IS 'Key(6); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."TutorialProgressInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_c3257cbb6960d6a1 ON protocol_data."TutorialProgressInfo" (owner_user_id);
CREATE TABLE IF NOT EXISTS protocol_data."UserInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Id" TEXT,
    "Name" TEXT,
    "Level" INTEGER,
    "Experience" BIGINT,
    "Stamina" JSONB,
    "QuizStamina" JSONB,
    "ProfileCharacterCode" BIGINT,
    "TutorialProgressInfo" JSONB,
    "FirstLoggedInAt" BIGINT,
    "LastLoggedInAt" BIGINT,
    "IsChatBanned" BOOLEAN,
    "ProfileIllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_c930ce7d904e31a5 ON protocol_data."UserInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."UserInfo"."Id" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."UserInfo"."Name" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."UserInfo"."Level" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."UserInfo"."Experience" IS 'Key(3); C# long';
COMMENT ON COLUMN protocol_data."UserInfo"."Stamina" IS 'Key(4); C# Stamina';
COMMENT ON COLUMN protocol_data."UserInfo"."QuizStamina" IS 'Key(5); C# Stamina';
COMMENT ON COLUMN protocol_data."UserInfo"."ProfileCharacterCode" IS 'Key(6); C# long';
COMMENT ON COLUMN protocol_data."UserInfo"."TutorialProgressInfo" IS 'Key(7); C# TutorialProgressInfo';
COMMENT ON COLUMN protocol_data."UserInfo"."FirstLoggedInAt" IS 'Key(8); C# long';
COMMENT ON COLUMN protocol_data."UserInfo"."LastLoggedInAt" IS 'Key(9); C# long';
COMMENT ON COLUMN protocol_data."UserInfo"."IsChatBanned" IS 'Key(10); C# bool';
COMMENT ON COLUMN protocol_data."UserInfo"."ProfileIllustrationIndex" IS 'Key(11); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."UserPersonalInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Id" TEXT,
    "Name" TEXT,
    "CharacterCode" BIGINT,
    "Level" INTEGER,
    "LastLoggedInAt" BIGINT,
    "Introduction" TEXT,
    "HonorCode" BIGINT,
    "TotalBattlePower" BIGINT,
    "IsFollower" BOOLEAN,
    "Rank" INTEGER,
    "Rarity" INTEGER,
    "SwitchableCharacterIndex" INTEGER,
    "IllustrationIndex" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_f9b4bbf7185d2aca ON protocol_data."UserPersonalInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."Id" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."Name" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."CharacterCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."Level" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."LastLoggedInAt" IS 'Key(4); C# long';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."Introduction" IS 'Key(5); C# string';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."HonorCode" IS 'Key(6); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."TotalBattlePower" IS 'Key(7); C# long';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."IsFollower" IS 'Key(8); C# bool';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."Rank" IS 'Key(9); C# int';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."Rarity" IS 'Key(10); C# int';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."SwitchableCharacterIndex" IS 'Key(11); C# int';
COMMENT ON COLUMN protocol_data."UserPersonalInfo"."IllustrationIndex" IS 'Key(12); C# CharacterIllustrationType';
CREATE TABLE IF NOT EXISTS protocol_data."UserPersonalInfoOld" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Id" TEXT,
    "Name" TEXT,
    "CharacterCode" BIGINT,
    "Level" INTEGER,
    "LastLoggedInAt" BIGINT,
    "Introduction" TEXT,
    "HonorCode" BIGINT,
    "TotalBattlePower" BIGINT,
    "IsFollower" BOOLEAN,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_cbc8848c17baa2a3 ON protocol_data."UserPersonalInfoOld" (owner_user_id);
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."Id" IS 'Key(0); C# string';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."Name" IS 'Key(1); C# string';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."CharacterCode" IS 'Key(2); C# long';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."Level" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."LastLoggedInAt" IS 'Key(4); C# long';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."Introduction" IS 'Key(5); C# string';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."HonorCode" IS 'Key(6); C# Nullable<long>';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."TotalBattlePower" IS 'Key(7); C# long';
COMMENT ON COLUMN protocol_data."UserPersonalInfoOld"."IsFollower" IS 'Key(8); C# bool';
CREATE TABLE IF NOT EXISTS protocol_data."UserProfileInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "UserPersonalInfo" JSONB,
    "GuildInfo" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_3ab5c8a76ebbbd93 ON protocol_data."UserProfileInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."UserProfileInfo"."UserPersonalInfo" IS 'Key(0); C# UserPersonalInfo';
COMMENT ON COLUMN protocol_data."UserProfileInfo"."GuildInfo" IS 'Key(1); C# GuildInfo';
CREATE TABLE IF NOT EXISTS protocol_data."UserRecordArenaInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "Category" JSONB,
    "Rank" INTEGER,
    "HighestRank" INTEGER,
    "HighestRankInHistory" INTEGER,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_5f7861e95bcfacfc ON protocol_data."UserRecordArenaInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."UserRecordArenaInfo"."Category" IS 'Key(0); C# ArenaCategory';
COMMENT ON COLUMN protocol_data."UserRecordArenaInfo"."Rank" IS 'Key(1); C# int';
COMMENT ON COLUMN protocol_data."UserRecordArenaInfo"."HighestRank" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."UserRecordArenaInfo"."HighestRankInHistory" IS 'Key(3); C# int';
CREATE TABLE IF NOT EXISTS protocol_data."UserRecordDungeon2Info" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "DungeonGroupCode" BIGINT,
    "HighestScore" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_b9562b50ce26e62e ON protocol_data."UserRecordDungeon2Info" (owner_user_id);
COMMENT ON COLUMN protocol_data."UserRecordDungeon2Info"."DungeonGroupCode" IS 'Key(0); C# long';
COMMENT ON COLUMN protocol_data."UserRecordDungeon2Info"."HighestScore" IS 'Key(1); C# long';
CREATE TABLE IF NOT EXISTS protocol_data."UserRecordInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "QuestStarCounts" JSONB,
    "ArenaRanking" JSONB,
    "OwnedCharacterCount" INTEGER,
    "UnlockedStoryCount" INTEGER,
    "OwnedMagicItemCount" INTEGER,
    "OwnedHonorCount" INTEGER,
    "HighestClearedTowerFloor" INTEGER,
    "LatestDuelRanking" JSONB,
    "EventDamageRanking" JSONB,
    "Dungeon2Records" JSONB,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_e7204d8eac1ba531 ON protocol_data."UserRecordInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."UserRecordInfo"."QuestStarCounts" IS 'Key(0); C# Dictionary<Difficulty, int>';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."ArenaRanking" IS 'Key(1); C# List<UserRecordArenaInfo>';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."OwnedCharacterCount" IS 'Key(2); C# int';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."UnlockedStoryCount" IS 'Key(3); C# int';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."OwnedMagicItemCount" IS 'Key(4); C# int';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."OwnedHonorCount" IS 'Key(5); C# int';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."HighestClearedTowerFloor" IS 'Key(6); C# int';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."LatestDuelRanking" IS 'Key(7); C# DuelMyRankingInfo';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."EventDamageRanking" IS 'Key(8); C# EventDamageRankingRecordInfo';
COMMENT ON COLUMN protocol_data."UserRecordInfo"."Dungeon2Records" IS 'Key(9); C# List<UserRecordDungeon2Info>';
CREATE TABLE IF NOT EXISTS protocol_data."WishListInfo" (
    response_id BIGINT NOT NULL REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    node_path TEXT NOT NULL,
    owner_user_id TEXT,
    wire_length INTEGER NOT NULL,
    unknown_fields JSONB NOT NULL,
    "WishListType" JSONB,
    "Code" BIGINT,
    PRIMARY KEY (response_id, node_path)
);
CREATE INDEX IF NOT EXISTS owner_38d79781a2fc244d ON protocol_data."WishListInfo" (owner_user_id);
COMMENT ON COLUMN protocol_data."WishListInfo"."WishListType" IS 'Key(0); C# WishListType';
COMMENT ON COLUMN protocol_data."WishListInfo"."Code" IS 'Key(1); C# long';
