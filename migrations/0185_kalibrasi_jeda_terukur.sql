-- 0185 — Biaya jeda DIUKUR LANGSUNG, bukan disimpulkan dari regresi
--
-- MASALAH YANG DISELESAIKAN (terukur 2026-08-01)
-- Koefisien jeda (koma, em-dash, elipsis, akhir-kalimat) selama ini diturunkan dengan regresi dari
-- naskah produksi. Regresi harus memisahkan enam pengaruh sekaligus dari data yang tidak dirancang
-- untuk itu — dan keempat tanda jeda itu bergerak bersama panjang naskah. Hasilnya angka yang tampak
-- masuk akal tapi salah:
--
--   id-ID-ArdiNeural   em-dash  regresi 1,137 dtk   ·  TERUKUR LANGSUNG 0,424 dtk   (2,7× terlalu besar)
--   id-ID-GadisNeural  em-dash  regresi 1,262 dtk   ·  TERUKUR LANGSUNG 0,400 dtk   (3,2× terlalu besar)
--   angka bawaan       elipsis          1,376 dtk   ·  TERUKUR LANGSUNG 0,156/0,288 (6–9× terlalu besar)
--   angka bawaan       koma             0,221 dtk   ·  TERUKUR LANGSUNG 0,396/0,388 (1,8× terlalu KECIL)
--
-- Angka koma itu dipakai SEMUA suara yang belum terkalibrasi (21 suara ElevenLabs/fal). Pada naskah
-- 90 detik dengan 25 koma, selisih 0,17 dtk/koma = 4,3 detik meleset — cukup untuk melempar video ke
-- luar batas sah.
--
-- CARA UKUR YANG TAK BISA SALAH: huruf dibuat IDENTIK, hanya tandanya berbeda.
--     v0       A B C D.            (tanpa tanda di 3 sambungan)
--     koma     A, B, C, D.
--     em-dash  A — B — C — D.
--     elipsis  A... B... C... D.
--     titik    A. B. C. D.
-- Biaya satu tanda = (durasi versi bertanda − durasi v0) ÷ jumlah tanda. Karena hurufnya identik, apa
-- pun yang tersisa dari selisih itu HANYA milik tandanya — tak ada yang bisa tercampur. Terbukti rapat:
-- rentang antar-6-teks hanya ±0,05 dtk.
--
-- Dibuktikan lebih akurat pada 36 render yang sama (leave-one-out, di rentang preset produksi):
--     Ardi   salah rata 1,47 → 1,18 dtk · terburuk 5,33 → 3,76 dtk
--     Gadis  salah rata 1,82 → 1,58 dtk · terburuk 5,89 → 4,61 dtk
--
-- YANG DIUBAH
--   1. tts_pace_calibration.pause_source — menandai baris yang biaya jedanya DIUKUR. Kalibrasi berkala
--      lalu MEMATOK angka jeda itu dan hanya mem-fit huruf+angka dari sisanya (2 parameter dari puluhan
--      titik = jauh lebih stabil daripada 6). Tanpa penanda ini, kalibrasi berikutnya akan menimpa
--      angka terukur dengan angka regresi lagi — dan ranjaunya kembali sendiri.
--   2. duration_probe_texts — teks alat ukur, DI DB bukan di kode: mengganti teks berarti mengganti
--      alat ukur, jadi ia harus terlihat dan bisa ditambah (bahasa baru) tanpa developer.

ALTER TABLE tts_pace_calibration
  ADD COLUMN IF NOT EXISTS pause_source     text,
  ADD COLUMN IF NOT EXISTS pause_measured_at timestamptz;

DO $$ BEGIN
  ALTER TABLE tts_pace_calibration
    ADD CONSTRAINT tts_pace_calibration_pause_source_chk
    CHECK (pause_source IS NULL OR pause_source IN ('measured', 'fitted'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMENT ON COLUMN tts_pace_calibration.pause_source IS
  'measured = biaya jeda DIUKUR dengan pasangan teks terkontrol (huruf identik, hanya tandanya beda) → kalibrasi berkala MEMATOKNYA dan hanya mem-fit huruf+angka. fitted = hasil regresi biasa. NULL = belum ada info (0185).';
COMMENT ON COLUMN tts_pace_calibration.pause_measured_at IS
  'Kapan biaya jeda diukur langsung. Kosong bila pause_source bukan measured (0185).';

-- ── Teks alat ukur (instrumen, bukan konten bisnis) ──────────────────────────────────────────────
-- Tiap baris = satu teks dasar berisi 4 klausa (→ 3 sambungan yang bisa disisipi tanda). Klausanya
-- SENGAJA tanpa angka dan tanpa tanda baca lain, supaya selisih durasi hanya milik tanda yang diuji.
CREATE TABLE IF NOT EXISTS duration_probe_texts (
  id         bigserial PRIMARY KEY,
  lang       text    NOT NULL,
  idx        int     NOT NULL,
  clauses    jsonb   NOT NULL,
  is_active  boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (lang, idx)
);

COMMENT ON TABLE duration_probe_texts IS
  'ALAT UKUR biaya jeda per tanda baca (0185). Tiap baris = 4 klausa tanpa angka/tanda; mesin menyusunnya jadi 5 versi ber-huruf IDENTIK (tanpa tanda / koma / em-dash / elipsis / titik) lalu mengukur selisih durasinya. Mengubah isi tabel ini = mengubah alat ukur.';
COMMENT ON COLUMN duration_probe_texts.lang IS
  'Awalan bahasa suara yang diukur (mis. id, en). Suara en-US tidak boleh diukur dengan teks Indonesia — lajunya beda.';

INSERT INTO duration_probe_texts (lang, idx, clauses) VALUES
 ('id', 1, '["Kapal itu menghilang di tengah badai","tak ada satu pun awak yang kembali","puing-puingnya baru ditemukan bertahun kemudian","dan penyebabnya tetap gelap sampai hari ini"]'),
 ('id', 2, '["Kota tua itu ditinggalkan penduduknya","rumah-rumahnya masih berdiri utuh","meja makan pun masih tertata rapi","seolah semua orang pergi dalam satu malam"]'),
 ('id', 3, '["Ilmuwan itu bekerja sendiri selama delapan tahun","catatannya menumpuk hingga ke langit-langit","tak seorang pun percaya temuannya waktu itu","hari ini seluruh dunia memakai hasilnya"]'),
 ('id', 4, '["Suara aneh terdengar dari dasar laut","alat perekam menangkapnya berulang kali","para ahli berdebat panjang tentang asalnya","sampai sekarang belum ada jawaban pasti"]'),
 ('id', 5, '["Sebuah pintu ditemukan di balik dinding","di belakangnya ada ruangan yang tak tercatat","isinya hanya kursi tua dan satu buku catatan","tulisan di dalamnya tak bisa dibaca siapa pun"]'),
 ('id', 6, '["Pesawat itu mengudara pada pagi yang cerah","kontak radionya hilang setelah dua jam","pencarian dilakukan di area seluas ribuan mil","tak sepotong logam pun pernah ditemukan"]'),
 ('en', 1, '["The ship vanished in the middle of the storm","not a single crew member ever came back","its wreckage surfaced only many years later","and the cause remains unexplained to this day"]'),
 ('en', 2, '["The old town was abandoned by its people","the houses are somehow still standing","dinner tables remain set and untouched","as if everyone left on the very same night"]'),
 ('en', 3, '["That scientist worked alone for eight long years","his notes piled up all the way to the ceiling","nobody believed a word of his findings then","today the entire world depends on his work"]'),
 ('en', 4, '["A strange sound came from the ocean floor","recording stations captured it again and again","experts argued for decades about its origin","and there is still no confirmed answer"]'),
 ('en', 5, '["A hidden door was found behind the wall","behind it lay a room on no floor plan","inside were one old chair and a single notebook","the writing in it cannot be read by anyone"]'),
 ('en', 6, '["The aircraft took off on a clear bright morning","radio contact was lost after only two hours","the search covered thousands of square miles","not one piece of metal was ever recovered"]')
ON CONFLICT (lang, idx) DO NOTHING;
