"""Channel yang SEDANG AKTIF tak boleh bisa dijatuhkan jadi tak-lengkap oleh satu penyimpanan.

LAHIR DARI KEJADIAN 6–11 SEP 2026 (channel owner "RAD The Explorer" diam 6 hari, stok terkuras).
Rantai yang terbukti: tenant mengganti penyedia suara ElevenLabs→OpenAI ⇒ layar MENGOSONGKAN model
& karakter suara (perilaku benar, voice lama tak sah di penyedia baru) ⇒ tombol Simpan MENERIMANYA
⇒ channel jatuh tak-lengkap ⇒ mesin melewatinya ⇒ 5 hari alarm "Buffer kosong" tanpa pernah
menyebut sebabnya.

AKAR — SATU, bukan empat. Gerbang `channels_activation_gate` menjaga pintu "MENGAKTIFKAN" channel
(tak lengkap ⇒ ditolak + disebutkan kurangnya), tapi syaratnya
`NEW.is_active and (INSERT or not OLD.is_active)` ⇒ channel yang SUDAH aktif tak pernah diperiksa
lagi. Terbukti terukur: 4 channel separuh di sistem semuanya NONAKTIF (gerbang menolak mereka
aktif), sementara channel aktif bisa jatuh separuh kapan saja.

KENAPA DI DB, BUKAN DI LAYAR: aturan kelengkapan `channel_missing()` adalah SUMBER KEBENARAN
TUNGGAL yang sudah dipakai layar DAN mesin. Memagari di layar berarti menulis aturan KEDUA yang
pasti melenceng seiring waktu, dan hanya menutup satu pintu dari banyak (kartu suara · kartu naskah
· kartu visual · layar admin · API · skrip). Satu pagar di DB menutup semuanya dengan aturan yang
sama.

DUA HAL YANG PAGAR INI HARAM RUSAK (justru lebih berbahaya dari bug aslinya):
  • Channel yang SUDAH tak lengkap wajib TETAP bisa disimpan — kalau tidak, tenant yang channelnya
    rusak karena katalog berubah TERSANDERA: ia tak bisa menyimpan perbaikan apa pun.
  • Channel NONAKTIF wajib tetap bebas disiapkan bertahap — di situ gerbang aktivasi sudah berjaga.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPagarKelengkapanChannelAktif(unittest.TestCase):
    """Dibuktikan BERTRANSAKSI ke DB live lalu ROLLBACK — nol data berubah."""

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

    @staticmethod
    def _sebagai_tenant(c, tenant_id):
        """Tiru tenant yang menyimpan lewat layar. `auth.uid()` membaca klaim JWT
        (`request.jwt.claims`); psycopg2 tanpa klaim = MESIN (service_role) ⇒ auth.uid() NULL.
        Pagar WAJIB memakai pembeda ini — persis pola `trg_channels_rem_readonly` yang sudah ada —
        sebab mesin SAH menjatuhkan kelengkapan: `youtube_oauth.py:401` mengosongkan
        `youtube_account_id` saat izin Google dicabut. Memagari mesin = mesin gagal bekerja."""
        c.execute("select set_config('request.jwt.claims', %s, true)",
                  ('{"sub":"%s","role":"authenticated"}' % tenant_id,))

    @staticmethod
    def _sebagai_mesin(c):
        c.execute("select set_config('request.jwt.claims', '', true)")

    @staticmethod
    def _coba(c, sql, params):
        """Jalankan di savepoint; return None bila DITERIMA, atau pesan galat bila DITOLAK."""
        c.execute("SAVEPOINT uji")
        try:
            c.execute(sql, params)
            c.execute("RELEASE SAVEPOINT uji")
            return None
        except Exception as e:                                   # noqa: BLE001
            c.execute("ROLLBACK TO SAVEPOINT uji")
            return str(e).splitlines()[0]

    def _channel_aktif_lengkap(self, c):
        c.execute("""select id, channel_name, tenant_id from channels
                      where is_active
                        and tenant_id ~ '^[0-9a-f-]{36}$'
                        and coalesce(array_length(channel_missing(channels.*),1),0) = 0
                      limit 1""")
        r = c.fetchone()
        if not r:
            self.skipTest("nol channel aktif-dan-lengkap — tak ada bahan menguji pagar")
        return r

    # ── INTI: perilaku yang diperbaiki ───────────────────────────────────────
    def test_channel_aktif_TAK_BISA_dijatuhkan_jadi_tak_lengkap(self):
        cn = self._cn()
        try:
            c = cn.cursor()
            cid, nama, tid = self._channel_aktif_lengkap(c)
            self._sebagai_tenant(c, tid)
            galat = self._coba(c, "update channels set voice_key = null where id = %s", (cid,))
            cn.rollback()
            self.assertIsNotNone(
                galat,
                f"channel AKTIF '{nama}' bisa dijatuhkan jadi tak-lengkap oleh satu penyimpanan "
                "(karakter suara dikosongkan). Inilah jalan yang membuat channel owner diam 6 hari: "
                "layar menjawab 'Tersimpan', channel mati, tenant tak diberi tahu.")
            self.assertIn(
                "lengkap", galat.lower(),
                f"ditolak, tapi pesannya tak menyebut kelengkapan — tenant tak tahu harus apa: {galat}")
        finally:
            cn.close()

    def test_pesan_penolakan_menyebut_apa_yang_kurang(self):
        """Ditolak tanpa menyebut kurangnya = tenant menebak. Gerbang aktivasi sudah menyebutkannya;
        pintu kedua ini wajib setara."""
        cn = self._cn()
        try:
            c = cn.cursor()
            cid, _, tid = self._channel_aktif_lengkap(c)
            self._sebagai_tenant(c, tid)
            galat = self._coba(c, "update channels set voice_key = null where id = %s", (cid,))
            cn.rollback()
            if galat is None:
                self.skipTest("pagar belum terpasang — diikat uji di atas")
            self.assertIn(
                "karakter suara", galat.lower(),
                f"pesan tak menyebut bagian yang kurang ('karakter suara'): {galat}")
        finally:
            cn.close()

    # ── PENJAGA: yang HARAM rusak oleh pagar di atas ─────────────────────────
    def test_channel_TAK_LENGKAP_tetap_bisa_diperbaiki(self):
        """ANTI-SANDERA. Channel aktif bisa jatuh tak-lengkap TANPA tenant menyentuhnya — mis. model
        pilihannya dinonaktifkan di katalog. Kalau pagar menolak SEMUA penyimpanan saat tak lengkap,
        tenant tak bisa menyimpan perbaikan apa pun: lebih buruk dari bug aslinya."""
        cn = self._cn()
        try:
            c = cn.cursor()
            cid, nama, tid = self._channel_aktif_lengkap(c)
            # jatuhkan channel LEWAT KATALOG (bukan lewat channels) → tiru model dipensiunkan
            c.execute("select tts_model, tts_provider from channels where id = %s", (cid,))
            mk, pv = c.fetchone()
            c.execute("""update ai_models set is_active = false
                          where model_key = %s and provider_key = %s and component = 'tts'""", (mk, pv))
            c.execute("select coalesce(array_length(channel_missing(channels.*),1),0) "
                      "from channels where id = %s", (cid,))
            kurang = c.fetchone()[0]
            self.assertGreater(kurang, 0, "penyiapan uji gagal: channel belum jadi tak-lengkap")
            self._sebagai_tenant(c, tid)
            galat = self._coba(c, "update channels set channel_name = channel_name where id = %s", (cid,))
            cn.rollback()
            self.assertIsNone(
                galat,
                f"channel '{nama}' yang SUDAH tak-lengkap TIDAK bisa disimpan lagi ⇒ tenant "
                f"tersandera, mustahil memperbaiki channelnya sendiri: {galat}")
        finally:
            cn.close()

    def test_channel_nonaktif_tetap_bebas_disiapkan_bertahap(self):
        """Di channel nonaktif, gerbang aktivasi sudah berjaga di pintu keluarnya. Memagari
        penyimpanannya = menghalangi tenant menyiapkan channel baru sepotong-sepotong."""
        cn = self._cn()
        try:
            c = cn.cursor()
            c.execute("select id, channel_name, tenant_id from channels "
                      "where not is_active and tenant_id ~ '^[0-9a-f-]{36}$' limit 1")
            r = c.fetchone()
            if not r:
                self.skipTest("nol channel nonaktif — tak ada bahan")
            cid, nama, tid = r
            self._sebagai_tenant(c, tid)
            galat = self._coba(c, "update channels set voice_key = null where id = %s", (cid,))
            cn.rollback()
            self.assertIsNone(
                galat, f"channel NONAKTIF '{nama}' tak bisa disiapkan bertahap: {galat}")
        finally:
            cn.close()

    def test_pintu_aktivasi_tetap_menolak_channel_tak_lengkap(self):
        """Perilaku yang SUDAH benar sejak 20-Jun — pagar baru haram melemahkannya."""
        cn = self._cn()
        try:
            c = cn.cursor()
            c.execute("""select id, channel_name from channels
                          where not is_active
                            and coalesce(array_length(channel_missing(channels.*),1),0) > 0
                          limit 1""")
            r = c.fetchone()
            if not r:
                self.skipTest("nol channel nonaktif-dan-tak-lengkap — tak ada bahan")
            cid, nama = r
            galat = self._coba(c, "update channels set is_active = true where id = %s", (cid,))
            cn.rollback()
            self.assertIsNotNone(
                galat, f"channel tak-lengkap '{nama}' BISA diaktifkan — gerbang 20-Jun jebol.")
        finally:
            cn.close()


    def test_MESIN_tetap_bisa_mencabut_koneksi_youtube(self):
        """RANJAU TERBESAR pagar ini. `youtube_oauth.py:401` mengosongkan `youtube_account_id`
        saat izin Google dicabut/kedaluwarsa — itu MENJATUHKAN kelengkapan, dan itu SAH: mesin
        wajib bisa menghentikan channel yang koneksinya mati. Bila pagar ikut memagari mesin,
        pencabutan gagal ⇒ mesin terus mencoba menerbitkan dgn koneksi mati (lebih buruk dari
        bug aslinya). Pembeda = `auth.uid()`, pola yang sudah dipakai `trg_channels_rem_readonly`."""
        cn = self._cn()
        try:
            c = cn.cursor()
            cid, nama, _ = self._channel_aktif_lengkap(c)
            self._sebagai_mesin(c)
            galat = self._coba(c, "update channels set youtube_account_id = null where id = %s", (cid,))
            cn.rollback()
            self.assertIsNone(
                galat,
                f"MESIN tak bisa mencabut koneksi YouTube channel '{nama}' — pagar memagari mesin: "
                f"channel dgn koneksi mati mustahil dihentikan sistem: {galat}")
        finally:
            cn.close()


if __name__ == "__main__":
    unittest.main()
