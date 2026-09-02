"""Setiap kenop yang DISIMPAN ke mesin wajib MENGGERAKKAN pratinjau.

LAHIR DARI TEGURAN OWNER 2026-09-02: *"tenant menggeser slider, layar tidak bergerak sama sekali —
ini bug kerja terakhir, atau memang dari awal tidak serius?"*

Fakta yang ditelusuri: slider `max_chars_per_line` lahir 27-Jul (`6020bbe`) bersama kartu Judul
Pembuka, dan **nol** commit 02-Sep menyentuhnya ⇒ **bukan regresi hari ini, melainkan kelalaian
sejak awal**. Audit menyeluruh sesudah teguran menemukan bukan satu melainkan **DUA** kenop mati:
  • Judul pembuka — `max_chars_per_line` (9 kenop disimpan, 8 dipakai pratinjau)
  • Caption       — `max_words_per_line` (11 disimpan, 10 dipakai)

Kenapa dikunci uji, bukan diingat: kenop di kedua kartu akan terus bertambah, dan kenop yang lahir
tanpa dipasang ke pratinjau **tidak menimbulkan galat apa pun** — layar tetap tampil rapi, tenant
yang menanggung. Tak ada yang menyadarinya kecuali ada tenant komplen. Maka MESIN yang menjaga:
uji ini membandingkan daftar kenop yang disimpan dengan yang benar-benar dibaca pratinjau, dan
merah begitu ada satu yang menggantung.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYAR = "apps/web/src/app/(app)/channels/[id]/page.tsx"


def _isi(rel: str) -> str:
    with open(os.path.join(AKAR, rel), encoding="utf-8") as f:
        return f.read()


def _tanpa_komentar(isi: str) -> str:
    isi = "\n".join(b for b in isi.splitlines() if not b.lstrip().startswith("//"))
    return re.sub(r"/\*.*?\*/", "", isi, flags=re.S)


def _blok_pratinjau(isi: str) -> dict:
    """Isi kedua kanvas pratinjau, berurutan: judul pembuka lalu caption."""
    idx = [m.start() for m in re.finditer(r'<div className="cd-prv-canvas">', isi)]
    assert len(idx) == 2, f"harus ada 2 kanvas pratinjau, ditemukan {len(idx)}"
    return {"hook": isi[idx[0]:idx[0] + 2600], "cap": isi[idx[1]:idx[1] + 2600]}


def _disimpan(isi: str, setter: str) -> set:
    return set(re.findall(setter + r"\(\{ \.\.\.[a-z]+, ([a-z_]+)", isi))


def _dibaca(blok: str) -> set:
    return (set(re.findall(r'(?:hook|cap)(?:Num|Str)\("([a-z_]+)"', blok))
            | set(re.findall(r'(?:hook|cap)\.([a-z_]+)', blok))
            | set(re.findall(r'\b([a-z_]+)Baris\b', blok)))


class TestNolKenopMenggantung(unittest.TestCase):
    """Penjaga umum — inilah yang mencegah kelalaian yang sama terulang pada kenop BERIKUTNYA."""

    def setUp(self):
        self.isi = _tanpa_komentar(_isi(LAYAR))
        self.prv = _blok_pratinjau(self.isi)

    def test_setiap_kenop_judul_pembuka_dibaca_pratinjau(self):
        simpan = _disimpan(self.isi, "setHook")
        self.assertTrue(simpan, "daftar kenop judul pembuka kosong — struktur layar berubah?")
        menggantung = sorted(simpan - _dibaca(self.prv["hook"]))
        self.assertEqual(
            menggantung, [],
            f"kenop judul pembuka disimpan ke mesin tapi TIDAK menggerakkan pratinjau: "
            f"{menggantung} — tenant menggesernya, layar diam.",
        )

    def test_setiap_kenop_caption_dibaca_pratinjau(self):
        simpan = _disimpan(self.isi, "setCap")
        self.assertTrue(simpan, "daftar kenop caption kosong — struktur layar berubah?")
        menggantung = sorted(simpan - _dibaca(self.prv["cap"]))
        self.assertEqual(
            menggantung, [],
            f"kenop caption disimpan ke mesin tapi TIDAK menggerakkan pratinjau: "
            f"{menggantung} — tenant menggesernya, layar diam.",
        )


class TestPotonganBarisMeniruMesin(unittest.TestCase):
    """Bukan sekadar 'dipakai' — cara memotongnya harus sama dengan mesin."""

    def setUp(self):
        self.isi = _tanpa_komentar(_isi(LAYAR))

    def test_judul_dipotong_pada_batas_huruf_seperti_mesin(self):
        """`video_renderer._add_hook_title`: baris pecah bila `len(calon) > max_chars`."""
        self.assertRegex(
            self.isi, r"max_chars_per_line[^\n]*\)|pecahBarisHook",
            "tak ada pemecah baris judul di layar.",
        )
        i = self.isi.find("function pecahBarisHook")
        self.assertNotEqual(i, -1, "helper pemecah baris judul tak ditemukan")
        badan = self.isi[i:i + 700]
        self.assertRegex(
            badan, r"\.length\s*>\s*maks",
            "pemecah baris judul tidak memakai batas JUMLAH HURUF seperti mesin.",
        )

    def test_caption_dikelompokkan_per_jumlah_kata_seperti_mesin(self):
        """`video_renderer._build_ass`: 'Grup kata ke baris fixed (max_words_per_line kata/baris)'."""
        i = self.isi.find("capBaris")
        self.assertNotEqual(i, -1, "pengelompokan baris caption tak ditemukan")
        badan = self.isi[max(0, i - 400):i + 500]
        self.assertRegex(
            badan, r'max_words_per_line',
            "pengelompokan baris caption tidak memakai max_words_per_line.",
        )


if __name__ == "__main__":
    unittest.main()
