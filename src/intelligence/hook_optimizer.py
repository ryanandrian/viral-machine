import os
import json
from datetime import datetime
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, NICHES, system_config

load_dotenv()

class HookOptimizer:
    def __init__(self):
        self.client = OpenAI(api_key=system_config.openai_api_key)

    HOOK_FORMULAS = {
        "question": "Opens with a provocative question that viewer MUST answer",
        "impossible_claim": "States something that sounds impossible but is true",
        "you_dont_know": "Implies viewer is missing crucial information",
        "number_shock": "Leads with a specific shocking number or statistic",
        "story_open": "Opens mid-action, like a story already happening",
    }

    def _generate_hooks(self, script: dict, tenant_config: TenantConfig) -> dict:
        niche_data = NICHES[tenant_config.niche]
        formulas_text = "\n".join([f"- {k}: {v}" for k, v in self.HOOK_FORMULAS.items()])

        prompt = f"""You are an expert at writing viral hooks for short-form video.

TOPIC: {script['topic']}
CURRENT HOOK: {script['hook']}
NICHE: {niche_data['name']}
TARGET EMOTION: {niche_data['target_emotion']}

Generate 5 alternative hooks using these formulas:
{formulas_text}

Rules:
- Maximum 15 words each
- Must create immediate curiosity or shock
- No clickbait that cannot be delivered
- Use "you" to speak directly to viewer
- Never start with "In this video"

Rate each hook:
- curiosity_score: 0-100
- shock_factor: 0-100
- clarity: 0-100
- scroll_stop_power: 0-100

Return ONLY valid JSON:
{{
  "hooks": [
    {{
      "formula": "question",
      "text": "exact hook text here",
      "curiosity_score": 88,
      "shock_factor": 75,
      "clarity": 90,
      "scroll_stop_power": 85
    }}
  ],
  "winner": {{
    "formula": "impossible_claim",
    "text": "the winning hook text",
    "curiosity_score": 92,
    "shock_factor": 88,
    "clarity": 85,
    "scroll_stop_power": 90,
    "reason": "one sentence explaining why this hook wins"
  }}
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral hook specialist. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.9
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Hook generation error: {e}")
            return {}

    def optimize(self, script: dict, tenant_config: TenantConfig) -> dict:
        logger.info(f"Optimizing hooks for: {script.get('topic', '')[:50]}...")
        hook_data = self._generate_hooks(script, tenant_config)

        if not hook_data or "winner" not in hook_data:
            logger.warning("Hook optimization failed — keeping original hook")
            return script

        winner = hook_data["winner"]
        script["original_hook"] = script.get("hook", "")
        script["optimized_hook"] = winner["text"]
        script["hook"] = winner["text"]
        script["hook_data"] = {
            "winner": winner,
            "all_hooks": hook_data.get("hooks", []),
            "optimized_at": datetime.now().isoformat()
        }
        logger.info(f"Winner [{winner['scroll_stop_power']}/100]: {winner['text'][:60]}")
        return script

    def optimize_batch(self, scripts: list, tenant_config: TenantConfig) -> list:
        optimized = []
        for script in scripts:
            result = self.optimize(script, tenant_config)
            optimized.append(result)

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/optimized_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(optimized, f, ensure_ascii=False, indent=2)

        return optimized


if __name__ == "__main__":
    from src.intelligence.trend_radar import TrendRadar
    from src.intelligence.niche_selector import NicheSelector
    from src.intelligence.script_engine import ScriptEngine

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    logger.info("Step 1: Scanning trends...")
    signals = TrendRadar().scan(tenant)

    logger.info("Step 2: Selecting best topic...")
    topics = NicheSelector().select(signals, tenant)

    logger.info("Step 3: Generating script...")
    scripts = ScriptEngine().generate_batch(topics, tenant, count=1)

    logger.info("Step 4: Optimizing hooks...")
    optimizer = HookOptimizer()
    optimized = optimizer.optimize_batch(scripts, tenant)

    if optimized:
        s = optimized[0]
        hooks = s.get("hook_data", {})
        winner = hooks.get("winner", {})
        all_hooks = hooks.get("all_hooks", [])

        print(f"\n{'='*60}")
        print(f"HOOK OPTIMIZATION REPORT")
        print(f"Topic: {s.get('topic', '')}")
        print(f"{'='*60}")
        print(f"\nOriginal hook:")
        print(f"  -> {s.get('original_hook', '')}")
        print(f"\nAll 5 hook variations:")
        for i, h in enumerate(all_hooks, 1):
            score = h.get('scroll_stop_power', 0)
            curiosity = h.get('curiosity_score', 0)
            shock = h.get('shock_factor', 0)
            formula = h.get('formula', '').upper()
            text = h.get('text', '')
            print(f"\n  #{i} [{formula}] score={score}/100 curiosity={curiosity} shock={shock}")
            print(f"     {text}")
        print(f"\n{'='*40}")
        print(f"WINNER [{winner.get('scroll_stop_power', 0)}/100]:")
        print(f"  -> {winner.get('text', '')}")
        print(f"  Why: {winner.get('reason', '')}")
        print(f"\nSaved to: logs/optimized_ryan_andrian.json")
