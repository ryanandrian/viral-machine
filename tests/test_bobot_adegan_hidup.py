"""BOBOT ADEGAN YANG DISETEL MESIN HARUS SAMPAI KE PRODUKSI — bukan berhenti di database.

Cacat yang ditutup di sini (terukur 2026-08-01, diperbaiki 2026-08-02):

`align_beat_weights` menulis bobot baru ke `content_beats` tiap hari — dan itu benar-benar berjalan
di produksi (log: `core_facts 12→11` 29-Jul; `climax 10→9` 1-Agu 10:23:23). Tetapi `script_engine`
membaca tabel itu SEKALI saat modul dimuat lalu menyimpannya sebagai konstanta modul
(`_BEAT_WEIGHT`, `_ROLE_LABEL`, `_ALL_SECTIONS`, `_DEFAULT_SECTION_TIMING`). Pekerja yang menyala
1-Agu 10:22:04 memegang foto lama, jadi perubahan 10:23:23 TIDAK PERNAH sampai ke pembagian kata —
dan tak akan sampai sampai proses di-restart. Perubahan MANUAL admin di layar "Bobot antar-adegan"
mengalami nasib yang sama: tersimpan benar, tak pernah berlaku.

Ini kelas cacat yang sama dengan pelajaran mahal 31-Jul ("mencabut separuh rantai"): mata rantai
TERAKHIR tertinggal, jadi seluruh rantai belajar tampak hidup padahal buntu.

Uji ini menirukan kejadian aslinya: ubah bobot di sumber SAAT proses sedang berjalan, lalu tuntut
pembagian kata ikut berubah — tanpa impor ulang, tanpa restart.
"""

import time

import src.content.beats as beats
import src.intelligence.script_engine as se

# Kosakata tiruan: sengaja bukan angka produksi, supaya kelulusan uji tak bisa datang dari kebetulan.
_VOCAB_A = [
    {"beat_key": "hook", "sort_order": 1, "label_upper": "HOOK", "weight": 5,
     "default_timing_sec": 3, "motion_index": 0, "motion_mode": "fix", "motion_dir": "zoom_in",
     "motion_rate": 0.05, "hint_id": "", "hint_en": ""},
    {"beat_key": "core_facts", "sort_order": 2, "label_upper": "CORE FACT", "weight": 5,
     "default_timing_sec": 15, "motion_index": 3, "motion_mode": "fix", "motion_dir": "zoom_in",
     "motion_rate": 0.03, "hint_id": "", "hint_en": ""},
    {"beat_key": "cta", "sort_order": 3, "label_upper": "CTA", "weight": 5,
     "default_timing_sec": 3, "motion_index": 5, "motion_mode": "fix", "motion_dir": "zoom_out",
     "motion_rate": 0.05, "hint_id": "", "hint_en": ""},
]


def _pasang(vocab):
    """Tanam kosakata langsung ke cache modul beats — meniru 'DB sudah berubah, cache masih segar'."""
    beats._CACHE.update(vocab=[dict(b) for b in vocab], ts=time.time())


def _pulihkan():
    beats._CACHE.update(vocab=None, ts=0.0)


def test_bobot_baru_langsung_dipakai_tanpa_restart():
    """Mesin menurunkan bobot satu adegan di tengah jalan → pembagian kata WAJIB ikut bergeser."""
    try:
        _pasang(_VOCAB_A)
        aktif = ["hook", "core_facts", "cta"]
        sebelum = se._distribute_words(aktif, 300)
        assert sebelum == {"hook": 100, "core_facts": 100, "cta": 100}, sebelum

        # Persis yang dilakukan `align_beat_weights` 1-Agu 10:23:23 — angka satu adegan turun.
        baru = [dict(b) for b in _VOCAB_A]
        baru[0]["weight"] = 1        # hook 5 → 1
        _pasang(baru)

        sesudah = se._distribute_words(aktif, 300)
        assert sesudah != sebelum, (
            "bobot berubah di sumber tetapi pembagian kata TIDAK bergeser — nilai masih beku "
            "seperti sebelum perbaikan 2026-08-02"
        )
        # 1 : 5 : 5 dari 300 kata
        assert sesudah == {"hook": 27, "core_facts": 136, "cta": 136}, sesudah
        assert sum(sesudah.values()) == 299    # pembulatan per-adegan, bukan kebocoran
    finally:
        _pulihkan()


def test_adegan_dinonaktifkan_admin_langsung_hilang_dari_daftar():
    """Admin menonaktifkan satu adegan → daftar adegan yang dipakai penulis ikut menyusut seketika."""
    try:
        _pasang(_VOCAB_A)
        assert se._all_sections() == ["hook", "core_facts", "cta"]
        _pasang([b for b in _VOCAB_A if b["beat_key"] != "core_facts"])
        assert se._all_sections() == ["hook", "cta"], "daftar adegan masih memakai foto lama"
    finally:
        _pulihkan()


def test_label_dan_durasi_bawaan_juga_ikut_hidup():
    """Tiga nilai lain yang dulu ikut beku: label peran & durasi bawaan per-adegan."""
    try:
        _pasang(_VOCAB_A)
        assert se._role_label()["hook"] == "HOOK"
        assert se._default_section_timing()["core_facts"] == 15

        diubah = [dict(b) for b in _VOCAB_A]
        diubah[0]["label_upper"] = "PEMBUKA"
        diubah[1]["default_timing_sec"] = 21
        _pasang(diubah)

        assert se._role_label()["hook"] == "PEMBUKA", "label peran masih beku"
        assert se._default_section_timing()["core_facts"] == 21, "durasi bawaan masih beku"
    finally:
        _pulihkan()


def test_tak_ada_lagi_nilai_beku_saat_modul_dimuat():
    """Penjaga anti-kambuh: konstanta modul yang membekukan isi DB tidak boleh lahir lagi.

    Bukan memeriksa nama lama, dan bukan membandingkan NILAI (versi pertama penjaga ini melakukan itu
    dan LOLOS pada kode lama — potret bekunya berisi angka DB asli, sementara pembandingnya kosakata
    tiruan). Yang diuji sekarang BENTUKNYA: adakah atribut modul yang berbentuk salinan tabel
    `content_beats` — peta berkunci-persis daftar adegan, atau daftar adegan itu sendiri. Kambuhnya
    cacat ini akan berbentuk begitu, dengan nama apa pun.
    """
    _pulihkan()                      # pakai kosakata SEBENARNYA (DB/kanon), bukan tiruan
    kunci_adegan = set(beats.all_beats())
    daftar_adegan = beats.all_beats()

    beku = []
    for nama in dir(se):
        if nama.startswith("__"):
            continue
        nilai = getattr(se, nama, None)
        if isinstance(nilai, dict) and nilai and set(nilai) == kunci_adegan:
            beku.append(f"{nama} (peta berkunci adegan)")
        elif isinstance(nilai, list) and nilai == daftar_adegan:
            beku.append(f"{nama} (daftar adegan)")
    assert not beku, (
        "isi tabel content_beats dibekukan sebagai atribut modul — perubahan bobot/label/daftar "
        f"adegan tak akan sampai ke produksi sampai proses di-restart: {beku}"
    )
