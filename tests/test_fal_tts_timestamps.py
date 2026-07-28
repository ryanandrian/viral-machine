"""Konversi penanda waktu fal (per KARAKTER) → per KATA — penentu presisi caption karaoke.

fal meneruskan penanda ElevenLabs dalam bentuk per karakter:
    {"characters": [...], "character_start_times_seconds": [...], "character_end_times_seconds": [...]}
Pembuat subtitle kita butuh per kata: {"word", "start", "end"}. Kalau konversi ini meleset, caption
kembali melompat atau sorot kata tidak sinkron — dua hal yang baru diberantas 2026-07-27/28.

Bentuk masukan di sini disalin dari respons NYATA fal (turbo-v2.5, 2026-07-28).
"""
from src.providers.tts.fal_tts import _karakter_ke_kata


def _blok(teks: str, mulai: float = 0.0, per_char: float = 0.05):
    """Bangun blok gaya-fal untuk sebuah kalimat, waktu naik rata per karakter."""
    ch = list(teks)
    st = [round(mulai + i * per_char, 3) for i in range(len(ch))]
    en = [round(s + per_char, 3) for s in st]
    return [{"characters": ch, "character_start_times_seconds": st, "character_end_times_seconds": en}]


def test_kata_dan_urutan_sama_persis_dengan_teks():
    teks = "Dasar laut menyimpan rahasia yang belum pernah dilihat manusia."
    wt = _karakter_ke_kata(_blok(teks))
    assert [w["word"] for w in wt] == teks.split()
    assert all(wt[i]["start"] <= wt[i + 1]["start"] for i in range(len(wt) - 1))
    assert all(w["end"] > w["start"] for w in wt)


def test_tanda_baca_menempel_pada_katanya():
    """Pemotong baris menghitung lebar termasuk tanda baca — kalau terpisah, lebar salah."""
    wt = _karakter_ke_kata(_blok("Halo, dunia!"))
    assert [w["word"] for w in wt] == ["Halo,", "dunia!"]


def test_spasi_ganda_dan_awalan_spasi_tidak_bikin_kata_kosong():
    """Respons fal sungguhan diawali spasi — kata kosong akan merusak pemotong baris."""
    wt = _karakter_ke_kata(_blok("  Dua   spasi  "))
    assert [w["word"] for w in wt] == ["Dua", "spasi"]
    assert all(w["word"].strip() for w in wt)


def test_beberapa_blok_digabung_berurutan():
    a = _blok("Satu dua", mulai=0.0)
    b = _blok("tiga empat", mulai=5.0)
    wt = _karakter_ke_kata(a + b)
    assert [w["word"] for w in wt] == ["Satu", "dua", "tiga", "empat"]
    assert wt[2]["start"] >= wt[1]["end"]


def test_blok_cacat_dilewati_tanpa_meledak():
    """Panjang array tak sepadan = data rusak; lebih baik lewati daripada mematikan produksi."""
    cacat = [{"characters": ["a", "b"], "character_start_times_seconds": [0.0],
              "character_end_times_seconds": [0.1, 0.2]}]
    assert _karakter_ke_kata(cacat) == []


def test_masukan_kosong_aman():
    assert _karakter_ke_kata([]) == []
    assert _karakter_ke_kata(None) == []


def test_bentuk_keluaran_persis_yang_dipakai_pembuat_subtitle():
    """Kunci WAJIB 'word'/'start'/'end' — nama lain akan diam-diam dibaca sebagai kosong."""
    wt = _karakter_ke_kata(_blok("uji bentuk"))
    for w in wt:
        assert set(w) == {"word", "start", "end"}
        assert isinstance(w["word"], str) and isinstance(w["start"], float) and isinstance(w["end"], float)
