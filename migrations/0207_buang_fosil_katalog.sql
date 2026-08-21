-- 0207 — BUANG FOSIL KATALOG: tiga kolom yang tak dibaca & tak ditulis siapa pun.
-- SSOT: ARSITEKTUR_AI_PROVIDER_MODEL.md §9.4 · penjaga: tests/test_katalog_nol_fosil_nol_lapis_ganda.py
--
-- ═══ KENAPA INI BUG, BUKAN "BATAS" ═══
-- Definisi owner (mengikat): BUG = "sesuatu yang rusak, atau berpotensi merusak, termasuk FOSIL,
-- atau objek pada screen yang tidak berfungsi atau tidak terwiring, DATA YANG DIKUMPULKAN TAPI
-- TIDAK DIGUNAKAN". Ketiga kolom di bawah persis itu, dan sempat saya laporkan sebagai "batas" —
-- teguran owner 22-Agu benar: melabeli bug sebagai batas = meninggalkan bug.
--
-- ═══ TERUKUR SEBELUM DIBUANG (22-Agu, produksi) ═══
--   tts_profiles.has_word_timeframe  : NOL pembaca & NOL penulis di src/ dan apps/web/.
--       Lebih buruk dari mati — ia SUMBER KEBENARAN KEDUA untuk hal yang sama dengan `tts_class`,
--       dan nilainya memang cermin 1:1 (true↔timed, false↔fast_fallback) di keenam baris.
--       Mengubah satu tanpa yang lain = kerusakan yang menunggu terjadi. Yang DIPAKAI mesin
--       (`format_catalog.tts_class`) adalah `tts_class`; kolom ini tinggal jejak migrasi lama.
--   voice_catalog.pace_sample_n      : NOL pembaca, NOL penulis, dan 0 dari 44 baris terisi.
--   voice_catalog.pace_updated_at    : sama — 0 dari 44 baris terisi.
--       Kalibrasi tempo yang SUNGGUHAN hidup di tabel `tts_pace_calibration` (ditulis mesin,
--       ditampilkan read-only di panel). Dua kolom ini peninggalan rancangan sebelum tabel itu ada.
--
-- ═══ PAGAR ═══
-- Hanya tiga kolom ini. `tts_class` · `delivery_wps` · `pace_locked` · `preview_url` dan seluruh
-- kolom lain TIDAK disentuh — dikunci uji (`test_TIDAK_menyentuh_kolom_yang_HIDUP`).
-- Kalau kelak butuh lagi: tambahkan kembali lewat migrasi baru, JANGAN dihidupkan diam-diam.

begin;

alter table tts_profiles  drop column if exists has_word_timeframe;
alter table voice_catalog drop column if exists pace_sample_n;
alter table voice_catalog drop column if exists pace_updated_at;

commit;
