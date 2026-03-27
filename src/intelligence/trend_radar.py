"""
Trend Radar — mengumpulkan sinyal tren dari 5 sumber resmi.
Multi-tenant ready.

Fix v0.2:
- Google Trends 429: exponential backoff + jitter + retry 3x
- Wikipedia trending: fix format tanggal (YYYY/MM/DD)
- urllib3/chardet: sudah difix di requirements.txt
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


class TrendRadar:
    """
    Mengumpulkan sinyal tren dari multiple sumber resmi.
    Multi-tenant ready — setiap scan menerima TenantConfig.
    """

    GOOGLE_TRENDS_MAX_RETRIES = 3
    GOOGLE_TRENDS_BASE_DELAY  = 5   # detik — base untuk exponential backoff
    GOOGLE_TRENDS_MAX_DELAY   = 60  # detik — cap backoff

    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=420, timeout=(10, 30))

    # ─── SOURCE 1: Google Trends ───────────────────────────────────────────

    def _get_google_trends(self, keywords: list, timeframe: str = "now 7-d") -> list:
        """
        Fetch Google Trends dengan exponential backoff + jitter.
        Fix: handle 429 rate limit yang sebelumnya crash pipeline.
        """
        for attempt in range(1, self.GOOGLE_TRENDS_MAX_RETRIES + 1):
            try:
                self.pytrends.build_payload(
                    keywords[:5],
                    timeframe=timeframe,
                    geo='',
                    gprop=''
                )
                interest = self.pytrends.interest_over_time()
                if interest.empty:
                    logger.warning("Google Trends: empty response")
                    return []

                results = []
                for kw in keywords[:5]:
                    if kw in interest.columns:
                        recent  = interest[kw].tail(7)
                        avg     = float(recent.mean())
                        momentum = float(recent.iloc[-1]) - float(recent.iloc[0])
                        results.append({
                            "keyword":      kw,
                            "avg_interest": round(avg, 1),
                            "momentum":     round(momentum, 1),
                            "source":       "google_trends"
                        })
                return sorted(results, key=lambda x: x["avg_interest"], reverse=True)

            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "too many" in err_str or "rate" in err_str

                if is_rate_limit and attempt < self.GOOGLE_TRENDS_MAX_RETRIES:
                    # Exponential backoff + jitter
                    delay = min(
                        self.GOOGLE_TRENDS_BASE_DELAY * (2 ** (attempt - 1)),
                        self.GOOGLE_TRENDS_MAX_DELAY
                    )
                    jitter = random.uniform(0, delay * 0.3)
                    wait   = round(delay + jitter, 1)
                    logger.warning(
                        f"Google Trends 429 rate limit — "
                        f"attempt {attempt}/{self.GOOGLE_TRENDS_MAX_RETRIES}, "
                        f"tunggu {wait}s..."
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

    def _get_youtube_trending_search(self, keywords: list, limit: int = 10) -> list:
        try:
            results = []
            # publishedAfter: 7 hari yang lalu dari sekarang
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

            for kw in keywords[:3]:
                url = (
                    f"https://www.googleapis.com/youtube/v3/search"
                    f"?part=snippet&q={quote_plus(kw)}&type=video"
                    f"&videoDuration=short&order=viewCount"
                    f"&publishedAfter={seven_days_ago}"
                    f"&maxResults=5&key={os.getenv('YOUTUBE_API_KEY', '')}"
                )
                with httpx.Client(timeout=10) as client:
                    r = client.get(url)
                    if r.status_code == 200:
                        items = r.json().get("items", [])
                        for item in items:
                            snippet = item.get("snippet", {})
                            results.append({
                                "title":     snippet.get("title", ""),
                                "channel":   snippet.get("channelTitle", ""),
                                "published": snippet.get("publishedAt", ""),
                                "keyword":   kw,
                                "source":    "youtube_search"
                            })
                    elif r.status_code == 403:
                        logger.warning("YouTube API key tidak valid atau quota habis")
                        break
                time.sleep(0.5)

            logger.info(f"YouTube Search: {len(results)} videos found")
            return results[:limit]

        except Exception as e:
            logger.warning(f"YouTube Search error: {e}")
            return []

    # ─── SOURCE 3: Google News RSS ─────────────────────────────────────────

    def _get_google_news_trending(self, keywords: list, limit: int = 20) -> list:
        try:
            results = []
            for kw in keywords[:2]:
                encoded = quote_plus(kw)
                url     = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
                feed    = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    results.append({
                        "title":     entry.get("title", ""),
                        "published": entry.get("published", ""),
                        "keyword":   kw,
                        "source":    "google_news"
                    })
                time.sleep(0.5)

            logger.info(f"Google News: {len(results)} articles found")
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
        Fix v0.2: format tanggal yang benar untuk Wikimedia API.
        API expects: YYYY/MM/DD (dengan leading zero)
        Sebelumnya kadang return 0 karena format tidak sesuai.
        """
        try:
            # Coba kemarin dulu, fallback ke 2 hari lalu
            # (Wikimedia kadang belum update data kemarin)
            for days_ago in [1, 2]:
                target_date = datetime.utcnow() - timedelta(days=days_ago)
                # Format yang benar: YYYY/MM/DD dengan leading zero
                date_str = target_date.strftime("%Y/%m/%d")

                url = (
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
                        logger.info(
                            f"Wikipedia Trending: {len(results)} articles "
                            f"(date: {date_str})"
                        )
                        return results
                    else:
                        logger.warning(f"Wikipedia: no results for {date_str}, trying earlier...")
                        continue
                else:
                    logger.warning(f"Wikipedia API {r.status_code} for {date_str}")
                    continue

            logger.warning("Wikipedia: tidak ada data tersedia")
            return []

        except Exception as e:
            logger.warning(f"Wikipedia error: {e}")
            return []

    # ─── MAIN SCAN ─────────────────────────────────────────────────────────

    def scan(self, tenant_config: TenantConfig) -> dict:
        niche_data = NICHES.get(tenant_config.niche, NICHES["universe_mysteries"])
        keywords   = niche_data["keywords"]

        logger.info(f"Scanning trends for tenant: {tenant_config.tenant_id}")
        logger.info(f"Niche: {niche_data['name']} | Keywords: {keywords[:3]}")

        signals = {
            "tenant_id":          tenant_config.tenant_id,
            "niche":              tenant_config.niche,
            "timestamp":          datetime.now().isoformat(),
            "google_trends":      [],
            "youtube_search":     [],
            "news_trending":      [],
            "hackernews":         [],
            "wikipedia_trending": []
        }

        logger.info("1/5 Scanning Google Trends...")
        signals["google_trends"] = self._get_google_trends(keywords)

        logger.info("2/5 Scanning YouTube Search...")
        signals["youtube_search"] = self._get_youtube_trending_search(keywords)

        logger.info("3/5 Scanning Google News...")
        signals["news_trending"] = self._get_google_news_trending(keywords)

        logger.info("4/5 Scanning HackerNews...")
        signals["hackernews"] = self._get_hackernews_trending(limit=10)

        logger.info("5/5 Scanning Wikipedia Trending...")
        signals["wikipedia_trending"] = self._get_wikipedia_trending(limit=10)

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/signals_{tenant_config.tenant_id}.json", "w") as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)

        total = sum(len(signals[k]) for k in signals if isinstance(signals[k], list))
        logger.info(f"Scan complete: {total} signals collected")
        return signals


if __name__ == "__main__":
    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")
    radar  = TrendRadar()
    signals = radar.scan(tenant)

    print(f"\n=== TREND SIGNALS — {tenant.tenant_id} ===")
    print(f"Google Trends : {len(signals['google_trends'])} keywords")
    print(f"YouTube Search: {len(signals['youtube_search'])} videos")
    print(f"Google News   : {len(signals['news_trending'])} articles")
    print(f"HackerNews    : {len(signals['hackernews'])} stories")
    print(f"Wikipedia     : {len(signals['wikipedia_trending'])} articles")

    if signals['google_trends']:
        t = signals['google_trends'][0]
        print(f"\nTop Trend: {t['keyword']} (interest: {t['avg_interest']}, momentum: {t['momentum']})")
    if signals['wikipedia_trending']:
        w = signals['wikipedia_trending'][0]
        print(f"Top Wiki : {w['title']} ({w['views']:,} views)")
    if signals['hackernews']:
        print(f"Top HN   : {signals['hackernews'][0]['title'][:70]}")
    print("=== SCAN COMPLETE ===")
