"""
Uji regresi PERMANEN — REM DARURAT: simpan sebabnya & katakan apa artinya [B25].
SSOT: AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8a (celah yang ditutup) + §9 (kontrak tampilan per-kelas).

Jalankan:  python -m unittest tests.test_pemulihan_channel

MASALAH YANG DIJAGA AGAR TAK KEMBALI
Saat rem darurat menyala, sistem SUDAH tahu kelas errornya — ia membacanya justru untuk memutuskan
mengerem cepat — lalu MEMBUANGNYA. Yang tersimpan hanya "3x produksi beruntun gagal/bermasalah",
sehingga layar & Telegram cuma bisa menganjurkan tebakan. Tenant tak pernah tahu pertanyaan yang
paling menentukan: APAKAH INI PULIH SENDIRI? Satu channel tenant BERBAYAR karena itu mati ±44 jam
menunggu sesuatu yang sudah pulih sendiri keesokan harinya.

Yang dijaga:
  A. `_pause_channel` menyimpan `production_paused_class` — untuk KEDUA cabang (rem-cepat & 3-gagal).
  B. Alasan yang tersimpan memuat pesan manusiawi dari kegagalan terakhir, bukan kalimat generik saja.
  C. Telegram memberi anjuran BERBEDA untuk kelas yang pulih-sendiri vs yang butuh tindakan.
  D. ANTI-DRIFT: `SELF_HEALING` (kode) ↔ kolom "Pulih sendiri?" (dokumen) ↔ resep layar (FE).
     Tiga tempat, satu kebenaran — kalau salah satu bergeser, uji ini merah.
"""
import os
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import FAST_FAIL, SELF_HEALING, ErrorClass  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOK = os.path.join(AKAR, "AI_ERROR_MANAGEMENT_ARCHITECTURE.md")
FE_PANEL = os.path.join(AKAR, "apps", "web", "src", "components", "pemulihan-channel.tsx")


def _baca(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Stub Supabase minimal: cukup untuk menangkap payload update ke `channels` ────────────────────
class _Tabel:
    def __init__(self, sink):
        self._sink = sink
        self._upd = None

    def update(self, payload):
        self._upd = payload
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        if self._upd is not None:
            self._sink.append(self._upd)
        class R:  # noqa: N801
            data = []
        return R()


class FakeSB:
    def __init__(self):
        self.tulisan = []

    def table(self, _nama):
        return _Tabel(self.tulisan)


class TestRemMenyimpanSebabnya(unittest.TestCase):
    """A — kelas error berhenti dibuang."""

    def _pause(self, kelas):
        from src.orchestrator import producer
        sb = FakeSB()
        producer._pause_channel(sb, {"id": "C1"}, "alasan apa pun", error_class=kelas)
        return sb.tulisan[0]

    def test_kelas_tersimpan(self):
        for kelas in ErrorClass:
            with self.subTest(kelas=kelas.value):
                self.assertEqual(self._pause(kelas.value)["production_paused_class"], kelas.value)

    def test_kelas_kosong_jadi_null_bukan_string_kosong(self):
        # String kosong di kolom teks = nilai yang tampak ada tapi tak bermakna; layar akan
        # memperlakukannya sebagai kelas tak dikenal alih-alih "tidak diketahui".
        self.assertIsNone(self._pause("")["production_paused_class"])
        from src.orchestrator import producer
        sb = FakeSB()
        producer._pause_channel(sb, {"id": "C1"}, "x")   # tanpa argumen sama sekali
        self.assertIsNone(sb.tulisan[0]["production_paused_class"])

    def test_kolom_rem_lama_tetap_ditulis(self):
        # REGRESI: menambah kolom baru tak boleh menghilangkan yang lama.
        p = self._pause("rate_limit")
        for k in ("production_paused", "production_paused_at", "production_paused_reason"):
            self.assertIn(k, p)
        self.assertTrue(p["production_paused"])


class TestAlasanMemuatPenyebabNyata(unittest.TestCase):
    """B — cabang 3-kegagalan dulu hanya menulis kalimat generik."""

    def test_kedua_cabang_menyertakan_pesan_terakhir(self):
        src = _baca(os.path.join(AKAR, "src", "orchestrator", "producer.py"))
        i = src.index("REM DARURAT")
        blok = src[i:i + 2000]
        self.assertIn("Penyebab terakhir:", blok,
                      "cabang 3-kegagalan tak lagi menyertakan penyebab — tenant kembali buta")
        self.assertIn("error_class=_kelas", blok, "kelas tak diteruskan ke penyimpan rem")


class TestTelegramBedakanPulihSendiri(unittest.TestCase):
    """C — satu bit terpenting: perlu bertindak atau tidak."""

    def _kirim(self, kelas):
        from src.utils.telegram_notifier import TelegramNotifier
        n = TelegramNotifier()
        with patch.object(n, "_chat_id_for_tenant", return_value="123"), \
             patch.object(n, "_send", side_effect=lambda _c, t: t) as kirim:
            n.notify_circuit_break("T1", "C1", "sebab apa pun", "Channel X", error_class=kelas)
        return kirim.call_args[0][1]

    def test_kelas_pulih_sendiri_menyuruh_menunggu(self):
        for kelas in SELF_HEALING:
            with self.subTest(kelas=kelas.value):
                t = self._kirim(kelas.value)
                self.assertIn("pulih sendiri", t)
                self.assertNotIn("perlu Anda kerjakan", t)

    def test_kelas_butuh_tindakan_menyuruh_bertindak(self):
        for kelas in FAST_FAIL:
            with self.subTest(kelas=kelas.value):
                t = self._kirim(kelas.value)
                self.assertIn("TIDAK pulih sendiri", t)

    def test_kelas_tak_diketahui_tidak_mengarang(self):
        for nilai in ("", "kelas_ngawur"):
            t = self._kirim(nilai)
            self.assertNotIn("pulih sendiri", t,
                             "tanpa kelas, sistem TIDAK boleh menjanjikan apa pun soal pemulihan")

    def test_mengantar_ke_layar_bila_alamat_diketahui(self):
        # Alamat aplikasi datang dari lingkungan (kosong di mesin uji, terisi di produksi) —
        # keduanya wajib diuji: ada alamat → tautan; tak ada → pesan tetap utuh tanpa tautan bolong.
        with patch.dict(os.environ, {"APP_BASE_URL": "https://mesinviral.com"}):
            self.assertIn("https://mesinviral.com/channels/C1", self._kirim("rate_limit"))
        with patch.dict(os.environ, {"APP_BASE_URL": ""}):
            t = self._kirim("rate_limit")
            self.assertNotIn("/channels/", t)
            self.assertIn("Pulihkan produksi", t, "tanpa alamat, anjurannya tetap harus utuh")


class TestAntiDriftTigaTempat(unittest.TestCase):
    """
    D — `SELF_HEALING` hidup di TIGA tempat: kode (Python), dokumen (tabel §1), layar (peta resep TS).
    Duplikasi ini tak terhindarkan (tiga bahasa berbeda) — maka diuji, bukan dipercaya.
    """

    def test_setiap_kelas_punya_kepastian(self):
        # Tak boleh ada kelas yang menggantung: ia pulih sendiri, atau butuh tindakan, atau UNKNOWN.
        menggantung = {k.name for k in ErrorClass} - {k.name for k in SELF_HEALING} \
            - {k.name for k in FAST_FAIL} - {ErrorClass.UNKNOWN.name}
        self.assertFalse(menggantung,
                         f"Kelas tanpa kepastian pulih-sendiri/butuh-tindakan: {sorted(menggantung)}")

    def test_dokumen_selaras_dengan_self_healing(self):
        tabel = [b for b in _baca(DOK).splitlines() if b.strip().startswith("| `")]
        for kelas in ErrorClass:
            baris = next((b for b in tabel if f"`{kelas.name}`" in b), None)
            self.assertIsNotNone(baris, f"{kelas.name} tak ada di tabel §1")
            if kelas in SELF_HEALING:
                self.assertIn("✅", baris, f"§1 tak menandai {kelas.name} sebagai pulih-sendiri")
            elif kelas is not ErrorClass.UNKNOWN:
                self.assertIn("❌", baris, f"§1 salah menandai {kelas.name} — ia butuh tindakan")

    def test_layar_selaras_dengan_self_healing(self):
        fe = _baca(FE_PANEL)
        for kelas in ErrorClass:
            if kelas is ErrorClass.UNKNOWN:
                continue   # ditangani resep bawaan
            m = re.search(rf"\n  {kelas.value}: \{{(.*?)\n  \}},", fe, re.S)
            self.assertIsNotNone(m, f"Layar tak punya resep untuk kelas {kelas.value}")
            harus = "true" if kelas in SELF_HEALING else "false"
            self.assertIn(f"pulihSendiri: {harus}", m.group(1),
                          f"Layar menyatakan pulihSendiri yang BERBEDA dari SELF_HEALING utk {kelas.value}")

    def test_layar_tak_menyebut_nama_penyedia(self):
        """Arahan owner: penyedia akan terus bertambah → petakan per KELAS, jangan per merek."""
        fe = _baca(FE_PANEL)
        # Buang blok komentar penjelas (di situ nama boleh muncul sebagai contoh sejarah).
        badan = fe[fe.index("const RESEP"):]
        for merek in ("groq", "openai", "elevenlabs", "gemini", "anthropic", "fal.ai", "edge_tts"):
            self.assertNotIn(merek, badan.lower(),
                             f"Nama penyedia '{merek}' muncul di peta layar — layar akan basi "
                             f"pada penyedia berikutnya. Petakan per KELAS.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
