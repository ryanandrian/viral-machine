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
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import httpx
from loguru import logger
from pytrends.request import TrendReq
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig, get_niches, system_config

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

    _GLOBAL = "_all"   # scope sumber global (HackerNews/Wikipedia — tak per-niche/geo)

    def __init__(self):
        # Lazy init — pytrends diinit per-scan berdasarkan region
        self._pytrends = None
        self._pytrends_tz = None
        self._sbc = None   # F1: client trend_cache (lazy, service_role worker)

    def _get_pytrends(self, tz: int = -300) -> TrendReq:
        """Inisialisasi (atau reinit jika tz berubah) TrendReq instance."""
        if self._pytrends is None or self._pytrends_tz != tz:
            self._pytrends    = TrendReq(hl='en-US', tz=tz, timeout=(10, 30))
            self._pytrends_tz = tz
        return self._pytrends

    # ─── F1: trend_cache (TREND_RADAR_ARCHITECTURE.md §3 Pilar-1 — decouple, anti-429 skala) ──
    # Produce BACA cache (hot-path NOL fetch eksternal); TrendRefresher (worker) yang ISI.
    def _cache_sb(self):
        if self._sbc is None:
            from supabase import create_client
            self._sbc = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        return self._sbc

    @staticmethod
    def _cache_key(niche: str, geo: str, source: str) -> str:
        return f"{niche}|{geo}|{source}|"

    def _read_cache(self, niche: str, geo: str, source: str) -> list:
        """Baca sinyal dari trend_cache (apa adanya — produce pakai yang tersedia, graceful)."""
        try:
            r = (self._cache_sb().table("trend_cache").select("signals")
                 .eq("cache_key", self._cache_key(niche, geo, source)).limit(1).execute())
            if r.data:
                return r.data[0].get("signals") or []
        except Exception as e:
            logger.warning(f"[TrendRadar] read_cache {source} gagal: {e}")
        return []

    def _cache_age_sec(self, niche: str, geo: str, source: str):
        """Umur cache (detik), atau None bila belum ada."""
        try:
            r = (self._cache_sb().table("trend_cache").select("fetched_at")
                 .eq("cache_key", self._cache_key(niche, geo, source)).limit(1).execute())
            if r.data and r.data[0].get("fetched_at"):
                ts = datetime.fromisoformat(str(r.data[0]["fetched_at"]).replace("Z", "+00:00"))
                return (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            pass
        return None

    def _write_cache(self, niche: str, geo: str, source: str, signals: list, ttl_sec: int = None) -> None:
        try:
            row = {
                "cache_key": self._cache_key(niche, geo, source),
                "niche": niche, "geo": geo, "source": source,
                "signals": signals or [],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            if ttl_sec:
                row["ttl_sec"] = int(ttl_sec)
            self._cache_sb().table("trend_cache").upsert(row, on_conflict="cache_key").execute()
        except Exception as e:
            logger.warning(f"[TrendRadar] write_cache {source} gagal: {e}")

    def refresh_niche_geo(self, niche: str, region_key: str, keywords: list,
                          ttl_sec: int, yt_api_key: str = "", only_stale: bool = True) -> int:
        """Dipakai TrendRefresher (worker, OFF hot-path). Fetch sumber per-(niche,geo) yang
        BASI → tulis trend_cache: google_trends, youtube_search, news_trending. Return jumlah ditulis."""
        region  = REGION_MAP.get(region_key, REGION_MAP["us"])
        written = 0
        def _stale(src):
            if not only_stale:
                return True
            age = self._cache_age_sec(niche, region_key, src)
            return age is None or age > ttl_sec
        if _stale("google_trends"):
            self._write_cache(niche, region_key, "google_trends",
                              self._get_google_trends(keywords, geo=region["geo"], tz=region["tz"]), ttl_sec); written += 1
        if _stale("youtube_search"):
            self._write_cache(niche, region_key, "youtube_search",
                              self._get_youtube_trending_search(keywords, region_code=region["yt_region"] or "US", api_key=yt_api_key), ttl_sec); written += 1
        if _stale("news_trending"):
            self._write_cache(niche, region_key, "news_trending",
                              self._get_google_news_trending(keywords, geo=region["news_geo"], ceid=region["news_ceid"]), ttl_sec); written += 1
        if _stale("youtube_autocomplete"):
            self._write_cache(niche, region_key, "youtube_autocomplete",
                              self._get_youtube_autocomplete(keywords), ttl_sec); written += 1
        return written

    def _get_youtube_autocomplete(self, keywords: list, limit: int = 10) -> list:
        """YouTube autocomplete/suggest (endpoint tak-resmi, GRATIS) — query emergent paling dini.
        TREND_RADAR_ARCHITECTURE.md §2c-C. Pelengkap demand (bukan tulang punggung). Fail-soft."""
        results, seen = [], set()
        for kw in (keywords or [])[:3]:
            try:
                url = (f"https://suggestqueries.google.com/complete/search"
                       f"?client=firefox&ds=yt&q={quote_plus(str(kw))}")
                r = httpx.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    data = json.loads(r.text)
                    for s in (data[1] if len(data) > 1 else [])[:limit]:
                        if s and s.lower() not in seen and s.lower() != str(kw).lower():
                            seen.add(s.lower())
                            results.append({"keyword": kw, "query": s})
            except Exception as e:
                logger.warning(f"[TrendRadar] autocomplete '{kw}' gagal: {e}")
        return results[: limit * 2]

    def refresh_global(self, ttl_sec: int, only_stale: bool = True) -> int:
        """Refresh sumber GLOBAL (HackerNews, Wikipedia) — sekali, tak per-niche/geo."""
        written = 0
        for src, fetch in (("hackernews", lambda: self._get_hackernews_trending(limit=10)),
                           ("wikipedia_trending", lambda: self._get_wikipedia_trending(limit=10))):
            age = self._cache_age_sec(self._GLOBAL, self._GLOBAL, src)
            if (not only_stale) or age is None or age > ttl_sec:
                self._write_cache(self._GLOBAL, self._GLOBAL, src, fetch(), ttl_sec); written += 1
        return written

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
        niches     = get_niches()
        niche_data = niches.get(tenant_config.niche) or next(
            (v for v in niches.values() if v.get("is_active", True)), {}
        )
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
            "wikipedia_trending": [],
            "youtube_autocomplete": []
        }

        # ── F1 (§3 Pilar-1): BACA trend_cache — hot-path TIDAK panggil sumber eksternal ──
        # (anti-429 skala; TrendRefresher worker yang mengisi cache di luar hot-path).
        # Per-(niche,geo): google_trends/youtube_search/news_trending · GLOBAL: hackernews/wikipedia.
        signals["google_trends"]      = self._read_cache(tenant_config.niche, peak_region, "google_trends")
        signals["youtube_search"]     = self._read_cache(tenant_config.niche, peak_region, "youtube_search")
        signals["news_trending"]      = self._read_cache(tenant_config.niche, peak_region, "news_trending")
        signals["hackernews"]         = self._read_cache(self._GLOBAL, self._GLOBAL, "hackernews")
        signals["wikipedia_trending"] = self._read_cache(self._GLOBAL, self._GLOBAL, "wikipedia_trending")
        signals["youtube_autocomplete"] = self._read_cache(tenant_config.niche, peak_region, "youtube_autocomplete")

        total = sum(len(signals[k]) for k in signals if isinstance(signals[k], list))
        if total == 0:
            logger.warning(
                f"[TrendRadar] trend_cache KOSONG (niche={tenant_config.niche}, geo={peak_region}) — "
                f"TrendRefresher belum mengisi? Produce lanjut dgn sinyal minim (niche_selector fallback)."
            )
        logger.info(f"Scan (cache) complete: {total} signals | niche={tenant_config.niche} | region: {peak_region.upper()}")
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
