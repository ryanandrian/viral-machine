"""LAJU BICARA satu bahasa untuk semua penyedia + biaya jeda yang DIUKUR, bukan disimpulkan.

Tiga ranjau nyata yang dikunci di sini, semuanya terhitung dari DB live 2026-08-01:

  1. **Suara berbayar tak akan pernah terkalibrasi.** Penjaga sampel (0184) membandingkan setelan laju
     sebagai TEKS, dan hanya adaptor Edge yang menulis teks bergaya `+15%`. Sampel ElevenLabs/fal/OpenAI
     karena itu SELALU ditolak — selamanya, tanpa satu pun pesan error. Klaim di dokumen bahwa suara
     ElevenLabs "akan mengkalibrasi diri setelah sampel terkumpul" tidak akan pernah terjadi.

  2. **Tuas kecepatan masih hidup di sisi pembaca.** Solvernya dicabut 2026-07-31, tapi keempat adaptor
     masih MEMBACA `tts_voice_settings[niche].speed`, dan nilai lamanya (0,83–0,93) masih ada di DB
     setiap tenant. Channel aktif BJ Yusroon dibacakan pada −17% sampai hari ini.

  3. **Biaya jeda dari regresi.** em-dash ter-fit 1,137 dtk (Ardi) padahal terukur langsung 0,424.
"""

import pytest

from src.production.duration_model import BAWAAN
from src.production.pace_calibration import _FIT_KOL, _fit_jeda_dipatok, _ramal
from src.production.voice_delivery import (RASIO_ALAMI, laju_sama, rasio_dari_teks, rasio_laju,
                                           rasio_teks, rate_edge)

# ── satu bahasa untuk semua penyedia ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("setelan,harap", [
    ({"rate": "+15%"}, 1.15),      # gaya Edge/SSML
    ({"rate": "+0%"},  1.00),
    ({"rate": "-5%"},  0.95),
    ({"speed": 0.87},  0.87),      # gaya ElevenLabs/fal/OpenAI
    ({"speed": 1.0},   1.00),
    ({},               1.00),      # tak disebut = laju alami
    (None,             1.00),
    ({"speed": "cepat sekali"}, 1.00),   # rusak → alami, bukan render gagal
    ({"speed": 99},    1.00),            # mustahil → alami, bukan diteruskan ke vendor
])
def test_setelan_penyedia_apa_pun_jadi_satu_angka(setelan, harap):
    assert rasio_laju(setelan) == pytest.approx(harap, abs=1e-6)


def test_persen_dan_pengali_TIDAK_tertukar_artinya():
    """Edge '+10%' = lebih CEPAT · ElevenLabs 0,87 = lebih LAMBAT. Membandingkan keduanya sebagai
    teks (cara lama) = membandingkan apel dan jam dinding."""
    assert rasio_laju({"rate": "+10%"}) > RASIO_ALAMI
    assert rasio_laju({"speed": 0.87}) < RASIO_ALAMI


def test_sampel_dari_penyedia_berbayar_TIDAK_lagi_ditolak_membabi_buta():
    """Inti ranjau #1: rasio dari ElevenLabs (0,87 → '0.8700') harus bisa dibandingkan dengan baseline
    katalognya. Cara lama membandingkan '' dengan '+0%' dan selalu menolak."""
    assert laju_sama(rasio_dari_teks("0.8700"), rasio_laju({"speed": 0.87}))
    assert laju_sama(rasio_dari_teks("1.0000"), rasio_laju({"speed": 1.0}))
    assert laju_sama(rasio_dari_teks("+15%"), rasio_laju({"rate": "+15%"})), \
        "bentuk LAMA harus tetap terbaca — kalau tidak, sampel peralihan hilang diam-diam"


def test_laju_tak_diketahui_DITOLAK_bukan_dianggap_sama():
    """Gagal-aman: sampel yang asalnya tak bisa dipastikan lebih baik dibuang daripada mencemari
    kalibrasi. Inilah kesalahan paling mahal 2026-07-31 (dua hari terbuang)."""
    assert laju_sama(None, 1.0) is False
    assert laju_sama(rasio_dari_teks(""), 1.0) is False
    assert laju_sama(rasio_dari_teks("entah"), 1.0) is False
    assert laju_sama(0.87, 1.0) is False, "selisih 13% dianggap laju yang sama"


def test_bolak_balik_rasio_utuh():
    for r in (0.83, 1.0, 1.15):
        assert rasio_dari_teks(rasio_teks(r)) == pytest.approx(r, abs=1e-6)
    assert rate_edge(1.0) == "+0%" and rate_edge(1.15) == "+15%" and rate_edge(0.83) == "-17%"


# ── biaya jeda DIPATOK dari pengukuran ────────────────────────────────────────────────────────────

BENAR = {"chars": 0.05, "digits": 0.13, "sentence": 1.10, "ellipsis": 0.30,
         "comma": 0.22, "em_dash": 0.44}
JEDA = {"sentence": 1.10, "ellipsis": 0.30, "comma": 0.22, "em_dash": 0.44}


def _sampel(n: int) -> list:
    rows = []
    for i in range(n):
        r = {"chars": 300 + i * 17, "digits": (i % 4) * 3, "sentence": 6 + i % 5,
             "ellipsis": 1 if i % 7 == 0 else 0, "comma": 4 + i % 3, "em_dash": 3 if i < 5 else 0}
        r["audio"] = sum(BENAR[k] * r[k] for k in BENAR)
        rows.append(r)
    return rows


def test_jeda_dipatok_menemukan_kembali_biaya_huruf_dan_angka():
    x = _fit_jeda_dipatok(_sampel(30), JEDA)
    assert x is not None
    assert x[_FIT_KOL.index("chars")] == pytest.approx(BENAR["chars"], abs=1e-4)
    assert x[_FIT_KOL.index("digits")] == pytest.approx(BENAR["digits"], abs=1e-3)


def test_angka_jeda_yang_dipatok_TIDAK_ikut_bergeser():
    """Kalau angka terukur ikut di-fit ulang, seluruh gunanya hilang: siklus berikutnya menimpanya
    dengan derau regresi lagi — dan ranjau em-dash 1,137 dtk kembali sendiri."""
    x = _fit_jeda_dipatok(_sampel(30), JEDA)
    for kol, v in JEDA.items():
        assert x[_FIT_KOL.index(kol)] == pytest.approx(v, abs=1e-9), f"{kol} bergeser dari patokan"


def test_em_dash_JARANG_tetap_berbiaya_benar_saat_dipatok():
    """Kasus yang mematahkan regresi: em-dash hanya di 5 dari 30 naskah. Regresi menghasilkan derau;
    patokan hasil pengukuran tidak peduli sesering apa tandanya muncul."""
    x = _fit_jeda_dipatok(_sampel(30), JEDA)
    r = {"chars": 500, "digits": 0, "sentence": 10, "ellipsis": 0, "comma": 5, "em_dash": 4}
    tanpa = _ramal(x, {**r, "em_dash": 0})
    assert _ramal(x, r) - tanpa == pytest.approx(4 * BENAR["em_dash"], abs=1e-6)


def test_data_tak_cukup_untuk_huruf_TIDAK_menghasilkan_angka():
    assert _fit_jeda_dipatok([], JEDA) is None
    assert _fit_jeda_dipatok([{**{k: 0 for k in _FIT_KOL}, "audio": 1.0}] * 5, JEDA) is None


# ── angka bawaan harus yang TERUKUR ───────────────────────────────────────────────────────────────

def test_bawaan_jeda_masuk_akal_menurut_pengukuran():
    """Angka bawaan dipakai 21 suara ElevenLabs/fal yang belum diukur, jadi ia tak boleh jauh dari
    kenyataan. Rentang di bawah = sebaran nyata 5 suara Edge yang diukur langsung 2026-08-01
    (koma 0,172–0,396 · em-dash 0,088–0,424 · elipsis 0,156–0,376 · kalimat 0,848–1,372)."""
    assert 0.15 <= BAWAAN["sec_per_comma"] <= 0.42
    assert 0.08 <= BAWAAN["sec_per_em_dash"] <= 0.45
    assert 0.10 <= BAWAAN["sec_per_ellipsis"] <= 0.40, \
        "angka bawaan elipsis kembali ke wilayah turunan-regresi (1,376) yang terbukti 5–9× terlalu besar"
    assert 0.80 <= BAWAAN["sec_per_sentence"] <= 1.40
