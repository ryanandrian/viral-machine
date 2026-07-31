-- 0184 — Sampel durasi WAJIB merekam setelan suara yang benar-benar dipakai
--
-- MASALAH YANG DISELESAIKAN (kesalahan paling mahal 2026-07-31)
-- Seluruh pengukuran durasi 29–31 Jul dilakukan pada baseline suara `-5%`, sementara produksi memakai
-- baseline lain. Selisihnya 15% pada laju bicara — cukup untuk membuat SETIAP angka hasil pengukuran
-- salah, dan pengukuran dua hari harus diulang dari nol. Tidak ada apa pun di sistem yang memberi tahu:
-- kolom `speed` bernilai 1,0 di kedua dunia, karena `speed` hanyalah PENGALI di atas baseline, bukan
-- setelan yang sesungguhnya dipakai.
--
-- Akibatnya bisa jauh lebih buruk daripada waktu terbuang: koefisien yang di-fit dari sampel dengan
-- baseline berbeda-beda akan tampak "terkalibrasi" (angka kesalahannya kecil di dalam sampelnya
-- sendiri) padahal salah untuk produksi. Itu kelas bug "kalibrasi yang percaya diri tapi salah".
--
-- YANG DIUBAH: satu kolom, boleh kosong.
--   • tts_delivery_samples.voice_rate — string setelan laju yang BENAR-BENAR dikirim ke penyedia suara
--     (mis. '+0%', '+15%'), diambil dari adaptor, bukan dihitung ulang.
--
-- KONSEKUENSI DI KODE: `pace_calibration` hanya memakai sampel yang `voice_rate`-nya SAMA dengan
-- baseline suara itu saat ini. Sampel dari baseline lain DIBUANG eksplisit + dilaporkan jumlahnya —
-- bukan dicampur diam-diam. Sampel lama (kolom kosong) juga dibuang: tak bisa diverifikasi asalnya.
--
-- Kosong = sampel itu tidak dipakai kalibrasi. Itu memang yang diinginkan: lebih baik menolak data
-- yang tak bisa dipastikan asalnya daripada menghasilkan angka yang tampak benar.

ALTER TABLE tts_delivery_samples
  ADD COLUMN IF NOT EXISTS voice_rate text;

COMMENT ON COLUMN tts_delivery_samples.voice_rate IS
  'Setelan laju yang BENAR-BENAR dikirim ke penyedia suara pada render ini (mis. +0%). Kalibrasi hanya memakai sampel yang setelannya sama dengan baseline suara saat ini — kosong = tidak dipakai (0184).';
