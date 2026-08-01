"""
AI Video Provider — text-to-video via AGREGATOR (transport per-platform, pola ai_image._TRANSPORTS).

[B6] F2 (2026-07-14): stub v0.2 diganti mesin nyata.
  - Model = katalog DB `ai_models` component='video' (admin-managed; model baru = baris DB, nol kode).
  - Transport perdana = 'fal' (queue.fal.run: submit → poll status_url → ambil response_url → unduh).
    Latency vendor 1-3 mnt/klip → pola async-poll (worker sudah async; MULTI_FORMAT §0).
  - NO-FALLBACK (§3.8): gagal/timeout = VisualError jujur → pipeline stop + Telegram. Tanpa provider
    pengganti diam-diam.
  - Biaya: cost_meter.add_video(model_id, detik-TERTAGIH) — detik yang diminta ke vendor (bukan hasil
    trim renderer), karena itulah yang vendor tagihkan.
  - Prompt = script['video_prompt'] (dibuat STEP 4.5 varian video, DNA-injected) — provider hanya
    memakai, tidak merangkai (pola s85c ai_image).
"""

import asyncio
import subprocess
from pathlib import Path

import httpx
from loguru import logger

from src.providers.visual.base import VisualProvider, VideoClip, VisualError

# Poll antrean vendor: interval & batas tunggu (latency riil 1-3 mnt/klip; batas 10 mnt = gagal jujur).
_POLL_INTERVAL_S = 5.0
_POLL_TIMEOUT_S  = 600.0
# Kunci META di default_params (petunjuk adapter, BUKAN parameter API — di-strip sebelum kirim).
_META_PARAM_KEYS = {"allowed_durations", "duration_param"}


class AIVideoProvider(VisualProvider):
    """Text-to-video 1 klip 9:16 dari katalog ai_models (component='video')."""

    def __init__(self, config: dict):
        super().__init__(config)

        provider_str  = config.get("visual_provider") or ""
        parts         = provider_str.split(":", 1)
        self.ai_model = parts[1] if len(parts) > 1 else ""
        if not self.ai_model:
            raise VisualError("Model video belum diset (visual_provider='ai_video:<model_key>').")

        # Katalog DB — config["model_row"] = injeksi model_tester (uji model NONAKTIF sebelum
        # diaktifkan; pola identik AIImageProvider). Produksi selalu lewat katalog-aktif.
        from src.providers.llm.catalog import get_models
        _row = config.get("model_row") or get_models().get(self.ai_model)
        if not _row or _row.get("component") != "video":
            raise VisualError(
                f"Model video '{self.ai_model}' tidak ada / non-aktif di katalog ai_models."
            )
        self.model_config = {
            "platform": _row["provider_key"],
            "model_id": _row["model_id"],
            "params":   dict(_row.get("default_params") or {}),
        }
        try:
            from src.providers.llm.catalog import get_providers
            self.model_config["base_url"] = (get_providers().get(_row["provider_key"]) or {}).get("base_url")
        except Exception:
            self.model_config["base_url"] = None

        self.niche = config.get("niche") or ""
        # Kunci = visual_api_key (BYOK pool, key_group vendor) — NO-FALLBACK env.
        self.api_key = config.get("visual_api_key") or ""
        if not self.api_key:
            raise VisualError(
                f"AI Video ({self.ai_model}) membutuhkan API key vendor — "
                f"hubungkan akun vendor di /integrations lalu tugaskan ke channel."
            )
        logger.info(f"[AIVideo] Initialized: model={self.ai_model} niche={self.niche}")

    # ──────────────────────────────────────────────
    # API publik (kontrak VisualProvider)
    # ──────────────────────────────────────────────

    async def fetch_clips(
        self,
        keywords: list[str],
        count: int,
        output_dir: Path,
        clip_durations: list[float] | None = None,
        beat_roles: list[str] | None = None,
    ) -> list[VideoClip]:
        """
        Generate SATU klip text-to-video (render_mode ai_video = 1 shot utuh; MULTI_FORMAT §3 8s).
        keywords[0]       = video_prompt final (STEP 4.5 varian video).
        clip_durations[0] = durasi audio yang harus TERTUTUPI klip (renderer men-trim kelebihan).
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        prompt = (keywords[0] if keywords else "").strip()
        if not prompt:
            raise VisualError("video_prompt kosong — STEP 4.5 varian video wajib mengisinya (no-fallback).")

        needed = float(clip_durations[0]) if clip_durations else 0.0
        chosen = self._choose_duration(needed)

        out_path = output_dir / "clip_01_ai.mp4"
        billed_s = await self._generate_video(prompt, out_path, chosen)

        actual = self._probe_duration(out_path)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        if actual <= 0 or size_mb <= 0:
            raise VisualError(f"Klip video hasil unduhan tidak valid (durasi={actual}s, {size_mb:.2f}MB).")
        if needed and actual + 0.05 < needed:
            # ⛔ NO-FALLBACK (§3.3): vendor mengirim klip lebih pendek dari yang diminta = kegagalan
            # komponen → STOP jujur (bukan freeze-frame menutupi kekurangan konten berbayar diam-diam).
            raise VisualError(
                f"Klip vendor {actual:.1f}s < audio {needed:.1f}s (diminta {billed_s}s) — "
                f"run dihentikan (no-fallback)."
            )

        # B2 cost-tracking: detik TERTAGIH vendor (durasi yang diminta; fallback durasi aktual).
        try:
            from src.utils import cost_meter
            cost_meter.add_video(self.model_config.get("model_id") or "", float(billed_s or actual))
        except Exception:
            pass

        logger.info(f"[AIVideo] ✓ Klip jadi: {out_path.name} {actual:.1f}s ({size_mb:.1f}MB) via {self.ai_model}")
        return [VideoClip(
            path=out_path, duration=actual, width=1080, height=1920,
            file_size_mb=round(size_mb, 1), source_url=f"ai_generated:{self.ai_model}",
            provider=self.provider_name,
        )]

    def extract_keywords_from_script(self, script: dict, niche: str, n: int = 1) -> list[str]:
        """Prompt video = script['video_prompt'] (Tahap-2 varian video). Provider tidak merangkai prompt."""
        vp = (script.get("video_prompt") or "").strip()
        return [vp] if vp else []

    @property
    def provider_name(self) -> str:
        return f"ai_video:{self.ai_model}"

    @property
    def is_ai_generated(self) -> bool:
        return True

    @property
    def is_enabled(self) -> bool:
        return True

    # ──────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────

    def _choose_duration(self, needed_s: float) -> float | None:
        """Pilih durasi klip dari `allowed_durations` (META default_params): TERKECIL yang ≥ kebutuhan
        (hemat biaya per-detik). Tak ada yang cukup → ambil MAKS + warning (freeze-frame menutup sisa).
        Tanpa meta → None (kirim default_params apa adanya)."""
        allowed = (self.model_config.get("params") or {}).get("allowed_durations")
        if not (isinstance(allowed, list) and allowed):
            return None
        try:
            opts = sorted(float(a) for a in allowed)
        except (TypeError, ValueError):
            raise VisualError(f"allowed_durations katalog tidak valid: {allowed!r} — perbaiki ai_models.default_params.")
        for o in opts:
            if o >= needed_s:
                return o
        # ⛔ NO-FALLBACK (§3.3, teguran owner 2026-07-14): audio > durasi maks vendor = konfigurasi
        # tak koheren → STOP jujur (bukan freeze-frame diam-diam). Praktis tak terjangkau utk preset 8s
        # (gerbang durasi pra-visual sudah menolak audio kepanjangan sebelum sampai sini).
        raise VisualError(
            f"Audio {needed_s:.1f}s melebihi durasi klip maksimum vendor ({opts[-1]:.0f}s) — "
            f"run dihentikan (no-fallback)."
        )

    @staticmethod
    def _probe_duration(path: Path) -> float:
        """Durasi nyata file via ffprobe (bukti, bukan asumsi)."""
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            return float((r.stdout or "0").strip() or 0)
        except Exception:
            return 0.0

    # F5-06: registry transport per-PLATFORM (mirror ai_image). Tambah platform (mis. replicate)
    # = +1 method `_generate_<x>` + 1 entri; MODEL-nya via ai_models (DB, nol kode).
    _TRANSPORTS = {"fal": "_generate_fal"}

    async def _generate_video(self, prompt: str, out_path: Path, chosen_duration: float | None) -> float | None:
        platform = self.model_config["platform"]
        method = self._TRANSPORTS.get(platform)
        if not method:
            raise VisualError(
                f"Platform transport video '{platform}' belum didukung kode. "
                f"Tambah adaptor _generate_<platform> + entri _TRANSPORTS (model via ai_models)."
            )
        return await getattr(self, method)(prompt, out_path, chosen_duration)

    async def _generate_fal(self, prompt: str, out_path: Path, chosen_duration: float | None) -> float | None:
        """Transport fal.ai (VERIFIED docs 2026-07-14):
          submit  : POST {base}/{model_id}  header 'Authorization: Key <FAL_KEY>'
                    → {request_id, status_url, response_url}
          poll    : GET status_url → {"status": IN_QUEUE|IN_PROGRESS|COMPLETED}
          hasil   : GET response_url → {"video": {"url": ...}}  → unduh mp4.
        Body = default_params (tanpa kunci META) + prompt + durasi terpilih. Return detik tertagih."""
        base = (self.model_config.get("base_url") or "").rstrip("/") or "https://queue.fal.run"
        url  = f"{base}/{self.model_config['model_id']}"
        params = {k: v for k, v in (self.model_config.get("params") or {}).items()
                  if k not in _META_PARAM_KEYS}
        body = {**params, "prompt": prompt}
        dur_param = (self.model_config.get("params") or {}).get("duration_param")
        if chosen_duration is not None and dur_param:
            # Vendor (Kling via fal) menerima duration sbg STRING enum ("5"/"10").
            body[dur_param] = str(int(chosen_duration))
        headers = {"Authorization": f"Key {self.api_key}"}

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=body, headers=headers)
            if r.status_code not in (200, 201, 202):
                raise VisualError(f"fal submit HTTP {r.status_code}: {r.text[:300]}")
            sub = r.json()
            status_url   = sub.get("status_url")
            response_url = sub.get("response_url")
            if not (status_url and response_url):
                raise VisualError(f"fal submit: respons tanpa status_url/response_url ({str(sub)[:250]})")

            # Poll sampai COMPLETED / timeout (gagal jujur — tanpa fallback senyap).
            waited = 0.0
            while True:
                await asyncio.sleep(_POLL_INTERVAL_S)
                waited += _POLL_INTERVAL_S
                s = await client.get(status_url, headers=headers)
                if s.status_code >= 400:
                    raise VisualError(f"fal status HTTP {s.status_code}: {s.text[:300]}")
                status = (s.json() or {}).get("status", "")
                if status == "COMPLETED":
                    break
                if status not in ("IN_QUEUE", "IN_PROGRESS"):
                    raise VisualError(f"fal job status tak dikenal/gagal: '{status}' ({s.text[:250]})")
                if waited >= _POLL_TIMEOUT_S:
                    raise VisualError(
                        f"fal job timeout >{int(_POLL_TIMEOUT_S)}s (status terakhir: {status}) — "
                        f"video-gen tidak selesai; coba ulang manual."
                    )

            res = await client.get(response_url, headers=headers)
            if res.status_code != 200:
                raise VisualError(f"fal result HTTP {res.status_code}: {res.text[:300]}")
            data = res.json() or {}
            video_url = ((data.get("video") or {}).get("url")) or ""
            if not video_url:
                raise VisualError(f"fal result: respons tanpa video.url ({str(data)[:250]})")

        # Unduh klip (klien terpisah, timeout longgar utk file video).
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as dl:
            v = await dl.get(video_url)
            if v.status_code != 200 or not v.content:
                raise VisualError(f"Unduh klip gagal HTTP {v.status_code} ({video_url[:120]})")
            out_path.write_bytes(v.content)
        return chosen_duration
