"""Hook hasil optimasi WAJIB ikut terbaca narator — dan tak boleh merusak durasi.

CACAT NYATA yang ditutup 2026-07-31, terbukti dari data produksi: pada 4 dari 4 video yang diperiksa,
hook hasil optimasi TIDAK ada di `full_script`. Yang dibacakan narator tetap hook ASLI, sementara
judul di layar memakai hook baru. Sebabnya hanya `script["hook"]` yang diganti, padahal pembuat suara
memakai `full_script`. Akibatnya optimasi hook — bagian paling menentukan retensi — selama ini hanya
menghias judul dan tak pernah sampai ke penonton.

Contoh nyata dari produksi:
  hook baru : "Apa rahasia di balik Gunung Tangkuban Perahu?"
  dibacakan : "Kamu tahu dari mana asal nama Gunung Tangkuban Perahu?"   ← hook LAMA
"""


class _TC:
    """TenantConfig tiruan seminimal mungkin — uji ini hanya menyoal penukaran teks hook,
    bukan pemanggilan LLM (yang di-monkeypatch)."""
    tenant_id = "t-uji"
    channel_id = None
    niche = "dark_history"


def _skrip():
    return {
        "hook": "Kamu tahu asal nama gunung ini?",
        "core_facts": "Pada tahun 1815 letusannya terdengar sampai Sumatra.",
        "cta": "Simak sampai habis.",
        "full_script": ("Kamu tahu asal nama gunung ini? "
                        "Pada tahun 1815 letusannya terdengar sampai Sumatra. Simak sampai habis."),
    }


def test_hook_baru_masuk_ke_naskah_yang_dibacakan(monkeypatch):
    from src.intelligence.hook_optimizer import HookOptimizer
    ho = HookOptimizer.__new__(HookOptimizer)
    monkeypatch.setattr(HookOptimizer, "_generate_hooks",
                        lambda self, s, tc, **kw: {"hooks": [{"text": "Apa rahasia gunung ini?",
                                                              "scroll_stop_power": 90}],
                                                   "winner": {"text": "Apa rahasia gunung ini?",
                                                              "scroll_stop_power": 90}})
    monkeypatch.setattr(HookOptimizer, "_select_winner",
                        lambda self, tc, hd: {"text": "Apa rahasia gunung ini?", "scroll_stop_power": 90})
    sc = ho.optimize(_skrip(), _TC())
    assert sc["hook"] == "Apa rahasia gunung ini?"
    assert "Apa rahasia gunung ini?" in sc["full_script"], \
        "hook baru TIDAK ikut terbaca narator — cacat 4-dari-4 kembali"
    assert "Kamu tahu asal nama gunung ini?" not in sc["full_script"], "hook lama masih tertinggal"
    # fakta di beat lain tak boleh hilang saat hook ditukar
    assert "1815" in sc["full_script"]


def test_hook_asli_tak_ditemukan_utuh_naskah_disusun_ULANG_dari_beat(monkeypatch):
    """Jangan biarkan naskah & hook berbeda diam-diam bila teks aslinya sudah tak utuh."""
    from src.intelligence.hook_optimizer import HookOptimizer
    ho = HookOptimizer.__new__(HookOptimizer)
    monkeypatch.setattr(HookOptimizer, "_generate_hooks",
                        lambda self, s, tc, **kw: {"hooks": [{"text": "Hook baru.", "scroll_stop_power": 90}],
                                                   "winner": {"text": "Hook baru.", "scroll_stop_power": 90}})
    monkeypatch.setattr(HookOptimizer, "_select_winner",
                        lambda self, tc, hd: {"text": "Hook baru.", "scroll_stop_power": 90})
    sk = _skrip()
    sk["full_script"] = "Naskah sudah diedit alur lain sehingga hook aslinya tak ada lagi."
    sc = ho.optimize(sk, _TC())
    # disusun ulang dari beat → hook baru ada, fakta beat lain ikut
    assert "Hook baru." in sc["full_script"] and "1815" in sc["full_script"]


def test_pagar_durasi_hook_ada_di_pipeline():
    """Hook yang lebih panjang mengubah durasi, dan gerbang durasi sudah lewat di STEP 3. Kalau hook
    baru membuat durasi keluar batas, hook ASLI dipulihkan — durasi benar lebih penting daripada hook
    lebih tajam, dan tenant tidak boleh menanggung pertukaran yang tak ia setujui."""
    import inspect

    from src.orchestrator.pipeline import Pipeline
    src = inspect.getsource(Pipeline.run)
    assert "hook_reverted_reason" in src
    assert "original_hook" in src
