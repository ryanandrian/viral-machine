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

Dipanggil oleh ScriptEngine — lightweight, satu GPT call per analyze.
"""

import json
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

VIRAL_DIMENSIONS = {
    "hook_power":           0.25,
    "curiosity_gap":        0.20,
    "retention_arc":        0.20,
    "emotional_peak":       0.20,
    "information_density":  0.10,
    "cta_strength":         0.05,
}

DEFAULT_EMOTION_CRITERIA = (
    "Score 80+ if the climax causes a genuine reaction — goosebumps, held breath, or the "
    "immediate need to tell someone. The emotion must be CAUSED by the content, not described. "
    "Score LOW for climaxes that explain what to feel instead of making the viewer feel it."
)


def _derive_emotion_criteria(niche_profile: dict | None) -> str:
    """
    Bangun emotional_peak scoring criteria dari niche profile Supabase.
    Config-driven — tidak ada hardcode niche. Niche baru otomatis works
    selama voice_profile diisi dengan benar di tabel niches.
    Fallback ke DEFAULT_EMOTION_CRITERIA jika data tidak tersedia.
    """
    if not niche_profile:
        return DEFAULT_EMOTION_CRITERIA

    vp          = niche_profile.get("voice_profile") or {}
    emotion_arc = vp.get("emotion_arc", "").strip()
    target      = niche_profile.get("target_emotion", "").strip()
    style       = vp.get("style", "").strip()

    if not (emotion_arc or target):
        return DEFAULT_EMOTION_CRITERIA

    parts = ["Score 80+ if the climax delivers the FINAL STAGE of this emotion arc:"]
    if emotion_arc:
        parts.append(f"'{emotion_arc}'.")
    if target:
        parts.append(f"The viewer must genuinely feel: {target}.")
    if style:
        parts.append(f"Achieve it through: {style}.")
    parts.append(
        "Do NOT describe the emotion — CAUSE it directly through the content. "
        "Score LOW if the climax tells the viewer what to feel instead of making them feel it."
    )
    return " ".join(parts)


def _build_prompt(script: dict, niche: str, niche_profile: dict | None = None) -> str:
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

    return f"""You are a strict viral content analyst. Analyze this {niche} video script.

SCRIPT:
{sections}

Score each dimension 0-100. Be honest and calibrated:
- 80-100: genuinely makes viewers stay, share, or feel something
- 60-79: decent but missing one key element
- below 60: viewers scroll away at this point

Dimensions:
- hook_power (25%): stops scroll in first second. Score 80+ only if the opening creates an information gap so specific it cannot apply to any other video. Score LOW for generic openers.
- curiosity_gap (20%): every section ends with an unanswered question. Score 80+ if viewer feels stopping is like leaving mid-sentence. Score LOW if any section summarizes instead of deepening.
- retention_arc (20%): every sentence adds new information or raises stakes. Score 80+ if no sentence could be cut without the video losing something. Score LOW for filler, repetition, or vague claims.
- emotional_peak (20%): {emotion_criteria}
- information_density (10%): specific numbers, names, dates — not vague claims. Score 80+ if every fact is verifiable and surprising. Score LOW for "very large", "long ago", "many scientists".
- cta_strength (5%): Score HIGH if it reads like one human sharing a thought — a question that demands an answer, an open loop, a perspective shift. Score HIGH for implicit engagement (curiosity that naturally leads to following). Score LOW for ANY explicit instruction: "follow", "subscribe", "like", "hit the bell", or any sentence starting with an imperative verb. The best CTA makes following feel like the viewer's own idea.

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
    Satu GPT call per script. Fallback local jika GPT gagal.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or ""
        self.model   = model

    def analyze(self, script: dict, niche: str, niche_profile: dict | None = None) -> dict:
        """
        Score script terhadap 6 dimensi viral.
        niche_profile: data niche dari Supabase (voice_profile, target_emotion, dll).
                       Dipakai untuk emotional_peak criteria yang niche-aware.
                       Jika None → fallback ke DEFAULT_EMOTION_CRITERIA.
        Returns dict dengan viral_score, weak_areas, strengths.
        Tidak pernah crash — fallback ke local estimate jika GPT gagal.
        """
        try:
            from openai import OpenAI
            client   = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict viral content analyst. "
                            "Score honestly. Only respond with valid JSON."
                        ),
                    },
                    {"role": "user", "content": _build_prompt(script, niche, niche_profile)},
                ],
            )

            raw      = response.choices[0].message.content
            analysis = json.loads(raw)

            # Hitung viral_score dari weighted dimensions jika tidak dikembalikan
            if "viral_score" not in analysis:
                dim = analysis.get("dimension_scores", {})
                analysis["viral_score"] = round(sum(
                    dim.get(k, 50) * w
                    for k, w in VIRAL_DIMENSIONS.items()
                ))

            analysis.setdefault("weak_areas", [])
            analysis.setdefault("strengths", [])
            analysis.setdefault("summary", "Analysis complete")
            analysis.setdefault("retry_suggestion", "")

            logger.info(
                f"[ScriptAnalyzer] Score: {analysis['viral_score']}/100 "
                f"| Weak: {analysis.get('weak_areas', [])}"
            )
            return analysis

        except Exception as e:
            logger.warning(f"[ScriptAnalyzer] GPT failed ({e}) — local estimate")
            return self._local_estimate(script)

    def _local_estimate(self, script: dict) -> dict:
        """Fallback estimasi lokal tanpa GPT — pipeline tidak crash."""
        hook        = script.get("hook", "")
        power_words = ["secret", "never", "impossible", "discovered", "truth",
                       "nobody", "scientists", "actually", "shocking", "reveals",
                       "hurtling", "changed", "terrifying", "hidden"]
        hook_score  = min(100, 55 + sum(8 for w in power_words if w in hook.lower()))

        sections_present = sum(
            1 for s in ["build_up", "core_facts", "climax", "cta"]
            if script.get(s)
        )
        base = round(sections_present / 4 * 65)

        dim_scores = {
            "hook_power":          hook_score,
            "curiosity_gap":       base,
            "retention_arc":       base,
            "emotional_peak":      base,
            "information_density": base,
            "cta_strength":        base,
        }
        viral_score = round(sum(
            dim_scores[k] * w for k, w in VIRAL_DIMENSIONS.items()
        ))

        return {
            "dimension_scores":  dim_scores,
            "viral_score":       viral_score,
            "summary":           "Local estimate (GPT unavailable)",
            "weak_areas":        ["GPT analysis unavailable"],
            "strengths":         [],
            "retry_suggestion":  "",
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
