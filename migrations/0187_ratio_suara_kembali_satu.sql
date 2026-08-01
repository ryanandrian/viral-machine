-- 0187 — Kembalikan laju bicara ke RATIO 1 (aturan owner) + buang sisa tuas kecepatan dari data
--
-- ATURAN OWNER (2026-08-01): "RATIO TTS TERBAIK ADALAH 1 (+0%). JUSTRU ISSUE UTAMA ADALAH TTS YANG
-- SANGAT LAMBAT MERUSAK MOOD YANG MENDENGAR, SEPERTI ORANG MALAS."
--
-- KEADAAN SEBELUM MIGRASI INI (terhitung dari DB live 2026-08-01) — aturan itu dilanggar di TIGA tempat
-- sekaligus, dan dua di antaranya tak terlihat di layar mana pun:
--
--  1. `tenant_configs.tts_voice_settings[niche].speed` = 0,83–0,93 pada 17 tenant. Ini sisa lubang
--     tempat solver durasi dulu menyuntikkan pengali kecepatan. Solvernya dicabut 2026-07-31, tapi
--     JALUR DATANYA tertinggal hidup dan lapisan ini MENANG di atas semua setelan lain. Akibat nyata
--     pada channel yang SEDANG AKTIF:
--         BJ Yusroon  (dark_history, preset 90 dtk, suara Gadis)   speed 0,83  → dibacakan −17%
--         Abyss ID    (ocean_mysteries, suara Christopher +5%)     speed 0,86  → dibacakan −10%
--     Jadi keluhan "suara seperti orang malas" MASIH BERLAKU hari ini meski tuasnya sudah "dicabut" —
--     yang dicabut hanya yang MENULIS, bukan yang MEMBACA.
--
--  2. `voice_catalog.default_settings.speed` = 0,83–0,95 pada 21 suara ElevenLabs/fal. Tak satu pun
--     dari angka ini pernah diputuskan sebagai keputusan produk; semuanya warisan.
--
--  3. Bawaan `0.87` DITANAM DI KODE pada adaptor ElevenLabs, fal, dan OpenAI (dicabut di commit yang
--     sama dengan migrasi ini).
--
-- AKIBAT KETIGA YANG TAK TERLIHAT: penjaga kalibrasi hanya memakai sampel ber-laju sama dengan
-- baseline suara. Selama speed ≠ 1 tertanam di lapisan yang tak tercatat, sampel ElevenLabs/fal tak
-- pernah lolos → suara berbayar TIDAK AKAN PERNAH mengkalibrasi dirinya sendiri.
--
-- YANG DIUBAH DI SINI: DATA-nya saja (kodenya di commit yang sama).
--   a. Buang kunci `speed` dari setiap objek niche di `tenant_configs.tts_voice_settings`.
--      `style`, `stability`, `similarity_boost` DIPERTAHANKAN — itu lapisan EKSPRESI VOKAL milik niche,
--      keputusan produk yang sah, dan tidak menyentuh laju bicara.
--   b. Setel `voice_catalog.default_settings.speed` = 1.0 untuk seluruh suara ElevenLabs & fal.
--      Kenopnya TETAP HIDUP (admin masih bisa mengubahnya, dan adaptor tetap membacanya) — yang
--      diperbaiki adalah NILAINYA, bukan keberadaan kenopnya.
--
-- SENGAJA TIDAK DISENTUH: `voice_catalog.default_settings.rate` suara Inggris Edge (+5%/+10%/+15%).
-- Itu keputusan owner yang belum diambil; ia terlihat di layar admin dan koefisien durasinya sudah
-- diukur pada baseline itu, jadi hari ini konsisten. Mengubahnya = keputusan produk, bukan perbaikan bug.

-- (a) buang `speed` dari lapisan warisan per-niche milik tenant
UPDATE tenant_configs tc
SET    tts_voice_settings = (
         SELECT jsonb_object_agg(kunci, isi - 'speed')
         FROM   jsonb_each(tc.tts_voice_settings) AS t(kunci, isi)
       )
WHERE  tc.tts_voice_settings IS NOT NULL
  AND  jsonb_typeof(tc.tts_voice_settings) = 'object'
  AND  EXISTS (SELECT 1 FROM jsonb_each(tc.tts_voice_settings) AS t(kunci, isi)
               WHERE jsonb_typeof(isi) = 'object' AND isi ? 'speed');

-- (b) laju bicara suara ElevenLabs & fal kembali ke laju alami
UPDATE voice_catalog
SET    default_settings = jsonb_set(coalesce(default_settings, '{}'::jsonb), '{speed}', '1.0'::jsonb, true)
WHERE  provider_key IN ('elevenlabs', 'fal')
  AND  coalesce((default_settings->>'speed')::numeric, 1.0) <> 1.0;

COMMENT ON COLUMN voice_catalog.default_settings IS
  'Setelan bawaan penyedia untuk suara ini (rate/speed/style/stability). LAJU BICARA hanya boleh dari sini — satu-satunya kenop yang terlihat admin. Aturan owner: ratio 1 = laju alami; nilai lain akan tercatat sebagai peringatan di log (0187).';
