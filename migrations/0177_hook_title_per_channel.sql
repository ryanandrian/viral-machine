-- 0177 — Gaya JUDUL PEMBUKA jadi per-channel (+ tutup default kolom yang masih menanam fosil)
--
-- SEBELUM:
--  * hook_title_style hanya ada di tenant_configs = berlaku SEMUA channel. Padahal judul pembuka
--    muncul di setiap video dan sekelas dengan caption/logo/CTA/hashtag yang SUDAH per-channel.
--    Tenant multi-channel tak bisa membedakan gaya judul channel horor vs channel jazz.
--  * DEFAULT KOLOM tenant_configs masih menanam kunci fosil ke SETIAP tenant baru (0174/0176 hanya
--    membersihkan baris yang sudah ada, bukan defaultnya) — fosil bereproduksi lewat pintu ini.
--
-- SESUDAH: channels.hook_title_style (pola SAMA dgn caption_style: overlay per-channel, fallback
-- tenant_configs bila NULL) + default kolom bersih.

BEGIN;

-- 1) Kolom per-channel. URUTAN PENTING: kolom dibuat TANPA default dulu.
--    Di PostgreSQL, ADD COLUMN ... DEFAULT langsung MENGISI seluruh baris lama dengan default itu —
--    kalau begitu, langkah 2 (mewarisi setelan tenant) tak akan pernah kena dan gaya judul channel
--    yang sudah disetel tenant akan tereset diam-diam. DEFAULT dipasang belakangan (langkah 2c),
--    sehingga hanya berlaku untuk channel BARU.
ALTER TABLE channels ADD COLUMN IF NOT EXISTS hook_title_style JSONB;

COMMENT ON COLUMN channels.hook_title_style IS
  'Gaya judul pembuka per-channel (overlay atas tenant_configs.hook_title_style). NULL = warisi tenant.';

-- 2) Channel yang SUDAH ADA diisi nilai EFEKTIF mereka saat ini (default kode ditimpa setelan
--    tenant), supaya tampilan video existing TIDAK berubah sedikit pun karena migrasi ini.
UPDATE channels c
   SET hook_title_style =
       '{"enabled": true, "font_name": "Anton", "font_size": 58, "font_color": "#FFD700",
         "border_color": "#000000", "outline": 4, "shadow": 3, "position_y_pct": 15,
         "max_chars_per_line": 25}'::jsonb
       || coalesce(tc.hook_title_style, '{}'::jsonb)
          - 'bold' - 'italic' - 'alignment' - 'outline_alpha'   -- kunci yg tak dibaca mesin
  FROM tenant_configs tc
 WHERE tc.tenant_id = c.tenant_id
   AND c.hook_title_style IS NULL;

-- 2b) Channel tanpa baris tenant_configs pasangan → cukup gaya standar.
UPDATE channels
   SET hook_title_style =
       '{"enabled": true, "font_name": "Anton", "font_size": 58, "font_color": "#FFD700",
         "border_color": "#000000", "outline": 4, "shadow": 3, "position_y_pct": 15,
         "max_chars_per_line": 25}'::jsonb
 WHERE hook_title_style IS NULL;

-- 2c) BARU sekarang default dipasang — berlaku untuk channel yang dibuat setelah ini, sehingga
--     tak pernah ada channel dengan gaya judul kosong (permintaan owner: harus ada default value).
ALTER TABLE channels ALTER COLUMN hook_title_style SET DEFAULT
  '{"enabled": true, "font_name": "Anton", "font_size": 58, "font_color": "#FFD700",
    "border_color": "#000000", "outline": 4, "shadow": 3, "position_y_pct": 15,
    "max_chars_per_line": 25}'::jsonb;

-- 3) TUTUP PINTU REPRODUKSI FOSIL: default kolom tenant_configs dibersihkan dari kunci yang tidak
--    pernah dibaca mesin (caption: bold_keywords/margin_v/max_lines · hook: outline_alpha).
ALTER TABLE tenant_configs ALTER COLUMN caption_style SET DEFAULT
  '{"font_size": 68, "active_word_color": "#FFD700", "inactive_word_color": "#FFFFFF",
    "max_words_per_line": 3}'::jsonb;

ALTER TABLE tenant_configs ALTER COLUMN hook_title_style SET DEFAULT
  '{"enabled": true, "font_size": 58, "font_color": "#FFD700", "outline": 4, "shadow": 3,
    "position_y_pct": 15, "max_chars_per_line": 25}'::jsonb;

-- 4) `alignment` caption: bukan pilihan gaya melainkan detail mesin subtitle — kini konstanta di
--    kode (VideoRenderer.ASS_ALIGNMENT). Buang dari data agar tak ada kenop menggantung.
UPDATE channels        SET caption_style = caption_style - 'alignment'    WHERE caption_style ? 'alignment';
UPDATE tenant_configs  SET caption_style = caption_style - 'alignment'    WHERE caption_style ? 'alignment';

COMMIT;
