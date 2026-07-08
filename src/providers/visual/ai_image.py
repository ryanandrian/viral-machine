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
        # config["model_row"] = injeksi model_tester agar model NONAKTIF bisa diuji SEBELUM
        # diaktifkan (prinsip katalog: aktif = terbukti; tanpa ini telur-ayam — image tak pernah
        # bisa lulus uji). Produksi tak pernah mengisi model_row → tetap katalog-aktif saja.
        from src.providers.llm.catalog import get_models
        _row = config.get("model_row") or get_models().get(self.ai_model)
        if not _row or _row.get("component") != "image":
            raise VisualError(
                f"Model image '{self.ai_model}' tidak ada / non-aktif di katalog ai_models."
            )
        self.model_config = {
            "platform": _row["provider_key"],
            "model_id": _row["model_id"],
            "size":     (_row.get("default_params") or {}).get("size", "1024x1536"),
            # default_params utuh (ai_models.default_params, admin-editable) — parameter per-model
            # config-driven (mis. steps Cloudflare), bukan hardcode di transport.
            "params":   (_row.get("default_params") or {}),
        }
        # base_url provider (ai_providers) — provider image OpenAI-compatible non-OpenAI (mis. Together
        # FLUX free-tier) cukup baris DB + transport openai. None (OpenAI asli) → SDK default = perilaku lama.
        try:
            from src.providers.llm.catalog import get_providers
            self.model_config["base_url"] = (get_providers().get(_row["provider_key"]) or {}).get("base_url")
        except Exception:
            self.model_config["base_url"] = None
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

        # Kunci visual = visual_api_key (BYOK per tenant) untuk SEMUA platform (openai/replicate/dst).
        # NO-FALLBACK: tak ada env-token platform (Replicate tetap OPSI; tenant isi kunci sendiri).
        # Kosong → di-raise di bawah (gagal jujur). llm_api_key dipisah khusus LLM (narasi + rejection rewrite).
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

        # Intensitas gerak Ken Burns per-niche (visual_style.camera_motion.intensity). Nilai tak valid → normal.
        _cm = (self.niche_visual_style or {}).get("camera_motion") or {}
        motion_intensity = _cm.get("intensity") if _cm.get("intensity") in self._MOTION_INTENSITY else "normal"
        # ARAH per-adegan (Fase 2, level system): resolve dari content_beats (fix/cerdas). Sejajar beat_roles.
        from src.content import beats as _beats
        motion_seq = _beats.resolve_motion_sequence(beat_roles or [])

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
                _mv = motion_seq[i] if i < len(motion_seq) else {"dir": "zoom_in", "rate": 0.05}
                self._image_to_video(img_path, clip_path, duration=duration, clip_index=i, role=role,
                                     intensity=motion_intensity, direction=_mv["dir"], rate=_mv["rate"])
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

    # F5-06: registry transport image per-PLATFORM (mirror LLM ADAPTERS). Tambah platform baru
    # (mis. stability/fireworks) = +1 method `_generate_<x>` + 1 entri di sini; model-nya via ai_models (DB).
    _TRANSPORTS = {"replicate": "_generate_replicate", "openai": "_generate_dalle",
                   # Together = protokol images OpenAI-compatible (base_url dari ai_providers) — FLUX free-tier.
                   "together": "_generate_dalle",
                   # Gemini = protokol Google generateContent modalitas IMAGE (kunci sama dgn LLM Gemini).
                   "gemini": "_generate_gemini",
                   # Cloudflare Workers AI = REST run model (FLUX free-tier 10k neuron/hari, tanpa kartu).
                   "cloudflare": "_generate_cloudflare"}

    async def _generate_image(self, prompt: str, negative_prompt: str, output_path: Path) -> None:
        platform = self.model_config["platform"]
        method = self._TRANSPORTS.get(platform)
        if not method:
            raise VisualError(
                f"Platform transport image '{platform}' belum didukung kode. "
                f"Tambah adaptor _generate_<platform> + entri _TRANSPORTS (model didaftar via ai_models)."
            )
        await getattr(self, method)(prompt, negative_prompt, output_path)
        # B2 cost-tracking: 1 gambar SUKSES ter-generate (retry gagal tak dihitung — hanya yg jadi). Fail-soft.
        try:
            from src.utils import cost_meter
            cost_meter.add_image(self.model_config.get("model_id") or "")
        except Exception:
            pass

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

        # base_url dari ai_providers → provider images OpenAI-compatible non-OpenAI (mis. Together FLUX
        # free-tier) jalan lewat transport ini. `quality` = parameter khusus keluarga OpenAI — hanya
        # dikirim ke platform openai (provider lain bisa menolak parameter tak dikenal).
        _client_kw = {"api_key": self.api_key}
        if self.model_config.get("base_url"):
            _client_kw["base_url"] = self.model_config["base_url"]
        _gen_kw = dict(model=self.model_config["model_id"], prompt=full_prompt, size=size, n=1)
        if self.model_config.get("platform") == "openai":
            _gen_kw["quality"] = self.image_quality

        async with AsyncOpenAI(**_client_kw) as client:
            response = await client.images.generate(**_gen_kw)
            # B2 cost-tracking: keluarga gpt-image-1 ditagih PER-TOKEN dan respons menyertakan usage —
            # tangkap token NYATA (dicatat sbg llm-bucket model image; harga in/out dari feed). Fail-soft.
            try:
                from src.utils import cost_meter
                u = getattr(response, "usage", None)
                if u and (getattr(u, "input_tokens", 0) or getattr(u, "output_tokens", 0)):
                    cost_meter.add_llm(self.model_config["model_id"], getattr(u, "input_tokens", 0), getattr(u, "output_tokens", 0))
            except Exception:
                pass
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

    async def _generate_gemini(self, prompt: str, negative_prompt: str, output_path: Path) -> None:
        """Transport Google generateContent (responseModalities IMAGE) — mis. gemini-2.5-flash-image.
        Root NATIF diturunkan dari ai_providers.base_url ('.../v1beta/openai/' → '.../v1beta';
        satu sumber URL). Negative prompt digabung ke prompt (pola sama _generate_dalle).
        Aspek 9:16 via generationConfig.imageConfig (vertikal Shorts)."""
        base = (self.model_config.get("base_url") or "").rstrip("/")
        base = base[:-len("/openai")] if base.endswith("/openai") else (base or "https://generativelanguage.googleapis.com/v1beta")
        url = f"{base}/models/{self.model_config['model_id']}:generateContent"
        full_prompt = f"{prompt}\n\nStrictly avoid: {negative_prompt}"
        body = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}},
        }
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(url, json=body, headers={"x-goog-api-key": self.api_key})
        if r.status_code != 200:
            raise VisualError(f"Gemini image HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        img_b64 = None
        for c in data.get("candidates", []):
            for p in (c.get("content") or {}).get("parts", []):
                if p.get("inlineData", {}).get("data"):
                    img_b64 = p["inlineData"]["data"]
                    break
            if img_b64:
                break
        if not img_b64:
            # Penolakan content-policy Google datang sbg finishReason/promptFeedback — angkat sbg error
            # agar jalur rejection-rewrite 3-percobaan yang ADA menangani (pola sama provider lain).
            raise VisualError(f"Gemini image: respons tanpa gambar (feedback: {str(data)[:250]})")
        import base64 as _b64
        output_path.write_bytes(_b64.b64decode(img_b64))
        # B2 cost-tracking: usageMetadata token NYATA bila ada (gemini image ditagih per-token output). Fail-soft.
        try:
            from src.utils import cost_meter
            u = data.get("usageMetadata") or {}
            if u.get("promptTokenCount") or u.get("candidatesTokenCount"):
                cost_meter.add_llm(self.model_config["model_id"], u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))
        except Exception:
            pass

    async def _generate_cloudflare(self, prompt: str, negative_prompt: str, output_path: Path) -> None:
        """Transport Cloudflare Workers AI — POST {base}/accounts/{acct}/ai/run/{model_id}.
        Kunci pool = 'ACCOUNT_ID:API_TOKEN' (dua kredensial CF digabung ':' dalam satu key_enc).
        base_url dari ai_providers (satu sumber URL, pola _generate_gemini). Skema input RESMI CF
        (verified docs 2026-07-08): prompt ≤2048 char · steps ≤8 (dari ai_models.default_params,
        config-driven) · seed. TANPA width/height → output persegi; renderer men-scale/pad ke 9:16
        (pola sama gpt-image 2:3). Respons: JSON {success, result:{image: base64}}."""
        acct, _, token = (self.api_key or "").partition(":")
        acct, token = acct.strip(), token.strip()
        if not (acct and token):
            raise VisualError("Kunci Cloudflare harus berformat 'ACCOUNT_ID:API_TOKEN' — dua nilai dari dashboard Cloudflare, digabung tanda titik dua.")
        base = (self.model_config.get("base_url") or "").rstrip("/") or "https://api.cloudflare.com/client/v4"
        url = f"{base}/accounts/{acct}/ai/run/{self.model_config['model_id']}"
        # PROMPT MURNI tanpa merge negative (beda dari transport lain): FLUX tak punya kanal
        # negative-prompt, dan klasifier NSFW CF terbukti FALSE-POSITIVE pada suntikan
        # "Strictly avoid: ..." (uji nyata 2026-07-08: prompt lingkaran-merah pun ditolak 3030).
        body: dict = {"prompt": prompt[:2048]}   # batas resmi input CF
        steps = (self.model_config.get("params") or {}).get("steps")
        if steps:
            body["steps"] = min(int(steps), 8)   # batas resmi CF
        if self.visual_seed is not None:
            body["seed"] = int(self.visual_seed)   # Diversity §9.1 — frame fingerprint per video
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            raise VisualError(f"Cloudflare image HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        img_b64 = ((data.get("result") or {}).get("image")) or ""
        if not (data.get("success") and img_b64):
            raise VisualError(f"Cloudflare image: respons tanpa gambar ({str(data)[:250]})")
        import base64 as _b64
        output_path.write_bytes(_b64.b64decode(img_b64))

    # ──────────────────────────────────────────────
    # Internal: image → video dengan Ken Burns effect
    # ──────────────────────────────────────────────

    # ── Ken Burns WORLD-CLASS ([B3]/F5-02, owner 2026-07-05) ─────────────────────────────
    # Perbaikan atas kode lama (yg CAPAI target di ~50% klip lalu DIAM = "ekor statis" pd klip panjang):
    #   1) KECEPATAN-KONSTAN dipersepsi: laju zoom/detik seragam (rate×faktor), tak lagi 1/durasi tak-menentu.
    #   2) FULL-SPAN: gerak menyapu SELURUH durasi (capai target di frame TERAKHIR) → tak ada ekor statis.
    #   3) travel di-CLAMP [min,max]: klip sangat pendek tetap terlihat gerak; klip panjang tak over-zoom.
    # Intensitas per-niche (halus/normal/dinamis) menskala laju. Sumber: niches.visual_style.camera_motion.
    # ⚠️ Durasi klip TAK tersentuh (dipaku `-t {duration}`); ini HANYA cara gambar bergerak di dalam durasi.
    _MOTION_INTENSITY = {"halus": 0.6, "normal": 1.0, "dinamis": 1.5, "cepat": 2.2}
    _TRAVEL_MIN, _TRAVEL_MAX = 0.10, 0.30   # batas travel BENTUK-DURASI (sebelum intensitas) — kecepatan-konstan
    _PANZOOM = 0.18                          # level zoom yang ditahan saat pan (@normal), di-skala intensitas
    # Arah gerak (Fase 2, dari content_beats.motion_dir via resolve_motion_sequence). zoom=pusat; pan=geser full-span.
    _PAN_DIRS = {"pan_lr", "pan_rl", "pan_ud", "pan_du", "pan_diag", "pan_diag_rev"}

    @staticmethod
    def _build_motion_vf(direction: str, frames: int, intensity: str = "normal", rate: float = 0.04) -> str:
        """Filter ffmpeg Ken Burns 1 klip: kecepatan-konstan + full-span + intensitas per-niche + ARAH (Fase 2).
        TAK memengaruhi durasi (dipaku `-t` di pemanggil). Arah/intensitas tak dikenal → default aman."""
        factor = AIImageProvider._MOTION_INTENSITY.get(intensity, 1.0)
        dur = frames / 30.0
        S   = "s=1080x1920,setsar=1"
        CX, CY = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"      # titik tengah
        XMAX, YMAX = "(iw-iw/zoom)", "(ih-ih/zoom)"
        if direction in ("zoom_in", "zoom_out"):
            # travel BENTUK-DURASI (kecepatan-konstan, clamp) → ×intensitas → halus<normal<dinamis<cepat selalu terpisah.
            r = float(rate)
            if r <= 0:                       # arah zoom butuh laju>0 (mis. peran pan yg diubah admin ke zoom) → default aman
                r = 0.04
            base_travel = min(AIImageProvider._TRAVEL_MAX, max(AIImageProvider._TRAVEL_MIN, r * dur))
            travel = round(min(0.60, max(0.05, base_travel * factor)), 4)
            inc = round(travel / frames, 6)                  # full-span: capai target di frame terakhir
            z = round(1.0 + travel, 4)
            if direction == "zoom_in":
                return f"scale=8000:-1,zoompan=z='min(zoom+{inc:.6f},{z})':d={frames}:x='{CX}':y='{CY}':{S}"
            return f"scale=8000:-1,zoompan=z='if(eq(on,1),{z},max(zoom-{inc:.6f},1.0))':d={frames}:x='{CX}':y='{CY}':{S}"
        # pan family — zoom ditahan; geser 0→penuh sepanjang klip (full-span, arah sesuai direction).
        z = round(1.0 + AIImageProvider._PANZOOM * factor, 4)
        fwd = f"on/{frames}"; rev = f"(1-on/{frames})"
        DIRS = {
            "pan_lr":       (f"{XMAX}*{fwd}", CY),
            "pan_rl":       (f"{XMAX}*{rev}", CY),
            "pan_ud":       (CX, f"{YMAX}*{fwd}"),
            "pan_du":       (CX, f"{YMAX}*{rev}"),
            "pan_diag":     (f"{XMAX}*{fwd}", f"{YMAX}*{fwd}"),
            "pan_diag_rev": (f"{XMAX}*{rev}", f"{YMAX}*{rev}"),
            "still":        (CX, CY),
        }
        x, y = DIRS.get(direction, (CX, CY))                 # arah tak dikenal → tahan-tengah (aman)
        if direction == "still":
            z = round(1.0 + 0.04 * factor, 4)
        return f"scale=8000:-1,zoompan=z='{z}':d={frames}:x='{x}':y='{y}':{S}"

    @staticmethod
    def _image_to_video(
        img_path: Path,
        output_path: Path,
        duration: float = 5.0,
        clip_index: int = 0,
        role: str = "",
        intensity: str = "normal",
        direction: str = "zoom_in",
        rate: float = 0.05,
    ) -> None:
        """
        Konversi gambar → video 9:16 dengan Ken Burns effect.
        direction/rate = arah & laju hasil resolve_motion_sequence (Fase 2, per-adegan fix/cerdas).
        intensity (per-niche camera_motion): skala rasa gerak. Durasi TAK berubah (dipaku `-t`).
        Default direction=zoom_in/rate=0.05 = perilaku hook (dipakai jalur hook-frame yg tak kirim arah).
        """
        fps    = 30
        frames = int(duration * fps)
        vf  = AIImageProvider._build_motion_vf(direction, frames, intensity, rate)

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

