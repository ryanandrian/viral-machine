"""JAWABAN TERPOTONG TIDAK BOLEH DIULANG SIA-SIA — uang tenant terbakar tanpa peluang berhasil.

CACAT YANG DIJAGA (kegagalan tenant BISIK NUSANTARA 18-Agu, terbukti pada jalur produksi):
jatah token adalah SATU kantong untuk dua keperluan — mesin AI berpikir di dalam, lalu menulis
jawaban. Model generasi baru memakai kantong itu untuk berpikir, sehingga jawabannya terpotong
di tengah kalimat dan JSON-nya gugur.

Perilaku mesin SEBELUM penjaga ini (diukur, bukan diduga):
    permintaan ke vendor : 3x   ← tiap kali DITAGIH tenant
    jatah tiap percobaan : 2000, 2000, 2000  ← identik, tak pernah naik
    topik didapat        : 0
    golongan galat       : UNKNOWN
    pesan untuk tenant   : TIDAK ADA

Tiga pelanggaran sekaligus: mengulang yang MUSTAHIL berhasil, tak mengenali sebabnya, dan tak
memberi tahu tenant apa pun.

RIWAYATNYA (mata ke-3 §0): mekanisme ini SAYA SENDIRI temukan & tulis di `ede8a88` (16-Jul) —
*"model bernalar menghabiskan jatah token untuk berpikir di dalam → jawaban kosong → vonis gagal
PALSU"* — lalu memperbaikinya HANYA di jalur uji (`model_tester` 16→512). Jalur produksi
ditinggalkan. Penjaga ini menutup separuh yang tertinggal itu.

Angka batas atas 4000 BUKAN tebakan: terukur 18-Agu — Gemini 3.6/3.7/flash-latest terpotong di
2000 dan LULUS di 4000; Groq MENOLAK 8000 (galat 413 "Request too large"). Jadi 4000 = titik yang
menyembuhkan tanpa ditolak vendor.

Hermetik: nol jaringan.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.providers.llm.adapters import OpenAIChatAdapter  # noqa: E402
from src.providers.llm.base import LLMError  # noqa: E402

JSON_UTUH = '{"topics": [{"topic": "a"}, {"topic": "b"}]}'
JSON_POTONG = '{"topics": [{"topic": "Kisah rumah tua", "angle": "penjaga mala'


class _Balasan:
    def __init__(self, isi, alasan):
        self.choices = [type("C", (), {
            "finish_reason": alasan,
            "message": type("M", (), {"content": isi})(),
        })()]
        self.usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 50})()


class _Klien:
    """Klien palsu: mencatat jatah token tiap panggilan, membalas sesuai skenario."""

    def __init__(self, skenario):
        self.skenario, self.jatah, self.n = list(skenario), [], 0
        klien = self

        class _Completions:
            def create(self, **kw):
                klien.jatah.append(kw.get("max_tokens") or kw.get("max_completion_tokens"))
                klien.n += 1
                isi, alasan = klien.skenario[min(klien.n - 1, len(klien.skenario) - 1)]
                return _Balasan(isi, alasan)

        self.chat = type("Chat", (), {"completions": _Completions()})()


def _jalan(skenario, as_json=True, model="model-uji"):
    k = _Klien(skenario)
    p = OpenAIChatAdapter(api_key="K", display_name="Uji", provider_key="groq")
    OpenAIChatAdapter._PARAM_ADAPTATIONS.clear()
    OpenAIChatAdapter._JATAH_NAIK.clear()
    hasil = galat = None
    with patch("openai.OpenAI", return_value=k), \
         patch("src.providers.llm.adapters._catalog.resolve_model_id", lambda n: n), \
         patch("src.providers.llm.adapters._catalog.get_models", lambda: {}):
        try:
            hasil = p.complete(system="s", user="u", model=model,
                               max_tokens=2000, as_json=as_json)
        except Exception as e:      # noqa: BLE001 — uji memeriksa jenis & isinya
            galat = e
    return k, hasil, galat


class TestA_TerpotongTakDiulangIdentik(unittest.TestCase):

    def test_jatah_dinaikkan_bukan_diulang_sama(self):
        k, hasil, galat = _jalan([(JSON_POTONG, "length"), (JSON_UTUH, "stop")])
        self.assertGreater(
            len(k.jatah), 1,
            "Jawaban terpotong tidak dicoba ulang sama sekali — permintaan yang sudah DITAGIH "
            "tenant dibuang begitu saja.")
        self.assertGreater(
            k.jatah[1], k.jatah[0],
            f"Percobaan ulang memakai jatah yang SAMA ({k.jatah}) — mustahil berhasil, dan tenant "
            "ditagih lagi untuk kegagalan yang sudah pasti.")

    def test_naik_sekali_lalu_berhasil(self):
        k, hasil, galat = _jalan([(JSON_POTONG, "length"), (JSON_UTUH, "stop")])
        self.assertIsNone(galat, f"seharusnya pulih sendiri, malah gagal: {galat}")
        self.assertEqual(hasil, JSON_UTUH)
        self.assertEqual(len(k.jatah), 2, f"boros: {len(k.jatah)} panggilan untuk 1 pemulihan")


class TestB_ModelYangMemangTakSanggupGagalJujur(unittest.TestCase):

    def test_tetap_terpotong_setelah_dinaikkan_gagal_dengan_sebab_benar(self):
        k, hasil, galat = _jalan([(JSON_POTONG, "length")] * 4)
        self.assertIsInstance(galat, LLMError, "harus gagal, bukan mengembalikan JSON rusak")
        pesan = (getattr(galat, "human_message", "") or "").lower()
        self.assertTrue(
            pesan, "tenant tidak diberi tahu apa pun — inilah yang membuatnya menyalahkan aplikasi")
        self.assertIn(
            "model", pesan,
            f"pesan tidak menyebut modelnya sebagai sebab: {pesan!r}. Tenant harus tahu tindakan "
            "yang perlu ia lakukan (ganti model), bukan menebak.")

    def test_tak_naik_tanpa_batas(self):
        """Terukur 18-Agu: Groq MENOLAK jatah 8000 (galat 413). Naik membabi buta = bug baru."""
        k, _, _ = _jalan([(JSON_POTONG, "length")] * 4)
        self.assertLessEqual(
            max(k.jatah), 4000,
            f"jatah dinaikkan sampai {max(k.jatah)} — vendor menolak di 8000, jadi ini "
            "menukar satu kegagalan dengan kegagalan lain.")


class TestC_RegresiPerilakuLama(unittest.TestCase):

    def test_jawaban_utuh_tak_tersentuh(self):
        k, hasil, galat = _jalan([(JSON_UTUH, "stop")])
        self.assertEqual((len(k.jatah), k.jatah[0], hasil), (1, 2000, JSON_UTUH),
                         "panggilan yang sehat berubah perilakunya — itu regresi")

    def test_teks_biasa_tak_ikut_dinaikkan(self):
        """Pemanggil teks pendek (mis. judul) TIDAK meminta JSON — teks terpotong di sana masih
        terpakai apa adanya, persis perilaku lama. Menaikkannya = biaya tanpa manfaat."""
        k, hasil, galat = _jalan([("judul yang terpoto", "length")], as_json=False)
        self.assertEqual(len(k.jatah), 1, "teks biasa ikut dinaikkan — biaya naik tanpa alasan")
        self.assertIsNone(galat)


class TestD_PelajaranTakMenularKeTugasLain(unittest.TestCase):
    """RISIKO YANG DITEMUKAN SAAT MEMBANGUN PERBAIKAN INI (18-Agu), dijaga supaya tak kembali:
    memo jatah tersimpan per-proses. Bila kuncinya hanya (vendor, model), pelajaran dari tugas
    BESAR (seleksi topik, 2.000) menular ke tugas KECIL (penilai naskah 500 · hook 1.200) —
    model diberi ruang bicara jauh di atas rancangan tugas itu. Kunci WAJIB memuat jatah-diminta."""

    def test_tugas_kecil_tak_mewarisi_jatah_tugas_besar(self):
        k = _Klien([(JSON_POTONG, "length"), (JSON_UTUH, "stop")])
        p = OpenAIChatAdapter(api_key="K", display_name="Uji", provider_key="groq")
        OpenAIChatAdapter._PARAM_ADAPTATIONS.clear()
        OpenAIChatAdapter._JATAH_NAIK.clear()
        with patch("openai.OpenAI", return_value=k), \
             patch("src.providers.llm.adapters._catalog.resolve_model_id", lambda n: n), \
             patch("src.providers.llm.adapters._catalog.get_models", lambda: {}):
            # tugas BESAR terpotong → belajar naik
            p.complete(system="s", user="u", model="m", max_tokens=2000, as_json=True)
            batas_besar = max(k.jatah)
            # tugas KECIL sesudahnya: jatahnya HARUS tetap 500
            k2 = _Klien([(JSON_UTUH, "stop")])
            with patch("openai.OpenAI", return_value=k2):
                p.complete(system="s", user="u", model="m", max_tokens=500, as_json=True)
        self.assertGreater(batas_besar, 2000, "tugas besar tidak belajar naik")
        self.assertEqual(
            k2.jatah, [500],
            f"tugas kecil mewarisi jatah tugas besar ({k2.jatah}) — model diberi ruang bicara "
            "di atas rancangan tugasnya, dan itu menggeser panjang keluaran yang sudah dikalibrasi.")

    def test_memo_tak_pernah_menurunkan_jatah(self):
        """Memo hanya boleh MENAIKKAN. Menurunkan = memotong jawaban yang tadinya utuh."""
        OpenAIChatAdapter._JATAH_NAIK.clear()
        OpenAIChatAdapter._JATAH_NAIK[(("openai", "m"), 2000)] = 1000   # memo cacat, sengaja
        k = _Klien([(JSON_UTUH, "stop")])
        p = OpenAIChatAdapter(api_key="K", display_name="Uji", provider_key="groq")
        with patch("openai.OpenAI", return_value=k), \
             patch("src.providers.llm.adapters._catalog.resolve_model_id", lambda n: n), \
             patch("src.providers.llm.adapters._catalog.get_models", lambda: {}):
            p.complete(system="s", user="u", model="m", max_tokens=2000, as_json=True)
        self.assertEqual(k.jatah, [2000], f"memo MENURUNKAN jatah jadi {k.jatah} — memotong jawaban sehat")

    def test_batas_model_dari_katalog_dihormati(self):
        """Batas atas = DATA. Model yang menyatakan batasnya sendiri tak boleh dilewati."""
        k = _Klien([(JSON_POTONG, "length")] * 3)
        p = OpenAIChatAdapter(api_key="K", display_name="Uji", provider_key="groq")
        OpenAIChatAdapter._JATAH_NAIK.clear()
        with patch("openai.OpenAI", return_value=k), \
             patch("src.providers.llm.adapters._catalog.resolve_model_id", lambda n: n), \
             patch("src.providers.llm.adapters._catalog.get_models",
                   lambda: {"m": {"default_params": {"max_output_tokens": 2500}}}):
            try:
                p.complete(system="s", user="u", model="m", max_tokens=2000, as_json=True)
            except LLMError:
                pass
        self.assertLessEqual(max(k.jatah), 2500,
                             f"batas model dari katalog dilanggar: {k.jatah}")


if __name__ == "__main__":
    unittest.main()
