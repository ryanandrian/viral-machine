"""
Script Engine v0.3.1 — Fase 6C
Fixes:
  - Pattern interrupt: tidak ada contoh verbatim yang bisa di-copy
  - Retry prompt: menyertakan weak areas dari analyzer sebagai feedback
  - Threshold: dibaca dari Supabase (sekarang 82 untuk ryan_andrian)
"""

import os, json, re, time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, NICHES, system_config

load_dotenv()

SECTION_TIMING = {
    "hook": 3, "mystery_drop": 5, "build_up": 12,
    "pattern_interrupt": 2, "core_facts": 15,
    "curiosity_bridge": 3, "climax": 8, "cta": 3,
}
TARGET_DURATION = sum(SECTION_TIMING.values())

NICHE_VOICE_PROFILE = {
    "universe_mysteries": {
        "tone":        "authoritative yet awe-inspiring, like a world-class documentary narrator",
        "style":       "dramatic pauses, building tension, sense of cosmic wonder and scale",
        "avoid":       "casual language, humor, sarcasm, weak openers, generic phrases",
        "hook_style":  "impossible_claim or number_shock about space/universe",
        "emotion_arc": "curiosity → shock → wonder → awe",
    },
    "dark_history": {
        "tone":        "serious and grave, like a true crime narrator uncovering hidden truth",
        "style":       "slow reveals, uncomfortable truths, moral weight, eerie calmness",
        "avoid":       "humor, lighthearted tone, casual slang",
        "hook_style":  "story_open or you_dont_know about a dark historical event",
        "emotion_arc": "intrigue → discomfort → shock → sobering realization",
    },
    "ocean_mysteries": {
        "tone":        "mysterious and calm yet deeply unsettling",
        "style":       "vast scale descriptions, eerie biological details, scientific credibility",
        "avoid":       "sensationalist claims, unscientific assertions",
        "hook_style":  "impossible_claim or question about ocean depths or creatures",
        "emotion_arc": "curiosity → unease → fascination → profound wonder",
    },
    "fun_facts": {
        "tone":        "enthusiastic and curious, like an excited friend sharing a discovery",
        "style":       "rapid fire delivery, surprising connections, relatable everyday analogies",
        "avoid":       "overly serious tone, academic jargon, slow pacing",
        "hook_style":  "number_shock or question about surprising everyday facts",
        "emotion_arc": "surprise → delight → disbelief → urge to share immediately",
    },
}


def _get_profile(niche):
    return NICHE_VOICE_PROFILE.get(niche, NICHE_VOICE_PROFILE["universe_mysteries"])


def _build_system_prompt():
    return (
        "You are a world-class short-form video scriptwriter. "
        "Your scripts go viral because every second stops the scroll, triggers curiosity, "
        "and makes viewers feel something real. "
        "You follow structural instructions precisely while sounding completely natural and original. "
        "Every line you write is specific to the topic — never generic, never templated. "
        "You ONLY respond with valid JSON. No markdown, no explanation, no text outside the JSON."
    )


def _build_user_prompt(topic, niche, niche_visual_style=None, feedback=None):
    """
    Build prompt. Jika feedback ada (dari retry), sisipkan sebagai instruksi perbaikan.
    niche_visual_style: dict dari tabel niches (base_style, color_palette, atmosphere).
    """
    profile    = _get_profile(niche)
    niche_data = NICHES.get(niche, NICHES["universe_mysteries"])
    WPS        = 2.4
    words      = {k: max(4, round(v * WPS)) for k, v in SECTION_TIMING.items()}

    feedback_block = ""
    if feedback:
        feedback_block = f"""
CRITICAL — PREVIOUS ATTEMPT FAILED QUALITY GATE.
Fix these specific weaknesses in this attempt:
{chr(10).join(f"  - {w}" for w in feedback)}
Do not repeat the previous output. Write fresh, with these issues resolved.
"""

    vs = niche_visual_style or {}
    visual_direction_block = ""
    if vs:
        visual_direction_block = f"""
VISUAL DIRECTION — apply to all visual_suggestions prompts:
- Style: {vs.get("base_style", "")}
- Color palette: {vs.get("color_palette", "")}
- Atmosphere: {vs.get("atmosphere", "")}
"""

    return f"""Write a viral short-form video script.

TOPIC: {topic.get('topic', '')}
ANGLE: {topic.get('angle', topic.get('topic', ''))}
NICHE: {niche_data.get('name', niche)}
TARGET: {TARGET_DURATION} seconds total
TONE: {profile['tone']}
STYLE: {profile['style']}
AVOID: {profile['avoid']}
EMOTION ARC: {profile['emotion_arc']}
HOOK FORMULA: {profile['hook_style']}
{visual_direction_block}{feedback_block}
Write all 8 sections. Each has ONE job. Be specific to this topic — no generic phrases:

1. HOOK ({SECTION_TIMING['hook']}s ~{words['hook']} words)
   JOB: Stop scroll in the first second. Create an information gap that demands resolution.
   MUST: Use {profile['hook_style']}. The most counterintuitive angle of THIS specific topic.
   FORBIDDEN: "Did you know", "In this video", "Today we", any opener that could apply to any topic.
   QUALITY BAR: If this hook could belong to a different video, rewrite it.

2. MYSTERY DROP ({SECTION_TIMING['mystery_drop']}s ~{words['mystery_drop']} words)
   JOB: Before answering hook, introduce a NEW layer of mystery specific to this topic.
   MUST: A detail that makes THIS topic even stranger than the hook implied.
   FORBIDDEN: Generic transitions. Every word must be about THIS specific topic.

3. BUILD UP ({SECTION_TIMING['build_up']}s ~{words['build_up']} words)
   JOB: Deliver surprising fact 1 with context. Make the viewer feel the weight and scale.
   MUST: At least one specific number, name, or date anchored to this topic.
   TECHNIQUE: Human-scale analogy — translate abstract scale into something felt viscerally.

4. PATTERN INTERRUPT ({SECTION_TIMING['pattern_interrupt']}s ~{words['pattern_interrupt']} words)
   JOB: Shatter the rhythm before they grow comfortable. Reframe everything said so far.
   MUST: Write something SPECIFIC to this topic that reframes the previous section unexpectedly.
   FORBIDDEN: "Wait. It gets worse." or any phrase that could appear in any video on any topic.
   QUALITY BAR: If this line could be copy-pasted into a different video, rewrite it.

5. CORE FACTS ({SECTION_TIMING['core_facts']}s ~{words['core_facts']} words)
   JOB: Facts 2 and 3 — each more surprising than the last. Maximum information density.
   MUST: At least 2 distinct, specific, verifiable facts. Each sentence adds new information.
   FORBIDDEN: Repeating anything said before. Vague claims without specifics.

6. CURIOSITY BRIDGE ({SECTION_TIMING['curiosity_bridge']}s ~{words['curiosity_bridge']} words)
   JOB: Create maximum anticipation for the climax. They must feel they cannot stop now.
   MUST: Point toward something not yet revealed — a specific unanswered question from THIS topic.
   FORBIDDEN: Summarizing. Generic "but it gets even more interesting" without specifics.

7. CLIMAX ({SECTION_TIMING['climax']}s ~{words['climax']} words)
   JOB: The biggest reveal. Deliver fully on everything built. The moment they share this video.
   MUST: The most unexpected, most impactful truth about this topic. Let it land with weight.
   TECHNIQUE: Write the climax first, then ensure everything before builds toward it.

8. CTA ({SECTION_TIMING['cta']}s ~{words['cta']} words)
   JOB: Make them follow without asking directly. Emotional + curiosity hook to next video.
   MUST: End with ONE of these — a question they must answer, a teaser for what comes next,
         or a statement so intriguing they NEED to follow to find out more.
   EXAMPLE PATTERNS (adapt to topic, never copy verbatim):
     - 'Follow — tomorrow we reveal what [specific next mystery] means for you.'
     - 'The answer changes everything. Follow to find out what scientists discovered next.'
     - 'That question has one answer. Follow this channel — it drops tomorrow.'
   FORBIDDEN: 'Like and subscribe', 'Hit the bell', generic phrases unrelated to topic.
   QUALITY BAR: Must contain implicit or explicit reason to follow. Topic-specific always.

WRITING RULES — every single one non-negotiable:
- Second person "you" throughout — intimacy is everything
- Maximum 15 words per sentence — punchy, direct, no run-ons
- Specific numbers always beat vague words: "13.8 billion years" not "billions of years ago"
- Every section transition must feel inevitable — not a gear shift, a deepening
- Zero filler: "basically", "literally", "you know", "kind of", "amazing", "incredible"
TTS DELIVERY RULES — write for the human ear, not the eye:
- Use em-dash (—) for dramatic mid-sentence pause: "It survived — against all odds."
- Use ellipsis (...) for suspense build-up: "No one knew what was coming..."
- Short standalone sentences for emphasis: "It was real. Completely real."
- ALWAYS "heard of" not "heard about": "You've never heard of this discovery."
- Sentence fragments for dramatic impact: "Thirteen billion years. Vanished."

Return ONLY valid JSON — no markdown, no preamble, no explanation:
{{
  "title": "SEO-optimized title under 60 characters — specific, not generic",
  "hook": "exact hook text",
  "mystery_drop": "exact mystery drop text",
  "build_up": "exact build up text",
  "pattern_interrupt": "exact pattern interrupt text — must be topic-specific",
  "core_facts": "exact core facts text",
  "curiosity_bridge": "exact curiosity bridge text",
  "climax": "exact climax text",
  "cta": "exact cta text — must sound human, not scripted",
  "full_script": "all 8 sections joined as one naturally flowing paragraph, no section labels",
  "word_count": 140,
  "estimated_duration_seconds": {TARGET_DURATION},
  "section_durations": {json.dumps(SECTION_TIMING)},
  "visual_suggestions": [
    "Scene 1 — hook: [Complete cinematic image prompt. Character: dramatic, tension-filled, stops the scroll in 1 second. Lighting: high contrast, sharp shadows. Camera: extreme close-up OR extreme wide establishing shot. Subject: the exact visual moment from this hook — specific, not generic. Apply VISUAL DIRECTION style. Vertical 9:16, photorealistic, no text no words no letters no numbers no signs no logos no watermarks.]",
    "Scene 2 — mystery drop: [Complete cinematic image prompt. Character: mysterious, unsettling, raises more questions than it answers. Lighting: low-key, shadows concealing as much as revealing, ambient glow. Camera: slow-reveal composition, subject partially obscured. Subject: the specific mysterious element from this section. Apply VISUAL DIRECTION style. Vertical 9:16, photorealistic, no text no words no letters no numbers no signs no logos no watermarks.]",
    "Scene 3 — build up: [Complete cinematic image prompt. Character: epic scale, awe-inspiring, conveys the full weight and context. Lighting: dramatic natural or cosmic light, golden hour or deep space. Camera: wide establishing shot showing overwhelming scale. Subject: the specific subject from build-up section at its grandest scale. Apply VISUAL DIRECTION style. Vertical 9:16, photorealistic, no text no words no letters no numbers no signs no logos no watermarks.]",
    "Scene 4 — core facts 1: [Complete cinematic image prompt. Character: visually striking, the undeniable proof, unexpected angle. Lighting: clinical precision or dramatic chiaroscuro. Camera: tight detail shot revealing something specific and surprising. Subject: the exact visual evidence of the first core fact. Apply VISUAL DIRECTION style. Vertical 9:16, photorealistic, no text no words no letters no numbers no signs no logos no watermarks.]",
    "Scene 5 — core facts 2: [Complete cinematic image prompt. Character: tension building, something enormous approaching, point of no return. Lighting: darkening atmosphere, spotlight on the key element. Camera: medium shot with leading lines converging toward the climax. Subject: the specific visual that bridges core facts to the final reveal. Apply VISUAL DIRECTION style. Vertical 9:16, photorealistic, no text no words no letters no numbers no signs no logos no watermarks.]",
    "Scene 6 — climax: [Complete cinematic image prompt. Character: overwhelming, emotionally peak, the single most unforgettable frame of the entire video. Lighting: dramatic peak — total darkness OR blinding light, nothing in between. Camera: the most powerful composition possible — scale, symmetry, or singular focal point. Subject: the ultimate visual payoff of this story — awe, shock, revelation, or profound emotion. Apply VISUAL DIRECTION style. Vertical 9:16, photorealistic, no text no words no letters no numbers no signs no logos no watermarks.]"
  "background_music_mood": "specific mood, instrumentation, and emotional arc — not just one word",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#shorts"],
  "thumbnail_concept": "the specific image that makes someone stop scrolling and need to click"
}}"""


class ScriptEngine:

    def __init__(self):
        from openai import OpenAI
        self._openai = OpenAI(api_key=system_config.openai_api_key)

    def _get_run_config(self, tenant_config):
        try:
            from src.config.tenant_config import load_tenant_config
            return load_tenant_config(tenant_config.tenant_id)
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

    def _validate_and_fix(self, script, topic):
        if not isinstance(script, dict):
            return None
        required = ["hook", "build_up", "core_facts", "climax", "cta", "full_script"]
        if any(not script.get(f) for f in required):
            logger.warning(f"[ScriptEngine] Missing required fields")
            return None
        for f in ["mystery_drop", "pattern_interrupt", "curiosity_bridge"]:
            script.setdefault(f, "")
        vs = script.get("visual_suggestions", [])
        if not isinstance(vs, list):
            vs = []
        topic_text = topic.get("topic", "the topic")
        while len(vs) < 6:
            vs.append(
                f"Cinematic documentary photograph directly related to {topic_text}. "
                f"Single powerful focal point, dramatic natural lighting. "
                f"Vertical 9:16, photorealistic, no text no words no letters no numbers no signs."
            )
        script["visual_suggestions"] = vs[:6]
        script.setdefault("section_durations", SECTION_TIMING)
        if not script.get("full_script"):
            parts = [script.get(s, "") for s in
                     ["hook","mystery_drop","build_up","pattern_interrupt",
                      "core_facts","curiosity_bridge","climax","cta"]]
            script["full_script"] = " ".join(p for p in parts if p)
        return script

    def _call_claude(self, topic, niche, attempt, niche_visual_style=None, feedback=None):
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY tidak ada")
            client   = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                temperature=1,
                system=_build_system_prompt(),
                messages=[{"role": "user", "content": _build_user_prompt(topic, niche, niche_visual_style, feedback)}],
            )
            raw    = response.content[0].text.strip()
            script = json.loads(self._clean_json(raw))
            script = self._validate_and_fix(script, topic)
            if script:
                logger.info(f"[ScriptEngine] Claude attempt {attempt} OK")
            return script
        except Exception as e:
            logger.warning(f"[ScriptEngine] Claude attempt {attempt} failed: {e}")
            return None

    def _call_openai(self, topic, niche, attempt, niche_visual_style=None, feedback=None):
        try:
            response = self._openai.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                temperature=0.85,
                max_tokens=1800,
                messages=[
                    {"role": "system", "content": _build_system_prompt()},
                    {"role": "user",   "content": _build_user_prompt(topic, niche, niche_visual_style, feedback)},
                ],
            )
            raw    = response.choices[0].message.content.strip()
            script = json.loads(self._clean_json(raw))
            script = self._validate_and_fix(script, topic)
            if script:
                logger.info(f"[ScriptEngine] GPT-4o-mini attempt {attempt} OK")
            return script
        except Exception as e:
            logger.warning(f"[ScriptEngine] GPT attempt {attempt} failed: {e}")
            return None

    def _call_llm(self, topic, niche, attempt, llm_provider, niche_visual_style=None, feedback=None):
        if llm_provider == "claude":
            script = self._call_claude(topic, niche, attempt, niche_visual_style, feedback)
            if script is None:
                logger.warning("[ScriptEngine] Claude gagal — fallback ke GPT-4o-mini")
                script = self._call_openai(topic, niche, attempt, niche_visual_style, feedback)
                return script, "openai_fallback"
            return script, "claude"
        else:
            script = self._call_openai(topic, niche, attempt, niche_visual_style, feedback)
            return script, "openai"

    def generate(self, topic, tenant_config):
        logger.info(f"[ScriptEngine] Generating: {topic.get('topic','')[:50]}...")

        run_config         = self._get_run_config(tenant_config)
        llm_provider       = run_config.llm_provider            if run_config else "openai"
        min_score          = run_config.script_min_viral_score  if run_config else 82
        max_retry          = run_config.script_max_retry        if run_config else 3
        niche_visual_style = getattr(run_config, "niche_visual_style", {}) or {}

        logger.info(
            f"[ScriptEngine] provider={llm_provider} "
            f"min_score={min_score} max_retry={max_retry}"
        )

        try:
            from src.intelligence.script_analyzer import ScriptAnalyzer
            analyzer = ScriptAnalyzer(api_key=system_config.openai_api_key)
        except Exception as e:
            logger.warning(f"[ScriptEngine] Analyzer failed ({e}) — no gate")
            analyzer = None

        best_script     = None
        best_score      = 0
        actual_provider = llm_provider
        feedback        = None  # Feedback dari attempt sebelumnya

        for attempt in range(1, max_retry + 1):
            logger.info(f"[ScriptEngine] Attempt {attempt}/{max_retry} via {llm_provider}")

            script, actual_provider = self._call_llm(
                topic, tenant_config.niche, attempt, llm_provider, niche_visual_style, feedback
            )
            logger.info(f"[ScriptEngine] Actually used: {actual_provider}")

            if not script:
                if attempt < max_retry:
                    time.sleep(2 ** attempt)
                continue

            if analyzer:
                analysis = analyzer.analyze(script, tenant_config.niche)
                score    = analysis.get("viral_score", 0)
                script["viral_analysis"] = analysis

                # Siapkan feedback untuk retry berikutnya
                weak_areas       = analysis.get("weak_areas", [])
                retry_suggestion = analysis.get("retry_suggestion", "")
                feedback = weak_areas.copy()
                if retry_suggestion:
                    feedback.append(retry_suggestion)

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

            if score > best_score:
                best_score  = score
                best_script = script

            if score >= min_score:
                logger.info(
                    f"[ScriptEngine] ✅ Quality gate passed: "
                    f"{score}/100 (attempt {attempt})"
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

        if best_score < min_score:
            logger.warning(
                f"[ScriptEngine] Best score {best_score}/100 below "
                f"threshold {min_score} — using best available"
            )

        best_script.update({
            "topic":                   topic.get("topic", ""),
            "viral_score":             topic.get("viral_score", 0),
            "script_viral_score":      best_score,
            "tenant_id":               tenant_config.tenant_id,
            "niche":                   tenant_config.niche,
            "generated_at":            datetime.now().isoformat(),
            "llm_provider_used":       actual_provider,
            "llm_provider_requested":  llm_provider,
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
