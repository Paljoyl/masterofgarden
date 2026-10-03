-- Missing TW beginner missions, from MasterData_RegionTw_Production 4.12.1.
-- Only static task definitions change; player progress and receipt records are preserved.
UPDATE public.game_time_definitions AS definitions
SET data = COALESCE((
    SELECT jsonb_agg(entry ORDER BY ordinal)
    FROM jsonb_array_elements(definitions.data) WITH ORDINALITY AS entries(entry, ordinal)
    WHERE (entry->>'Code')::bigint NOT IN (30310000002,30310000009)
), '[]'::jsonb) || '[{"Code":30310000002,"GroupCode":3021,"Title":"","Description":"【新手】將玩家等級提升至3","UserDataReference":{"Type":2,"Params":[]},"TargetCount":3,"RewardCode":30180000001,"MissionCodeForUnlock":0,"UserDataReferenceForUnlock":{"Type":0,"Params":[]},"UserDataReferenceCountForUnlock":0,"DisplayOrder":3,"ScreenTransition1":7,"ScreenTransition2":14,"ScreenTransition3":0,"ScreenTransitionParams":[0],"PromotionId":0,"IsObsoleted":false,"UserDataReferenceToReceive":null,"UserDataReferenceCountToReceive":0,"DescriptionToReceive":""},{"Code":30310000009,"GroupCode":3021,"Title":"","Description":"【新手】於主畫面變更交流角色","UserDataReference":{"Type":1,"Params":[1118000000]},"TargetCount":1,"RewardCode":30180000001,"MissionCodeForUnlock":0,"UserDataReferenceForUnlock":{"Type":0,"Params":[]},"UserDataReferenceCountForUnlock":0,"DisplayOrder":10,"ScreenTransition1":2,"ScreenTransition2":14,"ScreenTransition3":0,"ScreenTransitionParams":[0],"PromotionId":0,"IsObsoleted":false,"UserDataReferenceToReceive":null,"UserDataReferenceCountToReceive":0,"DescriptionToReceive":""}]'::jsonb
WHERE definitions.name = 'mission_master';
