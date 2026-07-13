-- 0156 — PAKET TAHUNAN (finalisasi_tier_plan.md Tahap 2, ratifikasi owner §3b butir 1, 2026-07-13).
-- (1) Knob diskon tahunan: admin-editable via /admin/app-config (label dwibahasa CFG_META se-batch).
--     Harga tahunan = harga_bulanan × 12 × (1 − annual_discount_pct/100). 0 = pilihan tahunan DISEMBUNYIKAN.
-- (2) payments.period_months: durasi periode yang DIBELI order ini (1=bulanan, 12=tahunan) — dibaca
--     _apply_settlement → compute_new_period (durasi = subscription_period_days × period_months).
--     Baris lama = bulanan (DEFAULT 1, backfill implisit) — nol perubahan perilaku data lama.
BEGIN;

INSERT INTO app_config (key, value, description)
VALUES ('annual_discount_pct', 20,
        'Diskon paket tahunan (%). Harga tahunan = bulanan × 12 × (100−nilai)%. 0 = pilihan tahunan disembunyikan. (Nilai default: 20)')
ON CONFLICT (key) DO NOTHING;

ALTER TABLE payments ADD COLUMN IF NOT EXISTS period_months INTEGER NOT NULL DEFAULT 1;

COMMIT;
