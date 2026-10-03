-- An unequipped placeholder may have wire CharacterCode=0 and MagicItem=null.
-- SQL NULL represents the absent owned character, without inventing character 0.
ALTER TABLE public.party_magic_items ALTER COLUMN character_code DROP NOT NULL;
ALTER TABLE public.party_magic_items ADD CONSTRAINT empty_magic_equipment
    CHECK (character_code IS NOT NULL OR magic_item_code IS NULL);
