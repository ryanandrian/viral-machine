"""
Visual Assembler — selector dan fallback handler untuk visual provider.
v0.2:
  - Visual mode: 'video' | 'ai_image:*' | 'ai_video:*'
  - Fallback hierarchy: provider user → Pexels gratis → cache → black screen
  - Real-time reporting setiap kondisi khusus
"""

import asyncio
import os
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig

load_dotenv()

# Path fallback black screen (dibuat jika dibutuhkan)
BLACK_SCREEN_CLIP = "logs/fallback_black.mp4"


class VisualAssembler:
    """
    Selector + fallback handler untuk visual provider.
    Tidak pernah crash — selalu return minimal 1 clip.
    """

    def assemble(
        self,
        script: dict,
        tenant_config: TenantConfig,
        output_dir: str = "logs",
        audio_duration: float = 0.0,
    ) -> list[str]:
        """
        Download/generate video clips dengan fallback hierarchy.

        Fallback:
          1. Provider pilihan user (dari tenant_configs.visual_mode)
          2. Pexels gratis (jika provider user gagal)
          3. Clips cache dari run sebelumnya
          4. Black screen (last resort — pipeline tetap jalan)

        Returns:
            List path clip (string) — selalu minimal 1 item
        """
        run_config  = self._load_run_config(tenant_config)
        visual_mode = run_config.get("visual_mode", "video")
        self._current_audio_duration = audio_duration
        max_clip_mb = run_config.get("visual_max_clip_mb", 150)
        is_dev      = run_config.get("is_developer", False)

        logger.info(
            f"[VisualAssembler] mode={visual_mode} "
            f"max={max_clip_mb}MB"
            f"{' [DEVELOPER]' if is_dev else ''}"
        )

        clips_dir = Path(output_dir) / f"clips_{tenant_config.tenant_id}"

        # Provider pilihan user — satu-satunya sumber clips.
        # Tidak ada fallback ke provider lain (Pexels, cache, black screen).
        # Kualitas konten non-negotiable: jika gagal → return [] →
        # pipeline raise exception → Telegram notify → user retry manual.
        clips = self._try_provider(
            visual_mode=visual_mode,
            script=script,
            tenant_config=tenant_config,
            clips_dir=clips_dir,
            max_clip_mb=max_clip_mb,
            run_config=run_config,
        )

        paths = [str(c) for c in clips]
        logger.info(f"[VisualAssembler] Assembly complete: {len(paths)}/6 clips")
        return paths

    # ──────────────────────────────────────────────
    # Provider handlers
    # ──────────────────────────────────────────────

    def _try_provider(
        self,
        visual_mode: str,
        script: dict,
        tenant_config: TenantConfig,
        clips_dir: Path,
        max_clip_mb: int,
        run_config: dict,
    ) -> list[Path]:
        """Coba provider sesuai visual_mode."""
        try:
            if visual_mode == "video":
                return self._try_pexels(
                    script, tenant_config, clips_dir, max_clip_mb, run_config
                )
            elif visual_mode.startswith("ai_image:"):
                return self._try_ai_image(
                    visual_mode, script, tenant_config, clips_dir, run_config
                )
            elif visual_mode.startswith("ai_video:"):
                logger.warning(
                    f"[VisualAssembler] AI Video provider DISABLED v0.2 — "
                    f"fallback ke Pexels"
                )
                return []
            else:
                logger.warning(
                    f"[VisualAssembler] visual_mode '{visual_mode}' tidak dikenal — "
                    f"fallback ke Pexels"
                )
                return []
        except Exception as e:
            logger.error(f"[VisualAssembler] Provider error: {e}")
            return []

    def _try_pexels(
        self,
        script: dict,
        tenant_config: TenantConfig,
        clips_dir: Path,
        max_clip_mb: int,
        run_config: dict,
    ) -> list[Path]:
        """Download clips dari Pexels."""
        try:
            from src.providers.visual.pexels import PexelsProvider

            config   = {
                "tenant_id":          tenant_config.tenant_id,
                "niche":              tenant_config.niche,
                "visual_provider":    "pexels",
                "visual_max_clip_mb": max_clip_mb,
                "visual_api_key":     (
                    run_config.get("visual_api_key")
                    or os.getenv("PEXELS_API_KEY", "")
                ),
            }
            provider = PexelsProvider(config)
            keywords = provider.extract_keywords_from_script(script, tenant_config.niche)
            logger.info(f"Searching footage: {keywords[:3]}")

            clips = asyncio.run(
                provider.fetch_clips(keywords=keywords, count=6, output_dir=clips_dir)
            )
            return [clip.path for clip in clips]

        except Exception as e:
            logger.error(f"[VisualAssembler] Pexels error: {e}")
            return []

    def _compute_clip_durations(self, script: dict, n_clips: int = 6, audio_duration: float = 0.0) -> list[float]:
        """
        Fase 6C s6c2: hitung durasi per clip dari section_durations script.
        Mapping 6 clips ke 8 sections — sections pendek digabung.
        """
        sd = script.get("section_durations", {})
        if not sd or len(sd) < 6:
            return []  # Fallback ke pembagian rata di renderer

        hook      = float(sd.get("hook", 3))
        mystery   = float(sd.get("mystery_drop", 5))
        buildup   = float(sd.get("build_up", 12))
        interrupt = float(sd.get("pattern_interrupt", 2))
        core      = float(sd.get("core_facts", 15))
        bridge    = float(sd.get("curiosity_bridge", 3))
        climax    = float(sd.get("climax", 8))
        cta       = float(sd.get("cta", 3))

        # Mapping 6 clips: gabung sections pendek agar tiap clip punya durasi wajar
        durations = [
            hook,                          # Clip 1: hook
            mystery,                       # Clip 2: mystery drop
            buildup,                       # Clip 3: build up
            round(interrupt + core / 2, 2),# Clip 4: interrupt + core awal
            round(core / 2 + bridge, 2),   # Clip 5: core akhir + bridge
            round(climax + cta, 2),        # Clip 6: climax + cta
        ]

        total = sum(durations)
        logger.info(
            f"[VisualAssembler] section_durations → clip_durations: "
            f"{durations} = {total:.1f}s"
        )
        # Scale clip durations agar total = audio_duration aktual
        if audio_duration > 0:
            total_raw = sum(durations)
            scale     = audio_duration / total_raw if total_raw > 0 else 1.0
            durations = [round(d * scale, 4) for d in durations]
            logger.info(
                f"[VisualAssembler] Scaled durations: {durations} "
                f"= {sum(durations):.1f}s (audio: {audio_duration:.1f}s)"
            )
        return durations

    def _try_ai_image(
        self,
        visual_mode: str,
        script: dict,
        tenant_config: TenantConfig,
        clips_dir: Path,
        run_config: dict,
    ) -> list[Path]:
        """Generate gambar AI + Ken Burns effect."""
        try:
            from src.providers.visual.ai_image import AIImageProvider

            config = {
                "tenant_id":              tenant_config.tenant_id,
                "niche":                  tenant_config.niche,
                "visual_provider":        visual_mode,
                "visual_ai_model":        visual_mode.split(":", 1)[1] if ":" in visual_mode else "dall-e-3",
                "visual_api_key":         run_config.get("visual_api_key"),
                "llm_api_key":            run_config.get("llm_api_key") or "",
                "llm_provider":           run_config.get("llm_provider", "openai"),
                "niche_visual_style":     run_config.get("niche_visual_style") or {},
                "niche_visual_fallbacks": run_config.get("niche_visual_fallbacks") or [],
            }
            provider  = AIImageProvider(config)
            keywords  = provider.extract_keywords_from_script(script, tenant_config.niche)
            clip_durs = self._compute_clip_durations(script, n_clips=6, audio_duration=self._current_audio_duration)

            logger.info(
                f"[VisualAssembler] Generating AI images: "
                f"{visual_mode} — {len(keywords)} scenes"
            )

            clips = asyncio.run(
                provider.fetch_clips(
                    keywords=keywords,
                    count=6,
                    output_dir=clips_dir,
                    clip_durations=clip_durs,
                )
            )

            if clips:
                logger.info(
                    f"[VisualAssembler] ✅ AI Image generated: "
                    f"{len(clips)} clips via {visual_mode}"
                )

                # ── s6c7: Hook frame optimization ─────────────────────
                # Replace clips[0] dengan hero image khusus dari hook text
                # Lebih scroll-stopping dari visual_suggestion generik
                hook_clip = self._generate_hook_frame(
                    script=script,
                    clips_dir=clips_dir,
                    config=config,
                    clip_durs=clip_durs,
                )
                if hook_clip:
                    clips[0] = hook_clip
                    logger.info(f"[VisualAssembler] s6c7 ✅ Hook frame replaced clips[0]")

            return [clip.path for clip in clips]

        except Exception as e:
            logger.error(f"[VisualAssembler] AI Image error: {e}")
            return []

    def _generate_hook_frame(
        self,
        script: dict,
        clips_dir: Path,
        config: dict,
        clip_durs: list[float],
    ):
        """
        Fase 6C s6c7: Generate hero image khusus untuk frame pertama.
        Prompt dibangun dari hook text aktual — bukan visual_suggestion generik.
        Hanya aktif saat visual_mode = ai_image:*.
        """
        try:
            from src.providers.visual.ai_image import AIImageProvider, VideoClip

            hook_text = script.get("hook", "").strip()
            # s72: thumbnail_concept = deskripsi visual murni dari script engine
            # Mencegah DALL-E render teks literal dari kalimat hook
            thumbnail_concept = script.get("thumbnail_concept", "").strip() or hook_text
            niche     = config.get("niche", "universe_mysteries")

            if not hook_text:
                return None

            # Hook frame prompt — dibangun dari niche visual_style Supabase (tidak hardcode)
            niche_vs   = config.get("niche_visual_style") or {}
            base_style = niche_vs.get("base_style", "documentary photography style, cinematic")
            color_pal  = niche_vs.get("color_palette", "natural cinematic colors")
            atmosphere = niche_vs.get("atmosphere", "dramatic cinematic atmosphere")

            prompt = (
                f"Cinematic vertical 9:16 hero image. "
                f"{thumbnail_concept}. "
                f"Style: {base_style}. "
                f"Color palette: {color_pal}. "
                f"Atmosphere: {atmosphere}. "
                f"Single striking focal point that stops the scroll instantly. "
                f"Photorealistic. "
                f"No text, no words, no letters, no numbers, no signs, no typography. No people."
            )
            provider  = AIImageProvider(config)
            img_path  = clips_dir / "hook_frame_img.jpg"
            clip_path = clips_dir / "clip_01_hook.mp4"

            # Durasi = durasi section hook (default 3 detik)
            hook_duration = clip_durs[0] if clip_durs else 3.0

            import asyncio
            asyncio.run(provider._generate_image(prompt, img_path))
            provider._image_to_video(img_path, clip_path, duration=hook_duration)

            from src.providers.visual.base import VideoClip
            size_mb = clip_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"[s6c7] Hook frame: {clip_path.name} ({size_mb:.1f}MB) "
                f"{hook_duration}s | prompt: '{hook_text[:60]}...'"
            )

            return VideoClip(
                path=clip_path,
                duration=hook_duration,
                width=1080,
                height=1920,
                file_size_mb=round(size_mb, 1),
                source_url="ai_generated:hook_frame",
                provider=config.get("visual_provider", "ai_image"),
            )

        except Exception as e:
            logger.warning(f"[s6c7] Hook frame generation failed ({e}) — keeping original clips[0]")
            return None

    # ──────────────────────────────────────────────
    # Config loader
    # ──────────────────────────────────────────────

    def _load_run_config(self, tenant_config: TenantConfig) -> dict:
        """Baca config dari Supabase, fallback ke defaults."""
        try:
            from src.config.tenant_config import load_tenant_config
            rc = load_tenant_config(tenant_config.tenant_id)
            return {
                "visual_mode":            getattr(rc, "visual_mode", "video"),
                "visual_max_clip_mb":     rc.visual_max_clip_mb,
                "visual_api_key":         rc.visual_api_key,
                "llm_api_key":            rc.llm_api_key,
                "llm_provider":           getattr(rc, "llm_provider", "openai"),
                "niche_visual_style":     getattr(rc, "niche_visual_style", {}) or {},
                "niche_visual_fallbacks": getattr(rc, "niche_visual_fallbacks", []) or [],
                "is_developer":           getattr(rc, "is_developer", False),
            }
        except Exception:
            return {
                "visual_mode":            "video",
                "visual_max_clip_mb":     150,
                "visual_api_key":         None,
                "llm_api_key":            None,
                "llm_provider":           "openai",
                "niche_visual_style":     {},
                "niche_visual_fallbacks": [],
                "is_developer":           False,
            }
