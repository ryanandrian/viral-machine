"""
Cost Meter — pengumpul KONSUMSI AI per-run (B2 BYOK cost-tracking, disepakati owner 2026-07-04).

Prinsip:
- ON-THE-FLY, NOL overhead: angka usage sudah menumpang di respons API yang memang kita terima
  (adapter LLM: resp.usage · image: hitung sukses · TTS: panjang teks). TIDAK ada panggilan API tambahan.
- THREAD-LOCAL per-run: pipeline reset() di awal run; add_* di adapter/provider hanya merekam bila
  meter aktif di thread itu (thread lain, mis. publisher, tak menginisialisasi → no-op, nol polusi).
- Meter = KONSUMSI saja (token/gambar/karakter). Konversi ke uang = src/billing/ai_cost.py
  (harga satuan dari katalog ai_models.pricing — sinkron otomatis feed komunitas + override admin).
  SATU pengecualian, disebut namanya supaya tak jadi kejutan: `biaya_vendor` [F5, 23-Agu] menyimpan
  UANG, bukan konsumsi — yaitu biaya yang VENDOR sendiri sebutkan di balasannya. Untuk penyedia
  seperti itu menaksir ulang justru MENAMBAH kesalahan; angka vendor sudah final.
"""

import threading

_tl = threading.local()


def reset() -> None:
    """Mulai pencatatan utk run di thread ini (dipanggil pipeline di awal run)."""
    # `tts_tokens` = keranjang KEDUA untuk suara: sebagian vendor (Gemini) menagih suara PER TOKEN,
    # bukan per huruf. WAJIB terdaftar di sini — `_bucket()` mengembalikan None untuk keranjang tak
    # dikenal, jadi keranjang yang lupa didaftarkan membuat add_* jadi no-op SENYAP (pencatatan hilang
    # tanpa jejak). Dikunci uji `test_biaya_ai_tak_bisa_nol_senyap.py`.
    _tl.data = {"llm": {}, "image": {}, "tts": {}, "tts_tokens": {}, "tts_seconds": {}, "video": {},
                "biaya_vendor": {}}


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


def add_tts_seconds(model: str, seconds: float) -> None:
    """Durasi audio NYATA (detik) untuk suara ber-tagih per-detik — mis. `gpt-4o-mini-tts`, yang
    vendornya mengirim audio mentah TANPA hitungan token sehingga satuan lain tak bisa dihitung.
    Diukur dari berkas audio yang baru saja jadi (bukan ditaksir), dicatat SEKALI di mesin suara."""
    b = _bucket("tts_seconds")
    if b is None or not model:
        return
    b[model] = round(float(b.get(model, 0.0)) + float(seconds or 0.0), 3)


def add_biaya_vendor(model: str, usd: float) -> None:
    """[F5] BIAYA yang VENDOR sebutkan sendiri untuk panggilan ini — satu-satunya angka di meteran
    ini yang berupa UANG, bukan konsumsi. Sengaja, dan sengaja di keranjang SENDIRI.

    KENAPA ADA. Seluruh keluarga cacat 23-Agu lahir dari MENAKSIR (jumlah yang kita ukur × tarif yang
    kita simpan): satuan bisa salah, tarif bisa basi, pencatat bisa dobel. Untuk penyedia yang
    melaporkan biayanya per panggilan, rantai itu tak perlu ada — dan angkanya bukan taksiran.
    Terverifikasi ke dokumen resmi OpenRouter (23-Agu): `usage.cost` SELALU dikirim, satuannya
    *credit*, dan 1 credit = 1 USD.

    KENAPA KERANJANG SENDIRI. Kalau ditumpangkan ke keranjang token, satu panggilan punya DUA cara
    ditagih di satu tempat — persis bentuk cacat "tertagih dua kali" yang baru ditutup. Terpisah
    berarti penghitung memilih salah satu berdasarkan FORMULA yang baris modelnya nyatakan.

    Fail-soft: nilai tak masuk akal / nol / negatif → tak dicatat (biar jalur jujur yang bicara,
    bukan angka gratis palsu)."""
    b = _bucket("biaya_vendor")
    if b is None or not model:
        return
    try:
        nilai = float(usd)
    except (TypeError, ValueError):
        return
    if nilai <= 0:
        return
    b[model] = round(float(b.get(model, 0.0)) + nilai, 8)


def summary() -> dict:
    """Snapshot konsumsi run ini (dict serializable utk run_metadata). Kosong bila meter tak aktif."""
    if not hasattr(_tl, "data"):
        return {}
    return {k: dict(v) for k, v in _tl.data.items() if v}
