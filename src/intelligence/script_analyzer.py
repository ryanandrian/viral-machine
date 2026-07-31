"""
Script Analyzer — Viral Quality Gate
Fase 6C s6c6 — file baru, tidak mengubah file existing.

Scoring 6 dimensi viral:
  hook_power (25%)         — seberapa kuat hook stop scroll
  curiosity_gap (20%)      — seberapa konsisten pertanyaan terjaga
  retention_arc (20%)      — setiap detik ada alasan untuk tidak berhenti
  emotional_peak (20%)     — emosi dibangun dan dilepas di climax
  information_density (10%)— nilai informasi nyata, bukan filler
  cta_strength (5%)        — natural dan efektif

Dipanggil oleh ScriptEngine — lightweight, satu LLM call per analyze.
"""

from loguru import logger

from src.providers.llm import parse_json_lenient

VIRAL_DIMENSIONS = {
    "hook_power":           0.25,
    "curiosity_gap":        0.20,
    "retention_arc":        0.20,
    "emotional_peak":       0.20,
    "information_density":  0.10,
    "cta_strength":         0.05,
}

# Dimensi yang TERIKAT pada satu beat tertentu (segmentasi). Bila beat itu tak aktif di
# preset (mis. 15s tanpa climax/cta), dimensi terkait DIBUANG dari penilaian — preset pendek
# tak boleh dihukum karena bagian yang SENGAJA tak ada. Dimensi lain (curiosity/retention/
# information_density) berlaku untuk naskah apa pun → selalu aktif.
_DIM_REQUIRES_BEAT = {
    "hook_power":     "hook",
    "emotional_peak": "climax",
    "cta_strength":   "cta",
}


def _active_dimensions(active_beats: list | None) -> dict:
    """Bobot dimensi yang RELEVAN dengan beat-aktif preset, di-renormalisasi ke 100%.
    active_beats None / kosong → semua 6 dimensi (perilaku lama, non-breaking).
    Catatan: untuk preset lengkap (hook+climax+cta hadir, mis. 45-90s) hasilnya = VIRAL_DIMENSIONS
    utuh → skor identik perilaku lama. Hanya preset tanpa climax/cta (8/15/30s) yang menciut."""
    if not active_beats:
        return dict(VIRAL_DIMENSIONS)
    return {d: w for d, w in VIRAL_DIMENSIONS.items()
            if d not in _DIM_REQUIRES_BEAT or _DIM_REQUIRES_BEAT[d] in active_beats}

DEFAULT_EMOTION_CRITERIA = (
    "Score 80+ if the climax delivers a genuine, specific emotional payoff for THIS topic — it LANDS, "
    "not merely states a feeling; 90+ if goosebumps-level. Score below 60 ONLY if it just describes/explains "
    "what to feel or is generic. A solid, well-earned climax deserves 80+ — do not withhold it at 70."
)


def _derive_emotion_criteria(niche_profile: dict | None) -> str:
    """
    Bangun emotional_peak scoring criteria dari niche profile Supabase.

    Prioritas:
    1. emotion_scoring_criteria (field khusus scoring — spesifik, dirancang sebagai
       scoring guide, diisi admin via migrate_s89)
    2. Derive dari narration_persona.emotion_arc + target_emotion + style
       (kurang spesifik tapi otomatis works untuk niche baru)
    3. DEFAULT_EMOTION_CRITERIA — generic fallback

    Config-driven: niche baru cukup diisi di Supabase, kode tidak perlu disentuh.
    """
    if not niche_profile:
        return DEFAULT_EMOTION_CRITERIA

    # Prioritas 1: field khusus scoring — paling spesifik
    explicit = (niche_profile.get("emotion_scoring_criteria") or "").strip()
    if explicit:
        return explicit

    # Prioritas 2: derive dari narration_persona (ex voice_profile — §10.B FINAL)
    vp          = niche_profile.get("narration_persona") or niche_profile.get("voice_profile") or {}
    emotion_arc = vp.get("emotion_arc", "").strip()
    target      = niche_profile.get("target_emotion", "").strip()
    style       = vp.get("style", "").strip()

    if not (emotion_arc or target):
        return DEFAULT_EMOTION_CRITERIA

    parts = ["Score the climax's emotional payoff for the FINAL STAGE of this emotion arc:"]
    if emotion_arc:
        parts.append(f"'{emotion_arc}'.")
    if target:
        parts.append(f"The viewer should genuinely feel: {target}.")
    if style:
        parts.append(f"Achieve it through: {style}.")
    parts.append(
        "Award 80+ when the climax genuinely LANDS this payoff for THIS topic (90+ if goosebumps-level); "
        "score below 60 ONLY if it merely describes/states the feeling or is generic. "
        "Do not withhold 80 from a solid, well-earned climax."
    )
    return " ".join(parts)


def _build_prompt(script: dict, niche: str, niche_profile: dict | None = None,
                  active_beats: list | None = None, content_language: str | None = None) -> str:
    sections = "\n".join([
        f"[HOOK]: {script.get('hook', '')}",
        f"[MYSTERY DROP]: {script.get('mystery_drop', '')}",
        f"[BUILD UP]: {script.get('build_up', '')}",
        f"[PATTERN INTERRUPT]: {script.get('pattern_interrupt', '')}",
        f"[CORE FACTS]: {script.get('core_facts', '')}",
        f"[CURIOSITY BRIDGE]: {script.get('curiosity_bridge', '')}",
        f"[CLIMAX]: {script.get('climax', '')}",
        f"[CTA]: {script.get('cta', '')}",
    ])

    # Untuk script 5-section lama (backward compat)
    if not script.get('mystery_drop'):
        sections = "\n".join([
            f"[HOOK]: {script.get('hook', '')}",
            f"[BUILD UP]: {script.get('build_up', '')}",
            f"[CORE FACTS]: {script.get('core_facts', '')}",
            f"[CLIMAX]: {script.get('climax', '')}",
            f"[CTA]: {script.get('cta', '')}",
        ])

    emotion_criteria = _derive_emotion_criteria(niche_profile)

    # Catatan FORMAT (preset-aware): bila preset pendek sengaja tak punya climax/cta, beri tahu
    # LLM agar TIDAK menghukum bagian yang absen (set dimensi terkait null, nilai hanya yang ada).
    beats_note = ""
    if active_beats:
        _PART_LABEL = {"hook": "hook", "core_facts": "core fact", "build_up": "build-up",
                       "mystery_drop": "mystery", "curiosity_bridge": "curiosity bridge",
                       "climax": "climax", "cta": "call-to-action"}
        present = ", ".join(_PART_LABEL.get(b, b) for b in active_beats)
        missing = []
        if "climax" not in active_beats:
            missing.append("emotional_peak (there is NO climax)")
        if "cta" not in active_beats:
            missing.append("cta_strength (there is NO call-to-action)")
        if "hook" not in active_beats:
            missing.append("hook_power (there is NO separate hook)")
        if missing:
            beats_note = (
                f"\nFORMAT NOTICE — this is a {len(active_beats)}-part ultra-short. "
                f"It INTENTIONALLY contains ONLY: {present}. "
                f"Do NOT penalize the absence of: {'; '.join(missing)}. "
                f"For those, output null and judge ONLY the parts that are present, on their own terms — "
                f"a great {present} script must be able to reach 80+.\n"
            )

    # Bahasa konten non-English → nilai DALAM bahasa naskah (standar sama; en → blok kosong = prompt lama).
    lang_note = ""
    try:
        from src.intelligence.config import is_english_locale, content_language_name
        if not is_english_locale(content_language):
            _ln = content_language_name(content_language)
            lang_note = (
                f"\nLANGUAGE NOTICE — the script is written in {_ln} ({content_language}), by design. "
                f"Judge it IN {_ln} with the exact same standards: idiomatic power, specificity, and emotional "
                f"impact FOR a native {_ln}-speaking audience. Do NOT penalize it for not being English; "
                f"DO penalize stiff 'translated-from-English' phrasing that no native speaker would say.\n"
            )
    except Exception:
        lang_note = ""

    return f"""You are a strict viral content analyst. Analyze this {niche} video script.

SCRIPT:
{sections}
{beats_note}{lang_note}
Score each dimension 0-100. Calibrate against real viral short-form — be FAIR, not perfectionist:
- 90-100: EXCEPTIONAL — best-in-class, rare. Reserve the gap above 88 for the truly outstanding.
- 80-89: STRONG & viral-ready — does its job well and SPECIFICALLY for THIS topic. **This is the target band for genuinely good content — award it freely when earned. Do NOT withhold 80 from solid work just because it isn't perfect.**
- 60-79: COMPETENT but generic or flat — the element is present yet not topic-specific, or doesn't fully land.
- below 60: WEAK — generic, vague, or would make viewers scroll away.

Dimensions (award 80+ for good execution, 90+ for exceptional; reserve <60 for genuinely weak):
- hook_power (25%): stops scroll in first second. Score 80+ if the opening creates a specific information gap tied to THIS topic (a number/name/claim it couldn't be about anything else); 90+ if irresistibly precise. Score below 60 for generic openers ("Did you know", "In this video").
- curiosity_gap (20%): sections leave loops open. Score 80+ if the viewer feels pulled to the next line; 90+ if stopping feels like leaving mid-sentence. Score below 60 only if sections summarize/close loops prematurely.
- retention_arc (20%): each sentence adds info or raises stakes. Score 80+ if it stays tight with little waste; 90+ if nothing could be cut. Score below 60 for filler, repetition, or vague claims.
- emotional_peak (20%): {emotion_criteria}
- information_density (10%): specific numbers, names, dates. Score 80+ if it carries concrete, verifiable specifics; 90+ if every fact is surprising AND precise. Score below 60 for "very large", "long ago", "many scientists".
- cta_strength (5%): Score 80+ if it reads like one human sharing a thought — a question, open loop, or perspective shift (implicit engagement that makes following feel like the viewer's own idea). Score below 50 for ANY explicit instruction ("follow", "subscribe", "like", "hit the bell", or any imperative verb at the viewer).

Return ONLY valid JSON, no markdown:
{{
  "dimension_scores": {{
    "hook_power": 0-100,
    "curiosity_gap": 0-100,
    "retention_arc": 0-100,
    "emotional_peak": 0-100,
    "information_density": 0-100,
    "cta_strength": 0-100
  }},
  "viral_score": 0-100,
  "summary": "one sentence: the single most important strength or weakness",
  "weak_areas": ["exact dimension name if score < 80"],
  "strengths": ["exact dimension name if score >= 80"],
  "retry_suggestion": "if any dimension < 80: one concrete technique the writer must apply, specific to THIS script's actual weakness — not generic advice"
}}"""


class ScriptAnalyzer:
    """
    Viral quality analyzer — dipanggil oleh ScriptEngine.
    Satu LLM call per script. Fallback local jika LLM gagal.
    """

    def __init__(self, provider=None, model: str = ""):
        """provider = LLMProvider (config-driven) dari ScriptEngine; model = task
        'analyzer'. Jika provider None / LLM gagal → fallback _local_estimate
        (quality gate tidak pernah meng-crash pipeline)."""
        self.provider = provider
        self.model    = model

    def analyze(self, script: dict, niche: str, niche_profile: dict | None = None,
                active_beats: list | None = None, content_language: str | None = None) -> dict:
        """
        Score script terhadap 6 dimensi viral via LLMProvider tenant (config-driven).
        niche_profile: data niche dari Supabase (narration_persona, target_emotion, dll).
                       Dipakai untuk emotional_peak criteria yang niche-aware.
                       Jika None → fallback ke DEFAULT_EMOTION_CRITERIA.
        content_language: bahasa KONTEN channel (locale). Non-English → analyzer diberi tahu agar
                          menilai DALAM bahasa itu (standar sama, tanpa hukuman non-English).
        Returns dict dengan viral_score, weak_areas, strengths.
        Tidak pernah crash — fallback ke local estimate jika LLM gagal/absen.
        """
        if not self.provider:
            logger.warning("[ScriptAnalyzer] tanpa LLM provider — taksiran lokal (DITANDAI)")
            return self._local_estimate(script, active_beats, sebab="tanpa provider LLM")
        try:
            raw = self.provider.complete(
                system=(
                    "You are a strict viral content analyst. "
                    "Score honestly. Only respond with valid JSON."
                ),
                user=_build_prompt(script, niche, niche_profile, active_beats,
                                   content_language=content_language),
                model=self.model,
                temperature=0.3,
                max_tokens=500,
                as_json=True,
            )
            analysis = parse_json_lenient(raw)

            # Skor preset-aware: bobot hanya atas dimensi yg RELEVAN dgn beat aktif, renormalisasi 100%.
            # Preset lengkap (45-90s: hook+climax+cta hadir) → active_dims = semua 6 → skor LLM
            # dipertahankan (perilaku lama, TAK berubah). Preset 8/15/30s (tanpa climax/cta) → recompute
            # tanpa dimensi absen → naskah pendek dinilai adil.
            active_dims = _active_dimensions(active_beats)
            if "viral_score" not in analysis or set(active_dims) != set(VIRAL_DIMENSIONS):
                dim  = analysis.get("dimension_scores", {})
                wsum = sum(active_dims.values()) or 1
                analysis["viral_score"] = round(
                    sum(dim.get(k, 50) * w for k, w in active_dims.items()) / wsum
                )

            analysis.setdefault("weak_areas", [])
            analysis.setdefault("strengths", [])
            # weak_areas hanya dimensi AKTIF → retry-feedback tak menuntut beat yg sengaja absen
            analysis["weak_areas"] = [a for a in analysis["weak_areas"]
                                      if a not in VIRAL_DIMENSIONS or a in active_dims]
            analysis.setdefault("summary", "Analysis complete")
            analysis.setdefault("retry_suggestion", "")

            logger.info(
                f"[ScriptAnalyzer] Score: {analysis['viral_score']}/100 "
                f"| Weak: {analysis.get('weak_areas', [])}"
            )
            return analysis

        except Exception as e:
            # ⚠️ JATUH KE TAKSIRAN LOKAL — kini SELALU BERTANDA (2026-07-31).
            # Cacat produksi yang ditemukan: kegagalan di sini diam-diam mengembalikan skor
            # `_local_estimate` yang terukur ±20 poin LEBIH RENDAH, tanpa penanda apa pun. Skor itu
            # dipakai gerbang mutu `script_min_viral_score` (ambang 70–80 per channel) DAN masuk data
            # mesin belajar — jadi naskah bagus bisa ditolak, dan data belajar keracunan, tanpa satu
            # pun jejak. Sekarang: `estimated=True` + `estimate_reason` ikut di hasil, dan pemanggil
            # (script_engine) TIDAK memakai skor bertanda ini untuk menjatuhkan naskah.
            logger.error(f"[ScriptAnalyzer] LLM GAGAL ({e}) — jatuh ke taksiran lokal (DITANDAI; "
                         f"skor ini TIDAK dipakai menjatuhkan naskah)")
            return self._local_estimate(script, active_beats, sebab=f"LLM gagal: {str(e)[:120]}")

    def _local_estimate(self, script: dict, active_beats: list | None = None,
                        sebab: str = "tidak diketahui") -> dict:
        """Taksiran lokal tanpa LLM — pipeline tidak crash. Preset-aware: denominator & skor hanya
        atas beat/dimensi yang AKTIF (preset pendek tak dihukum bagian absen).

        SELALU menandai dirinya (`estimated=True` + `estimate_reason`): angkanya terukur ±20 poin
        lebih rendah dari penilaian LLM, jadi memperlakukannya sebagai skor mutu yang sah = menolak
        naskah bagus dan mencemari data mesin belajar (cacat produksi, ditutup 2026-07-31)."""
        hook        = script.get("hook", "")
        power_words = ["secret", "never", "impossible", "discovered", "truth",
                       "nobody", "scientists", "actually", "shocking", "reveals",
                       "hurtling", "changed", "terrifying", "hidden"]
        hook_score  = min(100, 55 + sum(8 for w in power_words if w in hook.lower()))

        # Beat konten yang dihitung = beat aktif preset (fallback: skema 4-section lama)
        _content = [b for b in (active_beats or ["build_up", "core_facts", "climax", "cta"])
                    if b in ("build_up", "core_facts", "climax", "cta",
                             "mystery_drop", "curiosity_bridge")] or ["core_facts"]
        sections_present = sum(1 for s in _content if script.get(s))
        base = round(sections_present / len(_content) * 65)

        dim_scores = {
            "hook_power":          hook_score,
            "curiosity_gap":       base,
            "retention_arc":       base,
            "emotional_peak":      base,
            "information_density": base,
            "cta_strength":        base,
        }
        active_dims = _active_dimensions(active_beats)
        wsum        = sum(active_dims.values()) or 1
        viral_score = round(sum(dim_scores[k] * w for k, w in active_dims.items()) / wsum)

        return {
            "dimension_scores":  dim_scores,
            "viral_score":       viral_score,
            "summary":           f"Taksiran lokal (penilai LLM tak tersedia: {sebab})",
            "weak_areas":        [],          # kosong: bukan penilaian mutu, jadi jangan memicu retry palsu
            "strengths":         [],
            "retry_suggestion":  "",
            # PENANDA WAJIB — pemanggil memeriksa ini sebelum memakai skor sebagai gerbang mutu.
            "estimated":         True,
            "estimate_reason":   sebab,
        }


if __name__ == "__main__":
    # Test dengan script contoh
    test_script = {
        "hook":              "There's an asteroid hurtling toward Earth — and NASA just raised the odds.",
        "mystery_drop":      "But the asteroid isn't the scary part. It's what they found orbiting it.",
        "build_up":          "Asteroid 2024 YR4 is 60 meters wide. Large enough to flatten a city. For months, scientists gave it a 1 in 83 chance of impact in 2032. That's 150 times higher than any rock we've tracked before.",
        "pattern_interrupt": "But then the numbers changed. Not in the direction anyone expected.",
        "core_facts":        "New data from James Webb revealed the asteroid has a companion moonlet. Its gravity is subtly altering the trajectory. Updated impact probability: 1 in 32. Target zone: the Pacific Ocean.",
        "curiosity_bridge":  "And the part keeping planetary defense scientists awake isn't the asteroid itself.",
        "climax":            "It's that we've never deflected a binary asteroid system. Our best tool — DART — only works on solo rocks. We have 8 years to figure out something we've never done before.",
        "cta":               "This is why planetary defense isn't science fiction anymore. What would you do with 8 years of warning?",
        "full_script":       "",
    }

    analyzer = ScriptAnalyzer()
    result   = analyzer.analyze(test_script, "universe_mysteries")

    print("\n=== SCRIPT ANALYZER TEST ===")
    print(f"Overall Score : {result['viral_score']}/100")
    print(f"Summary       : {result['summary']}")
    print(f"Weak Areas    : {result['weak_areas']}")
    print(f"Strengths     : {result['strengths']}")
    print("\nDimension Scores:")
    for k, w in VIRAL_DIMENSIONS.items():
        score = result.get("dimension_scores", {}).get(k, 0)
        bar   = "█" * (score // 10) + "░" * (10 - score // 10)
        print(f"  {k:<22} {bar} {score:3}/100  (weight {int(w*100)}%)")
