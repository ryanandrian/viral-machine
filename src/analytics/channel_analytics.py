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

    def __init__(self, token_path: str = None, tenant_id: str = None, channel_id: str = None):
        """
        token_path: eksplisit path ke token file (opsional)
        tenant_id:  jika diisi, resolve path via konvensi tokens/{tenant_id}.json
        channel_id: jika diisi → creds PER-CHANNEL (channel_credentials); else fallback per-tenant.
        Fallback:   token_youtube.json (backward compatible)
        """
        self._tenant_id  = tenant_id
        self._channel_id = channel_id   # per-channel creds (channel_credentials, migr 0060)
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
        """OAuth credentials — DB-first (tenant_credentials, Phase 4.4) → fallback file."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            token_data = None
            if self._tenant_id:
                try:
                    from src.utils.tenant_credentials import load_google_credentials
                    token_data = load_google_credentials(self._tenant_id, channel_id=self._channel_id)
                except Exception as e:
                    logger.warning(f"[Analytics] DB creds gagal ({e}) — coba file")
            if not token_data:
                if not os.path.exists(self._token_path):
                    logger.error(f"[Analytics] OAuth tak ada (tenant_credentials & file {self._token_path})")
                    return None
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
                # Simpan access_token baru: DB (tenant_credentials) bila ada tenant; else file.
                if self._tenant_id:
                    try:
                        from src.utils.tenant_credentials import save_google_access_token
                        save_google_access_token(self._tenant_id, creds.token, channel_id=self._channel_id)
                    except Exception as e:
                        logger.warning(f"[Analytics] simpan token DB gagal (non-fatal): {e}")
                elif os.path.exists(self._token_path):
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

    def sync_channel_meta(self, tenant_id: str, channel_id: str = None) -> dict:
        """FAIL-SOFT: sinkronkan metadata channel dari YouTube (mine=True via OAuth) → tabel channels:
          • channel_name  = JUDUL channel YouTube (WAJIB sama dgn YouTube → anti-confuse tenant)
          • platform_channel_id = channel id YouTube (UC...)
          • subscriber_count   = jumlah subscriber (skip jika tersembunyi)
        Sumber kebenaran nama = YouTube. Terisolasi: gagal di sini TIDAK mengganggu produksi/fetch lain.
        PER-CHANNEL (migr 0060): scope update ke channels.id=channel_id (tiap channel pakai OAuth-nya
        sendiri → mine=true = channel itu). Tanpa channel_id → tenant-wide (legacy 1-channel)."""
        if not self._youtube or not self._supabase:
            return {"ok": False, "reason": "no_client"}
        try:
            resp = self._youtube.channels().list(part="snippet,statistics", mine=True).execute()
            items = resp.get("items", [])
            if not items:
                return {"ok": False, "reason": "no_channel"}
            it = items[0]
            uc_id = it.get("id")
            title = (it.get("snippet") or {}).get("title")
            stats = it.get("statistics") or {}
            patch = {"updated_at": datetime.now(timezone.utc).isoformat()}
            if title:
                patch["channel_name"] = title
            if uc_id:
                patch["platform_channel_id"] = uc_id
            if not stats.get("hiddenSubscriberCount"):
                patch["subscriber_count"] = int(stats.get("subscriberCount", 0))
                patch["subscriber_count_at"] = datetime.now(timezone.utc).isoformat()
            ch_id = channel_id or self._channel_id
            q = self._supabase.table("channels").update(patch).eq("tenant_id", tenant_id)
            if ch_id:
                q = q.eq("id", ch_id)   # multi-channel: HANYA channel ini (bukan semua channel tenant)
            q.execute()
            logger.info(f"[Analytics] sync channel meta tenant={tenant_id} ch={ch_id} name='{title}' id={uc_id} subs={patch.get('subscriber_count')}")
            return {"ok": True, "name": title, "channel_id": uc_id, "subscribers": patch.get("subscriber_count")}
        except Exception as e:
            logger.warning(f"[Analytics] sync channel meta gagal tenant={tenant_id}: {e}")
            return {"ok": False, "reason": str(e)}

    # ── Data fetching ─────────────────────────────────────────────────────

    def _get_videos_to_fetch(self, tenant_id: str) -> list:
        """
        Pilih video untuk di-fetch — ROTASI berbasis kesegaran (BUKAN hanya 50 terbaru).
        Kriteria: status='published', dipublish > 48 jam.
        Prioritas: video yang paling BASI (last fetched_at ASC; belum pernah di-fetch lebih dulu) →
        semua video ter-refresh bergiliran tiap run (cegah video lama beku snapshot selamanya).
        Skip yang sudah di-fetch < REFETCH_INTERVAL_HOURS. Ambil MAX_VIDEOS_PER_RUN per run.
        """
        if not self._supabase:
            return []
        try:
            cutoff_publish = (
                datetime.now(timezone.utc) - timedelta(hours=self.MIN_HOURS_AFTER_PUBLISH)
            ).isoformat()
            # SEMUA video eligible (cap aman 1000), bukan hanya 50 terbaru.
            result = (
                self._supabase.table("videos")
                .select("video_id, title, hook, niche, published_at")
                .eq("tenant_id", tenant_id).eq("status", "published")
                .lt("published_at", cutoff_publish)
                .order("published_at", desc=True).limit(1000).execute()
            )
            all_videos = [v for v in (result.data or []) if v.get("video_id")]
            if not all_videos:
                return []

            # last fetched_at per video (chunk IN agar URL aman utk channel besar)
            cutoff_fetch = (
                datetime.now(timezone.utc) - timedelta(hours=self.REFETCH_INTERVAL_HOURS)
            ).isoformat()
            ids = [v["video_id"] for v in all_videos]
            last_fetch: dict = {}
            for i in range(0, len(ids), 150):
                chunk = ids[i:i + 150]
                fa = (self._supabase.table("video_analytics")
                      .select("video_id, fetched_at").in_("video_id", chunk).execute())
                for r in (fa.data or []):
                    vid, ft = r["video_id"], r.get("fetched_at")
                    if ft and (vid not in last_fetch or ft > last_fetch[vid]):
                        last_fetch[vid] = ft

            # buang yang masih segar (<23j); sisanya urut PALING BASI dulu (never-fetched = "" → terdepan)
            candidates = [v for v in all_videos if last_fetch.get(v["video_id"], "") <= cutoff_fetch]
            candidates.sort(key=lambda v: last_fetch.get(v["video_id"], ""))
            to_fetch = candidates[:self.MAX_VIDEOS_PER_RUN]
            logger.info(
                f"[Analytics] {len(all_videos)} eligible, "
                f"{len(all_videos) - len(candidates)} fresh(<{self.REFETCH_INTERVAL_HOURS}h), "
                f"fetch {len(to_fetch)} (stalest-first rotation)"
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
                        # CATATAN: impressionClickThroughRate DIBUANG — metrik impression
                        # tidak tersedia pada granularitas per-video (dimensions=video) →
                        # Analytics API tolak 400 invalid yang men-poison SELURUH query
                        # (retensi averageViewPercentage ikut hilang). CTR per-video tak
                        # bisa via API path ini → biarkan ctr=0 jujur (FE tampil "—").
                        metrics = (
                            "views,estimatedMinutesWatched,"
                            "averageViewPercentage,subscribersGained"
                        ),
                        dimensions = "video",
                        filters    = f"video=={video_id}",
                        maxResults = 1,
                    )
                    .execute()
                )

                rows = response.get("rows", [])
                if rows:
                    # Column order matches metrics parameter order. dimensions=video →
                    # [video_id, views, estimatedMinutesWatched, averageViewPercentage,
                    #  subscribersGained]. ctr TIDAK di-fetch (lihat catatan di query).
                    row = rows[0]
                    metrics["watch_time_mins"]   = int(row[2])
                    metrics["avg_view_pct"]      = round(float(row[3]), 1)
                    metrics["subscriber_gain"]   = int(row[4])
                    metrics["has_full_analytics"] = True
                    logger.debug(
                        f"[Analytics] {video_id}: "
                        f"watch={metrics['watch_time_mins']}min "
                        f"avg_view={metrics['avg_view_pct']}% "
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
