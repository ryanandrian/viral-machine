"""
Pexels Visual Provider — stock footage gratis.
Provider default untuk semua tenant.

Fix v0.2:
- Filter by DURATION (prioritas utama) — ambil clip ≤ 15 detik
- Size limit 150MB sebagai hard ceiling safety net saja
- Streaming download + abort jika melebihi hard limit
- Fallback bertingkat: ≤15 detik → ≤30 detik → apapun
"""

import os
import time
from pathlib import Path

import httpx
from loguru import logger

from src.providers.visual.base import VisualProvider, VideoClip, VisualError


PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"

# Durasi target per clip — kita hanya butuh 5-8 detik per scene
DURATION_PRIORITY_1 = 15   # detik — ideal
DURATION_PRIORITY_2 = 30   # detik — masih OK
# Priority 3 = apapun yang tersedia

# Hard ceiling size — safety net, bukan filter utama
HARD_SIZE_LIMIT_MB = 150

# Fallback queries per niche
NICHE_FALLBACK_QUERIES = {
    "universe_mysteries": [
        "space galaxy", "nebula stars", "earth from space",
        "telescope cosmos", "milky way night sky",
    ],
    "fun_facts": [
        "world map aerial", "crowd people timelapse",
        "nature timelapse", "science lab", "city aerial drone",
    ],
    "dark_history": [
        "ancient ruins", "dark forest fog", "old castle",
        "historical monument", "abandoned building",
    ],
    "ocean_mysteries": [
        "deep ocean underwater", "coral reef", "ocean waves",
        "sea creature", "underwater light rays",
    ],
}


class PexelsProvider(VisualProvider):
    """
    Pexels stock footage — gratis, tidak butuh biaya per request.
    Filter utama: durasi clip (bukan ukuran file).
    Size limit hanya sebagai safety net.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = (
            config.get("visual_api_key")
            or os.getenv("PEXELS_API_KEY", "")
        )
        if not self.api_key:
            raise VisualError(
                "Pexels membutuhkan API key. "
                "Set visual_api_key di tenant_configs atau PEXELS_API_KEY di .env."
            )
        self.niche = config.get("niche", "universe_mysteries")
        # Gunakan hard limit jika config lebih besar dari HARD_SIZE_LIMIT_MB
        self.max_clip_size_mb = min(
            config.get("visual_max_clip_mb", HARD_SIZE_LIMIT_MB),
            HARD_SIZE_LIMIT_MB
        )

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    async def fetch_clips(
        self,
        keywords: list[str],
        count: int,
        output_dir: Path,
    ) -> list[VideoClip]:
        """
        Cari dan download clips dari Pexels.
        Filter utama: durasi ≤ 15 detik (fallback bertingkat).
        Size limit 150MB hanya sebagai safety net.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded: list[VideoClip] = []
        used_ids: set = set()

        for query in keywords:
            if len(downloaded) >= count:
                break

            # Ambil lebih banyak kandidat per query untuk filtering durasi
            videos = self._search_videos(query, per_page=5)

            # Sort by durasi — prioritaskan clip pendek
            videos = self._sort_by_duration_priority(videos)

            for video in videos:
                if len(downloaded) >= count:
                    break

                vid_id = video.get("id")
                if vid_id in used_ids:
                    continue
                used_ids.add(vid_id)

                clip_path = output_dir / f"clip_{len(downloaded)+1:02d}_{vid_id}.mp4"

                # Jika sudah ada dari run sebelumnya
                if clip_path.exists():
                    size_mb = clip_path.stat().st_size / (1024 * 1024)
                    if size_mb <= self.max_clip_size_mb:
                        downloaded.append(VideoClip(
                            path=clip_path,
                            duration=float(video.get("duration", 0)),
                            width=video.get("width", 0),
                            height=video.get("height", 0),
                            file_size_mb=round(size_mb, 1),
                            source_url=video.get("url", ""),
                            provider=self.provider_name,
                        ))
                        logger.info(
                            f"[Pexels] Reuse cached: {clip_path.name} "
                            f"({size_mb:.1f}MB, {video.get('duration', 0)}s)"
                        )
                        continue

                clip = self._download_with_size_check(video, clip_path)
                if clip:
                    downloaded.append(clip)

            time.sleep(0.5)

        logger.info(
            f"[Pexels] {len(downloaded)}/{count} clips downloaded"
        )
        return downloaded

    def extract_keywords_from_script(self, script: dict, niche: str) -> list[str]:
        """
        Bangun keyword list untuk pencarian Pexels:
        1. visual_suggestions dari script (AI-generated, paling relevan)
        2. Fallback queries niche
        """
        queries: list[str] = []

        visual_suggestions = script.get("visual_suggestions", [])
        if isinstance(visual_suggestions, list):
            queries.extend([q for q in visual_suggestions if q][:3])

        fallbacks = NICHE_FALLBACK_QUERIES.get(niche, NICHE_FALLBACK_QUERIES["universe_mysteries"])
        for fb in fallbacks:
            if fb not in queries:
                queries.append(fb)

        return queries[:5]

    @property
    def provider_name(self) -> str:
        return "pexels"

    @property
    def is_ai_generated(self) -> bool:
        return False

    @property
    def is_enabled(self) -> bool:
        return True

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _search_videos(self, query: str, per_page: int = 5) -> list[dict]:
        """Cari video di Pexels."""
        try:
            headers = {"Authorization": self.api_key}
            params  = {
                "query":       query,
                "per_page":    per_page,
                "orientation": "portrait",
                "size":        "medium",
            }
            with httpx.Client(timeout=15) as client:
                r = client.get(PEXELS_VIDEO_URL, headers=headers, params=params)

            if r.status_code == 200:
                results = []
                for v in r.json().get("videos", []):
                    best = self._pick_best_file(v)
                    if best:
                        best["duration"] = v.get("duration", 0)
                        results.append(best)
                return results
            elif r.status_code == 401:
                raise VisualError("Pexels API key tidak valid.")
            elif r.status_code == 429:
                logger.warning("[Pexels] Rate limit hit, menunggu 5 detik...")
                time.sleep(5)
                return []
            else:
                logger.warning(f"[Pexels] API returned {r.status_code} for '{query}'")
                return []

        except VisualError:
            raise
        except Exception as e:
            logger.error(f"[Pexels] Search error: {e}")
            return []

    def _sort_by_duration_priority(self, videos: list[dict]) -> list[dict]:
        """
        Sort videos berdasarkan prioritas durasi:
          Priority 1: ≤ 15 detik (ideal)
          Priority 2: ≤ 30 detik (masih OK)
          Priority 3: > 30 detik (last resort)
        Dalam setiap priority, sort by durasi ascending.
        """
        p1 = [v for v in videos if v.get("duration", 999) <= DURATION_PRIORITY_1]
        p2 = [v for v in videos if DURATION_PRIORITY_1 < v.get("duration", 999) <= DURATION_PRIORITY_2]
        p3 = [v for v in videos if v.get("duration", 999) > DURATION_PRIORITY_2]

        return (
            sorted(p1, key=lambda x: x.get("duration", 999)) +
            sorted(p2, key=lambda x: x.get("duration", 999)) +
            sorted(p3, key=lambda x: x.get("duration", 999))
        )

    def _pick_best_file(self, video: dict) -> dict | None:
        """
        Dari semua video_files, pilih yang:
        - Portrait (height > width)
        - Height >= 720p
        - Resolusi tertinggi yang memenuhi syarat
        """
        best = None
        for f in video.get("video_files", []):
            w, h = f.get("width", 0), f.get("height", 0)
            if h >= 720 and w <= h:
                if best is None or h > best.get("height", 0):
                    best = f
        if not best:
            return None
        return {
            "id":     video.get("id"),
            "url":    best.get("link", ""),
            "width":  best.get("width", 0),
            "height": best.get("height", 0),
        }

    def _check_remote_size_mb(self, url: str) -> float | None:
        """Cek ukuran file remote via HEAD request."""
        try:
            with httpx.Client(timeout=10) as client:
                r = client.head(url, follow_redirects=True)
            content_length = r.headers.get("content-length")
            if content_length:
                return int(content_length) / (1024 * 1024)
            return None
        except Exception:
            return None

    def _download_with_size_check(
        self,
        video: dict,
        output_path: Path,
    ) -> VideoClip | None:
        """
        Download video dengan:
        1. HEAD request cek size (safety net)
        2. Streaming download + abort jika melebihi hard limit
        """
        url      = video.get("url", "")
        duration = video.get("duration", 0)
        if not url:
            return None

        # Log durasi clip yang akan didownload
        priority = (
            "P1 ✅" if duration <= DURATION_PRIORITY_1
            else "P2 ⚠️" if duration <= DURATION_PRIORITY_2
            else "P3 ❗"
        )
        logger.info(
            f"[Pexels] Downloading {video.get('id')} — "
            f"{duration}s {priority}"
        )

        # HEAD check — safety net
        remote_size = self._check_remote_size_mb(url)
        if remote_size is not None and remote_size > self.max_clip_size_mb:
            logger.warning(
                f"[Pexels] Skip {video.get('id')} — "
                f"{remote_size:.1f}MB > hard limit {self.max_clip_size_mb}MB"
            )
            return None

        # Streaming download
        try:
            downloaded_bytes = 0
            limit_bytes      = self.max_clip_size_mb * 1024 * 1024

            with httpx.Client(timeout=60, follow_redirects=True) as client:
                with client.stream("GET", url) as r:
                    if r.status_code != 200:
                        logger.warning(f"[Pexels] HTTP {r.status_code}")
                        return None

                    with open(output_path, "wb") as f:
                        for chunk in r.iter_bytes(chunk_size=1024 * 256):
                            downloaded_bytes += len(chunk)
                            if downloaded_bytes > limit_bytes:
                                logger.warning(
                                    f"[Pexels] Abort {video.get('id')} — "
                                    f"exceeded {self.max_clip_size_mb}MB"
                                )
                                output_path.unlink(missing_ok=True)
                                return None
                            f.write(chunk)

            size_mb = downloaded_bytes / (1024 * 1024)
            logger.info(
                f"[Pexels] Downloaded: {output_path.name} "
                f"({size_mb:.1f}MB, {duration}s)"
            )
            return VideoClip(
                path=output_path,
                duration=float(duration),
                width=video.get("width", 0),
                height=video.get("height", 0),
                file_size_mb=round(size_mb, 1),
                source_url=url,
                provider=self.provider_name,
            )

        except Exception as e:
            logger.error(f"[Pexels] Download error: {e}")
            output_path.unlink(missing_ok=True)
            return None
