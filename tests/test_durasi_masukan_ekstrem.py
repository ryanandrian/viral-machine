"""Masukan EKSTREM pada rantai durasi & naskah — penjaga permanen, bukan uji sekali pakai.

Uji biasa memakai masukan wajar. Produksi tidak: LLM bisa mengembalikan teks kosong, satu tanda baca,
5.000 karakter tanpa titik, emoji, angka raksasa; kalibrasi di DB bisa berisi 0/negatif/NaN; overhead
bisa lebih besar dari presetnya. Setiap satu di antaranya bisa mematikan produksi tenant di tengah
jalan, dan tak ada uji "kasus normal" yang akan menangkapnya.

Yang dijaga bukan "tidak crash" saja, tapi juga tidak ada HASIL MUSTAHIL: durasi negatif,
batas terbalik, kata_min > kata_maks, atau koefisien rusak yang lolos pagar.
"""
import itertools
import math

import pytest

from src.intelligence.script_checker import ada_cacat_parah, periksa_naskah, ringkas_temuan
from src.intelligence.script_engine import _count_pauses, _fakta_hilang, _nama_diri
from src.production.duration_model import (
    PAGAR, angka_efektif, band_video, ciri_teks, prediksi_audio, resep, rincian_audio, vonis,
)

TEKS = ["", " ", "\n\n\n", ".", "...", "…", "—", ",,,,", "!?!?!?", "a", "1", "1348", "9" * 300,
        "Satu kalimat tanpa titik akhir", "x" * 5000, "Kata " * 2000, "😀🔥 emoji saja 🎬",
        "Ada\ttab\tdan\nbaris baru\r\ndan   spasi   ganda.",
        "MIXED case DAN Nama Diri Neuschwanstein Pajajaran 1348 2026.",
        "a. b. c. d. e. f. g. h. i. j.", None]
KAL_RUSAK = [None, {}, {"sec_per_char": 0}, {"sec_per_char": -1}, {"sec_per_char": "x"},
             {"words_per_sentence": 0}, {"chars_per_word": 0}, {"sec_per_sentence": 99999},
             {"sec_per_char": 1e9}, {"sec_per_char": float("nan")}, {"sec_per_char": float("inf")}]
TANGGA = [8, 15, 30, 45, 60, 75, 90]
OVERHEAD = [0.0, 2.0, 3.5, 1000.0, -5.0]


@pytest.mark.parametrize("t", TEKS)
def test_teks_ekstrem_tak_pernah_crash_dan_tak_pernah_negatif(t):
    f = ciri_teks(t)
    assert all(v >= 0 for v in f.values() if isinstance(v, int))
    d = prediksi_audio(t)
    assert d >= 0, f"durasi negatif untuk {t!r}"
    r = rincian_audio(t)
    assert abs((r["bicara"] + r["jeda"]) - r["total"]) < 0.02, "rincian tak menjumlah ke total"


@pytest.mark.parametrize("t", TEKS)
def test_pemeriksa_naskah_tahan_profil_niche_rusak(t):
    for prof in (None, {}, {"narration_persona": None}, {"narration_persona": {}},
                 {"narration_persona": {"avoid": ""}}, {"narration_persona": {"avoid": None}},
                 {"narration_persona": {"avoid": "x" * 3000}}):
        h = periksa_naskah(t, niche_profile=prof, content_language="id-ID",
                           beat_keys=["hook", "core_facts"])
        assert isinstance(h, list)
        ringkas_temuan(h)
        assert isinstance(ada_cacat_parah(h), bool)


@pytest.mark.parametrize("ps", [[8, 15, 30, 45, 60, 75, 90], [8], [8, 90], [120, 300, 480, 720], [480]])
def test_band_selalu_naik_dan_tak_negatif(ps):
    for p in ps:
        lo, hi = band_video(p, ps)
        assert 0 <= lo < hi, f"batas tak sah untuk preset {p} di tangga {ps}: {(lo, hi)}"


def test_tangga_kosong_atau_preset_asing_DITOLAK_bukan_dikarang():
    """Gagal-aman: lebih baik menolak daripada mengarang batas. Pemanggil (script_engine & pipeline)
    memperlakukan penolakan ini sebagai 'gerbang pasif'."""
    with pytest.raises(ValueError):
        band_video(45, [])
    with pytest.raises(ValueError):
        band_video(37, TANGGA)


@pytest.mark.parametrize("kal", KAL_RUSAK)
def test_kalibrasi_RUSAK_tak_pernah_lolos_pagar(kal):
    a = angka_efektif(kal)
    for k, (lo, hi) in PAGAR.items():
        v = a[k]
        assert not math.isnan(v), f"'{k}' NaN lolos"
        assert lo <= v <= hi, f"'{k}'={v} lolos pagar {lo}–{hi}"


@pytest.mark.parametrize("kal,ovh,p", list(itertools.product(KAL_RUSAK, OVERHEAD, (8, 60, 90))))
def test_resep_dan_vonis_tetap_masuk_akal_pada_kombinasi_rusak(kal, ovh, p):
    r = resep(p, TANGGA, ovh, kal)
    assert r["kata_min"] <= r["kata_maks"], f"kata_min > kata_maks: {r}"
    assert r["kata_min"] >= 1 and r["kalimat"] >= 1 and r["detik_per_kata"] > 0
    v = vonis("Uji naskah pendek.", p, TANGGA, ovh, kal)
    assert v["status"] in ("ok", "terlalu_panjang", "terlalu_pendek")
    assert v["kata_selisih"] >= 0


def test_penjaga_fakta_tahan_teks_ekstrem():
    for a, b in itertools.product(TEKS[:10], TEKS[:10]):
        assert isinstance(_fakta_hilang(a or "", b or ""), list)
        assert isinstance(_nama_diri(a or ""), set)
        assert set(_count_pauses(a or "")) >= {"sentence", "comma", "ellipsis", "em_dash", "digits"}


def test_naskah_acak_400_kombinasi():
    """Naskah gabungan acak dari kosakata yang paling sering merusak: angka, tanda baca, emoji,
    baris baru, nama diri. Bukan estetika — ini yang benar-benar keluar dari LLM saat gagal."""
    import random
    random.seed(7)
    KOS = ["kota", "1348", "Neuschwanstein", "wabah,", "runtuh.", "—", "...", "seribu", "!", "😀",
           "Pajajaran", "9999999", ":", ";", "\n"]
    for _ in range(400):
        t = " ".join(random.choice(KOS) for _ in range(random.randint(1, 60)))
        p = random.choice(TANGGA)
        assert prediksi_audio(t) >= 0
        v = vonis(t, p, TANGGA, random.choice([0.0, 2.0, 3.5]), random.choice(KAL_RUSAK))
        assert v["status"] in ("ok", "terlalu_panjang", "terlalu_pendek")
        assert isinstance(periksa_naskah(t, content_language="id-ID"), list)
