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


# Model registry
AI_IMAGE_MODELS = {
    "flux-schnell": {
        "platform":    "replicate",
        "model_id":    "black-forest-labs/flux-schnell",
        "description": "Tercepat, kualitas sangat baik",
    },
    "gpt-image-1-mini": {
        "platform":    "openai",
        "model_id":    "gpt-image-1-mini",
        "description": "GPT Image 1 Mini, low quality",
        "size":        "1024x1536",
    },
    "stable-diffusion": {
        "platform":    "replicate",
        "model_id":    "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
        "description": "Alternatif Replicate",
    },
}

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

        provider_str  = config.get("visual_provider", "ai_image:flux-schnell")
        parts         = provider_str.split(":", 1)
        self.ai_model = parts[1] if len(parts) > 1 else "flux-schnell"

        if self.ai_model not in AI_IMAGE_MODELS:
            raise VisualError(
                f"AI Image model '{self.ai_model}' tidak dikenal. "
                f"Pilihan: {list(AI_IMAGE_MODELS.keys())}"
            )

        self.model_config       = AI_IMAGE_MODELS[self.ai_model]
        self.image_quality      = config.get("image_quality", "low")
        self.niche              = config.get("niche", "universe_mysteries")
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
        self.llm_provider = config.get("llm_provider", "claude")
        self.llm_api_key  = config.get("llm_api_key") or ""

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
    ) -> list[VideoClip]:
        """
        Generate gambar AI per section → convert ke video dengan motion.
        keywords       = visual_suggestions dari script (sinematik dari s6c6).
        clip_durations = durasi per clip dari section_durations script (s6c2).
                         Jika None → fallback ke 5.0 detik per clip.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        clips: list[VideoClip] = []

        for i, keyword in enumerate(keywords[:count]):
            try:
                positive_prompt, negative_prompt = self._build_image_prompt(keyword)

                # Durasi per clip dari section_durations (s6c2)
                # Fallback ke 5.0 jika tidak tersedia
                if clip_durations and i < len(clip_durations):
                    duration = clip_durations[i]
                else:
                    duration = 5.0

                logger.info(
                    f"[AIImage:{self.ai_model}] Scene {i+1}/{count} | duration={duration}s"
                )
                logger.debug(f"[AIImage] Prompt: {positive_prompt[:120]}...")

                img_path  = output_dir / f"ai_img_{i+1:02d}.jpg"
                clip_path = output_dir / f"clip_{i+1:02d}_ai.mp4"

                await self._generate_image(positive_prompt, negative_prompt, img_path)

                self._image_to_video(img_path, clip_path, duration=duration, clip_index=i)

                size_mb = clip_path.stat().st_size / (1024 * 1024)

                clips.append(VideoClip(
                    path=clip_path,
                    duration=duration,
                    width=1080,
                    height=1920,
                    file_size_mb=round(size_mb, 1),
                    source_url=f"ai_generated:{self.ai_model}",
                    provider=self.provider_name,
                ))
                logger.info(
                    f"[AIImage] ✓ Scene {i+1}: {clip_path.name} ({size_mb:.1f}MB) {duration}s"
                )

            except Exception as e:
                # ── Retry loop ────────────────────────────────────────────────────────
                # Attempt 2-3: Claude/LLM rewrite dengan accumulated rejection_history.
                # Setiap iterasi Claude makin tahu apa yang harus dihindari.
                # Tidak ada fallback ke visual_fallbacks — visual harus relevan dengan narasi.
                # Tidak ada fallback ke provider lain — kualitas konten non-negotiable.
                # Jika semua attempt gagal: scene di-skip, pipeline laporkan ke Telegram.
                rejection_history = [{"prompt": positive_prompt, "rejection": str(e)}]
                succeeded = False
                for attempt in range(2, 4):  # attempt 2 dan 3
                    try:
                        logger.warning(
                            f"[AIImage] Scene {i+1} attempt {attempt-1} gagal — "
                            f"rewrite via {self.llm_provider} (attempt {attempt}/3)"
                        )
                        rewritten_main = await self._ai_rewrite_on_rejection(
                            original_keyword=keyword,
                            section_index=i,
                            rejection_history=rejection_history,
                        )
                        safe_positive, safe_negative = self._build_image_prompt(rewritten_main)
                        safe_output = output_dir / f"clip_{i+1:02d}_attempt{attempt}.jpg"
                        safe_clip   = output_dir / f"clip_{i+1:02d}_attempt{attempt}.mp4"
                        target_dur  = clip_durations[i] if clip_durations and i < len(clip_durations) else 5.0
                        await self._generate_image(safe_positive, safe_negative, safe_output)
                        self._image_to_video(safe_output, safe_clip, duration=target_dur, clip_index=i)
                        size_mb = safe_clip.stat().st_size / (1024 * 1024)
                        clips.append(VideoClip(
                            path=safe_clip, duration=target_dur,
                            width=1080, height=1920,
                            file_size_mb=round(size_mb, 1),
                            source_url=f"ai_generated:retry_{attempt}",
                            provider=self.provider_name,
                        ))
                        logger.info(f"[AIImage] ✅ Scene {i+1} berhasil pada attempt {attempt}")
                        succeeded = True
                        break
                    except Exception as retry_err:
                        rejection_history.append({"prompt": safe_positive, "rejection": str(retry_err)})
                        logger.warning(f"[AIImage] Scene {i+1} attempt {attempt} gagal: {retry_err}")

                if not succeeded:
                    logger.error(
                        f"[AIImage] Scene {i+1} GAGAL setelah 3 attempt — scene di-skip"
                    )
                    continue

        logger.info(f"[AIImage] Complete: {len(clips)}/{count} clips")
        return clips

    def extract_keywords_from_script(self, script: dict, niche: str) -> list[str]:
        """
        Extract visual subjects dari script.
        Priority: visual_suggestions dari script (sudah sinematik dari s6c6).
        Selalu return tepat 6 items untuk 6 section clips.
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

        # Priority 2: fallback ke niche visual_fallbacks dari Supabase jika kurang dari 6
        if len(keywords) < 6:
            fallbacks = self.niche_visual_fallbacks
            for fb in fallbacks:
                if len(keywords) >= 6:
                    break
                if fb not in keywords:
                    keywords.append(fb)
            logger.info(f"[AIImage] Setelah fallback: {len(keywords)} items")

        return keywords[:6]

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

        if not self.llm_api_key:
            raise VisualError(
                f"llm_api_key tidak tersedia untuk rejection rewrite "
                f"(provider={self.llm_provider}). "
                f"Set llm_api_key di tenant_configs Supabase."
            )

        if self.llm_provider == "claude":
            import anthropic
            client   = anthropic.Anthropic(api_key=self.llm_api_key)
            response = client.messages.create(
                model    = "claude-haiku-4-5-20251001",
                max_tokens  = 200,
                messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}],
            )
            rewritten = response.content[0].text.strip().strip('"')
        else:
            import openai
            client   = openai.OpenAI(api_key=self.llm_api_key)
            response = client.chat.completions.create(
                model    = "gpt-4o-mini",
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens  = 200,
                temperature = 0.7,
            )
            rewritten = response.choices[0].message.content.strip().strip('"')

        logger.info(
            f"[AIImage] {self.llm_provider} rewrite scene {section_index+1} "
            f"(attempt {len(rejection_history)+1}): {rewritten[:120]}"
        )
        return rewritten  # Already a full DALL-E ready prompt

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
        output = await asyncio.to_thread(
            replicate.run,
            self.model_config["model_id"],
            input={
                "prompt":          prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio":    "9:16",
            }
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
    @staticmethod
    def _image_to_video(
        img_path: Path,
        output_path: Path,
        duration: float = 5.0,
        clip_index: int = 0,
    ) -> None:
        """
        Konversi gambar → video 9:16 dengan Ken Burns effect.
        Fix G: section-aware motion — setiap clip punya karakter gerakan
        sesuai posisi dalam narasi agar terasa dinamis seperti footage video.
        """
        fps    = 30
        frames = int(duration * fps)
        idx    = clip_index % 6

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

