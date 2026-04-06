"""
Trend Radar — mengumpulkan sinyal tren dari 5 sumber resmi.
Multi-tenant ready.

v0.2: Google Trends 429 backoff, Wikipedia date fix
s82:  Regional targeting — geo disesuaikan peak_region tenant (default: US)
"""

import os
import json
import random
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import feedparser
import httpx
from loguru import logger
from pytrends.request import TrendReq
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig, NICHES, system_config

load_dotenv()

# ── Regional targeting map ─────────────────────────────────────────────────
# peak_region (dari tenant_configs) → parameter per API
REGION_MAP = {
    "us":     {"geo": "US", "yt_region": "US", "news_geo": "US", "news_ceid": "US:en", "tz": -300},
    "uk":     {"geo": "GB", "yt_region": "GB", "news_geo": "GB", "news_ceid": "GB:en", "tz":    0},
    "au":     {"geo": "AU", "yt_region": "AU", "news_geo": "AU", "news_ceid": "AU:en", "tz":  600},
    "ca":     {"geo": "CA", "yt_region": "CA", "news_geo": "CA", "news_ceid": "CA:en", "tz": -300},
    "global": {"geo": "",   "yt_region": "",   "news_geo": "US", "news_ceid": "US:en", "tz":    0},
}

REGION_DISPLAY = {
    "us":     "United States (Tier-1 — US audience)",
    "uk":     "United Kingdom (Tier-1 — UK audience)",
    "au":     "Australia (Tier-1 — AU audience)",
    "ca":     "Canada (Tier-1 — CA audience)",
    "global": "Global English-speaking audience",
}


class TrendRadar:
    """
    Mengumpulkan sinyal tren dari multiple sumber resmi.
    Multi-tenant ready — setiap scan menerima TenantConfig + opsional run_config.

    s82: regional targeting — semua sumber diarahkan ke peak_region tenant.
    """

    GOOGLE_TRENDS_MAX_RETRIES = 3
    GOOGLE_TRENDS_BASE_DELAY  = 5
    GOOGLE_TRENDS_MAX_DELAY   = 60

    def __init__(self):
        # Lazy init — pytrends diinit per-scan berdasarkan region
        self._pytrends = None
        self._pytrends_tz = None

    def _get_pytrends(self, tz: int = -300) -> TrendReq:
        """Inisialisasi (atau reinit jika tz berubah) TrendReq instance."""
        if self._pytrends is None or self._pytrends_tz != tz:
            self._pytrends    = TrendReq(hl='en-US', tz=tz, timeout=(10, 30))
            self._pytrends_tz = tz
        return self._pytrends

    # ─── SOURCE 1: Google Trends ───────────────────────────────────────────

    def _get_google_trends(self, keywords: list, geo: str = "US",
                           timeframe: str = "now 7-d", tz: int = -300) -> list:
        """
        Fetch Google Trends dengan exponential backoff + jitter.
        s82: geo parameter untuk regional targeting (default: US).
        """
        pytrends = self._get_pytrends(tz)

        for attempt in range(1, self.GOOGLE_TRENDS_MAX_RETRIES + 1):
            try:
                pytrends.build_payload(
                    keywords[:5],
                    timeframe=timeframe,
                    geo=geo,
                    gprop=''
                )
                interest = pytrends.interest_over_time()
                if interest.empty:
                    logger.warning(f"Google Trends [{geo}]: empty response")
                    return []

                results = []
                for kw in keywords[:5]:
                    if kw in interest.columns:
                        recent   = interest[kw].tail(7)
                        avg      = float(recent.mean())
                        momentum = float(recent.iloc[-1]) - float(recent.iloc[0])
                        results.append({
                            "keyword":      kw,
                            "avg_interest": round(avg, 1),
                            "momentum":     round(momentum, 1),
                            "geo":          geo,
                            "source":       "google_trends"
                        })
                return sorted(results, key=lambda x: x["avg_interest"], reverse=True)

            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "too many" in err_str or "rate" in err_str

                if is_rate_limit and attempt < self.GOOGLE_TRENDS_MAX_RETRIES:
                    delay  = min(self.GOOGLE_TRENDS_BASE_DELAY * (2 ** (attempt - 1)), self.GOOGLE_TRENDS_MAX_DELAY)
                    jitter = random.uniform(0, delay * 0.3)
                    wait   = round(delay + jitter, 1)
                    logger.warning(
                        f"Google Trends 429 [{geo}] — "
                        f"attempt {attempt}/{self.GOOGLE_TRENDS_MAX_RETRIES}, tunggu {wait}s..."
                    )
                    time.sleep(wait)
                    continue
                else:
                    logger.warning(f"Google Trends error (attempt {attempt}): {e}")
                    if attempt == self.GOOGLE_TRENDS_MAX_RETRIES:
                        logger.warning("Google Trends: semua attempt gagal, skip sumber ini")
                    return []

        return []

    # ─── SOURCE 2: YouTube Search API ──────────────────────────────────────

    def _get_youtube_trending_search(self, keywords: list, region_code: str = "US",
                                     limit: int = 10, api_key: str = "") -> list:
        """
        s82: tambah regionCode dan relevanceLanguage untuk Tier-1 targeting.
        """
        try:
            results        = []
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            if not api_key:
                logger.warning("[TrendRadar] youtube_api_key tidak tersedia — skip YouTube search")
                return []

            for kw in keywords[:3]:
                url = (
                    f"https://www.googleapis.com/youtube/v3/search"
                    f"?part=snippet&q={quote_plus(kw)}&type=video"
                    f"&videoDuration=short&order=viewCount"
                    f"&publishedAfter={seven_days_ago}"
                    f"&regionCode={region_code}"
                    f"&relevanceLanguage=en"
                    f"&maxResults=5&key={api_key}"
                )
                with httpx.Client(timeout=10) as client:
                    r = client.get(url)
                    if r.status_code == 200:
                        items = r.json().get("items", [])
                        for item in items:
                            snippet = item.get("snippet", {})
                            results.append({
                                "title":       snippet.get("title", ""),
                                "channel":     snippet.get("channelTitle", ""),
                                "published":   snippet.get("publishedAt", ""),
                                "keyword":     kw,
                                "region_code": region_code,
                                "source":      "youtube_search"
                            })
                    elif r.status_code == 403:
                        logger.warning("YouTube API: quota habis atau key tidak valid")
                        break
                time.sleep(0.5)

            logger.info(f"YouTube Search [{region_code}]: {len(results)} videos found")
            return results[:limit]

        except Exception as e:
            logger.warning(f"YouTube Search error: {e}")
            return []

    # ─── SOURCE 3: Google News RSS ─────────────────────────────────────────

    def _get_google_news_trending(self, keywords: list, geo: str = "US",
                                  ceid: str = "US:en", limit: int = 20) -> list:
        """
        s82: geo dan ceid untuk regional targeting.
        """
        try:
            results = []
            for kw in keywords[:2]:
                encoded = quote_plus(kw)
                url     = f"https://news.google.com/rss/search?q={encoded}&hl=en-{geo}&gl={geo}&ceid={ceid}"
                feed    = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    results.append({
                        "title":     entry.get("title", ""),
                        "published": entry.get("published", ""),
                        "keyword":   kw,
                        "geo":       geo,
                        "source":    "google_news"
                    })
                time.sleep(0.5)

            logger.info(f"Google News [{geo}]: {len(results)} articles found")
            return results[:limit]

        except Exception as e:
            logger.warning(f"Google News error: {e}")
            return []

    # ─── SOURCE 4: HackerNews ──────────────────────────────────────────────

    def _get_hackernews_trending(self, limit: int = 10) -> list:
        try:
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            with httpx.Client(timeout=10) as client:
                r = client.get(url)
                if r.status_code != 200:
                    return []

                story_ids = r.json()[:20]
                results   = []
                for sid in story_ids[:limit]:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                    sr = client.get(story_url)
                    if sr.status_code == 200:
                        story = sr.json()
                        if story.get("score", 0) > 100:
                            results.append({
                                "title":    story.get("title", ""),
                                "score":    story.get("score", 0),
                                "comments": story.get("descendants", 0),
                                "source":   "hackernews"
                            })
                    time.sleep(0.1)

            logger.info(f"HackerNews: {len(results)} stories found")
            return sorted(results, key=lambda x: x["score"], reverse=True)

        except Exception as e:
            logger.warning(f"HackerNews error: {e}")
            return []

    # ─── SOURCE 5: Wikipedia Trending ──────────────────────────────────────

    def _get_wikipedia_trending(self, limit: int = 10) -> list:
        """
        Fix v0.2: format tanggal YYYY/MM/DD.
        """
        try:
            for days_ago in [1, 2]:
                target_date = datetime.utcnow() - timedelta(days=days_ago)
                date_str    = target_date.strftime("%Y/%m/%d")
                url         = (
                    f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
                    f"en.wikipedia/all-access/{date_str}"
                )
                headers = {
                    "User-Agent": "MesinViral/1.0 (https://mesinviral.com; ryan.andrian.diputra@gmail.com)"
                }
                with httpx.Client(timeout=10, headers=headers) as client:
                    r = client.get(url)

                if r.status_code == 200:
                    items = r.json().get("items", [{}])[0].get("articles", [])
                    skip  = {
                        "Main_Page", "Special:Search",
                        "Wikipedia:Featured_pictures",
                        "Special:Statistics",
                    }
                    results = []
                    for item in items:
                        title = item.get("article", "")
                        if title not in skip and not title.startswith("Special:"):
                            results.append({
                                "title":  title.replace("_", " "),
                                "views":  item.get("views", 0),
                                "rank":   item.get("rank", 0),
                                "source": "wikipedia_trending"
                            })
                        if len(results) >= limit:
                            break

                    if results:
                        logger.info(f"Wikipedia Trending: {len(results)} articles (date: {date_str})")
                        return results
                    else:
                        logger.warning(f"Wikipedia: no results for {date_str}, trying earlier...")
                else:
                    logger.warning(f"Wikipedia API {r.status_code} for {date_str}")

            logger.warning("Wikipedia: tidak ada data tersedia")
            return []

        except Exception as e:
            logger.warning(f"Wikipedia error: {e}")
            return []

    # ─── MAIN SCAN ─────────────────────────────────────────────────────────

    def scan(self, tenant_config: TenantConfig, run_config=None,
             focus: str = None) -> dict:
        """
        s82: terima run_config (opsional) untuk baca peak_region.
        s84: terima focus (opsional) — keyword fokus dari production_schedules.
             Jika focus diisi, focus menjadi keyword prioritas pertama di semua sumber.
        Fallback: peak_region='us' (Tier-1 US default).
        """
        niche_data = NICHES.get(tenant_config.niche, NICHES["universe_mysteries"])
        base_keywords = niche_data["keywords"]

        # s84: focus keyword jadi prioritas #1, niche keywords pelengkap
        if focus and focus.strip():
            focus_clean = focus.strip()
            # Hindari duplikat jika focus sudah ada di base keywords
            extra = [k for k in base_keywords if k.lower() not in focus_clean.lower()]
            keywords = [focus_clean] + extra[:4]
            logger.info(f"[TrendRadar] Focus override: '{focus_clean}' + {extra[:4]}")
        else:
            keywords = base_keywords

        # ── Tentukan region ──────────────────────────────────────────
        peak_region = (
            getattr(run_config, "peak_region", None)
            or getattr(tenant_config, "peak_region", None)
            or "us"
        )
        region      = REGION_MAP.get(peak_region, REGION_MAP["us"])
        geo         = region["geo"]
        yt_region   = region["yt_region"]
        news_geo    = region["news_geo"]
        news_ceid   = region["news_ceid"]
        tz          = region["tz"]
        # ────────────────────────────────────────────────────────────

        logger.info(f"Scanning trends | tenant: {tenant_config.tenant_id}")
        logger.info(f"Niche: {niche_data['name']} | Region: {peak_region.upper()} | Keywords: {keywords[:3]}")

        signals = {
            "tenant_id":          tenant_config.tenant_id,
            "niche":              tenant_config.niche,
            "peak_region":        peak_region,
            "niche_focus":        focus or None,
            "timestamp":          datetime.now().isoformat(),
            "google_trends":      [],
            "youtube_search":     [],
            "news_trending":      [],
            "hackernews":         [],
            "wikipedia_trending": []
        }

        logger.info(f"1/5 Google Trends [geo={geo or 'global'}]...")
        signals["google_trends"] = self._get_google_trends(keywords, geo=geo, tz=tz)

        logger.info(f"2/5 YouTube Search [regionCode={yt_region or 'global'}]...")
        _yt_api_key = getattr(run_config, "youtube_api_key", None) or ""
        signals["youtube_search"] = self._get_youtube_trending_search(
            keywords, region_code=yt_region or "US", api_key=_yt_api_key
        )

        logger.info(f"3/5 Google News [geo={news_geo}]...")
        signals["news_trending"] = self._get_google_news_trending(keywords, geo=news_geo, ceid=news_ceid)

        logger.info("4/5 HackerNews...")
        signals["hackernews"] = self._get_hackernews_trending(limit=10)

        logger.info("5/5 Wikipedia Trending...")
        signals["wikipedia_trending"] = self._get_wikipedia_trending(limit=10)

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/signals_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)

        total = sum(len(signals[k]) for k in signals if isinstance(signals[k], list))
        logger.info(f"Scan complete: {total} signals | region: {peak_region.upper()}")
        return signals


if __name__ == "__main__":
    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")
    radar  = TrendRadar()
    signals = radar.scan(tenant)

    print(f"\n=== TREND SIGNALS — {tenant.tenant_id} ===")
    print(f"Region        : {signals.get('peak_region', 'us').upper()}")
    print(f"Google Trends : {len(signals['google_trends'])} keywords")
    print(f"YouTube Search: {len(signals['youtube_search'])} videos")
    print(f"Google News   : {len(signals['news_trending'])} articles")
    print(f"HackerNews    : {len(signals['hackernews'])} stories")
    print(f"Wikipedia     : {len(signals['wikipedia_trending'])} articles")

    if signals['google_trends']:
        t = signals['google_trends'][0]
        print(f"\nTop Trend: {t['keyword']} (geo={t.get('geo','?')}, interest={t['avg_interest']}, momentum={t['momentum']:+.1f})")
    if signals['wikipedia_trending']:
        w = signals['wikipedia_trending'][0]
        print(f"Top Wiki : {w['title']} ({w['views']:,} views)")
    if signals['hackernews']:
        print(f"Top HN   : {signals['hackernews'][0]['title'][:70]}")
    print("=== SCAN COMPLETE ===")
