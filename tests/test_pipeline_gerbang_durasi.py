"""Gerbang durasi pipeline memakai ATURAN TITIK-TENGAH owner — bukan toleransi persen.

Kenapa dijaga uji: sebelum 2026-07-31 ada TIGA penggaris berbeda untuk hal yang sama (naskah ±12%,
gerbang pra-visual ±15%, QC pasca-render ±15% + pagar 2×). Angka persen itu karangan, dan arahnya
terbukti salah: di preset 90s ±15% = ±13,5 dtk (LEBIH LONGGAR daripada jarak ke tetangga 75s, jadi
video "lulus" padahal sudah milik preset lain), sementara di preset 8s ±15% = ±1,2 dtk (lebih ketat
dari yang perlu). Sekarang satu sumber: `duration_model.band_video`.

Uji ini juga mengunci dua hal yang pernah menjadi penghalang keras:
  • batas platform 180 dtk tidak boleh lagi membunuh preset panjang (Regular 2–12 menit)
  • preset di luar tangga aktif → gerbang PASIF (tidak mengarang batas)
"""
import pytest

from src.orchestrator.pipeline import Pipeline

SHORT = [8, 15, 30, 45, 60, 75, 90]


@pytest.fixture
def qc(monkeypatch, tmp_path):
    """QC nyata, tapi tangga preset & berkas video dipalsukan supaya uji tak menyentuh DB/disk besar."""
    monkeypatch.setattr("src.config.format_catalog.active_presets", lambda: SHORT)
    f = tmp_path / "video.mp4"
    f.write_bytes(b"0" * (8 * 1024 * 1024))          # 8 MB → lolos ambang ukuran
    monkeypatch.setattr(Pipeline, "_probe_streams", lambda self, p: None)   # lewati cek stream
    p = Pipeline.__new__(Pipeline)
    return p, str(f)


def test_durasi_di_dalam_band_titik_tengah_LULUS(qc):
    p, f = qc
    ok, alasan = p._pre_publish_qc(f, 56.0, clip_count=5, target_seconds=60, expected_beats=5)
    assert ok, alasan


def test_contoh_owner_45_jadi_32_DITOLAK(qc):
    """Contoh yang owner berikan sendiri: pesan 45 dapat 32 = sudah lebih dekat ke preset 30."""
    p, f = qc
    ok, alasan = p._pre_publish_qc(f, 32.0, clip_count=4, target_seconds=45, expected_beats=4)
    assert not ok
    assert "kependekan" in alasan


def test_kepanjangan_menyeberang_ke_preset_tetangga_DITOLAK(qc):
    p, f = qc
    ok, alasan = p._pre_publish_qc(f, 70.0, clip_count=4, target_seconds=60, expected_beats=4)
    assert not ok and "kepanjangan" in alasan


def test_band_preset_90_LEBIH_KETAT_daripada_toleransi_15_persen(qc):
    """Bukti bahwa aturan lama salah arah: 100,0 dtk lolos ±15% (85–103,5) padahal sudah 10 dtk di
    atas titik tengah ke preset berikutnya. Aturan owner menolaknya."""
    p, f = qc
    assert 90 * 0.85 <= 100.0 <= 90 * 1.15          # lolos penggaris LAMA
    ok, _ = p._pre_publish_qc(f, 100.0, clip_count=7, target_seconds=90, expected_beats=7)
    assert not ok, "band preset 90s harus lebih ketat daripada ±15%"


def test_band_preset_8_LEBIH_LONGGAR_daripada_toleransi_15_persen(qc):
    """Sisi sebaliknya: 10,0 dtk DITOLAK ±15% (6,8–9,2) padahal masih jelas milik preset 8s."""
    p, f = qc
    assert not (8 * 0.85 <= 10.0 <= 8 * 1.15)       # ditolak penggaris LAMA
    ok, alasan = p._pre_publish_qc(f, 10.0, clip_count=1, target_seconds=8, expected_beats=1)
    assert ok, alasan


def test_preset_di_luar_tangga_aktif_TIDAK_dinilai_durasinya(monkeypatch, tmp_path):
    """Gagal-aman: tangga tak memuat preset itu → jangan mengarang batas. Cek integritas lain jalan."""
    monkeypatch.setattr("src.config.format_catalog.active_presets", lambda: [8, 15, 30])
    monkeypatch.setattr(Pipeline, "_probe_streams", lambda self, p: None)
    f = tmp_path / "v.mp4"
    f.write_bytes(b"0" * (8 * 1024 * 1024))
    p = Pipeline.__new__(Pipeline)
    # 120 dtk untuk preset 60 dtk: JAUH di luar band bila band dihitung — tapi tangga tak memuat 60,
    # jadi band tidak boleh dikarang. Lolos (integritas render tetap dijaga cek lain).
    ok, alasan = p._pre_publish_qc(str(f), 120.0, clip_count=5, target_seconds=60, expected_beats=5)
    assert ok, alasan
    # Jaring pengaman platform TETAP hidup — "tak dinilai" bukan berarti "apa pun diterima".
    ok2, alasan2 = p._pre_publish_qc(str(f), 999.0, clip_count=5, target_seconds=60, expected_beats=5)
    assert not ok2 and "terlalu panjang" in alasan2
    for kata in ("kependekan", "kepanjangan"):
        assert kata not in alasan2, "band dikarang padahal preset di luar tangga aktif"


def test_batas_platform_180s_tak_lagi_membunuh_preset_panjang(monkeypatch, tmp_path):
    """Penghalang keras yang ditemukan 2026-07-31: `QC_MAX_DURATION=180` menolak SEMUA video Regular
    (2–12 menit) sebelum apa pun sempat dinilai."""
    monkeypatch.setattr("src.config.format_catalog.active_presets", lambda: [120, 300, 480, 720])
    monkeypatch.setattr(Pipeline, "_probe_streams", lambda self, p: None)
    f = tmp_path / "v.mp4"
    f.write_bytes(b"0" * (40 * 1024 * 1024))
    p = Pipeline.__new__(Pipeline)
    ok, alasan = p._pre_publish_qc(str(f), 300.0, clip_count=8, target_seconds=300, expected_beats=8)
    assert ok, alasan


def test_batas_platform_tetap_berlaku_bila_preset_tak_diset(monkeypatch, tmp_path):
    monkeypatch.setattr("src.config.format_catalog.active_presets", lambda: SHORT)
    monkeypatch.setattr(Pipeline, "_probe_streams", lambda self, p: None)
    f = tmp_path / "v.mp4"
    f.write_bytes(b"0" * (40 * 1024 * 1024))
    p = Pipeline.__new__(Pipeline)
    ok, alasan = p._pre_publish_qc(str(f), 300.0, clip_count=8, target_seconds=None)
    assert not ok and "terlalu panjang" in alasan


# ── GERBANG PALING HULU: hentikan sebelum sepeser pun terpakai ────────────────────────────────────

def test_gerbang_durasi_HULU_ada_sebelum_hook_dan_suara():
    """Alat ukur kini meleset ~1 detik, jadi begitu naskah selesai kita SUDAH TAHU video jadinya
    berapa detik. Sampai 2026-08-01 pengetahuan itu tak dipakai: pipeline tetap membayar optimasi
    hook, pembuatan prompt gambar, dan SUARA (ElevenLabs ditagih per huruf) sebelum gerbang
    pasca-suara menghentikannya. Untuk tenant BYOK itu uang mereka, terbakar pada video yang sudah
    kita ketahui akan gagal."""
    import inspect

    import src.orchestrator.pipeline as pl
    src = inspect.getsource(pl.Pipeline.run)
    assert "GERBANG DURASI PALING HULU" in src, "gerbang hulu hilang"
    i_hulu = src.index("GERBANG DURASI PALING HULU")
    i_hook = src.index("STEP 4: Hook Optimization")
    i_tts = src.index("STEP 5: TTS Audio")
    assert i_hulu < i_hook < i_tts, "gerbang hulu tidak berada sebelum hook & suara"


def test_gerbang_hulu_memakai_PENGGARIS_YANG_SAMA_dengan_gerbang_pasca_suara():
    """Dua gerbang dengan aturan berbeda = 'tiga penggaris' yang dulu melahirkan insiden 15-Jul.
    Keduanya: band titik-tengah + pagar satu lebar band; near-miss LANJUT (tenant yang meninjau)."""
    import inspect

    import src.orchestrator.pipeline as pl
    src = inspect.getsource(pl.Pipeline.run)
    hulu = src[src.index("GERBANG DURASI PALING HULU"):src.index("STEP 4: Hook Optimization")]
    assert "band_video" in hulu and "effective_overhead" in hulu, "gerbang hulu memakai rumus sendiri"
    assert "_lebar35" in hulu and "near_miss" in hulu, "pagar/near-miss gerbang hulu berbeda aturan"


def test_kegagalan_gerbang_hulu_TIDAK_menjatuhkan_produksi():
    """Gerbang ini penghemat biaya, bukan penentu mutu. Bila ia sendiri error, produksi harus tetap
    jalan — gerbang pasca-suara yang menjaga."""
    import inspect

    import src.orchestrator.pipeline as pl
    src = inspect.getsource(pl.Pipeline.run)
    hulu = src[src.index("GERBANG DURASI PALING HULU"):src.index("STEP 4: Hook Optimization")]
    assert "except LLMError:" in hulu and "raise" in hulu, "kegagalan sah ikut tertelan"
    assert "non-fatal" in hulu, "error tak terduga di gerbang hulu bisa menjatuhkan produksi"
