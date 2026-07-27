-- 0176 — Sapu fosil caption/hook-title yang tersisa (lanjutan 0174)
--
-- Audit 2026-07-27 (perintah owner "hapus yang tak pernah di-wiring"):
--
--  1. fonts.preview_url — kolom sisa desain lama. NOL pemakaian di seluruh repo (BE/FE/SQL) dan
--     NOL baris terisi. URL file font disimpan di kolom `file_url` (0174), yang memang dibaca FE.
--
--  2. hook_title_style.{bold, italic, alignment} — tersimpan di 15 baris tenant_configs dan ikut
--     tercantum di DEFAULT hook title pada kode, tetapi _add_hook_title() TIDAK PERNAH membacanya:
--     overlay judul dibuat dengan FFmpeg drawtext, yang tidak punya parameter tebal/miring/perataan
--     (tebal ditentukan oleh file fontnya, perataan dihitung manual dari lebar teks).
--     Membiarkannya = kenop palsu: admin/tenant mengira bisa mengubah, padahal tak berefek apa pun.

BEGIN;

ALTER TABLE fonts DROP COLUMN IF EXISTS preview_url;

UPDATE tenant_configs
   SET hook_title_style = hook_title_style - 'bold' - 'italic' - 'alignment'
 WHERE hook_title_style ?| array['bold','italic','alignment'];

COMMIT;
