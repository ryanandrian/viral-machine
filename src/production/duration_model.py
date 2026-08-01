"""
Model durasi — mengubah "durasi yang dipesan" jadi angka yang PASTI, bukan ramalan.

═══ KENAPA MODUL INI ADA (ringkas; bukti penuh di QC_CONTENT_ARCHITECTURE.md §2c) ═══

Diukur dari 294 produksi nyata (2026-07-31): hanya **22% video mendarat** menurut aturan
titik-tengah owner. Rantai sebabnya:

  1. Estimator lama meramal dengan `kata ÷ (delivery_wps × 1,10) + Σ jeda_benih`. Angka jedanya
     BENIH yang tak pernah dikalibrasi (komentar aslinya sendiri menulis "SEED"). Diuji pada 60
     render naskah produksi: salah rata-rata **7,01 dtk**, hanya 10% yang akurat ±2 dtk.
  2. Karena taksirannya salah, anggaran kata salah, dan LLM hanya memenuhi 63–75% anggaran.
  3. Satu-satunya tambalan yang ada: MEMPERLAMBAT SUARA. Terukur: 41% render mentok di batas
     paling lambat (0,70) dan NOL render berjalan di kecepatan normal. Durasi tetap salah,
     dan mood narasi — barang yang kita jual — rusak. Owner MELARANG tuas ini (2026-07-29).

Modul ini menggantikan taksiran itu dengan pengukuran, dan menghapus kebutuhan akan tuas kecepatan.

═══ MODEL: SUARA MENGUCAP HURUF, BUKAN KATA ═══

    detik_audio = a·huruf + b·ANGKA + c·kalimat + d·elipsis + e·koma + f·em_dash

Bentuknya sama dengan estimator lama (bicara + jeda per tanda baca); yang berubah: satuan bicara
dari KATA → HURUF (+ suku ANGKA tersendiri), dan seluruh angkanya dikalibrasi dari render nyata.

Kenapa huruf: kata panjang butuh waktu lebih lama, dan panjang kata berbeda antar bahasa (terukur:
Inggris 5,07 huruf/kata · Indonesia 5,77). Dibandingkan jujur pada data yang sama dengan
leave-one-out (tiap naskah diramal oleh angka yang di-fit TANPA naskah itu):

    suara en-US-JennyNeural (n=60 naskah produksi)   suara id-ID-ArdiNeural (n=46)
      estimator lama    7,01 dtk · 10% akurat          2,76 dtk · 45%
      per KATA          1,55 dtk · 68%                 1,84 dtk · 64%
      per HURUF         0,96 dtk · 88%                 1,09 dtk · 89%
      per HURUF+ANGKA   0,84 dtk · 97%   ← dipakai     1,10 dtk · 89%   ← dipakai
      per VOKAL         1,27 dtk · 82%                 2,04 dtk · 73%

Diuji juga pada NASKAH PANJANG (190–383 kata, di luar rentang data kalibrasi — inilah rentang preset
75/90 & Regular): salah rata-rata 1,42 dtk (Gadis) dan 2,02 dtk (Ardi), terburuk 5,42 dtk. Jadi model
ini tidak jatuh saat diekstrapolasi ke naskah panjang — sifat yang WAJIB, karena preset panjang justru
yang paling sering meleset selama ini.

Kalibrasi PER-NICHE diuji juga dan TIDAK menang (1,17 dtk) — memecah data per niche membuat tiap
sel terlalu tipis. Jadi angka disimpan per SUARA, dan niche tetap berdampak lewat jalurnya sendiri
(persona narasi, gaya, avoid, visual, musik) — bukan lewat koefisien durasi. Bila kelak satu sel
(suara×niche) punya cukup sampel, `tts_pace_calibration` sudah berkunci (voice_key, niche) sehingga
bisa dipakai tanpa mengubah bentuk apa pun.

═══ ATURAN BATAS = KEPUTUSAN OWNER (2026-07-29) ═══

Hasil sah selama masih lebih dekat ke preset yang dipilih daripada ke preset tetangganya → batasnya
TITIK TENGAH antar-preset. Bukan persen karangan. Efek yang disengaja: batas melebar/menyempit
sendiri mengikuti kerapatan tangga preset. Preset 480 dtk = ambang iklan mid-roll: batas bawahnya
DIPATOK di 480,0 (kehilangan slot iklan = kehilangan uang, itu mengalahkan titik-tengah).

Modul ini SENGAJA fungsi murni (tanpa DB/jaringan/efek samping) supaya bisa diuji tuntas & di-replay.
Angka kalibrasi DISUNTIK oleh pemanggil (dari `tts_pace_calibration`), tidak pernah dibaca di sini.
"""

from __future__ import annotations

import re

# ── Angka BAWAAN (dipakai HANYA bila suara belum punya baris kalibrasi) ───────────────────────────
#
# Diperbarui 2026-08-01 dari PENGUKURAN LANGSUNG, menggantikan angka turunan-regresi yang terbukti
# salah besar. Yang lama vs yang terukur:
#
#     elipsis   1,376 → 0,288 dtk   (lama 5–9× terlalu BESAR)
#     koma      0,221 → 0,296 dtk   (lama 1,3–1,8× terlalu KECIL)
#     em-dash   0,442 → 0,292 dtk
#     kalimat   1,308 → 1,184 dtk
#
# Kenapa angka lama bisa sesalah itu: ia diturunkan dengan REGRESI dari naskah produksi, dan keempat
# tanda jeda bergerak bersama panjang naskah — regresi tak bisa memisahkannya. Angka baru diukur dengan
# pasangan teks ber-HURUF IDENTIK yang hanya berbeda tandanya (`pause_probe.py`), jadi selisih durasinya
# hanya bisa milik tanda itu.
#
# Sumber tiap angka (MEDIAN, bukan rata-rata — satu render aneh tak boleh menggeser hasil):
#   • jeda: median 5 suara Edge yang diukur langsung 2026-08-01 pada baseline produksinya masing-masing
#     (Ardi & Gadis di ratio 1; Christopher +5%, Guy +10%, Jenny +15% sesuai katalog).
#   • huruf & angka: median dua suara Indonesia dari 36 render naskah produksi di ratio 1, di-fit dengan
#     biaya jeda DIPATOK pada angka terukur (Ardi 0,04948/0,17796 · Gadis 0,06726/0,24625).
#
# Angka ini tetap CADANGAN, bukan tujuan: sebaran antar-suara lebar (kalimat 0,85–1,37 dtk), jadi suara
# yang benar-benar dipakai WAJIB diukur sendiri (`pause_probe`) atau dikalibrasi dari sampel produksi.
# Begitu `tts_pace_calibration` punya baris untuk sebuah suara, baris itu yang menang.
BAWAAN = {
    "sec_per_char":     0.05837,
    "sec_per_digit":    0.21211,
    "sec_per_sentence": 1.184,
    "sec_per_ellipsis": 0.288,
    "sec_per_comma":    0.296,
    "sec_per_em_dash":  0.292,
    "chars_per_word":   5.77,
    "words_per_sentence": 14.0,
}

# Ambang keras mid-roll YouTube (CONTENT_CATEGORY_ARCHITECTURE L9/OPSI A, 19-Jul): video preset ini
# TIDAK PERNAH boleh jadi di bawah 480,0 dtk → batas bawahnya satu-sisi.
AMBANG_MIDROLL = 480

# Batas kewajaran hasil kalibrasi. Di luar ini = data rusak → pakai bawaan + lapor (bukan clamp senyap).
PAGAR = {
    "sec_per_char":     (0.02, 0.12),
    "sec_per_digit":    (0.0, 0.60),
    "sec_per_sentence": (0.0, 4.0),
    "sec_per_ellipsis": (0.0, 5.0),
    "sec_per_comma":    (0.0, 2.0),
    "sec_per_em_dash":  (0.0, 3.0),
    "chars_per_word":   (3.0, 12.0),
    "words_per_sentence": (5.0, 30.0),
}

_RX_HURUF = re.compile(r"[^0-9A-Za-zÀ-ÿ]")


# ── ciri teks ─────────────────────────────────────────────────────────────────────────────────────

def ciri_teks(teks: str) -> dict:
    """Hitung ciri yang menentukan durasi. SEMUA dari teks — bebas provider & bebas bahasa.

    Elipsis tidak dihitung ulang sebagai akhir-kalimat (identik `script_engine._count_pauses`),
    supaya satu tanda tidak dihitung dua kali.
    """
    t = teks or ""
    ell = t.count("…") + t.count("...")
    t2 = t.replace("…", "  ").replace("...", "  ")
    return {
        "chars":    len(_RX_HURUF.sub("", t)),
        # ANGKA diucapkan JAUH lebih panjang daripada hurufnya: terukur langsung, "Pada tahun 1348
        # wabah itu datang." (27 huruf) = 4,94 dtk sedangkan "Pada tahun itu wabah besar datang."
        # (28 huruf) = 3,24 dtk — satu tahun empat-angka menambah 1,70 dtk, karena "1348" dibacakan
        # "seribu tiga ratus empat puluh delapan" (6 kata). Naskah niche sejarah penuh tahun, jadi
        # tanpa suku ini ramalan bisa meleset belasan detik. Digit dihitung TERPISAH (biayanya di ATAS
        # biaya hurufnya). Terukur konsisten 0,12–0,18 dtk/digit di kelima suara produksi.
        "digits":   sum(1 for ch in t if ch.isdigit()),
        "words":    len(t.split()),
        "sentence": len(re.findall(r"[.!?]+", t2)),
        "ellipsis": ell,
        "comma":    t2.count(",") + t2.count(";") + t2.count(":"),
        "em_dash":  t.count("—"),
    }


def angka_efektif(kalibrasi: dict | None) -> dict:
    """Gabung angka kalibrasi (dari DB) di atas angka bawaan, dengan pagar kewajaran.

    Nilai di luar pagar DIBUANG (pakai bawaan untuk kunci itu) — bukan di-clamp diam-diam, supaya
    data rusak tidak menyelinap jadi angka yang tampak masuk akal.
    """
    out = dict(BAWAAN)
    for k, (lo, hi) in PAGAR.items():
        v = (kalibrasi or {}).get(k)
        try:
            if v is not None and lo <= float(v) <= hi:
                out[k] = float(v)
        except (TypeError, ValueError):
            pass
    return out


def rincian_audio(teks: str, kalibrasi: dict | None = None) -> dict:
    """Pecahan detik audio: waktu BICARA vs waktu JEDA. Dipakai pelaporan & kalibrasi — memisahkan
    keduanya penting karena dua bulan pencarian akar meleset justru karena porsi JEDA tak terlihat."""
    a = angka_efektif(kalibrasi)
    f = ciri_teks(teks)
    bicara = a["sec_per_char"] * f["chars"] + a["sec_per_digit"] * f["digits"]
    jeda = (a["sec_per_sentence"] * f["sentence"] + a["sec_per_ellipsis"] * f["ellipsis"]
            + a["sec_per_comma"] * f["comma"] + a["sec_per_em_dash"] * f["em_dash"])
    return {"bicara": round(bicara, 2), "jeda": round(jeda, 2), "total": round(bicara + jeda, 2), **f}


def prediksi_audio(teks: str, kalibrasi: dict | None = None) -> float:
    """Perkiraan detik AUDIO dari teks. Inilah pengganti taksiran lama.

    Terukur (leave-one-out, 106 render naskah produksi): salah rata-rata 0,96–1,09 dtk, ~88% dalam
    ±2 dtk. Estimator lama pada data yang sama: 2,76–7,01 dtk, 10–45%.
    """
    a = angka_efektif(kalibrasi)
    f = ciri_teks(teks)
    return round(
        a["sec_per_char"] * f["chars"]
        + a["sec_per_digit"] * f["digits"]
        + a["sec_per_sentence"] * f["sentence"]
        + a["sec_per_ellipsis"] * f["ellipsis"]
        + a["sec_per_comma"] * f["comma"]
        + a["sec_per_em_dash"] * f["em_dash"], 2)


# ── batas sah (aturan titik-tengah owner) ─────────────────────────────────────────────────────────

def band_video(seconds: float, presets: list) -> tuple[float, float]:
    """Batas durasi VIDEO yang sah untuk sebuah preset (aturan titik-tengah owner).

    Preset terkecil tak punya tetangga bawah → 0 (video lebih pendek tidak menyeberang ke preset
    lain). Preset terbesar → dicerminkan dari jarak tetangga bawahnya. Preset ambang mid-roll →
    batas bawah dipatok di ambang itu.
    """
    if not presets:
        raise ValueError("daftar preset kosong — batas tak bisa dihitung tanpa tetangga")
    urut = sorted(float(p) for p in presets)
    s = float(seconds)
    if s not in urut:
        raise ValueError(f"preset {seconds} tak ada di tangga aktif {urut}")
    i = urut.index(s)
    lo = (urut[i - 1] + s) / 2 if i > 0 else 0.0
    hi = (s + urut[i + 1]) / 2 if i < len(urut) - 1 else (s + (s - urut[i - 1]) / 2 if i > 0 else s * 1.5)
    if int(s) == AMBANG_MIDROLL:
        lo = float(AMBANG_MIDROLL)
    return lo, hi


def resep(seconds: float, presets: list, overhead: float, kalibrasi: dict | None = None) -> dict:
    """Perintah yang diberikan ke penulis: berapa KATA dan berapa KALIMAT.

    Dua-duanya lahir dari satu perhitungan, karena keduanya saling menentukan: tiap kalimat memakan
    jeda (terukur 0,6–1,3 dtk), jadi jumlah kalimat mengubah berapa kata yang muat. Panjang kalimat
    dipatok ke panjang ALAMI hasil ukur naskah nyata (`words_per_sentence`) supaya perintahnya tidak
    melahirkan naskah aneh — satu kalimat 200 kata "muat" secara matematis tapi bukan narasi.

    Kenapa jumlah kalimat ikut diperintahkan: terukur, model MENAATI perintah jumlah kalimat jauh
    lebih baik daripada jumlah kata (kalimat bisa dihitung sendiri oleh model; kata tidak).

    overhead = detik non-suara di video final (jeda-akhir + loop bersih), dari `effective_overhead`.
    """
    a = angka_efektif(kalibrasi)
    lo, hi = band_video(seconds, presets)
    o = max(0.0, float(overhead))
    audio_lo, audio_hi = max(0.5, lo - o), max(0.5, hi - o)

    # tanda baca per kalimat = kebiasaan naskah nyata (median terukur), dipakai memperkirakan jeda
    jeda_per_kalimat = (a["sec_per_sentence"] + a["sec_per_comma"] * 1.0 + a["sec_per_em_dash"] * 0.2)
    detik_per_kata = a["sec_per_char"] * a["chars_per_word"] + jeda_per_kalimat / a["words_per_sentence"]

    kata_lo = max(3, int(audio_lo / detik_per_kata) + 1)
    kata_hi = max(kata_lo, int(audio_hi / detik_per_kata))
    kata_bidik = round((kata_lo + kata_hi) / 2)
    return {
        "kata_min": kata_lo, "kata_maks": kata_hi, "kata_bidik": kata_bidik,
        "kalimat": max(1, round(kata_bidik / a["words_per_sentence"])),
        "audio_min": round(audio_lo, 1), "audio_maks": round(audio_hi, 1),
        "band_video": (lo, hi), "detik_per_kata": round(detik_per_kata, 4),
    }


def vonis(teks: str, seconds: float, presets: list, overhead: float,
          kalibrasi: dict | None = None) -> dict:
    """Vonis SEBELUM sepeser pun dibelanjakan ke suara/gambar.

    status: 'ok' | 'terlalu_panjang' | 'terlalu_pendek'
    Bila tidak ok, `kata_selisih` = perkiraan kata yang harus ditambah/dikurangi — itulah angka yang
    diberikan ke penulis untuk memperbaiki naskahnya sendiri (bukan mesin yang membuang kalimat:
    terbukti 2026-07-31 aturan buatan-tangan membuang fakta terkuat naskah).
    """
    r = resep(seconds, presets, overhead, kalibrasi)
    audio = prediksi_audio(teks, kalibrasi)
    video = round(audio + max(0.0, float(overhead)), 2)
    lo, hi = r["band_video"]
    n = ciri_teks(teks)["words"]
    if video > hi:
        status, selisih = "terlalu_panjang", max(1, n - r["kata_maks"])
    elif video < lo:
        status, selisih = "terlalu_pendek", max(1, r["kata_min"] - n)
    else:
        status, selisih = "ok", 0
    return {"status": status, "kata_selisih": selisih, "audio_prediksi": audio,
            "video_prediksi": video, "band_video": (lo, hi), "kata": n,
            "kata_min": r["kata_min"], "kata_maks": r["kata_maks"]}
