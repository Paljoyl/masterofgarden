-- Local simulated purchases; no official payment receipts or upstream orders.
CREATE TABLE public.shop_purchase_counts (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    kind TEXT NOT NULL, code BIGINT NOT NULL, period BIGINT NOT NULL,
    purchased_count BIGINT NOT NULL CHECK (purchased_count >= 0), updated_at BIGINT NOT NULL,
    PRIMARY KEY (player_id,kind,code,period)
);
CREATE TABLE public.shop_lineup_selections (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    code BIGINT NOT NULL, period BIGINT NOT NULL, generation INTEGER NOT NULL DEFAULT 0,
    lottery_code BIGINT NOT NULL,
    PRIMARY KEY (player_id,code,period)
);
CREATE TABLE public.local_payment_orders (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    order_id TEXT NOT NULL, payment_code BIGINT NOT NULL, variant TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','complete')),
    created_at BIGINT NOT NULL, completed_at BIGINT, response BYTEA,
    PRIMARY KEY (player_id,order_id),
    CHECK ((status='pending' AND completed_at IS NULL AND response IS NULL)
        OR (status='complete' AND completed_at IS NOT NULL AND response IS NOT NULL))
);
CREATE UNIQUE INDEX local_payment_pending ON public.local_payment_orders(player_id,payment_code,variant)
    WHERE status='pending';
CREATE TABLE public.shop_owned_honors (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    honor_code BIGINT NOT NULL, acquired_at BIGINT NOT NULL,
    PRIMARY KEY (player_id,honor_code)
);
