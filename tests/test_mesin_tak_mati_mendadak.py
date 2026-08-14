"""⛔⛔ MESIN TIDAK BOLEH MATI MENDADAK KARENA SKEMA SDK DIBANGUN DI DALAM THREAD PRODUKSI.

Lahir 14-Agu 2026 dari kerugian yang bisa dihitung. SSOT: `AI_ERROR_MANAGEMENT_ARCHITECTURE.md §8L`.

  systemd: `code=killed, status=11/SEGV` — **6× sejak 1-Agu**. Setiap kali, produksi yang sedang
  berjalan HILANG TANPA JEJAK: proses mati sebelum sempat menulis `production_runs`, jadi bagi sistem
  kita produksi itu tak pernah ada dan tenant tak dikabari apa pun.

  Rantai kematian (rekaman 14-Agu 23:00:52), dari yang MEMULAI:
    producer._task → produce_one → pipeline.run → niche_selector.select → _analyze_with_ai
      → adapters.complete → openai completions.create → _base_client.request → [urai balasan]
      → openai/_models.py `_get_extra_fields_type` → pydantic `model_rebuild` → … → SIGSEGV

  Akar: SDK membangun skema pydantic secara MALAS, dan sentuhan pertamanya terjadi di dalam thread
  produksi tempat tumpukan sudah dalam. Pembangunan itu bolak-balik Python↔Rust ⇒ memakan tumpukan C
  tanpa menambah frame Python ⇒ penjaga rekursi Python tak pernah tersentuh ⇒ bukan `RecursionError`
  yang bisa ditangkap, melainkan tumpukan C jebol ⇒ SIGSEGV yang membunuh SELURUH proses.
  Bukti bahwa ini soal tumpukan C: rekamannya hanya **57 frame Python** (jebolnya tumpukan Python
  butuh RIBUAN).

⛔ Bila berkas ini merah: JANGAN dilonggarkan. Merahnya berarti mesin bisa mati mendadak lagi di
tengah produksi, dan pekerjaan tenant hilang tanpa seorang pun tahu.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import pemanasan_skema as ps  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPemanasanMenyiapkanSELURUHModel(unittest.TestCase):
    """⛔ INTI. Yang nyaris saya lewatkan: memanaskan model TERATAS saja TIDAK cukup.

    Terukur 14-Agu: `ChatCompletion.model_rebuild()` menyiapkan induknya, tapi `Choice`,
    `ChatCompletionMessage`, dan `CompletionUsage` TETAP tertunda — padahal SDK mengurai balasan
    secara bersarang dan menyentuh setiap tingkat. Perbaikan setengah = crash tetap terjadi.
    """

    def test_model_bersarang_ikut_siap(self):
        ps.panaskan_skema_sdk()
        from openai.types.chat import ChatCompletion
        from openai.types.chat.chat_completion import Choice
        from openai.types.chat.chat_completion_message import ChatCompletionMessage
        from openai.types.completion_usage import CompletionUsage
        for model in (ChatCompletion, Choice, ChatCompletionMessage, CompletionUsage):
            with self.subTest(model.__name__):
                self.assertTrue(
                    ps.skema_sudah_siap(model),
                    f"{model.__name__} masih TERTUNDA sesudah pemanasan ⇒ skemanya akan dibangun di "
                    f"dalam thread produksi (tumpukan sudah dalam) ⇒ SIGSEGV, 6 kejadian sejak 1-Agu")

    def test_nol_model_sdk_tersisa_tertunda(self):
        hasil = ps.panaskan_skema_sdk()
        self.assertEqual(hasil["sisa"], 0,
                         f"{hasil['sisa']} model SDK masih tertunda sesudah pemanasan")
        self.assertGreaterEqual(hasil["siap"] + hasil["sudah"], 100,
                                "terlalu sedikit model ditemukan — penelusuran turunan rusak?")

    def test_aman_dipanggil_berulang(self):
        ps.panaskan_skema_sdk()
        kedua = ps.panaskan_skema_sdk()
        self.assertEqual(kedua["siap"], 0, "pemanasan kedua membangun ulang — pemborosan")
        self.assertEqual(kedua["sisa"], 0)

    def test_gagal_terbuka_tak_menghentikan_mesin(self):
        """Pencegahan tak boleh jadi syarat produksi."""
        asli = ps._AWALAN_SDK
        try:
            ps._AWALAN_SDK = ("modul_yang_tidak_pernah_ada",)
            hasil = ps.panaskan_skema_sdk()          # tak boleh melempar
            self.assertEqual(hasil["sisa"], 0)
        finally:
            ps._AWALAN_SDK = asli


class TestUraiBalasanTakLagiMembangunSkema(unittest.TestCase):
    """⛔ UJI PERILAKU — bukti sesungguhnya, bukan pemeriksaan atribut.

    Meniru yang dilakukan produksi: mengurai balasan SDK berbentuk NYATA (lengkap dengan field
    tambahan `x_groq` yang justru memicu `_get_extra_fields_type`). Sesudah pemanasan, TIDAK BOLEH
    ada satu pun `model_rebuild` terpanggil — sebab panggilan itulah yang membunuh mesin.
    """

    BALASAN = {
        "id": "chatcmpl-x", "object": "chat.completion", "created": 1, "model": "llama-3.3-70b",
        "choices": [{"index": 0, "finish_reason": "stop", "logprobs": None,
                     "message": {"role": "assistant", "content": "[]"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "x_groq": {"id": "req_1"},          # field EXTRA — pemicu `_get_extra_fields_type`
    }

    GAMBAR = {"created": 1, "data": [{"b64_json": "AA=="}]}

    def _tanpa_pembangunan(self, kerja):
        """Jalankan `kerja` sambil mengintai SETIAP `model_rebuild`. Return daftar yang terpanggil."""
        import pydantic
        terpanggil = []
        asli = pydantic.BaseModel.model_rebuild.__func__

        def pengintai(cls, *a, **kw):
            terpanggil.append(getattr(cls, "__name__", "?"))
            return asli(cls, *a, **kw)

        pydantic.BaseModel.model_rebuild = classmethod(pengintai)
        try:
            kerja()
        finally:
            pydantic.BaseModel.model_rebuild = classmethod(asli)
        return terpanggil

    def test_nol_pembangunan_skema_saat_balasan_diurai(self):
        from openai.types.chat import ChatCompletion
        ps.panaskan_skema_sdk()

        def kerja():
            obj = ChatCompletion.construct(**self.BALASAN)
            self.assertEqual(obj.choices[0].message.content, "[]", "balasan gagal diurai")

        terpanggil = self._tanpa_pembangunan(kerja)
        self.assertEqual(
            terpanggil, [],
            f"skema masih dibangun saat balasan diurai: {terpanggil}. Di produksi, ini terjadi DI "
            f"DALAM thread pipeline (tumpukan sudah dalam) ⇒ SIGSEGV.")

    def test_KETIGA_jalur_mesin_tercakup(self):
        """⛔ UKURAN 'TUNTAS' YANG SEBENARNYA.

        SDK memuat ratusan model untuk endpoint yang mesin kita TIDAK PERNAH panggil (realtime ·
        webhooks · evals · conversations) — memanaskan semuanya mustahil dijamin dan tak ada
        gunanya. Yang WAJIB 100% panas adalah jalur yang mesin ini benar-benar lewati:
        **naskah (chat) · gambar (images) · naskah-Anthropic**. Diuji dengan mengurai balasan
        berbentuk NYATA di ketiganya, lalu memastikan NOL `model_rebuild` terpanggil.
        """
        ps.panaskan_skema_sdk()
        from openai.types.chat import ChatCompletion
        from openai.types import ImagesResponse

        jalur = [("naskah (chat)", lambda: ChatCompletion.construct(**self.BALASAN)),
                 ("gambar (images)", lambda: ImagesResponse.construct(**self.GAMBAR))]
        try:
            from anthropic.types import Message as AMessage
            jalur.append(("naskah (anthropic)", lambda: AMessage.construct(
                id="m", type="message", role="assistant", model="c",
                content=[{"type": "text", "text": "x"}], stop_reason="end_turn",
                stop_sequence=None, usage={"input_tokens": 1, "output_tokens": 1})))
        except Exception:
            pass

        for nama, kerja in jalur:
            with self.subTest(nama):
                terpanggil = self._tanpa_pembangunan(kerja)
                self.assertEqual(
                    terpanggil, [],
                    f"jalur {nama}: skema masih dibangun saat balasan diurai ({terpanggil}) ⇒ "
                    f"pembangunan itu akan terjadi di dalam thread produksi, dan itulah yang "
                    f"membunuh mesin 6× sejak 1-Agu")


class TestMesinMemanaskanSebelumThreadDibuat(unittest.TestCase):
    """URUTANNYA yang menyelamatkan, bukan keberadaannya: pemanasan SESUDAH thread = percuma."""

    def test_pemanasan_dipanggil_sebelum_thread_pertama(self):
        isi = open(os.path.join(AKAR, "scripts", "worker_decoupled.py"), encoding="utf-8").read()
        i_panas, i_thread = isi.find("panaskan_skema_sdk"), isi.find("threading.Thread(")
        self.assertGreater(i_panas, 0, "mesin tidak memanaskan skema sama sekali")
        self.assertGreater(i_thread, 0, "pola pembuatan thread berubah — uji ini perlu disesuaikan")
        self.assertLess(i_panas, i_thread,
                        "pemanasan SESUDAH thread dibuat ⇒ percuma: skema tetap dibangun di thread")

    def test_urutan_diperiksa_dari_STRUKTUR_kode_bukan_teks(self):
        """Pencarian teks sudah 4× tertipu komentar di proyek ini — jadi urutannya dibaca dari
        POHON SINTAKS: panggilan `panaskan_skema_sdk()` yang SUNGGUHAN wajib mendahului pembuatan
        `threading.Thread` yang SUNGGUHAN. Komentar & docstring tidak masuk pohon sintaks."""
        import ast

        pohon = ast.parse(open(os.path.join(AKAR, "scripts", "worker_decoupled.py"),
                               encoding="utf-8").read())
        baris_panas, baris_thread = [], []
        for simpul in ast.walk(pohon):
            if not isinstance(simpul, ast.Call):
                continue
            f = simpul.func
            nama = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nama == "panaskan_skema_sdk":
                baris_panas.append(simpul.lineno)
            elif nama == "Thread":
                baris_thread.append(simpul.lineno)

        self.assertTrue(baris_panas, "tak ada panggilan panaskan_skema_sdk() SUNGGUHAN di mesin "
                                     "(hanya komentar/teks?) ⇒ perbaikan tidak aktif")
        self.assertTrue(baris_thread, "pola pembuatan thread berubah — uji ini perlu disesuaikan")
        self.assertLess(min(baris_panas), min(baris_thread),
                        "pemanasan terjadi SESUDAH thread pertama dibuat ⇒ percuma: skema tetap "
                        "dibangun di dalam thread produksi")


class TestReproduksiCrashDanKesembuhannya(unittest.TestCase):
    """Menjalankan ULANG reproduksi crash yang sesungguhnya, sebagai SUBPROSES.

    Tumpukan thread sengaja dipersempit supaya keadaan "tumpukan sudah dalam saat skema dibangun"
    bisa ditiru dalam hitungan detik alih-alih menunggu produksi nyata. Tanpa pemanasan proses
    berakhir dibunuh sinyal; dengan pemanasan ia selesai wajar.
    """

    SKRIP = textwrap.dedent("""
        import faulthandler, sys, threading
        faulthandler.enable()
        MODE = sys.argv[1]
        sys.path.insert(0, ".")
        from openai.types.chat import ChatCompletion
        if MODE == "panas":
            from src.utils.pemanasan_skema import panaskan_skema_sdk
            panaskan_skema_sdk()
        BALASAN = {"id":"x","object":"chat.completion","created":1,"model":"m",
                   "choices":[{"index":0,"finish_reason":"stop","logprobs":None,
                               "message":{"role":"assistant","content":"[]"}}],
                   "usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2},
                   "x_groq":{"id":"r"}}
        def kerja(sisa):
            if sisa > 0:
                return kerja(sisa - 1)
            ChatCompletion.construct(**BALASAN)
        threading.stack_size(48 * 1024)
        t = threading.Thread(target=kerja, args=(100,))
        t.start(); t.join()
        print("SELESAI-WAJAR")
    """)

    def _jalankan(self, mode: str):
        return subprocess.run([sys.executable, "-c", self.SKRIP, mode], cwd=AKAR,
                              capture_output=True, text=True, timeout=300)

    def test_dengan_pemanasan_proses_SELAMAT(self):
        r = self._jalankan("panas")
        self.assertEqual(r.returncode, 0,
                         f"pemanasan tidak lagi menyelamatkan proses (kode {r.returncode}) — "
                         f"sebab SIGSEGV 14-Agu kembali terbuka")
        self.assertIn("SELESAI-WAJAR", r.stdout)

    def test_tanpa_pemanasan_proses_MATI(self):
        """Pagar-untuk-pagar. Bila suatu hari ini berhenti mati (pydantic/SDK/Python diperbaiki
        vendor), ujinya SKIP dengan terang — bukan diam-diam hijau, karena hijau tanpa bahaya =
        pagar yang tidur."""
        r = self._jalankan("dingin")
        if r.returncode == 0:
            self.skipTest("versi pydantic/SDK/Python sekarang tidak lagi jebol — pemanasan tetap "
                          "dijaga uji lain, tapi reproduksinya sudah tak berlaku")
        self.assertLess(r.returncode, 0,
                        f"proses berakhir dengan kode {r.returncode}, bukan dibunuh sinyal — "
                        f"reproduksi tidak lagi meniru kejadian nyata")


if __name__ == "__main__":
    unittest.main(verbosity=2)
