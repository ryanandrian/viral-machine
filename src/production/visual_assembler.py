"""
Visual Assembler — selector provider visual (GENERATOR AI saja).
v2:
  - Visual mode: 'ai_image:*' | 'ai_video:*' (stock footage Pexels = fosil v1, dibuang 2026-06-24)
  - NO-FALLBACK (§3.8): provider pilihan channel = satu-satunya sumber; gagal → [] → pipeline
    raise → notify → retry manual. Tak ada fallback diam-diam (Pexels/cache/black screen).
  - Real-time reporting setiap kondisi khusus
"""

import asyncio
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

from src.intelligence.config import TenantConfig

load_dotenv()


class VisualAssembler:
    """Selector provider visual (generator AI). NO-FALLBACK: gagal = gagal jujur (return [])."""

    def assemble(
        self,
        script: dict,
        tenant_config: TenantConfig,
        output_dir: str = "logs",
        audio_duration: float = 0.0,
    ) -> list[str]:
        """
        Generate video clips dari provider GENERATOR AI pilihan channel.

        NO-FALLBACK (§3.8): provider channel (visual_mode) = satu-satunya sumber.
        Gagal → return [] → pipeline raise exception → Telegram notify → user retry manual.

        Returns:
            List path clip (string).
        """
        run_config  = self._load_run_config(tenant_config)
        visual_mode = run_config.get("visual_mode") or ""
        self._current_audio_duration = audio_duration
        is_dev      = run_config.get("is_developer", False)

        logger.info(f"[VisualAssembler] mode={visual_mode}{' [DEVELOPER]' if is_dev else ''}")

        clips_dir = Path(output_dir) / f"clips_{tenant_config.tenant_id}"

        # Provider GENERATOR AI pilihan channel — satu-satunya sumber clips.
        # NO-FALLBACK: gagal → return [] → pipeline raise → Telegram notify → user retry manual.
        clips = self._try_provider(
            visual_mode=visual_mode,
            script=script,
            tenant_config=tenant_config,
            clips_dir=clips_dir,
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
        run_config: dict,
    ) -> list[Path]:
        """Coba provider GENERATOR AI sesuai visual_mode (no-fallback)."""
        try:
            if visual_mode.startswith("ai_image:"):
                return self._try_ai_image(
                    visual_mode, script, tenant_config, clips_dir, run_config
                )
            elif visual_mode.startswith("ai_video:"):
                logger.warning("[VisualAssembler] AI Video provider DISABLED v2 — gagal jujur (no-fallback)")
                return []
            else:
                logger.warning(
                    f"[VisualAssembler] visual_mode '{visual_mode}' tak dikenal — "
                    f"gagal jujur (no-fallback)"
                )
                return []
        except Exception as e:
            logger.error(f"[VisualAssembler] Provider error: {e}")
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
        # Scale clip durations agar total = audio_duration + xfade_loss
        # xfade_loss = (n-1) × 0.4s — dikompensasi agar Step A xfade output = audio_duration
        if audio_duration > 0:
            xfade_loss = (n_clips - 1) * 0.4 if n_clips >= 2 else 0.0
            target_total = audio_duration + xfade_loss
            total_raw = sum(durations)
            scale     = target_total / total_raw if total_raw > 0 else 1.0
            durations = [round(d * scale, 4) for d in durations]
            logger.info(
                f"[VisualAssembler] Scaled durations: {durations} "
                f"= {sum(durations):.1f}s (audio: {audio_duration:.1f}s + xfade_loss: {xfade_loss:.1f}s)"
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
            from src.providers.visual import build_visual_provider

            config = {
                "tenant_id":              tenant_config.tenant_id,
                "niche":                  tenant_config.niche,
                "visual_provider":        visual_mode,
                "visual_ai_model":        visual_mode.split(":", 1)[1] if ":" in visual_mode else "",
                "visual_api_key":         run_config.get("visual_api_key"),
                "llm_api_key":            run_config.get("llm_api_key") or "",
                "llm_library":            run_config.get("llm_library") or "",
                "llm_provider":           run_config.get("llm_provider") or "",
                "llm_models":             run_config.get("llm_models") or {},
                "niche_visual_style":     run_config.get("niche_visual_style") or {},
                "niche_visual_fallbacks": run_config.get("niche_visual_fallbacks") or [],
                "image_quality":          run_config.get("image_quality") or "",
                "visual_seed":            getattr(tenant_config, "visual_seed", None),  # Diversity §9.1
            }
            provider  = build_visual_provider(visual_mode, config)   # F5-06: registry
            # Image-gen PER-PRESET (MULTI_FORMAT §3): jumlah image = N beat (= visual_beats), durasi
            # per-beat dari pipeline (script.beat_durations, SINKRON TTS via word_timestamps). Fallback
            # ke _compute_clip_durations (6) bila beat_durations tak ada (legacy/no-preset).
            #
            # PENTING (sinkron bake↔concat): beat_durations = TTS-synced MENTAH (sum = audio_duration).
            # Source clip WAJIB di-bake dengan kompensasi xfade-loss IDENTIK dgn renderer._create_clip_list
            # (target = audio + (N-1)*0.4s). Tanpa ini: bake sum=audio, tapi clip_list scale ke audio+loss
            # → durasi bake < durasi list → xfade "makan" konten → video pendek (terbukti N=9/90s: -9s).
            # _compute_clip_durations (legacy) SUDAH ter-scale ke target ini, jadi hanya cabang
            # beat_durations yang perlu di-scale di sini.
            beat_durs = script.get("beat_durations")
            if beat_durs:
                clip_durs = [float(d) for d in beat_durs]
                ad = self._current_audio_duration
                if ad and ad > 0:
                    xfade_loss = (len(clip_durs) - 1) * 0.4 if len(clip_durs) >= 2 else 0.0
                    target     = ad + xfade_loss
                    raw_sum    = sum(clip_durs)
                    if raw_sum > 0:
                        clip_durs = [round(d * target / raw_sum, 4) for d in clip_durs]
            else:
                clip_durs = self._compute_clip_durations(
                    script, n_clips=6, audio_duration=self._current_audio_duration)
            n_img     = len(clip_durs) if clip_durs else 6
            keywords  = provider.extract_keywords_from_script(script, tenant_config.niche, n=n_img)
            beats     = script.get("beats") or []

            logger.info(
                f"[VisualAssembler] Generating AI images: "
                f"{visual_mode} — {n_img} scenes (beat-synced per-preset, beat-role motion)"
            )

            clips_dir.mkdir(parents=True, exist_ok=True)   # WAJIB sebelum hook-frame (A5 reorder: hook-frame kini sebelum fetch_clips yg biasanya mkdir)
            # A5 (Opsi A): clip[0] = HOOK-FRAME dari thumbnail_concept (= scene hook, dibuat SEKALI).
            # fetch HANYA scene beats[1:] → tak ada image yang dibuat-lalu-dibuang (boros).
            # A6: motion per-peran beat (beat_roles). Fallback aman: hook-frame gagal → fetch semua N
            # (satu jalur fetch saja → tanpa tabrakan penamaan clip).
            hook_clip = self._generate_hook_frame(
                script=script, clips_dir=clips_dir, config=config, clip_durs=clip_durs,
            )
            if hook_clip:
                scene_kw    = keywords[1:]
                scene_durs  = clip_durs[1:] if len(clip_durs) > 1 else []
                scene_roles = beats[1:] if len(beats) > 1 else []
                scene_clips = asyncio.run(
                    provider.fetch_clips(
                        keywords=scene_kw, count=len(scene_kw),
                        output_dir=clips_dir, clip_durations=scene_durs, beat_roles=scene_roles,
                    )
                ) if scene_kw else []
                clips = [hook_clip] + scene_clips
                logger.info(f"[VisualAssembler] s6c7 ✅ Hook-frame + {len(scene_clips)} scene (no waste)")
            else:
                logger.warning("[VisualAssembler] Hook-frame gagal → fetch semua N (clip0=thumbnail)")
                clips = asyncio.run(
                    provider.fetch_clips(
                        keywords=keywords, count=n_img,
                        output_dir=clips_dir, clip_durations=clip_durs, beat_roles=beats,
                    )
                )

            if clips:
                logger.info(
                    f"[VisualAssembler] ✅ AI Image generated: "
                    f"{len(clips)} clips via {visual_mode}"
                )

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
            from src.providers.visual import build_visual_provider

            hook_text = script.get("hook", "").strip()
            # s72: thumbnail_concept = deskripsi visual murni dari script engine
            # Mencegah DALL-E render teks literal dari kalimat hook
            thumbnail_concept = script.get("thumbnail_concept", "").strip() or hook_text
            niche     = config.get("niche") or config.get("niche_fallback") or ""

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
            provider  = build_visual_provider(config.get("visual_provider") or "ai_image:", config)   # F5-06: registry
            img_path  = clips_dir / "hook_frame_img.jpg"
            clip_path = clips_dir / "clip_01_hook.mp4"

            # Durasi = durasi section hook (default 3 detik)
            hook_duration = clip_durs[0] if clip_durs else 3.0

            import asyncio
            # Fix s1.6: _generate_image(prompt, negative_prompt, output_path) — sebelumnya
            # kurang arg negative_prompt → "missing output_path". Pakai _build_image_prompt
            # (quality tags + negative) konsisten dgn flow normal ai_image.
            positive, negative = provider._build_image_prompt(prompt)
            asyncio.run(provider._generate_image(positive, negative, img_path))
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
            rc = load_tenant_config(tenant_config.tenant_id, getattr(tenant_config, "channel_id", None), getattr(tenant_config, "niche", None))
            return {
                "visual_mode":            getattr(rc, "visual_mode", "") or "",
                "visual_api_key":         rc.visual_api_key,
                "llm_api_key":            rc.llm_api_key,
                "llm_library":            getattr(rc, "llm_library", None) or "",
                "llm_provider":           getattr(rc, "llm_provider", None) or "",
                "llm_models":             getattr(rc, "llm_models", None) or {},
                "niche_visual_style":     getattr(rc, "niche_visual_style", {}) or {},
                "niche_visual_fallbacks": getattr(rc, "niche_visual_fallbacks", []) or [],
                "is_developer":           getattr(rc, "is_developer", False),
                "image_quality":          getattr(rc, "image_quality", None) or "",
            }
        except Exception:
            return {
                "visual_mode":            "",
                "visual_api_key":         None,
                "llm_api_key":            None,
                "llm_library":            "",
                "llm_provider":           "",
                "llm_models":             {},
                "niche_visual_style":     {},
                "niche_visual_fallbacks": [],
                "is_developer":           False,
                "image_quality":          "low",
            }
