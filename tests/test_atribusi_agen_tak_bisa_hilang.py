"""PENJAGA — atribusi agen HARAM hilang, dan HARAM bergeser.

KEJADIAN NYATA (25/27-Agu-2026). Agen AGEN01 (THETANGGA) komplen: `andarini.nadia` seharusnya
tercatat sebagai pelanggan bawaannya. Diperiksa: tabel `tenant_attribution` **0 baris**, ketiga kode
rujukan **dipakai 0 kali**, buku komisi **0 baris** — padahal program agen hidup sejak 19-Jul.

AKARNYA (100% karya saya sendiri). SSOT §5a merancang atribusi lahir dari *"form daftar"* +
tautan `?ref=KODE`. Halaman daftar punya **DUA pintu**: email+password dan Google. Saya lengkapi
pintu email, dan tak pernah menanyakan pintu Google yang sudah ada lebih dulu. Terukur: **14 dari 14**
tenant sejak program agen lahir memakai **Google** — jadi satu-satunya jalur yang berfungsi adalah
jalur yang tak dipakai siapa pun. Layar bahkan sudah BERJANJI ("✓ Kode valid — pendaftaran Anda
tercatat lewat mitra kami") lalu janji itu dibuang tanpa jejak.

Mandat owner 27-Agu: *"jangan pernah ada lagi masalah/komplen dari agen terkait hal ini."*
Maka yang dijaga di sini BUKAN satu kasus, tapi kelasnya:

  1. SETIAP pintu masuk OAuth di halaman daftar WAJIB menitipkan kode rujukan — pintu ketiga
     (mis. Apple) yang lupa dilengkapi akan tertangkap di sini, bukan oleh komplen agen.
  2. Halaman penerima OAuth WAJIB membaca titipan itu dan menulis atribusi.
  3. Atribusi HARAM lahir untuk akun LAMA (§1b: "tidak ada klaim belakangan, tidak ada rebutan") —
     kalau tidak, agen bisa mengirim tautannya ke tenant yang sudah ada dan mengklaim komisinya.
  4. Atribusi yang sudah ada HARAM bergeser atau hilang — ditegakkan **DATABASE**, bukan disiplin
     kode; sebab sejak perbaikan ini penulisnya ada DUA, dan yang menjaga tak boleh salah satunya.
  5. Kegagalan atribusi WAJIB berisik. Dulu hanya masuk jejak audit yang nol pembaca — itulah
     sebabnya cacat ini baru ketahuan dari komplen agen, bukan dari mesin.
  6. Aturan sah-tidaknya kode hidup di SATU tempat (tak diketik ulang di pintu baru).

⚠️ BATAS JUJUR PENJAGA INI. Butir 1·2·3·5·6 berbasis TEKS/AST — ia menangkap pencabutan (pintu lupa
menitipkan · pembaca dicabut · pagar umur dihapus) tapi TIDAK menangkap pelumpuhan isi fungsi
sementara namanya dibiarkan. Proyek ini belum punya penjalan uji layar. Karena itu butir 4 — satu
yang paling berbahaya bila gagal — dipindah ke **pagar DATABASE** yang diuji BERTRANSAKSI, dan itu
mustahil dilumpuhkan oleh kode layar mana pun.
"""
from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAL_DAFTAR = "apps/web/src/app/auth/page.tsx"
PENERIMA = "apps/web/src/app/auth/callback/route.ts"
SIGNUP = "apps/web/src/app/api/auth/signup/route.ts"
CEK_KODE = "apps/web/src/app/api/partner/check/route.ts"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    """Komentar pernah MENYELAMATKAN uji palsu — kata yang dijaga dikutip di komentar sebelahnya."""
    isi = re.sub(r"/\*.*?\*/", "", isi, flags=re.S)
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))


class TestSetiapPintuMasukMenitipkanKode(unittest.TestCase):
    """Butir 1 — inti cacat 27-Agu: satu pintu dilengkapi, pintu lain dilupakan."""

    # [27-Agu] JANGKAR DIPERBAIKI SESUDAH SABOTASE. Versi pertama uji ini LOLOS saat pemanggilan
    # `titipRef()` dicabut — sebab jendela 600 huruf sebelum panggilan OAuth kebetulan memuat
    # DEFINISI fungsi itu (letaknya persis di atas), dan `titipRefMATI` masih memuat substring
    # `titipRef`. Dua pola uji palsu yang sudah tercatat, saya ulangi. Kini: hitung PEMANGGILAN
    # dengan batas kata, dan jangan pernah bergantung pada kedekatan teks.
    # `function titipRef()` juga cocok dengan pola "titipRef()" — itu sebabnya sabotase pertama
    # (pemanggilan dicabut) masih LOLOS pada percobaan kedua: definisinya sendiri ikut terhitung
    # sebagai pemanggilan. Kini definisi dikecualikan tegas.
    _RX_PANGGIL = re.compile(r"(?<!function\s)(?<![A-Za-z0-9_])titipRef\s*\(\s*\)")
    _RX_DEFINISI = re.compile(r"function\s+titipRef\s*\(")

    def test_setiap_pemanggilan_oauth_menitipkan_kode_rujukan(self):
        isi = _tanpa_komentar(_isi(HAL_DAFTAR))
        pintu = [m.start() for m in re.finditer(r"signInWithOAuth", isi)]
        self.assertTrue(pintu, "tak ada pintu OAuth di halaman daftar — periksa jangkar uji")
        panggil = [m.start() for m in self._RX_PANGGIL.finditer(isi)]
        self.assertGreaterEqual(
            len(panggil), len(pintu),
            f"PINTU MASUK TIDAK MENITIPKAN KODE RUJUKAN: {len(pintu)} pintu OAuth, tapi hanya "
            f"{len(panggil)} pemanggilan penitip. Atribusi agen akan hilang tanpa jejak — persis "
            f"cacat yang membuat agen AGEN01 komplen 27-Agu.")
        # tiap pintu punya penitip SEBELUMNYA di fungsi yang sama (bukan sekadar ada di berkas)
        for i in pintu:
            self.assertTrue(any(0 < i - j < 400 for j in panggil),
                            "ada pintu OAuth tanpa penitip kode di depannya")

    def test_penitip_kode_ada_dan_dipakai(self):
        isi = _tanpa_komentar(_isi(HAL_DAFTAR))
        m = self._RX_DEFINISI.search(isi)
        self.assertIsNotNone(
            m, "penitip kode rujukan TIDAK ADA (atau namanya diubah) — pintu OAuth tak punya cara "
               "membawa kode agen")
        badan = isi[m.start():m.start() + 500]
        self.assertIn("refCode", badan,
                      "penitip tidak menitipkan kode yang diisi/diwarisi tautan ?ref=")
        self.assertIn("mv_ref", badan, "penitip tidak menulis titipan yang dibaca penerima OAuth")


class TestPenerimaMenulisAtribusi(unittest.TestCase):
    """Butir 2 & 3 — pembaca titipan ada, DAN ia menolak akun lama."""

    def test_penerima_membaca_titipan_dan_menulis_atribusi(self):
        isi = _tanpa_komentar(_isi(PENERIMA))
        self.assertIn("tenant_attribution", isi,
                      "halaman penerima OAuth tidak menulis atribusi — kode rujukan tetap terbuang")
        # [27-Agu] Jangkar diperbaiki sesudah sabotase: `const titipan = undefined` LOLOS versi
        # pertama (kata "titipan" masih ada). Yang dijaga = PEMBACAANNYA, bukan namanya.
        self.assertRegex(isi, r'get\(\s*"mv_ref"\s*\)',
                         "penerima TIDAK membaca titipan kode rujukan — kode agen tetap terbuang, "
                         "dan cacat 27-Agu kembali")

    def test_penerima_MENOLAK_akun_lama(self):
        """§1b: 'tidak ada klaim belakangan, tidak ada rebutan'. Tanpa pagar umur, agen bisa
        mengirim tautannya ke tenant LAMA dan mengklaim komisinya — halaman penerima berjalan
        setiap kali orang masuk, bukan hanya saat mendaftar.
        Terukur dari data nyata 27-Agu: akun yang baru daftar berselisih 0 detik antara 'dibuat' dan
        'masuk terakhir'; andarini.nadia berselisih 17 HARI. Jadi umur akun = pembeda yang sah."""
        isi = _tanpa_komentar(_isi(PENERIMA))
        self.assertRegex(isi, r"UMUR_AKUN_BARU_DETIK|umurDetik",
                         "NOL pagar umur akun di penerima OAuth — tenant lama bisa diklaim agen "
                         "hanya dengan masuk lewat tautan rujukan (melanggar §1b)")
        self.assertRegex(isi, r"created_at",
                         "pagar umur tidak membaca kapan akun dibuat")

    def test_aturan_sah_kode_tidak_diketik_ulang(self):
        """Butir 6 — dua tempat menilai keabsahan kode = dua aturan yang bisa bergeser."""
        isi = _tanpa_komentar(_isi(PENERIMA))
        self.assertNotRegex(isi, r"\[A-Z0-9\]\{4,12\}",
                            "aturan format kode DIKETIK ULANG di penerima OAuth — wajib memakai "
                            "pemeriksa yang sudah ada (satu aturan, SSOT §5g.2)")

    def test_kegagalan_atribusi_BERISIK(self):
        """Butir 5 — cacat ini baru ketahuan dari komplen agen justru karena kegagalannya senyap."""
        # KEDUA pintu wajib berisik — satu pintu yang diam adalah pintu tempat kelas ini kembali.
        for rel, nama in ((PENERIMA, "penerima OAuth"), (SIGNUP, "pendaftaran email")):
            with self.subTest(nama):
                self.assertIn("atribusi_gagal", _tanpa_komentar(_isi(rel)),
                              f"kegagalan atribusi di {nama} TIDAK dialarmkan ke admin — ia akan "
                              f"senyap lagi, dan yang memberi tahu kita adalah agen yang komplen")
        # Pengirim alarmnya sendiri wajib ada di mesin (bukan nama op yang menggantung).
        from src.billing import partner
        self.assertTrue(hasattr(partner, "alarm_atribusi_gagal"),
                        "nama op dialamatkan ke pengirim alarm yang TIDAK ADA — alarm jadi kode mati")


class TestPagarDatabaseAtribusiPermanen(unittest.TestCase):
    """Butir 4 — SATU-SATUNYA yang diuji BERTRANSAKSI, sebab ia yang paling berbahaya bila gagal.

    SSOT §1b/§4: atribusi 'ditulis SEKALI saat signup, tidak pernah di-update'. Sampai 27-Agu aturan
    itu **hanya bersandar disiplin kode** — kunci utama mencegah baris kedua, tapi UPDATE bebas.
    Sejak perbaikan ini penulisnya DUA (signup email + penerima OAuth), jadi pagarnya wajib pindah ke
    tempat yang tak bisa dilumpuhkan kode layar mana pun."""

    def _cn(self):
        try:
            import psycopg2
            berkas = os.path.join(AKAR, "SUPABASE-CONNECTION.md")
            uri = next(l.strip() for l in open(berkas, encoding="utf-8")
                       if l.strip().startswith("postgresql://") and "atliatnjhysdibmfypul" in l)
            t = uri[len("postgresql://"):]
            kr, _, al = t.rpartition("@")
            u, _, pw = kr.partition(":")
            hp, _, db = al.partition("/")
            h, _, pt = hp.partition(":")
            return psycopg2.connect(user=u, password=pw, host=h, port=int(pt or 5432),
                                    dbname=db or "postgres", connect_timeout=20)
        except Exception as e:                                   # noqa: BLE001
            self.skipTest(f"DB live tak terjangkau ({type(e).__name__}) — pagar ini menuntut DB")

    def test_atribusi_tak_bisa_DIUBAH(self):
        cn = self._cn()
        try:
            c = cn.cursor()
            c.execute("select tenant_id, agent_id from tenant_attribution limit 1")
            baris = c.fetchone()
            if not baris:
                # Belum ada data: buktikan pagarnya lewat baris SEMENTARA, lalu ROLLBACK.
                c.execute("select id from agents limit 1")
                ag = c.fetchone()
                if not ag:
                    self.skipTest("nol agen di katalog — tak ada bahan untuk menguji pagar")
                c.execute("select code from partner_codes where agent_id = %s limit 1", (ag[0],))
                kd = c.fetchone()
                c.execute("select tenant_id::uuid from tenant_configs "
                          "where tenant_id ~ '^[0-9a-f-]{36}$' limit 1")
                tn = c.fetchone()
                c.execute("insert into tenant_attribution (tenant_id, agent_id, code) "
                          "values (%s,%s,%s)", (tn[0], ag[0], kd[0] if kd else None))
                baris = (tn[0], ag[0])
            gagal = None
            try:
                c.execute("update tenant_attribution set code = code where tenant_id = %s",
                          (baris[0],))
            except Exception as e:                               # noqa: BLE001
                gagal = str(e).splitlines()[0]
            cn.rollback()
            self.assertIsNotNone(
                gagal,
                "ATRIBUSI BISA DIUBAH — §1b/§4 menyebutnya 'tidak pernah di-update', tapi nol "
                "pagar menegakkannya. Sejak penulisnya DUA, satu kekeliruan bisa memindahkan "
                "pelanggan dari satu agen ke agen lain tanpa jejak.")
        finally:
            cn.close()

    def test_atribusi_tak_bisa_DIHAPUS(self):
        """Selaras keputusan yang SUDAH ada: `renewal.py` sengaja TIDAK menghapus atribusi saat data
        tenant dibersihkan, sebab 'dihapus = agen kehilangan komisi bila tenant kembali'."""
        cn = self._cn()
        try:
            c = cn.cursor()
            c.execute("select tenant_id from tenant_attribution limit 1")
            baris = c.fetchone()
            if not baris:
                c.execute("select id from agents limit 1")
                ag = c.fetchone()
                if not ag:
                    self.skipTest("nol agen di katalog")
                c.execute("select code from partner_codes where agent_id = %s limit 1", (ag[0],))
                kd = c.fetchone()
                c.execute("select tenant_id::uuid from tenant_configs "
                          "where tenant_id ~ '^[0-9a-f-]{36}$' limit 1")
                tn = c.fetchone()
                c.execute("insert into tenant_attribution (tenant_id, agent_id, code) "
                          "values (%s,%s,%s)", (tn[0], ag[0], kd[0] if kd else None))
                baris = (tn[0],)
            gagal = None
            try:
                c.execute("delete from tenant_attribution where tenant_id = %s", (baris[0],))
            except Exception as e:                               # noqa: BLE001
                gagal = str(e).splitlines()[0]
            cn.rollback()
            self.assertIsNotNone(gagal, "ATRIBUSI BISA DIHAPUS — agen kehilangan komisi selamanya")
        finally:
            cn.close()

    def test_INSERT_tetap_boleh(self):
        """Pagar yang mengunci segalanya = 'kunci tanpa jalur buka' (sudah ditegur owner).
        Atribusi BARU wajib tetap bisa lahir — itu justru jalur normalnya."""
        cn = self._cn()
        try:
            c = cn.cursor()
            c.execute("select id from agents limit 1")
            ag = c.fetchone()
            if not ag:
                self.skipTest("nol agen di katalog")
            c.execute("select code from partner_codes where agent_id = %s limit 1", (ag[0],))
            kd = c.fetchone()
            # `tenant_configs.tenant_id` bertipe TEXT, `tenant_attribution.tenant_id` UUID —
            # cast eksplisit (bukan cacat produk; PostgREST meng-cast sendiri di jalur aplikasi).
            c.execute("select tenant_id::uuid from tenant_configs "
                      "where tenant_id::uuid not in (select tenant_id from tenant_attribution) "
                      "and tenant_id ~ '^[0-9a-f-]{36}$' limit 1")
            tn = c.fetchone()
            if not tn:
                self.skipTest("semua tenant sudah ber-atribusi")
            c.execute("insert into tenant_attribution (tenant_id, agent_id, code) values (%s,%s,%s)",
                      (tn[0], ag[0], kd[0] if kd else None))
            self.assertEqual(c.rowcount, 1, "atribusi BARU tak bisa lahir — jalur normal terkunci")
            cn.rollback()
        finally:
            cn.close()


class TestKenopKomisiBawaanBenarBenarDipakai(unittest.TestCase):
    """SSOT §4 menjanjikan `partner_default_commission_*` sebagai 'nilai awal saat membuat agen baru',
    dan layar admin menuliskannya sebagai 'prefill'. Diperiksa 27-Agu: **nol pembaca** — dan nilainya
    di DB bahkan tidak sah (`type = 0`, padahal pilihannya `percent`/`flat_idr`). Menurut definisi
    owner (`[B38]`) objek layar yang tak terwiring = BUG."""

    def test_kenop_dibaca_saat_membuat_agen(self):
        ada = []
        for dp, _, fs in os.walk(os.path.join(AKAR, "apps/web/src/app")):
            if "node_modules" in dp:
                continue
            for f in fs:
                if not f.endswith((".ts", ".tsx")):
                    continue
                rel = os.path.relpath(os.path.join(dp, f), AKAR)
                if "app-config" in rel:
                    continue          # layar tempat kenop DISETEL, bukan tempat DIPAKAI
                if "partner_default_commission" in _isi(rel):
                    ada.append(rel)
        self.assertTrue(
            ada,
            "kenop 'Tipe/Nilai Komisi Default (Agen Baru)' NOL PEMBACA — layar admin menjanjikan "
            "prefill yang tak pernah terjadi (SSOT §4). Sambungkan, atau buang dari layar.")
        # [27-Agu] Sesudah sabotase: layar boleh menyebut kenopnya, tapi kalau API berhenti
        # MENGAMBILNYA dari app_config, nilainya tak pernah sampai — dan uji versi pertama lolos.
        api = _isi("apps/web/src/app/api/admin/partners/route.ts")
        for k in ("partner_default_commission_type", "partner_default_commission_value"):
            with self.subTest(k):
                self.assertIn(k, api,
                              f"API partners tidak MENGAMBIL {k} dari app_config — layar tak akan "
                              f"pernah menerimanya, dan prefill kembali jadi janji kosong")
        self.assertIn("value_text", api,
                      "API mengambil hanya kolom `value`; kenop bertipe TEKS tersimpan di "
                      "`value_text` — tanpa itu jenis komisi terbaca '0' (bukan 'percent')")
