"""Pesan sesaat ke tenant (toast/notice sesudah menekan tombol) WAJIB dwibahasa.

TEMUAN 11-SEP (pertanyaan owner: *"apakah hanya pesan ini yang belum dwibahasa?"*). Diukur:
label & tulisan TETAP di layar **bersih** — dijaga `test_dwibahasa_fe_tak_pincang.py`. Yang bocor
adalah **pesan sesaat**: 13 pesan hanya berbahasa Indonesia (setelan channel 5 · channel baru 4 ·
studio niche 2 · jadwal 2). Penjaga lama tak menjangkaunya sebab ia menghitung KESEIMBANGAN
`data-id`/`data-en`; teks yang sama sekali TAK memakai mekanisme dwibahasa tak terlihat olehnya.

KOREKSI RENCANA (teguran owner: *"sudah ada jalur dwibahasa di sistem ini, mengapa anda punya
rencana buat alur baru lagi?"*). Rencana pertama saya hendak menyalin pola "garis miring"
(`"Tersimpan / saved"`, 4 tempat) ke 13 pesan lain. Itu **bukan jalur resmi** — tenant melihat
KEDUA bahasa berjejer sekaligus, dan menyalinnya = memperbanyak jalur kedua.

JALUR RESMI yang dipakai sekarang (sudah ada, tinggal diperluas): pesan disimpan sebagai **KODE**
teks biasa, lalu diterjemahkan SAAT DITAMPILKAN oleh `PesanGalat` (`components/gate-message.tsx`)
→ `<Bi id en/>` → `data-id`/`data-en` → CSS menyembunyikan bahasa yang tak dipakai. Preseden:
penolakan gerbang `GATE:…` (B24). Keuntungannya: tipe state tetap `string` ⇒ nol perubahan tipe,
nol risiko pada logika yang sudah ada.

RANJAU: dua tempat MENGENDUS ISI pesan untuk memilih warna (`nicheMsg.includes("tersimpan")`,
`presetMsg.includes("tersimpan")`). Mengubah teks jadi kode TANPA memperbaiki itu = warna sukses
berubah jadi merah. Itu ikut dibereskan lewat helper, bukan endusan teks.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENERJEMAH = "apps/web/src/components/gate-message.tsx"
LAYAR = {
    "channel": "apps/web/src/app/(app)/channels/[id]/page.tsx",
    "baru": "apps/web/src/app/(app)/channels/new/page.tsx",
    "studio": "apps/web/src/app/(app)/niche-studio/page.tsx",
    "jadwal": "apps/web/src/app/(app)/schedule/page.tsx",
}
# 13 pesan yang terukur satu-bahasa (11-Sep)
SATU_BAHASA = [
    "Durasi tersimpan", "Belum bisa diaktifkan", "Server tak terjangkau", "Niche tersimpan",
    "Nama channel wajib", "Pilih minimal 1 niche", "Mode rotasi butuh minimal 2 niche",
    "Sesi tak valid", "Niche dibuat", "DNA tersimpan", "Jadwal disimpan", "slot (batas tier)",
]


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


class TestMemakaiJalurResmiBukanJalurBaru(unittest.TestCase):
    """Inti teguran owner: perluas yang ADA, jangan bikin mekanisme kedua."""

    def test_penerjemah_yang_sudah_ada_diperluas_bukan_diganti(self):
        p = _tanpa_komentar(_isi(PENERJEMAH))
        self.assertIn("PesanGalat", p, "penerjemah pesan yang sudah ada hilang")
        self.assertRegex(
            p, r'MSG:',
            "penerjemah belum mengenal kode pesan sesaat (`MSG:`) — 13 pesan tetap satu bahasa.",
        )
        self.assertRegex(
            p, r"<Bi\s+id=", "kode pesan tidak diterjemahkan lewat komponen dwibahasa `Bi`.")

    def test_nol_mekanisme_dwibahasa_baru(self):
        """Kalau lahir komponen/berkas penerjemah kedua, itu jalur baru — persis yang dilarang."""
        p = _isi(PENERJEMAH)
        self.assertEqual(
            p.count("function Bi("), 1,
            "ada lebih dari satu definisi `Bi` di penerjemah — mekanisme bercabang.")

    def test_pola_garis_miring_tak_bertambah(self):
        """Pola `"Tersimpan / saved"` menampilkan KEDUA bahasa sekaligus ke tenant. Ia sudah ada di
        4 tempat (warisan); uji ini mencegahnya BERTAMBAH."""
        n = 0
        for rel in LAYAR.values():
            n += len(re.findall(r'["`][^"`]*tersimpan[^"`]*/\s*saved', _isi(rel), re.I))
        self.assertLessEqual(
            n, 4, f"pola garis-miring bertambah jadi {n} — tenant melihat dua bahasa sekaligus.")


class TestTigaBelasPesanTakLagiSatuBahasa(unittest.TestCase):
    def test_tak_ada_lagi_pesan_indonesia_telanjang(self):
        gagal = []
        for nama, rel in LAYAR.items():
            src = _tanpa_komentar(_isi(rel))
            for frasa in SATU_BAHASA:
                # frasa boleh ada di penerjemah/kode, TAPI tak boleh lagi jadi isi setXxx(...)
                for m in re.finditer(r'set\w*(?:Msg|Err|Toast)\w*\(\s*(?:\{[^}]*text:\s*)?[`"\']([^`"\']*)', src):
                    if frasa in m.group(1):
                        gagal.append(f"{nama}: {frasa}")
        self.assertEqual(
            sorted(set(gagal)), [],
            "pesan sesaat masih disimpan sebagai teks Indonesia telanjang (seharusnya KODE yang "
            f"diterjemahkan saat tampil): {sorted(set(gagal))}")

    def test_setiap_kode_punya_terjemahan_kedua_bahasa(self):
        p = _tanpa_komentar(_isi(PENERJEMAH))
        # JANGKAR DIPERBAIKI: kunci di daftar terjemahan ditulis TANPA awalan `MSG:` (awalan itu
        # ditambahkan `msg()`), jadi pola lama menghitung NOL — cacat uji, bukan cacat kode.
        blok_daftar = p[p.find("MSG_TEKS"): p.find("export function msg")]
        kode = set(re.findall(r'^\s*([a-z0-9_]+):\s*\(', blok_daftar, re.M))
        self.assertGreaterEqual(
            len(kode), 12, f"kode pesan terlalu sedikit ({len(kode)}) — 13 pesan belum tercakup.")
        # JANGKAR DIPERBAIKI SESUDAH SABOTASE: `p.find(f"{k}:")` menemukan kemunculan PERTAMA kunci
        # di SELURUH berkas — termasuk di daftar `pesanSukses`, yang isinya bukan terjemahan. Uji
        # karena itu TETAP HIJAU saat satu terjemahan Inggris dicabut. Kini dicari HANYA di dalam
        # blok daftar terjemahan, dan potongannya berhenti di kunci berikutnya.
        for k in sorted(kode):
            i = blok_daftar.find(f"{k}:")
            self.assertNotEqual(i, -1, f"kunci {k} tak ada di daftar terjemahan")
            sisa = blok_daftar[i + len(k) + 1:]
            m = re.search(r"\n\s{2}[a-z0-9_]+:\s*\(", sisa)
            blok = sisa[: m.start()] if m else sisa
            with self.subTest(kode=k):
                # kode berparameter memakai `id={`…`}` (template), bukan `id="…"` — keduanya sah
                self.assertRegex(
                    blok, r'<Bi\s+id=(?:"[^"]+"|\{`[^`]+`\})\s*\n?\s*en=(?:"[^"]+"|\{`[^`]+`\})',
                    f"kode MSG:{k} tak punya pasangan terjemahan ID+EN yang lengkap.")


class TestWarnaTakLagiMengendusTeks(unittest.TestCase):
    """RANJAU: mengubah teks jadi kode tanpa ini ⇒ pesan sukses berubah jadi MERAH."""

    def test_nol_endusan_kata_tersimpan_untuk_menentukan_warna(self):
        src = _tanpa_komentar(_isi(LAYAR["channel"]))
        endus = re.findall(r'\w+\.includes\("tersimpan"\)', src)
        self.assertEqual(
            endus, [],
            f"warna pesan masih ditentukan dengan mengendus kata di dalam teks: {endus} — "
            "rapuh, dan langsung salah begitu teksnya jadi kode.")


if __name__ == "__main__":
    unittest.main()
