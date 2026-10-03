-- Missing TW beginner mission, from MasterData_RegionTw_Production 4.12.1.
-- Only changes static configuration in public; player progress and receipts are untouched.
-- The existing reward 30180000001 grants 100 free stones (item 990000001).
UPDATE public.game_time_definitions AS definitions
SET data = COALESCE((
    SELECT jsonb_agg(entry ORDER BY position)
    FROM jsonb_array_elements(definitions.data) WITH ORDINALITY AS entries(entry, position)
    WHERE (entry->>'Code')::bigint <> 30310000001
), '[]'::jsonb) || '[{"Code":30310000001,"GroupCode":3021,"Title":"","Description":"【新手】抽取10次轉蛋","UserDataReference":{"Type":1,"Params":[1116000000]},"TargetCount":10,"RewardCode":30180000001,"MissionCodeForUnlock":0,"UserDataReferenceForUnlock":{"Type":0,"Params":[]},"UserDataReferenceCountForUnlock":0,"DisplayOrder":2,"ScreenTransition1":4,"ScreenTransition2":0,"ScreenTransition3":0,"ScreenTransitionParams":[0],"PromotionId":0,"IsObsoleted":false,"UserDataReferenceToReceive":null,"UserDataReferenceCountToReceive":0,"DescriptionToReceive":""}]'::jsonb
WHERE definitions.name = 'mission_master';
