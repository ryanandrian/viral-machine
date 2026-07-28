-- 0180 — SATU penyedia `fal` untuk keempat kategori (mengoreksi 0179)
--
-- KOREKSI ATAS 0179 (keberatan owner, benar): 0179 memecah fal jadi tiga baris penyedia
-- (fal / fal_llm / fal_tts) hanya karena kolom `ai_providers.adapter` tak bisa menyandang tiga
-- identitas. Itu mengorbankan integritas relasi — penyedia→model seharusnya one-to-many:
-- SATU vendor, banyak model. Tiga baris untuk satu vendor = data yang menipu.
--
-- FAKTA YANG MEMBUAT SATU BARIS CUKUP (ditelusuri tuntas di seluruh backend 2026-07-28):
-- `ai_providers.adapter` HANYA dibaca satu tempat — src/providers/llm/__init__.py:44 (jalur LLM).
--   * Jalur VISUAL (ai_image/ai_video) hanya membaca `base_url`, tak pernah `adapter`.
--   * Jalur SUARA membaca `tts_profiles.adapter` — tabel terpisah, tak menyentuh kolom ini.
-- Maka kolom itu diisi identitas LLM ('fal_any_llm'); visual & suara tetap berjalan apa adanya.
-- Nilai tetap sah menurut taksonomi katalog (llm_adapter ∪ tts_adapter ∪ visual_transport).

BEGIN;

-- 1) Semua model fal kembali ke induk yang benar: satu penyedia `fal`.
UPDATE ai_models SET provider_key = 'fal' WHERE provider_key IN ('fal_llm', 'fal_tts');

-- 2) Profil suara ikut ke penyedia `fal` (adapter protokolnya tetap dari tabel ini).
INSERT INTO tts_profiles (provider_key, display_name, adapter, tts_class, delivery_wps,
                          has_word_timeframe, speed_param, is_active)
VALUES ('fal', 'fal.ai (ElevenLabs)', 'fal_tts', 'timed', 1.97, TRUE, 'speed', FALSE)
ON CONFLICT (provider_key) DO UPDATE
   SET adapter = EXCLUDED.adapter, tts_class = EXCLUDED.tts_class,
       delivery_wps = EXCLUDED.delivery_wps, has_word_timeframe = EXCLUDED.has_word_timeframe,
       speed_param = EXCLUDED.speed_param, display_name = EXCLUDED.display_name;
DELETE FROM tts_profiles WHERE provider_key = 'fal_tts';

-- 3) Kolom adapter penyedia `fal` = identitas LLM (satu-satunya pembacanya).
UPDATE ai_providers SET adapter = 'fal_any_llm' WHERE provider_key = 'fal';

-- 4) Dua baris penyedia berlebih dibuang — tak boleh ada penyedia kembar untuk satu vendor.
DELETE FROM ai_providers WHERE provider_key IN ('fal_llm', 'fal_tts');

COMMIT;
