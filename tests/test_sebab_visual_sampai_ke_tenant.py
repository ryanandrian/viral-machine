"""Sebab kegagalan visual harus SAMPAI ke tenant — bukan berhenti di worker.log.

KENAPA UJI INI ADA (celah §8e, ditemukan 2026-08-04):
Jalur gambar/video adalah langkah PALING MAHAL, dan satu-satunya yang MEMBUANG sebab errornya.
Tiga penangkap di `VisualAssembler` hanya menulis ke worker.log lalu `return []`, sehingga
`production_runs.error_message` — yang DITAMPILKAN APA ADANYA ke tenant di layar detail run dan
tabel run — hanya berbunyi "Visual assembly failed — no clips downloaded".

Bukti nyata yang melatarbelakangi (worker.log 2026-07-14 19:54/19:56/19:57, 6 kejadian):

    AI Video error: fal submit HTTP 403: {"detail":"User is locked. Reason: Exhausted balance.
                                          Top up your balance at fal.ai/dashboard/billing."}
    Assembly complete: 0/6 clips
    PIPELINE FAILED | 54.6s | Error: Visual assembly failed — no clips downloaded

Penyedia sudah berkata TERANG bahwa saldo tenant habis dan menyebut halaman isi-ulangnya —
sesuatu yang tenant bisa bereskan dalam 2 menit. Tiga run terbakar (55-85 detik) tanpa tenant
pernah diberi tahu. SEMUA sampel di uji ini diambil PERSIS dari log/DB produksi; tidak ada yang
disusun dari ingatan (pelajaran §11 04-Agu: temuan dari sampel karangan = mesin rantai bug tanpa ujung).

CATATAN LINGKUP: uji ini menjaga bahwa sebabnya SAMPAI (teks). Ia SENGAJA tidak menuntut
`error_class` terisi — memberi kelas memicu FAST_FAIL (rem setelah 1 kegagalan, bukan 3) yaitu
perilaku-saat-gagal = KEPUTUSAN PRODUK (CLAUDE.md §0.6), masih menunggu ketok owner (§8e).
"""
from pathlib import Path

import pytest

from src.orchestrator.pipeline import Pipeline
from src.production.visual_assembler import VisualAssembler

# ── SAMPEL PRODUKSI (verbatim) ───────────────────────────────────────────────
# worker.log 2026-07-14 19:54:36 — 6 kejadian identik
SAMPEL_FAL_403 = ('fal submit HTTP 403: {"detail":"User is locked. Reason: Exhausted balance. '
                  'Top up your balance at fal.ai/dashboard/billing."}')
# worker.log 2026-07-29 11:32:40 — jalur GAMBAR (OpenAI), batas tagihan akun tercapai
SAMPEL_BILLING_400 = ("Error code: 400 - {'error': {'message': 'Billing hard limit has been reached.', "
                      "'type': 'billing_limit_user_error', 'code': 'billing_hard_limit_reached'}}")


def _pipeline_dgn_sebab(sebab):
    """Pipeline tanpa __init__ (pola uji gerbang durasi) + assembler yang sudah mencatat sebab."""
    p = Pipeline.__new__(Pipeline)
    va = VisualAssembler()
    va.last_error = sebab
    p.visual_assembler = va
    return p


# ── 1. Pesan yang DILIHAT TENANT memuat sebab yang bisa ia kerjakan ──────────

def test_sebab_penyedia_ikut_dalam_pesan_yang_dilihat_tenant():
    pesan = _pipeline_dgn_sebab(SAMPEL_FAL_403)._pesan_gagal_visual()
    # Tenant harus bisa tahu APA dan HARUS APA — dua-duanya ada di jawaban penyedia.
    assert "Exhausted balance" in pesan, pesan
    assert "billing" in pesan, pesan
    # Kalimat dasar tetap ada (jangan hilangkan konteks langkah yang gagal).
    assert "no clips downloaded" in pesan, pesan


def test_sebab_jalur_gambar_batas_tagihan_juga_terbawa():
    pesan = _pipeline_dgn_sebab(SAMPEL_BILLING_400)._pesan_gagal_visual()
    assert "Billing hard limit" in pesan, pesan
    assert "billing_hard_limit_reached" in pesan, pesan


# ── 2. Tanpa sebab: JANGAN mengarang, jangan meninggalkan tanda pisah gantung ─

@pytest.mark.parametrize("kosong", [None, "", "   "])
def test_tanpa_sebab_tidak_mengarang_dan_tidak_ada_pisah_gantung(kosong):
    pesan = _pipeline_dgn_sebab(kosong)._pesan_gagal_visual()
    assert pesan == "Visual assembly failed — no clips downloaded", repr(pesan)
    assert not pesan.rstrip().endswith("—"), repr(pesan)


def test_assembler_tanpa_atribut_pun_tidak_meledak():
    """Objek assembler pihak-lain/lama tanpa `last_error` tidak boleh membuat pipeline crash —
    kegagalan visual sudah cukup buruk tanpa ditambah AttributeError yang menutupi sebabnya."""
    p = Pipeline.__new__(Pipeline)

    class Tanpa:
        pass

    p.visual_assembler = Tanpa()
    assert p._pesan_gagal_visual() == "Visual assembly failed — no clips downloaded"


# ── 3. Penangkap BERSARANG yang sebenarnya benar-benar merekam ───────────────
# Penting: `_try_ai_video`/`_try_ai_image` menangkap LEBIH DULU daripada `_try_provider`
# (terbukti di worker.log 14-Jul yang mencetak "AI Video error", bukan "Provider error").
# Jadi merekam hanya di penangkap luar TIDAK akan menangkap kasus nyata itu.

class _TC:
    """TenantConfig seminimal yang disentuh `_try_ai_video`/`_try_ai_image` sebelum gagal."""
    tenant_id = "t-uji"
    niche = "uji"


@pytest.mark.parametrize("mode,sampel", [
    ("ai_video:kling-v2", SAMPEL_FAL_403),
    ("ai_image:flux-schnell", SAMPEL_BILLING_400),
])
def test_penangkap_bersarang_merekam_sebab_asli(monkeypatch, tmp_path, mode, sampel):
    def _meledak(*a, **k):
        raise RuntimeError(sampel)

    # Titik gagal paling awal di KEDUA jalur → penangkap milik jalur itu sendiri yang menangkap.
    monkeypatch.setattr("src.providers.visual.build_visual_provider", _meledak)

    va = VisualAssembler()
    hasil = va._try_provider(visual_mode=mode, script={"sections": []},
                             tenant_config=_TC(), clips_dir=Path(tmp_path), run_config={})

    assert hasil == [], "no-fallback: gagal harus tetap mengembalikan daftar kosong"
    assert va.last_error and sampel in va.last_error, va.last_error


def test_mode_visual_tak_dikenal_menyebut_modenya(tmp_path):
    """Cabang mode-tak-dikenal dulu diam total. Tenant yang salah setel harus tahu mana yang salah."""
    va = VisualAssembler()
    hasil = va._try_provider(visual_mode="stock:pexels", script={}, tenant_config=_TC(),
                             clips_dir=Path(tmp_path), run_config={})
    assert hasil == []
    assert "stock:pexels" in (va.last_error or ""), va.last_error


# ── 4. Sebab run LAMA tidak boleh menempel di run BARU ──────────────────────

def test_sebab_lama_dibersihkan_di_awal_perakitan(monkeypatch):
    """Sebab basi yang menempel ke run berikutnya lebih menyesatkan daripada tanpa sebab:
    tenant akan mengejar masalah yang sudah selesai. `Pipeline()` memang dibuat baru tiap run
    hari ini, tapi pagar ini yang menjaganya tetap benar bila objeknya kelak dipakai ulang."""
    va = VisualAssembler()
    va.last_error = SAMPEL_FAL_403                       # sisa run sebelumnya

    monkeypatch.setattr(VisualAssembler, "_load_run_config",
                        lambda self, tc: {"visual_mode": "ai_video:x"})
    monkeypatch.setattr(VisualAssembler, "_try_provider",
                        lambda self, **k: [Path("/tmp/klip.mp4")])   # run BARU sukses

    va.assemble({"sections": []}, _TC())
    assert va.last_error is None, f"sebab run lama menempel: {va.last_error}"


# ── 5. Pesan yang lebih panjang tidak boleh mengusutkan ALASAN REM ─────────
# `_pause_channel` menyisipkan `error_message` kegagalan terakhir ke `production_paused_reason`,
# lalu `_potong_rapi` memotongnya di 500 huruf. Memperpanjang pesan visual = menambah tekanan pada
# batas itu; kalau tembus, justru BAGIAN YANG BISA DIKERJAKAN tenant (tautan isi-ulang) yang hilang
# — memperbaiki satu hal sambil merusak hal lain. Dijaga di kasus TERBURUK, bukan kasus rata-rata.

def test_alasan_rem_tetap_utuh_termasuk_kasus_terburuk():
    from src.orchestrator.producer import _potong_rapi

    PREFIKS = ("3x produksi beruntun gagal/bermasalah → produksi channel DIHENTIKAN otomatis."
               " Penyebab terakhir: ")
    dasar = "Visual assembly failed — no clips downloaded — "

    kasus = {
        # sampel nyata worker.log 14-Jul
        "nyata": dasar + SAMPEL_FAL_403,
        # terburuk: badan respons penyedia mentok batas `r.text[:300]`, bagian actionable di UJUNG
        "terburuk": dasar + "fal submit HTTP 403: " + ("x" * 260) + " top up at fal.ai/dashboard/billing",
    }
    for nama, pesan in kasus.items():
        alasan = PREFIKS + pesan
        hasil = _potong_rapi(alasan)
        assert len(alasan) <= 500, f"[{nama}] alasan {len(alasan)} huruf sudah melewati batas 500"
        assert hasil == alasan, f"[{nama}] alasan terpotong: {hasil[-60:]!r}"
        assert "fal.ai/dashboard/billing" in hasil, f"[{nama}] bagian yang bisa dikerjakan tenant hilang"


def test_atribut_kelas_tidak_bocor_antar_instance():
    """`last_error` atribut KELAS (agar cara objek dibuat tak berubah) — pastikan penulisannya
    per-instance, bukan menimpa kelas dan bocor ke run lain di proses yang sama."""
    a, b = VisualAssembler(), VisualAssembler()
    a.last_error = SAMPEL_FAL_403
    assert b.last_error is None, "sebab bocor lintas instance lewat atribut kelas"
    assert VisualAssembler.last_error is None
