"""
AI Image Visual Provider — generate gambar via AI + tambahkan motion effect.
Gambar digenerate per scene dari narasi, lalu dibuat video dengan Ken Burns effect.

Provider yang didukung:
  - flux-schnell (default) — via Replicate, ~$0.003/gambar, tercepat
  - dall-e-3               — via OpenAI, ~$0.040/gambar, kualitas tinggi
  - stable-diffusion       — via Replicate, ~$0.001/gambar, paling murah

Cara aktifkan via dashboard (nanti):
  visual_provider = 'ai_image:flux-schnell'
  visual_api_key  = 'r8_xxx...' (Replicate) atau pakai llm_api_key (DALL-E 3)
"""

import asyncio
import os
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
from loguru import logger

from src.providers.visual.base import VisualProvider, VideoClip, VisualError


# Model registry — tambah model baru di sini
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
        "description":  "Kualitas tertinggi OpenAI",
        "size":         "1024x1792",  # Portrait untuk 9:16
    },
    "stable-diffusion": {
        "platform":     "replicate",
        "model_id":     "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
        "cost_per_img": 0.001,
        "description":  "Paling murah",
    },
}

# Prompt template per niche untuk hasil visual yang lebih relevan
NICHE_PROMPT_TEMPLATES = {
    "universe_mysteries": (
        "Cinematic 9:16 vertical photo of {subject}. "
        "Deep space atmosphere, dramatic lighting, photorealistic, "
        "ultra high quality, 4K, dark background with stars"
    ),
    "fun_facts": (
        "Vibrant 9:16 vertical photo of {subject}. "
        "Colorful, dynamic, engaging, photorealistic, high quality"
    ),
    "dark_history": (
        "Moody 9:16 vertical photo of {subject}. "
        "Dark atmosphere, historical setting, dramatic shadows, "
        "cinematic, photorealistic, high quality"
    ),
    "ocean_mysteries": (
        "Underwater 9:16 vertical photo of {subject}. "
        "Deep ocean atmosphere, bioluminescent light, "
        "photorealistic, cinematic, ultra high quality"
    ),
}


class AIImageProvider(VisualProvider):
    """
    AI Image Generation + Motion Effect (Ken Burns) → Video clip.
    Menghasilkan visual yang 100% relevan dengan narasi karena
    prompt digenerate dari script.
    """

    def __init__(self, config: dict):
        super().__init__(config)

        # Parse model dari visual_provider: 'ai_image:flux-schnell'
        provider_str  = config.get("visual_provider", "ai_image:flux-schnell")
        parts         = provider_str.split(":", 1)
        self.ai_model = parts[1] if len(parts) > 1 else "flux-schnell"

        if self.ai_model not in AI_IMAGE_MODELS:
            raise VisualError(
                f"AI Image model '{self.ai_model}' tidak dikenal. "
                f"Pilihan: {list(AI_IMAGE_MODELS.keys())}"
            )

        self.model_config = AI_IMAGE_MODELS[self.ai_model]
        self.niche        = config.get("niche", "universe_mysteries")

        # API key: Replicate pakai visual_api_key, DALL-E 3 pakai llm_api_key
        if self.model_config["platform"] == "replicate":
            self.api_key = (
                config.get("visual_api_key")
                or os.getenv("REPLICATE_API_TOKEN", "")
            )
        else:  # openai
            self.api_key = (
                config.get("llm_api_key")
                or os.getenv("OPENAI_API_KEY", "")
            )

        if not self.api_key:
            raise VisualError(
                f"AI Image ({self.ai_model}) membutuhkan API key. "
                f"Platform: {self.model_config['platform']}"
            )

    async def fetch_clips(
        self,
        keywords: list[str],
        count: int,
        output_dir: Path,
    ) -> list[VideoClip]:
        """
        Generate gambar AI per keyword → convert ke video clip dengan motion.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        clips: list[VideoClip] = []
        template = NICHE_PROMPT_TEMPLATES.get(
            self.niche, NICHE_PROMPT_TEMPLATES["universe_mysteries"]
        )

        for i, keyword in enumerate(keywords[:count]):
            try:
                prompt = template.format(subject=keyword)
                logger.info(f"[AIImage:{self.ai_model}] Generating: '{keyword}'")

                # Generate gambar
                img_path = output_dir / f"ai_img_{i+1:02d}.jpg"
                await self._generate_image(prompt, img_path)

                # Konversi gambar → video dengan Ken Burns motion effect
                clip_path = output_dir / f"clip_{i+1:02d}_ai.mp4"
                duration  = 5.0  # detik per clip
                self._image_to_video(img_path, clip_path, duration=duration)

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
                logger.info(f"[AIImage] Clip {i+1}: {clip_path.name} ({size_mb:.1f}MB)")

            except Exception as e:
                logger.error(f"[AIImage] Failed for '{keyword}': {e}")
                continue

        return clips

    def extract_keywords_from_script(self, script: dict, niche: str) -> list[str]:
        """
        Untuk AI Image, keywords = subject untuk generate gambar.
        Selalu return 6 keywords untuk 6 clips.
        """
        keywords = []

        # Priority 1: visual_suggestions dari script (paling relevan)
        suggestions = script.get("visual_suggestions", [])
        if suggestions:
            keywords.extend([s for s in suggestions if s])

        # Priority 2: derive dari title + hook jika kurang dari 6
        if len(keywords) < 6:
            title = script.get("title", "")
            hook  = script.get("hook", "")
            if title and title not in keywords:
                keywords.append(title)
            if hook and len(hook) > 5 and hook not in keywords:
                keywords.append(hook[:80])

        # Priority 3: niche fallback keywords
        niche_fallbacks = {
            "universe_mysteries": [
                "deep space nebula cinematic",
                "spiral galaxy dramatic lighting",
                "astronaut floating in space",
                "cosmic explosion supernova",
                "black hole visualization art",
                "earth from orbit at night"
            ],
            "fun_facts": [
                "colorful world landmarks aerial",
                "science experiment lab",
                "nature timelapse dramatic",
                "human brain neural art",
                "microscopic world colorful",
                "city aerial drone view"
            ],
            "dark_history": [
                "ancient ruins dramatic fog",
                "medieval castle stormy night",
                "historical war scene epic",
                "old treasure map discovery",
                "archaeological excavation",
                "dark gothic monument"
            ],
            "ocean_mysteries": [
                "deep ocean bioluminescent creatures",
                "whale underwater dramatic",
                "coral reef colorful vibrant",
                "shipwreck underwater eerie",
                "ocean surface stormy waves",
                "submarine deep dive dark"
            ],
        }
        fallbacks = niche_fallbacks.get(niche, niche_fallbacks["universe_mysteries"])
        for fb in fallbacks:
            if len(keywords) >= 6:
                break
            if fb not in keywords:
                keywords.append(fb)

        return keywords[:6]

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
        """Route ke platform yang sesuai berdasarkan model config."""
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
        # Output adalah URL atau file-like — download ke disk
        img_url = output[0] if isinstance(output, list) else str(output)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(img_url)
            output_path.write_bytes(r.content)

    async def _generate_dalle(self, prompt: str, output_path: Path) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise VisualError("openai tidak terinstall. Jalankan: pip install openai")

        client   = AsyncOpenAI(api_key=self.api_key)
        size     = self.model_config.get("size", "1024x1792")
        response = await client.images.generate(
            model=self.model_config["model_id"],
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        img_url = response.data[0].url
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(img_url)
            output_path.write_bytes(r.content)

    # ──────────────────────────────────────────────
    # Internal: image → video dengan Ken Burns effect
    # ──────────────────────────────────────────────

    @staticmethod
    def _image_to_video(
        img_path: Path,
        output_path: Path,
        duration: float = 5.0,
    ) -> None:
        """
        Konversi gambar statis → video 9:16 dengan Ken Burns zoom effect.
        Menggunakan FFmpeg zoompan filter.
        """
        fps    = 30
        frames = int(duration * fps)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-vf", (
                f"scale=8000:-1,"
                f"zoompan=z='min(zoom+0.0015,1.5)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                f"setsar=1"
            ),
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise VisualError(f"FFmpeg image-to-video failed: {result.stderr[-500:]}")
