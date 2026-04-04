import os
import json
import re
from datetime import datetime
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, NICHES, VIRAL_SCORE_WEIGHTS, system_config
from src.intelligence.trend_radar import REGION_DISPLAY
from src.utils.supabase_writer import _normalize_slug, get_writer

load_dotenv()

class NicheSelector:
    """
    Menganalisis sinyal tren dan memilih topik terbaik untuk diproduksi.
    Multi-tenant ready — setiap analisis menerima TenantConfig + signals.

    Fix v0.2:
    - Retry logic 3x jika JSON parse gagal
    - response_format=json_object untuk paksa GPT return valid JSON
    - JSON extraction fallback — cari array [...] dari response apapun
    - Tidak pernah return [] tanpa mencoba ulang
    """

    MAX_RETRIES = 3

    def __init__(self):
        self.client = OpenAI(api_key=system_config.openai_api_key)

    def _prepare_signals_summary(self, signals: dict, tenant_config: TenantConfig) -> str:
        niche_data  = NICHES[tenant_config.niche]
        peak_region = signals.get("peak_region", "us")
        audience    = REGION_DISPLAY.get(peak_region, REGION_DISPLAY["us"])
        lines = [
            f"NICHE: {niche_data['name']}",
            f"TARGET EMOTION: {niche_data['target_emotion']}",
            f"TARGET AUDIENCE: {audience}",
            ""
        ]

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

    def _clean_json_response(self, raw: str) -> str:
        """
        Bersihkan response GPT sebelum di-parse:
        1. Hapus markdown code fences
        2. Cari JSON array [...] jika ada teks lain di luar
        3. Hapus trailing comma sebelum ] atau }
        4. Hapus control characters yang tidak valid di JSON
        """
        # Step 1: hapus markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()

        # Step 2: cari array JSON [...] — ambil dari [ pertama hingga ] terakhir
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            raw = match.group(0)

        # Step 3: hapus trailing comma sebelum ] atau }
        raw = re.sub(r',\s*([}\]])', r'\1', raw)

        # Step 4: hapus control characters tidak valid (kecuali \n \t \r)
        raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

        return raw.strip()

    def _calculate_viral_score(self, topic: dict) -> float:
        weights = VIRAL_SCORE_WEIGHTS
        return round(
            topic.get("search_volume", 0)       * weights["search_volume"] +
            topic.get("trend_momentum", 0)      * weights["trend_momentum"] +
            topic.get("emotional_trigger", 0)   * weights["emotional_trigger"] +
            topic.get("competition_gap", 0)     * weights["competition_gap"] +
            topic.get("evergreen_potential", 0) * weights["evergreen_potential"],
            1
        )

    def _analyze_with_ai(self, signals_summary: str, tenant_config: TenantConfig,
                         peak_region: str = "us", focus: str = None) -> list:
        niche_data = NICHES[tenant_config.niche]

        audience = REGION_DISPLAY.get(peak_region, REGION_DISPLAY["us"])

        # s84: focus constraint untuk AI prompt
        focus_block = ""
        if focus and focus.strip():
            focus_block = (
                f"\nFOCUS CONSTRAINT: Topics MUST be specifically about \"{focus.strip()}\". "
                f"Only select topics that directly relate to this focus within the "
                f"{niche_data['name']} niche. Generic topics outside this focus are NOT acceptable.\n"
            )

        prompt = f"""You are an expert viral content strategist specializing in short-form video (60 seconds max).

Analyze the following trending signals and select the TOP 5 video topics with the highest viral potential.

{signals_summary}

CONTENT STYLE: {niche_data['style']}
TARGET EMOTION: {niche_data['target_emotion']}
TARGET AUDIENCE: {audience}
LANGUAGE: {tenant_config.language}
PLATFORM: YouTube Shorts, TikTok, Instagram Reels
{focus_block}
IMPORTANT: Prioritize topics that are trending RIGHT NOW in the target region.
Pick angles and hooks that resonate specifically with the target audience's culture and interests.

For each topic, score these dimensions (0-100):
1. search_volume: How many people are searching for this?
2. trend_momentum: Is interest rising fast right now?
3. emotional_trigger: How strongly does it trigger awe, curiosity, or surprise?
4. competition_gap: Is there a lack of quality short-form content on this?
5. evergreen_potential: Will this topic stay relevant for months?

Return ONLY a valid JSON array with exactly 5 items, no other text:
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
The hook must be irresistible. The angle must be unique.
IMPORTANT: Return ONLY the JSON array. No explanation, no markdown, no extra text."""

        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"AI analysis attempt {attempt}/{self.MAX_RETRIES}...")

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a viral content strategist. "
                                "You MUST return only a valid JSON array. "
                                "No markdown, no explanation, no text outside the JSON array."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.8,
                    # Paksa GPT return JSON valid — eliminasi mayoritas parse error
                    response_format={"type": "json_object"}
                )

                raw = response.choices[0].message.content.strip()
                logger.debug(f"Raw response (first 200 chars): {raw[:200]}")

                cleaned = self._clean_json_response(raw)

                # Jika response_format=json_object return {"topics": [...]}
                # kita perlu extract array-nya
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    # Cari key yang valuenya list
                    topics = None
                    for key in ["topics", "results", "data", "items"]:
                        if key in parsed and isinstance(parsed[key], list):
                            topics = parsed[key]
                            break
                    # Fallback: ambil value pertama yang berupa list
                    if topics is None:
                        for val in parsed.values():
                            if isinstance(val, list) and len(val) > 0:
                                topics = val
                                break
                    if topics is None:
                        raise ValueError(f"Tidak menemukan array topics di response: {list(parsed.keys())}")
                elif isinstance(parsed, list):
                    topics = parsed
                else:
                    raise ValueError(f"Response bukan dict atau list: {type(parsed)}")

                if not topics:
                    raise ValueError("Topics array kosong")

                # Hitung ulang viral score untuk konsistensi
                for t in topics:
                    t["viral_score"] = self._calculate_viral_score(t)

                logger.info(f"AI analysis success on attempt {attempt}: {len(topics)} topics")
                return sorted(topics, key=lambda x: x["viral_score"], reverse=True)

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
        return []

    def select(self, signals: dict, tenant_config: TenantConfig,
               focus: str = None) -> list:
        """
        Analisis sinyal dan pilih top 5 topik viral.
        s71: Tambah duplicate prevention — topik yang sudah diproduksi
        dalam lookback_days terakhir difilter sebelum dikembalikan.
        s84: focus (opsional) — constraint AI agar topik spesifik ke focus keyword.

        Prinsip: produksi TIDAK pernah berhenti.
        Jika semua topik baru duplikat → pakai LRU dari riwayat (safety net).
        """
        total_signals = sum(len(v) for v in signals.values() if isinstance(v, list))
        logger.info(f"Analyzing {total_signals} signals...")

        # s84: ambil focus dari signals jika tidak di-pass langsung
        if not focus:
            focus = signals.get("niche_focus") or None

        if focus:
            logger.info(f"[NicheSelector] Focus constraint: '{focus}'")

        summary     = self._prepare_signals_summary(signals, tenant_config)
        peak_region = signals.get("peak_region", "us")
        topics      = self._analyze_with_ai(
            summary, tenant_config, peak_region=peak_region, focus=focus
        )

        # ── s71: Duplicate prevention ──────────────────────────────────
        topics = self._filter_duplicates(topics, tenant_config)
        # ───────────────────────────────────────────────────────────────

        result = {
            "tenant_id": tenant_config.tenant_id,
            "niche":     tenant_config.niche,
            "timestamp": datetime.now().isoformat(),
            "topics":    topics
        }

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/topics_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"Selected {len(topics)} topics after duplicate filter")
        return topics


    def _filter_duplicates(self, topics: list, tenant_config: TenantConfig) -> list:
        """
        Filter topik yang sudah diproduksi dalam lookback_days terakhir.

        Logika:
          1. Ambil recent_topics dari Supabase (per tenant + niche)
          2. Filter topics yang slug-nya tidak ada di recent_slugs
          3. Jika semua duplikat → ambil topik paling lama (LRU) sebagai safety net
             Produksi tidak pernah berhenti.
        """
        if not topics:
            return topics

        writer        = get_writer()
        lookback_days = self._get_lookback_days(tenant_config)

        recent = writer.get_recent_topics(
            tenant_id=tenant_config.tenant_id,
            niche=tenant_config.niche,
            lookback_days=lookback_days,
        )

        if not recent:
            logger.info("[NicheSelector] Tidak ada riwayat topik — semua dianggap baru")
            return topics

        recent_slugs = {r.get("topic_slug", "") for r in recent if r.get("topic_slug")}
        logger.info(
            f"[NicheSelector] Duplicate check: {len(recent_slugs)} recent slugs "
            f"(lookback={lookback_days}d, niche={tenant_config.niche})"
        )

        fresh_topics = []
        for t in topics:
            slug = _normalize_slug(t.get("topic", ""))
            if slug and slug not in recent_slugs:
                fresh_topics.append(t)
            else:
                logger.info(f"[NicheSelector] Duplikat difilter: '{t.get('topic', '')[:60]}'")

        if fresh_topics:
            logger.info(
                f"[NicheSelector] ✅ {len(fresh_topics)}/{len(topics)} topik baru "
                f"(difilter {len(topics) - len(fresh_topics)} duplikat)"
            )
            return fresh_topics

        # ── Safety net: semua topik AI adalah duplikat ────────────────
        logger.warning(
            f"[NicheSelector] ⚠️  SEMUA {len(topics)} topik AI duplikat. "
            f"Pakai LRU dari riwayat sebagai safety net."
        )

        # recent di-order ASC (oldest first) dari get_recent_topics
        lru = recent[0] if recent else None
        if lru and lru.get("topic"):
            fallback = {
                "topic":               lru["topic"],
                "angle":               "Revisiting this fascinating topic with fresh perspective",
                "hook":                f"You need to hear this again — {lru['topic'][:50]}",
                "why_viral":           "Previously produced topic — LRU safety net",
                "search_volume":       50,
                "trend_momentum":      50,
                "emotional_trigger":   60,
                "competition_gap":     40,
                "evergreen_potential": 70,
                "viral_score":         54.0,
                "keywords":            [],
                "estimated_views_range": "unknown",
                "content_type":        "evergreen",
                "_is_lru_fallback":    True,
            }
            logger.warning(
                f"[NicheSelector] LRU fallback: '{lru['topic'][:60]}' "
                f"(diproduksi: {lru.get('published_at', 'unknown')[:10]})"
            )
            return [fallback]

        # Last resort — kembalikan topik AI pertama meski duplikat
        logger.warning("[NicheSelector] LRU fallback gagal — pakai topik AI pertama")
        return topics[:1]

    def _get_lookback_days(self, tenant_config: TenantConfig) -> int:
        """
        Ambil duplicate_lookback_days dari Supabase config tenant.
        Fallback ke 30 hari. Config-driven: ubah via Supabase.
        """
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id)
            days = getattr(rc, "duplicate_lookback_days", 30) or 30
            return int(days)
        except Exception:
            return 30


if __name__ == "__main__":
    from src.intelligence.trend_radar import TrendRadar

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    logger.info("Step 1: Scanning trends...")
    signals = TrendRadar().scan(tenant)

    logger.info("Step 2: Selecting best topics with AI...")
    topics = NicheSelector().select(signals, tenant)

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
