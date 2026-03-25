import os
import json
from datetime import datetime
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, NICHES, VIRAL_SCORE_WEIGHTS, system_config

load_dotenv()

class NicheSelector:
    """
    Menganalisis sinyal tren dan memilih topik terbaik untuk diproduksi.
    Multi-tenant ready — setiap analisis menerima TenantConfig + signals.
    """

    def __init__(self):
        self.client = OpenAI(api_key=system_config.openai_api_key)

    def _prepare_signals_summary(self, signals: dict, tenant_config: TenantConfig) -> str:
        niche_data = NICHES[tenant_config.niche]
        lines = [f"NICHE: {niche_data['name']}", f"TARGET EMOTION: {niche_data['target_emotion']}", ""]

        if signals.get("google_trends"):
            lines.append("=== GOOGLE TRENDS (7 days) ===")
            for t in signals["google_trends"][:5]:
                lines.append(f"- {t['keyword']}: interest={t['avg_interest']}, momentum={t['momentum']:+.1f}")

        if signals.get("youtube_search"):
            lines.append("\n=== YOUTUBE TRENDING VIDEOS ===")
            for v in signals["youtube_search"][:10]:
                lines.append(f"- [{v['keyword']}] {v['title'][:80]}")

        if signals.get("news_trending"):
            lines.append("\n=== TRENDING NEWS ===")
            for n in signals["news_trending"][:10]:
                lines.append(f"- {n['title'][:80]}")

        if signals.get("hackernews"):
            lines.append("\n=== HACKERNEWS HOT ===")
            for h in signals["hackernews"][:5]:
                lines.append(f"- {h['title'][:80]} (score: {h['score']})")

        return "\n".join(lines)

    def _analyze_with_ai(self, signals_summary: str, tenant_config: TenantConfig) -> list:
        niche_data = NICHES[tenant_config.niche]

        prompt = f"""You are an expert viral content strategist specializing in short-form video (60 seconds max).

Analyze the following trending signals and select the TOP 5 video topics with the highest viral potential.

{signals_summary}

CONTENT STYLE: {niche_data['style']}
TARGET EMOTION: {niche_data['target_emotion']}
LANGUAGE: {tenant_config.language}
PLATFORM: YouTube Shorts, TikTok, Instagram Reels

For each topic, score these dimensions (0-100):
1. search_volume: How many people are searching for this?
2. trend_momentum: Is interest rising fast right now?
3. emotional_trigger: How strongly does it trigger awe, curiosity, or surprise?
4. competition_gap: Is there a lack of quality short-form content on this?
5. evergreen_potential: Will this topic stay relevant for months?

Return ONLY a valid JSON array, no other text:
[
  {{
    "topic": "specific video topic title",
    "angle": "unique angle that makes this special — not generic",
    "hook": "the exact first sentence to open the video (under 15 words, must stop the scroll)",
    "why_viral": "one sentence explaining viral potential",
    "search_volume": 85,
    "trend_momentum": 90,
    "emotional_trigger": 88,
    "competition_gap": 70,
    "evergreen_potential": 75,
    "viral_score": 82,
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "estimated_views_range": "100K-500K",
    "content_type": "mystery|facts|history|science"
  }}
]

Be specific with topics — not "space facts" but "The object NASA found that defies physics".
The hook must be irresistible. The angle must be unique."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral content strategist. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.8
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            topics = json.loads(raw)

            weights = VIRAL_SCORE_WEIGHTS
            for t in topics:
                calculated = (
                    t.get("search_volume", 0) * weights["search_volume"] +
                    t.get("trend_momentum", 0) * weights["trend_momentum"] +
                    t.get("emotional_trigger", 0) * weights["emotional_trigger"] +
                    t.get("competition_gap", 0) * weights["competition_gap"] +
                    t.get("evergreen_potential", 0) * weights["evergreen_potential"]
                )
                t["viral_score"] = round(calculated, 1)

            return sorted(topics, key=lambda x: x["viral_score"], reverse=True)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return []

    def select(self, signals: dict, tenant_config: TenantConfig) -> list:
        """
        Analisis sinyal dan pilih top 5 topik viral.
        Returns: list of topic dicts sorted by viral_score desc.
        """
        logger.info(f"Analyzing {sum(len(v) for v in signals.values() if isinstance(v, list))} signals...")

        summary = self._prepare_signals_summary(signals, tenant_config)
        topics = self._analyze_with_ai(summary, tenant_config)

        result = {
            "tenant_id": tenant_config.tenant_id,
            "niche": tenant_config.niche,
            "timestamp": datetime.now().isoformat(),
            "topics": topics
        }

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/topics_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"Selected {len(topics)} topics")
        return topics


if __name__ == "__main__":
    from src.intelligence.trend_radar import TrendRadar

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    logger.info("Step 1: Scanning trends...")
    radar = TrendRadar()
    signals = radar.scan(tenant)

    logger.info("Step 2: Selecting best topics with AI...")
    selector = NicheSelector()
    topics = selector.select(signals, tenant)

    print(f"\n{'='*60}")
    print(f"TOP {len(topics)} VIRAL TOPICS FOR: {tenant.tenant_id}")
    print(f"{'='*60}")
    for i, t in enumerate(topics, 1):
        print(f"\n#{i} [{t['viral_score']:.0f}/100] {t['topic']}")
        print(f"    Angle  : {t['angle']}")
        print(f"    Hook   : {t['hook']}")
        print(f"    Why    : {t['why_viral']}")
        print(f"    Est.   : {t.get('estimated_views_range', 'N/A')} views")
        print(f"    Scores : search={t['search_volume']} momentum={t['trend_momentum']} emotion={t['emotional_trigger']}")
    print(f"\n{'='*60}")
    print("Saved to logs/topics_ryan_andrian.json")
