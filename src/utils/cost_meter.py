"""
Cost Meter — pengumpul KONSUMSI AI per-run (B2 BYOK cost-tracking, disepakati owner 2026-07-04).

Prinsip:
- ON-THE-FLY, NOL overhead: angka usage sudah menumpang di respons API yang memang kita terima
  (adapter LLM: resp.usage · image: hitung sukses · TTS: panjang teks). TIDAK ada panggilan API tambahan.
- THREAD-LOCAL per-run: pipeline reset() di awal run; add_* di adapter/provider hanya merekam bila
  meter aktif di thread itu (thread lain, mis. publisher, tak menginisialisasi → no-op, nol polusi).
- Meter = KONSUMSI saja (token/gambar/karakter). Konversi ke uang = src/billing/ai_cost.py
  (harga satuan dari katalog ai_models.pricing — sinkron otomatis feed komunitas + override admin).
"""

import threading

_tl = threading.local()


def reset() -> None:
    """Mulai pencatatan utk run di thread ini (dipanggil pipeline di awal run)."""
    # `tts_tokens` = keranjang KEDUA untuk suara: sebagian vendor (Gemini) menagih suara PER TOKEN,
    # bukan per huruf. WAJIB terdaftar di sini — `_bucket()` mengembalikan None untuk keranjang tak
    # dikenal, jadi keranjang yang lupa didaftarkan membuat add_* jadi no-op SENYAP (pencatatan hilang
    # tanpa jejak). Dikunci uji `test_biaya_ai_tak_bisa_nol_senyap.py`.
    _tl.data = {"llm": {}, "image": {}, "tts": {}, "tts_tokens": {}, "video": {}}


def _bucket(kind: str) -> dict | None:
    return getattr(_tl, "data", {}).get(kind) if hasattr(_tl, "data") else None


def add_llm(model: str, tokens_in: int, tokens_out: int) -> None:
    b = _bucket("llm")
    if b is None or not model:
        return
    cur = b.setdefault(model, {"tokens_in": 0, "tokens_out": 0, "calls": 0})
    cur["tokens_in"] += int(tokens_in or 0)
    cur["tokens_out"] += int(tokens_out or 0)
    cur["calls"] += 1


def add_image(model: str, count: int = 1) -> None:
    b = _bucket("image")
    if b is None or not model:
        return
    b[model] = b.get(model, 0) + int(count)


def add_video(model: str, seconds: float, clips: int = 1) -> None:
    """[B6] F2: 1 klip video-gen SUKSES — catat DETIK TERTAGIH vendor (durasi diminta, bukan hasil trim)."""
    b = _bucket("video")
    if b is None or not model:
        return
    cur = b.setdefault(model, {"seconds": 0.0, "clips": 0})
    cur["seconds"] += float(seconds or 0)
    cur["clips"] += int(clips)


def add_tts(model: str, chars: int) -> None:
    b = _bucket("tts")
    if b is None or not model:
        return
    b[model] = b.get(model, 0) + int(chars or 0)


def add_tts_tokens(model: str, tokens_in: int, tokens_out: int) -> None:
    """Token NYATA dari balasan vendor untuk suara ber-tagih token (mis. Gemini TTS: token audio).
    TERPISAH dari keranjang `llm` supaya biaya suara tidak nyasar ke rincian naskah, dan terpisah
    dari keranjang `tts` (huruf) supaya penghitung biaya bisa memilih satuan tanpa risiko ganda."""
    b = _bucket("tts_tokens")
    if b is None or not model:
        return
    cur = b.setdefault(model, {"tokens_in": 0, "tokens_out": 0})
    cur["tokens_in"] += int(tokens_in or 0)
    cur["tokens_out"] += int(tokens_out or 0)


def summary() -> dict:
    """Snapshot konsumsi run ini (dict serializable utk run_metadata). Kosong bila meter tak aktif."""
    if not hasattr(_tl, "data"):
        return {}
    return {k: dict(v) for k, v in _tl.data.items() if v}
