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
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from src.intelligence.config import TenantConfig
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
from src.exceptions import ConfigError, LLMError, TTSError, VisualError, RenderError, ErrorClass

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

    def _load_tenant_run_config(self, tenant_config: TenantConfig):
        """
        Load TenantRunConfig dari Supabase.
        Fallback: gunakan tenant_config yang diberikan jika gagal.
        """
        try:
            from src.config.tenant_config import load_tenant_config
            run_config = load_tenant_config(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None), getattr(tenant_config, "niche", None))
            logger.info(
                f"[Pipeline] Config loaded from Supabase: "
                f"tts={run_config.tts_provider} | "
                f"visual_mode={run_config.visual_mode} | "  # selektor EFEKTIF (bukan visual_provider legacy)
                f"llm={run_config.llm_model}"
            )
            return run_config
        except Exception as e:
            logger.warning(
                f"[Pipeline] TenantConfigManager gagal ({e}) — "
                f"pakai TenantConfig default"
            )
            return None

    def run(self, tenant_config: TenantConfig, publish: bool = True, run_id: str | None = None) -> dict:
        """
        Jalankan full pipeline untuk satu tenant.

        Args:
            tenant_config: Config tenant (tenant_id + niche minimum)
            publish:       True → upload ke platform setelah render
            run_id:        opsional — bila diberikan caller (mis. produce_one yang sudah
                           contextualize log), dipakai apa adanya; else generate (backward-compatible).
        """
        run_id     = run_id or f"{tenant_config.tenant_id}_{int(time.time())}"
        start_time = time.time()

        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE START | run_id: {run_id}")
        logger.info(f"Tenant: {tenant_config.tenant_id} | Niche: {tenant_config.niche}")
        logger.info(f"{'='*60}")

        # Load config dari Supabase
        run_config = self._load_tenant_run_config(tenant_config)

        # ── Niche sudah di-resolve di HULU per-channel ([[decisions_niche_model]]) ──
        # SCHEDULED: producer._resolve_niche (random → rotasi LRU SELURUH entitlement / fixed → channels.niche).
        # DIRECT/test (run_direct): pakai niche EKSPLISIT job. Pipeline memproduksi niche yang DIBERIKAN
        # (tenant_config.niche) — TIDAK merotasi (single-source + cegah niche test/rerun ditimpa rotasi).
        niche_focus = None
        resolved_content_type = "short"
        logger.info(f"[Pipeline] Niche (resolved upstream): '{tenant_config.niche}'")
        # ────────────────────────────────────────────────────────────
        # B2 cost-tracking: mulai meter konsumsi AI run ini (thread-local; adapter/provider mencatat
        # on-the-fly dari respons yang sama — NOL panggilan ekstra). Ringkasan dilampirkan di akhir.
        try:
            from src.utils import cost_meter
            cost_meter.reset()
        except Exception:
            pass

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
            "run_kind":     getattr(tenant_config, "run_kind", ""),  # tandai laporan (test/private)
        }

        video_path = None
        # Sync result["niche"] setelah resolve_slot (mungkin sudah diubah)
        result["niche"] = tenant_config.niche

        try:
            # ── STEP 0: Validasi kredensial wajib (fail-loud SEBELUM produksi 35 mnt) ──
            _missing = run_config.missing_credentials() if run_config else []
            if _missing:
                raise ConfigError(
                    "Kredensial wajib belum lengkap: " + "; ".join(_missing),
                    step="validation",
                )
            # [B6] F2 — KOHERENSI preset ⇄ mode visual (fail-loud SEBELUM biaya, anti-human-error §3.1):
            # preset ai_video (8s) WAJIB model video; model video WAJIB preset ai_video (1 klip ≠ N beat).
            _vm0 = (getattr(run_config, "visual_mode", "") or "") if run_config else ""
            _preset0 = getattr(tenant_config, "duration_preset", None)
            if _preset0 or _vm0.startswith("ai_video:"):
                from src.config.format_catalog import preset_render_mode as _prm
                _rm0 = _prm(_preset0)
                if _rm0 == "ai_video" and not _vm0.startswith("ai_video:"):
                    raise ConfigError(
                        f"Preset {_preset0}s memakai render text-to-video — pilih MODEL VIDEO "
                        f"(ai_video:*) di Channel Setting (sekarang: '{_vm0 or 'kosong'}').",
                        step="validation",
                    )
                if _vm0.startswith("ai_video:") and _rm0 != "ai_video":
                    raise ConfigError(
                        f"Model video ({_vm0}) hanya untuk preset ber-render text-to-video — "
                        f"preset channel sekarang {_preset0 or '(kosong)'}s ({_rm0 or 'image_seq'}).",
                        step="validation",
                    )

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
                # Sertakan alasan vendor (kuota/kunci/model) — tenant butuh sebab yang actionable.
                _why = (getattr(self.niche_selector, "last_error", "") or "").strip()
                # [ERROR-MGMT 2026-07-20] bawa kelas + pesan manusiawi dari selector (pola TTS :279-281)
                # → production_runs.error_class terisi benar (dulu 'unknown' walau akar 401/404 jelas).
                raise LLMError((f"No topics selected — {_why}" if _why else "No topics selected"), step="niche",
                               error_class=getattr(self.niche_selector, "last_error_class", ErrorClass.UNKNOWN),
                               human_message=getattr(self.niche_selector, "last_human_error", None))
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
                _why = (getattr(self.script_engine, "last_error", "") or "").strip()
                raise LLMError((f"Script generation failed — {_why}" if _why else "Script generation failed"), step="script")
            result["steps"]["script"] = {
                "status":       "ok",
                "title":        scripts[0].get("title", ""),
                "viral_score":  scripts[0].get("script_viral_score", 0),
                "llm_provider": scripts[0].get("llm_provider_used", ""),
            }
            logger.info(f"STEP 3 DONE | {scripts[0].get('word_count', 0)} words")

            # ── STEP 3.5: GERBANG DURASI PALING HULU — hentikan SEBELUM sepeser pun terpakai ──────
            # Alat ukur durasi kini meleset ~1 detik (terukur 0,2–2,8 dtk pada 6 channel nyata). Jadi
            # begitu naskah selesai, kita SUDAH TAHU video jadinya akan berapa detik. Sampai 2026-08-01
            # pengetahuan itu tidak dipakai: pipeline tetap membayar optimasi hook (STEP 4), pembuatan
            # prompt gambar (STEP 4.5), dan SUARA (STEP 5, ElevenLabs ditagih per huruf) — baru
            # dihentikan gerbang pasca-suara. Untuk tenant BYOK itu UANG MEREKA, terbakar pada video
            # yang sudah kita ketahui akan gagal.
            # Aturannya SAMA PERSIS dengan gerbang pasca-suara (satu penggaris, bukan aturan baru):
            # hanya meleset PARAH (di luar band ± satu lebar band) yang dihentikan; near-miss tetap
            # lanjut supaya tenant yang meninjaunya, bukan mesin yang membuangnya.
            try:
                _p35 = getattr(tenant_config, "duration_preset", None)
                _est35 = (scripts[0].get("_duration_est") or {})
                _audio35 = _est35.get("est_seconds")
                if _p35 and _audio35:
                    from src.config.format_catalog import active_presets as _ap35
                    from src.config.format_catalog import effective_overhead as _eo35
                    from src.production.duration_model import band_video as _bv35
                    _rc35 = None
                    try:
                        from src.config.tenant_config import load_tenant_config as _ltc35
                        _rc35 = _ltc35(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None),
                                       getattr(tenant_config, "niche", None))
                    except Exception:
                        _rc35 = None
                    _tangga35 = _ap35()
                    if _tangga35 and int(_p35) in _tangga35:
                        _lo35, _hi35 = _bv35(_p35, _tangga35)
                        _proj35 = float(_audio35) + _eo35(_p35, _rc35)
                        _lebar35 = max(1.0, _hi35 - _lo35)
                        if not (_lo35 - _lebar35 <= _proj35 <= _hi35 + _lebar35):
                            raise LLMError(
                                f"Naskah tidak layak: perkiraan durasi video {_proj35:.0f} detik, jauh di "
                                f"luar rentang preset {int(_p35)} detik (sah {_lo35:.1f}–{_hi35:.1f} detik). "
                                f"Produksi dihentikan SEBELUM biaya suara & gambar terpakai; naskah baru "
                                f"dibuat otomatis pada siklus berikutnya.", step="script")
                        result["steps"]["duration_gate_hulu"] = {
                            "status": "ok" if _lo35 <= _proj35 <= _hi35 else "near_miss",
                            "projected": round(_proj35, 1), "window": [round(_lo35), round(_hi35)]}
                        logger.info(f"[Pipeline] Gerbang durasi HULU: proyeksi {_proj35:.1f}s vs band "
                                    f"{_lo35:.1f}-{_hi35:.1f}s → "
                                    f"{'lolos' if _lo35 <= _proj35 <= _hi35 else 'near-miss (lanjut)'}")
            except LLMError:
                raise
            except Exception as _e35:
                # Gerbang ini penghemat biaya, bukan penentu mutu — kegagalannya TIDAK boleh
                # menjatuhkan produksi. Gerbang pasca-suara tetap menjaga.
                logger.warning(f"[Pipeline] gerbang durasi hulu dilewati (non-fatal): {str(_e35)[:90]}")

            # ── STEP 4: Hook Optimization ───────────────────────────
            # [B6] F2: preset TANPA beat hook (8s = core-saja) → optimasi hook DILEWATI. script['hook']
            # tetap "" (setdefault validator) → overlay judul-hook & blok deskripsi publisher otomatis
            # skip (keduanya guard `if hook`). Judul video tetap dari script['title'] (tak tersentuh).
            _beats_active = (scripts[0].get("beats") or []) if scripts else []
            if _beats_active and "hook" not in _beats_active:
                script = scripts[0]
                result["script"] = script
                result["steps"]["hook"] = {"status": "skipped", "reason": "preset tanpa beat hook"}
                logger.info("STEP 4 SKIP | preset tanpa beat hook (ultra-short) — hook-optimize dilewati")
            else:
                logger.info("STEP 4/7 | Optimizing hook...")
                optimized = self.hook_optimizer.optimize_batch(scripts, tenant_config)
                if not optimized:
                    raise LLMError("Hook optimization failed", step="hook")
                script       = optimized[0]
                # ── PAGAR: hook baru TIDAK boleh merusak durasi yang sudah pas (2026-07-31) ────────
                # Sejak hook hasil optimasi ikut terbaca narator (perbaikan hari ini), panjangnya
                # mengubah durasi — dan gerbang durasi sudah lewat di STEP 3. Kalau hook baru membuat
                # durasi keluar dari batas sah, hook ASLI dipulihkan: durasi yang benar lebih penting
                # daripada hook yang lebih tajam, dan tenant tidak boleh dapat video salah durasi
                # karena pertukaran yang tak pernah ia setujui.
                _hp = getattr(tenant_config, "duration_preset", None)
                if _hp and script.get("original_hook"):
                    try:
                        from src.config.format_catalog import active_presets as _apr
                        from src.config.format_catalog import effective_overhead as _eoh
                        from src.production.duration_model import vonis as _vh
                        _tg = _apr()
                        if _tg and int(_hp) in _tg:
                            _kalh = (getattr(run_config, "duration_calibration", None) or None) if run_config else None
                            _ovh4 = _eoh(_hp, run_config)
                            _vv = _vh(script.get("full_script") or "", _hp, _tg, _ovh4, _kalh)
                            if _vv["status"] != "ok":
                                _fs_now = script.get("full_script") or ""
                                script["full_script"] = _fs_now.replace(script["hook"],
                                                                        script["original_hook"], 1)
                                script["hook"] = script["original_hook"]
                                script["hook_reverted_reason"] = (
                                    f"hook baru membuat durasi {_vv['video_prediksi']:.1f}s di luar batas "
                                    f"{_vv['band_video'][0]:.1f}-{_vv['band_video'][1]:.1f}s")
                                logger.warning(f"[Pipeline] hook optimasi DIPULIHKAN ke asal — "
                                               f"{script['hook_reverted_reason']}")
                    except Exception as _he:
                        logger.warning(f"[Pipeline] pagar durasi hook gagal (hook baru dipakai): {_he}")
                result["script"] = script  # Phase 5.3: ekspos full script dict (producer simpan utk publisher)
                winner_score = script.get("hook_data", {}).get("winner", {}).get("scroll_stop_power", 0)
                result["steps"]["hook"] = {
                    "status": "ok",
                    "score":  winner_score,
                    "hook":   script.get("hook", "")
                }
                logger.info(f"STEP 4 DONE | Hook [{winner_score}/100]: {script.get('hook', '')[:60]}")

            # ── STEP 4.5: Image-prompt generation (Opsi A — Tahap-2) ────
            # LLM TERDEDIKASI membuat prompt image per-beat dari narasi FINAL (hook sudah di-optimize STEP 4).
            # Niche-aware (visual_style + nama niche dari DB). Set script['visual_suggestions'] + ['thumbnail_concept'].
            # [B6] F2 — cabang render_mode: ai_video → SATU prompt-video (gerak+kamera); else prompt-image per-beat.
            from src.config.format_catalog import preset_render_mode as _prm45
            if _prm45(getattr(tenant_config, "duration_preset", None)) == "ai_video":
                logger.info("STEP 4.5/7 | Generating text-to-video prompt (dedicated LLM)...")
                script = self.script_engine.generate_video_prompt(script, tenant_config)
                result["script"] = script
                logger.info("STEP 4.5 DONE | 1 video prompt (niche-DNA aware)")
            else:
                logger.info("STEP 4.5/7 | Generating per-beat image prompts (dedicated LLM)...")
                script = self.script_engine.generate_visual_prompts(script, tenant_config)
                result["script"] = script
                logger.info(f"STEP 4.5 DONE | {len(script.get('visual_suggestions', []))} image prompts (niche-aware)")

            # ── STEP 5: TTS Audio ───────────────────────────────────
            logger.info("STEP 5/7 | Generating TTS audio...")
            # Closed-loop durasi (NOL biaya TTS): target audio = preset − trailing_silence. Bila preset
            # di-set → tts_engine rapikan via atempo HANYA jika di luar window QC + faktor dalam batas aman.
            # [DURASI-3 + F4] overhead PENUH = SATU rumus dgn budget script_engine + gerbang + renderer
            # (format_catalog.effective_overhead = trailing efektif per-preset + loop bersih). DURASI-3
            # menyatukan trailing; F4 menutup komponen LOOP yang masih terlewat di korektor (dulu:
            # target audio 1s ketinggian saat loop aktif → atempo bisa meregang audio yang sudah benar —
            # terparah di 8s ±12%).
            _preset_s = getattr(tenant_config, "duration_preset", None)
            _target_audio, _overhead = None, None
            if _preset_s:
                _rc5 = None
                try:
                    from src.config.tenant_config import load_tenant_config as _ltc5
                    _rc5 = _ltc5(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None), getattr(tenant_config, "niche", None))
                except Exception:
                    _rc5 = None
                from src.config.format_catalog import effective_overhead as _eff_ovh5
                _overhead = _eff_ovh5(_preset_s, _rc5)
                _target_audio = max(1.0, float(_preset_s) - _overhead)
            tts_result = self.tts_engine.generate(script, tenant_config, target_audio_secs=_target_audio,
                                                  overhead_secs=_overhead)
            audio_path, word_timestamps = (
                tts_result if isinstance(tts_result, tuple)
                else (tts_result, [])
            )
            if not audio_path:
                # [ERROR-MGMT] error TTS ditelan tts_engine (return "",[]); teruskan makna + pesan
                # manusiawi yang disimpan di last_* → mengalir ke result → production_runs.error_class.
                _te = self.tts_engine
                raise TTSError(
                    getattr(_te, "last_human_error", None) or getattr(_te, "last_error", None) or "TTS generation failed",
                    step="tts",
                    error_class=getattr(_te, "last_error_class", ErrorClass.UNKNOWN),
                    human_message=getattr(_te, "last_human_error", None),
                )
            ts_info = f"{len(word_timestamps)} word timestamps" if word_timestamps else "no timestamps (estimasi)"
            result["steps"]["tts"] = {
                "status": "ok", "path": audio_path, "timestamps": len(word_timestamps),
                # Transparansi fallback (§4b) — provider TERKONFIGURASI vs yang AKTUAL me-render.
                "configured_provider": getattr(self.tts_engine, "last_primary", None),
                "provider_used":       getattr(self.tts_engine, "last_provider", None),
                "fallback_used":       getattr(self.tts_engine, "last_fallback_used", False),
            }
            logger.info(f"STEP 5 DONE | Audio: {audio_path} | {ts_info}")

            # ── STEP 6: Visual Assembly ─────────────────────────────
            logger.info("STEP 6/7 | Assembling visuals...")
            audio_duration = self.tts_engine.get_duration(audio_path)
            logger.info(f"[Pipeline] Audio duration: {audio_duration:.1f}s — scaling clips")

            # ── GERBANG DURASI PRA-VISUAL (owner 2026-07-10) ─────────
            # Di titik ini durasi audio SUDAH PASTI; durasi video final = audio + trailing_silence
            # (rumus renderer s72b, sumber trailing SAMA: run-config). Bila proyeksi di luar window
            # batas sah = aturan titik-tengah (identik _pre_publish_qc) → STOP SEKARANG,
            # SEBELUM biaya gambar AI + render terbakar untuk video yang PASTI gagal QC
            # (salah sistem tidak boleh jadi rugi tenant). Tanpa preset → lewat (paritas QC interim).
            _gate_preset = getattr(tenant_config, "duration_preset", None)
            if _gate_preset:
                # [DURASI-F4] proyeksi = audio + overhead PENUH (trailing efektif + loop bersih) —
                # SATU rumus dgn naskah/korektor/renderer (format_catalog.effective_overhead).
                # Dulu trailing saja → proyeksi 1s KURANG saat loop aktif → salah vonis kasus batas.
                _rc = None
                try:
                    from src.config.tenant_config import load_tenant_config as _ltc
                    _rc = _ltc(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None),
                               getattr(tenant_config, "niche", None))
                except Exception:
                    _rc = None
                from src.config.format_catalog import active_presets as _act_p
                from src.config.format_catalog import effective_overhead as _eff_ovh
                from src.production.duration_model import band_video as _band
                _gate_trail = _eff_ovh(_gate_preset, _rc)
                _gate_proj = audio_duration + _gate_trail
                # ── BATAS SAH = ATURAN TITIK-TENGAH OWNER (2026-07-29), bukan persen ─────────────
                # Dulu: ±QC_DURATION_TOLERANCE (15%) + pagar 2× (30%). Angka karangan, dan terbukti
                # salah arah: di preset 90s ±15% = ±13,5s (lebih longgar dari jarak ke tetangga 75s),
                # sementara di preset 8s ±15% = ±1,2s (lebih ketat dari yang perlu). Aturan owner:
                # hasil sah selama lebih dekat ke preset yang dipilih daripada ke preset tetangganya
                # → batas = titik tengah antar-preset, MELEBAR/MENYEMPIT sendiri mengikuti tangga
                # preset aktif di DB (menonaktifkan satu preset otomatis melebarkan tetangganya).
                # Tangga kosong / preset tak aktif → gerbang PASIF (tak mengarang batas sendiri).
                _tangga_g = _act_p()
                _gate_lo = _gate_hi = None
                if _tangga_g and int(_gate_preset) in _tangga_g:
                    _gate_lo, _gate_hi = _band(_gate_preset, _tangga_g)
                if _gate_lo is None:
                    logger.warning(f"[Pipeline] preset {_gate_preset}s tak ada di tangga aktif {_tangga_g} — "
                                   f"gerbang durasi pra-visual DILEWATI (tak mengarang batas)")
                    result["steps"]["duration_gate"] = {"status": "pasif", "projected": round(_gate_proj, 1)}
                    _gate_lo = _gate_hi = None
                # PAGAR PENGAMAN (owner 2026-07-15, dipertahankan): near-miss TIDAK dibunuh — lanjut
                # produksi → QC pasca-render merutekannya ke `ready_with_issues` (tenant tinjau).
                # Yang di-stop pra-visual hanya meleset PARAH: naskah rusak, hemat biaya render BYOK.
                # Pagar dihitung dari LEBAR BAND (bukan persen preset): satu lebar band di luar batas.
                if _gate_lo is not None:
                    _lebar = max(1.0, _gate_hi - _gate_lo)
                    _gross_lo, _gross_hi = _gate_lo - _lebar, _gate_hi + _lebar
                    if not (_gross_lo <= _gate_proj <= _gross_hi):
                        raise TTSError(
                            f"Durasi proyeksi {_gate_proj:.1f}s meleset PARAH dari preset {_gate_preset}s "
                            f"(batas sah {_gate_lo:.1f}–{_gate_hi:.1f}s, pagar {_gross_lo:.1f}–{_gross_hi:.1f}s) — "
                            f"naskah tak layak, dihentikan sebelum biaya render terpakai; diproduksi ulang "
                            f"otomatis siklus berikutnya.", step="tts")
                _within = (_gate_lo is None) or (_gate_lo <= _gate_proj <= _gate_hi)
                if _gate_lo is not None:
                    result["steps"]["duration_gate"] = {
                        "status": "ok" if _within else "near_miss",
                        "projected": round(_gate_proj, 1), "window": [round(_gate_lo), round(_gate_hi)]}
                    if _within:
                        logger.info(f"[Pipeline] Gerbang durasi pra-visual LOLOS: proyeksi {_gate_proj:.1f}s "
                                    f"dalam batas sah {_gate_lo:.1f}–{_gate_hi:.1f}s (aturan titik-tengah)")
                    else:
                        logger.info(f"[Pipeline] Durasi NEAR-MISS {_gate_proj:.1f}s (batas sah {_gate_lo:.0f}–"
                                    f"{_gate_hi:.1f}s) — LANJUT produksi → review pasca-render (bukan dibuang)")
            # Image-gen per-preset (MULTI_FORMAT §3): durasi per-beat (1 image/beat) dari word_timestamps
            # NYATA → sinkron TTS. SUMBER TUNGGAL: dikonsumsi visual_assembler (bake) & video_renderer (concat).
            from src.intelligence.script_engine import compute_beat_durations
            script["beat_durations"] = compute_beat_durations(script, word_timestamps, audio_duration)
            logger.info(f"[Pipeline] beat_durations ({len(script['beat_durations'])}): "
                        f"{[round(d,1) for d in script['beat_durations']]} = {sum(script['beat_durations']):.1f}s")
            clips = self.visual_assembler.assemble(script, tenant_config, audio_duration=audio_duration)
            if not clips:
                # [ERROR-MGMT §8e] Sertakan sebab NYATA dari penyedia — pesan ini ditampilkan APA ADANYA
                # ke tenant (layar detail run + tabel run: `error_message`). Kalimat "no clips downloaded"
                # sendirian membuat tenant buta: sampel nyata 14-Jul, penyedia berkata "saldo habis, isi
                # ulang di dashboard billing" — 3 run terbakar tanpa tenant pernah tahu itu.
                # SENGAJA tanpa `error_class`: itu memicu FAST_FAIL (rem setelah 1 gagal) = keputusan
                # produk, menunggu ketok owner (§8e). Pola sama dgn niche_selector.last_error di STEP 1.
                raise VisualError(self._pesan_gagal_visual(), step="visual")
            # [2026-08-08] Klip SEBAGIAN = kerusakan yang selama ini lolos. Sampai hari ini pipeline
            # hanya memeriksa "NOL klip"; kekurangan sebagian diteruskan ke perender, yang menyusun
            # durasi dari JUMLAH klip → video lebih pendek dari narasi → cerita tenant terpotong,
            # lalu diberi label "durasi". Sebabnya diambil dari perakit (sebab penyedia yang NYATA).
            _kurang = self._periksa_kelengkapan_klip(
                clips, script, getattr(self.visual_assembler, "last_error", None))
            if _kurang:
                raise VisualError(_kurang, step="visual")
            clip_count = len(clips)
            result["steps"]["visuals"] = {"status": "ok", "clips": clip_count}
            # [§8f 2026-08-05] Frame pertama gagal = video TETAP terbit tapi pembukanya lebih lemah.
            # Dulu senyap total (hanya logger.warning di worker.log) ⇒ 4 kejadian dari 181 tak pernah
            # diketahui siapa pun, dan DUA di antaranya bug kita sendiri. Melaksanakan §0.6 ("HARAM
            # fallback senyap") yang SUDAH diketok owner — bukan keputusan baru; produksi tak dihentikan.
            _hf = getattr(self.visual_assembler, "hook_frame_error", None)
            if _hf:
                result["steps"]["visuals"]["status"] = "ok_degraded"
                result["steps"]["visuals"]["hook_frame_error"] = str(_hf)[:300]
            logger.info(f"STEP 6 DONE | {clip_count} clips ready")

            # ── STEP 7: Video Render ────────────────────────────────
            logger.info("STEP 7/7 | Rendering final video...")
            video_path = self.video_renderer.render(
                script, audio_path, clips, tenant_config,
                word_timestamps=word_timestamps,
                run_id=run_id,
            )
            if not video_path:
                raise RenderError("Video rendering failed", step="render")
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

            # QC relatif Duration Preset (§8) bila channel set preset; else interim integritas.
            _preset = getattr(tenant_config, "duration_preset", None)
            _beats  = None
            if _preset:
                from src.config.format_catalog import preset_visual_beats
                _beats = preset_visual_beats(_preset)
            qc_passed, qc_reason = self._pre_publish_qc(
                video_path, video_duration, clip_count,
                target_seconds=_preset, expected_beats=_beats,
            )
            result["steps"]["qc"] = {
                "passed":   qc_passed,
                "reason":   qc_reason,
                # kode+parameter → layar tenant menampilkan DWIBAHASA; teks di atas tetap jadi cadangan
                "reason_code":   getattr(self, "_qc_kode", None),
                "reason_params": getattr(self, "_qc_param", None),
                "duration": video_duration,
                "size_mb":  file_size_mb,
            }

            if not qc_passed:
                # Rekomendasi advisory DINAMIS (no-hardcode nama provider — §0.3) — dihitung utk KEDUA mode.
                # Provider diambil dari config run (configured vs aktual), bukan literal.
                _tts      = result.get("steps", {}).get("tts", {})
                _reason_l = (qc_reason or "").lower()
                _conf     = _tts.get("configured_provider")
                _used     = _tts.get("provider_used")
                if "dur" in _reason_l or "detik" in _reason_l or "second" in _reason_l:
                    if _tts.get("fallback_used") and _used and _conf and _used != _conf:
                        recommendation = (
                            f"Suara cadangan '{_used}' merender dengan kecepatan berbeda dari suara "
                            f"utama '{_conf}' → durasi meleset dari target preset. Periksa "
                            f"kredensial/saldo penyedia suara utama Anda, atau sesuaikan preset "
                            f"durasi di pengaturan channel."
                        )
                    else:
                        recommendation = (
                            "Durasi hasil di luar target preset. Sesuaikan preset durasi atau "
                            "panjang skrip di pengaturan channel."
                        )
                elif "aspect" in _reason_l or "9:16" in _reason_l or "rasio" in _reason_l:
                    recommendation = "Rasio video tidak 9:16. Periksa pengaturan format/visual channel."
                elif "audio" in _reason_l or "stream" in _reason_l:
                    recommendation = "Audio/stream video tidak lengkap. Periksa kredensial penyedia suara Anda."
                else:
                    recommendation = "Tinjau konfigurasi channel terkait, lalu jalankan ulang produksi."
                result["steps"]["qc"]["recommendation"] = recommendation

                if not publish:
                    # ── OPSI C (PRODUCER, publish=False) — QC §3/§6.2 + DESAIN §12d.F (2026-06-17) ──
                    # JANGAN upload YouTube, JANGAN Telegram, JANGAN hapus video. Video JADI →
                    # produce_one akan upload ke S3 + mark_ready_with_issues (DITINJAU tenant di dashboard,
                    # approve→publish ber-kuota / buang). Producer TAK PERNAH publish → invariant decouple
                    # §12c terjaga + RUNAWAY tertutup (issue dihitung stok = rem alami; tak ada upload off-schedule).
                    logger.warning(
                        f"QC FAILED (producer) | {qc_reason} — STOK ready_with_issues utk ditinjau "
                        f"(Opsi C, tanpa upload YouTube). Saran: {recommendation}"
                    )
                else:
                    # ── DIRECT (publish=True, on-demand MANUAL) — tetap publish PRIVATE + advisory ──
                    # One-shot dipicu tenant (BUKAN loop) → tak ada risiko runaway.
                    logger.warning(f"QC FAILED (direct) | {qc_reason} — publish PRIVATE + advisory")
                    try:
                        tenant_config.publish_privacy = "private"
                    except Exception:
                        pass
                    yt_result = self.youtube_publisher.publish(
                        video_path, script, tenant_config,
                        thumbnail_path=result.get("thumbnail_path", ""),
                        content_type=resolved_content_type,
                    )
                    result["published"]["youtube"] = yt_result if isinstance(yt_result, dict) else {}
                    _private_url = result["published"]["youtube"].get("url", "")
                    if _private_url:
                        logger.info(f"QC FAIL → PUBLISHED PRIVATE (advisory): {_private_url}")
                    else:
                        logger.warning(
                            f"QC FAIL → upload PRIVATE gagal: "
                            f"{result['published']['youtube'].get('error', 'unknown')}"
                        )
                    # Catat kegagalan QC (+ URL privat) ke `videos` (status qc_failed) → feedback §4
                    self.supabase_writer.write_qc_failed(
                        run_id        = run_id,
                        tenant_id     = tenant_config.tenant_id,
                        niche         = tenant_config.niche,
                        topic         = script.get("topic", ""),
                        qc_reason     = qc_reason,
                        duration_secs = video_duration,
                        file_size_mb  = file_size_mb,
                        url           = _private_url,
                    )
                    # Advisory Telegram: alasan + rekomendasi dinamis + URL privat → tenant putuskan
                    try:
                        self.telegram.notify_qc_fail(
                            run_id         = run_id,
                            tenant_id      = tenant_config.tenant_id,
                            topic          = script.get("topic", ""),
                            qc_reason      = qc_reason,
                            duration_secs  = video_duration,
                            size_mb        = file_size_mb,
                            run_config     = run_config,
                            url            = _private_url,
                            recommendation = recommendation,
                            is_test        = getattr(tenant_config, "run_kind", "") in ("test", "admin_test"),
                        )
                    except Exception as _te:
                        logger.warning(f"[Telegram] notify_qc_fail gagal: {_te}")
                    # Aset sudah aman di YouTube (privat) → bersihkan lokal (clips + video final)
                    self.storage_cleaner.cleanup_clips(
                        tenant_id  = tenant_config.tenant_id,
                        video_path = video_path,
                    )
                    try:
                        if video_path and Path(video_path).exists():
                            Path(video_path).unlink()
                    except Exception as _e:
                        logger.warning(f"[Pipeline] Gagal hapus video lokal QC fail: {_e}")
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
                    content_type=resolved_content_type,
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
                        # videos.channel_id WAJIB terisi → jadi histori per-channel utk DiversityEngine
                        # (rotasi niche random + voice/hook/music/visual). Publisher sudah kirim; di sini
                        # (direct publish) dulu kosong = videos.channel_id NULL → LRU buta. (decisions_niche_model)
                        channel_id     = getattr(tenant_config, "channel_id", None),
                        # voice_id = karakter suara TTS video ini (channels.voice_key → tts_voice) —
                        # sumber dimensi compliance voice_diversity (mandat owner 2026-07-11; dulu dibuang).
                        voice_id       = getattr(tenant_config, "tts_voice", None),
                    )
                    # ──────────────────────────────────────────────────

                    # s81: Notifikasi Telegram sukses publish
                    try:
                        self.telegram.notify_success(result, run_config=run_config)
                    except Exception as _te:
                        logger.warning(f"[Telegram] notify_success gagal: {_te}")

                else:
                    # [ERROR-MGMT §8b] `publish()` sudah MENGEMBALIKAN makna errornya
                    # (`error_class` + `human_error`, youtube_publisher [B11] 3.2) — dulu keduanya
                    # DIBUANG di sini, sehingga notifikasi kegagalan unggah adalah satu-satunya
                    # notifikasi yang tak bisa menjawab pertanyaan paling menentukan: "perlu saya
                    # kerjakan sesuatu, atau cukup ditunggu?". Sumber jawaban = `SELF_HEALING`,
                    # BUKAN nama penyedia (arahan owner: penyedia akan terus bertambah).
                    _yt_err   = yt_result.get("error", "unknown")
                    _yt_kelas = yt_result.get("error_class") or ""
                    _yt_human = yt_result.get("human_error") or ""
                    logger.warning(f"YouTube publish failed: {_yt_err}")
                    # s81: Notifikasi Telegram upload gagal (QC lulus tapi YouTube reject)
                    try:
                        self.telegram.notify_publish_fail(
                            run_id      = run_id,
                            tenant_id   = tenant_config.tenant_id,
                            error       = _yt_human or _yt_err,
                            error_class = _yt_kelas,
                            run_config  = run_config,
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
                logger.info(
                    "QC tidak lolos — di-publish PRIVATE (direct)" if publish
                    else "QC tidak lolos — STOK ready_with_issues utk ditinjau (producer, Opsi C)"
                )
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
            try:
                from src.utils import cost_meter
                result["ai_usage"] = cost_meter.summary()   # B2: konsumsi AI run ini (token/gambar/karakter)
            except Exception:
                pass

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
            # Phase 2: kategori + step terstruktur (PipelineError) untuk log/notify/persist.
            result["error_category"] = getattr(e, "category", "interrupt" if is_interrupt else "unknown")
            result["error_step"]     = getattr(e, "step", None)
            # [ERROR-MGMT] dimensi SEMANTIK (makna) + pesan manusiawi → dicatat producer & dipakai
            # circuit-breaker. Default UNKNOWN (aman) utk error non-PipelineError.
            _ec = getattr(e, "error_class", ErrorClass.UNKNOWN)
            result["error_class"]  = _ec.value if isinstance(_ec, ErrorClass) else str(_ec or ErrorClass.UNKNOWN.value)
            result["human_error"]  = getattr(e, "human_message", None)
            result["elapsed_seconds"] = elapsed
            try:
                from src.utils import cost_meter
                result["ai_usage"] = cost_meter.summary()   # B2: run gagal pun uang TERPAKAI — tetap dicatat
            except Exception:
                pass
            logger.exception(
                f"PIPELINE FAILED | {elapsed}s | [{result['error_category']}"
                f"{('/' + result['error_step']) if result['error_step'] else ''}] Error: {e}"
            )

            # ── s71: Catat pipeline failure ke Supabase ───────────────
            # Skip Supabase write jika interrupt — koneksi mungkin sudah mati
            if not is_interrupt:
                # [SSOT error — penegakan 2026-07-22] SATU pesan kanonik: pesan-manusiawi bila ada
                # (PipelineError.human_message), else teks mentah. NILAI SAMA dgn yg producer simpan ke
                # production_runs.error_message (human_error or error) → Telegram, tabel `videos`, dan
                # layar (drawer Runs / halaman detail) menampilkan teks IDENTIK. UNKNOWN → str(e) = perilaku lama (nol regresi).
                human_err = result.get("human_error") or str(e)
                self.supabase_writer.write_failed_run(
                    run_id    = run_id,
                    tenant_id = tenant_config.tenant_id,
                    niche     = getattr(tenant_config, "niche", "unknown"),
                    error     = human_err,
                )
                # s81: Notifikasi Telegram pipeline crash
                try:
                    self.telegram.notify_failure(
                        run_id          = run_id,
                        tenant_id       = tenant_config.tenant_id,
                        niche           = getattr(tenant_config, "niche", "unknown"),
                        error           = human_err,
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

    def _periksa_kelengkapan_klip(self, clips, script: dict, sebab: str | None) -> str | None:
        """Klip yang jadi WAJIB menutupi seluruh bagian naskah. Kurang = video lebih pendek dari
        narasinya ⇒ **cerita tenant terpotong di tengah kalimat**.

        Kenapa ini ada (dipetakan 07/08-Agu, run nyata RETRO REWIND 03-Agu):
        satu adegan gagal dibuat → perakit dulu tetap melapor sukses → perender menyusun durasi dari
        JUMLAH klip, bukan isinya → berkas jadi **36,7 dtk sementara narasinya 58,3 dtk** (±21 detik
        cerita hilang) → QC menamainya "Durasi kependekan" ⇒ tenant menyalahkan MesinViral untuk
        kegagalan yang terjadi di akun penyedia AI-nya sendiri.

        Jumlah yang seharusnya diambil dari `beat_durations` — data yang SUDAH ada di tangan, bukan
        dari hitungan klip berpenyebut tetap (angka "/6" di log adalah literal mati; log yang sama
        juga pernah mencetak "7/6" dan "8/6").

        Return: kalimat kegagalan bila kurang · **None bila lengkap ATAU bila jumlah seharusnya
        tidak bisa dipastikan** — tanpa `beat_durations` kita DIAM, tidak menebak.
        """
        _bagian = script.get("beat_durations") or []
        if not _bagian or len(clips) >= len(_bagian):
            return None
        _kurang = len(_bagian) - len(clips)
        _dasar = (f"{_kurang} dari {len(_bagian)} bagian video gagal dibuat gambarnya — videonya akan "
                  f"lebih pendek dari narasinya (cerita terpotong), jadi produksi dihentikan.")
        _s = (sebab or "").strip()
        if not _s:
            return _dasar
        # Menyebut TEMPATNYA, bukan menebak APA yang terjadi: "menolak" keliru untuk penyedia yang
        # menggantung / servernya rusak / modelnya dipensiunkan. Yang pasti benar untuk semuanya:
        # kegagalannya terjadi di layanan AI milik tenant, bukan di MesinViral.
        return f"{_dasar} Kegagalan terjadi di layanan AI Anda — keterangannya: {_s}"

    def _pesan_gagal_visual(self) -> str:
        """[ERROR-MGMT §8e] Pesan kegagalan visual yang MEMBAWA sebab nyata penyedia.

        Pesan ini bukan catatan internal: layar detail run dan tabel run menampilkan
        `production_runs.error_message` APA ADANYA ke tenant. Kalimat "no clips downloaded"
        sendirian membuat tenant buta terhadap sesuatu yang bisa ia bereskan sendiri —
        sampel nyata worker.log 2026-07-14 (6 kejadian): penyedia video menjawab
        `HTTP 403 {"detail":"User is locked. Reason: Exhausted balance. Top up your balance
        at fal.ai/dashboard/billing."}` sementara yang tersimpan hanya "no clips downloaded".

        Sebab kosong (mis. provider mengembalikan daftar kosong tanpa exception) → kalimat dasar
        saja; TIDAK mengarang sebab. Metode terpisah supaya bisa diuji langsung dengan sampel
        produksi (pola `Pipeline.__new__` seperti uji gerbang durasi).
        """
        _sebab = (getattr(self.visual_assembler, "last_error", None) or "").strip()
        dasar = "Visual assembly failed — no clips downloaded"
        return f"{dasar} — {_sebab}" if _sebab else dasar

    def _pre_publish_qc(self, video_path: str, duration_secs, clip_count: int = None,
                        target_seconds=None, expected_beats=None) -> tuple:
        """
        Pre-publish QC = gate INTEGRITAS RENDER, bukan penilaian konten.

        Kualitas konten SUDAH di-gate di STEP 3 (ScriptAnalyzer, ambang ≥80/100).
        QC di sini hanya mendeteksi render yang RUSAK/TIDAK LENGKAP sebelum upload —
        jangan membuang video yang baik (+biaya render) atas dasar penghakiman konten.

        Checks (semua ambang CONFIG-DRIVEN, no-hardcode):
          1. File size  >= QC_MIN_SIZE_MB (default 5)    — render tidak korup/kosong
          2. Durasi     >= QC_MIN_DURATION (default 20)   — deteksi render TERPOTONG (bukan "layak")
          3. Durasi     <= QC_MAX_DURATION (default 180)  — batas platform Shorts
          4. clip_count >= QC_MIN_CLIPS (default 6)       — semua visual scene berhasil

        Catatan: QC_MIN_DURATION sengaja rendah (integritas, bukan konten). Bila ingin
        kebijakan "durasi minimal untuk engagement", itu target SOFT di script word-count
        (STEP 3), BUKAN hard-discard setelah render dibayar.

        Returns: (passed, reason). passed=False → tidak dipublish, dicatat qc_failed (no crash).
        """
        # Ambang config-driven. Bila Duration Preset di-set (target_seconds) → QC RELATIF (§8):
        # durasi di dalam BAND titik-tengah (duration_model.band_video) + clip_count = visual_beats preset.
        # Tanpa preset → interim: floor integritas (deteksi render terpotong) + clips env default.
        from src.config import ambang as _ambang
        self._qc_kode, self._qc_param = None, None      # kode dwibahasa (§3.5); None = tak ada
        min_size_mb = _ambang.angka("qc_min_size_mb", 5)
        # [B6] F4 fix (mandat owner 2026-07-14): ambang ukuran SADAR-DURASI — basis env = per-60s
        # (60s→5MB tak berubah; 8s→0.67MB). Video 8s sehat (3.3MB) sempat dicap "render gagal?" oleh
        # ambang rata. Floor 0.3MB = deteksi file korup/kosong tetap hidup. Tanpa preset → perilaku lama.
        if target_seconds:
            min_size_mb = max(0.3, min_size_mb * float(target_seconds) / 60.0)
        max_dur     = _ambang.detik("qc_max_duration_sec", 180)
        min_clips   = int(expected_beats) if expected_beats else _ambang.angka("qc_min_clips", 6)

        # Check 1: File size — render korup/kosong
        try:
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            if size_mb < min_size_mb:
                return False, f"File terlalu kecil: {size_mb:.1f}MB < {min_size_mb}MB (render gagal?)"
        except Exception as e:
            return False, f"Tidak bisa baca file video: {e}"

        # Check 2 & 3: Durasi
        if duration_secs is not None:
            if target_seconds:
                # QC RELATIF ke preset = ATURAN TITIK-TENGAH OWNER (2026-07-29), bukan persen. SATU
                # sumber dengan gerbang pra-visual & resep naskah (`duration_model.band_video`) —
                # dulu tiga tempat memakai angka berbeda. Preset tak ada di tangga aktif → cek durasi
                # dilewati (jangan mengarang batas); integritas render tetap dijaga cek lain.
                from src.config.format_catalog import active_presets as _act_p
                from src.production.duration_model import band_video as _band
                _tangga = _act_p()
                if _tangga and int(target_seconds) in _tangga:
                    lo, hi = _band(target_seconds, _tangga)
                    if not (lo <= duration_secs <= hi):
                        _arah = "kepanjangan" if duration_secs > hi else "kependekan"
                        # KODE + PARAMETER supaya layar tenant bisa menampilkannya DWIBAHASA (§3.5):
                        # sebelumnya hanya teks Indonesia yang dikirim, dan layar Review menampilkannya
                        # apa adanya → tenant berbahasa Inggris (3 dari 6 channel aktif) membaca bahasa
                        # yang tidak ia pakai. Teks Indonesia tetap dikirim sebagai cadangan, jadi data
                        # lama & pemanggil lama tidak berubah perilakunya (nol regresi).
                        self._qc_kode = ("durasi_kepanjangan" if duration_secs > hi else "durasi_kependekan")
                        self._qc_param = {"durasi": round(float(duration_secs), 1),
                                          "preset": int(target_seconds),
                                          # SATU DESIMAL, bukan bulat: setiap batas band berakhir di
                                          # ",50" (titik tengah antar-preset), dan pembulatan Python
                                          # membuatnya kadang melebar kadang menyempit (82,5→82 tapi
                                          # 97,5→98). Terukur 2026-08-01: video 82,1 dtk DITOLAK
                                          # sementara tenant diberi tahu "masih sah 82–98 detik" —
                                          # angka yang ditampilkan membantah vonisnya sendiri.
                                          "min": round(lo, 1), "maks": round(hi, 1)}
                        return False, (f"Durasi {duration_secs:.1f}s {_arah} untuk preset {target_seconds}s "
                                       f"(masih sah {lo:.1f}–{hi:.1f}s — di luar itu lebih dekat ke preset lain)")
            else:
                # Interim (tanpa preset): floor integritas (deteksi render terpotong-total)
                min_dur = _ambang.detik("qc_min_duration_sec", 3)
                if duration_secs < min_dur:
                    return False, f"Durasi tak wajar (render terpotong?): {duration_secs:.1f}s < {min_dur}s"
            # Batas atas PLATFORM (bukan batas preset): hanya berlaku bila preset TIDAK di-set, atau
            # bila preset itu sendiri di bawah batas. Dulu 180s rata → preset panjang (Regular, 2–12
            # menit) akan SELALU ditolak di sini sebelum apa pun sempat dinilai.
            if duration_secs > max_dur and (not target_seconds or float(target_seconds) <= max_dur):
                return False, f"Durasi terlalu panjang: {duration_secs:.1f}s > {max_dur}s (bukan Shorts)"

        # Check 4: Jumlah clips — semua scene berhasil (relatif preset visual_beats bila ada)
        if clip_count is not None and clip_count < min_clips:
            return False, (
                f"Visual tidak lengkap: {clip_count}/{min_clips} clips berhasil "
                f"(scene gagal kemungkinan ditolak content policy provider gambar)."
            )

        # Check 5 (integritas render — QC v2 Lapis 1/3): render bisa "lolos size" tapi RUSAK
        # senyap — tanpa stream audio, atau aspect bukan vertikal. Config-driven; bila ffprobe
        # gagal probe → SKIP (fail-open, jangan blokir produksi karena tool error).
        streams = self._probe_streams(video_path)
        if streams is not None:
            if not streams["has_video"]:
                return False, "Render rusak: tidak ada stream VIDEO"
            if _ambang.saklar("qc_require_audio", True) and not streams["has_audio"]:
                return False, "Render rusak: tidak ada stream AUDIO (TTS tak ter-mux?)"
            w, h = streams["width"], streams["height"]
            if w and h:
                target = self._aspect_ratio(_ambang.teks("qc_aspect", "9:16"))   # w/h
                tol    = _ambang.pct("qc_aspect_tolerance_pct", 5)
                if target and abs((w / h) - target) > tol:
                    return False, f"Aspect salah: {w}x{h} (rasio {w/h:.3f}) ≠ target {_ambang.teks('qc_aspect', '9:16')} ({target:.3f})"

        return True, "ok"

    @staticmethod
    def _aspect_ratio(spec: str) -> float | None:
        """Parse 'W:H' (mis. '9:16') → rasio w/h (0.5625). None bila tak valid."""
        try:
            w, h = [float(x) for x in str(spec).split(":")[:2]]
            return w / h if h else None
        except Exception:
            return None

    def _probe_streams(self, video_path: str):
        """Cek stream via ffprobe → {has_video, has_audio, width, height}. None bila probe gagal."""
        import subprocess
        import json as _json
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                return None
            streams = _json.loads(res.stdout).get("streams", [])
            v = next((s for s in streams if s.get("codec_type") == "video"), None)
            return {
                "has_video": v is not None,
                "has_audio": any(s.get("codec_type") == "audio" for s in streams),
                "width":     int(v["width"]) if v and v.get("width") else 0,
                "height":    int(v["height"]) if v and v.get("height") else 0,
            }
        except Exception as e:
            logger.warning(f"[Pipeline] _probe_streams gagal (skip cek stream/aspect): {e}")
            return None

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
