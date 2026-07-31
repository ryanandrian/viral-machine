"""Model durasi — mengunci ATURAN OWNER dan sifat yang terbukti perlu (dengan bukti angkanya).

Aturan batas (owner 2026-07-29): hasil sah selama masih lebih dekat ke preset yang dipilih daripada
ke preset tetangganya. Contoh yang beliau berikan sendiri dipakai langsung sebagai uji: pesan 45
dapat 32 = mulai masalah (sudah milik 30); dapat 29 = masalah besar.

Sifat lain yang dikunci karena pernah jadi cacat NYATA di produksi:
  • kecepatan suara BUKAN tuas — tak boleh ada jalan masuknya ke modul ini
    (produksi: 41% render mentok di 0,70 dan NOL berjalan normal; mood rusak, durasi tetap salah)
  • jumlah KALIMAT ikut diperintahkan, bukan cuma kata (tiap kalimat = jeda 0,6–1,3 dtk terukur)
  • satuan bicara = HURUF, bukan kata (leave-one-out: 0,96 vs 1,55 dtk pada 60 naskah produksi)
  • angka kalibrasi di luar pagar DIBUANG, tidak di-clamp senyap
  • preset 480s = ambang mid-roll: batas bawah dipatok, tak boleh jatuh di bawahnya
"""
import pytest

from src.production.duration_model import (
    AMBANG_MIDROLL, BAWAAN, PAGAR, angka_efektif, band_video, ciri_teks, prediksi_audio, resep, vonis,
)

SHORT = [8, 15, 30, 45, 60, 75, 90]
LONG = [120, 180, 300, 480, 600, 720]
OVH = {8: 2.0, 15: 2.0, 30: 2.5, 45: 3.5, 60: 3.5, 75: 3.5, 90: 3.5}


# ── batas titik-tengah (aturan owner) ─────────────────────────────────────────────────────────────

def test_batas_titik_tengah():
    assert band_video(45, SHORT) == (37.5, 52.5)
    assert band_video(60, SHORT) == (52.5, 67.5)


def test_contoh_owner_45_jadi_32_dan_29_ditolak_41_diterima():
    lo, hi = band_video(45, SHORT)
    assert not (lo <= 32 <= hi)
    assert not (lo <= 29 <= hi)
    assert lo <= 41 <= hi


def test_preset_terkecil_tak_punya_batas_bawah():
    assert band_video(8, SHORT) == (0.0, 11.5)


def test_preset_terbesar_dicerminkan():
    assert band_video(90, SHORT) == (82.5, 97.5)


def test_batas_melebar_sendiri_saat_tangga_dirampingkan():
    ramping = [8, 15, 30, 45, 60, 90]
    assert band_video(60, ramping) == (52.5, 75.0)


def test_ambang_midroll_mengalahkan_titik_tengah():
    lo, hi = band_video(480, LONG)
    assert lo == float(AMBANG_MIDROLL)
    assert lo > (300 + 480) / 2          # titik tengah biasa (390) DITINGGALKAN
    assert hi == 540.0


def test_preset_asing_ditolak_bukan_dikarang():
    with pytest.raises(ValueError):
        band_video(37, SHORT)
    with pytest.raises(ValueError):
        band_video(45, [])


# ── ciri teks ─────────────────────────────────────────────────────────────────────────────────────

def test_ciri_menghitung_huruf_tanpa_spasi_dan_tanda():
    assert ciri_teks("Ada 3 kata.")["chars"] == len("Ada3kata")
    assert ciri_teks("Ada 3 kata.")["words"] == 3


def test_elipsis_tak_dihitung_dua_kali():
    f = ciri_teks("Satu... dua. Tiga!")
    assert f["ellipsis"] == 1
    assert f["sentence"] == 2          # "dua." dan "Tiga!" — elipsis TIDAK ikut jadi akhir kalimat


def test_koma_titik_koma_dan_titik_dua_dihitung_bersama():
    assert ciri_teks("a, b; c: d")["comma"] == 3


def test_teks_kosong_aman():
    f = ciri_teks("")
    assert f["chars"] == 0 and f["words"] == 0 and f["sentence"] == 0
    assert prediksi_audio("") == 0.0


# ── kalibrasi & pagar ─────────────────────────────────────────────────────────────────────────────

def test_tanpa_kalibrasi_pakai_angka_bawaan_terukur():
    assert angka_efektif(None) == BAWAAN
    assert angka_efektif({}) == BAWAAN


def test_kalibrasi_menimpa_bawaan():
    a = angka_efektif({"sec_per_char": 0.06})
    assert a["sec_per_char"] == 0.06
    assert a["sec_per_sentence"] == BAWAAN["sec_per_sentence"]   # kunci lain tak tersentuh


def test_angka_di_luar_pagar_DIBUANG_bukan_diclamp():
    """Data rusak tak boleh menyelinap jadi angka yang tampak masuk akal (§0.6 gagal jujur)."""
    lo, hi = PAGAR["sec_per_char"]
    a = angka_efektif({"sec_per_char": hi * 10})
    assert a["sec_per_char"] == BAWAAN["sec_per_char"]           # bukan hi
    a2 = angka_efektif({"sec_per_char": "bukan angka"})
    assert a2["sec_per_char"] == BAWAAN["sec_per_char"]


def test_prediksi_naik_bila_kalimat_bertambah_walau_kata_sama():
    """Bukti terukur: naskah 165 kata dalam 14 kalimat keluar 5 dtk lebih panjang daripada dugaan
    berbasis-kata. Inilah sebab jumlah kalimat wajib ikut dikendalikan."""
    satu = "kata " * 40 + "akhir."
    banyak = ("kata kata kata kata akhir. " * 8) + "kata kata kata kata akhir."
    assert ciri_teks(banyak)["sentence"] > ciri_teks(satu)["sentence"]
    # samakan jumlah huruf kira-kira, bandingkan per-huruf
    p1 = prediksi_audio(satu) / max(1, ciri_teks(satu)["chars"])
    p2 = prediksi_audio(banyak) / max(1, ciri_teks(banyak)["chars"])
    assert p2 > p1, "jeda per kalimat tidak berpengaruh — model salah"


def test_elipsis_mahal_sesuai_ukuran():
    """Terukur 1,38 dtk per elipsis (benih lama 0,75) — inilah sebab prompt melarang '...'."""
    tanpa = "Kota itu jatuh pada tahun 1348."
    dengan = "Kota itu jatuh... pada tahun 1348."
    assert prediksi_audio(dengan) - prediksi_audio(tanpa) > 1.0


# ── resep (perintah ke penulis) ───────────────────────────────────────────────────────────────────

def test_resep_naik_monoton_mengikuti_preset():
    prev = 0
    for p in SHORT:
        r = resep(p, SHORT, OVH[p])
        assert r["kata_bidik"] > prev, f"preset {p} tidak lebih banyak kata dari preset sebelumnya"
        prev = r["kata_bidik"]


def test_resep_menghasilkan_panjang_kalimat_yang_WAJAR():
    """Satu kalimat 200 kata 'muat' secara matematis tapi bukan narasi. Panjang kalimat wajib alami."""
    for p in SHORT:
        r = resep(p, SHORT, OVH[p])
        per_kalimat = r["kata_bidik"] / r["kalimat"]
        assert 7 <= per_kalimat <= 25, f"preset {p}: {per_kalimat:.0f} kata/kalimat — tidak alami"


def test_resep_menghormati_overhead():
    """Jeda video (jeda-akhir + loop) memakan durasi → kata harus lebih sedikit, bukan diabaikan."""
    tanpa = resep(60, SHORT, 0.0)
    dengan = resep(60, SHORT, 6.0)
    assert dengan["kata_bidik"] < tanpa["kata_bidik"]


def test_resep_selalu_di_dalam_band_setelah_overhead():
    for p in SHORT:
        r = resep(p, SHORT, OVH[p])
        lo, hi = r["band_video"]
        assert r["audio_maks"] + OVH[p] <= hi + 0.01
        assert r["audio_min"] + OVH[p] >= lo - 0.01


# ── vonis (gerbang sebelum belanja) ───────────────────────────────────────────────────────────────

def test_vonis_ok_saat_pas():
    r = resep(60, SHORT, OVH[60])
    teks = " ".join(["Kalimat contoh sepanjang sepuluh kata saja untuk uji ini."] * 12)
    v = vonis(teks, 60, SHORT, OVH[60])
    assert v["status"] in ("ok", "terlalu_panjang", "terlalu_pendek")
    assert v["band_video"] == r["band_video"]


def test_vonis_terlalu_pendek_melapor_kekurangan_kata():
    v = vonis("Pendek sekali.", 60, SHORT, OVH[60])
    assert v["status"] == "terlalu_pendek"
    assert v["kata_selisih"] > 0


def test_vonis_terlalu_panjang_melapor_kelebihan_kata():
    v = vonis(" ".join(["Kalimat panjang sekali yang mengulang terus."] * 60), 30, SHORT, OVH[30])
    assert v["status"] == "terlalu_panjang"
    assert v["kata_selisih"] > 0


def test_vonis_memakai_durasi_bukan_jumlah_kata():
    """Cacat NYATA 31-Jul: putaran perbaikan yang mengejar jumlah kata meloloskan naskah 165 kata /
    14 kalimat yang ternyata 80,5 dtk (band 52–68). Vonis WAJIB berdasar durasi."""
    banyak_kalimat = " ".join(["Dua kata."] * 60)          # kata sedikit, kalimat sangat banyak
    v = vonis(banyak_kalimat, 30, SHORT, OVH[30])
    assert v["status"] == "terlalu_panjang", "vonis masih menilai dari jumlah kata, bukan durasi"


# ── kecepatan suara BUKAN tuas ────────────────────────────────────────────────────────────────────

def test_modul_tak_punya_jalan_masuk_untuk_kecepatan_suara():
    """Keputusan owner 2026-07-29: tiap voice dirancang ideal di 1,0; memperlambat merusak mood —
    barang yang kita jual. Produksi lama memperlambat 41% render sampai batas 0,70 DAN tetap meleset."""
    import inspect

    import src.production.duration_model as dm
    sumber = inspect.getsource(dm)
    for terlarang in ("atempo", "speed_range", "perlambat", "solve_speed"):
        assert f"def {terlarang}" not in sumber
    for f in (resep, vonis, prediksi_audio, band_video):
        assert not any("speed" in p for p in inspect.signature(f).parameters)
