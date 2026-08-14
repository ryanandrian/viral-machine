"""PEMANASAN SKEMA SDK — menutup sebab mesin MATI MENDADAK (SIGSEGV). SSOT: §8L.

═══ APA YANG TERJADI ═══

`systemd`: `mv-worker.service: Main process exited, code=killed, status=11/SEGV` — **6× sejak 1-Agu**.
Setiap kali, produksi yang sedang berjalan HILANG TANPA JEJAK: proses mati sebelum sempat menulis satu
baris pun ke `production_runs`, jadi bagi sistem kita produksi itu tak pernah ada dan tenant tak
dikabari apa pun. Bentuk kerugian yang sama dengan video `xa3Rbi-SbXM` (12-Agu).

Sebabnya baru terlihat 14-Agu 23:00:52, saat perekam kematian ([B26]-D) berbicara pertama kali.
Rantai lengkapnya, dari frame PALING BAWAH (yang memulai) ke atas:

    producer._task → produce_one → pipeline.run → niche_selector.select → _analyze_with_ai
      → adapters.complete → openai chat.completions.create → _base_client.post → request
      → [balasan diurai] → openai/_models.py `_get_extra_fields_type`
      → pydantic `_mock_val_ser` → `model_rebuild` → `complete_model_class`
      → `generate_schema` → `_model_schema` → … (rekursif) → **SIGSEGV**

═══ AKAR MASALAHNYA — dua lapis, keduanya wajib dipahami ═══

**(1) JALURNYA.** SDK OpenAI membangun skema pydantic-nya **secara MALAS** — ditunda sampai balasan
PERTAMA diurai. `_get_extra_fields_type` menyentuh `cls.__pydantic_core_schema__`, dan sentuhan itulah
yang memicu pembangunan. Balasan pertama selalu tiba **di dalam thread produksi**, tempat tumpukan
panggilan sudah terpakai puluhan frame oleh pipeline. Pembangunan skema itu rekursif dan bolak-balik
menyeberang Python↔Rust (pydantic-core), memakan tumpukan C **tanpa menambah frame Python** — karena
itu yang terjadi bukan `RecursionError` yang bisa ditangkap, melainkan **SIGSEGV yang membunuh
SELURUH proses**, ketujuh thread sekaligus.

**(2) PENERJEMAHNYA VERSI KANDIDAT.** Mesin berjalan di atas **Python 3.11.0rc1** — *release
candidate* Agustus 2022, bukan rilis final; frame teratas rekaman kematian adalah
`contextlib.__exit__`, yaitu area yang dirombak besar di 3.11 dan terus diperbaiki pada rilis
berikutnya. Dimutakhirkan **di tempat** ke 3.11.15 stabil (paket sistem yang sudah ditunjuk `venv` —
nol lingkungan baru).

⚖️ **BATAS KEJUJURAN — mana dari keduanya yang menentukan, TIDAK bisa dibuktikan sekarang.**
Reproduksi lokal hanya jebol pada tumpukan thread **<96 KB**, sedangkan thread produksi punya **8 MB**
— jadi "tumpukan habis karena dalam" **tidak cukup menjelaskan** crash produksi, dan rc1 adalah
tersangka yang lebih kuat. Membuktikannya menuntut memasang ulang rc1 di produksi untuk memicu crash
— tindakan yang jelas tak boleh dilakukan. Karena itu **kedua sisi ditutup sekaligus**, dan keduanya
benar berdiri sendiri: penerjemah pra-rilis memang tak boleh menjalankan produksi, dan pembangunan
skema memang tak seharusnya terjadi di dalam thread. **Ukuran keberhasilan yang sesungguhnya = nol
SEGV baru** (garis dasar: 6 kejadian, 1–14 Agu).

═══ PERBAIKANNYA ═══

Bangun skema **satu kali di alur UTAMA saat mesin start**, ketika tumpukan masih kosong dan ruangnya
lapang. Sesudah itu pydantic menyimpannya, dan thread produksi memakai yang sudah jadi — pembangunan
rekursif itu **tidak pernah lagi terjadi di dalam thread**. Ini menutup SEBABNYA, bukan menambal
gejala: nol batas dinaikkan, nol rekursi dipotong, nol perilaku berubah. Yang berubah hanya **KAPAN**
pekerjaan itu dilakukan.

⚠️ **SELURUH model, bukan hanya yang teratas — ini yang nyaris saya lewatkan.** Diukur 14-Agu:
`ChatCompletion.model_rebuild()` menyiapkan induknya saja; `Choice`, `ChatCompletionMessage`, dan
`CompletionUsage` **TETAP tertunda**. Padahal SDK mengurai balasan secara bersarang dan memanggil
`_get_extra_fields_type` pada SETIAP tingkat ⇒ pembangunan skema tetap terjadi di dalam thread, dan
perbaikan "menghangatkan model teratas" tidak akan menyembuhkan apa pun.
Karena itu yang dipanaskan adalah **setiap turunan `BaseModel` milik SDK yang sudah termuat**:
terukur **747 model dalam 0,56 detik**, nol tersisa tertunda.

═══ KENAPA BERBENTUK DAFTAR AWALAN MODUL (GENERIK) ═══

Ketetapan owner 14-Agu: *"pastikan setiap perbaikan sedapat mungkin bersifat GENERIK, karena AI model
dan AI vendor akan terus bertambah."* Maka yang didaftar bukan nama kelas (yang berubah tiap versi
SDK dan mustahil dijaga lengkap), melainkan **awalan modul**. Menambah SDK baru = tambah SATU KATA di
`_AWALAN_SDK`. SDK yang tak terpasang dilewati diam-diam — bukan galat.

⚠️ **GAGAL-TERBUKA, disengaja.** Pemanasan yang gagal TIDAK PERNAH boleh menghentikan mesin: ia
pencegahan, bukan syarat produksi. Bila gagal, perilakunya kembali persis seperti sebelum berkas ini
ada — tidak lebih buruk.
"""
from __future__ import annotations

import importlib

from loguru import logger

# Awalan modul SDK yang balasannya kita urai dengan pydantic. Menambah vendor = tambah satu kata.
# `openai` mencakup seluruh keluarga OpenAI-compatible (openai · groq · gemini) karena semuanya
# memakai SDK yang sama lewat satu adaptor.
_AWALAN_SDK: tuple[str, ...] = ("openai", "anthropic")

# Modul yang WAJIB diimpor lebih dulu supaya kelas-kelasnya termuat dan bisa ditemukan.
#
# ⚠️ KENAPA `resources` IKUT — celah yang nyaris lolos (diukur 15-Agu). Memuat `openai.types` saja
# menyiapkan 747 model; lalu begitu `openai.resources.images`/`.audio` ikut dimuat, muncul **308
# model BARU** yang belum panas. Sebabnya: SDK memuat modul sumber dayanya secara MALAS, dan kode
# mesin kita mengimpor SDK **di dalam fungsi** (`from openai import OpenAI` di adapters ·
# `from openai import AsyncOpenAI` di ai_image) — yaitu **di dalam thread produksi**, persis keadaan
# yang hendak dihindari. Mengimpor `resources` di sini menarik seluruh permukaan SDK ke alur utama.
#
# Impor yang gagal dilewati diam-diam (SDK tak terpasang / nama modul berubah antar-versi).
_IMPOR_DULU: tuple[str, ...] = (
    "openai.types",
    "openai.types.chat",
    "openai.types.chat.chat_completion",
    "openai.types.chat.chat_completion_chunk",
    "openai.types.images_response",
    "openai.resources",            # ← seluruh sumber daya: chat · images · audio · dst.
    "anthropic.types",
    "anthropic.resources",
)


def _mock(model) -> bool:
    """True bila skema model ini masih TERTUNDA (belum dibangun)."""
    for atribut in ("__pydantic_core_schema__", "__pydantic_validator__"):
        if type(getattr(model, atribut, None)).__name__ in ("MockValSer", "MockCoreSchema"):
            return True
    return False


def skema_sudah_siap(model) -> bool:
    """Kebalikan `_mock` — dipakai uji untuk memeriksa PERILAKU, bukan mencari teks dalam kode.

    (Komentar sudah 4× menipu uji berbasis pencarian teks di proyek ini.)
    """
    return not _mock(model)


def _semua_turunan(kelas, hasil=None) -> set:
    hasil = hasil if hasil is not None else set()
    for anak in kelas.__subclasses__():
        if anak not in hasil:
            hasil.add(anak)
            _semua_turunan(anak, hasil)
    return hasil


def panaskan_skema_sdk() -> dict[str, int]:
    """Bangun skema SELURUH model SDK di alur UTAMA. Return ringkasan untuk dicatat.

    Aman dipanggil berkali-kali: model yang skemanya sudah jadi dilewati.
    """
    hasil = {"siap": 0, "sudah": 0, "gagal": 0, "sisa": 0}
    for modul in _IMPOR_DULU:
        try:
            importlib.import_module(modul)
        except Exception:
            pass                                    # SDK tak terpasang — bukan galat

    try:
        from pydantic import BaseModel
    except Exception as e:
        logger.warning(f"[pemanasan] pydantic tak tersedia (non-fatal): {e}")
        return hasil

    milik_sdk = [m for m in _semua_turunan(BaseModel)
                 if str(getattr(m, "__module__", "")).startswith(_AWALAN_SDK)]
    for model in milik_sdk:
        if not _mock(model):
            hasil["sudah"] += 1
            continue
        try:
            model.model_rebuild()
            hasil["siap"] += 1
        except Exception:                           # gagal-terbuka: jangan hentikan mesin
            hasil["gagal"] += 1

    hasil["sisa"] = sum(1 for m in milik_sdk if _mock(m))
    return hasil
