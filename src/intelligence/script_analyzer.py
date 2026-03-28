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


def _build_prompt(script: dict, niche: str) -> str:
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

    return f"""You are a strict viral content analyst. Analyze this {niche} video script.

SCRIPT:
{sections}

Score each dimension 0-100. Be honest — 75+ means this genuinely makes viewers stay.
Below 60 means viewers will scroll away at that point.

Dimensions:
- hook_power (25%): stops scroll in first second, creates information gap
- curiosity_gap (20%): maintains unanswered questions throughout
- retention_arc (20%): every second gives reason not to stop watching
- emotional_peak (20%): emotion built and released at climax
- information_density (10%): real surprising facts, no filler
- cta_strength (5%): sounds like one human talking to another — emotional, not instructional. Score HIGH for natural conversation closers (a thought, a question, a feeling). Score LOW only for robotic or sales-y phrases

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
  "summary": "one sentence: main strength or weakness",
  "weak_areas": ["specific area 1", "specific area 2"],
  "strengths": ["strength 1", "strength 2"],
  "retry_suggestion": "specific improvement instruction for next attempt if score < 75"
}}"""


class ScriptAnalyzer:
    """
    Viral quality analyzer — dipanggil oleh ScriptEngine.
    Satu GPT call per script. Fallback local jika GPT gagal.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model   = model

    def analyze(self, script: dict, niche: str) -> dict:
        """
        Score script terhadap 6 dimensi viral.
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
                    {"role": "user", "content": _build_prompt(script, niche)},
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
