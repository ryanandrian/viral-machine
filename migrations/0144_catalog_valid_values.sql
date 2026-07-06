-- 0144_catalog_valid_values.sql
-- Sumber-tunggal nilai-sah katalog AI (adapter/transport/enum) — CERMIN dari registry KODE.
-- Kenapa: form admin (dropdown) + validasi tulis (route.ts) harus tahu nilai yang BENAR-BENAR
-- didukung mesin. Kebenaran ada di kode; tabel ini di-refresh tiap startup service oleh
-- src/config/catalog_sync.sync_catalog_valid_values() → nol drift, adapter baru muncul otomatis.
-- Akses: service_role saja (FE katalog baca via /api/admin/catalog service_role; RLS default-deny).
-- (Owner 2026-07-07: tuntas + antisipatif.)

CREATE TABLE IF NOT EXISTS catalog_valid_values (
  field      text NOT NULL,   -- llm_adapter | tts_adapter | visual_transport | auth_type | component
  value      text NOT NULL,
  label      text,
  synced_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (field, value)
);

ALTER TABLE catalog_valid_values ENABLE ROW LEVEL SECURITY;  -- default-deny; service_role bypass

-- Normalisasi nilai VESTIGIAL: together tak punya model LLM (hanya image, transport=provider_key);
-- adapter='openai_images' bukan identitas adapter nyata mana pun → set ke transport visual sahnya.
UPDATE ai_providers SET adapter = 'together' WHERE provider_key = 'together' AND adapter = 'openai_images';
