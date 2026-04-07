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
from src.utils.supabase_writer import SupabaseWriter
from src.utils.telegram_notifier import TelegramNotifier
from src.intelligence.schedule_manager import ScheduleManager

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
        self.storage_cleaner    = StorageCleaner(base_dir="logs")
        self.supabase_writer    = SupabaseWriter()
        self.telegram           = TelegramNotifier()
        self.schedule_manager   = ScheduleManager()

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

        # ── s84: Resolve niche + focus dari production_schedules ────
        try:
            channel_id   = getattr(run_config, "channel_id", None) or tenant_config.tenant_id
            resolved_niche, niche_focus = self.schedule_manager.resolve_slot(
                tenant_id  = tenant_config.tenant_id,
                channel_id = channel_id,
            )
            if resolved_niche and resolved_niche != tenant_config.niche:
                logger.info(
                    f"[Pipeline] Niche override: "
                    f"{tenant_config.niche} → {resolved_niche}"
                )
                tenant_config.niche = resolved_niche
            if niche_focus:
                logger.info(f"[Pipeline] Niche focus: '{niche_focus}'")
        except Exception as _se:
            logger.warning(f"[Pipeline] ScheduleManager gagal ({_se}) — pakai niche default")
            niche_focus = None
        # ────────────────────────────────────────────────────────────

        result = {
            "run_id":       run_id,
            "tenant_id":    tenant_config.tenant_id,
            "niche":        tenant_config.niche,  # diupdate setelah resolve_slot
            "niche_focus":  niche_focus,
            "started_at":   datetime.now().isoformat(),
            "steps":        {},
            "status":       "running",
            "video_path":   None,
            "published":    {},
            "storage":      {},
        }

        video_path = None
        # Sync result["niche"] setelah resolve_slot (mungkin sudah diubah)
        result["niche"] = tenant_config.niche

        try:
            # ── STEP 1: Trend Scan ──────────────────────────────────
            logger.info("STEP 1/7 | Scanning trends...")
            signals = self.trend_radar.scan(
                tenant_config, run_config=run_config, focus=niche_focus
            )
            total_signals = sum(len(v) for v in signals.values() if isinstance(v, list))
            result["steps"]["trend_scan"] = {
                "status": "ok", "signals": total_signals,
                "niche_focus": niche_focus or None,
            }
            logger.info(f"STEP 1 DONE | {total_signals} signals collected")

            # ── STEP 2: Topic Selection ─────────────────────────────
            logger.info("STEP 2/7 | Selecting best topic...")
            topics = self.niche_selector.select(signals, tenant_config, focus=niche_focus)
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
            clip_count = len(clips)
            result["steps"]["visuals"] = {"status": "ok", "clips": clip_count}
            logger.info(f"STEP 6 DONE | {clip_count} clips ready")

            # ── STEP 7: Video Render ────────────────────────────────
            logger.info("STEP 7/7 | Rendering final video...")
            video_path = self.video_renderer.render(
                script, audio_path, clips, tenant_config,
                word_timestamps=word_timestamps,
                run_id=run_id,
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

            # ── s72: Simpan thumbnail SEBELUM clips dihapus ─────────
            thumbnail_path = self._save_thumbnail(
                tenant_id  = tenant_config.tenant_id,
                run_id     = run_id,
                output_dir = "logs",
            )
            result["thumbnail_path"] = thumbnail_path

            # ── CLEANUP: Hapus clips mentah setelah render ──────────
            clips_cleaned = self.storage_cleaner.cleanup_clips(
                tenant_id=tenant_config.tenant_id,
                video_path=video_path,
            )
            result["storage"]["clips_cleaned"] = clips_cleaned

            # ── PRE-PUBLISH QC ──────────────────────────────────────────
            video_duration = self._get_video_duration(video_path)
            file_size_mb   = round(os.path.getsize(video_path) / (1024 * 1024), 1)

            qc_passed, qc_reason = self._pre_publish_qc(video_path, video_duration, clip_count)
            result["steps"]["qc"] = {
                "passed":   qc_passed,
                "reason":   qc_reason,
                "duration": video_duration,
                "size_mb":  file_size_mb,
            }

            if not qc_passed:
                logger.warning(f"QC FAILED | {qc_reason} — video tidak dipublish")
                self.supabase_writer.write_qc_failed(
                    run_id        = run_id,
                    tenant_id     = tenant_config.tenant_id,
                    niche         = tenant_config.niche,
                    topic         = script.get("topic", ""),
                    qc_reason     = qc_reason,
                    duration_secs = video_duration,
                    file_size_mb  = file_size_mb,
                )
                # s81: Notifikasi Telegram QC fail
                try:
                    self.telegram.notify_qc_fail(
                        run_id        = run_id,
                        tenant_id     = tenant_config.tenant_id,
                        topic         = script.get("topic", ""),
                        qc_reason     = qc_reason,
                        duration_secs = video_duration,
                        size_mb       = file_size_mb,
                        run_config    = run_config,
                    )
                except Exception as _te:
                    logger.warning(f"[Telegram] notify_qc_fail gagal: {_te}")
                # Hapus clips dir DAN video final agar tidak bocor disk
                self.storage_cleaner.cleanup_clips(
                    tenant_id  = tenant_config.tenant_id,
                    video_path = video_path,
                )
                try:
                    if video_path and Path(video_path).exists():
                        Path(video_path).unlink()
                        logger.info(f"[Pipeline] QC fail — video dihapus: {video_path}")
                except Exception as _e:
                    logger.warning(f"[Pipeline] Gagal hapus video QC fail: {_e}")
            else:
                dur_str = f"{video_duration:.1f}" if video_duration is not None else "unknown"
                logger.info(f"QC PASSED | duration={dur_str}s | size={file_size_mb}MB")

            # ── PUBLISH ─────────────────────────────────────────────────
            published_platforms = []

            if publish and qc_passed:
                # YouTube
                logger.info("PUBLISHING | Uploading to YouTube Shorts...")
                yt_result = self.youtube_publisher.publish(
                    video_path, script, tenant_config,
                    thumbnail_path=result.get("thumbnail_path", ""),
                )
                result["published"]["youtube"] = yt_result

                if yt_result.get("video_id"):
                    published_platforms.append("youtube")
                    logger.info(f"PUBLISHED | YouTube: {yt_result['url']}")

                    # ── s71: Simpan metadata ke Supabase ──────────────
                    self.supabase_writer.write_video(
                        run_id         = run_id,
                        tenant_id      = tenant_config.tenant_id,
                        platform       = "youtube",
                        video_id       = yt_result["video_id"],
                        url            = yt_result["url"],
                        title          = yt_result.get("title", script.get("title", "")),
                        hook           = script.get("hook", ""),
                        topic          = script.get("topic", ""),
                        niche          = tenant_config.niche,
                        viral_score    = float(script.get("viral_score", 0)),
                        duration_secs  = video_duration,
                        file_size_mb   = file_size_mb,
                        topic_scores   = script.get("topic_scores"),
                        insights_grade = script.get("insights_grade", ""),
                    )
                    # ──────────────────────────────────────────────────

                    # s81: Notifikasi Telegram sukses publish
                    try:
                        self.telegram.notify_success(result, run_config=run_config)
                    except Exception as _te:
                        logger.warning(f"[Telegram] notify_success gagal: {_te}")

                else:
                    _yt_err = yt_result.get("error", "unknown")
                    logger.warning(f"YouTube publish failed: {_yt_err}")
                    # s81: Notifikasi Telegram upload gagal (QC lulus tapi YouTube reject)
                    try:
                        self.telegram.notify_publish_fail(
                            run_id     = run_id,
                            tenant_id  = tenant_config.tenant_id,
                            error      = _yt_err,
                            run_config = run_config,
                        )
                    except Exception as _te:
                        logger.warning(f"[Telegram] notify_publish_fail gagal: {_te}")

                # TikTok — akan ditambah di Fase 8
                # Instagram — akan ditambah di Fase 8

                # ── CLEANUP: Hapus video final setelah semua platform upload ──
                active_platforms = (
                    run_config.publish_platforms
                    if run_config
                    else ["youtube"]
                )
                video_cleaned = self.storage_cleaner.cleanup_video(
                    video_path          = video_path,
                    published_platforms = published_platforms,
                    required_platforms  = active_platforms,
                )
                result["storage"]["video_cleaned"] = video_cleaned

            elif not qc_passed:
                logger.info("PUBLISH SKIPPED | QC tidak lolos")
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

        except BaseException as e:
            # BaseException (bukan hanya Exception) agar Ctrl+C / SIGTERM
            # pun tetap trigger cleanup — tidak tinggalkan sampah di disk.
            is_interrupt = isinstance(e, (KeyboardInterrupt, SystemExit))

            elapsed          = round(time.time() - start_time, 1)
            result["status"] = "failed"
            result["error"]  = str(e) if not is_interrupt else "Interrupted (KeyboardInterrupt/SystemExit)"
            result["elapsed_seconds"] = elapsed
            logger.error(f"PIPELINE FAILED | {elapsed}s | Error: {e}")

            # ── s71: Catat pipeline failure ke Supabase ───────────────
            # Skip Supabase write jika interrupt — koneksi mungkin sudah mati
            if not is_interrupt:
                self.supabase_writer.write_failed_run(
                    run_id    = run_id,
                    tenant_id = tenant_config.tenant_id,
                    niche     = getattr(tenant_config, "niche", "unknown"),
                    error     = str(e),
                )
                # s81: Notifikasi Telegram pipeline crash
                try:
                    self.telegram.notify_failure(
                        run_id          = run_id,
                        tenant_id       = tenant_config.tenant_id,
                        niche           = getattr(tenant_config, "niche", "unknown"),
                        error           = str(e),
                        elapsed_seconds = elapsed,
                        run_config      = run_config,
                    )
                except Exception as _te:
                    logger.warning(f"[Telegram] notify_failure gagal: {_te}")
            # ─────────────────────────────────────────────────────────

            # Cleanup clips meski pipeline gagal (termasuk Ctrl+C)
            # Hapus clips_dir tanpa syarat video_path — bisa saja render belum selesai
            try:
                clips_dir = Path("logs") / f"clips_{tenant_config.tenant_id}"
                if clips_dir.exists():
                    import shutil as _shutil
                    _shutil.rmtree(clips_dir)
                    logger.info(f"[Pipeline] Cleanup clips dir: {clips_dir.name}")
            except Exception as _ce:
                logger.warning(f"[Pipeline] Cleanup clips gagal: {_ce}")
            # Hapus video final jika ada tapi belum di-publish
            if video_path and Path(video_path).exists():
                try:
                    Path(video_path).unlink()
                    logger.info(f"[Pipeline] Cleanup video: {Path(video_path).name}")
                except Exception as _ve:
                    logger.warning(f"[Pipeline] Cleanup video gagal: {_ve}")

            # Re-raise interrupt agar proses benar-benar berhenti
            if is_interrupt:
                raise

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/pipeline_{run_id}.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result


    def _save_thumbnail(self, tenant_id: str, run_id: str, output_dir: str = "logs") -> str:
        """s72: Copy hook_frame_img.jpg ke logs/ sebelum cleanup_clips."""
        import shutil
        clips_dir = Path(output_dir) / f"clips_{tenant_id}"
        src = clips_dir / "hook_frame_img.jpg"
        if not src.exists():
            logger.warning("[Pipeline] hook_frame_img.jpg tidak ada — thumbnail skip")
            return ""
        dst = Path(output_dir) / f"thumbnail_{run_id}.jpg"
        try:
            shutil.copy2(str(src), str(dst))
            logger.info(f"[Pipeline] s72 Thumbnail saved: {dst.name}")
            return str(dst)
        except Exception as e:
            logger.warning(f"[Pipeline] Thumbnail copy gagal: {e}")
            return ""

    def _pre_publish_qc(self, video_path: str, duration_secs, clip_count: int = None) -> tuple:
        """
        Fase 7 s71: Lightweight pre-publish quality control.
        Empat check cepat (<2 detik) sebelum upload ke YouTube.

        Checks:
          1. File size > 5 MB      — render tidak korup/kosong
          2. Durasi >= 45 detik    — minimum Shorts yang layak
          3. Durasi <= 180 detik   — maksimum YouTube Shorts
          4. clip_count >= 6       — semua visual scene berhasil

        Returns: (passed: bool, reason: str)
        Jika passed=False → video tidak dipublish, dicatat qc_failed.
        Pipeline tidak crash — lanjut ke run berikutnya.
        """
        # Check 1: File size
        try:
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            if size_mb < 5.0:
                return False, f"File terlalu kecil: {size_mb:.1f}MB < 5MB (render gagal?)"
        except Exception as e:
            return False, f"Tidak bisa baca file video: {e}"

        # Check 2 & 3: Durasi (skip jika ffprobe tidak tersedia)
        if duration_secs is not None:
            if duration_secs < 45:
                return False, f"Durasi terlalu pendek: {duration_secs:.1f}s < 45s"
            if duration_secs > 180:
                return False, f"Durasi terlalu panjang: {duration_secs:.1f}s > 180s (bukan Shorts)"

        # Check 4: Jumlah clips — semua scene harus berhasil
        # s71b: mencegah video dengan visual tidak lengkap dipublish
        if clip_count is not None and clip_count < 6:
            return False, (
                f"Visual tidak lengkap: {clip_count}/6 clips berhasil. "
                f"Scene gagal kemungkinan ditolak DALL-E 3 content policy."
            )

        return True, "ok"

    def _get_video_duration(self, video_path: str):
        """
        Dapatkan durasi video via FFprobe.
        Returns: durasi detik (float) jika berhasil dan > 0, None jika gagal.
        Jika None: QC skip cek durasi, pipeline tetap jalan.
        """
        import subprocess
        import json as _json

        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data         = _json.loads(result.stdout)
                duration_str = data.get("format", {}).get("duration")
                if duration_str:
                    duration = float(duration_str)
                    if duration > 0:
                        return round(duration, 2)
                logger.warning("[Pipeline] FFprobe OK tapi duration tidak valid")
                return None
        except Exception as e:
            logger.warning(f"[Pipeline] FFprobe gagal: {e} — QC skip duration check")

        return None


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
