-- 0209 — layar TENANT boleh membaca cermin nilai-sah katalog (termasuk SATUAN HARGA per jenis).
--
-- KENAPA (23-Agu-2026). Layar Channel Setting menampilkan harga model yang tenant pilih, dan
-- satuannya DIKETIK ULANG di kode layar: `llm → /1jt token · tts → /1jt karakter · selain itu →
-- /gambar`. Cabang itu ditulis saat baru ada 3 jenis model; sejak model VIDEO lahir, harga model
-- video tampil sebagai "≈ Rp —/gambar" — salah, tanpa suara, berbulan-bulan.
--
-- Perbaikannya: satuan & labelnya dibaca dari cermin `catalog_valid_values` (sudah ada; diisi
-- registry KODE tiap startup service). Tabelnya ber-RLS tetapi NOL policy, jadi layar tenant tak
-- bisa membacanya — hanya panel admin (kunci service) yang bisa. Migrasi ini menambah izin BACA.
--
-- Aman: isinya kapabilitas MESIN (nama adapter, jenis model, satuan harga) — nol data tenant, nol
-- rahasia, nol harga. Pola izin SAMA dengan `ai_models_read` (baca untuk semua).
create policy catalog_valid_values_read on public.catalog_valid_values
  for select using (true);
