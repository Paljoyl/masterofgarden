-- Local simulation odds for this exact SS-guaranteed start-dash pool.
-- Add one rule without replacing operator edits or existing pool rules.
-- No player balances, lottery limits, expiry or histories are modified.
INSERT INTO public.lottery_definitions (name, data) VALUES
('local_lottery_probability_master', $local$[
  {
    "Code": 11000156,
    "Distribution": "uniform-within-rarity",
    "Lineup": "special",
    "RarityChanceA": ["79", "18", "3"],
    "RarityChanceB": ["0", "0", "100"],
    "Source": "Local configuration for the 72-hour SS-guaranteed start-dash pool; official odds unavailable."
  }
]$local$::jsonb)
ON CONFLICT (name) DO UPDATE SET data =
  CASE WHEN EXISTS (
    SELECT 1 FROM jsonb_array_elements(public.lottery_definitions.data) AS rule
    WHERE rule->>'Code' = '11000156'
  ) THEN public.lottery_definitions.data
  ELSE public.lottery_definitions.data || EXCLUDED.data END;
