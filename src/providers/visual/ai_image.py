"""
AI Image Visual Provider — generate gambar via AI + motion effect.

s85c: LLM-generated prompts — tidak ada template manual.
  - visual_suggestions dari script = full DALL-E 3 ready prompts (dibuat oleh LLM)
  - ai_image.py hanya terima dan pakai, tidak merangkai prompt
  - Rejection rewrite menggunakan LLM tenant (Claude atau OpenAI), tidak hardcode
"""

import asyncio
import os
import subprocess
from pathlib import Path

import httpx
from loguru import logger

from src.providers.visual.base import VisualProvider, VideoClip, VisualError


# Katalog model image = DB (ai_models, component='image') — admin-managed via migration/DB.
# Tidak ada registry hardcode di sini; di-load lewat catalog loader (Phase 1.3).

# Default quality tags dan negative prompt — dipakai jika niche belum punya custom value.
# Per-niche value disimpan di tabel niches Supabase (kolom image_quality_tags / image_negative_prompt).
_DEFAULT_QUALITY_TAGS = (
    "ultra detailed, highly textured, fine details, sharp focus, cinematic lighting, "
    "volumetric lighting, global illumination, soft shadows, high contrast, realistic textures, "
    "depth of field, professional composition, 50mm lens, ambient occlusion, natural color grading, "
    "realistic reflections, surface imperfections, micro details, immersive atmosphere, 8k detail"
)
_DEFAULT_NEGATIVE_PROMPT = (
    "blurry, low detail, flat lighting, distorted, deformed, unrealistic, bad proportions, "
    "text, words, letters, numbers, signs, logos, watermarks, typography"
)




class AIImageProvider(VisualProvider):
    """
    AI Image Generation + Motion Effect → Video clip.
    Fase 6C: Cinematic prompts per section type, niche-aware styling.
    """

    def __init__(self, config: dict):
        super().__init__(config)

        provider_str  = config.get("visual_provider") or ""
        parts         = provider_str.split(":", 1)
        self.ai_model = parts[1] if len(parts) > 1 else ""
        if not self.ai_model:
            raise VisualError(
                "Model image belum diset (visual_provider='ai_image:<model_key>')."
            )

        # Katalog model image dari DB (ai_models, component='image') — config-driven,
        # admin-managed. Dispatch generate pakai platform = provider_key.
        from src.providers.llm.catalog import get_models
        _row = get_models().get(self.ai_model)
        if not _row or _row.get("component") != "image":
            raise VisualError(
                f"Model image '{self.ai_model}' tidak ada / non-aktif di katalog ai_models."
            )
        self.model_config = {
            "platform": _row["provider_key"],
            "model_id": _row["model_id"],
            "size":     (_row.get("default_params") or {}).get("size", "1024x1536"),
        }
        self.image_quality      = config.get("image_quality") or "low"  # tenant setting (DB default 'low')
        self.visual_seed        = config.get("visual_seed")  # Diversity §9.1 — fingerprint; None=acak provider
        self.niche              = config.get("niche") or ""
        # Niche visual data — dari Supabase via TenantRunConfig (tidak hardcode)
        self.niche_visual_style     = config.get("niche_visual_style") or {}
        self.niche_visual_fallbacks = config.get("niche_visual_fallbacks") or []

        # Image quality tags dan negative prompt — per-niche dari Supabase
        try:
            from src.intelligence.config import get_niches
            _niche_data = get_niches().get(self.niche) or {}
            self.image_quality_tags    = _niche_data.get("image_quality_tags") or _DEFAULT_QUALITY_TAGS
            self.image_negative_prompt = _niche_data.get("image_negative_prompt") or _DEFAULT_NEGATIVE_PROMPT
        except Exception:
            self.image_quality_tags    = _DEFAULT_QUALITY_TAGS
            self.image_negative_prompt = _DEFAULT_NEGATIVE_PROMPT
        # LLM config — untuk rejection rewrite (pakai LLM tenant, bukan hardcode)
        # Key harus dari tenant DB — tidak ada env fallback (DESIGN.md)
        self.llm_provider   = config.get("llm_provider", "")
        self.llm_library    = config.get("llm_library")
        self.llm_api_key    = config.get("llm_api_key") or ""
        self.llm_models     = config.get("llm_models") or {}
        self.llm_model_flat = config.get("llm_model") or ""

        if self.model_config["platform"] == "replicate":
            self.api_key = (
                config.get("visual_api_key")
                or os.getenv("REPLICATE_API_TOKEN", "")
            )
        else:
            # OpenAI image: pakai visual_api_key — bukan llm_api_key
            # llm_api_key dipisah khusus untuk LLM (narasi + rejection rewrite)
            self.api_key = config.get("visual_api_key") or ""

        if not self.api_key:
            raise VisualError(
                f"AI Image ({self.ai_model}) membutuhkan API key. "
                f"Set visual_api_key (OpenAI key) di tenant_configs Supabase."
            )

        logger.info(
            f"[AIImage] Initialized: model={self.ai_model} niche={self.niche}"
        )

    async def fetch_clips(
        self,
        keywords: list[str],
        count: int,
        output_dir: Path,
        clip_durations: list[float] | None = None,
        beat_roles: list[str] | None = None,
    ) -> list[VideoClip]:
        """
        Generate gambar AI per section → convert ke video dengan motion.
        keywords       = visual_suggestions dari script (sinematik dari s6c6).
        clip_durations = durasi per clip dari section_durations script (s6c2).
                         Jika None → fallback ke 5.0 detik per clip.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        def _dur(i: int) -> float:
            """Durasi per clip dari section_durations (s6c2); fallback 5.0s."""
            return clip_durations[i] if (clip_durations and i < len(clip_durations)) else 5.0

        async def _gen_image(i: int, keyword: str) -> tuple[int, "Path | None", str]:
            """
            Hasilkan 1 IMAGE (I/O-bound). Retry attempt 2-3 = LLM rewrite dgn rejection_history
            (makin tahu apa yang dihindari). TIDAK ada fallback provider/visual_fallbacks — visual
            harus relevan + kualitas non-negotiable. Gagal 3× → (i, None) (scene di-skip).
            Return (i, image_path|None, source_tag). NB: image→video (CPU) dilakukan TERPISAH (Phase 2).
            """
            positive_prompt, negative_prompt = self._build_image_prompt(keyword)
            img_path = output_dir / f"ai_img_{i+1:02d}.jpg"
            logger.info(f"[AIImage:{self.ai_model}] Scene {i+1}/{count} | duration={_dur(i)}s")
            logger.debug(f"[AIImage] Prompt: {positive_prompt[:120]}...")
            try:
                await self._generate_image(positive_prompt, negative_prompt, img_path)
                return (i, img_path, f"ai_generated:{self.ai_model}")
            except Exception as e:
                rejection_history = [{"prompt": positive_prompt, "rejection": str(e)}]
                safe_positive = positive_prompt
                for attempt in range(2, 4):  # attempt 2 dan 3
                    try:
                        logger.warning(
                            f"[AIImage] Scene {i+1} attempt {attempt-1} gagal — "
                            f"rewrite via {self.llm_provider} (attempt {attempt}/3)"
                        )
                        rewritten_main = await self._ai_rewrite_on_rejection(
                            original_keyword=keyword, section_index=i,
                            rejection_history=rejection_history,
                        )
                        safe_positive, safe_negative = self._build_image_prompt(rewritten_main)
                        safe_output = output_dir / f"ai_img_{i+1:02d}_attempt{attempt}.jpg"
                        await self._generate_image(safe_positive, safe_negative, safe_output)
                        logger.info(f"[AIImage] ✅ Scene {i+1} image berhasil pada attempt {attempt}")
                        return (i, safe_output, f"ai_generated:retry_{attempt}")
                    except Exception as retry_err:
                        rejection_history.append({"prompt": safe_positive, "rejection": str(retry_err)})
                        logger.warning(f"[AIImage] Scene {i+1} attempt {attempt} gagal: {retry_err}")
                logger.error(f"[AIImage] Scene {i+1} GAGAL setelah 3 attempt — scene di-skip")
                return (i, None, "")

        # ── Phase 1: generate SEMUA image KONKUREN (I/O-bound — decisions_production_scaling §5: 10→2mnt).
        #    Aman: ini tunggu API (bukan CPU); concurrency I/O boleh tinggi (§3).
        gen_results = await asyncio.gather(*[
            _gen_image(i, kw) for i, kw in enumerate(keywords[:count])
        ])

        # ── Phase 2: image→video Ken Burns SEKUENSIAL (CPU-bound ffmpeg).
        #    SENGAJA tidak diparalelkan → jaga rem anti-OOM "concurrency render = core" (§3);
        #    paralel ffmpeg di sini = spike CPU yang dilarang arsitektur produksi.
        clips: list[VideoClip] = []
        for i, img_path, source_tag in sorted(gen_results, key=lambda r: r[0]):
            if img_path is None:
                continue
            duration  = _dur(i)
            role      = beat_roles[i] if (beat_roles and i < len(beat_roles)) else ""
            clip_path = output_dir / f"clip_{i+1:02d}_ai.mp4"
            try:
                self._image_to_video(img_path, clip_path, duration=duration, clip_index=i, role=role)
                size_mb = clip_path.stat().st_size / (1024 * 1024)
                clips.append(VideoClip(
                    path=clip_path, duration=duration, width=1080, height=1920,
                    file_size_mb=round(size_mb, 1), source_url=source_tag,
                    provider=self.provider_name,
                ))
                logger.info(f"[AIImage] ✓ Scene {i+1}: {clip_path.name} ({size_mb:.1f}MB) {duration}s")
            except Exception as e:
                logger.error(f"[AIImage] Scene {i+1} image→video gagal: {e} — scene di-skip")
                continue

        logger.info(f"[AIImage] Complete: {len(clips)}/{count} clips (image-gen paralel I/O, convert sekuensial CPU)")
        return clips

    def extract_keywords_from_script(self, script: dict, niche: str, n: int = 6) -> list[str]:
        """
        Extract visual subjects dari script.
        Priority: visual_suggestions dari script (sudah sinematik dari s6c6).
        Return tepat N items (= visual_beats preset; 1 image per beat — image-gen per-preset MULTI_FORMAT §3).
        """
        keywords = []

        # Priority 1: visual_suggestions dari script engine
        # Script engine v0.3.1 sudah menghasilkan suggestions yang sinematik
        suggestions = script.get("visual_suggestions", [])
        if isinstance(suggestions, list):
            for s in suggestions:
                if s and isinstance(s, str) and len(s) > 5:
                    keywords.append(s.strip())

        logger.info(
            f"[AIImage] visual_suggestions dari script: {len(keywords)} items"
        )

        # Priority 2: fallback ke niche visual_fallbacks dari Supabase jika kurang dari N
        if len(keywords) < n:
            fallbacks = self.niche_visual_fallbacks
            for fb in fallbacks:
                if len(keywords) >= n:
                    break
                if fb not in keywords:
                    keywords.append(fb)
            logger.info(f"[AIImage] Setelah fallback: {len(keywords)} items (target {n})")

        return keywords[:n]

    async def _ai_rewrite_on_rejection(
        self,
        original_keyword: str,
        section_index: int,
        rejection_history: list[dict],
    ) -> str:
        """
        Kirim penolakan dari image generator kembali ke LLM tenant.
        LLM yang berpikir ulang — pakai Claude atau OpenAI sesuai config tenant.

        rejection_history: list of {"prompt": str, "rejection": str}
        Returns: full DALL-E ready prompt baru (langsung siap dipakai)
        """
        section_names = ["hook", "mystery", "build-up", "core facts", "tension", "climax"]
        section_name  = section_names[min(section_index, 5)]
        niche_style   = self.niche_visual_style
        base_style    = niche_style.get("base_style", "documentary photography")
        atmosphere    = niche_style.get("atmosphere", "cinematic")

        rejection_context = "\n".join([
            f"Attempt {idx+1}:\n  Prompt: \"{r['prompt'][:200]}\"\n  Rejected because: {r['rejection'][:200]}"
            for idx, r in enumerate(rejection_history)
        ])

        system_prompt = (
            "You are a visual prompt engineer for DALL-E 3. "
            "An image generator rejected your prompt. "
            "Create a new complete DALL-E 3 prompt that conveys the same narrative concept "
            "but avoids the rejection reason. "
            "Use environmental cues, abstract elements, scale, light, and texture instead of direct depiction. "
            "Output ONLY the new complete DALL-E 3 prompt, 2-3 sentences, no explanation."
        )
        user_prompt = (
            f"Original prompt (rejected): \"{original_keyword}\"\n"
            f"Scene: {section_name} (scene {section_index+1}/6)\n"
            f"Visual style: {base_style}\n"
            f"Atmosphere: {atmosphere}\n\n"
            f"Rejection history:\n{rejection_context}\n\n"
            f"Write ONLY the main prompt (2-3 sentences). "
            f"Do not include quality tags or negative instructions — those are added automatically. "
            f"End with: vertical 9:16, photorealistic."
        )

        # Rejection rewrite pakai LLM tenant via factory tunggal (config-driven).
        # Provider memegang SDK client + format API — di sini tak ada nama SDK.
        from src.providers.llm import build_llm_provider, LLMError

        rewrite_model = self.llm_models.get("rewrite") or self.llm_model_flat
        try:
            provider = build_llm_provider({
                "llm_library":  self.llm_library,
                "llm_provider": self.llm_provider,
                "llm_api_key":  self.llm_api_key,
                "llm_model":    self.llm_model_flat,
            })
            rewritten = provider.complete(
                system=system_prompt,
                user=user_prompt,
                model=rewrite_model,
                max_tokens=200,
                temperature=0.7,
            ).strip().strip('"')
        except LLMError as e:
            raise VisualError(f"Rejection rewrite gagal — LLM error: {e}") from e

        logger.info(
            f"[AIImage] {provider.provider_name} rewrite scene {section_index+1} "
            f"(attempt {len(rejection_history)+1}): {rewritten[:120]}"
        )
        return rewritten  # full image-ready prompt

    def _build_image_prompt(self, main_prompt: str) -> tuple[str, str]:
        """
        Bangun prompt 3-bagian: [PROMPT UTAMA] + [QUALITY TAGS] + [NEGATIVE PROMPT].
        Returns: (positive_prompt, negative_prompt)
        Quality tags dan negative prompt diambil dari niche (Supabase) atau default.
        """
        positive = f"{main_prompt}\n\n{self.image_quality_tags}"
        return positive, self.image_negative_prompt

    @property
    def provider_name(self) -> str:
        return f"ai_image:{self.ai_model}"

    @property
    def is_ai_generated(self) -> bool:
        return True

    @property
    def is_enabled(self) -> bool:
        return True

    # ──────────────────────────────────────────────
    # Internal: generate image
    # ──────────────────────────────────────────────

    async def _generate_image(self, prompt: str, negative_prompt: str, output_path: Path) -> None:
        platform = self.model_config["platform"]
        if platform == "replicate":
            await self._generate_replicate(prompt, negative_prompt, output_path)
        elif platform == "openai":
            await self._generate_dalle(prompt, negative_prompt, output_path)
        else:
            raise VisualError(f"Platform tidak dikenal: {platform}")

    async def _generate_replicate(self, prompt: str, negative_prompt: str, output_path: Path) -> None:
        try:
            import replicate
        except ImportError:
            raise VisualError("replicate tidak terinstall. Jalankan: pip install replicate")

        os.environ["REPLICATE_API_TOKEN"] = self.api_key
        _input = {
            "prompt":          prompt,
            "negative_prompt": negative_prompt,
            "aspect_ratio":    "9:16",
        }
        if self.visual_seed is not None:
            _input["seed"] = int(self.visual_seed)   # Diversity §9.1 — frame fingerprint per video
        output = await asyncio.to_thread(
            replicate.run,
            self.model_config["model_id"],
            input=_input,
        )
        img_url = output[0] if isinstance(output, list) else str(output)
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(img_url)
            output_path.write_bytes(r.content)

    async def _generate_dalle(self, prompt: str, negative_prompt: str, output_path: Path) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise VisualError("openai tidak terinstall. Jalankan: pip install openai")

        # OpenAI tidak support parameter negative_prompt terpisah —
        # digabung ke prompt utama sebagai instruksi eksplisit.
        full_prompt = f"{prompt}\n\nStrictly avoid: {negative_prompt}"

        size = self.model_config.get("size", "1024x1536")

        async with AsyncOpenAI(api_key=self.api_key) as client:
            response = await client.images.generate(
                model=self.model_config["model_id"],
                prompt=full_prompt,
                size=size,
                quality=self.image_quality,
                n=1,
            )
            item = response.data[0]
            if item.b64_json:
                import base64
                output_path.write_bytes(base64.b64decode(item.b64_json))
            elif item.url:
                async with httpx.AsyncClient(timeout=60) as http:
                    r = await http.get(item.url)
                    output_path.write_bytes(r.content)
            else:
                raise VisualError("Response tidak mengandung b64_json maupun url")

    # ──────────────────────────────────────────────
    # Internal: image → video dengan Ken Burns effect
    # ──────────────────────────────────────────────

    @staticmethod
    def _image_to_video(
        img_path: Path,
        output_path: Path,
        duration: float = 5.0,
        clip_index: int = 0,
        role: str = "",
    ) -> None:
        """
        Konversi gambar → video 9:16 dengan Ken Burns effect.
        A6 (Opsi A): motion BEAT-ROLE-aware — gerakan dipilih dari PERAN beat (hook/climax/…),
        bukan posisi idx%6, agar cocok narasi di semua preset (3-9 beat). Unknown/kosong → idx%6.
        """
        fps    = 30
        frames = int(duration * fps)
        # role → indeks SECTION_MOTIONS (reuse ekspresi zoompan terbukti); fallback idx%6 non-breaking.
        _ROLE_MOTION = {"hook": 0, "mystery_drop": 1, "build_up": 2, "pattern_interrupt": 1,
                        "core_facts": 3, "core_facts_2": 4, "curiosity_bridge": 2, "climax": 5, "cta": 5}
        idx    = _ROLE_MOTION.get(role, clip_index % 6)

        # Section-aware Ken Burns motions
        # Kecepatan disesuaikan dengan durasi — clip pendek lebih agresif
        speed_zoom_in  = round(0.5 / frames, 6)   # zoom in speed
        speed_zoom_out = round(0.5 / frames, 6)   # zoom out speed

        SECTION_MOTIONS = {
            0: (  # Hook — zoom in agresif, langsung grab attention
                f"scale=8000:-1,"
                f"zoompan=z='min(zoom+{speed_zoom_in*2:.6f},1.5)':d={frames}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                f"setsar=1"
            ),
            1: (  # Mystery Drop — zoom out perlahan, reveal skala misteri
                f"scale=8000:-1,"
                f"zoompan=z='if(eq(on,1),1.5,max(zoom-{speed_zoom_out:.6f},1.0))':d={frames}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                f"setsar=1"
            ),
            2: (  # Build Up — diagonal pan, kesan perjalanan dan eksplorasi
                f"scale=8000:-1,"
                f"zoompan=z='1.3':d={frames}"
                f":x='(iw-iw/zoom)*on/{frames}':y='(ih-ih/zoom)*on/{frames}':s=1080x1920,"
                f"setsar=1"
            ),
            3: (  # Core Facts — zoom in presisi ke detail
                f"scale=8000:-1,"
                f"zoompan=z='min(zoom+{speed_zoom_in:.6f},1.4)':d={frames}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                f"setsar=1"
            ),
            4: (  # Core Facts 2 — pan horizontal, menjelajahi konteks
                f"scale=8000:-1,"
                f"zoompan=z='1.3':d={frames}"
                f":x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                f"setsar=1"
            ),
            5: (  # Climax — zoom out dramatis dari dekat ke jauh
                f"scale=8000:-1,"
                f"zoompan=z='if(eq(on,1),1.8,max(zoom-{speed_zoom_out*1.5:.6f},1.0))':d={frames}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                f"setsar=1"
            ),
        }

        vf = SECTION_MOTIONS[idx]

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-preset", "fast",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise VisualError(
                f"FFmpeg image-to-video failed: {result.stderr[-500:]}"
            )

