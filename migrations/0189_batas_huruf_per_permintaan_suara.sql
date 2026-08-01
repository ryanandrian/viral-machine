-- 0189 — Batas huruf per permintaan suara, PER PENYEDIA
--
-- Melaksanakan desain yang SUDAH DIKETOK di `CONTENT_CATEGORY_ARCHITECTURE.md §7h`:
--   "+kolom `tts_profiles.max_chars_per_request` (fakta 19-Jul: kolom belum ada; nilai per vendor
--    diisi dari dokumentasi resmi saat build)"
--
-- MASALAH YANG DISELESAIKAN
-- Pemotongan naskah panjang (video Regular 2–12 menit) memakai SATU angka untuk semua penyedia. Aman
-- hari ini karena angkanya konservatif, tapi bukan jawaban yang benar: tiap penyedia punya batasnya
-- sendiri, dan katalog penyedia akan terus bertambah (arahan owner 2026-08-01: perbaikan harus GENERAL,
-- bukan per-vendor). Penyedia baru dengan batas LEBIH KECIL akan gagal, dan yang batasnya lebih besar
-- dipecah lebih banyak dari yang perlu — tiap potongan tambahan adalah satu permintaan berbayar lagi.
--
-- CARA MENGISI (aturan §7h): HANYA dari dokumentasi resmi vendor. Yang belum terverifikasi DIBIARKAN
-- KOSONG → memakai kenop global `app_config.tts_chunk_maks_huruf` yang konservatif dan terbukti aman.
-- Mengarang angka di sini berarti produksi gagal di tengah naskah panjang tanpa sebab yang terlihat.
--
--   openai_tts  4096  — batas keras terdokumentasi OpenAI Speech API (input.max_length)
--   elevenlabs  5000  — batas terdokumentasi model standar ElevenLabs
--   fal         5000  — meneruskan model ElevenLabs yang sama
--   edge_tts    KOSONG — tak ada batas huruf resmi (aliran websocket); yang membatasi justru risiko
--                        menggantung, dan itu diurus batas waktu + kenop global
--   gemini      KOSONG — belum diverifikasi dari dokumentasi resmi
--   groq        KOSONG — belum diverifikasi dari dokumentasi resmi

ALTER TABLE tts_profiles
  ADD COLUMN IF NOT EXISTS max_chars_per_request integer;

COMMENT ON COLUMN tts_profiles.max_chars_per_request IS
  'Batas huruf SATU permintaan ke penyedia ini, dari dokumentasi RESMI vendor. Naskah lebih panjang dipotong di batas kalimat. KOSONG = pakai kenop global app_config.tts_chunk_maks_huruf (konservatif). Jangan diisi dengan angka karangan: salah isi = produksi gagal di tengah naskah panjang (0189).';

UPDATE tts_profiles SET max_chars_per_request = 4096 WHERE provider_key = 'openai_tts' AND max_chars_per_request IS NULL;
UPDATE tts_profiles SET max_chars_per_request = 5000 WHERE provider_key IN ('elevenlabs', 'fal') AND max_chars_per_request IS NULL;
