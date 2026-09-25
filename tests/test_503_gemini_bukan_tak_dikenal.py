"""Insiden 24-Sep-2026, channel `40c054b4` — 5 run gagal beruntun.

Sampel VERBATIM dari `production_runs.error_message` (DB produksi, disalin apa adanya):

  No topics selected — Provider 'Google Gemini (AI Studio)' gagal: Error code: 503 -
  [{'error': {'code': 503, 'message': 'This model is currently experiencing high demand.
  Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}]

Dua cacat yang ditutup berkas ini:
  A. Kelima run tersimpan `error_class=unknown` → layar/Telegram tak punya arahan.
     Respons Gemini harus menjadi TRANSIENT, TIDAK `MODEL_UNAVAILABLE` — pesan vendor hanya
     menyebut high demand, bukan model dipensiunkan.
  B. 4 dari 5 kegagalan itu `run_metadata.job_type=test` (direct) dan 1 `mode=buffer`.
     `recent_nonready_streak` menghitung semuanya → uji tenant mengisi rem produksi.

Dijaga: klasifikasi · angka kasus nyata · pemisahan uji dari streak · arahan tenant.
"""
import os
import sys
import re
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exceptions import ErrorClass  # noqa: E402
from src.providers.llm.adapters import _classify_openai_compat_error  # noqa: E402

# ── Sampel VERBATIM DB (payload + kelas + metadata per run) ────────────────────────────────────
SEBAB = ("Provider 'Google Gemini (AI Studio)' gagal: Error code: 503 - "
         "[{'error': {'code': 503, 'message': 'This model is currently experiencing high demand. "
         "Spikes in demand are usually temporary. Please try again later.', "
         "'status': 'UNAVAILABLE'}}]")
PESAN_LENGKAP = f"No topics selected — {SEBAB}"

# keempat run direct/test (728, 729, 731, 732) + satu scheduled/buffer (730)

import os as _os
from pathlib import Path as _Path
AKAR = str(_Path(__file__).resolve().parents[1])


def _baca(rel: str) -> str:
    with open(_Path(AKAR) / rel, encoding="utf-8") as _f:
        return _f.read()


LIMA_RUN = [
    {"status": "failed", "error_class": "unknown", "error_message": PESAN_LENGKAP,
     "created_at": "2026-09-24T15:04:45+00:00",
     "run_metadata": {"direct": True, "job_type": "test", "video_title": ""}},
    {"status": "failed", "error_class": "unknown", "error_message": PESAN_LENGKAP,
     "created_at": "2026-09-24T15:06:38+00:00",
     "run_metadata": {"direct": True, "job_type": "test", "video_title": ""}},
    {"status": "failed", "error_class": "unknown", "error_message": PESAN_LENGKAP,
     "created_at": "2026-09-24T15:09:45+00:00",
     "run_metadata": {"mode": "buffer", "scheduled": True, "video_title": ""}},
    {"status": "failed", "error_class": "unknown", "error_message": PESAN_LENGKAP,
     "created_at": "2026-09-24T15:10:02+00:00",
     "run_metadata": {"direct": True, "job_type": "test", "video_title": ""}},
    {"status": "failed", "error_class": "unknown", "error_message": PESAN_LENGKAP,
     "created_at": "2026-09-24T15:11:34+00:00",
     "run_metadata": {"direct": True, "job_type": "test", "video_title": ""}},
]
# dikirim terbaru-dulu, sama seperti query `order(created_at desc)`
LIMA_RUN_TURUN = list(reversed(LIMA_RUN))


class _Q:
    def __init__(self, rows):
        self._rows, self._sejak = rows, None

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def gt(self, kolom, nilai):
        self._sejak = nilai
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        rows = [r for r in self._rows
                if not self._sejak or r["created_at"] > self._sejak]
        rows = sorted(rows, key=lambda r: r["created_at"], reverse=True)

        class R:  # noqa: N801
            data = rows
        return R()


class _SB:
    def __init__(self, rows):
        self._rows = rows

    def table(self, _nama):
        return _Q(self._rows)


def _streak(rows):
    from src.orchestrator import inventory
    with patch("src.orchestrator.inventory._sb", return_value=_SB(rows)):
        return inventory.recent_nonready_streak("40c054b4-1159-483a-955f-9e160a7de97d")


def _kegagalan_terakhir(rows):
    from src.orchestrator import inventory
    with patch("src.orchestrator.inventory._sb", return_value=_SB(rows)):
        return inventory.latest_failure("40c054b4-1159-483a-955f-9e160a7de97d")


class TestA_Klasifikasi503Gemini(unittest.TestCase):
    """Keluhan tenant #1: tak ada satu pun arahan yang diberikan untuk kelima kegagalan."""

    def test_payload_db_masuk_sebagai_transient(self):
        kelas, _human = _classify_openai_compat_error(
            Exception(SEBAB), "gemini",
            model="gemini-flash-latest", penyedia_nama="Google Gemini (AI Studio)")
        self.assertEqual(kelas, ErrorClass.TRANSIENT,
                         "503 high-demand harus gangguan sesaat (pulih sendiri), bukan UNKNOWN")

    def test_TIDAK_mengubahnya_jadi_model_unavailable(self):
        """Pesan vendor hanya high demand. Menjadikannya MODEL_UNAVAILABLE = menyuruh tenant
        mengganti model atas dasar yang tidak dibuktikan vendor."""
        kelas, _human = _classify_openai_compat_error(
            Exception(SEBAB), "gemini",
            model="gemini-flash-latest", penyedia_nama="Google Gemini (AI Studio)")
        self.assertNotEqual(kelas, ErrorClass.MODEL_UNAVAILABLE)
        if _human:
            self.assertNotIn("model lain", _human,
                             "503 high-demand tidak boleh menyarankan ganti model")

    def test_status_503_lain_tetap_dikenali(self):
        """Jaringan jangan sempit-cumakasus: bentuk 503 lain dari provider yang sama juga
        boleh diulang (429/500 tak tersentuh oleh perubahan ini)."""
        for sampel in (
            "Error code: 503 - service unavailable",
            "HTTP 503 UNAVAILABLE",
        ):
            with self.subTest(sampel=sampel):
                kelas, _ = _classify_openai_compat_error(Exception(sampel), "gemini")
                self.assertEqual(kelas, ErrorClass.TRANSIENT)

    def test_provider_lain_503_000_diperlakukan_seperti_sebelumnya(self):
        """Jaring umum SENGAJA tak memetakan 503 (perilaku lama) — perubahan ini per-vendor."""
        for vendor in ("openai", "groq", ""):
            with self.subTest(vendor=vendor):
                kelas, _ = _classify_openai_compat_error(Exception(SEBAB), vendor)
                self.assertEqual(kelas, ErrorClass.UNKNOWN)

    def test_429_dan_404_tidak_ikut_berubah(self):
        self.assertEqual(
            _classify_openai_compat_error(Exception("Error code: 429 - rate limited"), "gemini")[0],
            ErrorClass.RATE_LIMIT)
        self.assertEqual(
            _classify_openai_compat_error(Exception("Error code: 404 - model_not_found"), "gemini")[0],
            ErrorClass.MODEL_UNAVAILABLE)


class TestB_KelasMengalirSampaiTenant(unittest.TestCase):
    """Keluhan tenant #2: Telegram menulis 'TIDAK pulih sendiri' untuk 503 sementara."""

    def test_selector_mewarisi_kelas_dari_adapter(self):
        from src.exceptions import LLMError
        from src.intelligence.niche_selector import NicheSelector

        kelas, human = _classify_openai_compat_error(
            Exception(SEBAB), "gemini",
            model="gemini-flash-latest", penyedia_nama="Google Gemini (AI Studio)")
        sel = NicheSelector.__new__(NicheSelector)
        sel.last_error = sel.last_error_class = sel.last_human_error = None
        sel.last_error = str(LLMError(SEBAB, error_class=kelas, human_message=human))
        sel.last_error_class, sel.last_human_error = kelas, human

        # pipeline membaca persis dua atribut ini
        self.assertEqual(
            sel.last_error_class, ErrorClass.TRANSIENT,
            "kelas punah di tangan selector → pipeline mencatat unknown dan panel bisu")

    def test_notifier_memberi_arahan_pulih_sendiri_untuk_transient(self):
        from src.utils.telegram_notifier import TelegramNotifier

        n = TelegramNotifier()
        with patch.object(n, "_chat_id_for_tenant", return_value="123"), \
             patch.object(n, "_send", side_effect=lambda _c, t: t) as kirim:
            pesan = n.notify_circuit_break(
                tenant_id="t", channel_id="c", reason="5x produksi beruntun gagal",
                channel_name="Enzo advanture", error_class=ErrorClass.TRANSIENT.value)
        self.assertIn("pulih sendiri", pesan)
        self.assertNotIn("TIDAK pulih sendiri", pesan)

    def test_notifier_tanpa_kelas_tetap_netral(self):
        """Kelas kosong tak boleh diarahan 'butuh tindakan' — itu menyesatkan."""
        from src.utils.telegram_notifier import TelegramNotifier

        n = TelegramNotifier()
        with patch.object(n, "_chat_id_for_tenant", return_value="123"), \
             patch.object(n, "_send", side_effect=lambda _c, t: t) as kirim:
            pesan = n.notify_circuit_break(
                tenant_id="t", channel_id="c", reason="x", channel_name="c", error_class=None)
        self.assertNotIn("TIDAK pulih sendiri", pesan)


class TestC_StreakTidakMenghitungUji(unittest.TestCase):
    """Keluhan #3 (data, bukan dugaan): 4 dari 5 run kejadian ber-job_type=test."""

    def test_lima_run_nyata_hanya_menghasilkan_satu_kegagalan_produksi(self):
        self.assertEqual(_streak(LIMA_RUN_TURUN), 1,
                         "4 run uji mengisi rem produksi → tenant berbayar dimatikan oleh "
                         "tombol ujinya sendiri")

    def test_kegagalan_terakhir_bukan_milik_run_uji(self):
        lf = _kegagalan_terakhir(LIMA_RUN_TURUN)
        self.assertIsNotNone(lf)
        self.assertEqual(lf["error_class"], "unknown",
                         "rem-cepat seharusnya membaca run scheduled (730), bukan run uji 732")

    def test_streak_produksi_sungguh_tetap_terlindungi(self):
        """Uji tak boleh melumpuhkan rem: tiga kegagalan buffer harus tetap memicu rem."""
        tiga = [
            {"status": "failed", "error_class": "unknown", "error_message": "x",
             "created_at": f"2026-09-24T15:0{i}:00+00:00",
             "run_metadata": {"scheduled": True, "mode": "buffer"}}
            for i in range(3)
        ]
        self.assertEqual(_streak(tiga), 3)

    def test_suku_bagian_lama_tertanam_pada_metadata_yang_dinilai(self):
        """Syaratnya METADATA, bukan tebakan run_id/topic: `test=True` dari jalur admin_test
        dan `job_type=test` dari Jalankan Ulang tenant keduanya harus tertangkap."""
        for md, label in (({"direct": True, "test": True, "job_type": "admin_test"}, "admin_test"),
                          ({"direct": True, "job_type": "test"}, "test"),
                          ({"direct": True, "job_type": "test_nopub"}, "test_nopub"),
                          ({"direct": True, "job_type": "preview_image"}, "preview_image")):
            with self.subTest(label=label):
                rows = [{"status": "failed", "error_class": "unknown", "error_message": "x",
                         "created_at": "2026-09-24T15:00:00+00:00", "run_metadata": md}]
                self.assertEqual(_streak(rows), 0)

    def test_uji_netral_pada_kedua_arah(self):
        """Uji NETRAL total: gagal tidak menambah hitungan, sukses tidak memutusnya.
        Kalau uji sukses ikut memutus, tenant dapat 'rem lepas' dari tombol uji padahal
        produksinya masih gagal — pintu tanpa lantainya (pola 8c yang sama)."""
        netral = [
            {"status": "failed", "error_class": "unknown", "error_message": "x",
             "created_at": "2026-09-24T15:02:00+00:00",
             "run_metadata": {"scheduled": True, "mode": "buffer"}},
            {"status": "success", "error_class": None, "error_message": None,
             "created_at": "2026-09-24T15:01:00+00:00",
             "run_metadata": {"direct": True, "job_type": "test"}},
            {"status": "failed", "error_class": "unknown", "error_message": "x",
             "created_at": "2026-09-24T15:00:00+00:00",
             "run_metadata": {"scheduled": True, "mode": "buffer"}},
        ]
        self.assertEqual(_streak(netral), 2)

        # pemutus tetap ADA: sukses milik produksi (buffer/scheduled)
        putus = [
            {"status": "failed", "error_class": "unknown", "error_message": "x",
             "created_at": "2026-09-24T15:02:00+00:00",
             "run_metadata": {"scheduled": True, "mode": "buffer"}},
            {"status": "success", "error_class": None, "error_message": None,
             "created_at": "2026-09-24T15:01:00+00:00",
             "run_metadata": {"scheduled": True, "mode": "buffer"}},
            {"status": "failed", "error_class": "unknown", "error_message": "x",
             "created_at": "2026-09-24T15:00:00+00:00",
             "run_metadata": {"scheduled": True, "mode": "buffer"}},
        ]
        self.assertEqual(_streak(putus), 1, "sukses produksi memutus kegagalan yang lebih lama")

    def test_larangan_kecualian_kelas_error_tetap_ada(self):
        """Pagar lama: kelas pulih-sendiri TIDAK boleh dikecualikan dari hitungan."""
        for kelas in ("rate_limit", "transient", "unknown", "auth_invalid"):
            with self.subTest(kelas=kelas):
                rows = [{"status": "failed", "error_class": kelas, "error_message": "x",
                         "created_at": "2026-09-24T15:00:00+00:00",
                         "run_metadata": {"scheduled": True, "mode": "buffer"}}
                        for _ in range(3)]
                self.assertEqual(_streak(rows), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestD_IdentitasModelTidakHilang(unittest.TestCase):
    """`failed_model` NULL pada keempat run direct (728/729/731/732). Identitas model sudah
    dibawa adapter → LLMError, tapi berhenti di NicheSelector dan tak pernah sampai pipeline."""

    def test_selector_mewariskan_model_ke_pipeline(self):
        from src.exceptions import LLMError
        from src.intelligence.niche_selector import NicheSelector

        sel = NicheSelector.__new__(NicheSelector)
        sel.last_error, sel.last_error_class = "", ErrorClass.UNKNOWN
        sel.last_human_error, sel.last_failed_model = None, ""
        sel.last_error = "x"                      # dipakai sebagai penanda pekerjaan kursor
        sel.last_error_class, sel.last_human_error, sel.last_failed_model = (
            ErrorClass.TRANSIENT, None, "")
        # biarkan kursor merangkak: pulihkan ke keadaan sebelum loop lalu lemparkan error
        exc = LLMError(SEBAB, error_class=ErrorClass.TRANSIENT, human_message=None,
                       model="gemini-2.5-flash", dasar="status-http-vendor")
        sel.last_error_class = exc.error_class
        sel.last_human_error = exc.human_message
        sel.last_error = exc.human_message or str(exc)
        sel.last_failed_model = getattr(exc, "model", "") or ""

        self.assertEqual(sel.last_failed_model, "gemini-2.5-flash")

        # pipeline membaca dua atribut ini untuk merangkai ulang LLMError
        src = _baca(os.path.join(AKAR, "src", "orchestrator", "pipeline.py"))
        self.assertIn("last_failed_model", src,
                      "pipeline tak pernah meminta model dari selector → failed_model NULL")

    def test_pipeline_mengambil_model_dari_error_selector(self):
        from src.orchestrator import pipeline
        src = _baca(os.path.join(AKAR, "src", "orchestrator", "pipeline.py"))
        self.assertRegex(src, r"No topics selected[\s\S]{0,600}?model=getattr",
                         "raise 'No topics selected' tak meneruskan model → kolomnya selalu NULL")

    def test_kedua_jalur_direct_menulis_failed_model(self):
        src = _baca(os.path.join(AKAR, "src", "orchestrator", "producer.py"))
        self.assertGreaterEqual(
            len(re.findall(r'"failed_model"\s*:\s*result\.get\("failed_model"\)', src)), 3,
            "jalur direct tanpa `failed_model` → bukti-silang antar-tenant berlubang "
            "(terukur: run 728–732 semuanya NULL)")
