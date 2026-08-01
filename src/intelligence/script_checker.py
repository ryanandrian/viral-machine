"""
Pemeriksa mutu naskah — CACAT MEKANIS yang bisa dipastikan tanpa menebak.

═══ KENAPA DI KODE, BUKAN DI AI ═══

Diuji berdampingan pada naskah yang sama (riset 29–31 Jul 2026): KODE menangkap LEBIH BANYAK cacat
daripada penilai AI — kalimat menggantung, kata bahasa asing menyelinap, kata yang DILARANG niche,
frasa berulang, artefak sambungan. Sebaliknya AI MELEWATKAN pelanggaran register meskipun DNA niche
diberikan (mis. "secara magis" lolos di niche islami). Pembagian tugasnya karena itu:

  • KODE (modul ini) — cacat yang bisa DIPASTIKAN: pasti, gratis, tidak pernah halusinasi.
  • AI (`script_analyzer`) — penilaian rasa: daya hook, ketegangan, kepadatan informasi.

Modul ini TIDAK menilai mutu artistik dan tidak pernah memberi skor. Ia hanya menjawab satu
pertanyaan: apakah ada cacat yang PASTI merusak, dan di mana persisnya.

═══ NICHE ADALAH SUMBER ATURAN, BUKAN KODE ═══

Kata terlarang, nada, dan gaya diambil dari baris niche di DB (`niches.narration_persona.avoid`,
`.tone`, `.style`) — modul ini tidak pernah memuat daftar per-niche di dalam kode. Konsekuensinya
disengaja: menambah niche ke-48 sampai ke-500 tidak menyentuh kode sama sekali, dan mengubah aturan
sebuah niche cukup di baris niche-nya. (Pelajaran: ratusan niche akan datang; setelan per-niche di
kode akan mati sejak niche kesepuluh.)

═══ APA YANG DIPERIKSA ═══

1. `kalimat_menggantung` — naskah tidak berakhir di tanda baca akhir → penonton mendengar potongan.
2. `elipsis` — tanda "..." memakan >1 detik hening TERUKUR dan merusak takaran durasi.
3. `frasa_berulang` — frasa 3-kata yang sama muncul ≥3× (mis. "peradaban ini" 8× dalam satu naskah
   long-form) → terdengar seperti mesin, dan itu profil yang didemonetisasi YouTube (risiko #1 produk).
4. `kata_terlarang_niche` — kata dari `narration_persona.avoid` niche itu sendiri.
5. `bahasa_asing` — kata bahasa lain menyelinap saat bahasa konten non-Inggris; DAFTARNYA dari kata
   fungsi yang mustahil muncul secara sah, bukan kamus (tidak menghakimi istilah teknis).
6. `label_beat_bocor` — nama bagian ("hook:", "core_facts") ikut terbaca narator.
7. `artefak_sambungan` — sisa penggabungan per-segmen: spasi ganda, titik ganda, kalimat diawali
   huruf kecil setelah titik.

Keluaran: daftar temuan {jenis, parah, pesan, bukti}. `parah=True` = cacat yang pasti terdengar/
terlihat penonton → pemanggil boleh menolak naskah. `parah=False` = layak diperbaiki, bukan penolak.
"""

from __future__ import annotations

import re
from collections import Counter

# Kata fungsi bahasa Inggris yang tidak mungkin muncul SAH di narasi non-Inggris. Sengaja SEMPIT —
# istilah teknis/nama asing memang lumrah dipakai; yang ditangkap hanya penanda "model lupa bahasa".
_KATA_INGGRIS_UMUM = {
    "the", "and", "but", "with", "that", "this", "these", "those", "from", "have", "has", "was",
    "were", "will", "would", "could", "should", "there", "their", "which", "when", "while",
    "because", "however", "moreover", "therefore", "although", "beneath", "through", "within",
    "imagine", "discovered", "actually", "literally", "basically",
}
_TANDA_AKHIR = ".!?…\"'”’)"
# Satu kata asing nyasar bukan bukti "model lupa bahasa" (bisa nama diri/istilah);
# dua kata berbeda baru pola. Ambang ini menutup salah-tuduh yang terukur saat uji sendiri.
_MIN_KATA_ASING = 2
_PISAH = "\"'“”‘’«»()[]{}.,;:!?…—–-"
_RX_KATA = re.compile(r"[A-Za-zÀ-ÿ']+")
# Penutup KALIMAT sebenarnya — sengaja BUKAN `_TANDA_AKHIR` (yang juga memuat kutip & kurung untuk
# memeriksa akhir naskah). Menghitung kalimat dengan tanda kutip akan melipatgandakan hitungannya.
_TANDA_KALIMAT = ".!?…"


def _temuan(jenis: str, parah: bool, pesan: str, bukti: str = "") -> dict:
    return {"jenis": jenis, "parah": parah, "pesan": pesan, "bukti": bukti[:200]}


def periksa_naskah(teks: str, niche_profile: dict | None = None,
                   content_language: str | None = None,
                   beat_keys: list | None = None) -> list[dict]:
    """Periksa satu naskah final. Mengembalikan daftar temuan (kosong = bersih).

    `niche_profile` = baris niche dari DB (dipakai `narration_persona.avoid`). None → cek kata
    terlarang dilewati (tidak mengarang daftar sendiri).
    `content_language` = locale konten channel; non-`en*` menghidupkan cek bahasa asing.
    `beat_keys` = nama bagian aktif, untuk mendeteksi labelnya bocor jadi ucapan narator.
    """
    t = (teks or "").strip()
    out: list[dict] = []
    if not t:
        return [_temuan("kosong", True, "Naskah kosong.")]

    # 1. kalimat menggantung
    if t[-1] not in _TANDA_AKHIR:
        out.append(_temuan("kalimat_menggantung", True,
                           "Naskah tidak berakhir dengan tanda baca akhir — penonton akan mendengar "
                           "kalimat terputus.", t[-60:]))

    # 1b. NARASI SATU TARIKAN NAPAS — kalimat kepanjangan / nyaris tanpa titik.
    #
    # Terukur pada pipeline SUNGGUHAN (BISIK NUSANTARA, 2026-08-02 03:01): llama-3.3 mengirim naskah
    # 76 kata dengan **NOL kalimat** — tak satu pun titik. Penyebabnya umpan balik durasi kita
    # sendiri: "Every sentence end costs real silence — merge sentences instead of adding them."
    # Benar secara durasi, tapi model lemah menelannya mentah dan membuang SELURUH titik. Hasilnya
    # narator membaca tanpa jeda sampai kehabisan napas — persis "potongan yang merusak narasi".
    #
    # Ambangnya sengaja bukan "jumlah kalimat" (itu bergantung panjang naskah/preset) melainkan
    # KEPADATAN: rata-rata kata per kalimat. Naskah nyata bermedian ±13 kata/kalimat; di atas 2,5×
    # itu bukan gaya, melainkan kalimat yang tak pernah ditutup.
    _kata = _RX_KATA.findall(t)
    _n_kal = sum(t.count(x) for x in _TANDA_KALIMAT)
    if len(_kata) >= 25:
        from src.config import ambang as _amb
        from src.production.duration_model import BAWAAN as _DUR
        _maks = _amb.angka("script_maks_kata_per_kalimat", 32)
        _wpk = len(_kata) / max(1, _n_kal)
        if _n_kal == 0 or _wpk > _maks:
            out.append(_temuan(
                "narasi_tanpa_jeda", True,
                f"{len(_kata)} kata hanya dalam {_n_kal} kalimat ({_wpk:.0f} kata/kalimat; wajar "
                f"±{_DUR['words_per_sentence']:.0f}, batas {_maks}) — narator membaca tanpa jeda "
                f"sampai kehabisan napas. Pecah jadi kalimat-kalimat utuh.", t[:120]))

    # 2. elipsis (biaya hening TERUKUR >1 detik per tanda)
    n_ell = t.count("…") + t.count("...")
    if n_ell:
        out.append(_temuan("elipsis", False,
                           f"{n_ell} tanda '...' — prompt melarangnya: ia menambah keheningan "
                           f"(terukur 0,16–0,38 dtk per tanda, tergantung suara) dan membuat narasi "
                           f"terdengar menggantung.", ""))

    # 3. frasa berulang (3-kata, ≥3 kemunculan)
    kata = [w.lower() for w in _RX_KATA.findall(t)]
    if len(kata) >= 12:
        tri = Counter(tuple(kata[i:i + 3]) for i in range(len(kata) - 2))
        ulang = [(" ".join(k), n) for k, n in tri.items() if n >= 3]
        if ulang:
            ulang.sort(key=lambda x: -x[1])
            out.append(_temuan("frasa_berulang", False,
                               f"{len(ulang)} frasa berulang ≥3 kali — terdengar seperti mesin.",
                               "; ".join(f'"{f}" ({n}x)' for f, n in ulang[:4])))

    # 4. kata terlarang menurut NICHE ITU SENDIRI (bukan daftar di kode)
    avoid_raw = ((niche_profile or {}).get("narration_persona") or {}).get("avoid") if niche_profile else None
    if avoid_raw:
        frasa = [x.strip().lower() for x in re.split(r"[,;·|]|\band\b", str(avoid_raw)) if len(x.strip()) >= 4]
        # Cocok per-KATA (batas kata), BUKAN potongan kata. Terukur saat uji sendiri: avoid "keras"
        # menandai "Kekerasan itu tercatat pada tahun 1965." sebagai pelanggaran → naskah sah DITOLAK
        # dan satu putaran retry terbuang. Cacat ini ditanam hari yang sama saat modul dibuat.
        rendah = t.lower()
        kena = [f for f in frasa
                if re.search(rf"(?<![0-9a-zà-ÿ]){re.escape(f)}(?![0-9a-zà-ÿ])", rendah)]
        if kena:
            out.append(_temuan("kata_terlarang_niche", True,
                               f"{len(kena)} kata/frasa yang DILARANG niche ini masih dipakai.",
                               "; ".join(kena[:5])))

    # 5. bahasa asing menyelinap (hanya untuk konten non-Inggris)
    if content_language and not str(content_language).lower().startswith("en"):
        # Kata asing di dalam NAMA DIRI itu SAH ("Kanal The Explorer", "Discovery Channel"). Terukur
        # saat uji sendiri: kalimat sah "Kanal The Explorer membahas Palung Mariana sejak 2019."
        # ditandai pelanggaran PARAH → naskah ditolak. Karena itu: token yang berada dalam rangkaian
        # ber-huruf-besar DILEWATI, dan satu kata nyasar saja belum dianggap "model lupa bahasa" —
        # butuh minimal dua kata berbeda. Cacat ini ditanam hari yang sama saat modul dibuat.
        token = re.findall(r"\S+", t)
        asing = set()
        for i, w in enumerate(token):
            b = w.strip(_PISAH)
            if b.lower() not in _KATA_INGGRIS_UMUM:
                continue
            tetangga = [token[j].strip(_PISAH) for j in (i - 1, i + 1) if 0 <= j < len(token)]
            if any(x[:1].isupper() for x in tetangga if x):
                continue                      # dalam rangkaian nama diri → sah
            asing.add(b.lower())
        if len(asing) >= _MIN_KATA_ASING:
            out.append(_temuan("bahasa_asing", True,
                               f"{len(asing)} kata bahasa Inggris menyelinap ke narasi non-Inggris.",
                               ", ".join(sorted(asing)[:8])))

    # 6. label beat bocor jadi ucapan narator
    for b in (beat_keys or []):
        pola = re.compile(rf"\b{re.escape(str(b))}\b\s*:", re.I)
        if pola.search(t):
            out.append(_temuan("label_beat_bocor", True,
                               f"Nama bagian '{b}' terbaca di naskah — narator akan mengucapkannya.",
                               pola.search(t).group(0)))
            break

    # 7. artefak sambungan (khas naskah yang digabung per-segmen)
    #
    # ELIPSIS DIKELUARKAN DULU. Cacat di pemeriksa ini sendiri, terukur pada 82 naskah produksi
    # (2026-08-02): `\.\s*\.` ikut cocok DI DALAM "..." , dan `[.!?]\s+[a-z]` cocok pada "you... it's".
    # Hasilnya elipsis dihitung DUA KALI — sekali sebagai elipsis (aturan 2, benar) dan sekali lagi
    # sebagai "titik ganda" + "kalimat diawali huruf kecil" (10× dan 5×, keduanya SALAH). Penulis lalu
    # diminta memperbaiki sisa-penggabungan yang tidak pernah ada, memakai putaran perbaikan dan kuota
    # penyedia untuk mengejar hantu.
    #
    # Elipsis diganti satu karakter penanda (bukan spasi, bukan titik) supaya penggantiannya sendiri
    # tak melahirkan "spasi ganda" palsu.
    _tj = t.replace("…", "\x01")
    while "..." in _tj:
        _tj = _tj.replace("...", "\x01")
    _tj = _tj.replace("..", "\x01\x01")     # dua titik = artefak sungguhan, jangan disamarkan
    artefak = []
    if "\x01\x01" in _tj or re.search(r"\.\s*\.", _tj):
        artefak.append("titik ganda")
    if "  " in _tj:
        artefak.append("spasi ganda")
    if re.search(r"[.!?]\s+[a-zà-ÿ]", _tj):
        artefak.append("kalimat diawali huruf kecil")
    if artefak:
        out.append(_temuan("artefak_sambungan", False,
                           "Sisa penggabungan naskah: " + ", ".join(artefak) + ".", ""))
    return out


def ringkas_temuan(temuan: list[dict]) -> str:
    """Satu baris ringkas untuk log & umpan-balik retry ke penulis."""
    if not temuan:
        return "bersih"
    return " · ".join(f"{'⛔' if t['parah'] else '⚠'}{t['jenis']}"
                      + (f"[{t['bukti']}]" if t["bukti"] else "") for t in temuan)


def ada_cacat_parah(temuan: list[dict]) -> bool:
    return any(t["parah"] for t in temuan)
