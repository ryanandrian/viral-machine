import os
import time
import httpx
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, system_config

load_dotenv()

class VisualAssembler:
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
    PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"

    FALLBACK_QUERIES = {
        "universe_mysteries": ["space galaxy", "nebula stars", "earth from space", "telescope cosmos", "milky way"],
        "fun_facts": ["world map aerial", "crowd people", "nature timelapse", "science lab", "city aerial"],
        "dark_history": ["ancient ruins", "dark forest fog", "old castle", "historical monument", "cave"],
        "ocean_mysteries": ["deep ocean", "underwater coral", "ocean waves", "sea creature", "submarine"],
    }

    def _search_videos(self, query: str, per_page: int = 3) -> list:
        try:
            headers = {"Authorization": self.PEXELS_API_KEY}
            params = {"query": query, "per_page": per_page, "orientation": "portrait", "size": "medium"}
            with httpx.Client(timeout=15) as client:
                r = client.get(self.PEXELS_VIDEO_URL, headers=headers, params=params)
                if r.status_code == 200:
                    videos = r.json().get("videos", [])
                    results = []
                    for v in videos:
                        files = v.get("video_files", [])
                        best = None
                        for f in files:
                            w, h = f.get("width", 0), f.get("height", 0)
                            if h >= 720 and w <= h:
                                if best is None or f.get("height", 0) > best.get("height", 0):
                                    best = f
                        if best:
                            results.append({
                                "id": v.get("id"),
                                "duration": v.get("duration", 0),
                                "url": best.get("link", ""),
                                "width": best.get("width"),
                                "height": best.get("height"),
                                "query": query
                            })
                    return results
                elif r.status_code == 401:
                    logger.error("Pexels API key invalid")
                    return []
                else:
                    logger.warning(f"Pexels API returned {r.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Pexels search error: {e}")
            return []

    def _download_video(self, url: str, output_path: str) -> bool:
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                r = client.get(url)
                if r.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(r.content)
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    logger.info(f"Downloaded: {os.path.basename(output_path)} ({size_mb:.1f} MB)")
                    return True
        except Exception as e:
            logger.error(f"Download error: {e}")
        return False

    def _build_queries(self, script: dict, tenant_config: TenantConfig) -> list:
        queries = list(script.get("visual_suggestions", []))[:3]
        fallbacks = self.FALLBACK_QUERIES.get(tenant_config.niche, self.FALLBACK_QUERIES["universe_mysteries"])
        for fb in fallbacks:
            if fb not in queries:
                queries.append(fb)
        return queries[:5]

    def assemble(self, script: dict, tenant_config: TenantConfig, output_dir: str = "logs") -> list:
        queries = self._build_queries(script, tenant_config)
        logger.info(f"Searching footage: {queries[:3]}")

        clips_dir = os.path.join(output_dir, f"clips_{tenant_config.tenant_id}")
        os.makedirs(clips_dir, exist_ok=True)

        downloaded, used_ids = [], set()

        for query in queries:
            if len(downloaded) >= 6:
                break
            videos = self._search_videos(query)
            for video in videos:
                if len(downloaded) >= 6:
                    break
                vid_id = video.get("id")
                if vid_id in used_ids:
                    continue
                used_ids.add(vid_id)
                clip_path = os.path.join(clips_dir, f"clip_{len(downloaded)+1:02d}_{vid_id}.mp4")
                if os.path.exists(clip_path):
                    downloaded.append(clip_path)
                    continue
                if self._download_video(video["url"], clip_path):
                    downloaded.append(clip_path)
            time.sleep(0.5)

        logger.info(f"Assembly complete: {len(downloaded)} clips")
        return downloaded


if __name__ == "__main__":
    from src.intelligence.trend_radar import TrendRadar
    from src.intelligence.niche_selector import NicheSelector
    from src.intelligence.script_engine import ScriptEngine
    from src.intelligence.hook_optimizer import HookOptimizer
    from src.production.tts_engine import TTSEngine

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    logger.info("Step 1-4: Intelligence pipeline...")
    signals = TrendRadar().scan(tenant)
    topics = NicheSelector().select(signals, tenant)
    scripts = ScriptEngine().generate_batch(topics, tenant, count=1)
    optimized = HookOptimizer().optimize_batch(scripts, tenant)
    script = optimized[0]

    logger.info("Step 5: TTS audio...")
    audio_path = TTSEngine().generate(script, tenant)

    logger.info("Step 6: Visual assembly...")
    assembler = VisualAssembler()
    clips = assembler.assemble(script, tenant)

    print(f"\n{'='*60}")
    print(f"VISUAL ASSEMBLY COMPLETE")
    print(f"{'='*60}")
    print(f"Script : {script.get('title', '')}")
    print(f"Clips  : {len(clips)} downloaded")
    for i, clip in enumerate(clips, 1):
        size_mb = os.path.getsize(clip) / (1024*1024)
        print(f"  #{i}: {os.path.basename(clip)} ({size_mb:.1f} MB)")
    print(f"Audio  : {audio_path}")
    print(f"{'='*60}")
