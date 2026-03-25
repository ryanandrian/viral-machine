import os
import json
from datetime import datetime
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, NICHES, system_config

load_dotenv()

class ScriptEngine:
    """
    Menghasilkan script video lengkap dari topik terpilih.
    Struktur: Hook (3s) → Build-up (20s) → Core Facts (25s) → Climax (7s) → CTA (5s)
    Multi-tenant ready.
    """

    def __init__(self):
        self.client = OpenAI(api_key=system_config.openai_api_key)

    def _build_script_prompt(self, topic: dict, tenant_config: TenantConfig) -> str:
        niche_data = NICHES[tenant_config.niche]
        hook_templates = "\n".join([f"- {h}" for h in niche_data["hook_templates"]])

        return f"""You are a world-class short-form video scriptwriter. 
You specialize in {niche_data['name']} content that goes viral on YouTube Shorts, TikTok, and Instagram Reels.

TOPIC: {topic['topic']}
ANGLE: {topic['angle']}
SUGGESTED HOOK: {topic['hook']}
TARGET EMOTION: {niche_data['target_emotion']}
STYLE: {niche_data['style']}
VIDEO LENGTH: 58 seconds maximum
LANGUAGE: English (clear, simple, globally understood)

HOOK STYLE EXAMPLES FOR THIS NICHE:
{hook_templates}

Write a complete video script following this EXACT structure:

[HOOK - 3 seconds, 1-2 sentences]
Must stop the scroll immediately. Question, shocking statement, or impossible claim.
Never start with "In this video" or "Today we'll learn".
Use pattern interrupt — say something unexpected.

[BUILD-UP - 20 seconds, 3-4 sentences]  
Create tension and curiosity. Give just enough context to make viewer NEED to know more.
Use phrases like: "But here's what they don't tell you..." / "And this is where it gets strange..."

[CORE FACTS - 25 seconds, 4-5 sentences]
The main revelation. Specific numbers, names, comparisons that create awe.
Use human-scale comparisons: "That's like stacking 500 Eiffel Towers" not "That's 2,750 km".

[CLIMAX - 7 seconds, 1-2 sentences]
The most mind-blowing fact or twist. The moment that makes them share.
Should feel like a punchline or revelation.

[CTA - 3 seconds, 1 sentence]
Soft call to action. NOT "like and subscribe". Something like:
"Follow for more facts that will change how you see the universe."

RULES:
- Total word count: 120-150 words maximum (58 seconds at normal pace)
- No filler words: "amazing", "incredible", "literally" — show don't tell
- Every sentence must earn its place — if it doesn't add tension or information, cut it
- Use "you" to speak directly to viewer
- Short sentences. Maximum 15 words per sentence.
- End each section with tension or a question that pulls to the next section

Return ONLY valid JSON, no other text:
{{
  "title": "SEO-optimized video title (under 60 chars)",
  "hook": "exact hook text",
  "build_up": "exact build-up text",
  "core_facts": "exact core facts text", 
  "climax": "exact climax text",
  "cta": "exact CTA text",
  "full_script": "complete script as one flowing text",
  "word_count": 135,
  "estimated_duration_seconds": 54,
  "visual_suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
  "background_music_mood": "tense and mysterious",
  "hashtags": ["#space", "#universe", "#facts", "#mindblowing", "#shorts"],
  "thumbnail_concept": "description of ideal thumbnail"
}}"""

    def generate(self, topic: dict, tenant_config: TenantConfig) -> dict:
        """
        Generate script lengkap untuk satu topik.
        Returns: dict berisi semua elemen script.
        """
        logger.info(f"Generating script: {topic['topic'][:50]}...")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert viral video scriptwriter. Return only valid JSON."},
                    {"role": "user", "content": self._build_script_prompt(topic, tenant_config)}
                ],
                max_tokens=1500,
                temperature=0.85
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            script = json.loads(raw)

            script["topic"] = topic["topic"]
            script["viral_score"] = topic["viral_score"]
            script["tenant_id"] = tenant_config.tenant_id
            script["niche"] = tenant_config.niche
            script["generated_at"] = datetime.now().isoformat()

            logger.info(f"Script generated: {script.get('word_count', 0)} words, "
                       f"~{script.get('estimated_duration_seconds', 0)}s")
            return script

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            return {}

    def generate_batch(self, topics: list, tenant_config: TenantConfig, count: int = 1) -> list:
        """
        Generate scripts untuk beberapa topik sekaligus.
        count: berapa topik yang akan di-generate (default: 1 = topik terbaik saja)
        """
        scripts = []
        for topic in topics[:count]:
            script = self.generate(topic, tenant_config)
            if script:
                scripts.append(script)

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/scripts_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)

        logger.info(f"Generated {len(scripts)} scripts")
        return scripts


if __name__ == "__main__":
    from src.intelligence.trend_radar import TrendRadar
    from src.intelligence.niche_selector import NicheSelector

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    logger.info("Step 1: Scanning trends...")
    radar = TrendRadar()
    signals = radar.scan(tenant)

    logger.info("Step 2: Selecting best topic...")
    selector = NicheSelector()
    topics = selector.select(signals, tenant)

    logger.info("Step 3: Generating script for top topic...")
    engine = ScriptEngine()
    scripts = engine.generate_batch(topics, tenant, count=1)

    if scripts:
        s = scripts[0]
        print(f"\n{'='*60}")
        print(f"SCRIPT: {s.get('title', '')}")
        print(f"{'='*60}")
        print(f"\n[HOOK]\n{s.get('hook', '')}")
        print(f"\n[BUILD-UP]\n{s.get('build_up', '')}")
        print(f"\n[CORE FACTS]\n{s.get('core_facts', '')}")
        print(f"\n[CLIMAX]\n{s.get('climax', '')}")
        print(f"\n[CTA]\n{s.get('cta', '')}")
        print(f"\n{'-'*40}")
        print(f"Words     : {s.get('word_count', 0)}")
        print(f"Duration  : ~{s.get('estimated_duration_seconds', 0)}s")
        print(f"Viral Score: {s.get('viral_score', 0)}/100")
        print(f"\nVisuals   : {', '.join(s.get('visual_suggestions', []))}")
        print(f"Music     : {s.get('background_music_mood', '')}")
        print(f"Thumbnail : {s.get('thumbnail_concept', '')}")
        print(f"Hashtags  : {' '.join(s.get('hashtags', []))}")
        print(f"\nSaved to  : logs/scripts_ryan_andrian.json")
    else:
        print("Script generation failed")
