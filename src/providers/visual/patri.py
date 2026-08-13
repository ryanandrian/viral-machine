"""PATRI LARANGAN — lima larangan yang TIDAK BISA dibatalkan setelan mana pun.

═══ KENAPA BERKAS INI ADA (ketetapan owner 2026-08-13/14) ═══

Arsitektur yang diketok owner: **selebihnya milik tenant.** Aturan agama, adab, aurat, gaya — semua
itu dipilih pemilik niche lewat DNA-nya sendiri, dan tanggung jawab isi konten ada pada tenant
(sudah tertulis di Syarat & Ketentuan). Yang dipatri di kode HANYA yang tetap menempel pada
MesinViral walau tenant sudah menyetujui apa pun:

  1. Penggambaran ALLAH SWT                      — ketetapan owner
  2. Wajah/wujud NABI MUHAMMAD ﷺ                 — ketetapan owner
  3. Tulisan Arab / teks Al-Qur'an yang TERBACA   — mesin gambar SELALU mengacak huruf Arab; ayat
                                                    yang salah tulis = mudarat, dan itu kecelakaan
                                                    otomatis, bukan pilihan tenant
  4. Keselamatan anak                             — pidana; tak ada disclaimer yang memindahkannya
  5. Konten seksual / ketelanjangan               — mengancam IZIN PENERBITAN GOOGLE milik MesinViral,
                                                    aset kita, bukan aset tenant

═══ KENAPA DUA MEKANISME, BUKAN SATU ═══

(a) TEMPELAN — patri ikut di setiap prompt. Ia melarang, tapi hanya sekuat kepatuhan model.
(b) PENYARING — prompt yang MEMINTA hal terlarang TIDAK PERNAH DIKIRIM. Ini kunci sungguhan:
    tidak bergantung pada kepatuhan siapa pun.

Tempelan WAJIB masuk ke prompt POSITIF untuk transport yang tak punya kanal larangan. Terukur
13-Agu: FLUX/Cloudflare mengabaikan kanal larangan sepenuhnya, dan jalur video tak punya kanal itu
sama sekali. Menaruh patri hanya di kanal larangan = patri mati di sebagian besar channel.

═══ TANGGAPAN BERTINGKAT — INI YANG MENJAGA PRODUKSI TETAP HIDUP ═══

Rancangan pertama memblokir setiap prompt yang MENYEBUT nama. Diuji-kering pada 679 prompt produksi
nyata: **3 produksi SAH akan mati** — halaman masjid sunyi "melambangkan perjalanan Nabi Muhammad",
mushaf terbuka "perwujudan wahyu yang diterima Nabi Muhammad", timbangan "merenungkan mukjizat Nabi
Muhammad". Ketiganya benda/tempat, nol sosok. Rancangan daftar-kata bahkan memblokir 8.

Karena itu:
  • BLOKIR  — hanya bila niat menggambarkan SOSOK tak terbantahkan, atau meminta teks terbaca,
              atau huruf Arab sudah ada di dalam prompt.
  • KUATKAN — bila namanya muncul sebagai KONTEKS cerita: produksi JALAN TERUS, prompt ditambahi
              penegasan tepat sasaran.
Hasil uji-kering rancangan ini: **0 dari 679 prompt produksi diblokir**, 10/10 uji tandingan benar.

═══ GAGAL-TERBUKA (disengaja) ═══
Bila penyaring ini sendiri error, ia MELOLOSKAN. Kesalahan di kode kami tidak boleh menghentikan
produksi tenant; tempelan patri tetap terpasang sebagai jaring.
"""
from __future__ import annotations

import re

# ── TEMPELAN ────────────────────────────────────────────────────────────────────────────────────
# Sengaja PENDEK. Makin panjang teks tempelan, makin encer kepatuhan model pada tiap barisnya — dan
# makin besar pergeseran gaya pada channel yang menerimanya lewat prompt positif.
PATRI_GAMBAR = (
    "Absolute: never depict Allah/God or the Prophet Muhammad in any form; "
    "no readable Arabic or Qur'anic script; no nudity or sexual content; no minors in unsafe context."
)

# Penegasan tepat-sasaran saat nama hanya muncul sebagai konteks cerita (BUKAN pemblokiran).
PENEGAS_KONTEKS = (
    "Show only places, objects, light and landscape — no human figure of any revered religious "
    "figure appears in the frame."
)

_NAMA = (r"(?:prophet\s+muhammad|nabi\s+muhammad|rasulullah|muhammad\s*\(?(?:saw|pbuh|ﷺ)\)?)")
_GAMBAR = (r"(?:portrait\w*|depict\w*|portray\w*|imag\w*|figure|face|silhouette|likeness|show\w*|"
           r"standing|seated|sitting|walking|praying|holding|riding|speaking|wajah|sosok|gambar\w*)")

# BLOKIR: kata-menggambar dan NAMA berdekatan (≤40 huruf), dua arah. Jarak dekat inilah yang
# memisahkan "portrait of Nabi Muhammad" dari "melambangkan perjalanan Nabi Muhammad".
_RX_SOSOK = re.compile(rf"(?:{_GAMBAR}[^.]{{0,40}}{_NAMA}|{_NAMA}[^.]{{0,40}}{_GAMBAR})", re.I)
_RX_ALLAH = re.compile(
    r"\b(?:depict\w*|portray\w*|portrait|image|picture|face|form|figure|likeness|visage)\s+of\s+"
    r"(?:allah|god\s+almighty|the\s+almighty)\b|\ballah'?s\s+(?:face|form|figure|likeness)\b", re.I)
_RX_TEKS = re.compile(
    r"\b(?:readable|legible|visible|clear|written)\s+(?:arabic|qur'?anic|quranic)|"
    r"(?:arabic|qur'?anic|quranic)\s+(?:verse|ayah|text|inscription)\b", re.I)
_RX_ARAB = re.compile(r"[؀-ۿ]")
_RX_SEBUT = re.compile(_NAMA, re.I)

# Dua patri sisanya tak punya pola prompt yang khas (tak ada penulis prompt kami yang memintanya),
# jadi keduanya ditegakkan lewat TEMPELAN + kanal larangan, bukan lewat penyaring. Menuliskan pola
# tebakan untuk keduanya hanya akan melahirkan salah-tangkap tanpa menambah penjagaan.


def periksa_prompt(teks: str) -> str | None:
    """`None` = lolos · `"kuatkan"` = jalan terus dengan penegasan · selain itu = ALASAN BLOKIR."""
    try:
        # Teks patri kami SENDIRI memuat kata "depict … the Prophet Muhammad" — kalau ikut diperiksa,
        # penjaga akan memblokir prompt gara-gara kalimat penjaganya sendiri. Dibuang dulu.
        t = (teks or "").replace(PATRI_GAMBAR, " ").replace(PENEGAS_KONTEKS, " ")
        if _RX_SOSOK.search(t):
            return "meminta menggambarkan sosok Nabi Muhammad ﷺ"
        if _RX_ALLAH.search(t):
            return "meminta menggambarkan Allah SWT"
        if _RX_TEKS.search(t):
            return "meminta teks Arab/Al-Qur'an yang terbaca"
        if _RX_ARAB.search(t):
            return "memuat huruf Arab di dalam prompt (berisiko salah tulis)"
        if _RX_SEBUT.search(t):
            return "kuatkan"
        return None
    except Exception:      # gagal-terbuka: kesalahan kami tak boleh menghentikan produksi tenant
        return None


def tempel(positif: str, negatif: str, *, kanal_negatif: bool) -> tuple[str, str]:
    """Tempelkan patri PALING AKHIR supaya ia yang berbicara terakhir.

    `kanal_negatif=False` (FLUX, jalur video) → patri WAJIB ikut ke prompt positif, sebab tanpa itu
    ia tidak berlaku sama sekali di sana.
    """
    pos = f"{positif}\n\n{PATRI_GAMBAR}" if not kanal_negatif else positif
    neg = f"{negatif}, {PATRI_GAMBAR}" if kanal_negatif and negatif else (
        PATRI_GAMBAR if kanal_negatif else negatif)
    return pos, neg


def kuatkan(positif: str) -> str:
    """Prompt yang menyebut nama sebagai konteks — dikuatkan, TIDAK diblokir."""
    return f"{positif}\n\n{PENEGAS_KONTEKS}"


def potong_aman(prompt: str, batas: int) -> str:
    """Potong prompt ke `batas` huruf TANPA PERNAH memakan ekor patri.

    ⚠️ JEBAKAN YANG DITUTUP DI SINI (terukur 14-Agu, sebelum satu baris kode ditulis):
    Cloudflare memotong keras di 2.048 huruf. Patri ditempel di AKHIR supaya ia berbicara terakhir —
    dan justru karena itu ia jadi bagian PERTAMA yang hilang saat dipotong. Diukur pada 679 prompt
    produksi nyata: **12 (2%) melewati 2.048 huruf** sesudah patri + larangan niche ikut. Tanpa
    fungsi ini, 2% gambar akan dibuat TANPA patri sama sekali — bocor senyap, persis penyakit yang
    sedang diobati.

    Yang dikorbankan saat sempit: rincian adegan (bagian tengah). Yang TIDAK PERNAH dikorbankan:
    patri. Prioritas itu disengaja — larangan mengalahkan keindahan.
    """
    p = prompt or ""
    if len(p) <= batas:
        return p
    ekor = f"\n\n{PATRI_GAMBAR}"
    if p.endswith(ekor):
        kepala = p[: -len(ekor)]
        sisa = batas - len(ekor)
        if sisa > 0:
            return kepala[:sisa] + ekor
        return ekor[:batas]          # batas terlalu sempit → patri yang diselamatkan, bukan adegan
    return p[:batas]
