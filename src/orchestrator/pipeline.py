"""
Master Pipeline Controller — MesinViral.com
Menjalankan full pipeline dari tren hingga video live di platform.

v0.2 Changes:
- Baca config dari Supabase via TenantConfigManager (provider-agnostic)
- Integrasi StorageCleaner — hapus clips setelah render, video setelah upload
- Siap untuk supabase_writer (diimplementasikan di Fase 7 s71)
- Fallback ke TenantConfig lama jika TenantConfigManager gagal
"""

import os
import random
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from src.intelligence.config import TenantConfig, system_config
from src.intelligence.trend_radar import TrendRadar
from src.intelligence.niche_selector import NicheSelector
from src.intelligence.script_engine import ScriptEngine
from src.intelligence.hook_optimizer import HookOptimizer
from src.production.tts_engine import TTSEngine
from src.production.visual_assembler import VisualAssembler
from src.production.video_renderer import VideoRenderer
from src.distribution.youtube_publisher import YouTubePublisher
from src.utils.storage_cleaner import StorageCleaner

load_dotenv()


class Pipeline:
    """
    Master controller — menjalankan full pipeline dari tren hingga video live.
    Config-driven: baca provider dan settings dari Supabase tenant_configs.
    """

    def __init__(self):
        self.trend_radar       = TrendRadar()
        self.niche_selector    = NicheSelector()
        self.script_engine     = ScriptEngine()
        self.hook_optimizer    = HookOptimizer()
        self.tts_engine        = TTSEngine()
        self.visual_assembler  = VisualAssembler()
        self.video_renderer    = VideoRenderer()
        self.youtube_publisher = YouTubePublisher()
        self.storage_cleaner   = StorageCleaner(base_dir="logs")

    def _load_tenant_run_config(self, tenant_config: TenantConfig):
        """
        Load TenantRunConfig dari Supabase.
        Fallback: gunakan tenant_config yang diberikan jika gagal.
        """
        try:
            from src.config.tenant_config import load_tenant_config
            run_config = load_tenant_config(tenant_config.tenant_id)
            logger.info(
                f"[Pipeline] Config loaded from Supabase: "
                f"tts={run_config.tts_provider} | "
                f"visual={run_config.visual_provider} | "
                f"llm={run_config.llm_model}"
            )
            return run_config
        except Exception as e:
            logger.warning(
                f"[Pipeline] TenantConfigManager gagal ({e}) — "
                f"pakai TenantConfig default"
            )
            return None

    def run(self, tenant_config: TenantConfig, publish: bool = True) -> dict:
        """
        Jalankan full pipeline untuk satu tenant.

        Args:
            tenant_config: Config tenant (tenant_id + niche minimum)
            publish:       True → upload ke platform setelah render
        """
        run_id     = f"{tenant_config.tenant_id}_{int(time.time())}"
        start_time = time.time()

        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE START | run_id: {run_id}")
        logger.info(f"Tenant: {tenant_config.tenant_id} | Niche: {tenant_config.niche}")
        logger.info(f"{'='*60}")

        # Load config dari Supabase
        run_config = self._load_tenant_run_config(tenant_config)

        result = {
            "run_id":       run_id,
            "tenant_id":    tenant_config.tenant_id,
            "niche":        tenant_config.niche,
            "started_at":   datetime.now().isoformat(),
            "steps":        {},
            "status":       "running",
            "video_path":   None,
            "published":    {},
            "storage":      {},
        }

        video_path = None

        try:
            # ── STEP 1: Trend Scan ──────────────────────────────────
            logger.info("STEP 1/7 | Scanning trends...")
            signals       = self.trend_radar.scan(tenant_config)
            total_signals = sum(len(v) for v in signals.values() if isinstance(v, list))
            result["steps"]["trend_scan"] = {"status": "ok", "signals": total_signals}
            logger.info(f"STEP 1 DONE | {total_signals} signals collected")

            # ── STEP 2: Topic Selection ─────────────────────────────
            logger.info("STEP 2/7 | Selecting best topic...")
            topics = self.niche_selector.select(signals, tenant_config)
            if not topics:
                raise Exception("No topics selected")
            result["steps"]["topic_selection"] = {
                "status": "ok",
                "topics": len(topics),
                "top":    topics[0]["topic"]
            }
            logger.info(
                f"STEP 2 DONE | Top topic: {topics[0]['topic'][:50]} "
                f"(score: {topics[0]['viral_score']})"
            )

            # ── STEP 3: Script Generation ───────────────────────────
            logger.info("STEP 3/7 | Generating script...")
            scripts = self.script_engine.generate_batch(topics, tenant_config, count=1)
            if not scripts:
                raise Exception("Script generation failed")
            result["steps"]["script"] = {
                "status": "ok",
                "title":  scripts[0].get("title", "")
            }
            logger.info(f"STEP 3 DONE | {scripts[0].get('word_count', 0)} words")

            # ── STEP 4: Hook Optimization ───────────────────────────
            logger.info("STEP 4/7 | Optimizing hook...")
            optimized = self.hook_optimizer.optimize_batch(scripts, tenant_config)
            if not optimized:
                raise Exception("Hook optimization failed")
            script       = optimized[0]
            winner_score = script.get("hook_data", {}).get("winner", {}).get("scroll_stop_power", 0)
            result["steps"]["hook"] = {
                "status": "ok",
                "score":  winner_score,
                "hook":   script.get("hook", "")
            }
            logger.info(f"STEP 4 DONE | Hook [{winner_score}/100]: {script.get('hook', '')[:60]}")

            # ── STEP 5: TTS Audio ───────────────────────────────────
            logger.info("STEP 5/7 | Generating TTS audio...")
            tts_result = self.tts_engine.generate(script, tenant_config)
            audio_path, word_timestamps = (
                tts_result if isinstance(tts_result, tuple)
                else (tts_result, [])
            )
            if not audio_path:
                raise Exception("TTS generation failed")
            ts_info = f"{len(word_timestamps)} word timestamps" if word_timestamps else "no timestamps (estimasi)"
            result["steps"]["tts"] = {"status": "ok", "path": audio_path, "timestamps": len(word_timestamps)}
            logger.info(f"STEP 5 DONE | Audio: {audio_path} | {ts_info}")

            # ── STEP 6: Visual Assembly ─────────────────────────────
            logger.info("STEP 6/7 | Assembling visuals...")
            audio_duration = self.tts_engine.get_duration(audio_path)
            logger.info(f"[Pipeline] Audio duration: {audio_duration:.1f}s — scaling clips")
            clips = self.visual_assembler.assemble(script, tenant_config, audio_duration=audio_duration)
            if not clips:
                raise Exception("Visual assembly failed — no clips downloaded")
            result["steps"]["visuals"] = {"status": "ok", "clips": len(clips)}
            logger.info(f"STEP 6 DONE | {len(clips)} clips ready")

            # ── STEP 7: Video Render ────────────────────────────────
            logger.info("STEP 7/7 | Rendering final video...")
            video_path = self.video_renderer.render(
                script, audio_path, clips, tenant_config,
                word_timestamps=word_timestamps
            )
            if not video_path:
                raise Exception("Video rendering failed")
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            result["steps"]["render"] = {
                "status":  "ok",
                "path":    video_path,
                "size_mb": round(size_mb, 1)
            }
            result["video_path"] = video_path
            logger.info(f"STEP 7 DONE | Video: {video_path} ({size_mb:.1f} MB)")

            # ── CLEANUP: Hapus clips mentah setelah render ──────────
            clips_cleaned = self.storage_cleaner.cleanup_clips(
                tenant_id=tenant_config.tenant_id,
                video_path=video_path,
            )
            result["storage"]["clips_cleaned"] = clips_cleaned

            # ── PUBLISH ─────────────────────────────────────────────
            published_platforms = []

            if publish:
                # YouTube
                logger.info("PUBLISHING | Uploading to YouTube Shorts...")
                yt_result = self.youtube_publisher.publish(video_path, script, tenant_config)
                result["published"]["youtube"] = yt_result

                if yt_result.get("video_id"):
                    published_platforms.append("youtube")
                    logger.info(f"PUBLISHED | YouTube: {yt_result['url']}")

                    # ── Fase 7 placeholder: simpan metadata ke Supabase ──
                    # supabase_writer akan diimplementasikan di s71
                    # self._write_to_supabase(run_id, script, yt_result, tenant_config)

                else:
                    logger.warning(
                        f"YouTube publish failed: {yt_result.get('error', 'unknown')}"
                    )

                # TikTok — akan ditambah di Fase 8
                # Instagram — akan ditambah di Fase 8

                # ── CLEANUP: Hapus video final setelah semua platform upload ──
                active_platforms = (
                    run_config.publish_platforms
                    if run_config
                    else ["youtube"]
                )
                video_cleaned = self.storage_cleaner.cleanup_video(
                    video_path=video_path,
                    published_platforms=published_platforms,
                    required_platforms=active_platforms,
                )
                result["storage"]["video_cleaned"] = video_cleaned

            else:
                logger.info("PUBLISH SKIPPED | publish=False")

            # ── CLEANUP: Log lama ───────────────────────────────────
            log_cleanup = self.storage_cleaner.cleanup_old_logs(
                max_age_days_json=30,
                max_age_days_audio=7,
            )
            result["storage"]["log_cleanup"] = log_cleanup

            # ── Storage report ──────────────────────────────────────
            storage_report = self.storage_cleaner.report_storage()
            result["storage"]["usage"] = storage_report
            logger.info(
                f"[Storage] Usage after cleanup: "
                f"{storage_report.get('total_mb', 0):.1f}MB"
            )

            elapsed        = round(time.time() - start_time, 1)
            result["status"]        = "success"
            result["completed_at"]  = datetime.now().isoformat()
            result["elapsed_seconds"] = elapsed

            logger.info(f"{'='*60}")
            logger.info(f"PIPELINE COMPLETE | {elapsed}s | Status: SUCCESS")
            if result["published"].get("youtube", {}).get("url"):
                logger.info(f"Live at: {result['published']['youtube']['url']}")
            logger.info(f"{'='*60}")

        except Exception as e:
            elapsed          = round(time.time() - start_time, 1)
            result["status"] = "failed"
            result["error"]  = str(e)
            result["elapsed_seconds"] = elapsed
            logger.error(f"PIPELINE FAILED | {elapsed}s | Error: {e}")

            # Cleanup clips meski pipeline gagal
            # (jika render sudah selesai sebelum error)
            if video_path and Path(video_path).exists():
                self.storage_cleaner.cleanup_clips(
                    tenant_id=tenant_config.tenant_id,
                    video_path=video_path,
                )

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/pipeline_{run_id}.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result


if __name__ == "__main__":
    import sys
    publish_flag = "--publish" in sys.argv

    # Config-driven niche — tidak ada hardcode, baca dari Supabase
    try:
        from src.config.tenant_config import load_tenant_config
        _rc   = load_tenant_config("ryan_andrian")
        _mode = getattr(_rc, "niche_mode", "fixed") or "fixed"
        _pool = list(getattr(_rc, "niche_pool", None) or ["universe_mysteries"])
        if _mode == "random" and _pool:
            import random as _r
            _niche = _r.choice(_pool)
            logger.info(f"[Pipeline] niche_mode=random → {_niche} dari {_pool}")
        else:
            _niche = getattr(_rc, "niche", "universe_mysteries")
            logger.info(f"[Pipeline] niche_mode=fixed → {_niche}")
    except Exception as _e:
        logger.warning(f"[Pipeline] Gagal baca niche config ({_e}) — fallback")
        _niche = "universe_mysteries"
    tenant = TenantConfig(tenant_id="ryan_andrian", niche=_niche)

    print(f"\n{'='*60}")
    print(f"MESINVIRAL — AUTOMATED PIPELINE")
    print(f"{'='*60}")
    print(f"Tenant  : {tenant.tenant_id}")
    print(f"Niche   : {tenant.niche}")
    print(f"Publish : {publish_flag}")
    print(f"{'='*60}\n")

    pipeline = Pipeline()
    result   = pipeline.run(tenant, publish=publish_flag)

    print(f"\n{'='*60}")
    print(f"PIPELINE RESULT")
    print(f"{'='*60}")
    print(f"Status  : {result['status'].upper()}")
    print(f"Time    : {result.get('elapsed_seconds', 0)}s")
    if result.get("video_path"):
        vp = Path(result["video_path"])
        if vp.exists():
            size = vp.stat().st_size / (1024 * 1024)
            print(f"Video   : {result['video_path']} ({size:.1f} MB)")
    if result.get("published", {}).get("youtube", {}).get("url"):
        print(f"YouTube : {result['published']['youtube']['url']}")
    if result.get("storage"):
        s = result["storage"]
        print(f"Storage : {s.get('usage', {}).get('total_mb', 0):.1f}MB remaining")
        print(f"Clips   : {'deleted' if s.get('clips_cleaned') else 'kept'}")
    if result.get("error"):
        print(f"Error   : {result['error']}")
    print(f"{'='*60}")
