import os
import json
import time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from src.intelligence.config import TenantConfig, system_config
from src.intelligence.trend_radar import TrendRadar
from src.intelligence.niche_selector import NicheSelector
from src.intelligence.script_engine import ScriptEngine
from src.intelligence.hook_optimizer import HookOptimizer
from src.production.tts_engine import TTSEngine
from src.production.visual_assembler import VisualAssembler
from src.production.video_renderer import VideoRenderer
from src.distribution.youtube_publisher import YouTubePublisher

load_dotenv()

class Pipeline:
    """
    Master controller — menjalankan full pipeline dari tren hingga video live.
    Multi-tenant ready. Setiap run menghasilkan satu video siap publish.
    """

    def __init__(self):
        self.trend_radar = TrendRadar()
        self.niche_selector = NicheSelector()
        self.script_engine = ScriptEngine()
        self.hook_optimizer = HookOptimizer()
        self.tts_engine = TTSEngine()
        self.visual_assembler = VisualAssembler()
        self.video_renderer = VideoRenderer()
        self.youtube_publisher = YouTubePublisher()

    def run(self, tenant_config: TenantConfig, publish: bool = True) -> dict:
        """
        Jalankan full pipeline untuk satu tenant.
        publish=True  → upload ke YouTube setelah render
        publish=False → hanya render, tidak upload (untuk testing)
        """
        run_id = f"{tenant_config.tenant_id}_{int(time.time())}"
        start_time = time.time()

        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE START | run_id: {run_id}")
        logger.info(f"Tenant: {tenant_config.tenant_id} | Niche: {tenant_config.niche}")
        logger.info(f"{'='*60}")

        result = {
            "run_id": run_id,
            "tenant_id": tenant_config.tenant_id,
            "niche": tenant_config.niche,
            "started_at": datetime.now().isoformat(),
            "steps": {},
            "status": "running",
            "video_path": None,
            "published": {}
        }

        try:
            # ── STEP 1: Trend Scan ──────────────────────────────────
            logger.info("STEP 1/7 | Scanning trends...")
            signals = self.trend_radar.scan(tenant_config)
            total_signals = sum(len(v) for v in signals.values() if isinstance(v, list))
            result["steps"]["trend_scan"] = {"status": "ok", "signals": total_signals}
            logger.info(f"STEP 1 DONE | {total_signals} signals collected")

            # ── STEP 2: Topic Selection ─────────────────────────────
            logger.info("STEP 2/7 | Selecting best topic...")
            topics = self.niche_selector.select(signals, tenant_config)
            if not topics:
                raise Exception("No topics selected")
            result["steps"]["topic_selection"] = {"status": "ok", "topics": len(topics), "top": topics[0]["topic"]}
            logger.info(f"STEP 2 DONE | Top topic: {topics[0]['topic'][:50]} (score: {topics[0]['viral_score']})")

            # ── STEP 3: Script Generation ───────────────────────────
            logger.info("STEP 3/7 | Generating script...")
            scripts = self.script_engine.generate_batch(topics, tenant_config, count=1)
            if not scripts:
                raise Exception("Script generation failed")
            result["steps"]["script"] = {"status": "ok", "title": scripts[0].get("title", "")}
            logger.info(f"STEP 3 DONE | {scripts[0].get('word_count', 0)} words")

            # ── STEP 4: Hook Optimization ───────────────────────────
            logger.info("STEP 4/7 | Optimizing hook...")
            optimized = self.hook_optimizer.optimize_batch(scripts, tenant_config)
            if not optimized:
                raise Exception("Hook optimization failed")
            script = optimized[0]
            winner_score = script.get("hook_data", {}).get("winner", {}).get("scroll_stop_power", 0)
            result["steps"]["hook"] = {"status": "ok", "score": winner_score, "hook": script.get("hook", "")}
            logger.info(f"STEP 4 DONE | Hook [{winner_score}/100]: {script.get('hook', '')[:60]}")

            # ── STEP 5: TTS Audio ───────────────────────────────────
            logger.info("STEP 5/7 | Generating TTS audio...")
            audio_path = self.tts_engine.generate(script, tenant_config)
            if not audio_path:
                raise Exception("TTS generation failed")
            result["steps"]["tts"] = {"status": "ok", "path": audio_path}
            logger.info(f"STEP 5 DONE | Audio: {audio_path}")

            # ── STEP 6: Visual Assembly ─────────────────────────────
            logger.info("STEP 6/7 | Assembling visuals...")
            clips = self.visual_assembler.assemble(script, tenant_config)
            if not clips:
                raise Exception("Visual assembly failed — no clips downloaded")
            result["steps"]["visuals"] = {"status": "ok", "clips": len(clips)}
            logger.info(f"STEP 6 DONE | {len(clips)} clips ready")

            # ── STEP 7: Video Render ────────────────────────────────
            logger.info("STEP 7/7 | Rendering final video...")
            video_path = self.video_renderer.render(script, audio_path, clips, tenant_config)
            if not video_path:
                raise Exception("Video rendering failed")
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            result["steps"]["render"] = {"status": "ok", "path": video_path, "size_mb": round(size_mb, 1)}
            result["video_path"] = video_path
            logger.info(f"STEP 7 DONE | Video: {video_path} ({size_mb:.1f} MB)")

            # ── PUBLISH ─────────────────────────────────────────────
            if publish:
                logger.info("PUBLISHING | Uploading to YouTube Shorts...")
                yt_result = self.youtube_publisher.publish(video_path, script, tenant_config)
                result["published"]["youtube"] = yt_result
                if yt_result.get("video_id"):
                    logger.info(f"PUBLISHED | YouTube: {yt_result['url']}")
                else:
                    logger.warning(f"YouTube publish failed: {yt_result.get('error', 'unknown')}")
            else:
                logger.info("PUBLISH SKIPPED | publish=False")

            elapsed = round(time.time() - start_time, 1)
            result["status"] = "success"
            result["completed_at"] = datetime.now().isoformat()
            result["elapsed_seconds"] = elapsed

            logger.info(f"{'='*60}")
            logger.info(f"PIPELINE COMPLETE | {elapsed}s | Status: SUCCESS")
            if result["published"].get("youtube", {}).get("url"):
                logger.info(f"Live at: {result['published']['youtube']['url']}")
            logger.info(f"{'='*60}")

        except Exception as e:
            elapsed = round(time.time() - start_time, 1)
            result["status"] = "failed"
            result["error"] = str(e)
            result["elapsed_seconds"] = elapsed
            logger.error(f"PIPELINE FAILED | {elapsed}s | Error: {e}")

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/pipeline_{run_id}.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result


if __name__ == "__main__":
    import sys
    publish_flag = "--publish" in sys.argv

    tenant = TenantConfig(tenant_id="ryan_andrian", niche="universe_mysteries")

    print(f"\n{'='*60}")
    print(f"MESINVIRAL — AUTOMATED PIPELINE")
    print(f"{'='*60}")
    print(f"Tenant  : {tenant.tenant_id}")
    print(f"Niche   : {tenant.niche}")
    print(f"Publish : {publish_flag}")
    print(f"{'='*60}\n")

    pipeline = Pipeline()
    result = pipeline.run(tenant, publish=publish_flag)

    print(f"\n{'='*60}")
    print(f"PIPELINE RESULT")
    print(f"{'='*60}")
    print(f"Status  : {result['status'].upper()}")
    print(f"Time    : {result.get('elapsed_seconds', 0)}s")
    if result.get("video_path"):
        size = os.path.getsize(result["video_path"]) / (1024*1024)
        print(f"Video   : {result['video_path']} ({size:.1f} MB)")
    if result.get("published", {}).get("youtube", {}).get("url"):
        print(f"YouTube : {result['published']['youtube']['url']}")
    if result.get("error"):
        print(f"Error   : {result['error']}")
    print(f"{'='*60}")
