"""
AI Image Visual Provider — generate gambar via AI + motion effect.
Fase 6C s6c5: Cinematic prompt engineering per section type.

Upgrade dari versi sebelumnya:
  - Section-aware prompts: Hook=dramatic, Climax=epic, Core=informative
  - visual_suggestions dari script langsung dipakai tanpa dilusi template generik
  - DALL-E 3 optimized: natural language yang kaya, bukan template robotik
  - Niche style modifier: universe=cosmic, dark_history=ominous, dll
  - Negative prompt support untuk Replicate models
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
        "platform":     "replicate",
        "model_id":     "black-forest-labs/flux-schnell",
        "cost_per_img": 0.003,
        "description":  "Tercepat, kualitas sangat baik",
    },
    "dall-e-3": {
        "platform":     "openai",
        "model_id":     "dall-e-3",
        "cost_per_img": 0.040,
        "description":  "Kualitas tertinggi, DALL-E 3 memahami natural language",
        "size":         "1024x1792",
    },
    "stable-diffusion": {
        "platform":     "replicate",
        "model_id":     "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
        "cost_per_img": 0.001,
        "description":  "Paling murah",
    },
}

# ── Section type enhancer ─────────────────────────────────────────────────────
# Dipilih berdasarkan posisi clip dalam 6-clip sequence
# Mapping: clip index → section character
SECTION_ENHANCERS = {
    0: {  # Hook — harus stop scroll dalam 1 detik
        "character":  "dramatic, tension-filled, scroll-stopping",
        "lighting":   "high contrast dramatic lighting, sharp shadows",
        "camera":     "extreme close-up or extreme wide establishing shot",
        "mood":       "immediate visual impact, creates instant question",
        "technical":  "cinematic 9:16 vertical, photorealistic, 8K sharp",
    },
    1: {  # Mystery Drop — menambah lapisan misteri
        "character":  "mysterious, unsettling, raises more questions",
        "lighting":   "low key lighting, mysterious shadows, ambient glow",
        "camera":     "slow reveal composition, partially obscured subject",
        "mood":       "eerie beauty, something unknown lurking",
        "technical":  "cinematic 9:16 vertical, photorealistic, atmospheric depth",
    },
    2: {  # Build Up — membangun konteks dan skala
        "character":  "epic scale, awe-inspiring, informative yet beautiful",
        "lighting":   "natural dramatic lighting, golden hour or cosmic light",
        "camera":     "wide establishing shot showing full scale and context",
        "mood":       "sense of vast scale, weight of information lands visually",
        "technical":  "cinematic 9:16 vertical, photorealistic, ultra detailed",
    },
    3: {  # Core Facts — informasi padat, visual yang kuat
        "character":  "visually striking, information-rich, unexpected angle",
        "lighting":   "clinical precision or dramatic chiaroscuro",
        "camera":     "detail shot revealing something specific and surprising",
        "mood":       "this is the proof, the evidence, the undeniable visual",
        "technical":  "cinematic 9:16 vertical, photorealistic, razor sharp detail",
    },
    4: {  # Core Facts 2 — building to climax
        "character":  "tension building, anticipation, something about to change",
        "lighting":   "darkening atmosphere, spotlight on key element",
        "camera":     "medium shot with leading lines pointing to climax",
        "mood":       "the viewer feels they are approaching something enormous",
        "technical":  "cinematic 9:16 vertical, photorealistic, dramatic composition",
    },
    5: {  # Climax — emotional peak, most memorable frame
        "character":  "overwhelming, emotionally peak, unforgettable visual impact",
        "lighting":   "dramatic peak lighting — could be total darkness or blinding light",
        "camera":     "the single most powerful composition of the entire video",
        "mood":       "this is the moment — awe, shock, revelation, or profound emotion",
        "technical":  "cinematic 9:16 vertical, photorealistic, masterpiece composition, 8K",
    },
}

def _build_cinematic_prompt(
    visual_suggestion: str,
    section_index: int,
    niche_style: dict,
    model: str,
) -> str:
    """
    Build prompt sinematik dari visual_suggestion script.
    niche_style: dict dari tabel niches.visual_style (loaded dari Supabase).
    """
    enhancer = SECTION_ENHANCERS.get(section_index, SECTION_ENHANCERS[2])

    base_style    = niche_style.get("base_style", "documentary photography style")
    color_palette = niche_style.get("color_palette", "natural colors")
    atmosphere    = niche_style.get("atmosphere", "cinematic atmosphere")

    if model == "dall-e-3":
        prompt = (
            f"{visual_suggestion}. "
            f"Shot in {base_style}. "
            f"The image should feel {enhancer['character']}. "
            f"{enhancer['lighting']}. "
            f"Framed as {enhancer['camera']}. "
            f"Color palette: {color_palette}. "
            f"Atmosphere: {atmosphere}. "
            f"Vertical 9:16 format optimized for mobile full-screen viewing. "
            f"Photorealistic, not illustrated or painted. "
            f"No text, no words, no letters, no numbers, no signs, "
            f"no logos, no watermarks, no typography of any kind."
        )
    else:
        # Flux/SD: keyword-style prompts
        prompt = (
            f"{visual_suggestion}, "
            f"{base_style}, "
            f"{enhancer['character']}, "
            f"{enhancer['lighting']}, "
            f"{enhancer['camera']}, "
            f"color palette {color_palette}, "
            f"{enhancer['technical']}"
        )

    return prompt




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
        self.niche              = config.get("niche", "universe_mysteries")
        # Niche visual data — dari Supabase via TenantRunConfig (tidak hardcode)
        self.niche_visual_style     = config.get("niche_visual_style") or {}
        self.niche_visual_fallbacks = config.get("niche_visual_fallbacks") or []

        if self.model_config["platform"] == "replicate":
            self.api_key = (
                config.get("visual_api_key")
                or os.getenv("REPLICATE_API_TOKEN", "")
            )
        else:
            self.api_key = (
                config.get("llm_api_key")
                or os.getenv("OPENAI_API_KEY", "")
            )

        if not self.api_key:
            raise VisualError(
                f"AI Image ({self.ai_model}) membutuhkan API key. "
                f"Platform: {self.model_config['platform']}"
            )

        logger.info(
            f"[AIImage] Initialized: model={self.ai_model} "
            f"niche={self.niche} "
            f"cost=${self.model_config['cost_per_img']:.3f}/img"
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
        total_cost = 0.0

        for i, keyword in enumerate(keywords[:count]):
            try:
                # Build cinematic prompt — section-aware, niche style dari Supabase
                prompt = _build_cinematic_prompt(
                    visual_suggestion=keyword,
                    section_index=i,
                    niche_style=self.niche_visual_style,
                    model=self.ai_model,
                )

                # Durasi per clip dari section_durations (s6c2)
                # Fallback ke 5.0 jika tidak tersedia
                if clip_durations and i < len(clip_durations):
                    duration = clip_durations[i]
                else:
                    duration = 5.0

                logger.info(
                    f"[AIImage:{self.ai_model}] Scene {i+1}/{count} "
                    f"| duration={duration}s "
                    f"| section={list(SECTION_ENHANCERS.keys())[min(i,5)]}"
                )
                logger.debug(f"[AIImage] Prompt: {prompt[:120]}...")

                img_path  = output_dir / f"ai_img_{i+1:02d}.jpg"
                clip_path = output_dir / f"clip_{i+1:02d}_ai.mp4"

                await self._generate_image(prompt, img_path)

                self._image_to_video(img_path, clip_path, duration=duration, clip_index=i)

                size_mb = clip_path.stat().st_size / (1024 * 1024)
                cost    = self.model_config["cost_per_img"]
                total_cost += cost

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
                    f"[AIImage] ✓ Scene {i+1}: {clip_path.name} "
                    f"({size_mb:.1f}MB) {duration}s ~${cost:.3f}"
                )

            except Exception as e:
                # ── Retry loop: kirim rejection ke GPT, biarkan AI yang memikirkan ulang ──
                rejection_history = [{"prompt": prompt, "rejection": str(e)}]
                succeeded = False
                for attempt in range(2, 4):  # attempt 2 dan 3
                    try:
                        logger.warning(
                            f"[AIImage] Scene {i+1} attempt {attempt-1} gagal — "
                            f"kirim rejection ke GPT untuk rewrite (attempt {attempt}/3)"
                        )
                        safe_prompt = await self._ai_rewrite_on_rejection(
                            original_keyword=keyword,
                            section_index=i,
                            rejection_history=rejection_history,
                        )
                        safe_output = output_dir / f"clip_{i+1:02d}_attempt{attempt}.jpg"
                        safe_clip   = output_dir / f"clip_{i+1:02d}_attempt{attempt}.mp4"
                        target_dur  = clip_durations[i] if clip_durations and i < len(clip_durations) else 5.0
                        await self._generate_image(safe_prompt, safe_output)
                        self._image_to_video(safe_output, safe_clip, duration=target_dur, clip_index=i)
                        size_mb = safe_clip.stat().st_size / (1024 * 1024)
                        clips.append(VideoClip(
                            path=safe_clip, duration=target_dur,
                            width=1080, height=1920,
                            file_size_mb=round(size_mb, 1),
                            source_url=f"ai_generated:retry_{attempt}",
                            provider=self.provider_name,
                        ))
                        total_cost += self.model_config["cost_per_img"]
                        logger.info(f"[AIImage] ✅ Scene {i+1} berhasil pada attempt {attempt}")
                        succeeded = True
                        break
                    except Exception as retry_err:
                        rejection_history.append({"prompt": safe_prompt, "rejection": str(retry_err)})
                        logger.warning(f"[AIImage] Scene {i+1} attempt {attempt} juga ditolak: {retry_err}")

                if not succeeded:
                    logger.error(
                        f"[AIImage] Scene {i+1} GAGAL setelah 3 attempt — "
                        f"GPT tidak bisa hasilkan prompt yang diterima image generator"
                    )
                    continue

        logger.info(
            f"[AIImage] Complete: {len(clips)}/{count} clips "
            f"| total cost ~${total_cost:.3f}"
        )
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
        Kirim penolakan dari image generator kembali ke GPT.
        Biarkan GPT yang berpikir ulang — tidak ada manipulasi kata dari kita.

        rejection_history: list of {"prompt": str, "rejection": str}
          — semua attempt sebelumnya beserta alasan penolakannya.
        """
        import openai

        enhancer      = SECTION_ENHANCERS.get(section_index, SECTION_ENHANCERS[2])
        section_names = ["hook", "mystery", "build-up", "core facts", "tension", "climax"]
        section_name  = section_names[min(section_index, 5)]
        niche_style   = self.niche_visual_style
        base_style    = niche_style.get("base_style", "documentary photography")
        atmosphere    = niche_style.get("atmosphere", "cinematic")

        # Build rejection context untuk GPT
        rejection_context = "\n".join([
            f"Attempt {idx+1}:\n  Prompt: \"{r['prompt'][:200]}\"\n  Rejected: {r['rejection'][:200]}"
            for idx, r in enumerate(rejection_history)
        ])

        system_prompt = (
            "You are a visual prompt engineer. "
            "An image generator rejected your visual scene description. "
            "Your task: create a new safe prompt that still visually communicates "
            "the same narrative concept and emotional atmosphere. "
            "You may NOT directly repeat any element from rejected prompts. "
            "Think creatively — use environmental cues, abstract elements, scale, "
            "light, texture, and composition to convey the concept indirectly. "
            "Output ONLY the new visual description, 1-2 sentences, no explanation."
        )
        user_prompt = (
            f"Original visual concept: \"{original_keyword}\"\n"
            f"Scene position: {section_name} (scene {section_index+1}/6)\n"
            f"Visual style: {base_style}\n"
            f"Mood needed: {enhancer['mood']}\n"
            f"Atmosphere: {atmosphere}\n\n"
            f"Previous attempts that were rejected:\n{rejection_context}\n\n"
            f"Write a new visual description that conveys the same narrative moment safely:"
        )

        client   = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model    = "gpt-4o-mini",
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens  = 150,
            temperature = 0.7,
        )
        rewritten = response.choices[0].message.content.strip().strip('"')
        logger.info(
            f"[AIImage] GPT rewrite scene {section_index+1} "
            f"(attempt {len(rejection_history)+1}): {rewritten[:120]}"
        )
        return _build_cinematic_prompt(
            visual_suggestion = rewritten,
            section_index     = section_index,
            niche_style       = self.niche_visual_style,
            model             = self.ai_model,
        )

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

    async def _generate_image(self, prompt: str, output_path: Path) -> None:
        platform = self.model_config["platform"]
        if platform == "replicate":
            await self._generate_replicate(prompt, output_path)
        elif platform == "openai":
            await self._generate_dalle(prompt, output_path)
        else:
            raise VisualError(f"Platform tidak dikenal: {platform}")

    async def _generate_replicate(self, prompt: str, output_path: Path) -> None:
        try:
            import replicate
        except ImportError:
            raise VisualError("replicate tidak terinstall. Jalankan: pip install replicate")

        os.environ["REPLICATE_API_TOKEN"] = self.api_key
        output = await asyncio.to_thread(
            replicate.run,
            self.model_config["model_id"],
            input={"prompt": prompt, "aspect_ratio": "9:16"}
        )
        img_url = output[0] if isinstance(output, list) else str(output)
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(img_url)
            output_path.write_bytes(r.content)

    async def _generate_dalle(self, prompt: str, output_path: Path) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise VisualError("openai tidak terinstall. Jalankan: pip install openai")

        client = AsyncOpenAI(api_key=self.api_key)
        size   = self.model_config.get("size", "1024x1792")

        response = await client.images.generate(
            model=self.model_config["model_id"],
            prompt=prompt,
            size=size,
            quality="hd",       # Upgrade dari 'standard' ke 'hd' untuk kualitas terbaik
            style="vivid",      # 'vivid' lebih dramatic vs 'natural' — sesuai konten viral
            n=1,
        )
        img_url = response.data[0].url
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(img_url)
            output_path.write_bytes(r.content)

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

