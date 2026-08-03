-- 0194 — Tabel antrean produksi: tutup dua celah LINTAS-TENANT + batasi perpanjangan mandiri
-- SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10e-3.
--
-- Ditemukan pada audit putaran ketiga (perintah owner "kalau masih menemukan bug, berarti audit
-- terakhir juga bisa miss"). Owner benar: dua celah ini lebih serius dari yang sudah ditutup.
--
-- ══ CELAH A — pekerjaan bisa DISAMARKAN sebagai pekerjaan admin ══════════════════════════════
-- Aturan lama hanya memeriksa "atas nama diri sendiri". Ia TIDAK memeriksa JENIS pekerjaan.
-- Sementara itu worker sengaja MELEWATI gerbang untuk jenis 'admin_test' (channel internal admin),
-- dan penghitung jatah masa coba hanya menghitung 'test'/'test_nopub'/'retry'.
-- Akibatnya tenant masa coba cukup menulis 'admin_test' untuk memproduksi TANPA BATAS: melewati
-- jatah DAN melewati pemeriksaan worker. TERBUKTI dengan penyisipan nyata (HTTP 201).
--
-- ══ CELAH B — produksi bisa dipicu di channel MILIK TENANT LAIN ══════════════════════════════
-- Aturan lama memeriksa `tenant_id = auth.uid()` tetapi TIDAK memeriksa bahwa channel yang ditunjuk
-- memang milik tenant itu. Worker mengambil channel dari job apa adanya lalu memakai kredensialnya.
-- Akibatnya tenant A bisa memicu produksi memakai kunci AI + koneksi YouTube milik tenant B —
-- membakar dompet B dan mengunggah ke kanal B. TERBUKTI dengan penyisipan nyata (HTTP 201).
--
-- KEJUJURAN: kedua celah ini LEBIH TUA dari gerbang uji — aturan `direct_jobs_tenant_insert` sudah
-- begitu sejak dibuat. Tetapi aturan itu baru saja saya ganti (0191) dan saya TIDAK memperbaikinya
-- saat itu. Data historis diperiksa: NOL pekerjaan pernah memakai channel milik orang lain, jadi
-- celah ini belum pernah dieksploitasi.
--
-- ══ CELAH C — perpanjangan masa coba mandiri bisa BERULANG tanpa batas ═══════════════════════
-- Link 1-klik di email nurture memperpanjang masa coba GRATIS. Kode lama hanya menolak bila status
-- sudah bukan 'trial_expired' — padahal masa coba itu lapse lagi beberapa hari kemudian, dan
-- tokennya berlaku 90 hari. Siklus lapse → klik → lapse → klik bisa diulang terus.
-- Owner: "JELAS-JELAS BUG YANG HARUS DITUTUP." Ditutup dengan penghitung + kenop batas.

-- ── A/B: aturan akses tabel antrean ──────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS direct_jobs_tenant_insert ON direct_jobs;
CREATE POLICY direct_jobs_tenant_insert ON direct_jobs
  FOR INSERT
  WITH CHECK (
    -- (1) atas nama diri sendiri
    tenant_id = (auth.uid())::text
    -- (2) HANYA jenis pekerjaan yang memang hak tenant. 'admin_test' milik jalur internal admin
    --     (kunci layanan) — bukan sesuatu yang boleh ditulis dari browser.
    AND job_type IN ('test', 'test_nopub', 'retry')
    -- (3) channel yang ditunjuk WAJIB miliknya sendiri — kredensial & kanal orang lain tak boleh
    --     dipakai. Subquery aman: `channels` punya indeks primer pada id.
    AND EXISTS (
      SELECT 1 FROM channels c
       WHERE c.id::text = direct_jobs.channel_id
         AND c.tenant_id = (auth.uid())::text
    )
    -- (4) gerbang uji
    AND coalesce((public.tenant_test_gate(tenant_id) ->> 'allowed')::boolean, false)
  );

COMMENT ON POLICY direct_jobs_tenant_insert ON direct_jobs IS
  'Tenant boleh mengantre pekerjaan HANYA: atas namanya sendiri · jenis yang jadi haknya '
  '(test/test_nopub/retry — bukan admin_test) · pada channel MILIKNYA · dan bila gerbang uji '
  'mengizinkan. Kunci layanan (API/worker) melewati aturan ini — pemeriksaannya di kode masing-masing.';

-- ── C: perpanjangan masa coba mandiri ────────────────────────────────────────────────────────────
ALTER TABLE tenant_configs ADD COLUMN IF NOT EXISTS trial_self_extends integer NOT NULL DEFAULT 0;

COMMENT ON COLUMN tenant_configs.trial_self_extends IS
  'Berapa kali tenant memperpanjang masa cobanya SENDIRI lewat link 1-klik di email nurture. '
  'Dibatasi kenop app_config.nurture_self_extend_max. Perpanjangan oleh ADMIN tidak menambah angka '
  'ini — admin memang berwenang memperpanjang berkali-kali.';

INSERT INTO app_config (key, value, description) VALUES
 ('nurture_self_extend_max', 1,
  'Berapa kali tenant boleh memperpanjang masa cobanya SENDIRI lewat link 1-klik di email. '
  'Melebihi ini, link mengarahkan ke halaman pembayaran. 0 = tenant tidak boleh memperpanjang '
  'sendiri sama sekali (hanya admin yang bisa, dari layar Tenant).')
ON CONFLICT (key) DO NOTHING;
