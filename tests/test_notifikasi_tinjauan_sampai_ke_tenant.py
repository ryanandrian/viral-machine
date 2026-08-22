"""Pesan "video menunggu keputusan Anda" WAJIB sampai ke tenant pada jalur TERJADWAL.

MASALAH YANG DIJAGA (dilaporkan owner 2026-08-22)
`notify_review_pending` mengambil nomor Telegram HANYA dari lembar setelan yang diberikan pemanggil.
Satu-satunya pemanggilnya — `producer.produce_one` (jalur terjadwal/Opsi C) — memberikan
`intelligence.config.TenantConfig`, lembar yang dibangun dari baris `channels` dan **tidak punya
kolom Telegram sama sekali**. Akibatnya nomor selalu kosong → fungsi keluar `False` **tanpa satu
baris log** (pengirim hanya mencatat saat benar-benar mengirim). Terukur di produksi: 11 video
ber-catatan QC (4 channel, 4 tenant, 19-Jul → 22-Agu) NOL pesan; pembanding di sebelah — 12 video
jalur langsung/uji, yang memakai lembar `TenantRunConfig`, pesannya terkirim SEMUA.

Akibat nyatanya bukan kosmetik: video ber-catatan QC dibuang otomatis saat TTL habis, jadi biaya
produksinya hangus tanpa tenant pernah tahu ada yang perlu ia putuskan.

POLANYA SUDAH ADA DI BERKAS INI — `notify_circuit_break` & `notify_published` me-resolve nomor
sendiri dari `tenant_configs` lewat `_chat_id_for_tenant`. Perbaikannya menyeragamkan, bukan
menambah jalur baru.

DUA ARAH DIJAGA:
  (a) lembar tanpa kolom Telegram WAJIB tetap terkirim (nomor di-resolve dari tenant_configs)
  (b) saklar "matikan notifikasi" tenant WAJIB tetap dihormati — perbaikan (a) tak boleh
      berubah jadi pesan yang tak bisa dimatikan (over-correction = bug baru)
"""
import ast
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _notifier():
    from src.utils.telegram_notifier import TelegramNotifier
    n = TelegramNotifier.__new__(TelegramNotifier)
    n.bot_token = "uji-token"
    return n


class LembarTanpaKolomTelegram:
    """Tiruan `TenantConfig` jalur terjadwal: nol kolom telegram_*, nol channel_name."""


class TestNomorTeleponDiresolveSendiri(unittest.TestCase):

    def test_lembar_tanpa_kolom_telegram_tetap_terkirim(self):
        """(a) Ini kasus produksi yang gagal senyap 11x."""
        n = _notifier()
        terkirim = []
        with patch.object(type(n), "_chat_id_for_tenant", return_value="123456"), \
             patch.object(type(n), "_send", side_effect=lambda c, t: terkirim.append((c, t)) or True):
            hasil = n.notify_review_pending(
                tenant_id="t-1", title="Judul", qc_reason="Durasi 71.0s kependekan",
                recommendation="Sesuaikan preset", run_config=LembarTanpaKolomTelegram())
        self.assertTrue(hasil, "pesan tinjauan TIDAK terkirim untuk lembar tanpa kolom Telegram — "
                               "ini persis kegagalan senyap yang dijaga uji ini")
        self.assertEqual(len(terkirim), 1)
        self.assertEqual(terkirim[0][0], "123456", "nomor bukan dari tenant_configs")

    def test_tanpa_lembar_sama_sekali_tetap_terkirim(self):
        n = _notifier()
        terkirim = []
        with patch.object(type(n), "_chat_id_for_tenant", return_value="777"), \
             patch.object(type(n), "_send", side_effect=lambda c, t: terkirim.append((c, t)) or True):
            n.notify_review_pending(tenant_id="t-2", title="J", qc_reason="R")
        self.assertEqual([c for c, _ in terkirim], ["777"])

    def test_pesan_mengarahkan_ke_halaman_review(self):
        """Isi pesan = arahan aksi, bukan kabar buruk tanpa jalan keluar."""
        n = _notifier()
        terkirim = []
        with patch.object(type(n), "_chat_id_for_tenant", return_value="9"), \
             patch.object(type(n), "_send", side_effect=lambda c, t: terkirim.append(t) or True), \
             patch.dict(os.environ, {"APP_BASE_URL": "https://mesinviral.com"}):
            n.notify_review_pending(tenant_id="t-3", title="J", qc_reason="R",
                                    run_config=LembarTanpaKolomTelegram())
        teks = terkirim[0]
        self.assertIn("Review", teks)
        self.assertIn("/review", teks)

    def test_nama_channel_dipakai_bukan_nomor_tenant(self):
        """Header pesan = nama channel yang tenant kenali (pola notify_circuit_break)."""
        n = _notifier()
        terkirim = []
        with patch.object(type(n), "_chat_id_for_tenant", return_value="9"), \
             patch.object(type(n), "_send", side_effect=lambda c, t: terkirim.append(t) or True):
            n.notify_review_pending(tenant_id="uuid-panjang-tenant", title="J", qc_reason="R",
                                    run_config=LembarTanpaKolomTelegram(),
                                    channel_name="Penjaga Dakwah")
        self.assertIn("Penjaga Dakwah", terkirim[0])
        self.assertNotIn("uuid-panjang-tenant", terkirim[0])


class TestSaklarTenantTetapDihormati(unittest.TestCase):

    def test_saklar_mati_di_lembar_setelan_menghentikan_pesan(self):
        """(b) Anti over-correction: resolve-sendiri TIDAK BOLEH mengakali saklar tenant."""
        class LembarSaklarMati:
            telegram_enabled = False
            telegram_chat_id = None

        n = _notifier()
        with patch.object(type(n), "_chat_id_for_tenant", return_value="123") as resolver, \
             patch.object(type(n), "_send", return_value=True) as pengirim:
            hasil = n.notify_review_pending(tenant_id="t-4", title="J", qc_reason="R",
                                            run_config=LembarSaklarMati())
        self.assertFalse(hasil, "saklar notifikasi tenant DILANGGAR — pesan tetap dikirim")
        pengirim.assert_not_called()
        resolver.assert_not_called()

    def test_saklar_mati_di_database_menghentikan_pesan(self):
        """`_chat_id_for_tenant` mengembalikan kosong saat saklar DB mati → wajib berhenti."""
        n = _notifier()
        with patch.object(type(n), "_chat_id_for_tenant", return_value=""), \
             patch.object(type(n), "_send", return_value=True) as pengirim:
            hasil = n.notify_review_pending(tenant_id="t-5", title="J", qc_reason="R",
                                            run_config=LembarTanpaKolomTelegram())
        self.assertFalse(hasil)
        pengirim.assert_not_called()


class TestPemanggilMenyerahkanNamaChannel(unittest.TestCase):
    """Diperiksa lewat AST, bukan teks: penjaga berbasis teks lolos saat panggilannya dikomentari."""

    def _panggilan(self):
        with open(os.path.join(AKAR, "src/orchestrator/producer.py"), encoding="utf-8") as f:
            pohon = ast.parse(f.read())
        return [n for n in ast.walk(pohon)
                if isinstance(n, ast.Call)
                and getattr(n.func, "attr", "") == "notify_review_pending"]

    def test_panggilan_ada_tepat_satu(self):
        self.assertEqual(len(self._panggilan()), 1,
                         "jumlah pemanggil notify_review_pending berubah — cakupan uji ini ikut berubah")

    def test_nama_channel_diambil_dari_baris_channel(self):
        kw = {k.arg: ast.unparse(k.value) for k in self._panggilan()[0].keywords}
        self.assertIn("channel_name", kw,
                      "producer tak menyerahkan nama channel → header pesan jatuh ke nomor tenant")
        self.assertIn("channel_row", kw["channel_name"],
                      f"nama channel bukan dari baris channel: {kw['channel_name']}")


if __name__ == "__main__":
    unittest.main()
