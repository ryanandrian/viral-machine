"""Klaim `reason_codes` analis AI WAJIB benar terhadap dosirnya — mekanik MENGADILI.

SSOT: `PROGRAM_BUKTI_KECERDASAN.md` §6c HUKUM DESAIN #1 —
  *"Fakta & penalaran dipisah mati: mekanik MENGUKUR → LLM MEMUTUSKAN → mekanik MENGADILI.
    LLM tak pernah menilai dirinya sendiri (LLM pandai berdongeng dari derau)."*
dan #4 — *"Hakim tertinggi = Kurva F0 (bukan klaim LLM, bukan klaim Claude)."*

MASALAH YANG DIJAGA (terukur 2026-08-04 dari 3 siklus BAYANGAN nyata di produksi)
Hukum desain di atas TERTULIS sejak 18-Jul tapi **tak pernah ditegakkan kode**: `validate_decisions`
memeriksa BENTUK keputusan, sedangkan `reason_codes` hanya dicek "string tidak kosong" — ISINYA tak
pernah diadili. (Pola yang sama pernah terjadi pada aturan anti-komisi-diri agen: "hanya tertulis, TAK
ditegakkan di kode", diperbaiki 19-Jul.)

Hasil audit 3 siklus (18-Jul · 26-Jul · 2-Agu) di channel RAD The Explorer:
  • 3 klaim perbandingan BENAR   (`universe_mysteries.views_per_video` tertinggi — cocok dosir)
  • 3 klaim perbandingan SALAH   — kesalahan yang SAMA, terulang setiap siklus:
      `per_niche.fun_facts.retention_avg=60.0 higher than dark_history`
      padahal dosir yang ANALIS SENDIRI BACA mencatat `dark_history.retention_avg=69.2`.
Angka dibaca PERSIS BENAR; yang salah PERBANDINGANNYA — lalu dipakai membenarkan arahan produksi
"perbanyak fun_facts", padahal dark_history justru yang retensinya tertinggi.

DAMPAK BILA A2 DIKETOK TANPA INI: arahan berbasis perbandingan palsu masuk produksi → tenant menerima
konten lebih LEMAH, nol jejak sebabnya. Mode bayangan menahannya selama 3 minggu (desain bekerja).

SAMPEL DI UJI INI = ANGKA ASLI dari `channel_decisions.dossier` produksi (bukan karangan — pelajaran
`AI_ERROR_MANAGEMENT_ARCHITECTURE.md` §11 04-Agu: temuan dari sampel karangan = rantai bug tanpa ujung).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence.channel_analyst import (  # noqa: E402
    validate_decisions, verifikasi_klaim_reason_codes,
)

# ── DOSIR ASLI produksi, siklus 2026-08-02 (channel RAD The Explorer) ────────
DOSIR_NYATA = {
    "per_niche": {
        "fun_facts":          {"videos": 45, "retention_avg": 60.0, "subs_per_video": 1.11, "views_per_video": 200.1},
        "dark_history":       {"videos": 61, "retention_avg": 69.2, "subs_per_video": 0.30, "views_per_video": 94.6},
        "ocean_mysteries":    {"videos": 45, "retention_avg": 56.8, "subs_per_video": 0.69, "views_per_video": 254.3},
        "universe_mysteries": {"videos": 61, "retention_avg": 65.1, "subs_per_video": 1.05, "views_per_video": 306.8},
    },
}

CTX = {"niche_mode": "fixed", "niche_pool": []}


def _keputusan(reason_codes):
    """Satu keputusan sah-bentuk; hanya reason_codes yang berubah antar-kasus."""
    return [{
        "type": "topic_direction",
        "detail": {"directive": "Fokus ke niche berperforma terbaik."},
        "prediction": {"metric": "views_per_video", "direction": "up", "horizon_days": 30},
        "reason_codes": reason_codes,
    }]


class TestKlaimPalsuDitolak(unittest.TestCase):

    def test_kasus_NYATA_perbandingan_terbalik_DITOLAK(self):
        """Kesalahan asli yang terulang 3 siklus di produksi."""
        ok, err = verifikasi_klaim_reason_codes(
            _keputusan(["per_niche.fun_facts.retention_avg=60.0 higher than dark_history"]), DOSIR_NYATA)
        self.assertFalse(ok, "perbandingan terbalik LOLOS — hukum desain §6c.1 tak ditegakkan")
        self.assertIn("BUKAN higher than", err)
        self.assertIn("69.2", err, "pesan tak menyebut angka pembanding → analis tak bisa memperbaiki diri")

    def test_kasus_NYATA_klaim_benar_LOLOS(self):
        """Regresi terpenting: klaim yang BENAR tak boleh ikut ditolak (kalau ikut ditolak, seluruh
        lapis kecerdasan mati dan itu bug baru yang jauh lebih parah)."""
        ok, err = verifikasi_klaim_reason_codes(
            _keputusan(["per_niche.universe_mysteries.views_per_video=306.8 highest"]), DOSIR_NYATA)
        self.assertTrue(ok, f"klaim BENAR ikut ditolak: {err}")

    def test_angka_dikarang_DITOLAK(self):
        """Halusinasi angka: dosir 200.1, analis menulis 999."""
        ok, err = verifikasi_klaim_reason_codes(
            _keputusan(["per_niche.fun_facts.retention_avg=999 higher than dark_history"]), DOSIR_NYATA)
        self.assertFalse(ok)
        self.assertIn("mengarang angka", err)

    def test_klaim_tertinggi_padahal_bukan_DITOLAK(self):
        ok, err = verifikasi_klaim_reason_codes(
            _keputusan(["per_niche.fun_facts.views_per_video=200.1 highest"]), DOSIR_NYATA)
        self.assertFalse(ok)
        self.assertIn("BUKAN highest", err)

    def test_klaim_lower_than_yang_benar_LOLOS(self):
        ok, err = verifikasi_klaim_reason_codes(
            _keputusan(["per_niche.dark_history.views_per_video=94.6 lower than fun_facts"]), DOSIR_NYATA)
        self.assertTrue(ok, f"klaim 'lower than' yang benar ikut ditolak: {err}")


class TestYangTakTerukurDILEWATI(unittest.TestCase):
    """DISIPLIN ANTI-BUG-BARU: hanya tolak yang TERBUKTI salah.

    Menolak karena parser kita tak paham = membuang keputusan sah = bug baru yang lebih parah
    daripada masalah aslinya. Kasus di bawah SEMUANYA ada di produksi atau sangat mungkin muncul.
    """

    def test_pembanding_bukan_kunci_dosir_dilewati(self):
        """Kasus NYATA siklus 18-Jul: 'higher than average' — 'average' bukan kunci dosir."""
        ok, err = verifikasi_klaim_reason_codes(
            _keputusan(["content_type_perf.mystery.avg_views=177 higher than average"]), DOSIR_NYATA)
        self.assertTrue(ok, f"klaim tak terukur ikut ditolak: {err}")

    def test_jalur_tak_ada_di_dosir_dilewati(self):
        ok, _ = verifikasi_klaim_reason_codes(
            _keputusan(["per_niche.niche_yang_tak_ada.retention_avg=50 higher than fun_facts"]), DOSIR_NYATA)
        self.assertTrue(ok)

    def test_kalimat_bebas_dilewati(self):
        ok, _ = verifikasi_klaim_reason_codes(
            _keputusan(["retensi fun_facts terlihat menjanjikan menurut analisis"]), DOSIR_NYATA)
        self.assertTrue(ok)

    def test_dosir_kosong_atau_bentuk_asing_tidak_meledak(self):
        for dos in ({}, {"per_niche": None}, {"per_niche": {"x": "bukan dict"}}):
            ok, _ = verifikasi_klaim_reason_codes(
                _keputusan(["per_niche.fun_facts.retention_avg=60.0 highest"]), dos)
            self.assertTrue(ok, "dosir tak lengkap membuat keputusan sah ditolak")

    def test_toleransi_pembulatan_tidak_dianggap_halusinasi(self):
        """Dosir membulatkan 1 desimal. Beda 0,1 = pembulatan, BUKAN karangan — kalau ini dianggap
        halusinasi, hampir semua keputusan sah akan ditolak."""
        ok, err = verifikasi_klaim_reason_codes(
            _keputusan(["per_niche.fun_facts.retention_avg=60.1 higher than ocean_mysteries"]), DOSIR_NYATA)
        self.assertTrue(ok, f"beda pembulatan dianggap halusinasi: {err}")


class TestDuaLapisTetapTerpisah(unittest.TestCase):
    """Validator BENTUK dan validator ISI harus tetap dua fungsi berbeda: bentuk salah tak boleh
    dilaporkan sebagai 'klaim bohong' (menyesatkan yang membaca alasan penolakan), dan sebaliknya."""

    def test_bentuk_salah_ditangkap_validator_bentuk(self):
        ok, err = validate_decisions([{"type": "tak_ada_di_menu", "detail": {}}], CTX)
        self.assertFalse(ok)
        self.assertIn("di luar menu", err)

    def test_bentuk_benar_isi_bohong_lolos_lapis1_ditangkap_lapis2(self):
        dec = _keputusan(["per_niche.fun_facts.retention_avg=60.0 higher than dark_history"])
        ok1, _ = validate_decisions(dec, CTX)
        self.assertTrue(ok1, "lapis bentuk seharusnya LOLOS — itu sebabnya lapis 2 dibutuhkan")
        ok2, _ = verifikasi_klaim_reason_codes(dec, DOSIR_NYATA)
        self.assertFalse(ok2, "lapis 2 tak menangkap klaim bohong yang lolos lapis 1")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestSpecMasihMemuatHukumnya(unittest.TestCase):
    """DOKUMEN ↔ KODE. `PROGRAM_BUKTI_KECERDASAN.md` sebelumnya termasuk dokumen TANPA penjaga —
    dan seluruh insiden A1b lahir justru dari hukum yang tertulis di dokumen tapi tak ditegakkan kode.
    Kalau hukumnya dicabut dari dokumen sementara kodenya tetap (atau sebaliknya), dokumen berhenti
    menjelaskan perilaku sistem. Owner 04-Agu: *"buat apa file MD dibuat? pajangan?"*
    """

    SPEC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "PROGRAM_BUKTI_KECERDASAN.md")

    def _teks(self):
        return open(self.SPEC, encoding="utf-8").read()

    def test_hukum_desain_mekanik_mengadili_masih_tertulis(self):
        t = self._teks()
        self.assertIn("mekanik MENGADILI", t,
                      "§6c.1 (mekanik MENGADILI) hilang dari SPEC — dasar keberadaan pemeriksa ini")
        self.assertIn("LLM tak pernah menilai dirinya sendiri", t)

    def test_temuan_a1b_terdokumentasi_dengan_angkanya(self):
        """Angka temuan wajib tetap tercatat: sesi berikutnya harus tahu analis PERNAH salah 3 dari 6,
        supaya tidak mengetok A2 dengan asumsi otaknya sudah tepercaya."""
        t = self._teks()
        self.assertIn("A1b", t, "baris A1b hilang dari tracker §5")
        self.assertRegex(t, r"fun_facts\.retention_avg=60\.0 higher than dark_history",
                         "sampel kesalahan NYATA hilang dari dokumen")
        self.assertIn("69.2", t, "angka pembanding dosir hilang — temuan jadi tak bisa diverifikasi")

    def test_peringatan_a2_masih_ada(self):
        """Peringatan 'jangan ketok A2 sebelum siklus baru LOLOS' = pagar keputusan owner.
        Hilang = owner bisa mengetok A2 tanpa tahu otaknya pernah salah sistematis."""
        t = self._teks()
        self.assertRegex(t, r"[Jj]angan ketok A2",
                         "peringatan A2 hilang dari SPEC — pagar keputusan owner lenyap")
