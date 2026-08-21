-- 0205 — KATALOG BELAJAR: jejak karantina + nama model yang gagal (Batch B).
-- Rencana: /home/rad/.claude/plans/cozy-booping-shell.md · SSOT: AI_ERROR_MANAGEMENT §9b
--
-- ═══ PERSOALAN ═══
-- Mesin SUDAH membuktikan kematian model — 7 run ber-`error_class='model_unavailable'`, termasuk
-- `gemini-2.5-flash` (18-Agu). Tapi sinyal itu berhenti di `production_runs` + Telegram tenant.
-- NOL baris kode pernah menyentuh `ai_models` saat sebuah model terbukti mati (penulis `ai_models`
-- di seluruh src/ hanya: model_tester → cost_hint, price_sync → pricing).
-- Akibatnya: model yang TERBUKTI mati tetap `is_active=true`, tetap ditawarkan ke tenant BERIKUTNYA,
-- tetap lolos gerbang, tetap berlencana "✓ Teruji" dari uji bulan lalu. Abyss ID diam 24 hari.
--
-- ═══ KEBERATAN OWNER 21-Agu (mengikat) ═══
-- Rancangan semula: buktikan dengan memanggil vendor memakai kunci admin/Test Lab. DITOLAK owner —
-- itu "menghabiskan kredit saya diam-diam, dan biayanya cukup besar ke depannya".
-- ⇒ Karantina memakai bukti yang SUDAH ADA di tangan. NOL panggilan berbayar:
--     A (wajib) `dasar` = kode/teks-vendor       (bukan 404 telanjang — 404 bisa salah alamat KITA)
--     B1 kata GLOBAL di pesan vendor             (decommissioned / no longer available / deprecated…)
--     B2 ≥2 TENANT BERBEDA gagal pada model sama (dua kunci API berbeda ⇒ bukan soal akses akun)
--     B3 hilang dari umpan harga publik          (price_sync sudah menghitungnya tiap 24 jam)
-- A tanpa B ⇒ NOL karantina, alarm admin ber-bukti.
--
-- Diuji pada riwayat NYATA: `gemini-2.5-flash` gagal di 2 tenant berbeda ⇒ B2 MENYALA (gratis).
-- `gemini-flash-lite-latest` hanya 1 tenant ⇒ tidak dikarantina buta — alarm admin.
--
-- Kolom `production_runs.failed_model` WAJIB ada, kalau tidak B2 mustahil dihitung: hari ini yang
-- disimpan hanya `llm_provider`, sementara nama modelnya cuma hidup di teks bebas `error_message` —
-- padahal vendor SUDAH menyebutkannya persis.

begin;

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 1) Jejak karantina pada katalog. ADITIF — nol kolom lama berubah.
--    `is_active` TETAP satu-satunya saklar yang menentukan model ditawarkan atau tidak; dua kolom
--    ini hanya MENJELASKAN kenapa ia dimatikan, supaya admin tak menyalakannya kembali membuta.
-- ─────────────────────────────────────────────────────────────────────────────────────────────
alter table ai_models add column if not exists unavailable_since  timestamptz;
alter table ai_models add column if not exists unavailable_reason text;

comment on column ai_models.unavailable_since is
  'Kapan model ini dikarantina karena terbukti mati di vendor (NULL = tidak dikarantina). Ditulis mesin; dibersihkan admin saat menghidupkan kembali.';
comment on column ai_models.unavailable_reason is
  'Bukti yang memicu karantina (pesan vendor apa adanya + bukti B1/B2/B3). Ditulis mesin - CHANNEL_LOCK/AI_ERROR_MGMT §9b.';

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- 2) Nama model yang GAGAL pada tiap run — prasyarat bukti-silang antar-tenant (B2).
--    Sengaja TANPA foreign key ke `ai_models`: catatan riwayat harus tetap utuh walau baris
--    katalognya kelak dihapus/di-rename. (Ini catatan sejarah, bukan rujukan hidup.)
-- ─────────────────────────────────────────────────────────────────────────────────────────────
alter table production_runs add column if not exists failed_model text;

comment on column production_runs.failed_model is
  'model_key yang menyebabkan run ini gagal (vendor menyebutkannya). Dipakai bukti-silang antar-tenant untuk karantina - AI_ERROR_MGMT §9b. Tanpa FK: riwayat harus utuh walau katalog berubah.';

create index if not exists ix_pr_failed_model on production_runs (failed_model)
  where failed_model is not null;

commit;
