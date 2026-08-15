-- 0199 — TIGA TABEL KATALOG BISA DITULIS SIAPA SAJA TANPA LOGIN → DIKUNCI
-- SSOT: SISA_KERJA_GO_LIVE.md [B32] T2.
--
-- ═══ LUBANG (dibuktikan 2026-08-15 dengan kunci publik yang dipegang SETIAP browser) ═══
-- Uji aman (menulis nilai yang SAMA PERSIS dengan isinya, jadi nol data berubah):
--     UPDATE niches SET name = <nilai yang sudah ada> WHERE niche_id = 'sunnah_harian';
-- Server MENERIMANYA dan mengembalikan 1 baris. Artinya siapa pun di internet — tanpa akun, tanpa
-- login — bisa menulis ulang DNA niche mana pun, mematikannya, atau merusak seluruh katalog.
-- Sapuan 19 tabel: yang terbuka HANYA `niches`, `moods`, `music_library`. Seluruh data tenant
-- (channels · tenant_configs · videos · production_runs · kunci AI · akun YouTube · direct_jobs ·
-- niche_requests · admin_audit · content_inventory) TERKUNCI RAPAT — jadi ini bukan kebocoran
-- menyeluruh, melainkan tiga tabel katalog yang RLS-nya memang tak pernah dinyalakan (migr 0071
-- menuliskannya sendiri: *"niches RLS tetap OFF (tak diubah) → nol-risiko mesin"*), sementara izin
-- tulis untuk peran publik tak pernah dicabut.
--
-- ⚠️ JANGAN TERTUKAR dengan celah yang owner SENGAJA TUNDA 30-Jun (memory `decisions_niche_model`):
-- di sana `authenticated` bisa UPDATE `channels.niche` lewat REST — butuh LOGIN dan terbatas pada
-- baris MILIK SENDIRI (RLS channels aktif). Keputusan owner *"jangan over-engineer sekarang"* untuk
-- celah itu TIDAK dibatalkan migrasi ini dan `channels` tidak disentuh sama sekali.
--
-- ═══ YANG DIJAGA AGAR TIDAK RUSAK ═══
-- 1. MESIN memakai `service_role` (diverifikasi: peran kunci `.env` = service_role) → RLS TIDAK
--    berlaku baginya. Nol perubahan perilaku produksi.
-- 2. Seluruh route API admin & Niche Studio memakai `createAdminClient()` (service_role) → tak terpengaruh.
-- 3. Yang membaca dari BROWSER (kunci publik + sesi tenant) hanya 4 titik — semuanya dicakup policy di
--    bawah: `(app)/niches` · `(app)/channels/new` · `(app)/channels/[id]` · `components/niche-dna-editor`.
-- 4. Seluruh RPC yang menyentuh `niches` (`set_channel_niche`, `channel_readiness`, tulis channel) =
--    SECURITY DEFINER → berjalan sebagai pemilik fungsi, tidak dihalangi RLS.
-- 5. Predikat SELECT `niches` di bawah SENGAJA menyalin PERSIS penyaring yang selama ini dipakai layar
--    (`(app)/niches/page.tsx`): `exclusive_to = saya` ATAU `(exclusive_to IS NULL AND is_active AND
--    access_type='public')`. Jadi yang berubah hanya SIAPA yang menegakkannya — dari browser (bisa
--    dilewati) pindah ke database (tidak bisa) — bukan APA yang tampil.
--    Efek samping yang disengaja: DNA niche PRIVAT tenant lain berhenti terkirim ke browser.
--
-- REVERSIBLE: DROP POLICY + DISABLE ROW LEVEL SECURITY pada ketiga tabel mengembalikan keadaan lama.

-- ── niches ────────────────────────────────────────────────────────────────────────────────────────
ALTER TABLE niches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS niches_baca_katalog ON niches;
CREATE POLICY niches_baca_katalog ON niches
  FOR SELECT
  USING (
    -- `exclusive_to` bertipe TEXT (sama seperti `channels.tenant_id`), `auth.uid()` bertipe UUID →
    -- cast WAJIB; tanpa itu Postgres menolak: "operator does not exist: text = uuid".
    exclusive_to = auth.uid()::text                              -- niche milik tenant ini (aktif atau belum)
    OR (exclusive_to IS NULL AND is_active = true AND access_type = 'public')
  );
-- Tidak ada policy INSERT/UPDATE/DELETE → tulis tertutup untuk anon & authenticated.
-- Sabuk kedua (kalau kelak ada yang menambah policy tulis tanpa sadar):
REVOKE INSERT, UPDATE, DELETE ON niches FROM anon, authenticated;

-- ── moods ─────────────────────────────────────────────────────────────────────────────────────────
-- Katalog mood musik: dibaca editor DNA (admin & tenant Business) untuk memilih urutan mood.
ALTER TABLE moods ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS moods_baca ON moods;
CREATE POLICY moods_baca ON moods FOR SELECT TO authenticated USING (true);
REVOKE INSERT, UPDATE, DELETE ON moods FROM anon, authenticated;

-- ── music_library ─────────────────────────────────────────────────────────────────────────────────
-- Daftar lagu: dibaca editor DNA untuk menampilkan "X track tersedia" + pemilih lagu mode `fixed`.
-- Berkas audionya sendiri TIDAK ada di sini (hanya `object_key`; unduhannya lewat presign ber-otentikasi).
ALTER TABLE music_library ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS music_library_baca ON music_library;
CREATE POLICY music_library_baca ON music_library FOR SELECT TO authenticated USING (true);
REVOKE INSERT, UPDATE, DELETE ON music_library FROM anon, authenticated;
