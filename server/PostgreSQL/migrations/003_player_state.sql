-- Hand-designed current player state. Keys express ownership, never capture identity.

CREATE TABLE public.players (
    player_id TEXT PRIMARY KEY CHECK (length(player_id) > 0),
    name TEXT NOT NULL, level INTEGER NOT NULL CHECK (level >= 1),
    experience BIGINT NOT NULL CHECK (experience >= 0),
    profile_character_code BIGINT NOT NULL,
    tutorial_progress INTEGER,
    first_logged_in_at BIGINT NOT NULL, last_logged_in_at BIGINT NOT NULL,
    is_chat_banned BOOLEAN NOT NULL, profile_illustration_index INTEGER NOT NULL,
    revision BIGINT NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE public.player_stamina (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('normal','quiz')),
    value BIGINT NOT NULL CHECK (value >= 0), updated_at BIGINT NOT NULL,
    PRIMARY KEY (player_id,kind)
);
CREATE TABLE public.characters (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    character_code BIGINT NOT NULL,
    level INTEGER NOT NULL CHECK (level >= 1), experience BIGINT NOT NULL CHECK (experience >= 0),
    rank INTEGER NOT NULL CHECK (rank >= 0), limit_break INTEGER NOT NULL CHECK (limit_break >= 0),
    rarity INTEGER NOT NULL CHECK (rarity >= 0), closeness INTEGER NOT NULL CHECK (closeness >= 0),
    PRIMARY KEY (player_id,character_code)
);
CREATE TABLE public.items (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    item_code BIGINT NOT NULL, quantity BIGINT NOT NULL CHECK (quantity >= 0),
    recovered_at BIGINT NOT NULL,
    PRIMARY KEY (player_id,item_code)
);
CREATE TABLE public.character_equipment (
    player_id TEXT NOT NULL, character_code BIGINT NOT NULL,
    slot INTEGER NOT NULL CHECK (slot >= 0),
    PRIMARY KEY (player_id,character_code,slot),
    FOREIGN KEY (player_id,character_code) REFERENCES public.characters ON DELETE CASCADE
);
CREATE TABLE public.magic_items (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    magic_item_code BIGINT NOT NULL, level INTEGER NOT NULL CHECK (level >= 1),
    created_at BIGINT NOT NULL,
    PRIMARY KEY (player_id,magic_item_code)
);
CREATE TABLE public.magic_item_effects (
    player_id TEXT NOT NULL, magic_item_code BIGINT NOT NULL,
    effect_slot INTEGER NOT NULL CHECK (effect_slot >= 0), effect_code BIGINT NOT NULL,
    PRIMARY KEY (player_id,magic_item_code,effect_slot),
    FOREIGN KEY (player_id,magic_item_code) REFERENCES public.magic_items ON DELETE CASCADE
);
CREATE TABLE public.parties (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    party_type INTEGER NOT NULL, party_no INTEGER NOT NULL CHECK (party_no >= 0),
    name TEXT NOT NULL, is_active BOOLEAN NOT NULL,
    total_power BIGINT NOT NULL CHECK (total_power >= 0),
    PRIMARY KEY (player_id,party_type,party_no)
);
CREATE TABLE public.party_characters (
    player_id TEXT NOT NULL, party_type INTEGER NOT NULL, party_no INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0), character_code BIGINT,
    switchable_character_index INTEGER NOT NULL,
    PRIMARY KEY (player_id,party_type,party_no,position),
    FOREIGN KEY (player_id,party_type,party_no) REFERENCES public.parties ON DELETE CASCADE,
    FOREIGN KEY (player_id,character_code) REFERENCES public.characters
);
CREATE TABLE public.party_magic_items (
    player_id TEXT NOT NULL, party_type INTEGER NOT NULL, party_no INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0), character_code BIGINT NOT NULL,
    equip_slot INTEGER NOT NULL CHECK (equip_slot >= 0), magic_item_code BIGINT,
    PRIMARY KEY (player_id,party_type,party_no,position),
    FOREIGN KEY (player_id,party_type,party_no) REFERENCES public.parties ON DELETE CASCADE,
    FOREIGN KEY (player_id,character_code) REFERENCES public.characters,
    FOREIGN KEY (player_id,magic_item_code) REFERENCES public.magic_items
);
CREATE TABLE public.party_rentals (
    player_id TEXT NOT NULL, party_type INTEGER NOT NULL, party_no INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0), rental_character_code BIGINT NOT NULL,
    switchable_character_index INTEGER NOT NULL,
    PRIMARY KEY (player_id,party_type,party_no,position),
    FOREIGN KEY (player_id,party_type,party_no) REFERENCES public.parties ON DELETE CASCADE
);
CREATE TABLE public.quests (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    quest_code BIGINT NOT NULL, clear_count INTEGER NOT NULL CHECK (clear_count >= 0),
    star_count SMALLINT NOT NULL CHECK (star_count BETWEEN 0 AND 255),
    challenge_count INTEGER, challenge_last_reset_at BIGINT,
    recover_count INTEGER, recover_last_reset_at BIGINT,
    PRIMARY KEY (player_id,quest_code),
    CHECK ((challenge_count IS NULL) = (challenge_last_reset_at IS NULL)),
    CHECK ((recover_count IS NULL) = (recover_last_reset_at IS NULL))
);
CREATE TABLE public.quest_groups (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    quest_group_code BIGINT NOT NULL, clear_count INTEGER NOT NULL CHECK (clear_count >= 0),
    challenge_count INTEGER, challenge_last_reset_at BIGINT,
    recover_count INTEGER, recover_last_reset_at BIGINT,
    PRIMARY KEY (player_id,quest_group_code),
    CHECK ((challenge_count IS NULL) = (challenge_last_reset_at IS NULL)),
    CHECK ((recover_count IS NULL) = (recover_last_reset_at IS NULL))
);
CREATE TABLE public.quest_clear_counts (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    quest_code BIGINT NOT NULL, count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (player_id,quest_code)
);
CREATE TABLE public.stories (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    story_code BIGINT NOT NULL, status INTEGER NOT NULL,
    PRIMARY KEY (player_id,story_code)
);
CREATE TABLE mog_local.player_state_imports (
    player_id TEXT PRIMARY KEY REFERENCES public.players ON DELETE CASCADE,
    source_response_id BIGINT REFERENCES mog_local.responses ON DELETE SET NULL,
    captured_at DOUBLE PRECISION NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE public.operations (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    operation_key TEXT NOT NULL CHECK (length(operation_key) > 0),
    operation_type TEXT NOT NULL, request_hash TEXT NOT NULL, result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id,operation_key)
);
CREATE TABLE public.item_ledger (
    player_id TEXT NOT NULL, operation_key TEXT NOT NULL,
    item_code BIGINT NOT NULL, delta BIGINT NOT NULL CHECK (delta <> 0),
    balance BIGINT NOT NULL CHECK (balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id,operation_key,item_code),
    FOREIGN KEY (player_id,operation_key) REFERENCES public.operations ON DELETE CASCADE,
    FOREIGN KEY (player_id,item_code) REFERENCES public.items
);
CREATE INDEX party_character_lookup ON public.party_characters(player_id,character_code);
CREATE INDEX party_magic_character_lookup ON public.party_magic_items(player_id,character_code);
CREATE INDEX party_magic_item_lookup ON public.party_magic_items(player_id,magic_item_code);
CREATE INDEX item_ledger_item_history ON public.item_ledger(player_id,item_code,created_at);
COMMENT ON TABLE public.items IS 'StackItemInfo including unclassified currency codes; no guessed wallet mapping';
COMMENT ON TABLE public.character_equipment IS 'EquipmentInfo identifies an occupied character slot, not an item instance';
COMMENT ON TABLE public.quest_clear_counts IS 'QuestClearCountInfo kept distinct from QuestInfo.ClearCount until reset semantics are known';
COMMENT ON TABLE mog_local.player_state_imports IS 'One-time bootstrap provenance; importing more captures never overwrites local state';
