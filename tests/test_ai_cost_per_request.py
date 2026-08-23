"""Kalkulator biaya: jenis tarif PER PERMINTAAN tidak boleh mengubah perhitungan model lama.

`compute_cost_usd` dipakai SEMUA model (LLM, gambar, suara, video). Menambah cabang tarif baru
di situ berisiko menggeser angka tagihan model yang sudah berjalan — karena itu uji ini mengunci
perilaku lama dengan angka eksplisit, bukan sekadar "tidak error".

Tarif per-permintaan dipakai fal any-llm: $0,001 sekali panggil, berapa pun panjang naskahnya.
"""
import src.billing.ai_cost as ac


def _pakai_harga(monkeypatch, harga: dict, formula: dict | None = None):
    """[F2, 23-Agu] Formula tiap model WAJIB dinyatakan di sini juga. Sebelumnya uji ini membiarkan
    `_formula_map` menembak DATABASE SUNGGUHAN: saat dijalankan sendiri panggilannya gagal (jatuh ke
    perilaku lama, uji hijau), saat dijalankan bersama uji lain panggilannya BERHASIL dan model
    karangan ini tak ada formulanya (uji merah). Hasil uji jadi bergantung URUTAN — itu rapuh dan
    menyesatkan. Formula diturunkan dari kunci harga yang dipakai tiap kasus, jadi maknanya persis
    sama seperti sebelumnya, hanya kini TEGAS."""
    monkeypatch.setattr(ac, "_pricing_map", lambda sb=None: harga)

    def _turunkan(p: dict) -> str:
        if p.get("per_request_usd") is not None:
            return "naskah_panggilan"
        if p.get("per_1m_chars") is not None:
            return "suara_huruf"
        if p.get("per_image") is not None:
            return "gambar_satuan"
        if p.get("per_second_usd") is not None:
            return "video_detik"
        if p.get("per_video_base_usd") is not None:
            return "video_klip"
        return "naskah_token"

    peta = formula if formula is not None else {m: _turunkan(p or {}) for m, p in harga.items()}
    monkeypatch.setattr(ac, "_formula_map", lambda sb=None: peta)


def test_model_per_token_hasilnya_tidak_berubah(monkeypatch):
    """Angka dikunci eksplisit: 1jt token masuk @ $0,15 + 0,5jt keluar @ $0,60 = $0,45."""
    _pakai_harga(monkeypatch, {"gpt-4o-mini": {"in_per_1m": 0.15, "out_per_1m": 0.60}})
    hasil = ac.compute_cost_usd({"llm": {"gpt-4o-mini": {"tokens_in": 1_000_000, "tokens_out": 500_000}}})
    assert round(hasil["breakdown"]["llm"], 6) == 0.45
    assert hasil["unpriced"] == []


def test_model_per_permintaan_dihitung_dari_jumlah_panggilan(monkeypatch):
    _pakai_harga(monkeypatch, {"anthropic/claude-haiku-4.5": {"per_request_usd": 0.001}})
    hasil = ac.compute_cost_usd({"llm": {"anthropic/claude-haiku-4.5": {"calls": 3}}})
    assert round(hasil["breakdown"]["llm"], 6) == 0.003
    assert hasil["unpriced"] == []


def test_per_permintaan_mengabaikan_jumlah_token(monkeypatch):
    """Justru inti tarif ini: panjang naskah tak memengaruhi biaya."""
    _pakai_harga(monkeypatch, {"m": {"per_request_usd": 0.001}})
    a = ac.compute_cost_usd({"llm": {"m": {"calls": 1, "tokens_in": 10, "tokens_out": 10}}})
    b = ac.compute_cost_usd({"llm": {"m": {"calls": 1, "tokens_in": 999_999, "tokens_out": 999_999}}})
    assert a["breakdown"]["llm"] == b["breakdown"]["llm"] == 0.001


def test_model_tanpa_harga_apa_pun_tetap_masuk_daftar_tak_berharga(monkeypatch):
    """Perilaku lama yang WAJIB bertahan: jangan diam-diam dihitung nol."""
    _pakai_harga(monkeypatch, {"misterius": {"in_per_1m": None, "out_per_1m": None}})
    hasil = ac.compute_cost_usd({"llm": {"misterius": {"tokens_in": 1000}}})
    assert hasil["unpriced"] == ["misterius"]
    assert hasil["breakdown"]["llm"] == 0.0


def test_model_tak_ada_di_katalog_harga_juga_masuk_daftar(monkeypatch):
    _pakai_harga(monkeypatch, {})
    hasil = ac.compute_cost_usd({"llm": {"entah": {"tokens_in": 1000}}})
    assert hasil["unpriced"] == ["entah"]


def test_campuran_per_token_dan_per_permintaan_dijumlah_benar(monkeypatch):
    _pakai_harga(monkeypatch, {
        "lama": {"in_per_1m": 1.0, "out_per_1m": 2.0},
        "baru": {"per_request_usd": 0.01},
    })
    hasil = ac.compute_cost_usd({"llm": {
        "lama": {"tokens_in": 1_000_000, "tokens_out": 1_000_000},   # 1 + 2 = 3
        "baru": {"calls": 5},                                         # 5 x 0,01 = 0,05
    }})
    assert round(hasil["breakdown"]["llm"], 6) == 3.05


def test_per_permintaan_tanpa_jumlah_panggilan_dihitung_nol_bukan_meledak(monkeypatch):
    """Data pemakaian lama tak punya field `calls` — jangan sampai mematikan perhitungan tagihan."""
    _pakai_harga(monkeypatch, {"m": {"per_request_usd": 0.001}})
    hasil = ac.compute_cost_usd({"llm": {"m": {"tokens_in": 100}}})
    assert hasil["breakdown"]["llm"] == 0.0
    assert hasil["unpriced"] == []
