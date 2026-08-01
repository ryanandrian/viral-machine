"""VIDEO REGULAR (2–12 menit): naskah 1.000+ kata dipotong & disambung — tanpa merusak narasi.

Naskah sepanjang itu (±6.000–11.000 huruf) melampaui batas satu permintaan di semua penyedia suara,
dan bahkan bila diterima, satu permintaan sebesar itu jauh lebih sering menggantung atau terputus di
tengah. Yang dikunci di sini: potongannya SELALU di batas kalimat, penanda waktu tetap presisi setelah
disambung, dan penjaga audio-terpotong berlaku PER POTONGAN — justru di sinilah ia paling dibutuhkan,
karena satu potongan yang gagal akan tersembunyi di dalam audio panjang.
"""

import inspect

import pytest

from src.production.tts_engine import _geser_timestamp, _potong_kalimat


def test_potongan_selalu_berakhir_di_batas_kalimat():
    """Memotong di tengah kalimat terdengar: narator berhenti mendadak lalu memulai lagi dengan
    intonasi awal-kalimat. Itu 'potongan yang merusak narasi' (isu utama owner #2)."""
    teks = " ".join(f"Ini kalimat nomor {i} yang cukup panjang untuk diuji." for i in range(1, 61))
    bagian = _potong_kalimat(teks, 500)
    assert len(bagian) > 1, "naskah panjang tidak dipotong"
    for b in bagian:
        assert b.rstrip()[-1] in ".!?…", f"potongan berakhir di tengah kalimat: …{b[-40:]!r}"


def test_tidak_ada_kata_yang_hilang_atau_ganda():
    teks = " ".join(f"Kalimat {i} berisi angka {i * 7} dan nama Kanto." for i in range(1, 41))
    bagian = _potong_kalimat(teks, 400)
    assert " ".join(bagian).split() == teks.split(), "penggabungan potongan tidak sama dengan naskah asal"


def test_naskah_pendek_TIDAK_dipotong():
    teks = "Satu kalimat pendek saja."
    assert _potong_kalimat(teks, 3000) == [teks]
    assert _potong_kalimat("", 3000) == []


def test_kalimat_tunggal_yang_kelewat_panjang_TIDAK_dipotong_paksa():
    """Lebih baik satu permintaan besar daripada narasi yang patah di tengah kalimat."""
    panjang = "Kalimat ini sangat panjang " * 60 + "dan berakhir di sini."
    bagian = _potong_kalimat(panjang, 200)
    assert len(bagian) == 1 and bagian[0] == panjang


def test_penanda_waktu_digeser_ke_posisi_di_audio_gabungan():
    """Tanpa pergeseran, caption potongan ke-2 dst akan muncul di detik yang salah."""
    ts = [{"word": "satu", "start": 0.0, "end": 0.5}, {"word": "dua", "start": 0.6, "end": 1.1}]
    g = _geser_timestamp(ts, 12.5)
    assert [w["start"] for w in g] == pytest.approx([12.5, 13.1])
    assert [w["end"] for w in g] == pytest.approx([13.0, 13.6])
    assert [w["word"] for w in g] == ["satu", "dua"]


def test_penjaga_audio_terpotong_berlaku_PER_POTONGAN():
    import src.production.tts_engine as te
    src = inspect.getsource(te._run_provider)
    assert "_potong_kalimat" in src, "jalur render tidak memotong naskah panjang"
    assert "tts_potong_ambang_pct" in src, "penjaga audio-terpotong tidak berlaku per potongan"
    assert "batas waktu" in src.lower() or "timeout" in src.lower()
    assert "_sambung_audio" in src, "potongan tidak disambung"


def test_penyambungan_memakai_RE_ENCODE_bukan_salin_mentah():
    """Menyambung mp3 mentah menyisakan padding encoder di tiap sambungan — terdengar sebagai 'tik'
    halus DAN menambah durasi yang tak terhitung model durasi."""
    import src.production.tts_engine as te
    src = inspect.getsource(te._sambung_audio)
    assert "libmp3lame" in src, "penyambungan memakai salin mentah — sambungannya akan berbunyi"
    assert "concat" in src


# ── batas huruf PER PENYEDIA (CONTENT_CATEGORY §7h, migr 0189) ────────────────────────────────────

def test_batas_huruf_dibaca_per_penyedia_bukan_satu_angka_untuk_semua():
    """Satu angka untuk semua penyedia aman hari ini tapi bukan jawaban yang benar: penyedia baru
    dengan batas LEBIH KECIL akan gagal, dan yang batasnya lebih besar dipecah lebih banyak dari perlu
    — tiap potongan tambahan adalah satu permintaan berbayar lagi. Desainnya sudah diketok di
    CONTENT_CATEGORY_ARCHITECTURE.md §7h; ini pelaksanaannya."""
    import inspect

    import src.production.tts_engine as te
    src = inspect.getsource(te._run_provider)
    assert "tts_max_chars" in src, "jalur render memakai satu angka untuk semua penyedia"


def test_penyedia_tanpa_batas_terverifikasi_pakai_kenop_global():
    """Aturan §7h: isi HANYA dari dokumentasi resmi vendor. Yang belum terverifikasi dibiarkan kosong
    → kenop global konservatif. Mengarang angka = produksi gagal di tengah naskah panjang tanpa sebab
    yang terlihat."""
    from src.config.format_catalog import tts_max_chars
    assert tts_max_chars("penyedia_yang_belum_ada", 3000) == 3000
    assert tts_max_chars(None, 3000) == 3000
    assert tts_max_chars("", 1234) == 1234


# ── penjaga PER POTONGAN benar-benar MENYALA (butir yang belum pernah terbukti di render nyata) ────

def test_potongan_yang_tak_lengkap_MENGHENTIKAN_produksi(tmp_path, monkeypatch):
    """Penjaga ini paling dibutuhkan justru di naskah panjang: satu potongan yang gagal di tengah akan
    TERSEMBUNYI di dalam audio gabungan yang panjang — penonton mendengar cerita melompat, dan tak
    satu pun log menyebut apa pun. Diuji dengan penyedia tiruan yang menghasilkan audio jauh lebih
    pendek dari naskahnya, karena kejadian nyatanya (1 dari 73 render) tak bisa dipesan."""
    import subprocess

    import src.production.tts_engine as te
    from src.exceptions import ErrorClass, TTSError

    class _Pendek:
        """Potongan ke-2 sengaja menghasilkan audio yang jauh lebih pendek dari teksnya."""
        def __init__(self, cfg): self.n = 0
        async def generate(self, teks, out):
            self.n += 1
            detik = 0.3 if "POTONGAN_CACAT" in teks else max(1.0, len(teks) * 0.05)
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
                            "-t", str(detik), "-c:a", "libmp3lame", str(out)],
                           capture_output=True, timeout=60)
            return out
        def get_word_timestamps(self): return []

    monkeypatch.setattr("src.providers.tts.build_tts_provider", lambda p, c: _Pendek(c))
    monkeypatch.setattr(te._ambang, "angka",
                        lambda k, d: 200 if k == "tts_chunk_maks_huruf" else d)

    kal_pendek = "Kalimat biasa yang cukup panjang untuk mengisi potongan pertama ini. " * 3
    teks = kal_pendek + "POTONGAN_CACAT " + ("kalimat lanjutan yang panjang sekali. " * 8)
    with pytest.raises(TTSError) as e:
        te._run_provider("edge_tts", teks, {"tenant_id": "uji"}, str(tmp_path))
    assert e.value.error_class is ErrorClass.TRANSIENT, \
        "potongan tak lengkap harus TRANSIENT (produksi diulang), bukan mematikan channel"
    pesan = (getattr(e.value, "human_message", "") or str(e.value)).lower()
    assert "tidak lengkap" in pesan or "terputus" in pesan, f"pesan tak menjelaskan sebabnya: {pesan}"
