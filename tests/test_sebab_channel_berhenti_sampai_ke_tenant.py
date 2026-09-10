"""Saat channel berhenti karena belum lengkap, SEBABNYA wajib sampai ke tenant.

LAHIR DARI KEJADIAN 6–11 SEP 2026. Selama 5 hari owner hanya menerima, berulang tiap jam tayang:

    ⚠️ [RAD The Explorer] Buffer kosong, slot 14:00 dilewati

Itu SELURUH isi pesannya — gejala, bukan sebab. Padahal pada detik itu sistem SUDAH TAHU
jawabannya (`channel_readiness` → "karakter suara"); keterangan itu ditulis ke log server
(`logger.info` di producer), bukan ke tenant. Owner baru menemukan sebabnya 5 hari kemudian dengan
membuka layar sendiri.

Pola YANG BENAR sudah ada di sistem ini — alarm koneksi YouTube putus
(`tenant_credentials.py`) menyebut SEBAB + AKIBAT + LANGKAH:
    "Koneksi YouTube terputus … Produksi & publish DITAHAN … Sambungkan ulang di menu Integrasi"
Uji ini menuntut alarm buffer-kosong setara, dan layar berhenti menyembunyikan label yang SUDAH
ada di tangannya.

RANJAU: penambahan sebab HARAM membuat alarm yang sudah jalan jadi hilang — gerbang gagal dibaca
⇒ alarm tetap terkirim apa adanya (fail-soft).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISHER = "src/orchestrator/publisher.py"
LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar_py(isi: str) -> str:
    return "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("#"))


def _tanpa_komentar_tsx(isi: str) -> str:
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


class TestAlarmBufferKosongMenyebutSebab(unittest.TestCase):
    """T2 — sisi mesin."""

    def setUp(self):
        self.p = _tanpa_komentar_py(_isi(PUBLISHER))

    def _blok_buffer_kosong(self) -> str:
        i = self.p.find("Buffer KOSONG")
        self.assertNotEqual(i, -1, "jalur alarm buffer-kosong tak ditemukan")
        return self.p[max(0, i - 700): i + 1500]

    def test_alarm_memakai_gerbang_kelengkapan_yang_SUDAH_dipakai_mesin(self):
        """Aturan kelengkapan = sumber kebenaran TUNGGAL. Menulis pemeriksaan sendiri di penerbit
        = aturan kedua yang pasti melenceng."""
        blok = self._blok_buffer_kosong()
        self.assertIn(
            "channel_readiness", blok,
            "alarm buffer-kosong tak menanyakan kelengkapan lewat gerbang yang sudah dipakai "
            "mesin produksi — tenant tetap hanya menerima gejala.",
        )

    def test_alarm_menyebut_bagian_yang_kurang(self):
        blok = self._blok_buffer_kosong()
        self.assertRegex(
            blok, r"missing",
            "alarm tak menyertakan daftar bagian yang kurang.",
        )

    def test_alarm_menyebut_langkah_perbaikan(self):
        """Sebab tanpa langkah = tenant tahu rusak tapi tak tahu harus apa (pola alarm koneksi
        YouTube menyebut lokasi perbaikannya)."""
        blok = self._blok_buffer_kosong()
        self.assertRegex(
            blok, r"(Lengkapi|lengkapi)",
            "alarm tak memberi langkah perbaikan yang bisa dikerjakan tenant.",
        )

    def test_pembacaan_gerbang_fail_soft(self):
        """RANJAU: alarm yang sudah jalan HARAM hilang karena keterangan tambahan gagal dibaca."""
        blok = self._blok_buffer_kosong()
        i = blok.find("channel_readiness")
        if i == -1:
            self.skipTest("gerbang belum dipasang — diikat uji di atas")
        self.assertRegex(
            blok[max(0, i - 400): i + 700], r"except\s+Exception",
            "pembacaan gerbang tidak dibungkus penjaga — sekali gagal, alarm buffer-kosong "
            "yang sudah jalan bisa lenyap.",
        )


class TestLayarBerhentiMenYEMBUNYIKANSebab(unittest.TestCase):
    """T3 & T4 — sisi layar. Label presisi SUDAH di tangan FE (`rd.missing`), hanya tak ditampilkan."""

    def setUp(self):
        self.l = _tanpa_komentar_tsx(_isi(LAYAR))

    def test_checklist_menyebut_bagian_yang_kurang_bukan_hanya_titik_merah(self):
        """16 label kelengkapan diringkas jadi 7 baris ⇒ 'karakter suara' kosong hanya tampil
        sebagai titik merah di 'Pengisi Suara (TTS)'. Keterangan `channel_blockers` tak menolong:
        ia hanya terisi bila pilihan TERISI tapi tak sah — kasus 'belum dipilih' nol alasan."""
        i = self.l.find("const REQS")
        self.assertNotEqual(i, -1, "daftar syarat kesiapan tak ditemukan di layar")
        blok = self.l[max(0, i - 2000): i + 3000]
        # JANGKAR DIPERBAIKI SESUDAH SABOTASE: versi pertama hanya mencari kata "kurangJsx"
        # dan TETAP HIJAU saat pemanggilannya dicabut dari daftar — helper yang didefinisikan tapi
        # tak dipakai tak menampilkan apa pun. Yang diikat = PEMANGGILANNYA di baris daftar.
        self.assertIn(
            "kurangJsx(r.kata)", blok,
            "checklist tak MEMANGGIL penampil label kurang di barisnya — tenant melihat titik "
            "merah tanpa tahu bagian mana yang kurang (label sudah ada di `rd.missing`).",
        )
        self.assertRegex(
            blok, r"kata:\s*\"[a-z]+\"",
            "baris syarat tak punya kata pencocok ke `rd.missing` — penampil tak tahu label mana "
            "milik baris mana.",
        )

    def test_banner_belum_lengkap_menjelaskan_cara_produksi_jalan_lagi(self):
        """Kebingungan owner 11-Sep: panel uji tetap terpampang, owner menyangka jeda harus dibuka
        lewat uji. Untuk keadaan 'belum lengkap' produksi jalan SENDIRI begitu dilengkapi."""
        i = self.l.find('eff.key === "incomplete"')
        self.assertNotEqual(i, -1, "cabang banner 'belum lengkap' tak ditemukan")
        blok = self.l[max(0, i - 1200): i + 1200]
        self.assertRegex(
            blok, r"(jalan sendiri|otomatis)",
            "banner tak menjelaskan bahwa produksi jalan sendiri begitu dilengkapi — "
            "tenant menyangka wajib menjalankan uji.",
        )
        self.assertRegex(
            blok, r"<Bi\s+id=\"[^\"]+\"\s+en=\"[^\"]+\"",
            "keterangan banner tidak dwibahasa.",
        )


if __name__ == "__main__":
    unittest.main()
