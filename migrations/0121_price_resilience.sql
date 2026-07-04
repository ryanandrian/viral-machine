-- 0121 — Ketahanan sumber harga (owner 2026-07-04): sanity-guard perubahan drastis.
-- pricing_pending = USULAN harga dari sinkron yang DITAHAN (berubah >faktor dari harga lama) —
-- menunggu keputusan admin di Catalog (Terapkan/Abaikan). Kasus nyata: feed EL $180 vs resmi $100.
ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS pricing_pending jsonb;
