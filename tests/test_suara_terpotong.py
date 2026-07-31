"""Audio suara TIDAK LENGKAP wajib GAGAL JUJUR — bukan dipakai jadi video.

CACAT NYATA yang ditemukan 2026-08-01 saat memeriksa penyebab kesalahan 13,1 detik pada kalibrasi:

    teks 581 huruf → berkas audio 27,0 detik
    teks SAMA di-render ulang 2× → 40,8 detik (konsisten)
    → audionya TERPOTONG 13,8 detik

Sebabnya: adaptor menulis potongan audio sambil menerima aliran dari vendor; kalau aliran berhenti di
tengah, loop-nya hanya berhenti menulis — tanpa error. Berkasnya ADA, tidak kosong, dan durasinya
tampak wajar, jadi SELURUH pipeline menerimanya.

Yang membuatnya berbahaya: dulu korektor atempo MEREGANGKAN audio pendek itu supaya pas durasi preset,
sehingga narasi yang terputus tersembunyi sempurna dari setiap pemeriksaan — penonton mendengar cerita
yang berhenti mendadak, dan tak ada satu pun log yang menyebutkan apa pun.

Baru bisa dideteksi setelah ada alat ukur yang akurat (~1 detik): kalau audio jauh lebih pendek dari
yang diramal dari TEKSNYA, yang hilang adalah suaranya — bukan ramalannya.
"""
import inspect
import os

import pytest


def test_lapis1_adaptor_menolak_sintesis_yang_tak_sampai_habis():
    """Lapis pertama (khusus Edge): penanda kalimat dari vendor menunjukkan seberapa jauh sintesis
    sampai. Cakupan di bawah ambang = aliran berhenti di tengah."""
    import src.providers.tts.edge_tts as e
    src = inspect.getsource(e.EdgeTTSProvider.generate)
    assert "TTS_CAKUPAN_MIN" in src, "adaptor tidak memeriksa cakupan naskah"
    assert "raise TTSError" in src, "cakupan kurang tidak menggagalkan — audio tak lengkap bisa dipakai"
    assert "sentence_boundaries and" in src, \
        "pemeriksaan tak dijaga: tanpa penanda vendor, adaptor bisa menuduh secara salah"


def test_lapis2_mesin_suara_menolak_audio_jauh_lebih_pendek_dari_ramalan():
    """Lapis kedua berlaku untuk SEMUA penyedia suara, bukan cuma Edge — sebab semua bisa memutus
    aliran. Perbandingannya dengan ramalan dari teks, yang kini akurat ~1 detik."""
    import src.production.tts_engine as te
    src = inspect.getsource(te.TTSEngine.generate)
    assert "TTS_POTONG_AMBANG" in src, "mesin suara tidak memeriksa audio terpotong"
    assert "_duration_est" in src, "pemeriksaan tidak memakai ramalan alat ukur"
    assert 'return "", []' in src, "audio terpotong tidak menggagalkan produksi"
    assert "os.remove(audio_path)" in src, "berkas audio cacat tidak dibuang"


def test_ambang_default_di_ATAS_derau_ramalan_dan_di_BAWAH_pemotongan_nyata():
    """Ambang harus longgar terhadap derau ramalan (±1–2 dtk) tapi ketat terhadap pemotongan nyata.
    Kasus nyata: 27,0 dari 40,8 = 66% → wajib tertangkap. Derau normal ~95–105% → wajib lolos."""
    amb = float(os.getenv("TTS_POTONG_AMBANG", "0.75"))
    assert 0.6 < amb < 0.9, f"ambang {amb} tak masuk akal"
    assert (27.0 / 40.8) < amb, "kasus nyata 66% TIDAK tertangkap ambang ini"
    assert 0.93 > amb, "ambang terlalu ketat — derau ramalan normal akan salah dituduh"


def test_gagalnya_TRANSIENT_supaya_diproduksi_ulang_bukan_dihentikan_permanen():
    """Aliran terputus itu gangguan sesaat: produksi harus DIULANG, bukan channel dimatikan.
    Kalau dikelasifikasi non-retryable, satu gangguan jaringan bisa menghentikan produksi tenant."""
    import src.production.tts_engine as te
    src = inspect.getsource(te.TTSEngine.generate)
    assert "ErrorClass.TRANSIENT" in src, "audio terpotong tidak dikelaskan sebagai gangguan sesaat"


def test_pesan_ke_tenant_tanpa_jargon():
    import src.production.tts_engine as te
    src = inspect.getsource(te.TTSEngine.generate)
    assert "narasinya" in src and "terputus" in src, "pesan manusiawi untuk tenant tidak ada"
