"""⛔⛔ PENJAGA PERILAKU — BERAPA KALI MESIN MENCOBA & BERAPA KABAR YANG TENANT TERIMA.

Berkas ini lahir dari kerusakan 13/14-Agu 2026, dan bentuknya sengaja berbeda dari uji rem yang
sudah ada. Yang sudah ada memeriksa **angka di dalam mesin** (`streak == 3`). Semuanya HIJAU
sepanjang insiden — 880 uji lulus — sementara dua tenant dibanjiri 53 kabar gagal.

**Sebabnya uji lama tak bisa menangkapnya:** hitungan streak MEMANG benar (2 dari ambang 3).
Yang salah adalah AKIBATNYA di dunia nyata — mesin mencoba tanpa henti, satu produksi baru tiap
±14 detik (±257 kabar/jam), sampai tenant mematikan channelnya sendiri.

Karena itu uji di sini mengukur **yang tenant rasakan**, bukan angka perantara:
  • berapa kali produksi benar-benar di-submit sebelum mesin berhenti
  • berapa kabar gagal yang benar-benar terkirim
  • apakah mesin akhirnya BERHENTI sendiri, atau butuh manusia turun tangan

**Data insiden yang ditagih uji ini** (`production_runs` + worker.log VPS):
  13-Agu Thetangga Property  30 kegagalan / 8 menit  (29 jatah-harian)  rem TIDAK menyala
  14-Agu BISIK NUSANTARA     23 kegagalan / 11 menit (21 jatah-harian)  rem TIDAK menyala
  50 dari 53 kegagalan `rate_limit` sepanjang umur aplikasi terjadi di dua hari itu (94%)

⛔ Bila berkas ini merah, JANGAN dilonggarkan ambangnya. Merahnya berarti mesin kembali bisa
mencoba tanpa batas — yaitu bug yang sama, memakai nama lain.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

AMBANG_REM = 3           # PRODUCER_FAIL_STREAK_STOP bawaan
SIKLUS_DIUJI = 25        # jauh di atas ambang: cukup untuk memperlihatkan "tanpa henti"


class _Q:
    """Peniru rantai kueri Supabase — hanya sejauh yang producer & inventory pakai."""

    def __init__(self, gudang, tabel):
        self._g, self._t = gudang, tabel
        self._limit = None
        self._count = False

    # ── select/filter/urut: semuanya mengembalikan diri sendiri ──
    def select(self, *_a, **kw):
        self._count = kw.get("count") == "exact"
        return self

    def eq(self, *_a):
        return self

    def gt(self, *_a):
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def update(self, patch):
        self._g.pembaruan.append((self._t, dict(patch)))
        if self._t == "channels":
            for ch in self._g.channels:
                ch.update(patch)
        return self

    def execute(self):
        class R:
            pass
        r = R()
        if self._t == "production_runs":
            baris = list(reversed(self._g.runs))          # terbaru dulu
            r.data = baris[: self._limit] if self._limit else baris
        elif self._t == "channels":
            r.data = [dict(c) for c in self._g.channels]
        else:                                            # content_inventory
            r.data = []
        r.count = 0 if self._count else None
        return r


class _SB:
    def __init__(self, gudang):
        self._g = gudang

    def table(self, nama):
        return _Q(self._g, nama)


class _Gudang:
    """Keadaan dunia palsu: channel, buku besar run, dan catatan pembaruan."""

    def __init__(self):
        self.channels = [{
            "id": "CH-UJI", "tenant_id": "T-UJI", "channel_name": "Channel Uji",
            "is_active": True, "production_paused": False, "production_resumed_at": None,
            "buffer_depth": 2,               # eksplisit → target_stock tak menyentuh DB/config
            "publish_slots": ["07:00"],
        }]
        self.runs: list[dict] = []
        self.pembaruan: list[tuple] = []

    def catat_gagal(self, kelas: str, pesan: str = "jatah harian penyedia habis"):
        self.runs.append({"status": "failed", "error_class": kelas, "error_message": pesan,
                          "created_at": f"2026-08-14T12:{len(self.runs):02d}:00+00:00"})


class _Pool:
    """Pengganti ThreadPoolExecutor: mencatat, tidak menjalankan apa pun."""

    def __init__(self):
        self.submit_ke = []

    def submit(self, fn):
        self.submit_ke.append(fn)


def _jalankan_siklus(gudang, kelas_kegagalan, siklus=SIKLUS_DIUJI):
    """Putar penjadwal `siklus` kali. Setiap produksi yang di-submit dianggap GAGAL dengan kelas
    yang diminta — persis pola 13/14-Agu (gagal 1-7 detik, stok tak pernah bertambah).

    Return: (jumlah produksi di-submit, jumlah kabar gagal ke tenant, jumlah alarm rem).
    """
    import threading
    from src.orchestrator import producer

    sb = _SB(gudang)
    kabar_gagal, alarm_rem = [], []

    def _kabar_gagal(*_a, **_kw):
        kabar_gagal.append(1)
        return True

    class _Notif:
        def notify_circuit_break(self, **_kw):
            alarm_rem.append(1)
            return True

    total_submit = 0
    with patch("src.orchestrator.inventory._sb", return_value=sb), \
         patch("src.billing.limits.gate_for_channel", return_value={"can_produce": True}), \
         patch("src.orchestrator.readiness.channel_readiness",
               return_value={"ready": True, "check_failed": False, "missing": []}), \
         patch("src.utils.telegram_notifier.TelegramNotifier", _Notif):
        for _ in range(siklus):
            pool = _Pool()
            sem = threading.Semaphore(4)
            producer.plan_and_submit(sb, pool, sem)
            for _fn in pool.submit_ke:
                total_submit += 1
                gudang.catat_gagal(kelas_kegagalan)      # produksi itu gagal
                _kabar_gagal()                            # → satu kabar Telegram ke tenant
    return total_submit, len(kabar_gagal), len(alarm_rem)


class TestMesinBerhentiSendiri(unittest.TestCase):
    """Ukurannya BUKAN 'streak benar', tapi 'mesin berhenti dan tenant tidak dibanjiri'."""

    def test_jatah_harian_habis_mesin_BERHENTI_setelah_ambang(self):
        """⛔ INTI. Sebab yang pulih sendiri (jatah harian) WAJIB tetap menghentikan mesin.

        Inilah kegagalan 13/14-Agu: kelas ini dikecualikan dari hitungan, jadi mesin tak pernah
        berhenti dan tenant menerima kabar tiap ±14 detik sampai ia mematikan channelnya.
        """
        for kelas in ("rate_limit", "transient"):
            with self.subTest(kelas):
                g = _Gudang()
                submit, kabar, alarm = _jalankan_siklus(g, kelas)
                self.assertLessEqual(
                    submit, AMBANG_REM,
                    f"'{kelas}': mesin mencoba {submit}× dalam {SIKLUS_DIUJI} siklus dan tak pernah "
                    f"berhenti sendiri. Ini bentuk persis insiden 13/14-Agu (30 & 23 kegagalan).")
                self.assertLessEqual(
                    kabar, AMBANG_REM,
                    f"'{kelas}': tenant menerima {kabar} kabar gagal. Terukur di produksi: "
                    f"±257 kabar/jam sampai tenant mematikan channelnya sendiri.")
                self.assertTrue(
                    g.channels[0]["production_paused"],
                    f"'{kelas}': mesin tidak pernah mengerem — tak ada apa pun di aplikasi ini "
                    f"yang menghentikan percobaan berulang selain rem ini.")
                self.assertEqual(alarm, 1, "rem menyala wajib mengabari tenant TEPAT sekali")

    def test_SETIAP_kelas_error_membuat_mesin_berhenti(self):
        """Anti-drift menyeluruh, ditulis atas seluruh anggota `ErrorClass` — bukan daftar tangan.

        Kelas yang ditambahkan kelak ikut terjaga tanpa uji ini perlu disunting. Tak satu pun kelas
        boleh mendapat izin 'coba terus tanpa batas'.
        """
        from src.exceptions import ErrorClass
        for kelas in ErrorClass:
            with self.subTest(kelas.value):
                g = _Gudang()
                submit, kabar, _ = _jalankan_siklus(g, kelas.value)
                self.assertLessEqual(submit, AMBANG_REM,
                                     f"'{kelas.value}' tidak menghentikan mesin ({submit} percobaan)")
                self.assertTrue(g.channels[0]["production_paused"],
                                f"'{kelas.value}' tidak pernah mengerem channel")

    def test_channel_yang_sudah_direm_TIDAK_dicoba_lagi(self):
        """Sesudah rem menyala, nol percobaan berikutnya — rem yang tak menahan bukan rem."""
        g = _Gudang()
        g.channels[0]["production_paused"] = True
        submit, kabar, _ = _jalankan_siklus(g, "rate_limit")
        self.assertEqual(submit, 0, "channel ter-rem masih diproduksi")
        self.assertEqual(kabar, 0, "channel ter-rem masih mengirim kabar gagal ke tenant")

    def test_produksi_SUKSES_tidak_kena_rem(self):
        """Arah kedua — rem tidak boleh menghukum channel sehat.

        Bila produksi berhasil, hitungan putus dan mesin terus berproduksi selama stok kurang.
        Tanpa uji ini, 'mengerem lebih cepat' bisa lolos sebagai perbaikan padahal ia mematikan
        channel yang sehat.
        """
        import threading
        from src.orchestrator import producer

        g = _Gudang()
        sb = _SB(g)
        total = 0
        with patch("src.orchestrator.inventory._sb", return_value=sb), \
             patch("src.billing.limits.gate_for_channel", return_value={"can_produce": True}), \
             patch("src.orchestrator.readiness.channel_readiness",
                   return_value={"ready": True, "check_failed": False, "missing": []}):
            for _ in range(6):
                pool, sem = _Pool(), threading.Semaphore(4)
                producer.plan_and_submit(sb, pool, sem)
                for _fn in pool.submit_ke:
                    total += 1
                    g.runs.append({"status": "success", "error_class": None, "error_message": None,
                                   "created_at": f"2026-08-14T13:{len(g.runs):02d}:00+00:00"})
        self.assertGreaterEqual(total, 6, "channel SEHAT ikut terhenti — rem terlalu galak")
        self.assertFalse(g.channels[0]["production_paused"],
                         "channel yang produksinya SUKSES tidak boleh direm")


class TestLarangan(unittest.TestCase):
    """Larangan yang dijaga PERILAKU, bukan pencarian teks.

    Komentar sudah 4× menipu uji berbasis pencarian teks di proyek ini (SSOT §10). Karena itu uji
    di bawah membuktikan lewat hasil pemanggilan, bukan lewat isi berkas.
    """

    def test_hitungan_kegagalan_tidak_mengecualikan_kelas_apa_pun(self):
        """Uji ini merah bila ada yang mengembalikan penyaringan `SELF_HEALING` (percobaan 12-Agu).

        Dibandingkan LANGSUNG: hitungan untuk kelas pulih-sendiri wajib SAMA dengan kelas yang
        menuntut tindakan. Berbeda = ada kelas yang diistimewakan lagi.
        """
        from src.exceptions import SELF_HEALING, ErrorClass
        from src.orchestrator import inventory

        def _hitung(kelas):
            g = _Gudang()
            for i in range(3):
                g.runs.append({"status": "failed", "error_class": kelas, "error_message": "x",
                               "created_at": f"2026-08-14T12:0{i}:00+00:00"})
            with patch("src.orchestrator.inventory._sb", return_value=_SB(g)):
                return inventory.recent_nonready_streak("CH-UJI")

        acuan = _hitung(ErrorClass.AUTH_INVALID.value)      # kelas yang jelas menuntut tindakan
        self.assertEqual(acuan, 3, "acuan hitungan sendiri sudah tidak benar")
        for kelas in SELF_HEALING:
            with self.subTest(kelas.value):
                self.assertEqual(
                    _hitung(kelas.value), acuan,
                    f"'{kelas.value}' dihitung berbeda dari kelas biasa → pengecualian 12-Agu hidup "
                    f"kembali, dan bersamanya banjir kabar 13/14-Agu")


if __name__ == "__main__":
    unittest.main(verbosity=2)
