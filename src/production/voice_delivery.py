"""
[DURASI] LAJU BICARA suara — satu tempat yang menerjemahkan setelan penyedia menjadi satu angka.

═══ KENAPA MODUL INI ADA ═══

Tiap penyedia menulis "laju bicara" dengan caranya sendiri:
    Edge / SSML   `rate: "+15%"`     (persen relatif terhadap laju alami)
    ElevenLabs    `speed: 0.87`      (pengali langsung)
    fal           `speed: 0.87`
    OpenAI TTS    `speed: 1.0`
    Gemini TTS    tak punya konsep ini

Selama ini tiap tempat menafsirkannya sendiri-sendiri, dan itulah sumber dua kesalahan yang mahal:

  1. Sampel kalibrasi merekam `"+0%"` untuk Edge dan TIDAK MEREKAM APA PUN untuk penyedia lain. Akibat
     nyata: penjaga kalibrasi (migr 0184) membandingkan rekaman kosong dengan baseline katalog dan
     MENOLAK setiap sampel ElevenLabs/fal/OpenAI — jadi suara berbayar tak akan pernah terkalibrasi
     sendiri, selamanya, tanpa satu pun pesan error. Klaim "akan mengkalibrasi diri setelah sampel
     terkumpul" tidak pernah bisa terjadi.
  2. Angka yang sama punya arti berlawanan antar penyedia: Edge `+10%` = LEBIH CEPAT, ElevenLabs `0,87`
     = LEBIH LAMBAT. Membandingkan keduanya sebagai teks = membandingkan apel dan jam dinding.

Modul ini menjadikannya SATU angka tanpa satuan: **rasio terhadap laju alami suara**.
    1,00 = laju alami (ATURAN OWNER 2026-08-01: "ratio terbaik adalah 1; suara lambat merusak mood,
           seperti orang malas")
    1,15 = 15% lebih cepat        0,87 = 13% lebih lambat

Fungsi murni, tanpa DB/jaringan — dipakai BERSAMA oleh adaptor suara (melaporkan apa yang benar-benar
dikirim) dan oleh kalibrasi (memeriksa sampel diukur pada laju yang sama). Satu implementasi, jadi
keduanya tak bisa berbeda diam-diam.
"""

from __future__ import annotations

import re

# Rasio "alami" — nilai netral, dan satu-satunya yang sesuai aturan owner.
RASIO_ALAMI = 1.0
# Selisih rasio yang masih dianggap "laju yang sama" saat membandingkan sampel dengan baseline.
# 0,005 = 0,5%: jauh di bawah selisih yang bisa didengar, tapi cukup ketat untuk menangkap perbedaan
# baseline sungguhan (kesalahan 2026-07-31 selisihnya 15%).
TOLERANSI_RASIO = 0.005

_RX_PERSEN = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*%\s*$")


def rasio_laju(setelan: dict | None, rentang: tuple | None = None) -> float:
    """Setelan suara (gaya penyedia apa pun) → rasio terhadap laju alami.

    `rate` bergaya persen diprioritaskan bila ada, lalu `speed` bergaya pengali. Tak ada keduanya,
    atau nilainya tak masuk akal → 1,0 (laju alami). TIDAK PERNAH melempar: dipakai di jalur render.

    `rentang` = (min, maks) pengali yang BENAR-BENAR diterima penyedia ini, diambil pemanggil dari
    `format_catalog.tts_speed_range()` yang membacanya dari `tts_profiles.param_schema` di DB.
    Diberikan → nilai di luar rentang DIBUANG (pakai laju alami), bukan diteruskan ke vendor dan
    menghasilkan error. Tidak diberikan → hanya pagar kewajaran paling longgar.

    Kenapa rentangnya dari DB dan bukan dari kode: tiap penyedia punya batas sendiri (ElevenLabs
    0,7–1,2 · OpenAI 0,25–4,0 · Edge −50%..+100% · Gemini tak punya kenop sama sekali), dan katalog
    penyedia akan terus bertambah. Menuliskannya di kode berarti tiap penyedia baru menuntut perubahan
    kode — persis yang dilarang: perbaikan harus GENERAL, bukan per-vendor.
    """
    s = setelan if isinstance(setelan, dict) else {}
    lo, hi = (rentang if (isinstance(rentang, (tuple, list)) and len(rentang) == 2) else (0.1, 4.0))
    r = s.get("rate")
    if isinstance(r, (str, bytes)):
        m = _RX_PERSEN.match(str(r))
        if m:
            try:
                v = round(1.0 + float(m.group(1).replace(",", ".")) / 100.0, 6)
                return v if lo <= v <= hi else RASIO_ALAMI
            except ValueError:
                pass
    sp = s.get("speed")
    if isinstance(sp, (int, float)) and not isinstance(sp, bool):
        try:
            v = round(float(sp), 6)
            return v if lo <= v <= hi else RASIO_ALAMI
        except (TypeError, ValueError):
            pass
    return RASIO_ALAMI


def rasio_teks(rasio: float) -> str:
    """Rasio → teks untuk kolom `tts_delivery_samples.voice_rate`. Bentuk tetap agar bisa dibandingkan."""
    try:
        return f"{float(rasio):.4f}"
    except (TypeError, ValueError):
        return f"{RASIO_ALAMI:.4f}"


def rasio_dari_teks(teks: str | None) -> float | None:
    """Kebalikan `rasio_teks`. Tak terbaca → None (sampel tak bisa diverifikasi → jangan dipakai).
    Menerima juga bentuk LAMA bergaya persen ('+0%') supaya sampel peralihan tetap terbaca."""
    if teks is None:
        return None
    t = str(teks).strip()
    if not t:
        return None
    m = _RX_PERSEN.match(t)
    if m:
        try:
            return round(1.0 + float(m.group(1).replace(",", ".")) / 100.0, 6)
        except ValueError:
            return None
    try:
        return round(float(t), 6)
    except ValueError:
        return None


def laju_sama(a: float | None, b: float | None) -> bool:
    """Apakah dua rasio menggambarkan laju yang sama? None di salah satu = TIDAK (gagal-aman:
    sampel yang asalnya tak bisa dipastikan lebih baik ditolak daripada mencemari kalibrasi)."""
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= TOLERANSI_RASIO


def rate_edge(rasio: float) -> str:
    """Rasio → string `rate` gaya Edge/SSML. 1,0 → '+0%'."""
    pct = (float(rasio) - 1.0) * 100.0
    bulat = int(round(pct))
    return f"+{bulat}%" if bulat >= 0 else f"{bulat}%"
