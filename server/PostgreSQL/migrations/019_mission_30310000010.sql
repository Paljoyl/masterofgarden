-- Missing TW beginner chat mission, from MasterData_RegionTw_Production 4.12.1.
-- Bulk claims roll back when any requested mission is missing. Preserve all player state.
UPDATE public.game_time_definitions AS definitions
SET data = COALESCE((
    SELECT jsonb_agg(entry ORDER BY ordinal)
    FROM jsonb_array_elements(definitions.data) WITH ORDINALITY AS entries(entry, ordinal)
    WHERE (entry->>'Code')::bigint <> 30310000010
), '[]'::jsonb) || '[{"Code":30310000010,"GroupCode":3021,"Title":"","Description":"【新手】進行2次交流","UserDataReference":{"Type":1,"Params":[1103000000]},"TargetCount":2,"RewardCode":30180000001,"MissionCodeForUnlock":0,"UserDataReferenceForUnlock":{"Type":0,"Params":[]},"UserDataReferenceCountForUnlock":0,"DisplayOrder":11,"ScreenTransition1":2,"ScreenTransition2":14,"ScreenTransition3":0,"ScreenTransitionParams":[0],"PromotionId":0,"IsObsoleted":false,"UserDataReferenceToReceive":null,"UserDataReferenceCountToReceive":0,"DescriptionToReceive":""}]'::jsonb
WHERE definitions.name = 'mission_master';
