-- 0200 — PRATINJAU 1 GAMBAR DARI DNA (Niche Studio + Niche Library)
-- SSOT: SISA_KERJA_GO_LIVE.md [B32] T11.
--
-- ═══ MASALAH YANG DIJAWAB (pertanyaan owner 2026-08-15: "apa pantas dijual?") ═══
-- Satu-satunya cara mencocokkan gaya visual sebuah niche hari ini adalah **memproduksi VIDEO PENUH**:
-- ±4 menit dan ±Rp 1.500 sekali coba. Terukur pada sesi ini sendiri — enam putaran video hanya untuk
-- menyetel gaya, dan tiap putaran menunggu empat menit. Beban itu akan diwarisi SETIAP tenant yang
-- ingin nichenya terlihat seperti yang ia bayangkan.
-- Pratinjau 1 gambar = **±6 detik, ±Rp 250, nol video, nol kuota, nol jejak di stok konten.**
--
-- ⚠️ SYARAT MUTLAK YANG MEMBENTUK RANCANGAN INI:
-- pratinjau WAJIB memakai perakit prompt yang SAMA PERSIS dengan produksi (`_build_image_prompt` +
-- corong patri di `_generate_image`). Merakitnya ulang di layar = melahirkan KEBENARAN KEDUA yang
-- suatu hari berbeda dari produksi — persis kelas cacat yang [B32] tutup seharian ini (tiga jalur baca
-- DNA, dua tempat menghitung hal yang sama). Karena itu pratinjau berjalan lewat PEKERJA, memakai
-- kode produksi apa adanya, bukan lewat rute layar yang memanggil vendor sendiri.
--
-- Karena itu ia menumpang `direct_jobs` (antrean kerja yang sudah teruji) — bukan tabel baru:
--   • job_type 'preview_image'  → pekerja hanya membuat SATU gambar, tak menyentuh naskah/suara/render
--   • result_key                → kunci S3 gambar hasil, dibaca layar lewat tautan berjangka
-- Nol tabel baru · nol layanan baru · nol jalur baru.
--
-- REVERSIBLE: kembalikan CHECK ke 4 nilai lama + DROP COLUMN result_key.

ALTER TABLE direct_jobs DROP CONSTRAINT IF EXISTS direct_jobs_job_type_check;
ALTER TABLE direct_jobs ADD CONSTRAINT direct_jobs_job_type_check
  CHECK (job_type = ANY (ARRAY['test'::text, 'retry'::text, 'admin_test'::text,
                               'test_nopub'::text, 'preview_image'::text]));

-- Hasil pratinjau: kunci objek S3 (bukan URL) — layar meminta tautan berjangka saat menampilkan,
-- pola yang sama dengan video uji. NULL untuk seluruh jenis job lain.
ALTER TABLE direct_jobs ADD COLUMN IF NOT EXISTS result_key text;

COMMENT ON COLUMN direct_jobs.result_key IS
  'Kunci S3 hasil job yang bukan video (mis. gambar pratinjau DNA, job_type=preview_image). '
  'NULL untuk job produksi — hasilnya ada di production_runs.run_metadata.video_s3.';
