"""Panel pemulihan channel tak boleh menjebak tenant pada sebab yang PULIH SENDIRI.

JEBAKAN YANG DIJAGA (ditemukan owner 2026-08-06)
Rem darurat menyala karena jatah HARIAN penyedia AI habis (Groq: "tokens per day", pulih ±34 menit).
Panel pemulihan lalu **menyembunyikan tombol "Pulihkan produksi"** selama tenant masih boleh menguji,
dan mengarahkannya ke *"Jalankan uji & pulihkan"*. Untuk sebab ini arahan itu **dijamin gagal**:

  • uji = satu produksi NYATA → memanggil penyedia AI yang jatahnya SEDANG habis
  • ujinya gagal, dan sisa jatah hari itu ikut terbakar untuk sesuatu yang mustahil berhasil
  • jalur gratis ADA — melepas rem "tidak memanggil AI, tidak merender, tidak mengunggah"
    (kalimat itu tertulis di `api/channels/[id]/resume/route.ts` sendiri) — tapi DISEMBUNYIKAN
    tepat pada keadaan yang paling membutuhkannya.

Terukur: channel *Bang Us-Dat* (tenant BERBAYAR, langganan aktif) berhenti 1-Agu 12:00 dan masih
berhenti 6-Agu. Karena langganannya aktif, ia masih "boleh menguji" ⇒ tombol pemulih tak pernah
muncul untuknya.

YANG DIPERBAIKI: jalur pemulihan ditentukan oleh **SEBABNYA**, bukan oleh "boleh menguji atau tidak".

DUA ARAH DIJAGA — arah kedua sama pentingnya:
  (a) sebab yang pulih sendiri / tak diketahui  → tombol pemulih WAJIB tampil
  (b) sebab yang butuh tindakan tenant          → tetap diarahkan ke UJI selama uji boleh.
      Ini melindungi pelajaran mahal 3-Agu: tombol pemulih pernah ditawarkan ke SEMUA orang, tenant
      menekannya tanpa memperbaiki apa pun, mesin mengerem lagi beberapa detik kemudian, dan tenant
      menyimpulkan aplikasinya rusak. Perbaikan hari ini TIDAK boleh menghidupkan kembali itu.
  (c) tombol pemulih WAJIB disertai peringatan jujur ("bila penyebabnya belum lewat, produksi akan
      gagal lagi") — supaya tenant menekan dengan sadar, bukan menebak.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(AKAR, "apps", "web", "src", "components", "pemulihan-channel.tsx")
TITIK_PANGGIL = os.path.join(AKAR, "apps", "web", "src", "app", "(app)", "channels", "[id]", "page.tsx")
RUTE_RESUME = os.path.join(AKAR, "apps", "web", "src", "app", "api", "channels", "[id]", "resume", "route.ts")

# Nama penyedia HARAM muncul di panel ini (aturan yang sudah mengikat berkas ini sejak [B25]:
# pemetaan per KELAS, tidak pernah per merek — kalau tidak, layar basi pada penyedia berikutnya).
MEREK = ("groq", "openai", "gemini", "anthropic", "elevenlabs", "cloudflare", "deepseek")


def _teks(p: str) -> str:
    return open(p, encoding="utf-8", errors="ignore").read()


def _blok_jalur_pemulihan(t: str) -> str:
    """Ambil blok tombol/arahan saja (antara penanda JALUR PEMULIHAN dan bagian keterangan teknis)."""
    m = re.search(r"JALUR PEMULIHAN(.*?)Keterangan teknis", t, re.S)
    return m.group(1) if m else ""


class TestPemindaiBenar(unittest.TestCase):
    """Pagar-untuk-pagar: alat ukur yang salah lebih berbahaya daripada tak mengukur."""

    def test_berkas_ada(self):
        for nama, p in (("panel", PANEL), ("titik panggil", TITIK_PANGGIL), ("rute resume", RUTE_RESUME)):
            self.assertTrue(os.path.exists(p), f"{nama} tak ditemukan: {p}")

    def test_blok_jalur_pemulihan_terambil(self):
        blok = _blok_jalur_pemulihan(_teks(PANEL))
        self.assertGreater(len(blok), 200, "blok JALUR PEMULIHAN tak terbaca — pemindai jadi buta")
        self.assertIn("onPulihkan", blok, "blok yang terambil bukan blok tombol pemulihan")


class TestJalurDitentukanOlehSEBAB(unittest.TestCase):

    def test_blok_render_bercabang_pada_SEBAB_bukan_pada_boleh_menguji(self):
        """Inti perbaikannya. Selama penentunya hanya `bisaUji`, tenant dengan sebab yang pulih
        sendiri akan SELALU diarahkan membakar jatahnya untuk uji yang pasti gagal.

        Yang diperiksa di sini: blok render memakai penjaga ber-nama `ujiJalurYangBenar` (definisinya
        diuji ketat di `test_uji_hanya_ditawarkan_bila_sebabnya_butuh_tindakan`), DAN tidak ada lagi
        percabangan pada `bisaUji` mentah — pola lama itulah jebakannya.
        (Versi pertama uji ini mencari `pulihSendiri` di dalam blok render; itu keliru — penjaganya
        sengaja dinamai dan diletakkan di satu tempat supaya bisa dijaga, jadi blok render memang
        tidak lagi menyebut `pulihSendiri` langsung. Alat ukur yang salah, bukan kodenya.)"""
        blok = _blok_jalur_pemulihan(_teks(PANEL))
        self.assertIn(
            "ujiJalurYangBenar", blok,
            "blok render tak memakai penjaga berbasis SEBAB — kemungkinan kembali bercabang pada "
            "'boleh menguji atau tidak', dan jebakannya lahir lagi.")
        self.assertNotRegex(
            blok, r"[:?]\s*bisaUji\s*\?",
            "blok render masih bercabang langsung pada `bisaUji` — itu pola lama yang menyuruh tenant "
            "menguji meski sebabnya pulih sendiri (uji memanggil penyedia yang jatahnya sedang habis, "
            "jadi dijamin gagal sambil menghabiskan sisa jatah).")

    def test_uji_hanya_ditawarkan_bila_sebabnya_butuh_tindakan(self):
        """Uji masuk akal HANYA sebagai pembuktian bahwa perbaikan tenant berhasil."""
        t = _teks(PANEL)
        m = re.search(r"const\s+ujiJalurYangBenar\s*=\s*([^;]+);", t)
        self.assertIsNotNone(
            m, "penanda `ujiJalurYangBenar` tak ada — syarat kapan uji PANTAS ditawarkan tidak "
               "dinyatakan di satu tempat, jadi tak bisa dijaga dan mudah bergeser diam-diam")
        syarat = m.group(1)
        self.assertIn("bisaUji", syarat, "syarat uji tak lagi memeriksa gerbang uji")
        self.assertRegex(syarat, r"pulihSendiri\s*===\s*false",
                         "uji harus ditawarkan HANYA untuk sebab yang butuh tindakan tenant "
                         "(pulihSendiri === false); di luar itu uji hanya membakar jatah")


class TestTombolPemulihTampilSaatDIBUTUHKAN(unittest.TestCase):

    def test_tombol_pemulih_adalah_jalur_cadangan_bukan_dikubur(self):
        """Sebab pulih-sendiri DAN sebab tak-diketahui (termasuk rem lama seperti Bang Us-Dat yang
        kelasnya kosong) sama-sama harus sampai ke tombol pemulih."""
        blok = _blok_jalur_pemulihan(_teks(PANEL))
        self.assertIn("onPulihkan", blok, "tombol pemulih hilang dari panel")
        # Tombol harus berada di cabang TERAKHIR (fallback) — bukan di dalam cabang ber-`bisaUji`.
        i_uji = blok.find("ujiJalurYangBenar")
        i_btn = blok.find("onPulihkan")
        self.assertGreater(i_btn, i_uji if i_uji >= 0 else -1,
                           "tombol pemulih tidak berada di cabang cadangan — kemungkinan masih "
                           "terkubur di belakang syarat uji")

    def test_peringatan_jujur_menyertai_tombol(self):
        """Tanpa peringatan ini kita menghidupkan kembali insiden 3-Agu: tenant menekan tombol tanpa
        memperbaiki apa pun, mesin mengerem lagi, tenant menyimpulkan aplikasinya rusak."""
        blok = _blok_jalur_pemulihan(_teks(PANEL))
        self.assertRegex(
            blok, r"gagal lagi|berhenti lagi|fail again",
            "tombol pemulih tak disertai peringatan bahwa menekannya sebelum penyebabnya lewat akan "
            "membuat produksi gagal lagi dan mesin berhenti lagi")


class TestTakAdaRegresi(unittest.TestCase):
    """Perbaikan yang DILEBIHKAN = bug baru. Tiga hal ini wajib tetap utuh."""

    def test_jalur_uji_untuk_sebab_butuh_tindakan_tidak_dibuang(self):
        blok = _blok_jalur_pemulihan(_teks(PANEL))
        self.assertRegex(blok, r"Jalankan uji|Run & recover",
                         "arahan ke 'Jalankan uji & pulihkan' terhapus — pelajaran 3-Agu hilang: "
                         "sebab yang butuh tindakan tenant WAJIB dibuktikan satu produksi berhasil")

    def test_gerbang_langganan_tidak_dibuang(self):
        blok = _blok_jalur_pemulihan(_teks(PANEL))
        self.assertIn("bolehPulihkan", blok,
                      "pemeriksaan langganan hilang — tenant non-aktif bisa memulihkan produksi")

    def test_semua_teks_dwibahasa(self):
        """§3.5 CLAUDE.md: satu bahasa = cacat."""
        blok = _blok_jalur_pemulihan(_teks(PANEL))
        n_bi = len(re.findall(r"<Bi\s", blok))
        n_en = len(re.findall(r"\ben=", blok))
        self.assertGreaterEqual(n_bi, 3, "jumlah teks dwibahasa di jalur pemulihan mencurigakan sedikit")
        self.assertEqual(n_bi, n_en, f"ada teks tanpa pasangan Inggris ({n_bi} Bi vs {n_en} en=)")

    def test_tak_ada_nama_penyedia(self):
        """Aturan yang sudah mengikat berkas ini: pemetaan per KELAS, tidak pernah per merek."""
        t = _teks(PANEL).lower()
        ada = [m for m in MEREK if m in t]
        self.assertFalse(ada, f"nama penyedia muncul di panel: {ada} — layar akan basi pada penyedia "
                              f"berikutnya. Pemetaan WAJIB per kelas error.")

    def test_titik_panggil_tidak_perlu_berubah(self):
        """Blast radius terkecil: KONTRAK prop panel tidak berubah.

        [15-Agu] Dulu uji ini mencocokkan teks harfiah `kelas={ch.production_paused_class}`. Yang
        HENDAK dijaga bukan susunan hurufnya, melainkan **kontraknya**: prop `kelas` tetap dikirim
        dan tetap bersumber dari kolom rem — tak ada prop baru, tak ada kontrak yang bergeser.
        Sumbernya kini boleh punya CADANGAN (`|| kelasCadangan`, §8m) karena kolom itu NULL untuk rem
        yang menyala sebelum migr 0196; kosong bukan cuma bikin pesan tumpul — ia mengubah jalur
        pemulihan yang disarankan. Yang dijaga tetap sama, hanya berhenti mengikat bentuk hurufnya.
        """
        t = _teks(TITIK_PANGGIL)
        for prop in ("kelas=", "bisaUji=", "bolehPulihkan=", "onPulihkan="):
            self.assertIn(prop, t, f"prop `{prop}` hilang dari titik panggil — kontraknya berubah")
        self.assertRegex(
            t, r"kelas=\{ch\.production_paused_class\b",
            "prop `kelas` tak lagi bersumber dari `production_paused_class` — panel bisa membaca "
            "dunia yang berbeda dari mesin (§3 SSOT: nol jalur yang bercerita sendiri)")

    def test_golongan_kosong_punya_CADANGAN(self):
        """⛔ §8m — kolom rem NULL tidak boleh melumpuhkan panel.

        migr 0196 (3-Agu) hanya MENAMBAH `production_paused_class`; nol pengisian baris lama. Komentar
        kolomnya bahkan menuliskan sendiri *"NULL = rem menyala sebelum kolom ini ada"* — keadaan itu
        ditulis, lalu tak pernah ditangani. Akibat TERUKUR: 2 channel tenant BERBAYAR diam 13 & 24 hari
        sambil membaca *"kami belum bisa memastikan penyebabnya"*, padahal golongannya tersimpan rapi
        di catatan produksi mereka sendiri — dan untuk Abyss ID panel yang tepat SUDAH ADA
        (*"Ganti model"*). Lebih buruk lagi: `ujiJalurYangBenar = bisaUji && r.pulihSendiri === false`
        ⇒ golongan kosong MENGUBAH jalur pemulihan yang disarankan, bukan sekadar menumpulkan pesan.
        """
        t = _teks(TITIK_PANGGIL)
        self.assertRegex(
            t, r"kelas=\{ch\.production_paused_class\s*\|\|",
            "cadangan golongan hilang — channel yang direm sebelum 3-Agu kembali melihat panel "
            "'penyebab tak diketahui' dan diarahkan ke jalur pemulihan yang keliru")
        self.assertIn(
            "production_runs", t.split("kelasCadangan")[0] if "kelasCadangan" in t else t,
            "cadangan tidak bersumber dari `production_runs` — sumbernya WAJIB sama dengan yang "
            "dibaca rem darurat di mesin, supaya layar & mesin tak membaca dunia yang berbeda")


class TestJalurGratisMemangGRATIS(unittest.TestCase):
    """Dasar seluruh perbaikan ini: melepas rem TIDAK memanggil AI. Bila suatu saat rute itu diubah
    hingga memicu produksi, perbaikan hari ini berubah jadi jebakan yang sama."""

    def test_rute_resume_tidak_memicu_produksi(self):
        t = _teks(RUTE_RESUME)
        self.assertRegex(t, r"tidak memanggil AI|tidak merender|tidak mengunggah",
                         "jaminan 'melepas rem tidak memanggil AI' hilang dari rute pemulihan")
        for haram in ("direct_jobs", "job_type"):
            self.assertNotIn(haram, t,
                             f"rute pemulihan kini menyentuh `{haram}` — artinya ia bisa memicu "
                             f"produksi/uji, dan jalur 'gratis' tak gratis lagi")


if __name__ == "__main__":
    unittest.main(verbosity=2)
