"""
ChannelAnalytics — Pull YouTube video metrics dan simpan ke Supabase.

s84b: Dua layer analytics:
  Layer Basic : YouTube Data API v3  — views, likes, comments
                (scope youtube.readonly — sudah ada di token)
  Layer Full  : YouTube Analytics v2 — watch_time, avg_view_pct, CTR, subscriber_gain
                (scope yt-analytics.readonly — aktifkan via scripts/reauth_youtube.py)

Dijalankan harian via cron: scripts/fetch_analytics.sh
Data tersedia 48 jam setelah video dipublish (YouTube delay normal).
"""

import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Scope yang dibutuhkan untuk full analytics
YT_ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"


class ChannelAnalytics:
    """
    Pull YouTube video metrics dan upsert ke tabel video_analytics Supabase.

    Cara pakai:
        analytics = ChannelAnalytics()
        result = analytics.fetch_and_store(tenant_id="ryan_andrian")
        print(result)  # {"fetched": 12, "updated": 12, "full_analytics": True}
    """

    # Delay minimum setelah publish sebelum analytics tersedia (YouTube SLA)
    MIN_HOURS_AFTER_PUBLISH = 48

    # Jangan re-fetch video yang analytics-nya sudah diambil dalam N jam
    REFETCH_INTERVAL_HOURS = 23

    # Maksimum video yang diproses per run
    MAX_VIDEOS_PER_RUN = 50

    def __init__(self, token_path: str = None, tenant_id: str = None):
        """
        token_path: eksplisit path ke token file (opsional)
        tenant_id:  jika diisi, resolve path via konvensi tokens/{tenant_id}.json
        Fallback:   token_youtube.json (backward compatible)
        """
        self._token_path = self._resolve_token_path(token_path, tenant_id)
        self._supabase   = self._init_supabase()
        self._creds      = None
        self._youtube    = None      # Data API v3
        self._analytics  = None      # Analytics API v2
        self._has_analytics_scope = False
        self._analytics_403_count = 0   # consecutive 403s — disable scope setelah 3
        self._init_clients()

    @staticmethod
    def _resolve_token_path(token_path: str = None, tenant_id: str = None) -> str:
        """Resolve token path dengan priority: eksplisit → per-channel → fallback."""
        if token_path:
            return token_path
        if tenant_id:
            per_channel = f"tokens/{tenant_id}.json"
            if os.path.exists(per_channel):
                return per_channel
        return "token_youtube.json"

    # ── Init ──────────────────────────────────────────────────────────────

    def _init_supabase(self):
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                return create_client(url, key)
            logger.warning("[Analytics] SUPABASE_URL/KEY tidak ada")
            return None
        except Exception as e:
            logger.warning(f"[Analytics] Supabase init gagal: {e}")
            return None

    def _init_clients(self):
        """Load OAuth credentials dan inisialisasi YouTube API clients."""
        try:
            self._creds = self._load_credentials()
            if not self._creds:
                return

            from googleapiclient.discovery import build

            # Data API v3 — selalu tersedia
            self._youtube = build("youtube", "v3", credentials=self._creds)
            logger.info("[Analytics] YouTube Data API v3 siap")

            # Analytics API v2 — cek scope
            token_scopes = list(self._creds.scopes or [])
            if YT_ANALYTICS_SCOPE in token_scopes:
                self._analytics = build("youtubeAnalytics", "v2", credentials=self._creds)
                self._has_analytics_scope = True
                logger.info("[Analytics] YouTube Analytics API v2 siap (full metrics)")
            else:
                logger.warning(
                    "[Analytics] yt-analytics scope tidak ditemukan di token. "
                    "Hanya basic stats (views/likes/comments). "
                    "Jalankan scripts/reauth_youtube.py untuk full analytics."
                )

        except Exception as e:
            logger.error(f"[Analytics] API client init gagal: {e}")

    def _load_credentials(self):
        """Load dan refresh OAuth credentials dari token_youtube.json."""
        if not os.path.exists(self._token_path):
            logger.error(f"[Analytics] Token tidak ditemukan: {self._token_path}")
            return None
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            with open(self._token_path) as f:
                token_data = json.load(f)

            creds = Credentials(
                token         = token_data.get("token"),
                refresh_token = token_data.get("refresh_token"),
                token_uri     = token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id     = token_data.get("client_id"),
                client_secret = token_data.get("client_secret"),
                scopes        = token_data.get("scopes", []),
            )

            if creds.expired and creds.refresh_token:
                logger.info("[Analytics] Refreshing token...")
                creds.refresh(Request())
                token_data["token"] = creds.token
                with open(self._token_path, "w") as f:
                    json.dump(token_data, f)
                logger.info("[Analytics] Token refreshed")

            return creds

        except Exception as e:
            logger.error(f"[Analytics] Load credentials gagal: {e}")
            return None

    # ── Public API ────────────────────────────────────────────────────────

    def fetch_and_store(self, tenant_id: str) -> dict:
        """
        Pull analytics untuk semua video tenant yang sudah > 48 jam dipublish.
        Upsert hasil ke tabel video_analytics.

        Returns:
            dict: {"fetched": int, "updated": int, "skipped": int,
                   "errors": int, "full_analytics": bool}
        """
        if not self._youtube:
            logger.error("[Analytics] YouTube client tidak tersedia — abort")
            return {"fetched": 0, "updated": 0, "skipped": 0, "errors": 0, "full_analytics": False}

        result = {"fetched": 0, "updated": 0, "skipped": 0, "errors": 0,
                  "full_analytics": self._has_analytics_scope}

        # 1. Ambil video yang perlu di-fetch
        videos = self._get_videos_to_fetch(tenant_id)
        if not videos:
            logger.info(f"[Analytics] Tidak ada video baru untuk di-fetch ({tenant_id})")
            return result

        logger.info(
            f"[Analytics] Fetching {len(videos)} videos | tenant={tenant_id} "
            f"| full_analytics={self._has_analytics_scope}"
        )

        # 2. Fetch + upsert per video
        for video in videos:
            result["fetched"] += 1
            try:
                metrics = self._fetch_video_metrics(video)
                if metrics:
                    self._upsert_analytics(tenant_id, video, metrics)
                    result["updated"] += 1
                else:
                    result["skipped"] += 1
                # Rate limit: jangan spam API
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"[Analytics] Error video {video.get('video_id')}: {e}")
                result["errors"] += 1

        logger.info(
            f"[Analytics] Done: {result['updated']} updated, "
            f"{result['skipped']} skipped, {result['errors']} errors"
        )
        return result

    # ── Data fetching ─────────────────────────────────────────────────────

    def _get_videos_to_fetch(self, tenant_id: str) -> list:
        """
        Ambil video dari Supabase yang:
        - Status = 'published'
        - Dipublish > 48 jam yang lalu (data tersedia di Analytics)
        - Belum di-fetch dalam 23 jam terakhir (hindari re-fetch berlebihan)
        """
        if not self._supabase:
            return []
        try:
            cutoff_publish = (
                datetime.now(timezone.utc) - timedelta(hours=self.MIN_HOURS_AFTER_PUBLISH)
            ).isoformat()

            result = (
                self._supabase
                .table("videos")
                .select("video_id, title, hook, niche, published_at")
                .eq("tenant_id", tenant_id)
                .eq("status", "published")
                .lt("published_at", cutoff_publish)
                .order("published_at", desc=True)
                .limit(self.MAX_VIDEOS_PER_RUN)
                .execute()
            )
            all_videos = result.data or []

            # Filter: skip yang sudah di-fetch baru-baru ini
            cutoff_fetch = (
                datetime.now(timezone.utc) - timedelta(hours=self.REFETCH_INTERVAL_HOURS)
            ).isoformat()

            recent_fetches = set()
            if all_videos:
                video_ids = [v["video_id"] for v in all_videos if v.get("video_id")]
                # Cek video_analytics: mana yang baru di-fetch
                fa = (
                    self._supabase
                    .table("video_analytics")
                    .select("video_id, fetched_at")
                    .in_("video_id", video_ids)
                    .gt("fetched_at", cutoff_fetch)
                    .execute()
                )
                recent_fetches = {r["video_id"] for r in (fa.data or [])}

            # Return hanya yang belum di-fetch baru-baru ini
            to_fetch = [v for v in all_videos if v.get("video_id") not in recent_fetches]
            logger.info(
                f"[Analytics] {len(all_videos)} published videos, "
                f"{len(recent_fetches)} recently fetched, "
                f"{len(to_fetch)} to fetch"
            )
            return to_fetch

        except Exception as e:
            logger.warning(f"[Analytics] _get_videos_to_fetch gagal: {e}")
            return []

    def _fetch_video_metrics(self, video: dict) -> Optional[dict]:
        """
        Fetch metrics untuk satu video.
        Selalu coba basic stats (Data API v3).
        Tambah full stats (Analytics API v2) jika scope tersedia.
        """
        video_id = video.get("video_id")
        if not video_id:
            return None

        metrics = {
            "views": 0, "likes": 0, "comments": 0,
            "watch_time_mins": 0, "avg_view_pct": 0.0,
            "ctr": 0.0, "subscriber_gain": 0,
            "has_full_analytics": False,
        }

        # ── Basic stats via Data API v3 ───────────────────────────────────
        try:
            response = (
                self._youtube.videos()
                .list(part="statistics", id=video_id)
                .execute()
            )
            items = response.get("items", [])
            if not items:
                logger.warning(f"[Analytics] Video tidak ditemukan di YouTube: {video_id}")
                return None

            stats = items[0].get("statistics", {})
            metrics["views"]    = int(stats.get("viewCount", 0))
            metrics["likes"]    = int(stats.get("likeCount", 0))
            metrics["comments"] = int(stats.get("commentCount", 0))
            logger.debug(
                f"[Analytics] {video_id}: views={metrics['views']} "
                f"likes={metrics['likes']} comments={metrics['comments']}"
            )
        except Exception as e:
            logger.warning(f"[Analytics] Data API gagal untuk {video_id}: {e}")
            return None

        # ── Full stats via Analytics API v2 ──────────────────────────────
        if self._has_analytics_scope and self._analytics:
            try:
                published_at = video.get("published_at", "")
                start_date   = published_at[:10] if published_at else "2020-01-01"
                end_date     = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                response = (
                    self._analytics.reports()
                    .query(
                        ids     = "channel==MINE",
                        startDate = start_date,
                        endDate   = end_date,
                        metrics = (
                            "views,estimatedMinutesWatched,"
                            "averageViewPercentage,impressionClickThroughRate,"
                            "subscribersGained"
                        ),
                        dimensions = "video",
                        filters    = f"video=={video_id}",
                        maxResults = 1,
                    )
                    .execute()
                )

                rows = response.get("rows", [])
                if rows:
                    # Column order matches metrics parameter order
                    # [video_id, views, estimatedMinutesWatched, averageViewPercentage,
                    #  impressionClickThroughRate, subscribersGained]
                    row = rows[0]
                    metrics["watch_time_mins"]   = int(row[2])
                    metrics["avg_view_pct"]      = round(float(row[3]), 1)
                    metrics["ctr"]               = round(float(row[4]) * 100, 2)  # decimal → pct
                    metrics["subscriber_gain"]   = int(row[5])
                    metrics["has_full_analytics"] = True
                    logger.debug(
                        f"[Analytics] {video_id}: "
                        f"watch={metrics['watch_time_mins']}min "
                        f"avg_view={metrics['avg_view_pct']}% "
                        f"ctr={metrics['ctr']}% "
                        f"subs={metrics['subscriber_gain']}"
                    )
            except Exception as e:
                err_str = str(e).lower()
                if "insufficient" in err_str or "forbidden" in err_str or "403" in err_str:
                    self._analytics_403_count += 1
                    logger.warning(
                        f"[Analytics] Analytics API 403 untuk {video_id} "
                        f"(mungkin data belum tersedia / video baru) — "
                        f"403 count: {self._analytics_403_count}"
                    )
                    # Disable scope hanya jika 3 video berturut-turut gagal (auth issue)
                    if self._analytics_403_count >= 3:
                        logger.error(
                            "[Analytics] 3x 403 berturut-turut — scope kemungkinan invalid. "
                            "Jalankan scripts/reauth_youtube.py"
                        )
                        self._has_analytics_scope = False
                else:
                    self._analytics_403_count = 0
                    logger.warning(f"[Analytics] Analytics API gagal untuk {video_id}: {e}")

        return metrics

    # ── Storage ───────────────────────────────────────────────────────────

    def _upsert_analytics(self, tenant_id: str, video: dict, metrics: dict):
        """Upsert row ke video_analytics. Fire-and-forget."""
        if not self._supabase:
            return
        try:
            row = {
                "video_id":           video.get("video_id"),
                "tenant_id":          tenant_id,
                "platform":           "youtube",
                "niche":              video.get("niche"),
                "title":              (video.get("title") or "")[:200],
                "hook_text":          (video.get("hook") or "")[:300],
                "views":              metrics["views"],
                "likes":              metrics["likes"],
                "comments":           metrics["comments"],
                "watch_time_mins":    metrics["watch_time_mins"],
                "avg_view_pct":       metrics["avg_view_pct"],
                "ctr":                metrics["ctr"],
                "subscriber_gain":    metrics["subscriber_gain"],
                "has_full_analytics": metrics["has_full_analytics"],
                "published_at":       video.get("published_at"),
                "fetched_at":         datetime.now(timezone.utc).isoformat(),
            }
            self._supabase.table("video_analytics").upsert(row).execute()
        except Exception as e:
            logger.warning(f"[Analytics] Upsert gagal untuk {video.get('video_id')}: {e}")
