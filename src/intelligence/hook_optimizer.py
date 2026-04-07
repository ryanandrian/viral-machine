import os
import json
import re
from datetime import datetime
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, get_niches, system_config

load_dotenv()

class HookOptimizer:
    """
    Mengoptimalkan hook video menggunakan 5 formula viral.
    Fix v0.2: retry 3x + response_format json_object.
    """

    MAX_RETRIES = 3

    HOOK_FORMULAS = {
        "question":        "Opens with a provocative question that viewer MUST answer",
        "impossible_claim":"States something that sounds impossible but is true",
        "you_dont_know":   "Implies viewer is missing crucial information",
        "number_shock":    "Leads with a specific shocking number or statistic",
        "story_open":      "Opens mid-action, like a story already happening",
    }

    def __init__(self):
        pass

    def _build_historical_block(self, top_hooks: list) -> str:
        """Format top_hooks dari channel_insights sebagai referensi historis."""
        if not top_hooks:
            return ""
        lines = [
            "HISTORICAL HIGH-CTR HOOKS from this channel (real data — these formulas worked):"
        ]
        for i, h in enumerate(top_hooks[:3], 1):
            ctr     = h.get("avg_ctr", 0)
            pattern = h.get("hook_pattern", "unknown")
            text    = h.get("hook", "")[:80]
            lines.append(f"  {i}. [{pattern}] \"{text}\" — CTR: {ctr:.1f}%")
        lines.append(
            "Use these as formula inspiration. "
            "Generate a 6th hook variant inspired by the highest-CTR pattern above. "
            "Rate it honestly — if it truly rivals the historical winners, score it high."
        )
        return "\n".join(lines)

    def _build_prompt(self, script: dict, tenant_config: TenantConfig,
                      top_hooks: list | None = None) -> str:
        niches     = get_niches()
        niche_data = niches.get(tenant_config.niche) or next(
            (v for v in niches.values() if v.get("is_active", True)), {}
        )
        formulas_text  = "\n".join([f"- {k}: {v}" for k, v in self.HOOK_FORMULAS.items()])
        historical_block = self._build_historical_block(top_hooks or [])
        hooks_count    = 6 if historical_block else 5
        historical_section = f"\n{historical_block}\n" if historical_block else ""

        return f"""You are an expert at writing viral hooks for short-form video.

TOPIC: {script['topic']}
CURRENT HOOK: {script['hook']}
NICHE: {niche_data['name']}
TARGET EMOTION: {niche_data['target_emotion']}
{historical_section}
Generate {hooks_count} alternative hooks using these formulas:
{formulas_text}{"" if not historical_block else chr(10) + "- historical_variant: Inspired by the highest-CTR hook pattern shown above"}

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

Return ONLY a valid JSON object, no other text:
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
}}

IMPORTANT: Return ONLY the JSON object. No markdown, no explanation, no extra text."""

    def _clean_json_response(self, raw: str) -> str:
        raw   = raw.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        raw = re.sub(r',\s*([}\]])', r'\1', raw)
        raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
        return raw.strip()

    def _load_insights(self, tenant_id: str) -> dict | None:
        """Load channel_insights terbaru. Fire-and-forget — tidak pernah crash pipeline."""
        try:
            from src.analytics.performance_analyzer import PerformanceAnalyzer
            return PerformanceAnalyzer().load_latest_insights(tenant_id)
        except Exception as e:
            logger.warning(f"[HookOptimizer] Load insights gagal (non-fatal): {e}")
            return None

    def _generate_hooks(self, script: dict, tenant_config: TenantConfig,
                        openai_api_key: str = "",
                        top_hooks: list | None = None) -> dict:
        if not openai_api_key:
            raise ValueError(
                f"visual_api_key (OpenAI) tidak ada di tenant_configs "
                f"untuk tenant '{tenant_config.tenant_id}'"
            )
        client     = OpenAI(api_key=openai_api_key)
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"Hook generation attempt {attempt}/{self.MAX_RETRIES}...")

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a viral hook specialist. "
                                "You MUST return only a valid JSON object. "
                                "No markdown, no explanation, no text outside the JSON."
                            )
                        },
                        {"role": "user", "content": self._build_prompt(
                            script, tenant_config, top_hooks
                        )}
                    ],
                    max_tokens=1200,
                    temperature=0.9,
                    response_format={"type": "json_object"}
                )

                raw     = response.choices[0].message.content.strip()
                cleaned = self._clean_json_response(raw)
                data    = json.loads(cleaned)

                if not isinstance(data, dict):
                    raise ValueError(f"Response bukan dict: {type(data)}")
                if "winner" not in data:
                    raise ValueError("Field 'winner' tidak ada di response")
                if "text" not in data.get("winner", {}):
                    raise ValueError("Field 'winner.text' tidak ada di response")

                logger.info(f"Hook generation success on attempt {attempt}")
                return data

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed — parse error: {e}")
                if attempt < self.MAX_RETRIES:
                    logger.info("Retrying...")
                continue

            except Exception as e:
                last_error = e
                logger.error(f"Attempt {attempt} failed — unexpected error: {e}")
                if attempt < self.MAX_RETRIES:
                    logger.info("Retrying...")
                continue

        logger.error(f"All {self.MAX_RETRIES} attempts failed. Last error: {last_error}")
        return {}

    def optimize(self, script: dict, tenant_config: TenantConfig) -> dict:
        logger.info(f"Optimizing hooks for: {script.get('topic', '')[:50]}...")
        # Load OpenAI key dari tenant DB — tidak ada env fallback
        _openai_key = ""
        try:
            from src.config.tenant_config import load_tenant_config
            _rc = load_tenant_config(tenant_config.tenant_id)
            _openai_key = (_rc.visual_api_key if _rc else "") or ""
        except Exception as _ke:
            logger.warning(f"[HookOptimizer] Gagal load tenant key: {_ke}")

        # S1-C: load channel insights → ambil top_hooks untuk formula ke-6
        top_hooks = None
        insights  = self._load_insights(tenant_config.tenant_id)
        if insights:
            grade = insights.get("performance_grade", "insufficient_data")
            if grade != "insufficient_data":
                top_hooks = insights.get("top_hooks") or None
                if top_hooks:
                    logger.info(
                        f"[HookOptimizer] Historical hooks loaded | grade={grade} | "
                        f"top_hooks={len(top_hooks)} — adding formula ke-6"
                    )

        hook_data = self._generate_hooks(
            script, tenant_config, openai_api_key=_openai_key, top_hooks=top_hooks
        )

        if not hook_data or "winner" not in hook_data:
            logger.warning("Hook optimization failed — keeping original hook")
            return script

        winner = hook_data["winner"]
        script["original_hook"]  = script.get("hook", "")
        script["optimized_hook"] = winner["text"]
        script["hook"]           = winner["text"]
        script["hook_data"]      = {
            "winner":       winner,
            "all_hooks":    hook_data.get("hooks", []),
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
    topics  = NicheSelector().select(signals, tenant)
    logger.info("Step 3: Generating script...")
    scripts = ScriptEngine().generate_batch(topics, tenant, count=1)
    logger.info("Step 4: Optimizing hooks...")
    optimized = HookOptimizer().optimize_batch(scripts, tenant)

    if optimized:
        s      = optimized[0]
        hooks  = s.get("hook_data", {})
        winner = hooks.get("winner", {})
        all_h  = hooks.get("all_hooks", [])

        print(f"\n{'='*60}")
        print(f"HOOK OPTIMIZATION REPORT")
        print(f"Topic: {s.get('topic', '')}")
        print(f"{'='*60}")
        print(f"\nOriginal hook:\n  -> {s.get('original_hook', '')}")
        print(f"\nAll 5 hook variations:")
        for i, h in enumerate(all_h, 1):
            print(f"\n  #{i} [{h.get('formula','').upper()}] score={h.get('scroll_stop_power',0)}/100")
            print(f"     {h.get('text', '')}")
        print(f"\n{'='*40}")
        print(f"WINNER [{winner.get('scroll_stop_power', 0)}/100]:")
        print(f"  -> {winner.get('text', '')}")
        print(f"  Why: {winner.get('reason', '')}")
        print(f"\nSaved to: logs/optimized_ryan_andrian.json")
