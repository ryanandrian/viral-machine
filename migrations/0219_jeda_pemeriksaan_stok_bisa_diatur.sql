-- 0219 — Jeda pemeriksaan stok video jadi kenop admin (kuota egress Supabase jebol 11-Sep).
--
-- KEJADIAN: proyek DIBLOKIR `402 exceed_egress_quota` — kuota gratis 5 GB, terpakai 9,55 GB.
-- Seluruh tenant berhenti produksi. Grafik dasbor RATA ±400 MB/hari sejak 18-Agu (bukan lonjakan
-- ⇒ pola loop, bukan ulah tenant).
--
-- AKAR: `producer.run_forever(idle_seconds=10)` = 8.640 putaran/hari, dan TIAP putaran menjalankan
-- `plan_and_submit` yang menarik seluruh channel aktif (19,3 KB) + ±7 panggilan per channel.
-- Statistik DB membuktikan: `content_inventory` 8,0 juta baca · `ai_providers` 6,4 juta (tabel
-- 9 BARIS). Database hanya 52 MB ⇒ yang boros FREKUENSI, bukan besar data. Stok video berubah
-- beberapa kali sehari, tapi diperiksa 8.640 kali sehari.
--
-- Nilai 300 dtk = 288 pemeriksaan/hari (30× lebih jarang). Aman: satu video butuh 8–15 menit
-- diproduksi dan target stok dihitung per HARI, jadi 5 menit masih 2–3× lebih cepat dari kebutuhan.
--
-- Antrean uji tenant (`drain_direct`) TIDAK diatur kenop ini — ia tetap diperiksa tiap putaran
-- (10 dtk, hanya 2,1 MB/hari) supaya tombol "Uji sekarang" tetap responsif.
--
-- Batas bawah 30 dtk DIPAKSA DI KODE (`max(30, …)`): nilai 0 membuat `time.sleep(0)` berputar tanpa
-- henti — CPU 100% dan egress justru MELEDAK. Satu salah ketik di panel cukup melumpuhkan server.

insert into app_config (key, value, description)
values (
  'producer_stock_interval_sec',
  300,
  'Jeda antar pemeriksaan stok video (detik). Mesin memeriksa apakah ada channel yang stok videonya '
  'kurang, lalu memproduksi penggantinya. Makin kecil = makin cepat stok terisi, tapi makin boros '
  'kuota transfer data Supabase. 300 detik (5 menit) sudah 2-3x lebih cepat dari laju pemakaian video. '
  'Nilai di bawah 30 otomatis dianggap 30 (angka 0 akan melumpuhkan server). '
  'TIDAK memengaruhi tombol "Uji sekarang" milik tenant — antrean uji tetap diperiksa tiap 10 detik.'
)
on conflict (key) do nothing;   -- idempoten: aman dijalankan ulang, nol timpa nilai yang sudah diubah admin
