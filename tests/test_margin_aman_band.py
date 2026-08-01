"""MESIN TIDAK BOLEH MENYATAKAN MENANG DI DALAM DERAUNYA SENDIRI.

Terukur 2026-08-02 (uji rantai penuh 6 channel): BJ Yusroon mendarat **82,1 dtk** pada band
82,5–97,5 — meleset 0,4 detik. Mesinnya tidak salah hitung; ia BERHENTI memperbaiki begitu ramalannya
nyaris menyentuh tepi, padahal ramalan itu punya galat ±1–2 dtk (leave-one-out per suara: Ardi 1,13 ·
Gadis 1,52 · Jenny 0,89 · EL Adam 2,34). Berhenti tepat di tepi = menyerahkan hasil pada undian.

Perbaikannya: SASARAN PENULIS dijauhkan dari tepi sebanyak `script_margin_band_pct` dari lebar band.
GERBANG penilai tidak memakai margin sama sekali — kalau ikut memakai, video yang sebenarnya SAH akan
ditolak, dan itu menukar satu cacat dengan cacat yang lebih mahal.
"""

import src.production.duration_model as dm

_PRESETS = [8, 15, 30, 45, 60, 75, 90]


def test_margin_dibatasi_agar_sasaran_tak_mengerut_jadi_titik():
    lo, hi = 82.5, 97.5                       # lebar 15 dtk
    assert dm._margin_aman(lo, hi, 0) == 0.0
    assert dm._margin_aman(lo, hi, 1.5) == 1.5
    assert dm._margin_aman(lo, hi, 99) == 0.30 * 15 / 2, "margin gila tidak dibatasi"
    assert dm._margin_aman(10.0, 10.0, 5) == 0.0, "band selebar nol menghasilkan margin"


def test_sasaran_kata_menyempit_saat_margin_dipakai():
    tanpa = dm.resep(90, _PRESETS, 3.5)
    dengan = dm.resep(90, _PRESETS, 3.5, margin=1.5)
    assert dengan["kata_min"] > tanpa["kata_min"], "batas bawah sasaran tidak naik"
    assert dengan["kata_maks"] < tanpa["kata_maks"], "batas atas sasaran tidak turun"
    assert dengan["band_video"] == tanpa["band_video"], (
        "band yang dilaporkan ikut berubah — gerbang & laporan harus tetap memakai band SEBENARNYA"
    )


def test_naskah_tepat_di_tepi_dinilai_BELUM_selesai_oleh_penulis():
    """Inti perbaikannya: yang mendarat di bibir band tidak lagi dianggap sudah beres."""
    lo, hi = dm.band_video(90, _PRESETS)
    # cari panjang naskah yang ramalan videonya jatuh persis sedikit di atas batas bawah
    teks = None
    for n in range(80, 400):
        t = " ".join(["kata"] * n) + "."
        v = dm.vonis(t, 90, _PRESETS, 3.5)
        if v["video_prediksi"] >= lo and v["video_prediksi"] <= lo + 1.0:
            teks = t
            break
    assert teks, "tidak menemukan naskah uji di bibir band"
    assert dm.vonis(teks, 90, _PRESETS, 3.5)["status"] == "ok", "prasyarat uji tidak terpenuhi"
    ketat = dm.vonis(teks, 90, _PRESETS, 3.5, margin=1.5)
    assert ketat["status"] == "terlalu_pendek", (
        "dengan margin, naskah di bibir band masih dianggap selesai — perbaikan tidak bekerja"
    )
    assert ketat["kata_selisih"] >= 1


def test_gerbang_tanpa_margin_tidak_menolak_video_yang_SAH():
    """Tanpa margin (cara gerbang memanggil), apa pun di dalam band tetap 'ok'."""
    lo, hi = dm.band_video(60, _PRESETS)
    for n in range(60, 260, 10):
        t = " ".join(["kata"] * n) + "."
        v = dm.vonis(t, 60, _PRESETS, 3.5)
        if lo <= v["video_prediksi"] <= hi:
            assert v["status"] == "ok", f"video {v['video_prediksi']} di dalam band {lo}-{hi} ditolak"


def test_perilaku_lama_persis_saat_margin_nol():
    a = dm.resep(60, _PRESETS, 3.5)
    b = dm.resep(60, _PRESETS, 3.5, margin=0.0)
    assert a == b, "margin=0 mengubah hasil — bukan lagi perilaku lama"
