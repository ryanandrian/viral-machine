"""
Uji regresi PERMANEN — GERBANG UJI PRODUKSI [B24].
SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10 (matriks §10f).

Jalankan:  python -m unittest tests.test_gerbang_uji

Hermetik: nol koneksi database, nol jaringan. Lapis database diuji terpisah dengan menyamar sebagai
tenant sungguhan (skrip di scratchpad, hasilnya tercatat di §10e) — uji ini menjaga sisi Python.

Yang dijaga:
  A. `test_gate` memanggil RPC yang benar dan meneruskan hasilnya apa adanya (tidak menghitung sendiri).
  B. GAGAL JUJUR: RPC melempar / bentuk hasil aneh / tenant kosong → allowed=False, bukan dibuka diam-diam.
  C. `resume_channels` mengembalikan jumlah & tidak pernah melempar.
  D. `run_direct` MENOLAK job saat gerbang menolak — dan menulis KODE (`GATE:…`), bukan kalimat
     satu-bahasa, supaya layar bisa menerjemahkannya dwibahasa.
  E. `run_direct` MELEWATI gerbang untuk `admin_test` (channel internal admin, tenant comp).
  F. REGRESI: gerbang PRODUKSI (`can_produce`) tidak ikut berubah — masa tenggang tetap boleh produksi.
  G. ANTI-DRIFT: daftar status produksi di fungsi database WAJIB sama dengan `PRODUCING_STATUSES`
     Python. Duplikasi ini tak terhindarkan (satu di SQL, satu di Python); ujilah, jangan percaya.
  H. ANTI-DRIFT: rumus akun comp di database WAJIB sama dengan `is_comp_account` Python.
"""
import os
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# `test_gate` di-alias: pytest mengumpulkan SETIAP nama ber-awalan `test_` di berkas uji sebagai
# fungsi uji — termasuk yang cuma di-impor. Tanpa alias, pytest mencoba menjalankannya sebagai tes
# dan gagal mencari fixture `sb`/`tenant_id`.
from src.billing.limits import (  # noqa: E402
    PRODUCING_STATUSES, can_produce, is_comp_account, resume_channels,
)
from src.billing.limits import test_gate as periksa_gerbang  # noqa: E402

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGR_GERBANG = os.path.join(AKAR, "migrations", "0191_gerbang_uji_tenant.sql")
MIGR_PRODUKSI = os.path.join(AKAR, "migrations", "0192_gerbang_produksi_untuk_unduh.sql")


# ── Stub Supabase: hanya rpc() yang dipakai kedua fungsi ────────────────────────────────────────
class _RpcHasil:
    def __init__(self, data):
        self.data = data


class FakeSB:
    """Meniru sb.rpc(nama, args).execute(). `hasil` boleh nilai atau Exception untuk dilempar."""

    def __init__(self, hasil):
        self._hasil = hasil
        self.dipanggil = []

    def rpc(self, nama, args):
        self.dipanggil.append((nama, args))
        outer = self

        class _P:
            def execute(self):
                if isinstance(outer._hasil, Exception):
                    raise outer._hasil
                return _RpcHasil(outer._hasil)

        return _P()


class TestGerbangPanggilRpc(unittest.TestCase):
    """A — meneruskan hasil database apa adanya, tidak menghitung ulang di Python."""

    def test_meneruskan_hasil_apa_adanya(self):
        sb = FakeSB({"allowed": True, "reason": "ok", "used": 1, "max": 3})
        g = periksa_gerbang(sb, "T1")
        self.assertEqual(sb.dipanggil, [("tenant_test_gate", {"p_tenant_id": "T1"})])
        self.assertEqual(g, {"allowed": True, "reason": "ok", "used": 1, "max": 3})

    def test_hasil_dibungkus_daftar_juga_diterima(self):
        # PostgREST kadang mengembalikan daftar berisi satu baris.
        g = periksa_gerbang(FakeSB([{"allowed": False, "reason": "subscription"}]), "T1")
        self.assertFalse(g["allowed"])
        self.assertEqual(g["reason"], "subscription")

    def test_penolakan_jatah_membawa_angkanya(self):
        g = periksa_gerbang(FakeSB({"allowed": False, "reason": "trial_quota", "used": 5, "max": 3}), "T1")
        self.assertEqual((g["used"], g["max"]), (5, 3))


class TestGagalJujur(unittest.TestCase):
    """B — saat kita buta, pintu DITUTUP. Bukan dibuka diam-diam."""

    def test_rpc_melempar(self):
        g = periksa_gerbang(FakeSB(RuntimeError("koneksi putus")), "T1")
        self.assertFalse(g["allowed"])
        self.assertEqual(g["reason"], "gate_unavailable")

    def test_bentuk_hasil_tak_dikenal(self):
        for aneh in (None, "boleh", 42, [], [{"tidak": "relevan"}]):
            with self.subTest(aneh=aneh):
                g = periksa_gerbang(FakeSB(aneh), "T1")
                self.assertFalse(g["allowed"], f"{aneh!r} tak boleh membuka pintu")
                self.assertEqual(g["reason"], "gate_unavailable")

    def test_masukan_kosong(self):
        for sb, tid in ((FakeSB({}), ""), (FakeSB({}), None), (None, "T1")):
            with self.subTest(tid=tid):
                self.assertFalse(periksa_gerbang(sb, tid)["allowed"])


class TestPelepasRem(unittest.TestCase):
    """C — mengembalikan jumlah; kegagalan tak pernah merambat ke jalur pembayaran."""

    def test_jumlah_diteruskan(self):
        self.assertEqual(resume_channels(FakeSB(3), "T1"), 3)
        self.assertEqual(resume_channels(FakeSB([2]), "T1"), 2)
        self.assertEqual(resume_channels(FakeSB(None), "T1"), 0)

    def test_gagal_tidak_melempar(self):
        self.assertEqual(resume_channels(FakeSB(RuntimeError("boom")), "T1"), 0)
        self.assertEqual(resume_channels(None, "T1"), 0)
        self.assertEqual(resume_channels(FakeSB(1), ""), 0)


# ── D/E: run_direct ─────────────────────────────────────────────────────────────────────────────
class _TabelJob:
    def __init__(self, sink, channel_row):
        self._sink = sink
        self._ch = channel_row
        self._nama = None
        self._upd = None

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def update(self, payload):
        self._upd = payload
        return self

    def execute(self):
        if self._upd is not None:
            self._sink.append(self._upd)
            self._upd = None
            return _RpcHasil([])
        return _RpcHasil([self._ch] if self._ch else [])


class FakeSBJob:
    """Cukup untuk jalur penolakan run_direct: baca channels, tulis direct_jobs."""

    def __init__(self, channel_row):
        self.tulisan = []
        self._ch = channel_row

    def table(self, nama):
        return _TabelJob(self.tulisan, self._ch if nama == "channels" else None)


class TestRunDirectDitolakGerbang(unittest.TestCase):
    JOB = {"id": "J1", "tenant_id": "T1", "channel_id": "C1", "job_type": "test"}
    CH = {"id": "C1", "tenant_id": "T1", "niche": "history"}

    def _jalankan(self, job, hasil_gerbang):
        from src.orchestrator import producer
        sb = FakeSBJob(self.CH)
        with patch("src.billing.limits.test_gate", return_value=hasil_gerbang):
            producer.run_direct(sb, dict(job))
        return sb.tulisan

    def test_ditolak_langganan_menulis_kode_bukan_kalimat(self):
        tulisan = self._jalankan(self.JOB, {"allowed": False, "reason": "subscription"})
        akhir = [t for t in tulisan if t.get("status") == "failed"]
        self.assertTrue(akhir, "job wajib ditandai gagal")
        self.assertEqual(akhir[0]["error"], "GATE:subscription")
        # KODE, bukan kalimat: layar yang menerjemahkan ID/EN (§3.5).
        self.assertNotIn(" ", akhir[0]["error"])

    def test_ditolak_jatah_membawa_angka(self):
        tulisan = self._jalankan(self.JOB, {"allowed": False, "reason": "trial_quota",
                                            "used": 5, "max": 3})
        akhir = [t for t in tulisan if t.get("status") == "failed"]
        self.assertEqual(akhir[0]["error"], "GATE:trial_quota:5:3")

    def test_ditolak_saat_gerbang_tak_terjawab(self):
        tulisan = self._jalankan(self.JOB, {"allowed": False, "reason": "gate_unavailable"})
        akhir = [t for t in tulisan if t.get("status") == "failed"]
        self.assertEqual(akhir[0]["error"], "GATE:gate_unavailable")

    def test_ditolak_TIDAK_menandai_run_id(self):
        # Job yang ditolak tak boleh terlihat seperti pernah berjalan.
        tulisan = self._jalankan(self.JOB, {"allowed": False, "reason": "subscription"})
        self.assertFalse([t for t in tulisan if "run_id" in t],
                         "job yang ditolak tak boleh menulis run_id")

    def test_admin_test_TIDAK_LAGI_melewati_gerbang(self):
        """
        E — [§10e-3 CELAH A] Dulu jenis 'admin_test' dikecualikan dari gerbang. Itu pintu belakang:
        tenant tinggal menulis 'admin_test' untuk melewati gerbang DAN penghitung jatah. Pengecualian
        dicabut — dan tak diperlukan, karena tenant internal admin adalah akun comp yang gerbangnya
        selalu mengizinkan.
        """
        job = dict(self.JOB, job_type="admin_test")
        from src.orchestrator import producer

        # (a) Gerbang menolak → admin_test WAJIB ikut ditolak (pintu belakang tertutup).
        sb = FakeSBJob(self.CH)
        with patch("src.billing.limits.test_gate", return_value={"allowed": False, "reason": "trial_quota", "used": 9, "max": 3}), \
             patch("src.orchestrator.producer._run_test_no_publish") as jalan:
            producer.run_direct(sb, job)
        jalan.assert_not_called()
        self.assertEqual([t for t in sb.tulisan if t.get("status") == "failed"][0]["error"],
                         "GATE:trial_quota:9:3")

        # (b) Akun comp (tenant admin internal) → gerbang mengizinkan → jalur admin tetap hidup.
        sb2 = FakeSBJob(self.CH)
        with patch("src.billing.limits.test_gate", return_value={"allowed": True, "reason": "comp"}), \
             patch("src.orchestrator.producer._run_test_no_publish") as jalan2:
            producer.run_direct(sb2, dict(job))
        jalan2.assert_called_once()

    def test_channel_milik_tenant_lain_DITOLAK(self):
        """
        [§10e-3 CELAH B] Job yang menunjuk channel orang lain akan memakai kunci AI + koneksi
        YouTube KORBAN. Aturan tabel kini menahannya, tapi jalur kunci-layanan melewati aturan itu —
        worker wajib punya pemeriksaannya sendiri.
        """
        from src.orchestrator import producer
        ch_orang_lain = {"id": "C1", "tenant_id": "TENANT-LAIN", "niche": "history"}
        sb = FakeSBJob(ch_orang_lain)
        with patch("src.billing.limits.test_gate", return_value={"allowed": True, "reason": "ok"}) as g, \
             patch("src.orchestrator.producer._run_test_no_publish") as jalan:
            producer.run_direct(sb, dict(self.JOB))
        jalan.assert_not_called()
        g.assert_not_called()   # ditolak SEBELUM apa pun dikerjakan
        self.assertEqual([t for t in sb.tulisan if t.get("status") == "failed"][0]["error"],
                         "GATE:forbidden")
        self.assertFalse([t for t in sb.tulisan if "run_id" in t])


class TestGerbangProduksiTakBerubah(unittest.TestCase):
    """F — kerja ini HANYA menambah gerbang uji. Gerbang produksi wajib utuh."""

    def test_daftar_status_produksi(self):
        self.assertEqual(PRODUCING_STATUSES, {"active", "trial", "grace"})

    def test_masa_tenggang_tetap_boleh_produksi(self):
        self.assertTrue(can_produce("grace"))

    def test_status_mati_tetap_ditolak(self):
        for st in ("trial_expired", "suspended", "cancelled", "blocked"):
            self.assertFalse(can_produce(st), st)

    def test_kosong_tetap_back_compat_active(self):
        self.assertTrue(can_produce(None))
        self.assertTrue(can_produce(""))


class TestAntiDriftSqlVsPython(unittest.TestCase):
    """
    G/H — aturan yang sama tertulis di dua bahasa (SQL & Python). Itu tak terhindarkan: aturan akses
    tabel tak bisa memanggil Python. Yang bisa dilakukan: MENGUJI bahwa keduanya tak pernah melenceng.
    """

    def _sql(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_daftar_status_produksi_sama_di_sql(self):
        sql = self._sql(MIGR_PRODUKSI)
        m = re.search(r"in\s*\(([^)]*)\)\s*;", sql[sql.index("coalesce(tc.subscription_status"):])
        self.assertIsNotNone(m, "daftar status di 0192 tak ditemukan — struktur berubah?")
        di_sql = {s.strip().strip("'") for s in m.group(1).split(",")}
        self.assertEqual(di_sql, PRODUCING_STATUSES,
                         "daftar status SQL melenceng dari PRODUCING_STATUSES Python")

    def test_rumus_comp_sama_di_kedua_fungsi_sql(self):
        # is_comp_account: is_developer TRUE, ATAU diskon>=100 yang belum kedaluwarsa.
        for path in (MIGR_GERBANG, MIGR_PRODUKSI):
            sql = self._sql(path)
            self.assertIn("coalesce(tc.is_developer, false)", sql, path)
            self.assertIn("coalesce(tc.discount_pct, 0) >= 100", sql, path)
            self.assertIn("tc.discount_until is null or tc.discount_until >= now()", sql, path)

    def test_rumus_comp_python_sesuai_klaim_sql(self):
        self.assertTrue(is_comp_account({"is_developer": True}))
        self.assertTrue(is_comp_account({"discount_pct": 100}))
        self.assertTrue(is_comp_account({"discount_pct": 100, "discount_until": "2999-01-01T00:00:00Z"}))
        self.assertFalse(is_comp_account({"discount_pct": 100, "discount_until": "2000-01-01T00:00:00Z"}))
        self.assertFalse(is_comp_account({"discount_pct": 99}))
        self.assertFalse(is_comp_account({}))

    def test_bawaan_kenop_di_sql_sama_dengan_migrasi_penanam(self):
        # Fungsi gerbang memakai nilai bawaan bila kenop hilang. Bawaan itu WAJIB sama dengan yang
        # ditanam 0190 — kalau berbeda, menghapus satu baris kenop diam-diam mengubah kebijakan.
        penanam = self._sql(os.path.join(AKAR, "migrations", "0190_kenop_gerbang_uji.sql"))
        fungsi = self._sql(MIGR_GERBANG)
        for kenop, bawaan in (("test_gate_enabled", "1"), ("trial_test_quota", "3"),
                              ("trial_quota_reset_on_extend", "1")):
            self.assertRegex(penanam, rf"\('{kenop}',\s*{bawaan},", f"{kenop} di 0190")
            self.assertRegex(fungsi, rf"key = '{kenop}'\),\s*{bawaan}\)", f"{kenop} bawaan di 0191")
        self.assertIn("'[\"active\",\"trial\"]'", penanam)
        self.assertIn("array['active', 'trial']", fungsi)
        self.assertIn("'success'", penanam)
        self.assertIn("'success')", fungsi)


class TestJalurBukaTerpasang(unittest.TestCase):
    """
    I — SETIAP KUNCI WAJIB PUNYA JALUR BUKA (mandat owner 2026-08-02).

    Lima jalur reaktivasi harus memanggil pelepas rem. Dua di antaranya (settlement Midtrans dan
    link 1-klik) hanya bisa dibuktikan penuh saat ada pembayaran/klik NYATA — jadi di sini yang
    dijaga adalah pemasangannya: kalau suatu hari pemanggilan itu terhapus saat refactor, uji ini
    merah SEBELUM ada tenant yang terjebak. Tiga jalur lain sudah dibuktikan lewat HTTP nyata.
    """

    def _baca(self, rel):
        with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
            return f.read()

    def test_settlement_midtrans_melepas_rem(self):
        src = self._baca("src/billing/midtrans.py")
        self.assertIn("resume_channels", src,
                      "settlement Midtrans tak lagi melepas rem → tenant yang baru bayar TERJEBAK")
        # Wajib fail-soft: urusan rem tak boleh menggagalkan pencatatan pembayaran.
        blok = src[src.index("from src.billing.limits import resume_channels") - 400:]
        self.assertIn("try:", blok[:500])

    def test_link_reaktivasi_melepas_rem_dan_mencatat_perpanjangan(self):
        src = self._baca("src/billing/webhook_app.py")
        self.assertIn("resume_channels", src, "link 1-klik tak melepas rem")
        self.assertIn("trial_extended_at", src,
                      "link 1-klik tak mencatat perpanjangan → jatah uji tak pernah segar")

    def test_jalur_admin_melepas_rem(self):
        for rel in ("apps/web/src/app/api/admin/tenants/[id]/suspend/route.ts",
                    "apps/web/src/app/api/admin/tenants/[id]/lifecycle/route.ts"):
            self.assertIn("tenant_resume_channels", self._baca(rel), rel)

    def test_jalur_buka_manual_ada(self):
        # Tenant yang produksinya boleh tapi ujinya terkunci HARUS punya cara memulihkan channel.
        src = self._baca("apps/web/src/app/api/channels/[id]/resume/route.ts")
        self.assertIn("tenant_produce_allowed", src, "jalur buka manual wajib pakai gerbang PRODUKSI")
        self.assertIn("tenant_resume_channels", src)
        halaman = self._baca("apps/web/src/app/(app)/channels/[id]/page.tsx")
        self.assertIn("pulihkanProduksi", halaman, "tombol pemulih hilang dari layar channel")

    def test_aturan_tabel_membatasi_jenis_dan_kepemilikan_channel(self):
        """[§10e-3 CELAH A & B] Aturan akses tabel antrean wajib memuat KEEMPAT syarat."""
        sql = self._baca("migrations/0194_antrean_produksi_tak_bisa_disamarkan.sql")
        self.assertIn("job_type IN ('test', 'test_nopub', 'retry')", sql,
                      "jenis pekerjaan tak dibatasi → 'admin_test' jadi pintu belakang lagi")
        self.assertIn("c.tenant_id = (auth.uid())::text", sql,
                      "kepemilikan channel tak diperiksa → produksi bisa dipicu di kanal orang lain")
        self.assertIn("tenant_test_gate", sql)
        self.assertIn("tenant_id = (auth.uid())::text", sql)

    def test_perpanjangan_mandiri_dibatasi(self):
        """[§10e-3 CELAH C] Link 1-klik tak boleh bisa diulang tanpa batas."""
        src = self._baca("src/billing/webhook_app.py")
        self.assertIn("nurture_self_extend_max", src, "batas perpanjangan mandiri hilang")
        self.assertIn("trial_self_extends", src, "penghitung perpanjangan mandiri tak dinaikkan")
        # Setelah jatah habis, tenant WAJIB diarahkan ke jalur uang yang tepat.
        self.assertIn('"arah"', src)
        self.assertIn("upgrade", src)
        self.assertIn("renew", src)
        fe = self._baca("apps/web/src/app/reactivate/page.tsx")
        self.assertIn("Perpanjang sekarang", fe, "tenant yang pernah bayar tak diajak memperpanjang")
        self.assertIn("Lihat paket", fe, "tenant masa coba tak diajak memilih paket")

    def test_rem_darurat_readonly_bagi_tenant(self):
        """[§10e-4 CELAH D] Tenant tak boleh mematikan rem darurat sendiri lewat perubahan langsung."""
        sql = self._baca("migrations/0195_rem_darurat_tak_bisa_dimatikan_tenant.sql")
        self.assertIn("auth.uid() is null", sql, "kunci layanan wajib tetap berwenang")
        for kol in ("production_paused", "production_paused_at", "production_paused_reason"):
            self.assertIn(f"NEW.{kol}", sql, f"{kol} tak dijaga")
        self.assertIn("channels_rem_readonly", sql)

    def test_akun_youtube_wajib_milik_tenant(self):
        """[§10e-4 CELAH E] Saudara kembar celah B: akun yang ditunjuk channel wajib milik tenant."""
        src = self._baca("src/utils/tenant_credentials.py")
        i = src.index("def _account_id_for")
        blok = src[i:i + 1800]
        self.assertIn('.eq("tenant_id", tenant_id)', blok,
                      "akun YouTube diambil tanpa memeriksa pemiliknya → bisa pakai token tenant lain")

    def test_pintu_unduh_hasil_uji_bergerbang(self):
        # Pintu paling senyap: tautan unduh terbit ulang tiap halaman dibuka, tanpa menekan apa pun.
        src = self._baca("apps/web/src/lib/test-run.ts")
        i = src.index("presignBufferKey(s3key)")
        self.assertIn("tenant_produce_allowed", src[:i],
                      "tautan unduh video uji diterbitkan TANPA gerbang — pintu bocor terbuka lagi")


if __name__ == "__main__":
    unittest.main(verbosity=2)
