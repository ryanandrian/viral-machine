-- 0181 — Identitas suara KATALOG vs VENDOR + 12 suara fal.ai
--
-- MASALAH YANG DISELESAIKAN
-- `voice_catalog.voice_key` adalah kunci utama GLOBAL (dirujuk `channels.voice_key` lewat kunci asing,
-- `tts_delivery_samples.voice_key` untuk kalibrasi pace, dan atribusi video). Untuk ElevenLabs isinya
-- kebetulan = ID suara di sisi vendor. Selama satu suara hanya ada di satu vendor, dua identitas itu
-- boleh tertumpuk. Begitu vendor AGREGATOR masuk — fal.ai menyajikan model ElevenLabs yang SAMA —
-- suara yang sama harus punya dua baris katalog dengan identitas vendor IDENTIK, dan itu mustahil bila
-- identitas vendor dipakai sebagai kunci utama.
--
-- Mengubah kunci utama jadi (penyedia, suara) SENGAJA TIDAK dipilih: itu menyeret kunci asing
-- `channels`, kunci baris di API katalog admin, dan pencarian Test Lab — risikonya jauh di atas
-- manfaatnya. Yang dipilih: kolom terpisah, boleh kosong. Kosong = pakai `voice_key` apa adanya,
-- jadi 32 baris suara yang sudah ada berperilaku PERSIS seperti sebelumnya.
--
-- Terjemahan katalog→vendor terjadi di SATU tempat: `build_tts_provider` (src/providers/tts/__init__.py).
-- Dengan begitu produksi, Test Lab, dan tombol "Uji model" admin ikut benar tanpa kode terpisah, dan
-- config pemanggil TIDAK dimutasi — kalibrasi pace & atribusi video tetap memakai kunci katalog kita.
--
-- BUKTI NYATA (uji langsung ke fal, 2026-07-28)
--   • Ke-12 ID suara ElevenLabs kita diterima fal; audio ke-12-nya BERBEDA (12 md5 unik) — bukan
--     diam-diam jatuh ke suara bawaan.
--   • ID ngawur ditolak jujur: HTTP 422 "Voice not found" — tak ada kegagalan senyap.
--   • 8 suara Indonesia kita berasal dari Voice Library; lewat ElevenLabs langsung tenant masih harus
--     menekan "Add to my voices" di akunnya, lewat fal langsung jalan. Catatan itu karena itu DIBUANG
--     dari deskripsi baris fal (kalau disalin apa adanya = keterangan menipu).
--   • 12 berkas pratinjau dibuat lewat adaptor produksi memakai default_settings masing-masing suara,
--     diunggah ke S3 aset, dan diverifikasi HTTP 200. Setiap baris MEMILIKI berkasnya sendiri
--     (`voice-previews/<voice_key>.mp3`) — sebab jalur hapus admin menghapus objek berdasarkan
--     voice_key; kalau berbagi berkas dengan baris ElevenLabs, menghapus satu suara ElevenLabs akan
--     diam-diam merusak pratinjau baris fal.

BEGIN;

-- 1) Kolom identitas vendor. TANPA DEFAULT — `ADD COLUMN ... DEFAULT` mengisi SELURUH baris lama
--    (pelajaran migrasi 0177); di sini NULL justru bermakna "identitasnya sama dengan voice_key".
ALTER TABLE voice_catalog ADD COLUMN IF NOT EXISTS vendor_voice_id text;
COMMENT ON COLUMN voice_catalog.vendor_voice_id IS
  'Identitas suara di sisi VENDOR. NULL = sama dengan voice_key (perilaku semua penyedia non-agregator). '
  'Diterjemahkan sekali di build_tts_provider; voice_key tetap kunci katalog untuk pace & atribusi.';

-- 2) Rentang parameter profil suara fal — dari SKEMA RESMI endpoint fal (diperiksa 2026-07-28):
--    speed 0.7–1.2 · style 0–1 · stability 0–1 · similarity_boost 0–1 (identik ElevenLabs, sebab
--    modelnya memang model ElevenLabs). Dipakai gate durasi §10.A untuk clamp speed lintas-penyedia —
--    kosong berarti gate itu tak punya pagar untuk fal.
UPDATE tts_profiles
   SET param_schema = '{"speed":[0.7,1.2],"style":[0,1],"stability":[0,1],"similarity_boost":[0,1]}'::jsonb
 WHERE provider_key = 'fal';

-- 3) 12 suara fal — sifatnya DISALIN dari baris ElevenLabs padanannya (bukan diketik ulang: nol risiko
--    salah transkripsi), dengan lima hal yang sengaja berbeda:
--      • voice_key      = nama terbaca milik katalog kita (bukan ID vendor)
--      • vendor_voice_id= ID ElevenLabs yang dikirim ke fal
--      • preview_url    = berkas pratinjau milik baris ini sendiri
--      • description    = catatan "Add to my voices" dibuang (tak berlaku lewat fal)
--      • niche_default  = NULL (kolom tanpa konsumen di kode/DB; menandai dua suara sebagai bawaan
--                         niche yang sama hanya akan menyesatkan admin)
--    delivery_wps NULL = ikut pace dasar engine (tts_profiles.fal = 1,97, angka ElevenLabs), lalu
--    dikalibrasi sendiri dari sampel render nyata — terpisah dari sampel jalur ElevenLabs langsung.
INSERT INTO voice_catalog (voice_key, provider_key, vendor_voice_id, display_name, locale, language,
                           gender, age, accent, use_case, description, default_settings, preview_url,
                           niche_default, delivery_wps, is_active, sort_order)
SELECT m.baru, 'fal', v.voice_key, v.display_name, v.locale, v.language,
       v.gender, v.age, v.accent, v.use_case,
       COALESCE(regexp_replace(v.description, '\s*\[Voice Library[^\]]*\]\s*$', ''), '')
         || CASE WHEN v.description LIKE '%Voice Library%'
                 THEN ' [lewat fal: langsung tersedia, tanpa Add to my voices]' ELSE '' END,
       v.default_settings,
       'https://nos.wjv-1.neo.id/mesinviral-assets/voice-previews/' || m.baru || '.mp3',
       NULL, NULL, TRUE, m.urut
  FROM (VALUES
          ('pNInz6obpgDQGcFmaJgB', 'fal-adam',       110),
          ('21m00Tcm4TlvDq8ikWAM', 'fal-rachel',     111),
          ('VR6AewLTigWG4xSOukaG', 'fal-arnold',     112),
          ('EXAVITQu4vr4xnSDxMaL', 'fal-bella',      113),
          ('BfwyZzLnL4udYd1qYpiN', 'fal-luna-id',    114),
          ('44refPigMdH30vLdnBkE', 'fal-aluna-id',   115),
          ('o5s6XRBkPSTD4syv6mZg', 'fal-arunika-id', 116),
          ('vkW2LzXraZVeZ5G7Yv7c', 'fal-dila-id',    117),
          ('j7n5yC6BN3oA2ZIWImty', 'fal-bambang-id', 118),
          ('wvv6DzcHyOVTDgDY7SMW', 'fal-andi-id',    119),
          ('YaOJRohVGQB7O7pekQTF', 'fal-senja-id',   120),
          ('pIdeS8l1cmJzzqqt7NRc', 'fal-menit-id',   121)
       ) AS m(el, baru, urut)
  JOIN voice_catalog v ON v.voice_key = m.el
ON CONFLICT (voice_key) DO NOTHING;

COMMIT;

-- GERBANG YANG MASIH TERTUTUP: `tts_profiles.provider_key='fal'` tetap is_active=FALSE, jadi penyedia
-- suara fal TIDAK muncul di layar tenant dan 12 baris ini tak bisa dipilih siapa pun. Membukanya =
-- keputusan owner, satu sakelar di layar Katalog admin.
