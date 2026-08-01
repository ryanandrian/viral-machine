-- 0188 — Ambang rantai DURASI · NASKAH · SUARA jadi kenop yang bisa dilihat & diatur owner
--
-- MASALAH YANG DISELESAIKAN (diperiksa 2026-08-01)
-- Dua puluh sembilan ambang yang menentukan perilaku mesin hanya hidup sebagai variabel lingkungan
-- dengan angka bawaan di kode: batas audio-terpotong, cakupan naskah, jumlah putaran perbaikan,
-- ambang alarm akurasi, syarat minimum kalibrasi, batas waktu penyedia suara, dan seterusnya.
-- `.env` di server TIDAK MEMUAT SATU PUN — jadi semuanya berjalan dengan angka bawaan kode, tak
-- terlihat di layar mana pun, dan mengubahnya berarti menyunting kode lalu deploy ulang.
--
-- Itu pola yang sama persis dengan cacat yang baru dicabut hari ini: `voice_catalog.default_settings`
-- yang berisi angka tak terlihat selama berbulan-bulan sampai akhirnya ketahuan memperlambat suara 17%.
-- Angka yang tak terlihat tidak pernah diperiksa siapa pun.
--
-- BENTUK NILAI: sengaja BILANGAN BULAT dalam satuan yang wajar bagi manusia (persen · detik ·
-- milidetik · jumlah), bukan pecahan — supaya layar admin memakai kotak angka biasa dan owner tak
-- perlu memikirkan desimal. Kode mengubahnya kembali lewat `src/config/ambang.py`.
--
-- Angka di bawah = PERSIS angka bawaan yang selama ini berjalan. Migrasi ini TIDAK mengubah perilaku
-- apa pun; ia hanya memindahkan kendalinya ke tempat yang terlihat.

INSERT INTO app_config (key, value, description) VALUES
-- ── Mutu video jadi (QC pasca-render) ────────────────────────────────────────────────────────────
 ('qc_min_size_mb',            5,   'Ukuran berkas video minimum (MB). Di bawah ini video dianggap rusak/kosong dan TIDAK dipublikasikan.'),
 ('qc_max_duration_sec',       180, 'Batas atas durasi video yang diterima QC (detik). Hanya berlaku bila preset channel di bawah batas ini — video Regular tidak ikut dibatasi.'),
 ('qc_min_duration_sec',       3,   'Durasi video minimum (detik). Di bawah ini pasti render gagal.'),
 ('qc_min_clips',              6,   'Jumlah potongan visual minimum bila jumlah adegan tak diketahui.'),
 ('qc_require_audio',          1,   '1 = video WAJIB punya jalur suara (video bisu = gagal). 0 = tidak diperiksa.'),
 ('qc_aspect_tolerance_pct',   5,   'Toleransi rasio layar (%). Di luar ini video ditolak karena bentuknya salah untuk platform tujuan.'),
-- ── Suara ────────────────────────────────────────────────────────────────────────────────────────
 ('tts_potong_ambang_pct',     75,  'Audio yang lebih pendek dari sekian persen ramalan = narasi TERPUTUS → produksi dihentikan & diulang. Terukur terjadi 1 dari 73 render.'),
 ('tts_cakupan_min_pct',       85,  'Berapa persen naskah minimal yang harus benar-benar terucap menurut penanda dari penyedia suara. Di bawah ini = suara tak selesai dibuat.'),
 ('tts_timeout_dasar_sec',     180, 'Batas waktu dasar menunggu penyedia suara (detik). Penyedia yang menggantung tanpa batas waktu akan mematikan satu utas pekerja selamanya.'),
 ('tts_timeout_per_huruf_ms',  200, 'Tambahan batas waktu per huruf naskah (milidetik) — naskah panjang memang perlu lebih lama.'),
 ('tts_timeout_maks_sec',      900, 'Batas waktu tertinggi menunggu penyedia suara (detik), berapa pun panjang naskahnya.'),
-- ── Penulisan naskah ─────────────────────────────────────────────────────────────────────────────
 ('script_perbeat_trigger_pct', 80, 'Naskah yang panjangnya di bawah sekian persen batas bawah → ditulis ULANG per bagian (satu panggilan per adegan, lebih patuh).'),
 ('script_perbeat_min_rasio_pct', 85, 'Tiap bagian yang di bawah sekian persen jatahnya langsung diminta ditambah saat itu juga.'),
 ('script_perbeat_retry',      3,   'Berapa kali satu bagian dicoba ulang bila penyedia AI menolak sementara (kuota/jaringan).'),
 ('script_refit_rounds',       3,   'Berapa putaran maksimum model diminta merapatkan sendiri panjang naskahnya sebelum produksi berhenti jujur.'),
 ('script_refit_parse_retry',  2,   'Berapa kali jawaban AI yang formatnya rusak diminta ulang.'),
 ('script_length_tolerance_pct', 12, 'Toleransi panjang naskah (%) untuk channel TANPA preset durasi. Channel ber-preset memakai batas titik-tengah antar-preset, bukan persen.'),
-- ── Kalibrasi otomatis (mesin mengukur dirinya) ──────────────────────────────────────────────────
 ('pace_calib_min_n',          14,  'Berapa render nyata minimum sebelum sebuah suara boleh punya angka kalibrasi sendiri. Kurang dari ini = menebak.'),
 ('pace_calib_min_chars',      60,  'Naskah lebih pendek dari sekian huruf tidak dipakai mengkalibrasi (porsi jedanya tak wajar).'),
 ('pace_calib_min_fitur_n',    10,  'Sebuah tanda baca hanya dapat angkanya sendiri bila muncul di sekian naskah. Tanda yang JARANG menghasilkan angka yang tampak masuk akal tapi salah (em-dash pernah 1,137 dtk padahal 0,424).'),
 ('pace_calib_max_err_ms',     2500,'Bila kesalahan hasil kalibrasi melebihi ini (milidetik), angkanya DIBUANG dan mesin memakai angka bawaan — angka yang tak lebih baik tidak dipasang.'),
-- ── Alat ukur biaya jeda ─────────────────────────────────────────────────────────────────────────
 ('probe_min_teks',            4,   'Berapa teks alat ukur minimum yang harus berhasil sebelum biaya jeda sebuah suara dianggap terukur.'),
 ('probe_min_positif_pct',     75,  'Berapa persen teks yang harus menunjukkan tanda itu MENAMBAH waktu. Di bawah ini arah pengukurannya sendiri tidak konsisten.'),
 ('probe_maks_mad_ms',         100, 'Sebaran antar-teks maksimum (milidetik). Penyedia yang tak konsisten (ElevenLabs) menghasilkan sebaran besar — angkanya ditolak, bukan dipakai.'),
 ('probe_min_detik_ms',        50,  'Biaya jeda di bawah ini (milidetik) dianggap tak terbedakan dari derau.'),
 ('probe_ts_min_dasar',        30,  'Berapa jarak antar-kata TANPA tanda yang dibutuhkan sebagai pembanding, saat mengukur dari penanda waktu penyedia.'),
 ('probe_ts_min_tanda',        12,  'Berapa kemunculan sebuah tanda yang dibutuhkan saat mengukur dari penanda waktu penyedia.'),
-- ── Pemantauan akurasi ───────────────────────────────────────────────────────────────────────────
 ('drift_alarm_pct',           10,  'Bila rata-rata durasi video meleset lebih dari sekian persen, Anda dikabari lewat Telegram.'),
 ('drift_window_n',            30,  'Berapa video terakhir yang dinilai saat memeriksa akurasi durasi.'),
 ('drift_alarm_cooldown_h',    24,  'Jarak minimum antar-alarm akurasi durasi (jam), supaya tidak berdering berkali-kali sehari.'),
 ('beat_align_min_n',          10,  'Berapa sampel minimum sebelum bobot sebuah adegan disesuaikan ke kenyataan.'),
 ('beat_align_max_step_pct',   20,  'Seberapa jauh bobot adegan boleh bergeser dalam satu siklus (%). Geser halus, tak pernah melompat.')
ON CONFLICT (key) DO NOTHING;

INSERT INTO app_config (key, value, value_text, description) VALUES
 ('qc_aspect', 0, '9:16', 'Rasio layar yang diharapkan untuk video vertikal (lebar:tinggi). Video di luar rasio ini ditolak QC.')
ON CONFLICT (key) DO NOTHING;
