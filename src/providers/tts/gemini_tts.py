"""
Gemini TTS Provider — protokol Google generateContent (responseModalities AUDIO).

Adapter 'gemini_speech' (registry src/providers/tts/__init__). Konfigurasi 100% DB:
- ai_providers.base_url  = root OpenAI-compat ('.../v1beta/openai/') → root NATIF diturunkan
  dengan memangkas segmen 'openai' (satu sumber URL, tanpa hardcode ganda).
- tts_profiles ('gemini') = adapter/delivery_wps/param_schema; voice = voice_catalog (Kore/Puck/dll).
- Kunci = pool tenant (key_group 'gemini' — kunci yang SAMA dengan LLM Gemini).

Keluaran API = PCM mentah (audio/L16;rate=24000) base64 → dikonversi ke MP3 via ffmpeg
(ffmpeg = dependensi inti pipeline, sudah ada). Tanpa word-timestamps (kelas fast_fallback —
caption memakai estimasi, pola sama edge/openai_tts). Tanpa parameter speed di API — durasi
preset tetap akurat via jalur atempo closed-loop yang ada.
"""
import base64
import re
import subprocess
import tempfile
from pathlib import Path

import httpx
from loguru import logger

from src.providers.tts.base import TTSProvider, TTSError

_NATIVE_FALLBACK = "https://generativelanguage.googleapis.com/v1beta"


def _native_root(openai_compat_url: str | None) -> str:
    """'.../v1beta/openai/' (base_url provider utk adapter chat) → root NATIF '.../v1beta'.
    Fail-soft ke endpoint publik resmi bila base_url kosong/tak berpola."""
    u = (openai_compat_url or "").rstrip("/")
    if u.endswith("/openai"):
        return u[: -len("/openai")]
    return u or _NATIVE_FALLBACK


class GeminiTTSProvider(TTSProvider):
    """Gemini TTS via generateContent — voice prebuilt dari voice_catalog, multibahasa (incl. id-ID)."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("tts_api_key") or ""
        if not self.api_key:
            raise TTSError("Gemini TTS membutuhkan API key (pool kredensial, vendor 'gemini').")
        self.voice = config.get("tts_voice")
        if not self.voice:
            raise TTSError("Gemini TTS: voice belum ter-resolve (channels.voice_key, §10.B FINAL).")
        self.model = config.get("tts_model") or ""
        if not self.model:
            raise TTSError("Gemini TTS: model belum ter-resolve (channels.tts_model dari katalog).")
        try:
            from src.providers.llm.catalog import get_providers
            self.base = _native_root((get_providers().get("gemini") or {}).get("base_url"))
        except Exception:
            self.base = _NATIVE_FALLBACK

    async def generate(self, text: str, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.base}/models/{self.model}:generateContent"
        body = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.voice}}},
            },
        }
        logger.info(f"[GeminiTTS] voice={self.voice} model={self.model} chars={len(text)}")
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                r = await client.post(url, json=body, headers={"x-goog-api-key": self.api_key})
            if r.status_code != 200:
                raise TTSError(f"Gemini TTS HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            part = None
            for c in data.get("candidates", []):
                for p in (c.get("content") or {}).get("parts", []):
                    if p.get("inlineData", {}).get("data"):
                        part = p["inlineData"]
                        break
                if part:
                    break
            if not part:
                raise TTSError(f"Gemini TTS: respons tanpa audio (feedback: {str(data)[:200]})")
            pcm = base64.b64decode(part["data"])
            # mimeType mis. 'audio/L16;codec=pcm;rate=24000' → ambil sample-rate NYATA dari respons.
            m = re.search(r"rate=(\d+)", part.get("mimeType") or "")
            rate = m.group(1) if m else "24000"
            with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
                f.write(pcm)
                raw = f.name
            try:
                res = subprocess.run(
                    ["ffmpeg", "-y", "-f", "s16le", "-ar", rate, "-ac", "1", "-i", raw,
                     "-b:a", "128k", str(output_path)],
                    capture_output=True, text=True, timeout=120,
                )
                if res.returncode != 0:
                    raise TTSError(f"Gemini TTS: konversi PCM→MP3 gagal: {res.stderr[-200:]}")
            finally:
                Path(raw).unlink(missing_ok=True)
            # B2 cost-tracking. DUA satuan dicatat, keduanya dari data yang sudah di tangan:
            #  • huruf  — catatan pemakaian (satuan tagihan ElevenLabs/OpenAI tts-1 dsb)
            #  • token  — Gemini menagih suara PER TOKEN, dan hitungannya DIKIRIM VENDOR di balasan
            #             yang baru saja kita terima (`usageMetadata`). Pola ini sudah terpasang &
            #             terbukti di mesin gambar (`visual/ai_image.py`).
            # [2026-08-22] Sebelum ini hanya huruf yang dicatat, dengan komentar saya sendiri
            # "satuan tagihan TTS" — sebuah ASUMSI. Akibatnya biaya suara 4 channel aktif dilaporkan
            # Rp 0 selama 16 produksi. Token TIDAK boleh ditaksir dari panjang teks (= angka karangan):
            # vendor tak mengirim hitungan ⇒ biaya jujur dilaporkan "belum terhitung".
            # Fail-soft: apa pun yang gagal di sini TIDAK boleh menggagalkan produksi.
            try:
                from src.utils import cost_meter
                cost_meter.add_tts(self.model, len(text))
                u = data.get("usageMetadata") or {}
                if u.get("promptTokenCount") or u.get("candidatesTokenCount"):
                    cost_meter.add_tts_tokens(self.model,
                                              u.get("promptTokenCount", 0),
                                              u.get("candidatesTokenCount", 0))
            except Exception:
                pass
            return output_path
        except TTSError:
            raise
        except Exception as e:
            raise TTSError(f"Gemini TTS gagal: {e}") from e

    def get_word_timestamps(self) -> list[dict] | None:
        return None   # tidak disediakan API — caption memakai estimasi (pola edge/openai_tts)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def supports_word_timestamps(self) -> bool:
        return False
