"""PENERBITAN TAK BOLEH HILANG, DAN ALARM TAK BOLEH LUPA — dua janji yang dijaga berkas ini.

Ditulis 2026-08-13 sesudah dua kejadian NYATA yang keduanya bermuara pada hal yang sama:
**keadaan penting disimpan di ingatan proses, sementara proses ini bisa mati kapan saja.**

──────────────────────────────────────────────────────────────────────────────────────────────────
A. KABAR "PULIH" YANG TIDAK PERNAH DATANG
   Akun penyimpanan diblokir penyedia 04:24–10:21 (tagihan belum dibayar). Alarm "BERMASALAH"
   terkirim 04:54 ✅. Penyimpanan lalu pulih — dan kabar PULIH TIDAK PERNAH terkirim. Terukur di
   catatan server: hari itu HANYA 2 notifikasi keluar (04:54 & 06:00), tak ada yang ketiga. Owner
   ditinggal percaya seluruh channel masih mati padahal sudah normal berjam-jam.
   Sebabnya: hitungan "sudah gagal berapa kali" hidup di ingatan proses; ingatan itu terhapus DUA
   kali hari itu (mesin mati mendadak 07:54, restart bersih 10:21). Saat penyimpanan pulih,
   hitungannya tinggal 1 (< ambang 2) → mesin menyimpulkan "tak pernah ada masalah" → diam.
   Alarm BAHAYA selamat dari restart, kabar PULIH tidak. **Asimetri itulah bugnya.**

B. VIDEO YANG TERBIT TAPI TIDAK PERNAH TERCATAT
   12-Agu 19:00, channel BISIK NUSANTARA (tenant BERBAYAR): unggahan SELESAI, lalu mesin mati 7
   detik kemudian — sebelum pembukuan. Video xa3Rbi-SbXM hidup, PUBLIK, 1.024 penonton, 11 suka,
   1 komentar. Bagi sistem kita video itu tidak pernah ada: `videos` tanpa barisnya, tautan YouTube
   di catatan produksi kosong, tenant tak dikabari, aset menumpuk, dan mesin pembelajaran tak
   pernah melihat video yang justru paling laku.
   Baris stoknya nyangkut di 'publishing' **permanen** — satu-satunya status dalam-proses yang tak
   punya penyapu, dan asetnya justru DILINDUNGI dari pembersihan selama status itu.

⚠️ YANG PALING PENTING DI BERKAS INI — `test_sudah_mulai_unggah_TIDAK_diterbitkan_ulang`.
   Rencana pertama untuk B berbunyi: "tak ada nomor YouTube ⇒ belum terunggah ⇒ terbitkan ulang".
   Itu SALAH. Unggahan dikirim bertahap; ada celah sempit di mana YouTube sudah menerima potongan
   terakhir tapi mesin kita belum tahu nomornya. Menerbitkan ulang di keadaan itu = VIDEO KEMBAR di
   channel tenant. Uji itu mengunci cabang ketiga: keadaan yang tak bisa dipastikan **dilaporkan**,
   bukan ditebak (§0.6 — perilaku-saat-gagal = gagal jujur).
"""
import importlib
import inspect
import io
import re
import tokenize
from datetime import datetime, timedelta, timezone

import pytest

from src.orchestrator import buffer_janitor as bj


def _kode(obj) -> str:
    """Sumber fungsi TANPA komentar — uji urutan/larangan harus menilai KODE, bukan penjelasannya.

    Ditulis setelah dua uji di berkas ini tersandung komentar buatan sendiri: komentar yang MENYEBUT
    `updated_at` dan `yt_video_id` membuat uji melapor pelanggaran yang tidak ada. Alat ukur yang
    salah menghasilkan temuan palsu — pola yang sudah dua kali menipu di proyek ini.
    """
    toks = [t for t in tokenize.generate_tokens(io.StringIO(inspect.getsource(obj)).readline)
            if t.type != tokenize.COMMENT]
    return tokenize.untokenize(toks)


@pytest.fixture(autouse=True)
def _larang_sambungan_sungguhan(monkeypatch):
    """PAGAR KESELAMATAN — uji TIDAK BOLEH menyentuh basis data produksi.

    Lahir dari kecelakaan nyata 13-Agu: penyapu memanggil `inventory.mark_published()`, yang membuat
    klien Supabase-nya SENDIRI dari env — sehingga uji lokal ini benar-benar mengubah status baris
    PRODUKSI inv=231. Basis data tiruan tidak menolong bila kodenya diam-diam membuka sambungan
    sendiri. Pagar ini mengubah kecelakaan senyap itu menjadi kegagalan uji yang lantang.
    """
    def _tolak(*_a, **_k):
        raise AssertionError(
            "UJI MENCOBA MEMBUKA SAMBUNGAN BASIS DATA SUNGGUHAN. Kode yang diuji membuat kliennya "
            "sendiri alih-alih memakai `sb` yang diberikan — itu jalur yang pernah membuat uji "
            "menulis ke baris produksi. Perbaiki KODENYA (pakai `sb`), jangan pagar ini.")

    import supabase
    monkeypatch.setattr(supabase, "create_client", _tolak)
    from src.orchestrator import inventory
    monkeypatch.setattr(inventory, "_sb", _tolak)
    monkeypatch.setattr(bj, "_sb", _tolak)


# ── Basis data & Telegram TIRUAN (pola `tests/test_drift_alarm_flow.py`) ─────────────────────────

class _Q:
    """Peniru rantai query supabase-py seperlunya: select/eq/limit/execute + update/upsert/insert."""

    def __init__(self, db, tabel):
        self.db, self.tabel = db, tabel
        self._eq, self._count, self._patch, self._insert = {}, False, None, None

    def select(self, *_a, **kw):
        self._count = kw.get("count") == "exact"
        return self

    def limit(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def eq(self, kol, val):
        self._eq[kol] = val
        return self

    def update(self, patch):
        self._patch = patch
        return self

    def insert(self, rows):
        self._insert = rows if isinstance(rows, list) else [rows]
        return self

    def upsert(self, row, **_k):
        baris = self.db.data.setdefault(self.tabel, [])
        for i, r in enumerate(baris):
            if r.get("key") == row.get("key"):
                baris[i] = row
                break
        else:
            baris.append(row)
        return self

    def _cocok(self):
        rows = self.db.data.setdefault(self.tabel, [])
        return [r for r in rows if all(r.get(k) == v for k, v in self._eq.items())]

    def execute(self):
        if self.db.gagal_tabel and self.tabel in self.db.gagal_tabel:
            raise RuntimeError(f"basis data tiruan sengaja gagal untuk {self.tabel}")
        if self._insert is not None:
            self.db.data.setdefault(self.tabel, []).extend(self._insert)
            return type("R", (), {"data": self._insert, "count": len(self._insert)})()
        target = self._cocok()
        if self._patch is not None:
            for r in target:
                r.update(self._patch)
            return type("R", (), {"data": target, "count": len(target)})()
        return type("R", (), {"data": target, "count": len(target)})()


class _DB:
    def __init__(self, **tabel):
        self.data = {"system_state": [], "content_inventory": [], "videos": [],
                     "production_runs": []}
        self.data.update(tabel)
        self.gagal_tabel: set = set()

    def table(self, nama):
        return _Q(self, nama)

    def nilai(self, key):
        for r in self.data["system_state"]:
            if r.get("key") == key:
                return str(r.get("value"))
        return None


@pytest.fixture
def pesan(monkeypatch):
    """Sadap Telegram: pesan dikumpulkan, tak ada yang benar-benar terkirim."""
    keluar = []

    class _TN:
        def notify_admin(self, teks):
            keluar.append(teks)
            return True

        @staticmethod
        def aman(v):
            return str(v)

    import src.utils.telegram_notifier as tn
    monkeypatch.setattr(tn, "TelegramNotifier", _TN)
    return keluar


@pytest.fixture(autouse=True)
def _bersihkan_cadangan():
    """Tiap uji mulai dari nol — cadangan ingatan tidak boleh bocor antar-uji."""
    bj._streak_cadangan = 0
    yield
    bj._streak_cadangan = 0


def _galat_s3(kode="AccountProblem"):
    from botocore.exceptions import ClientError
    return ClientError({"Error": {"Code": kode, "Message": "There is a problem with your account"}},
                       "ListObjectsV2")


# ══ A. ALARM PENYIMPANAN ═════════════════════════════════════════════════════════════════════════

class TestA_AlarmSelamatDariRestart:

    def test_alarm_bahaya_berbunyi_setelah_ambang(self, pesan):
        db = _DB()
        bj._on_loop_error(db, _galat_s3())
        assert pesan == [], "berbunyi pada kegagalan PERTAMA — ambang 2 diabaikan"
        bj._on_loop_error(db, _galat_s3())
        assert len(pesan) == 1 and "BERMASALAH" in pesan[0]

    def test_hitungan_gagal_tersimpan_di_BASIS_DATA(self, pesan):
        """Kalau hitungannya hanya di ingatan, ia lenyap tiap kali mesin mati/di-deploy — dan
        itulah sebab kabar pulih tak pernah datang 13-Agu."""
        db = _DB()
        bj._on_loop_error(db, _galat_s3())
        assert db.nilai("s3_fail_streak") == "1", "hitungan gagal tidak ditulis ke basis data"

    def test_KABAR_PULIH_SELAMAT_DARI_RESTART(self, pesan, monkeypatch):
        """INTI berkas ini. Mesin mati/di-restart di tengah gangguan, LALU penyimpanan pulih.
        Sebelum perbaikan: senyap total. Sesudah: kabar pulih tetap terkirim."""
        db = _DB()
        bj._on_loop_error(db, _galat_s3())
        bj._on_loop_error(db, _galat_s3())
        assert len(pesan) == 1, "alarm bahaya tidak terkirim — prasyarat uji tak terpenuhi"

        # ── SIMULASI RESTART: seluruh ingatan proses hilang (persis kejadian 07:54 & 10:21) ──
        importlib.reload(bj)
        monkeypatch.setattr(bj, "_streak_cadangan", 0, raising=False)
        import src.utils.telegram_notifier as tn
        kelas_tiruan = type(tn.TelegramNotifier)  # notifier tiruan tetap terpasang lewat monkeypatch
        assert kelas_tiruan is not None

        bj._on_loop_success(db)
        assert len(pesan) == 2, ("kabar PULIH TIDAK terkirim setelah restart — inilah bug 13-Agu: "
                                 "owner ditinggal percaya semua channel masih mati")
        assert "PULIH" in pesan[1]

    def test_kabar_pulih_HANYA_SEKALI(self, pesan):
        db = _DB()
        bj._on_loop_error(db, _galat_s3())
        bj._on_loop_error(db, _galat_s3())
        bj._on_loop_success(db)
        bj._on_loop_success(db)
        bj._on_loop_success(db)
        assert len([p for p in pesan if "PULIH" in p]) == 1, "kabar pulih berulang = dering sampah"

    def test_tak_pernah_mengabarkan_PULIH_untuk_yang_tak_diumumkan(self, pesan):
        """Alarm tertahan rem cooldown = owner TIDAK PERNAH diberi tahu ada masalah. Mengirim
        'PULIH' sesudahnya = mengabarkan akhir dari sesuatu yang tak pernah punya awal."""
        db = _DB(system_state=[{"key": "s3_failure_alerted_at",
                                "value": str(int(datetime.now(timezone.utc).timestamp()))}])
        bj._on_loop_error(db, _galat_s3())
        bj._on_loop_error(db, _galat_s3())
        assert pesan == [], "rem cooldown bocor — alarm terkirim padahal masih dalam jendela"
        assert db.nilai("s3_alarm_active") != "1", "penanda menyala padahal alarm tak pernah dikirim"
        bj._on_loop_success(db)
        assert pesan == [], "mengabarkan PULIH untuk masalah yang tak pernah diumumkan"

    def test_sukses_menol_kan_hitungan(self, pesan):
        db = _DB()
        bj._on_loop_error(db, _galat_s3())
        bj._on_loop_success(db)
        assert db.nilai("s3_fail_streak") == "0", "hitungan tak di-nol-kan → alarm palsu berikutnya"

    def test_galat_BUKAN_penyimpanan_tidak_dihitung(self, pesan):
        db = _DB()
        for _ in range(5):
            bj._on_loop_error(db, RuntimeError("gangguan lain, bukan penyimpanan"))
        assert pesan == [], "galat non-penyimpanan ikut menaikkan hitungan → alarm salah sasaran"

    def test_basis_data_tak_terbaca_TETAP_berbunyi(self, pesan):
        """Prinsip yang sudah berlaku di alarm lain: lebih baik dering ganda daripada bisu senyap.
        Kalau status di DB gagal dibaca, cadangan ingatan mengambil alih — bukan menyerah diam."""
        db = _DB()
        db.gagal_tabel = {"system_state"}
        bj._on_loop_error(db, _galat_s3())
        bj._on_loop_error(db, _galat_s3())
        assert len(pesan) == 1, "DB tak terbaca membuat alarm BISU — kegagalan senyap lahir kembali"


# ══ C. STOK NYANGKUT DI "SEDANG DITERBITKAN" ══════════════════════════════════════════════════════

def _baris(meta, umur_menit=120, status="publishing"):
    t = (datetime.now(timezone.utc) - timedelta(minutes=umur_menit)).isoformat()
    return {"id": 231, "tenant_id": "t-1", "channel_id": "c-1", "status": status, "niche": "horror",
            "s3_key": "t-1/c-1/vid.mp4", "created_at": t, "target_slot": t, "updated_at": t,
            "metadata": meta}


class TestC_StokNyangkut:

    def test_ada_nomor_youtube_maka_pembukuan_DITUNTASKAN(self, pesan, monkeypatch):
        """Kasus BISIK NUSANTARA: video memang sudah terbit, hanya pembukuannya tertinggal."""
        terbit = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        row = _baris({"yt_video_id": "xa3Rbi-SbXM", "yt_url": "https://youtu.be/xa3Rbi-SbXM",
                      "yt_upload_started_at": terbit, "run_id": "r-1", "viral_score": 84.7,
                      "duration_secs": 90.5, "size_mb": 42.7,
                      "script": {"title": "Hantu Paling Terkenal", "hook": "h", "topic": "t"}})
        db = _DB(content_inventory=[row], production_runs=[{"run_id": "r-1", "tenant_id": "t-1",
                                                            "status": "success"}])
        ditulis = {}

        class _W:
            def write_video(self, **kw):
                ditulis.update(kw)
                db.data["videos"].append({"video_id": kw["video_id"], "published_at": "SEKARANG"})
                return {"id": 1}

        import src.utils.supabase_writer as sw
        monkeypatch.setattr(sw, "SupabaseWriter", _W)
        monkeypatch.setattr(bj.s3_buffer, "delete", lambda *_a, **_k: None)

        hasil = bj.sweep_publishing_nyangkut(db)

        assert hasil["publishing_rapi"] == 1
        assert row["status"] == "published", "baris stok tetap nyangkut"
        assert ditulis["video_id"] == "xa3Rbi-SbXM"
        assert ditulis["channel_id"] == "c-1", ("baris video tanpa channel → angka per-channel & "
                                                "mesin pembelajaran tetap buta")
        assert db.data["videos"][0]["published_at"] == terbit, (
            "waktu terbit dicap SEKARANG, padahal videonya terbit sebelumnya — analitik & kuota "
            "harian membaca kolom ini, jadi salah hari = angka salah")
        pr = db.data["production_runs"][0]
        assert pr["youtube_video_id"] == "xa3Rbi-SbXM" and pr["youtube_url"].endswith("xa3Rbi-SbXM")
        assert any("dirapikan" in p or "SUDAH terbit" in p for p in pesan), "owner tidak dikabari"

    def test_belum_mulai_unggah_maka_KEMBALI_ke_stok(self, pesan):
        row = _baris({"run_id": "r-2", "script": {"title": "x"}})
        db = _DB(content_inventory=[row])
        hasil = bj.sweep_publishing_nyangkut(db)
        assert hasil["publishing_kembali"] == 1
        assert row["status"] == "ready", "video sehat dibiarkan nyangkut, padahal aman diulang"

    def test_sudah_mulai_unggah_TIDAK_diterbitkan_ulang(self, pesan):
        """⚠️ UJI PALING PENTING. Unggahan sempat dimulai tapi nomor videonya tak tercatat →
        mungkin videonya SUDAH tayang. Menerbitkan ulang = video kembar di channel tenant."""
        row = _baris({"yt_upload_started_at": (datetime.now(timezone.utc)
                                               - timedelta(hours=3)).isoformat(),
                      "run_id": "r-3", "script": {"title": "Ragu"}})
        db = _DB(content_inventory=[row])
        hasil = bj.sweep_publishing_nyangkut(db)
        assert hasil["publishing_ambigu"] == 1
        assert row["status"] == "publishing", ("dikembalikan ke stok → akan diterbitkan ULANG → "
                                              "video kembar di channel tenant")
        assert row["metadata"].get("perlu_ditinjau_manusia") is True
        assert any("diperiksa manusia" in p for p in pesan), "keadaan ambigu tak dilaporkan"

    def test_ambigu_dilaporkan_SEKALI_saja(self, pesan):
        row = _baris({"yt_upload_started_at": (datetime.now(timezone.utc)
                                               - timedelta(hours=3)).isoformat(),
                      "run_id": "r-3", "script": {"title": "Ragu"}})
        db = _DB(content_inventory=[row])
        bj.sweep_publishing_nyangkut(db)
        bj.sweep_publishing_nyangkut(db)
        bj.sweep_publishing_nyangkut(db)
        assert len([p for p in pesan if "diperiksa manusia" in p]) == 1

    def test_penerbitan_yang_masih_BERJALAN_tidak_disentuh(self, pesan):
        row = _baris({"yt_upload_started_at": datetime.now(timezone.utc).isoformat()},
                     umur_menit=0)
        db = _DB(content_inventory=[row])
        hasil = bj.sweep_publishing_nyangkut(db)
        assert hasil == {"publishing_rapi": 0, "publishing_kembali": 0, "publishing_ambigu": 0}
        assert row["status"] == "publishing", "penerbitan yang sedang berjalan malah diganggu"

    def test_tidak_menulis_baris_video_DUA_KALI(self, pesan, monkeypatch):
        """Idempoten: siklus yang terputus di tengah tak boleh melahirkan baris video kembar."""
        row = _baris({"yt_video_id": "VID1", "yt_upload_started_at":
                      (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                      "run_id": "r-4", "script": {"title": "x"}})
        db = _DB(content_inventory=[row], videos=[{"video_id": "VID1"}])
        dipanggil = []

        class _W:
            def write_video(self, **kw):
                dipanggil.append(kw)
                return {}

        import src.utils.supabase_writer as sw
        monkeypatch.setattr(sw, "SupabaseWriter", _W)
        monkeypatch.setattr(bj.s3_buffer, "delete", lambda *_a, **_k: None)
        bj.sweep_publishing_nyangkut(db)
        assert dipanggil == [], "baris video ditulis dua kali untuk satu video yang sama"
        assert row["status"] == "published"


class TestC_PenyapuTerpasangDanWaras:

    def test_penyapu_dipanggil_setiap_siklus(self):
        src = _kode(bj.run_once)
        assert "sweep_publishing_nyangkut" in src, ("penyapu ada tapi tak pernah dijalankan — "
                                                   "lubangnya tetap terbuka")

    def test_TIDAK_memakai_updated_at_sebagai_jangkar_waktu(self):
        """Terbukti pada baris nyata inv=231: `updated_at` TIDAK berubah saat status jadi
        'publishing' (updated_at == created_at). Memakainya = umur salah = keputusan salah."""
        src = _kode(bj.sweep_publishing_nyangkut)
        assert 'updated_at' not in src, ("jangkar waktu memakai updated_at — kolom itu terbukti "
                                        "tidak ikut berubah saat status berganti")
        assert "target_slot" in src and "yt_upload_started_at" in src

    def test_status_publishing_masih_dilindungi_penyapu_yatim(self):
        """ANTI-REGRESI: aset milik baris 'publishing' TIDAK boleh ikut dihapus penyapu-yatim —
        kalau ikut, video yang sedang diunggah kehilangan berkasnya di tengah jalan."""
        src = _kode(bj.reconcile_orphans)
        assert '"publishing"' in src, "status 'publishing' hilang dari daftar lindung penyapu-yatim"


# ══ C. SISI MESIN PENERBIT — jejak unggahan ══════════════════════════════════════════════════════

class TestC_JejakUnggahanDiPenerbit:

    def _src(self):
        from src.orchestrator import publisher
        return _kode(publisher._publish_from_buffer)

    def test_penanda_ditulis_SEBELUM_unggah(self):
        src = self._src()
        i_tanda = src.find("yt_upload_started_at")
        i_unggah = src.find("YouTubePublisher().publish")
        assert 0 <= i_tanda < i_unggah, ("penanda unggahan ditulis SESUDAH unggah — di celah itu "
                                        "kematian mesin membuat penyapu menyangka 'belum diunggah' "
                                        "pada video yang sudah naik ⇒ video kembar")

    def test_penanda_sebelum_unggah_WAJIB_berhasil(self):
        src = self._src()
        blok = src[:src.find("YouTubePublisher().publish")]
        assert "wajib=True" in blok, ("penanda pra-unggah bersifat best-effort — gagal menulisnya "
                                     "lalu tetap mengunggah = risiko video kembar diterima diam-diam")

    def test_nomor_youtube_dicatat_SEGERA_setelah_unggah(self):
        src = self._src()
        i_unggah = src.find("YouTubePublisher().publish")
        i_id = src.find("yt_video_id")
        i_runs = src.find('table("production_runs")')
        assert i_unggah < i_id < i_runs, ("nomor YouTube dicatat terlambat — celah kematian melebar "
                                         "tanpa alasan")

    def test_penanda_pra_unggah_dicabut_saat_percobaan_gagal(self):
        from src.orchestrator import publisher
        src = _kode(publisher.publish_due_for_channel)
        assert re.search(r'_tandai_meta\([^)]*"yt_upload_started_at": None', src, re.S), (
            "penanda basi dibiarkan → percobaan BERIKUTNYA yang gagal akan dianggap ambigu")

    def test_metadata_lain_tidak_ikut_terhapus(self):
        """Penanda ditulis dengan baca-gabung-tulis. Menimpa metadata = membuang naskah, angka
        produksi, dan kunci aset sekaligus."""
        from src.orchestrator import publisher
        db = _DB(content_inventory=[{"id": 9, "metadata": {"script": {"title": "x"}, "run_id": "r"}}])
        item = {"id": 9, "metadata": {"script": {"title": "x"}, "run_id": "r"}}
        publisher._tandai_meta(db, item, {"yt_video_id": "V"})
        meta = db.data["content_inventory"][0]["metadata"]
        assert meta["run_id"] == "r" and meta["script"]["title"] == "x", "isi metadata lain hilang"
        assert meta["yt_video_id"] == "V"
        assert item["metadata"]["yt_video_id"] == "V", "salinan di memori tak ikut → dua versi"

    def test_penanda_wajib_yang_gagal_membatalkan_penerbitan(self):
        from src.orchestrator import publisher
        db = _DB(content_inventory=[{"id": 9, "metadata": {}}])
        db.gagal_tabel = {"content_inventory"}
        with pytest.raises(Exception):
            publisher._tandai_meta(db, {"id": 9, "metadata": {}}, {"x": 1}, wajib=True)
