"""MODEL BERNALAR TIDAK BOLEH MEMBAKAR JATAH SAMPAI JAWABANNYA TAK PERNAH DITULIS.

CACAT YANG DIJAGA (10 kegagalan produksi 18–26 Agu: BISIK NUSANTARA · RETRO REWIND GARAGE ·
JaydenSaverio · Bang Us-Dat — SEMUANYA Groq, nol di channel Gemini/OpenAI).

Terukur 27-Agu pada `openai/gpt-oss-120b` di Groq, memakai prompt naskah SUNGGUHAN:
    tanpa kekangan  : reasoning_tokens 4.498 dari 4.500 · isi jawaban 0 huruf · finish=length
    jatah 8.000     : tetap 0 huruf — menaikkan jatah hanya memberi waktu berpikir lebih lama
    reasoning_effort="low" : berpikir 1.270 + jawaban 805 → JAWABAN UTUH, finish=stop
Diulang 3x lewat adapter sesudah perbaikan: 3/3 berhasil (sebelum perbaikan 1/3).

⚠️ KOREKSI ATAS ANALISA SAYA SENDIRI, ditulis di sini supaya tak dikerjakan ulang: saya sempat
menyimpulkan sebabnya "jatah 2.000 kekecilan, 51% naskah melebihinya". SALAH — yang saya ukur objek
naskah TERSIMPAN (sudah bercampur turunan mesin). Bagian yang LLM benar-benar kembalikan: tengah
392 · p95 571 · terpanjang 670 token dari 184 naskah ⇒ nol yang melebihi 2.000.

DUA WAJAH GEJALA YANG SAMA — keduanya wajib tertangani:
  (a) vendor MENGEMBALIKAN jawaban kosong + finish=length + ada token berpikir
  (b) vendor MENOLAK 400 `json_validate_failed`/`json_generate_failed` dgn `failed_generation` KOSONG
      (mode JSON Groq menolak SEBELUM ada objek jawaban ⇒ (a) mustahil terbaca di sana)

Hermetik: nol jaringan.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import ErrorClass  # noqa: E402
from src.providers.llm.adapters import OpenAIChatAdapter  # noqa: E402
from src.providers.llm.base import LLMError  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JSON_UTUH = '{"title": "a", "hook": "b"}'
JSON_POTONG = '{"title": "a", "ho'

# Pesan vendor NYATA (27-Agu, Groq) — disalin apa adanya, bukan diringkas.
NIHIL = ("Error code: 400 - {'error': {'message': \"Failed to validate JSON. Please adjust your "
         "prompt. See 'failed_generation' for more details.\", 'type': 'invalid_request_error', "
         "'code': 'json_validate_failed', 'failed_generation': ''}}")
JSON_CACAT_BERISI = ("Error code: 400 - {'error': {'code': 'json_validate_failed', "
                     "'failed_generation': '{\"title\": \"Kisah bengkel'}}")
KEBESARAN = ("Error code: 413 - {'error': {'message': 'Request too large for model "
             "`openai/gpt-oss-120b` in organization `org_x` service tier `on_demand` on tokens per "
             "minute (TPM): Limit 8000, Requested 8121, please reduce your message size'}}")
KEBESARAN_MUSTAHIL = ("Error code: 413 - {'error': {'message': 'Request too large ... on tokens per "
                      "minute (TPM): Limit 3000, Requested 8121'}}")


class _Balasan:
    def __init__(self, isi, alasan, berpikir=0):
        self.choices = [type("C", (), {
            "finish_reason": alasan,
            "message": type("M", (), {"content": isi})(),
        })()]
        self.usage = type("U", (), {
            "prompt_tokens": 100, "completion_tokens": 50,
            "completion_tokens_details": type("D", (), {"reasoning_tokens": berpikir})(),
        })()


class _Klien:
    """Klien palsu. Skenario = daftar; tiap butir salah satu dari:
    `Exception(...)` → dilemparkan · `(isi, alasan)` · `(isi, alasan, token_berpikir)`."""

    def __init__(self, skenario):
        self.skenario, self.panggilan, self.n = list(skenario), [], 0
        klien = self

        class _Completions:
            def create(self, **kw):
                klien.panggilan.append(dict(kw))
                klien.n += 1
                butir = klien.skenario[min(klien.n - 1, len(klien.skenario) - 1)]
                if isinstance(butir, BaseException):
                    raise butir
                return _Balasan(*butir)

        self.chat = type("Chat", (), {"completions": _Completions()})()


def _jalan(skenario, as_json=True, jatah=4500, model="model-uji", bersihkan_memo=True):
    k = _Klien(skenario)
    p = OpenAIChatAdapter(api_key="K", display_name="Groq", provider_key="groq")
    if bersihkan_memo:
        OpenAIChatAdapter._PARAM_ADAPTATIONS.clear()
        OpenAIChatAdapter._JATAH_NAIK.clear()
        OpenAIChatAdapter._KEKANG_NALAR.clear()
    hasil = galat = None
    with patch("openai.OpenAI", return_value=k), \
         patch("src.providers.llm.adapters._catalog.resolve_model_id", lambda n: n), \
         patch("src.providers.llm.adapters._catalog.get_models", lambda: {}):
        try:
            hasil = p.complete(system="s", user="u", model=model, max_tokens=jatah, as_json=as_json)
        except Exception as e:      # noqa: BLE001 — uji memeriksa jenis & isinya
            galat = e
    return k, p, hasil, galat


def _kekangan(panggilan):
    return [c.get("reasoning_effort") for c in panggilan]


def _jatah(panggilan):
    return [c.get("max_tokens") or c.get("max_completion_tokens") for c in panggilan]


# ══ A. VENDOR MENOLAK & MENYATAKAN NOL KELUARAN → KEKANG BERPIKIRNYA ════════════════════════════

class TestA_PenolakanNihilKeluaran(unittest.TestCase):

    def test_dikekang_bukan_dinaikkan(self):
        """Menaikkan jatah TERUKUR tidak menolong (8.000 tetap kosong) — ia hanya membakar uang."""
        k, _, hasil, galat = _jalan([Exception(NIHIL), (JSON_UTUH, "stop")])
        self.assertIsNone(galat, f"tidak pulih padahal kekangan tersedia: {galat}")
        self.assertEqual(hasil, JSON_UTUH)
        self.assertEqual(_kekangan(k.panggilan), [None, "low"],
                         f"percobaan ulang tidak mengekang waktu berpikir: {_kekangan(k.panggilan)}")
        self.assertEqual(_jatah(k.panggilan)[1], _jatah(k.panggilan)[0],
                         "jatah ikut dinaikkan — terukur TIDAK menolong pada model bernalar, "
                         "dan pada Groq justru menabrak batas token/menit")

    def test_sekali_saja_tidak_berputar(self):
        k, _, hasil, galat = _jalan([Exception(NIHIL)] * 5)
        self.assertIsInstance(galat, LLMError, "harus gagal jujur, bukan mengembalikan apa pun")
        self.assertLessEqual(len(k.panggilan), 2,
                             f"{len(k.panggilan)} panggilan — tenant ditagih berulang untuk gejala "
                             f"yang sudah pasti tak berubah")

    def test_terbukti_menolong_maka_DIMEMO(self):
        """Tanpa memo, TIAP panggilan berikutnya membayar satu percobaan kosong lagi."""
        k, p, _, _ = _jalan([Exception(NIHIL), (JSON_UTUH, "stop")])
        self.assertEqual(p._KEKANG_NALAR.get(("openai", "model-uji")), "low",
                         f"kekangan yang terbukti menolong tidak diingat: {p._KEKANG_NALAR!r}")
        k2 = _Klien([(JSON_UTUH, "stop")])
        with patch("openai.OpenAI", return_value=k2), \
             patch("src.providers.llm.adapters._catalog.resolve_model_id", lambda n: n), \
             patch("src.providers.llm.adapters._catalog.get_models", lambda: {}):
            p.complete(system="s", user="u", model="model-uji", max_tokens=4500, as_json=True)
        self.assertEqual(_kekangan(k2.panggilan), ["low"],
                         "panggilan berikutnya TIDAK langsung dikekang — percobaan kosong dibayar ulang")

    def test_kekangan_ditolak_vendor_TIDAK_dimemo(self):
        """Kekangan dimemo hanya SESUDAH terbukti menghasilkan jawaban. Memo optimistis akan
        memaksakan parameter yang vendor tolak pada SETIAP panggilan berikutnya — satu cacat
        menular ke seluruh produksi tenant itu."""
        k, p, _, galat = _jalan([Exception(NIHIL), Exception("Error code: 400 - unknown parameter")])
        self.assertIsNotNone(galat, "kegagalan disembunyikan")
        self.assertEqual(p._KEKANG_NALAR, {},
                         f"kekangan yang GAGAL tetap diingat: {p._KEKANG_NALAR!r}")

    def test_kekangan_ditolak_di_jalur_jawaban_ada_TIDAK_dimemo(self):
        """Jalur kedua (jawaban dikembalikan kosong) punya penanganannya sendiri — ia juga tak
        boleh mengingat kekangan yang vendor tolak."""
        k, p, _, galat = _jalan([("", "length", 4498),
                                 Exception("Error code: 400 - unknown parameter")])
        self.assertEqual(p._KEKANG_NALAR, {},
                         f"kekangan yang GAGAL tetap diingat: {p._KEKANG_NALAR!r}")
        self.assertIsInstance(galat, LLMError, "kegagalan tidak dilaporkan jujur")


# ══ B. PENYAKIT LAIN HARAM DISAMARKAN JADI "MODEL BERNALAR" ═════════════════════════════════════

class TestB_JanganMenyamarkanSebabLain(unittest.TestCase):

    def test_failed_generation_BERISI_tidak_dikekang(self):
        """`failed_generation` berisi = model MENULIS JSON cacat. Mengekang waktu berpikir takkan
        menolong, dan hanya menutupi sebab yang sesungguhnya."""
        k, _, _, galat = _jalan([Exception(JSON_CACAT_BERISI)])
        self.assertIsNotNone(galat)
        self.assertEqual(_kekangan(k.panggilan), [None],
                         "penyakit lain ikut dikekang — sebabnya jadi tersamarkan")
        self.assertEqual(len(k.panggilan), 1, "percobaan ulang yang mustahil menolong = uang terbakar")

    def test_teks_biasa_terpotong_TAPI_BERISI_tidak_dikekang(self):
        """Pemanggil teks biasa (judul, prompt gambar) masih memakai jawaban terpotong — perilaku
        lama itu HARAM berubah."""
        k, _, hasil, _ = _jalan([("kalimat yang terpotong di tengah", "length", 900)],
                                as_json=False, jatah=350)
        self.assertEqual(_kekangan(k.panggilan), [None],
                         "teks biasa yang masih berguna ikut dikekang — regresi perilaku lama")
        self.assertEqual(len(k.panggilan), 1, f"panggilan berlebih: {len(k.panggilan)}")

    def test_tanpa_token_berpikir_tidak_dikekang(self):
        """Model biasa yang jawabannya terpotong = urusan jaring 'naikkan jatah', bukan kekangan."""
        k, _, _, _ = _jalan([(JSON_POTONG, "length", 0), (JSON_UTUH, "stop")])
        self.assertEqual(_kekangan(k.panggilan)[1], None,
                         "model non-bernalar ikut dikekang tanpa bukti apa pun")
        self.assertGreater(_jatah(k.panggilan)[1], _jatah(k.panggilan)[0],
                           "jaring 'naikkan jatah' yang sudah ada tidak lagi bekerja — regresi")


# ══ C. JAWABAN KOSONG YANG DIKEMBALIKAN (bukan ditolak) ════════════════════════════════════════

class TestC_JawabanKosongDikembalikan(unittest.TestCase):

    def test_kosong_plus_token_berpikir_dikekang(self):
        k, _, hasil, galat = _jalan([("", "length", 4498), (JSON_UTUH, "stop")])
        self.assertIsNone(galat, f"tidak pulih: {galat}")
        self.assertEqual(hasil, JSON_UTUH)
        self.assertIn("low", _kekangan(k.panggilan),
                      f"jawaban KOSONG + 4.498 token berpikir tidak memicu kekangan: "
                      f"{_kekangan(k.panggilan)}")


# ══ D. VENDOR MENOLAK KARENA PERMINTAAN KEBESARAN ══════════════════════════════════════════════

class TestD_PenolakanKebesaran(unittest.TestCase):

    def test_diturunkan_ke_hitungan_EKSAK_dari_pesan_vendor(self):
        """Batas 8000, diminta 8121, terkirim 4500 ⇒ pertanyaan = 3621 ⇒ pas = 8000-3621-200 = 4179.
        Angka dari VENDOR, bukan tebakan dan bukan kenop admin."""
        k, _, hasil, galat = _jalan([Exception(KEBESARAN), (JSON_UTUH, "stop")])
        self.assertIsNone(galat, f"tidak pulih dari penolakan kebesaran: {galat}")
        j = _jatah(k.panggilan)
        self.assertEqual(len(j), 2, f"pemulihan boros/kurang: {j}")
        self.assertEqual(j[1], 8000 - (8121 - 4500) - 200,
                         f"jatah tidak dihitung dari angka vendor: {j}")

    def test_pertanyaan_sendiri_melebihi_batas_GAGAL_JUJUR(self):
        """Menurunkan jatah tak mungkin menolong ⇒ tenant wajib diberi tindakan yang NYATA."""
        k, _, _, galat = _jalan([Exception(KEBESARAN_MUSTAHIL)])
        self.assertIsInstance(galat, LLMError)
        self.assertEqual(galat.error_class, ErrorClass.QUOTA_EXHAUSTED,
                         "mengulang MUSTAHIL menolong, jadi kelasnya tak boleh yang boleh-diulang")
        pesan = (galat.human_message or "").lower()
        self.assertTrue(pesan, "tenant tidak diberi tahu apa pun")
        self.assertTrue(any(x in pesan for x in ("paket", "preset", "penyedia lain")),
                        f"pesan tidak menyebut tindakan yang bisa tenant lakukan: {pesan!r}")
        self.assertEqual(len(k.panggilan), 1, "masih dicoba ulang padahal mustahil")

    def test_ditolak_lagi_sesudah_diturunkan_TIDAK_berputar(self):
        k, _, _, galat = _jalan([Exception(KEBESARAN)] * 5)
        self.assertIsInstance(galat, LLMError)
        self.assertLessEqual(len(k.panggilan), 2,
                             f"berputar {len(k.panggilan)} kali antara dua kegagalan")

    def test_kenaikan_jatah_TIDAK_melampaui_langit_langit_vendor(self):
        """Jaring 'naikkan jatah' haram mengembalikan angka yang baru saja vendor tolak."""
        k, _, _, galat = _jalan([(JSON_POTONG, "length", 0), Exception(KEBESARAN),
                                 (JSON_POTONG, "length", 0)])
        self.assertIsInstance(galat, LLMError, "harus gagal jujur")
        self.assertLessEqual(len(k.panggilan), 3, f"berputar: {len(k.panggilan)} panggilan")


# ══ E. JATAH NASKAH-UTUH = SATU TETAPAN, NOL LITERAL TERTINGGAL ════════════════════════════════

class TestE_SatuTetapanNaskahUtuh(unittest.TestCase):

    def _src(self):
        with open(os.path.join(AKAR, "src/intelligence/script_engine.py"), encoding="utf-8") as f:
            return f.read()

    def test_tiga_titik_naskah_utuh_memakai_tetapan(self):
        src = self._src()
        self.assertEqual(src.count("max_tokens=JATAH_NASKAH_UTUH"), 3,
                         "titik naskah-utuh tidak semuanya memakai satu tetapan — angka bisa "
                         "berbeda antar jalur, dan itulah cara cacat ini kembali diam-diam")

    def test_nol_jatah_2000_tertinggal(self):
        self.assertNotIn("max_tokens=2000", self._src(),
                         "masih ada jatah 2000 yang ditanam di jalur naskah")

    def test_tetapan_menyediakan_ruang_berpikir_plus_menjawab(self):
        """Terukur: berpikir-dikekang 1.270 + jawaban 805 = 2.075 ⇒ 2.000 TIDAK cukup."""
        from src.intelligence.script_engine import JATAH_NASKAH_UTUH
        self.assertGreaterEqual(JATAH_NASKAH_UTUH, 2075 * 2,
                                "tetapan tak menyediakan cadangan 2x atas kebutuhan terukur")
        self.assertLessEqual(JATAH_NASKAH_UTUH, 4850,
                             "tetapan melewati ruang yang Groq izinkan di percobaan ke-1 "
                             "(8.000/menit − prompt ±3.100) ⇒ setiap panggilan ditolak dulu")


if __name__ == "__main__":
    unittest.main()
