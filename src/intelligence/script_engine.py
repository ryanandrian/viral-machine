"""
Script Engine v0.3.2 — Fase 6C
Fixes:
  - Pattern interrupt: tidak ada contoh verbatim yang bisa di-copy
  - Retry prompt: menyertakan weak areas dari analyzer sebagai feedback
  - Threshold: dibaca dari Supabase (sekarang 82 untuk ryan_andrian)
  - CLIMAX: instruksi emosi eksplisit — cause, don't describe
  - CTA: chemistry-first, zero explicit CTA verbs
  - Retry feedback: skor per dimensi + teknik konkret per area lemah
"""

import os, json, re, time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, get_niches, system_config

# Teknik perbaikan konkret per dimensi — dikirim ke LLM saat retry.
# Harus actionable dan spesifik, bukan saran generik.
DIMENSION_RETRY_GUIDANCE = {
    "emotional_peak": (
        # Generic fallback — dipakai hanya jika niche_profile tidak tersedia.
        # Normalnya diganti oleh _build_emotional_peak_guidance(niche_profile).
        "Do NOT describe the emotion — CAUSE it. Rewrite the CLIMAX so the viewer "
        "feels the final stage of this niche's emotion arc physically. "
        "Choose the technique that serves THIS specific topic: scale contrast, reversal, "
        "or infinite implication. Test: read aloud alone. If you don't feel it — rewrite."
    ),
    "cta_strength": (
        "Delete everything. Rewrite the CTA as a thought, not a request. "
        "NEVER use: follow, subscribe, like, hit, smash, or any imperative verb. "
        "Choose one: (1) A question so specific to this topic they cannot answer it alone. "
        "(2) A statement that implies something is coming that changes what they just learned. "
        "(3) A perspective shift that makes the viewer feel they now belong to a group that "
        "sees the world differently. Following should feel like THEIR idea."
    ),
    "hook_power": (
        "Rewrite the hook so it cannot belong to any other video. Use a specific number, "
        "name, or date from THIS topic. The information gap must be so precise that the "
        "viewer's only path forward is to keep watching. "
        "Test: could this hook appear on a different channel's video? If yes — rewrite."
    ),
    "curiosity_gap": (
        "Every section must end mid-thought — with something unresolved that only the next "
        "section answers. Each answer must reveal a deeper question. Cut any sentence that "
        "summarizes, explains, or closes a loop prematurely. "
        "The viewer stopping should feel like leaving a sentence unfinished."
    ),
    "retention_arc": (
        "Cover each sentence. Ask: does the video lose anything without it? "
        "If no — cut it. Every 5 seconds must deliver something new: a fact, a reframe, "
        "or a raised stake. Cut all filler words, all transitions that don't carry new information, "
        "all sentences that repeat what was already said in different words."
    ),
    "information_density": (
        "Replace every vague claim with its specific measurement. "
        "'Very large' → the actual size. 'Long ago' → the exact year. "
        "'Many scientists' → the specific institution or person. "
        "A fact without specificity is an opinion. Specificity is what makes content shareable — "
        "viewers share facts they can quote precisely, not impressions."
    ),
}

def _build_emotional_peak_guidance(niche_profile: dict) -> str:
    """
    Bangun retry guidance emotional_peak dari niche profile Supabase.
    Config-driven — tidak hardcode per niche.
    """
    vp          = niche_profile.get("narration_persona") or niche_profile.get("voice_profile") or {}
    emotion_arc = vp.get("emotion_arc", "").strip()
    target      = niche_profile.get("target_emotion", "").strip()
    style       = vp.get("style", "").strip()

    base = "Do NOT describe the emotion — CAUSE it. Rewrite the CLIMAX to deliver "
    if emotion_arc:
        base += f"the final stage of this arc: '{emotion_arc}'. "
    if target:
        base += f"The viewer must feel: {target}. "
    if style:
        base += f"Technique guidance: {style}. "
    base += (
        "Choose what serves THIS specific topic best: scale contrast, reversal, "
        "or infinite implication. Test: read aloud alone. If you don't feel it — rewrite completely."
    )
    return base


load_dotenv()

_DEFAULT_SECTION_TIMING = {
    "hook": 3, "mystery_drop": 5, "build_up": 12,
    "pattern_interrupt": 2, "core_facts": 15,
    "curiosity_bridge": 3, "climax": 8, "cta": 3,
}

def _get_section_timing(niche: str) -> dict:
    """Load section timing dari tabel niches (Supabase). Fallback ke default jika tidak ada."""
    try:
        niches = get_niches()
        timing = (niches.get(niche) or {}).get("section_timing") or {}
        if timing and all(k in timing for k in _DEFAULT_SECTION_TIMING):
            return timing
    except Exception:
        pass
    return _DEFAULT_SECTION_TIMING.copy()


def _scale_section_timing(section_timing: dict, target_seconds: float) -> dict:
    """Skala proporsional section_timing agar total ≈ target_seconds (Duration Preset).
    Pertahankan rasio antar-section; min 1 dtk/section. Sesuai compression-mapping
    MULTI_FORMAT_STUDIO §3 (skema 8-section TETAP, durasi diskalakan ke preset;
    pengelompokan ke N visual-beat = urusan sisi visual, bukan struktur script)."""
    total = sum(section_timing.values()) or 1
    factor = target_seconds / total
    return {k: max(1, round(v * factor)) for k, v in section_timing.items()}


def _get_profile(niche: str) -> dict:
    """
    Load narration_persona dari niche registry (Supabase-driven, no hardcode).
    Jika narration_persona belum diisi admin, derive dari base fields niche.
    """
    niches     = get_niches()
    niche_data = niches.get(niche)
    if not niche_data:
        # Niche tidak dikenal — pakai niche aktif pertama sebagai fallback
        active     = {k: v for k, v in niches.items() if v.get("is_active", True)}
        niche_data = next(iter(active.values()), {})
        logger.warning(f"[ScriptEngine] Niche '{niche}' tidak ada di registry — pakai fallback")

    vp = niche_data.get("narration_persona") or niche_data.get("voice_profile") or {}

    # Jika admin belum isi narration_persona, derive dari base fields
    if not vp.get("tone"):
        style          = niche_data.get("style", "engaging and informative")
        target_emotion = niche_data.get("target_emotion", "curiosity and wonder")
        vp = {
            "tone":        f"engaging narrator with {style} delivery",
            "style":       f"builds toward {target_emotion}, specific and concrete",
            "avoid":       "generic phrases, weak openers, filler words, vague claims",
            "hook_style":  "impossible_claim or question",
            "emotion_arc": f"curiosity → interest → {target_emotion}",
        }
        logger.debug(f"[ScriptEngine] narration_persona '{niche}' derived dari base fields")

    return vp


def _build_system_prompt():
    return (
        "You are a world-class short-form video scriptwriter. "
        "Your scripts go viral because every second stops the scroll, triggers curiosity, "
        "and makes viewers feel something real. "
        "You follow structural instructions precisely while sounding completely natural and original. "
        "Every line you write is specific to the topic — never generic, never templated. "
        "You ONLY respond with valid JSON. No markdown, no explanation, no text outside the JSON."
    )


def _build_insights_block(insights: dict) -> str:
    """
    Format channel_insights menjadi blok instruksi untuk prompt ScriptEngine.
    Hanya dipanggil jika grade != insufficient_data.
    """
    lines = ["CHANNEL PERFORMANCE INSIGHTS — This channel's real data. Apply these learnings:"]

    top_hooks = insights.get("top_hooks", [])
    if top_hooks:
        lines.append("TOP PERFORMING HOOKS from this channel (highest CTR — study these patterns):")
        for i, h in enumerate(top_hooks[:3], 1):
            ctr     = h.get("avg_ctr", 0)
            pattern = h.get("hook_pattern", "")
            text    = h.get("hook", "")[:80]
            lines.append(f"  {i}. \"{text}\" | Pattern: {pattern} | CTR: {ctr:.1f}%")

    ct_perf_raw = insights.get("content_type_perf", {})
    # content_type_perf dari PerformanceAnalyzer adalah dict {ct_name: {...}}
    if isinstance(ct_perf_raw, dict):
        ct_perf = sorted(
            [{"content_type": k, **v} for k, v in ct_perf_raw.items()],
            key=lambda x: x.get("avg_view_pct", 0),
            reverse=True,
        )
    else:
        ct_perf = ct_perf_raw
    if ct_perf:
        lines.append("CONTENT TYPES ranked by audience retention:")
        for ct in ct_perf[:3]:
            lines.append(
                f"  - {ct.get('content_type','?')}: "
                f"retention {ct.get('avg_view_pct',0):.0f}% | "
                f"avg views {ct.get('avg_views',0):,.0f}"
            )

    # avoid_patterns adalah list[str] dari PerformanceAnalyzer
    avoid_patterns = insights.get("avoid_patterns", [])
    if isinstance(avoid_patterns, list) and avoid_patterns:
        lines.append("AVOID — these content types underperform on this channel:")
        for p in avoid_patterns[:3]:
            lines.append(f"  - {p}")

    return "\n".join(lines)


# ── Compression-mapping (MULTI_FORMAT §3): N beat per preset = visual_beats = jumlah scene = QC clip.
# 8s=1 (ai_video, di luar image-sequence). Image-sequence: 3..9 beat. Tiap beat = 1 seksi narasi + 1 scene.
_BEAT_WEIGHT = {"hook": 3, "mystery_drop": 5, "build_up": 12, "pattern_interrupt": 2,
                "core_facts": 15, "core_facts_2": 10, "curiosity_bridge": 3, "climax": 8, "cta": 3}
_BEATS_FOR_N = {
    3: ["hook", "core_facts", "cta"],
    4: ["hook", "build_up", "core_facts", "cta"],
    5: ["hook", "build_up", "core_facts", "climax", "cta"],
    6: ["hook", "mystery_drop", "build_up", "core_facts", "climax", "cta"],
    7: ["hook", "mystery_drop", "build_up", "core_facts", "curiosity_bridge", "climax", "cta"],
    8: ["hook", "mystery_drop", "build_up", "pattern_interrupt", "core_facts", "curiosity_bridge", "climax", "cta"],
    9: ["hook", "mystery_drop", "build_up", "pattern_interrupt", "core_facts", "core_facts_2", "curiosity_bridge", "climax", "cta"],
}
_ROLE_LABEL = {"hook": "HOOK", "mystery_drop": "MYSTERY DROP", "build_up": "BUILD-UP",
               "pattern_interrupt": "PATTERN INTERRUPT", "core_facts": "CORE FACT", "core_facts_2": "CORE FACT 2",
               "curiosity_bridge": "CURIOSITY BRIDGE", "climax": "CLIMAX", "cta": "CTA"}
_ALL_SECTIONS = ["hook", "mystery_drop", "build_up", "pattern_interrupt", "core_facts", "curiosity_bridge", "climax", "cta"]


def _active_beats(n_beats: int) -> list:
    return _BEATS_FOR_N[max(3, min(9, int(n_beats)))]


def _beats_for_preset(preset_seconds) -> list:
    """Beat aktif (SEGMENTASI) preset = SINGLE-SOURCE dari DB `duration_presets.beats`
    (konsisten dgn panel tenant/admin); fallback `_BEATS_FOR_N` bila DB kosong (pra-migrasi/legacy).
    Validasi: hanya key beat dikenal (_BEAT_WEIGHT)."""
    from src.config.format_catalog import preset_beats, preset_visual_beats
    db = preset_beats(preset_seconds)
    if db:
        known = [b for b in db if b in _BEAT_WEIGHT]
        if known:
            return known
    return _active_beats(int(preset_visual_beats(preset_seconds)))


def _distribute_words(active: list, total_words: int) -> dict:
    tot = sum(_BEAT_WEIGHT.get(b, 5) for b in active) or 1
    return {b: max(5, round(total_words * _BEAT_WEIGHT.get(b, 5) / tot)) for b in active}


# ── §10.A PAUSE-AWARE DURATION ESTIMATOR (provider-AGNOSTIK) ────────────────────────
# Durasi-ucap = waktu-BICARA + waktu-JEDA. Jeda (em-dash/elipsis/akhir-kalimat) = sumber variansi
# utama (data NYATA: P_base 1.37–2.20 → seed pace TUNGGAL salah ~½ kasus; 75s pernah meledak 105s).
# Estimator ini BERLAKU UMUM utk SEMUA TTS provider:
#   • pace dasar  = `tts_profiles.delivery_wps` per provider (DB) — beda provider mengalir dari sini
#   • speech_wps  = delivery_wps × _PAUSE_INFLATION (bicara MURNI; delivery_wps sudah meng-include jeda rata-rata)
#   • jeda dihitung dari TEKS (tanda baca) → bebas-provider & bebas-bahasa
# Seed di bawah = AWAL; F5-01 kalibrasi PER PROVIDER dari tts_delivery_samples (EL presisi via
# word_timestamps; provider tanpa word-timeframe via agregat) → pindah ke kolom DB. Tak ada angka 1-vendor.
_PAUSE_INFLATION = 1.10   # SEED universal: speech_wps = delivery_wps × ini (F5-01 kalibrasi per provider)
_PAUSE_SECONDS = {        # SEED hening/token (detik) — universal; F5-01 kalibrasi per provider → DB
    "em_dash": 0.55, "ellipsis": 0.75, "sentence": 0.35, "comma": 0.12, "linebreak": 0.45,
}

def _count_pauses(text: str) -> dict:
    """Hitung token-jeda dari TEKS (bebas-provider/bahasa). Elipsis tak dihitung ulang sbg akhir-kalimat."""
    import re
    t = text or ""
    ell = t.count("…") + t.count("...")
    t2 = t.replace("…", "  ").replace("...", "  ")
    return {
        "em_dash":   t.count("—"),
        "ellipsis":  ell,
        "sentence":  len(re.findall(r"[.!?]+", t2)),
        "comma":     t2.count(",") + t2.count(";") + t2.count(":"),
        "linebreak": t.count("\n"),
    }

def pause_seconds(text: str, model: dict | None = None) -> float:
    m = model or _PAUSE_SECONDS
    c = _count_pauses(text)
    return round(sum(c.get(k, 0) * float(m.get(k, 0)) for k in c), 3)

def estimate_spoken_seconds(text: str, speed: float, delivery_wps: float,
                            pause_model: dict | None = None) -> tuple:
    """(est_detik, jeda_detik, speech_wps) — sadar-jeda, GENERIK lintas provider."""
    swps = max(0.1, float(delivery_wps) * _PAUSE_INFLATION)
    wc = len((text or "").split())
    pause = pause_seconds(text, pause_model)
    speech = wc / (swps * max(0.1, float(speed or 1.0)))
    return round(speech + pause, 2), pause, round(swps, 3)

def solve_speed_for_duration(text: str, t_spoken: float, delivery_wps: float,
                             speed_range=(0.7, 1.2), pause_model: dict | None = None) -> tuple:
    """SOLVE pengali-kecepatan agar (bicara + jeda) = t_spoken; clamp ke rentang provider (generik).
    Returns (speed, est_detik, jeda_detik, speech_wps)."""
    swps = max(0.1, float(delivery_wps) * _PAUSE_INFLATION)
    wc = len((text or "").split())
    pause = pause_seconds(text, pause_model)
    budget = max(0.4, float(t_spoken) - pause)          # detik tersisa utk bicara setelah jeda
    lo, hi = speed_range
    need = wc / (swps * budget) if budget else hi
    speed = round(min(hi, max(lo, need)), 3)
    est = round(wc / (swps * speed) + pause, 2)
    return speed, est, pause, round(swps, 3)


def _narrative_intent(target_duration, n_beats) -> str:
    if n_beats <= 3:
        return (f"ULTRA-SHORT {target_duration}s: ONE razor-sharp idea. No setup, no padding — "
                f"hook straight into the single most striking fact, then a resonant close. Every word fights to stay.")
    if n_beats <= 5:
        return (f"SHORT {target_duration}s: a tight arc — hook, the core revelation with hard specifics, a landing. Dense, zero filler.")
    if n_beats <= 7:
        return (f"{target_duration}s: a full short-form arc — build-up, surprising facts, emotional climax. Develop but stay tight.")
    return (f"LONG {target_duration}s: the complete arc — layered mystery, multiple distinct facts, build and release with depth. Zero filler.")


def compute_beat_durations(script: dict, word_timestamps: list | None, audio_duration: float) -> list:
    """Durasi per-beat untuk image-gen + render (1 image per beat). SUMBER TUNGGAL (dipanggil SEKALI di
    pipeline) → dikonsumsi visual_assembler (bake Ken-Burns) DAN renderer (concat) = bake==display=exact
    → sinkron TTS, nol glitch. Dari word_timestamps NYATA (presisi per-beat) bila ada+andal; else proporsi
    jumlah-kata. Total dinormalisasi = audio_duration."""
    beats  = script.get("beats") or _ALL_SECTIONS
    counts = [max(1, len((script.get(b) or "").split())) for b in beats]
    total_w = sum(counts) or 1
    wt = word_timestamps or []
    durs = None
    if wt and len(wt) >= total_w * 0.6:          # cukup andal (ElevenLabs ~98%, edge ~80%)
        durs, idx = [], 0
        for c in counts:
            s_i = min(idx, len(wt) - 1)
            e_i = min(idx + c - 1, len(wt) - 1)
            d = float(wt[e_i].get("end", 0)) - float(wt[s_i].get("start", 0))
            durs.append(max(0.6, d))
            idx += c
    if not durs:                                  # fallback: proporsi jumlah-kata
        durs = [max(0.6, audio_duration * c / total_w) for c in counts]
    tot = sum(durs) or 1
    if audio_duration > 0:                         # normalisasi total = audio_duration (presisi)
        durs = [round(d * audio_duration / tot, 4) for d in durs]
    return durs


def _build_user_prompt(topic, niche, niche_visual_style=None, feedback=None, insights_block=None,
                       preset_seconds=None, format_wps=None, render_overhead_sec=0.0,
                       cta_mode="implicit", brand_name=None, brand_cta_text=None,
                       delivery_p=None, voice_name=None, tts_provider=None, base_speed=None):
    """
    Build prompt. Jika feedback ada (dari retry), sisipkan sebagai instruksi perbaikan.
    niche_visual_style: dict dari tabel niches (base_style, color_palette, atmosphere).
    preset_seconds/format_wps: Duration Preset per-channel (MULTI_FORMAT §3). None → perilaku lama.
    cta_mode/brand_name: Branded Content (§6) — 'soft_sell' izinkan SATU sebutan brand halus.
    """
    profile        = _get_profile(niche)
    niches         = get_niches()
    niche_data     = niches.get(niche) or next(
        (v for v in niches.values() if v.get("is_active", True)), {}
    )
    section_timing = _get_section_timing(niche)
    # Duration Preset (per-channel, opsional): skalakan timing ke target + WPS per-format (§3).
    # preset_seconds/format_wps None → perilaku lama (timing niche, WPS 2.4). Non-breaking.
    if preset_seconds:
        section_timing = _scale_section_timing(section_timing, preset_seconds)
    WPS             = float(format_wps) if format_wps else 2.4
    target_duration = int(preset_seconds) if preset_seconds else sum(section_timing.values())
    words           = {k: max(4, round(v * WPS)) for k, v in section_timing.items()}
    total_words     = sum(words.values())          # total kata = target_duration × WPS provider terdaftar
    _lo, _hi        = round(total_words * 0.92), round(total_words * 1.12)

    # ── Compression-mapping per-preset (MULTI_FORMAT §3): N beat = visual_beats → narasi + scene + QC.
    from src.config.format_catalog import preset_visual_beats as _pvb
    if preset_seconds:
        # Budget = (detik − overhead render) × WPS. QC mengukur VIDEO FINAL = audio + trailing_silence
        # (+ loop net), jadi target AUDIO = preset − overhead agar video JADI ≈ preset. Tanpa ini, kata
        # in-range pun bisa overshoot di preset pendek (terbukti: 15s 27 kata → 18.2s > window 17.2).
        _spoken = max(1.0, float(preset_seconds) - float(render_overhead_sec or 0))
        total_words = round(_spoken * WPS)
        _lo, _hi    = round(total_words * 0.92), round(total_words * 1.12)
        active  = _beats_for_preset(preset_seconds)  # SEGMENTASI dari DB (single-source) / fallback _BEATS_FOR_N
        n_beats = len(active)
        words   = _distribute_words(active, total_words)   # konsentrasi budget ke beat aktif (bukan sebar 8)
        n_scenes = len(active)
        inactive = [s for s in _ALL_SECTIONS if s not in active]
        _wsum = sum(words.get(b, 0) for b in active) or 1
        # Anggaran-kata ABSOLUT + MAX per-beat (bukan cuma %): plafon konkret per-beat jauh lebih dipatuhi
        # LLM daripada total agregat — akar osilasi preset pendek (LLM "mengisi" tiap beat seukuran preset
        # lebih panjang → total membengkak → speed mentok → atempo/QC-fail). `words` = _distribute_words atas
        # total_words = T_spoken × WPS(provider) → GENERIK & no-hardcode. MAX = +15% per-beat (sedikit ruang).
        _plan_lines = "\n".join(
            f"   beat {i+1} — {_ROLE_LABEL.get(b, b)}: ~{words.get(b,0)} words (HARD MAX {round(words.get(b,0)*1.15)+1}) — {round(100*words.get(b,0)/_wsum)}%"
            for i, b in enumerate(active))
        beat_plan = (
            f"\n📐 BEAT PLAN — {target_duration}s video = {len(active)} BEATS (compression-mapping, non-negotiable):\n"
            f"{_narrative_intent(target_duration, len(active))}\n"
            f"Write EXACTLY these {len(active)} beats IN ORDER. Each beat has a HARD per-beat word budget — "
            f"do NOT exceed any beat's MAX (over-writing ONE beat is the #1 cause of overruns):\n{_plan_lines}\n"
            f"⚠️ PER-BEAT BUDGETS ARE BINDING: their sum (~{sum(words.get(b,0) for b in active)} words) is your TOTAL ceiling. "
            f"Write a {target_duration}s script — NOT a longer one trimmed down.\n"
            + (f"Leave these JSON fields as EMPTY string \"\": {', '.join(inactive)}.\n" if inactive else "")
            + (f"Also output field \"core_facts_2\" (a SECOND distinct fact).\n" if "core_facts_2" in active else "")
            + f"The numbered section guide below is your CRAFT TOOLBOX — apply only the active beats' techniques.\n"
        )
        words = {s: words.get(s, 0) for s in _ALL_SECTIONS}   # panduan ber-nomor (1-8) refs semua 8; inactive→0
    else:
        active, n_scenes, beat_plan = list(words.keys()), 6, ""

    feedback_block = ""
    if feedback:
        feedback_block = f"""
QUALITY GATE FAILED — The previous attempt did not reach the threshold.
Rewrite completely from scratch. Do not rephrase — fundamentally rethink each weak dimension.
The previous attempt's structure, phrasing, and approach are now off-limits.

Dimensions that need improvement (with specific techniques to apply):
{chr(10).join(f"  • {w}" for w in feedback)}

Apply each technique above precisely. Fresh thinking only — not a revision of what came before.
"""


    insights_section = ""
    if insights_block:
        insights_section = f"\n{insights_block}\n"

    # Branded Content §6 — soft-sell: izinkan SATU sebutan brand halus di CTA (anti-hard-sell TETAP).
    soft_sell_block = ""
    if cta_mode == "soft_sell" and brand_name:
        soft_sell_block = f"""
SOFT-SELL MODE (anti-hard-sell TETAP berlaku): KHUSUS di bagian CTA, kamu BOLEH menyisipkan
SATU sebutan brand yang HALUS & natural untuk "{brand_name}" — terasa seperti pemikiran tulus,
bukan iklan. Pola contoh (jangan salin mentah, adaptasi ke topik): "… bersama {brand_name}."
DILARANG hard-sell: tanpa "beli", "diskon", "promo", "klik link sekarang", tanpa imperative jualan.
Maksimal SATU sebutan brand di seluruh script.{(' Arahan brand: ' + brand_cta_text) if brand_cta_text else ''}
"""

    # ── Length directive — DUA-SISI + sadar-preset (B2). Ganti blok satu-sisi lama yang seragam
    # ("FEWER=fail / Do NOT be terse / at least lo") — penyebab 15s OVERSHOOT (lawan sinyal ringkas)
    # & 60s UNDERSHOOT (dorongan floor kurang). Preset PENDEK: density=quality, batas-ATAS galak,
    # "bukan asal-pendek". Preset PANJANG/legacy: capai budget dgn fakta spesifik (bukan filler) +
    # batas-atas tetap ada. Terukur: 15s 30w(budget24), 60s 70w(budget97), skor <80 (lihat journal 2026-06-18).
    if preset_seconds and delivery_p:
        # §10.A DURASI-VIA-SPEED: LLM kontrol KATA + SPEED. Speed menyerap variansi hitung-kata →
        # durasi mendarat di window QC. Ganti pemaksaan word-count kaku (akar 15s-overshoot/60s-undershoot).
        _P = float(delivery_p); _bspeed = float(base_speed) if base_speed else 0.95
        _Tspoken = max(1.0, float(preset_seconds) - float(render_overhead_sec or 0))
        _Tlo, _Thi = round(_Tspoken * 0.90, 1), round(_Tspoken * 1.10, 1)
        length_block = (
            "🎙️ THIS SCRIPT WILL BE SPOKEN — you control BOTH the words and the pace.\n"
            f"VOICE: {voice_name or 'the narrator'} ({tts_provider or 'TTS'}) speaks ≈{_P} words/sec at speed 1.0.\n"
            f"Set `speed` ∈ [0.7,1.2] to match the mood of {niche_data.get('name', niche)} "
            "(somber/dramatic→~0.85, punchy/urgent→~1.05, neutral→~0.95).\n"
            f"The {len(active)} beats TOGETHER must last ≈{round(_Tspoken,1)}s (acceptable {_Tlo}–{_Thi}s), keeping proportions.\n"
            f"KEEP TOTAL WORDS ≈{round(_P*_Tspoken)} (hard range {round(0.7*_P*_Tspoken)}–{round(1.2*_P*_Tspoken)}). "
            f"The system sets the EXACT speed to land on {round(_Tspoken,1)}s — your job is to keep word count in that range (NEVER exceed {round(1.2*_P*_Tspoken)}).\n"
            f"⏱ PAUSE BUDGET — at most ~{len(active)} deliberate pauses total (≈1 per beat). Each em-dash (—) or "
            f"ellipsis (…) adds ≈0.6s of SILENCE that EATS runtime — over-using pauses is the #1 cause of overruns. "
            f"Keep pacing tight; let speed (not pauses) carry the mood.\n"
            f" 1. Pick a mood-fitting base speed (suggested for this niche: ~{_bspeed}).\n"
            f" 2. Write the {len(active)} beats naturally — STORY FIRST.\n"
            f" 3. Count words W. Spoken ≈ W ÷ ({_P} × speed).\n"
            f" 4. PREFER nudging `speed` within [0.7,1.2] to fit your actual W; rewrite length only if speed can't reach {_Tlo}–{_Thi}s.\n"
            " 5. Report word_count + est_seconds in `_duration_check`; confirm in range.\n"
            "Words serve the story; speed makes it land on time."
        )
    elif preset_seconds and len(active) <= 5:
        length_block = (
            f"🎯 LENGTH — WAJIB (video {target_duration} detik = SANGAT PENDEK):\n"
            f"Total narasi HARUS {total_words} kata — rentang KETAT {_lo}–{_hi}. "
            f"LEBIH dari {_hi} kata = audio kepanjangan = video DITOLAK. KURANG dari {_lo} = DITOLAK.\n"
            f"Di durasi sependek ini setiap kata WAJIB berbobot: padat, tajam, NOL filler, NOL pengulangan. "
            f"Ini BUKAN 'asal pendek' — justru tiap kata harus memukul & spesifik (angka/nama/fakta nyata). "
            f"JANGAN memanjang atau menjelaskan berlebih. Hitung jumlah katamu sebelum selesai — pastikan ≤ {_hi}."
        )
    else:
        length_block = (
            f"🎯 CRITICAL LENGTH REQUIREMENT — NON-NEGOTIABLE:\n"
            f"The COMPLETE narration (all sections combined) MUST total {total_words} words (range {_lo}–{_hi} words).\n"
            f"This word count makes the spoken audio last {target_duration}s — FEWER than {_lo} = audio too short = video FAILS; "
            f"MORE than {_hi} = audio too long = video FAILS.\n"
            f"Reach {total_words} words by adding SPECIFIC facts, numbers, names, concrete detail — NOT filler or repetition. "
            f"The per-section counts below add up to {total_words} — hit every one. Verify the total is between {_lo} and {_hi} before finishing."
        )

    return f"""Write a viral short-form video script.

TOPIC: {topic.get('topic', '')}
ANGLE: {topic.get('angle', topic.get('topic', ''))}
NICHE: {niche_data.get('name', niche)}
TARGET DURATION: {target_duration} seconds of spoken narration.

{length_block}

TONE: {profile['tone']}
STYLE: {profile['style']}
AVOID: {profile['avoid']}
EMOTION ARC: {profile['emotion_arc']}
HOOK FORMULA: {profile['hook_style']}
{("🎯 NICHE EMOTIONAL QUALITY BAR (aim for this from the first draft — it is how this script is scored): " + niche_data.get('emotion_scoring_criteria','')) if niche_data.get('emotion_scoring_criteria') else ""}
{insights_section}{soft_sell_block}{feedback_block}{beat_plan}
Follow the BEAT PLAN above — write ONLY the active beats (others = empty ""). The numbered guide below is craft reference per section:

1. HOOK ({section_timing['hook']}s ~{words['hook']} words)
   JOB: Stop scroll in the first second. Create an information gap that demands resolution.
   MUST: Use {profile['hook_style']}. The most counterintuitive angle of THIS specific topic.
   FORBIDDEN: "Did you know", "In this video", "Today we", any opener that could apply to any topic.
   QUALITY BAR: If this hook could belong to a different video, rewrite it.

2. MYSTERY DROP ({section_timing['mystery_drop']}s ~{words['mystery_drop']} words)
   JOB: Before answering hook, introduce a NEW layer of mystery specific to this topic.
   MUST: A detail that makes THIS topic even stranger than the hook implied.
   FORBIDDEN: Generic transitions. Every word must be about THIS specific topic.

3. BUILD UP ({section_timing['build_up']}s ~{words['build_up']} words)
   JOB: Deliver surprising fact 1 with context. Make the viewer feel the weight and scale.
   MUST: At least one specific number, name, or date anchored to this topic.
   TECHNIQUE: Human-scale analogy — translate abstract scale into something felt viscerally.

4. PATTERN INTERRUPT ({section_timing['pattern_interrupt']}s ~{words['pattern_interrupt']} words)
   JOB: Shatter the rhythm before they grow comfortable. Reframe everything said so far.
   MUST: Write something SPECIFIC to this topic that reframes the previous section unexpectedly.
   FORBIDDEN: "Wait. It gets worse." or any phrase that could appear in any video on any topic.
   QUALITY BAR: If this line could be copy-pasted into a different video, rewrite it.

5. CORE FACTS ({section_timing['core_facts']}s ~{words['core_facts']} words)
   JOB: Facts 2 and 3 — each more surprising than the last. Maximum information density.
   MUST: At least 2 distinct, specific, verifiable facts. Each sentence adds new information.
   FORBIDDEN: Repeating anything said before. Vague claims without specifics.

6. CURIOSITY BRIDGE ({section_timing['curiosity_bridge']}s ~{words['curiosity_bridge']} words)
   JOB: Create maximum anticipation for the climax. They must feel they cannot stop now.
   MUST: Point toward something not yet revealed — a specific unanswered question from THIS topic.
   FORBIDDEN: Summarizing. Generic "but it gets even more interesting" without specifics.

7. CLIMAX ({section_timing['climax']}s ~{words['climax']} words)
   JOB: The moment they feel something they cannot name but must share.
   MUST: The most unexpected, most impactful truth about this topic. Let it land in silence.
   TECHNIQUE: Write the climax first, then build everything before toward it.
   EMOTIONAL TECHNIQUE — do NOT describe the emotion. CAUSE it through one of these:
     • Scale contrast: reduce something infinite to a single human moment — or expand
       a human to cosmic/historical scale until the viewer feels the weight physically.
     • Reversal: the truth about this topic is the precise opposite of what seemed obvious.
       The setup leads one direction; the climax breaks it completely.
     • Infinite implication: one fact that permanently changes how the viewer sees
       something they encounter every day — their life, their place in the world, time itself.
   QUALITY BAR: Read the climax aloud alone. If you don't feel something — rewrite it.
   The viewer's next instinct should be to sit in silence, screenshot it, or tell someone immediately.

8. CTA ({section_timing['cta']}s ~{words['cta']} words)
   JOB: Create a chemical reaction — leave something unresolved that only this channel completes.
   PHILOSOPHY: Never ask. Never instruct. Chemistry is built through resonance, not solicitation.
   The viewer must feel that following is THEIR decision — the only logical response to what
   they just experienced. The channel sees something about the world that most people miss.
   MUST: Choose ONE — a question so specific to this topic they cannot answer it alone,
         a revelation that implies something larger is coming, or a reframe that makes
         the viewer feel they now see the world differently than they did 90 seconds ago.
   EXAMPLE PATTERNS (absorb the principle — never copy the words, adapt deeply to topic):
     - Open question: 'What does it mean that you now know this — and most people never will?'
     - Implication drop: 'The next discovery in this field makes this one look like a footnote.'
     - Identity shift: 'You just understood something that took scientists decades to accept.'
   FORBIDDEN: 'Follow', 'Subscribe', 'Like', 'Hit the bell', 'Smash the like button',
              any sentence beginning with an imperative verb directed at the viewer,
              any phrase that sounds like a creator asking for something from the audience.
   QUALITY BAR: Read it aloud as if speaking to one person you respect.
   If it sounds like a pitch — delete it and rewrite. If it sounds like a genuine thought — keep it.

WRITING RULES — every single one non-negotiable:
- Second person "you" throughout — intimacy is everything
- Maximum 15 words per sentence — punchy, direct, no run-ons
- Specific numbers always beat vague words: "13.8 billion years" not "billions of years ago"
- Every section transition must feel inevitable — not a gear shift, a deepening
- Zero filler: "basically", "literally", "you know", "kind of", "amazing", "incredible"
TTS DELIVERY RULES — write for the human ear, not the eye:
- ⏱ DURATION-CRITICAL: each em-dash (—) and ellipsis (…) becomes ≈0.6–1.0s of SILENCE when spoken — they EAT runtime. Over-using pauses is the #1 reason a video runs too long. Use them DELIBERATELY: at most ~1 per beat, only where the drama truly earns it.
- Em-dash (—) for ONE key mid-sentence pause per beat: "It survived — against all odds."
- Ellipsis (…) sparingly for suspense: "No one knew what was coming…"
- Short standalone sentences for emphasis (these read FAST — safe for runtime): "It was real. Completely real."
- ALWAYS "heard of" not "heard about": "You've never heard of this discovery."
- Sentence fragments for impact, used sparingly: "Thirteen billion years. Vanished."
- KEEP PACING TIGHT: every line moves the story forward — no dwelling, no padding. When in doubt, fewer pauses = more reliable runtime + punchier delivery.

Return ONLY valid JSON — no markdown, no preamble, no explanation:
{{
  "title": "SEO-optimized title under 60 characters — specific, not generic",
  "hook": "exact hook text",
  "mystery_drop": "exact mystery drop text",
  "build_up": "exact build up text",
  "pattern_interrupt": "exact pattern interrupt text — must be topic-specific",
  "core_facts": "exact core facts text",
  "core_facts_2": "exact SECOND distinct fact text — ONLY if CORE FACT 2 is listed in the BEAT PLAN above; otherwise an empty string",
  "curiosity_bridge": "exact curiosity bridge text",
  "climax": "exact climax text",
  "cta": "exact cta text — must sound human, not scripted",
  "full_script": "ONLY the active beats joined as one naturally flowing paragraph — no section labels, no empty gaps",
  "word_count": 140,
  "estimated_duration_seconds": {target_duration},
  "section_durations": {json.dumps(section_timing)},
  "tts_params": {{"speed": 0.95, "stability": 0.5, "style": 0.3}},
  "_duration_check": {{"word_count": 95, "est_seconds": 56.5}},
  "background_music_mood": "specific mood, instrumentation, and emotional arc — not just one word",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#shorts"]
}}

NOTE: This call writes the NARRATION ONLY. Do NOT output image prompts/visual_suggestions/thumbnail — those are generated in a separate dedicated step."""


class ScriptEngine:

    def __init__(self):
        pass

    def _get_run_config(self, tenant_config):
        try:
            from src.config.tenant_config import load_tenant_config
            return load_tenant_config(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None), getattr(tenant_config, "niche", None))
        except Exception as e:
            logger.warning(f"[ScriptEngine] RunConfig failed ({e}) — defaults")
            return None

    def _clean_json(self, raw):
        raw   = raw.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        raw = re.sub(r',\s*([}\]])', r'\1', raw)
        raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
        return raw.strip()

    def _validate_and_fix(self, script, topic, section_timing: dict | None = None, active_beats: list | None = None):
        """Validasi TAHAP-1 (narasi saja). visual_suggestions TIDAK dibuat di sini lagi —
        dipindah ke Tahap-2 terdedikasi (Opsi A) pasca hook-optimize."""
        if not isinstance(script, dict):
            return None
        # required = beat inti yg BENAR-BENAR aktif di preset ini (segmentasi DB bisa <hook+core+cta,
        # mis. 15s=hook-core tanpa cta, 8s=core saja). Intersection {hook,core,cta} ∩ active + full_script.
        _core_req = [b for b in ("hook", "core_facts", "cta") if (not active_beats or b in active_beats)]
        required = _core_req + ["full_script"]
        if any(not script.get(f) for f in required):
            logger.warning(f"[ScriptEngine] Missing required fields")
            return None
        for f in ["mystery_drop", "build_up", "pattern_interrupt", "curiosity_bridge", "climax", "core_facts_2"]:
            script.setdefault(f, "")
        # A2 (Opsi A): SETIAP beat aktif preset WAJIB punya teks — compute_beat_durations + image-gen
        # baca per-beat; beat aktif kosong → durasi & scene meleset. Kosong → tolak (retry attempt).
        if active_beats:
            empty = [b for b in active_beats if not (script.get(b) or "").strip()]
            if empty:
                logger.warning(f"[ScriptEngine] Beat aktif kosong (tolak→retry): {empty}")
                return None
        script.setdefault("section_durations", section_timing or _DEFAULT_SECTION_TIMING)
        if not script.get("full_script"):
            parts = [script.get(s, "") for s in
                     ["hook","mystery_drop","build_up","pattern_interrupt",
                      "core_facts","core_facts_2","curiosity_bridge","climax","cta"]]
            script["full_script"] = " ".join(p for p in parts if p)
        return script

    def _generate_one(self, provider, model, topic, niche, attempt,
                      niche_visual_style=None, feedback=None, insights_block=None,
                      preset_seconds=None, format_wps=None, render_overhead_sec=0.0,
                      cta_mode="implicit", brand_name=None, brand_cta_text=None,
                      delivery_p=None, voice_name=None, tts_provider=None, base_speed=None):
        """Satu attempt generate script via LLMProvider (config-driven).

        Provider memegang SDK client + format API spesifik vendor — di sini tak
        ada nama SDK/provider. Gagal LLM (LLMError) = stop attempt ini (loop akan
        retry provider yang SAMA); TIDAK ada silent fallback ke provider lain.
        """
        from src.providers.llm import LLMError

        section_timing = _get_section_timing(niche)
        active_beats = None
        if preset_seconds:   # selaras dgn prompt (validate pakai timing + beat aktif yg sama)
            section_timing = _scale_section_timing(section_timing, preset_seconds)
            from src.config.format_catalog import preset_visual_beats as _pvb
            active_beats = _beats_for_preset(preset_seconds)   # segmentasi DB (single-source) — WAJIB non-kosong (A2)
        try:
            raw = provider.complete(
                system=_build_system_prompt(),
                user=_build_user_prompt(
                    topic, niche, niche_visual_style, feedback, insights_block,
                    preset_seconds=preset_seconds, format_wps=format_wps,
                    render_overhead_sec=render_overhead_sec,
                    cta_mode=cta_mode, brand_name=brand_name, brand_cta_text=brand_cta_text,
                    delivery_p=delivery_p, voice_name=voice_name, tts_provider=tts_provider, base_speed=base_speed,
                ),
                model=model,
                temperature=1.0,
                max_tokens=2000,
                as_json=True,
            )
            script = json.loads(self._clean_json(raw))
            script = self._validate_and_fix(script, topic, section_timing, active_beats=active_beats)
            if script:
                logger.info(
                    f"[ScriptEngine] {provider.provider_name} attempt {attempt} "
                    f"OK (model={model})"
                )
            return script
        except LLMError as e:
            # Kegagalan provider tenant — JANGAN pindah ke provider lain.
            logger.warning(
                f"[ScriptEngine] {provider.provider_name} attempt {attempt} "
                f"gagal: {e}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"[ScriptEngine] attempt {attempt} parse/validate gagal: {e}"
            )
            return None

    def _load_insights(self, tenant_id: str) -> dict | None:
        """Load channel_insights terbaru. Fire-and-forget — tidak pernah crash pipeline."""
        try:
            from src.analytics.performance_analyzer import PerformanceAnalyzer
            return PerformanceAnalyzer().load_latest_insights(tenant_id)
        except Exception as e:
            logger.warning(f"[ScriptEngine] Load insights gagal (non-fatal): {e}")
            return None

    def generate_visual_prompts(self, script: dict, tenant_config) -> dict:
        """TAHAP-2 (Opsi A): LLM TERDEDIKASI membuat prompt image per-beat dari narasi FINAL.
        Dipanggil SETELAH hook-optimize (hook sudah final). Clue = teks beat + niche_visual_style +
        peran arc. 1 LLM call melihat SEMUA beat → koheren + bervariasi (through-line + varied composition).
        Set script['thumbnail_concept'] + script['visual_suggestions'] (index0 = thumbnail = scene hook).
        Sanitize tiap prompt + fallback EKSTRAKTIF (robust): tak pernah "N/A"/instruksi/kosong → tahan
        model image murah (flux/SD). visual_suggestions panjang = jumlah beat (= visual_beats preset)."""
        beats      = script.get("beats") or list(_ALL_SECTIONS)
        run_config = self._get_run_config(tenant_config)
        # VISUAL DNA niche (owner: SELURUH property niche = sumber prompting; NO-HARDCODE).
        # Inject SELURUH key visual_style apa adanya → admin tambah key (lighting/camera/composition/
        # realism/reference/color_grading/motion/…) langsung berpengaruh TANPA ubah kode. Kosong → fallback minimal.
        nvs        = (getattr(run_config, "niche_visual_style", {}) or {}) if run_config else {}
        dna_lines  = "\n".join(f"- {k.replace('_',' ')}: {v}" for k, v in nvs.items() if v) \
                     or "- style: cinematic, photorealistic, dramatic lighting"
        dna_inline = "; ".join(str(v) for v in nvs.values() if v) or "cinematic, photorealistic, dramatic lighting"
        # style_exemplars = eks-`visual_fallbacks` (di-repurpose): contoh shot terbaik niche → few-shot
        # acuan kualitas (bukan lagi padding stock-lib v1). Admin kurasi di niche.
        exemplars  = (getattr(run_config, "niche_visual_fallbacks", []) or []) if run_config else []
        exemplar_block = ("\nEXEMPLAR SHOTS (this niche's signature look — MATCH this quality bar, don't copy verbatim):\n"
                          + "\n".join(f"  • {e}" for e in exemplars[:6])) if exemplars else ""
        topic_text = script.get("topic", "") or script.get("title", "")
        niche_key  = getattr(tenant_config, "niche", "") or script.get("niche", "")
        niche_name = (get_niches().get(niche_key) or {}).get("name", niche_key)

        def _extractive(beat: str) -> str:
            txt   = (script.get(beat) or "").strip()
            first = (txt.split(".")[0].strip() if txt else topic_text) or topic_text
            return (f"{first}. {dna_inline}. Single commanding focal point, vertical 9:16, "
                    f"photorealistic, no text no words no letters no numbers no logos no watermarks.")

        def _bad(p) -> bool:
            if not p or not isinstance(p, str):
                return True
            s = p.strip().lower()
            if len(s) < 15:
                return True
            return any(m in s for m in ["n/a", "look at", "you just wrote", "[", "visual direction", "scene 1", "scene 2"])

        non_hook  = beats[1:]                 # beat[0]=hook → jadi thumbnail/hook-frame
        thumbnail = ""
        scenes    = []
        llm       = run_config.get_llm_provider()      if run_config else None
        model     = run_config.llm_model_for("utility") if run_config else ""
        if llm:
            try:
                beat_lines = "\n".join(
                    f"- BEAT {i+2} [{_ROLE_LABEL.get(b, b)}]: {(script.get(b) or '').strip()[:400]}"
                    for i, b in enumerate(non_hook)
                )
                system = (
                    "You are an elite cinematic visual director for viral short-form vertical video. "
                    "You convert each narration beat into ONE photorealistic image prompt grounded in what "
                    "the beat actually says. Output ONLY valid JSON — no markdown, no preamble."
                )
                user = f"""TOPIC: {topic_text}
NICHE: {niche_name}

VISUAL DNA — the signature cinematic identity of this niche. Apply ALL of it to EVERY image:
{dna_lines}
{exemplar_block}

Below is the FINAL narration, beat by beat. Make each image match what is actually SAID in that beat.

RULES (every prompt — non-negotiable for a VIRAL, breathtaking result):
- Build the image around the single most CONCRETE visual element named/implied in that beat's text — not the topic in general.
- BEAUTY FIRST: every frame must be gallery-grade cinematic. EXPLICITLY apply the VISUAL DNA's lighting, camera/lens, composition, color, and realism in your description. Not "good enough" — stunning, scroll-stopping, emotionally striking.
- Photorealistic, vertical 9:16, ONE commanding focal point with depth.
- Keep ONE consistent visual through-line across all scenes (a recurring subject/setting/palette that evolves), but VARY composition, scale, and camera angle so no two scenes look alike.
- Write a concrete, richly cinematic DESCRIPTION (2-3 sentences) that explicitly names the lighting + camera + mood. NEVER write instructions. NEVER output "N/A".
- ABSOLUTELY NO text, words, letters, numbers, signs, logos, or watermarks inside the image.

THUMBNAIL = the opening HOOK frame. HOOK text: "{(script.get(beats[0]) or '').strip()[:300]}"
Make it the most scroll-stopping, beautiful frame of all — one striking focal point, FULL VISUAL DNA applied, clear NEGATIVE SPACE in the upper third for a title overlay.

BEATS to illustrate (one prompt each, IN ORDER):
{beat_lines}

Return ONLY valid JSON:
{{
  "thumbnail_concept": "concrete description of the opening hook image (negative space at top)",
  "scenes": ["concrete prompt for BEAT 2", "concrete prompt for BEAT 3", "... EXACTLY {len(non_hook)} items, in order"]
}}"""
                raw  = llm.complete(system=system, user=user, model=model,
                                    temperature=0.8, max_tokens=1400, as_json=True)
                data = json.loads(self._clean_json(raw))
                thumbnail = (data.get("thumbnail_concept") or "").strip()
                scenes    = data.get("scenes") if isinstance(data.get("scenes"), list) else []
            except Exception as e:
                logger.warning(f"[ScriptEngine] Tahap-2 image-prompt gagal ({e}) → fallback ekstraktif")

        # Sanitize + pad/trim tepat len(non_hook); cacat → fallback ekstraktif per-beat
        clean_scenes = []
        for i, b in enumerate(non_hook):
            p = scenes[i] if i < len(scenes) else ""
            clean_scenes.append(_extractive(b) if _bad(p) else p.strip())
        if _bad(thumbnail):
            thumbnail = _extractive(beats[0]) if beats else _extractive("hook")

        script["thumbnail_concept"]  = thumbnail
        script["visual_suggestions"] = [thumbnail] + clean_scenes   # index0 = scene hook = thumbnail
        logger.info(
            f"[ScriptEngine] Tahap-2 prompt-image: {len(script['visual_suggestions'])} "
            f"(1 thumbnail + {len(clean_scenes)} scene) via {'LLM' if llm and scenes else 'fallback-ekstraktif'}"
        )
        return script

    def generate(self, topic, tenant_config):
        logger.info(f"[ScriptEngine] Generating: {topic.get('topic','')[:50]}...")

        run_config         = self._get_run_config(tenant_config)
        llm_provider       = run_config.effective_llm_provider() if run_config else ""
        min_score          = run_config.script_min_viral_score  if run_config else 82
        max_retry          = run_config.script_max_retry        if run_config else 3
        niche_visual_style = getattr(run_config, "niche_visual_style", {}) or {}
        # LLM via provider abstraction (config-driven, BYOK). Provider memegang
        # API key + SDK client — di sini tak ada nama SDK/provider/model.
        llm          = run_config.get_llm_provider()      if run_config else None
        script_model = run_config.llm_model_for("script") if run_config else ""
        # Duration Preset per-channel (MULTI_FORMAT §3) — dari tenant_config (konteks channel).
        # null → legacy (timing niche, WPS 2.4) = non-breaking. WPS EFEKTIF = delivery TTS provider
        # (solusi 2-kelas: ElevenLabs-class ~1.8 vs edge ~2.6) → word-budget pas per kelas.
        from src.config.format_catalog import effective_wps as _eff_wps
        preset_seconds = getattr(tenant_config, "duration_preset", None)
        # Beat-aktif preset (segmentasi DB single-source) — dipakai analyzer utk renormalisasi bobot
        # (preset pendek tak dihukum climax/cta absen). None (legacy tanpa preset) → analyzer pakai 6 dim.
        active_beats   = _beats_for_preset(preset_seconds) if preset_seconds else None
        # Word-budget pakai delivery_wps provider TERDAFTAR tenant (mis. elevenlabs 1.8 → 60s=108 kata).
        # TTS apa-adanya: premium dulu → bila kredit kurang fallback edge (produk jadi, durasi bisa
        # tak lolos QC → Opsi C: flagged + tenant putuskan). Akar akurasi durasi = LLM hit word-budget.
        _tts_provider  = getattr(run_config, "tts_provider", None) if run_config else None
        format_wps     = _eff_wps(getattr(tenant_config, "format_profile", None), _tts_provider) if preset_seconds else None
        # F5-01: pace VOICE-FIRST (no-hardcode voice) — voice_catalog.delivery_wps menimpa pace provider
        # HANYA untuk voice ini (mis. Arnold lebih cepat = DATA di baris voice, bukan if-else di kode).
        # NULL/di-luar-guard [1.0,4.0] → tetap pakai pace provider (fallback) = perilaku sekarang.
        if preset_seconds and run_config:
            _vw = getattr(run_config, "voice_delivery_wps", None)
            try:
                if _vw is not None and 1.0 <= float(_vw) <= 4.0:
                    format_wps = float(_vw)
                    logger.info(f"[ScriptEngine] F5-01 pace voice-first: {format_wps} wps "
                                f"(voice={getattr(run_config,'tts_voice',None)}) — override pace provider")
            except Exception:
                pass
        # §10.A DURASI-VIA-SPEED: P = pace DASAR (delivery_wps @speed 1.0), DITANGKAP SEBELUM B1 → dipakai
        # di speed-block LLM. base_speed = speed-mood niche (hint awal; LLM nudge ∈[0.7,1.2] dari sini).
        # Speed jadi TUAS LLM (menyerap variansi kata), bukan dibakar ke word-budget. Gate = DURASI (bukan kata).
        _base_p = float(format_wps) if format_wps else None
        _base_speed = 1.0
        if run_config:
            _vs0 = (getattr(run_config, "tts_voice_settings", {}) or {})
            try:
                _base_speed = min(1.2, max(0.7, float((_vs0.get(tenant_config.niche) or {}).get("speed", 1.0) or 1.0)))
            except Exception:
                _base_speed = 1.0
        _voice_name = (getattr(run_config, "tts_voice", None) if run_config else None) or None
        # Cacat B (B1) — BUDGET SADAR-SPEED: delivery EL diperlambat oleh voice `speed` per-niche
        # (tts_voice_settings DB). audio = kata / (delivery_wps × speed) → kata = detik × delivery_wps × speed.
        # Tanpa ini budget kebanyakan kata → audio molor → QC durasi gagal (terbukti 30s→34.9s @ speed 0.9).
        # Hanya provider ber-setting speed (elevenlabs); edge sudah benar di delivery_wps-nya. No-hardcode:
        # speed dari DB. (B2 closed-loop kalibrasi delivery_wps base dari data NYATA — menyusul.)
        if format_wps and preset_seconds and (_tts_provider or "").lower().startswith("eleven"):
            _vs    = (getattr(run_config, "tts_voice_settings", {}) or {}) if run_config else {}
            _speed = float((_vs.get(tenant_config.niche) or {}).get("speed", 1.0) or 1.0)
            if 0.5 <= _speed <= 1.5 and _speed != 1.0:
                format_wps = round(format_wps * _speed, 4)
                logger.info(f"[ScriptEngine] B1 budget speed-adjust: × speed({_speed}) → {format_wps} wps (niche={tenant_config.niche})")
        # Cacat B (#3) — BUDGET SADAR-OVERHEAD RENDER: QC mengukur VIDEO FINAL = audio + trailing_silence
        # (+ loop net = loop_dur−0.5 xfade). Target AUDIO = preset − overhead agar video JADI ≈ preset.
        # Tanpa ini kata in-range pun overshoot di preset pendek (terbukti: 15s 27 kata → video 18.2s > 17.2).
        # No-hardcode: trailing_silence + loop dari tenant_configs (sama dgn yang dipakai video_renderer).
        render_overhead_sec = 0.0
        if preset_seconds and run_config:
            _trail = float(getattr(run_config, "trailing_silence", 2.5) or 2.5)
            _loopn = (float(getattr(run_config, "loop_ending_duration", 1.5) or 1.5) - 0.5) \
                     if getattr(run_config, "loop_ending_enabled", True) else 0.0
            render_overhead_sec = max(0.0, _trail + max(0.0, _loopn))
            logger.info(f"[ScriptEngine] #3 budget overhead-aware: preset {preset_seconds}s − overhead {render_overhead_sec}s "
                        f"= audio-target {max(1.0, preset_seconds-render_overhead_sec)}s")
        # Branded Content §6 — soft-sell (opsional; implicit → tanpa brand)
        _cta_mode  = getattr(tenant_config, "cta_mode", "implicit") or "implicit"
        _brand     = getattr(tenant_config, "brand_name", None)
        _brand_cta = getattr(tenant_config, "brand_cta_text", None)

        # S1-B: load channel insights — inject ke semua attempt jika grade cukup
        insights       = self._load_insights(tenant_config.tenant_id)
        insights_block = None
        insights_grade = ""
        if insights:
            grade          = insights.get("performance_grade", "insufficient_data")
            insights_grade = grade
            if grade != "insufficient_data":
                insights_block = _build_insights_block(insights)
                logger.info(
                    f"[ScriptEngine] Insights injected | grade={grade} | "
                    f"top_hooks={len(insights.get('top_hooks', []))} | "
                    f"content_types={len(insights.get('content_type_perf', []))}"
                )

        logger.info(
            f"[ScriptEngine] provider={llm_provider} "
            f"min_score={min_score} max_retry={max_retry}"
        )

        try:
            from src.intelligence.script_analyzer import ScriptAnalyzer
            # Analyzer pakai provider LLM tenant yang sama (model task 'analyzer').
            analyzer = ScriptAnalyzer(
                provider=llm,
                model=(run_config.llm_model_for("analyzer") if run_config else ""),
            )
        except Exception as e:
            logger.warning(f"[ScriptEngine] Analyzer failed ({e}) — no gate")
            analyzer = None

        # Niche profile untuk emotional_peak scoring yang niche-aware.
        # Config-driven dari Supabase — tidak hardcode per niche.
        niches_data   = get_niches()
        niche_profile = niches_data.get(tenant_config.niche) or {}

        best_script     = None
        best_score      = 0
        best_len_ok_script = None   # #2 — best yang LULUS length-gate (panjang PAS → lolos QC durasi)
        best_len_ok_score  = 0
        actual_provider = llm_provider
        feedback        = None  # Feedback dari attempt sebelumnya
        # F2d — target word-budget (LLM-QC length gate). Aktif hanya bila preset di-set.
        word_budget = round(max(1.0, preset_seconds - render_overhead_sec) * float(format_wps)) if (preset_seconds and format_wps) else None
        _LEN_TOL    = float(os.getenv("SCRIPT_LENGTH_TOLERANCE", "0.12"))  # ketat: jaga durasi pas (was 0.25 → terlalu longgar, 82w lolos 108-budget → video pendek)

        for attempt in range(1, max_retry + 1):
            logger.info(f"[ScriptEngine] Attempt {attempt}/{max_retry} via {llm_provider}")

            script = self._generate_one(
                llm, script_model, topic, tenant_config.niche, attempt,
                niche_visual_style, feedback, insights_block,
                preset_seconds=preset_seconds, format_wps=format_wps,
                render_overhead_sec=render_overhead_sec,
                cta_mode=_cta_mode, brand_name=_brand, brand_cta_text=_brand_cta,
                delivery_p=_base_p, voice_name=_voice_name, tts_provider=_tts_provider, base_speed=_base_speed,
            )

            if not script:
                if attempt < max_retry:
                    time.sleep(2 ** attempt)
                continue

            if analyzer:
                # active_beats (segmentasi DB preset) → analyzer renormalisasi bobot atas dimensi
                # relevan; preset pendek (tanpa climax/cta) tak dihukum bagian absen.
                analysis = analyzer.analyze(script, tenant_config.niche,
                                            niche_profile=niche_profile, active_beats=active_beats)
                score    = analysis.get("viral_score", 0)
                script["viral_analysis"] = analysis

                # Siapkan feedback untuk retry berikutnya.
                # Sertakan skor aktual + teknik konkret per dimensi lemah
                # agar model tahu ANGKA yang harus dicapai dan CARA spesifiknya.
                weak_areas   = analysis.get("weak_areas", [])
                dim_scores   = analysis.get("dimension_scores", {})
                retry_note   = analysis.get("retry_suggestion", "")
                feedback = []
                for area in weak_areas:
                    area_score = dim_scores.get(area, "?")
                    # emotional_peak: gunakan guidance niche-aware dari Supabase
                    # dimensi lain: guidance universal dari DIMENSION_RETRY_GUIDANCE
                    if area == "emotional_peak" and niche_profile:
                        guidance = _build_emotional_peak_guidance(niche_profile)
                    else:
                        guidance = DIMENSION_RETRY_GUIDANCE.get(
                            area, "improve this dimension — be more specific and impactful"
                        )
                    feedback.append(
                        f"{area} scored {area_score}/100 (need {min_score}+): {guidance}"
                    )
                if retry_note:
                    feedback.append(f"Analyzer note: {retry_note}")

                logger.info(
                    f"[ScriptEngine] Score: {score}/100 "
                    f"(threshold: {min_score}) | {analysis.get('summary','')}"
                )
                if weak_areas:
                    logger.info(f"[ScriptEngine] Weak areas: {weak_areas}")
            else:
                score = 82
                script["viral_analysis"] = {}
                feedback = None

            # §3.1 JARING DETERMINISTIK TIPIS + §10.A: durasi = DITENTUKAN, bukan ditebak. Setelah LLM tulis
            # W kata, SISTEM SOLVE speed = W ÷ (P × T_spoken) lalu clamp [0.7,1.2] (param_schema EL) → est
            # mendarat di window TANPA bergantung tebakan-speed LLM (yg terbukti tak andal: 9/12). Speed =
            # tuas matematis (§10.A "speed menyerap variansi"). Hanya bila W di luar JANGKAUAN speed (kata
            # ekstrem) → retry sesuaikan KATA. Speed resolved → script.tts_params → TTS (F4-03).
            length_ok = True
            if preset_seconds and _base_p:
                # §10.A JARING SADAR-JEDA (provider-agnostik). Akar Cacat-B = jeda (em-dash/elipsis/akhir-
                # kalimat) jadi hening tak-terduga → est `kata÷(P×speed)` BUTA-JEDA meleset (75s nyata 105s).
                # Kini est = bicara + Σjeda(dari teks); SISTEM solve speed agar mendarat; clamp = rentang
                # speed PROVIDER (tts_profiles.param_schema, bukan EL-hardcode). Speed resolved → TTS (F4-03).
                from src.config.format_catalog import tts_speed_range as _tsr
                _txt = script.get("full_script") or ""
                wc   = len(_txt.split())
                _tp  = script.get("tts_params") if isinstance(script.get("tts_params"), dict) else {}
                _Tspoken   = max(1.0, float(preset_seconds) - float(render_overhead_sec or 0))
                _plo, _phi = _tsr(_tts_provider)                       # rentang speed provider (GENERIK, DB)
                _rng       = (max(_plo, 0.7), min(_phi, 1.3))          # comfort-band: jaga MUTU suara lintas provider
                _speed, _est, _pause, _swps = solve_speed_for_duration(_txt, _Tspoken, _base_p, speed_range=_rng)
                _Tlo, _Thi = _Tspoken * 0.90, _Tspoken * 1.10
                script["tts_params"] = {**_tp, "speed": _speed}        # SPEED RESOLVED (sadar-jeda) → TTS
                script["_duration_est"] = {"est_seconds": _est, "pause_seconds": _pause,   # observability
                                           "speed": _speed, "speech_wps": _swps, "words": wc}
                if not (_Tlo <= _est <= _Thi):
                    length_ok = False
                    _np  = sum(_count_pauses(_txt).values())
                    _act = (f"PERPENDEK naskah / KURANGI jeda (speed sudah {_speed})" if _est > _Thi
                            else f"PERPANJANG naskah sedikit (speed sudah {_speed})")
                    feedback = (feedback or []) + [
                        f"DURATION FAIL: {wc} kata + {_pause:.1f}s jeda ({_np} tanda-jeda) → speed {_speed} → "
                        f"est {_est:.1f}s di luar {_Tlo:.1f}–{_Thi:.1f}s (target {_Tspoken:.1f}s). {_act}. "
                        f"Tiap em-dash/elipsis ≈0.6s hening — pangkas yang berlebih; sasaran ≈{round(_swps*_Tspoken)} kata "
                        f"bila jeda minim (≈1/beat)."]
                    logger.info(f"[ScriptEngine] §10.A jeda-aware: {wc}w +{_pause:.1f}s jeda → speed {_speed} → "
                                f"est {_est:.1f}s vs {_Tlo:.1f}-{_Thi:.1f}s → retry")
                else:
                    logger.info(f"[ScriptEngine] §10.A jeda-aware: {wc}w +{_pause:.1f}s jeda (swps {_swps}) → "
                                f"speed {_speed} → est {_est:.1f}s ∈ band ✓")

            if score > best_score:
                best_score  = score
                best_script = script
            # #2 — lacak best LENGTH-COMPLIANT terpisah. Naskah salah-durasi GAGAL QC (→ ready_with_issues,
            # tak auto-publish); lebih baik kirim yang panjangnya PAS + skor tertinggi DI ANTARA yang pas.
            if length_ok and score > best_len_ok_score:
                best_len_ok_score  = score
                best_len_ok_script = script

            if score >= min_score and length_ok:
                logger.info(
                    f"[ScriptEngine] ✅ Quality gate passed: "
                    f"{score}/100 (attempt {attempt}) | length_ok={length_ok}"
                )
                break

            if attempt < max_retry:
                logger.info(
                    f"[ScriptEngine] Score {score} < {min_score} — "
                    f"retry dengan feedback: {feedback}"
                )
                time.sleep(1)

        if best_script is None:
            logger.error("[ScriptEngine] All attempts failed")
            return {}

        # #2 — FINAL: utamakan naskah length-compliant (lolos QC durasi) + skor tertinggi di antaranya;
        # bila tak ada yang pas → fallback skor-tertinggi (perilaku lama). Jaga kualitas DALAM batas panjang.
        if best_len_ok_script is not None and best_len_ok_script is not best_script:
            logger.info(f"[ScriptEngine] #2 pilih naskah length-compliant (skor {best_len_ok_score}) alih-alih "
                        f"skor-tertinggi {best_score} (salah-durasi) — agar lolos QC durasi")
            best_script = best_len_ok_script
            best_score  = best_len_ok_score

        if best_score < min_score:
            logger.warning(
                f"[ScriptEngine] Best score {best_score}/100 below "
                f"threshold {min_score} — using best available"
            )

        from src.config.format_catalog import preset_visual_beats as _pvb_g
        _beats = _beats_for_preset(preset_seconds) if preset_seconds else list(_ALL_SECTIONS)
        best_script.update({
            "topic":                   topic.get("topic", ""),
            "viral_score":             topic.get("viral_score", 0),
            "script_viral_score":      best_score,
            "tenant_id":               tenant_config.tenant_id,
            "niche":                   tenant_config.niche,
            "beats":                   _beats,   # urutan beat aktif (compression-mapping) → image-gen + render per-preset

            "generated_at":            datetime.now().isoformat(),
            "llm_provider_used":       actual_provider,
            "llm_provider_requested":  llm_provider,
            # S3-A: simpan 5 skor dimensi untuk adaptive weight computation
            "topic_scores": {
                "search_volume":       topic.get("search_volume", 0),
                "trend_momentum":      topic.get("trend_momentum", 0),
                "emotional_trigger":   topic.get("emotional_trigger", 0),
                "competition_gap":     topic.get("competition_gap", 0),
                "evergreen_potential": topic.get("evergreen_potential", 0),
            },
            # S3-B: tag grade saat produksi untuk attribution
            "insights_grade": insights_grade,
        })

        logger.info(
            f"[ScriptEngine] Done: "
            f"{len(best_script.get('full_script','').split())} words | "
            f"score={best_score}/100 | used={actual_provider}"
        )
        return best_script

    def generate_batch(self, topics, tenant_config, count=1):
        scripts = []
        for topic in topics[:count]:
            script = self.generate(topic, tenant_config)
            if script:
                scripts.append(script)
        os.makedirs("logs", exist_ok=True)
        with open(f"logs/scripts_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)
        logger.info(f"[ScriptEngine] Batch: {len(scripts)}/{count} generated")
        return scripts


if __name__ == "__main__":
    tenant     = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")
    test_topic = {
        "topic":       "The Fermi Paradox — Why the Universe is Silent",
        "angle":       "The universe is 13.8 billion years old — where is everyone?",
        "hook":        "The universe should be full of alien civilizations. So where are they?",
        "viral_score": 88,
    }
    logger.info("Testing Script Engine v0.3.1...")
    engine  = ScriptEngine()
    scripts = engine.generate_batch([test_topic], tenant, count=1)
    if scripts:
        s = scripts[0]
        print(f"\n{'='*60}")
        print(f"SCRIPT   : {s.get('title','')}")
        print(f"PROVIDER : {s.get('llm_provider_used','')} (requested: {s.get('llm_provider_requested','')}) ")
        print(f"SCORE    : {s.get('script_viral_score',0)}/100")
        print(f"WORDS    : {s.get('word_count', len(s.get('full_script','').split()))}")
        print(f"DURATION : ~{s.get('estimated_duration_seconds',51)}s")
        print(f"{'='*60}")
        for sec in ["hook","mystery_drop","build_up","pattern_interrupt",
                    "core_facts","curiosity_bridge","climax","cta"]:
            val = s.get(sec,"")
            if val:
                print(f"\n[{sec.upper().replace('_',' ')}]\n{val}")
        print(f"\n{'─'*40}")
        print("VISUAL SUGGESTIONS:")
        for i, vs in enumerate(s.get("visual_suggestions",[]),1):
            print(f"  {i}. {vs}")
        print(f"\nMUSIC MOOD: {s.get('background_music_mood','')}")
        print(f"\nTHUMBNAIL: {s.get('thumbnail_concept','')}")
        analysis = s.get("viral_analysis",{})
        if analysis.get("dimension_scores"):
            print("\nDIMENSION SCORES:")
            for k,v in analysis["dimension_scores"].items():
                bar = "█"*(v//10) + "░"*(10-v//10)
                print(f"  {k:<22} {bar} {v}/100")
    else:
        print("FAILED")
