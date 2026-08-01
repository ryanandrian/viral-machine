"""SATU KOLOM KOEFISIEN HANYA BOLEH LAHIR BILA ADA CUKUP BUKTI UNTUKNYA.

Dua ranjau NYATA yang terhitung langsung di DB 2026-08-01, keduanya dari aturan lama
`any(r[k] for r in rows)` — "ada satu saja, fit-lah":

  1. `sec_per_ellipsis = 0,000` untuk id-ID-ArdiNeural DAN id-ID-GadisNeural. Sebabnya: 36 naskah
     kalibrasi memuat NOL elipsis → kolom seluruh-nol → ter-fit 0,0. Mesin lalu percaya "..." itu
     GRATIS, padahal terukur >1 detik per tanda.
  2. `sec_per_em_dash = 1,137` (Ardi) / `1,262` (Gadis) — di-fit dari 6 naskah / 20 kemunculan.
     Tiga suara Inggris yang datanya tebal: 0,164 · 0,247 · (satu kosong, benar). Jadi angka ID-nya
     5–7× lipat — bukan pengukuran, tapi derau yang menyamar jadi pengukuran.

Yang dikunci di sini: kolom JARANG ditolak sama seperti kolom KOSONG, dan penolakan itu berarti
"pakai angka BAWAAN terukur", bukan "nol detik".
"""

import pytest

from src.production.duration_model import BAWAAN
from src.production.pace_calibration import _FIT_KOL, _fit, _ramal

# Kebenaran buatan: audio = Σ koefisien·ciri. Dipakai supaya bisa dibandingkan dengan angka yang
# ditemukan kembali oleh fit — bukan sekadar "tidak error".
BENAR = {"chars": 0.05, "digits": 0.13, "sentence": 1.10,
         "ellipsis": 1.40, "comma": 0.22, "em_dash": 0.44}


def _sampel(n: int, *, em_dash_di: int = 0, ellipsis_di: int = 0) -> list:
    """n naskah; em-dash/elipsis hanya muncul di `*_di` naskah pertama (itulah variabel yang diuji)."""
    rows = []
    for i in range(n):
        r = {"chars": 300 + i * 17, "digits": (i % 4) * 3, "sentence": 6 + i % 5,
             "ellipsis": 2 if i < ellipsis_di else 0, "comma": 4 + i % 3,
             "em_dash": 3 if i < em_dash_di else 0}
        r["audio"] = sum(BENAR[k] * r[k] for k in BENAR)
        rows.append(r)
    return rows


def _koef(x: list, kol: str):
    return x[_FIT_KOL.index(kol)]


def test_tanda_yang_TIDAK_PERNAH_muncul_tidak_dapat_koefisien_nol():
    """Ranjau #1 apa adanya: 36 naskah tanpa satu pun elipsis."""
    x = _fit(_sampel(36, em_dash_di=20))
    assert x is not None
    assert _koef(x, "ellipsis") is None, \
        "elipsis yang tak pernah muncul dapat koefisien — nol berarti 'gratis' bagi mesin"


def test_tanda_yang_JARANG_muncul_juga_ditolak_meski_bukan_nol():
    """Ranjau #2 apa adanya: em-dash di 6 dari 36 naskah. Aturan lama meluluskannya."""
    x = _fit(_sampel(36, em_dash_di=6))
    assert x is not None
    assert _koef(x, "em_dash") is None, \
        "koefisien dari 6 naskah diterima — inilah yang menghasilkan 1,137 dtk/em-dash (5× kenyataan)"
    assert _koef(x, "chars") is not None, "kolom bukti-tebal ikut mati — fit jadi tak berguna"


def test_tanda_dengan_bukti_CUKUP_tetap_terukur_dan_angkanya_benar():
    """Pagar tidak boleh membuang bukti yang sah — kalau tidak, kita cuma tukar bug."""
    x = _fit(_sampel(36, em_dash_di=14))
    assert _koef(x, "em_dash") == pytest.approx(BENAR["em_dash"], abs=0.02), \
        "em-dash dengan 14 naskah bukti gagal ditemukan kembali"
    assert _koef(x, "chars") == pytest.approx(BENAR["chars"], abs=0.002)
    assert _koef(x, "sentence") == pytest.approx(BENAR["sentence"], abs=0.05)


def test_sel_kecil_TIDAK_membunuh_kolom_yang_hadir_di_semua_naskah():
    """Ambang bukti tak boleh melebihi ukuran selnya sendiri. Sel 14 sampel (PACE_CALIB_MIN_N) dengan
    ambang 10 harus tetap menghasilkan koefisien huruf & kalimat — bila tidak, kalibrasi mati total
    justru untuk suara yang baru punya sedikit data."""
    x = _fit(_sampel(14, em_dash_di=2))
    assert x is not None, "sel 14 sampel gagal di-fit — ambang bukti mematikan kalibrasi"
    assert _koef(x, "chars") is not None and _koef(x, "sentence") is not None
    assert _koef(x, "em_dash") is None


def test_kolom_ditolak_memakai_angka_BAWAAN_bukan_nol_detik():
    """Konsekuensi penolakan harus 'pakai angka terukur bawaan', BUKAN 'tanda ini tak berbiaya'.
    Diuji pada ramalan, bukan pada isi variabel — karena ramalanlah yang menentukan durasi video."""
    rows = _sampel(36, em_dash_di=6)
    x = _fit(rows)
    uji = {"chars": 500, "digits": 0, "sentence": 10, "ellipsis": 0, "comma": 5, "em_dash": 4}
    tanpa_em = _ramal(x, {**uji, "em_dash": 0})
    dengan_em = _ramal(x, uji)
    assert dengan_em - tanpa_em == pytest.approx(4 * BAWAAN["sec_per_em_dash"], abs=1e-6), \
        "em-dash yang ditolak dihitung nol detik — naskah ber-em-dash akan diramal terlalu pendek"


def test_ambang_bukti_bisa_diatur_lewat_config_bukan_angka_mati():
    """Ambang ini kenop operasional, bukan angka mati di kode (aturan owner: nol hardcode)."""
    import inspect

    import src.production.pace_calibration as pc
    src = inspect.getsource(pc._fit)
    assert "PACE_CALIB_MIN_FITUR_N" in src, "ambang bukti ditanam mati di kode"
