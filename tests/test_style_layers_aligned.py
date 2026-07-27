"""Pagar otomatis: properti gaya TIDAK BOLEH menggantung di satu lapis.

Kelas masalah yang dicegah (insiden 2026-07-27):
  * `alignment`, `shadow`, `italic` dibaca mesin render + tersimpan di DB, tapi tak ada kenopnya
    di layar mana pun — tenant tak bisa mengubah, dan tak ada yang sadar selama berbulan-bulan.
  * `max_lines`, `margin_v`, `bold_keywords`, `outline_alpha` tersimpan di DB tapi TIDAK PERNAH
    dibaca mesin — kenop palsu yang bereproduksi tiap kali layar menyimpan objek gaya utuh.
  * Nilai bawaan gaya judul tercecer di tiga tempat (kode · default kolom DB · layar) dan bisa
    melenceng diam-diam.

ATURAN YANG DIJAGA:
  1. Setiap kunci di DEFAULT gaya (kode) WAJIB benar-benar dibaca fungsi yang memakainya.
  2. Setiap kunci gaya caption yang dibaca mesin WAJIB punya kenop di layar channel.
  3. Nilai bawaan gaya judul pembuka WAJIB seangka antara kode dan layar.

Uji ini sengaja membaca SUMBER (kode BE & FE) — bukan salinan — supaya tak bisa melenceng.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BE = (ROOT / "src/production/video_renderer.py").read_text(encoding="utf-8")

# Repo runtime di VPS sengaja TIDAK membawa folder frontend (VPS = runtime saja). Uji yang butuh
# berkas layar dilewati dgn alasan jelas di lingkungan itu — bukan gagal palsu yang menyesatkan.
_FE_PATH = ROOT / "apps/web/src/app/(app)/channels/[id]/page.tsx"
FE = _FE_PATH.read_text(encoding="utf-8") if _FE_PATH.exists() else ""
butuh_fe = pytest.mark.skipif(not FE, reason="berkas layar tidak ada di lingkungan ini (repo runtime tanpa apps/web)")


def _blok(teks: str, pola: str) -> str:
    m = re.search(pola, teks, re.S)
    assert m, f"blok tidak ditemukan: {pola}"
    return m.group(1)


def _kunci_default_caption() -> list[str]:
    return re.findall(r'"(\w+)":', _blok(BE, r"DEFAULT_CAPTION_STYLE = \{(.*?)\n\}"))


def _kunci_default_hook() -> list[str]:
    return re.findall(r'"(\w+)":', _blok(BE, r"def _load_hook_title_style.*?DEFAULT = \{(.*?)\n        \}"))


def test_default_caption_semuanya_dibaca_mesin():
    """Tiap kunci bawaan caption harus benar-benar dipakai pembuat subtitle."""
    fn = _blok(BE, r"(def _generate_karaoke_ass.*?)(?=\n    def )")
    nganggur = [k for k in _kunci_default_caption() if f'"{k}"' not in fn]
    assert not nganggur, f"kunci caption ada di DEFAULT tapi tak pernah dibaca mesin: {nganggur}"


def test_default_hook_semuanya_dibaca_mesin():
    """Tiap kunci bawaan judul pembuka harus benar-benar dipakai penggambar judul."""
    fn = _blok(BE, r"(def _add_hook_title.*?)(?=\n    def )")
    nganggur = [k for k in _kunci_default_hook() if f'"{k}"' not in fn]
    assert not nganggur, f"kunci judul ada di DEFAULT tapi tak pernah dibaca mesin: {nganggur}"


@butuh_fe
def test_setiap_kenop_caption_terjangkau_tenant():
    """Properti caption yang dibaca mesin WAJIB punya kenop di layar channel."""
    capdef = set(re.findall(r"(\w+):", _blok(FE, r"const CAP_DEFAULT = \{(.*?)\};")))
    hilang = [k for k in _kunci_default_caption() if k not in capdef]
    assert not hilang, (
        f"properti caption dibaca mesin tapi TIDAK ADA kenopnya di layar: {hilang}. "
        "Tambahkan kenopnya, atau keluarkan dari DEFAULT bila memang bukan pilihan tenant."
    )


@butuh_fe
def test_setiap_kenop_hook_terjangkau_tenant():
    """Properti judul pembuka yang dibaca mesin WAJIB punya kenop di layar channel."""
    hookdef = set(re.findall(r"(\w+):", _blok(FE, r"const HOOK_DEFAULT = \{(.*?)\};")))
    hilang = [k for k in _kunci_default_hook() if k not in hookdef]
    assert not hilang, f"properti judul dibaca mesin tapi TIDAK ADA kenopnya di layar: {hilang}"


@butuh_fe
def test_nilai_bawaan_judul_seangka_antara_mesin_dan_layar():
    """Nilai bawaan judul pembuka tak boleh melenceng antara kode mesin dan layar."""
    be_blok = _blok(BE, r"def _load_hook_title_style.*?DEFAULT = \{(.*?)\n        \}")
    fe_blok = _blok(FE, r"const HOOK_DEFAULT = \{(.*?)\};")

    def norm(v: str) -> str:
        return v.strip().strip(",").strip('"').lower()

    be_val = {k: norm(v) for k, v in re.findall(r'"(\w+)":\s*([^,\n]+)', be_blok)}
    fe_val = {k: norm(v) for k, v in re.findall(r'(\w+):\s*([^,}]+)', fe_blok)}
    beda = {k: (be_val[k], fe_val[k]) for k in be_val if k in fe_val and be_val[k] != fe_val[k]}
    assert not beda, f"nilai bawaan judul berbeda antara mesin dan layar: {beda}"


def test_alignment_bukan_kenop_menggantung():
    """`alignment` sengaja jadi konstanta mesin — tak boleh kembali jadi properti gaya."""
    assert "ASS_ALIGNMENT" in BE, "konstanta ASS_ALIGNMENT hilang"
    assert '"alignment"' not in _blok(BE, r"DEFAULT_CAPTION_STYLE = \{(.*?)\n\}"), (
        "`alignment` kembali masuk DEFAULT_CAPTION_STYLE — ia detail mesin subtitle, bukan pilihan "
        "tenant; nilai selain 2 mengembalikan gejala baris melompat."
    )
