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
_RX_KATA = re.compile(r"[A-Za-zÀ-ÿ']+")


def _kalimat(teks: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?…])\s+", (teks or "").strip()) if x.strip()]


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

    # 2. elipsis (biaya hening TERUKUR >1 detik per tanda)
    n_ell = t.count("…") + t.count("...")
    if n_ell:
        out.append(_temuan("elipsis", False,
                           f"{n_ell} tanda '...' — tiap tanda memakan lebih dari 1 detik hening dan "
                           f"mengacaukan takaran durasi.", ""))

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
        rendah = t.lower()
        kena = [f for f in frasa if f in rendah]
        if kena:
            out.append(_temuan("kata_terlarang_niche", True,
                               f"{len(kena)} kata/frasa yang DILARANG niche ini masih dipakai.",
                               "; ".join(kena[:5])))

    # 5. bahasa asing menyelinap (hanya untuk konten non-Inggris)
    if content_language and not str(content_language).lower().startswith("en"):
        asing = sorted({w for w in kata if w in _KATA_INGGRIS_UMUM})
        if asing:
            out.append(_temuan("bahasa_asing", True,
                               f"{len(asing)} kata bahasa Inggris menyelinap ke narasi non-Inggris.",
                               ", ".join(asing[:8])))

    # 6. label beat bocor jadi ucapan narator
    for b in (beat_keys or []):
        pola = re.compile(rf"\b{re.escape(str(b))}\b\s*:", re.I)
        if pola.search(t):
            out.append(_temuan("label_beat_bocor", True,
                               f"Nama bagian '{b}' terbaca di naskah — narator akan mengucapkannya.",
                               pola.search(t).group(0)))
            break

    # 7. artefak sambungan (khas naskah yang digabung per-segmen)
    artefak = []
    if re.search(r"\.\s*\.", t):
        artefak.append("titik ganda")
    if "  " in t:
        artefak.append("spasi ganda")
    if re.search(r"[.!?]\s+[a-zà-ÿ]", t):
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
