"""
TTS via fal.ai — SATU kunci fal untuk gambar, video, dan suara ElevenLabs.

Kenapa ada: tenant yang sudah punya kunci fal (untuk visual) tak perlu kunci ElevenLabs terpisah.
Kualitas suaranya identik — fal meneruskan model ElevenLabs apa adanya.

PENANDA WAKTU (yang menentukan presisi caption karaoke):
fal mengembalikannya PER KARAKTER, bukan per kata:
    {"characters": [...], "character_start_times_seconds": [...], "character_end_times_seconds": [...]}
Itu justru LEBIH detail daripada per kata. Adaptor ini menggabungkannya jadi per kata
(pecah di spasi; mulai = karakter pertama, selesai = karakter terakhir) — terverifikasi pada
panggilan nyata 2026-07-28: 9 kata masuk, 9 kata keluar, urutan waktu menaik, teks cocok persis.

Endpoint per model diambil dari katalog DB (`ai_models.model_key`), BUKAN hardcode di sini —
menambah model ElevenLabs baru cukup satu baris DB.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

from loguru import logger

from src.providers.tts.base import TTSProvider, TTSError

# Endpoint fal dipanggil sinkron (fal.run) — narasi video pendek selesai dalam hitungan detik;
# antrean (queue.fal.run) hanya perlu untuk pekerjaan panjang seperti video.
_BASE = "https://fal.run/"


def _karakter_ke_kata(blok: list) -> list[dict]:
    """Penanda per-KARAKTER fal → per-KATA (bentuk yang dipakai pembuat subtitle kita).

    Spasi jadi pemisah kata; tanda baca ikut menempel pada katanya (sama seperti keluaran
    ElevenLabs langsung), sehingga pemotong baris di renderer tak perlu tahu asal datanya.
    """
    hasil: list[dict] = []
    for b in blok or []:
        ch = b.get("characters") or []
        st = b.get("character_start_times_seconds") or []
        en = b.get("character_end_times_seconds") or []
        if not (len(ch) == len(st) == len(en)):
            logger.warning("[falTTS] panjang penanda waktu tak sepadan — blok dilewati")
            continue
        kata, mulai = "", None
        for i, k in enumerate(ch):
            if str(k).isspace():
                if kata:
                    hasil.append({"word": kata, "start": round(mulai, 3), "end": round(en[i - 1], 3)})
                    kata = ""
                continue
            if not kata:
                mulai = st[i]
            kata += k
        if kata:
            hasil.append({"word": kata, "start": round(mulai, 3), "end": round(en[-1], 3)})
    return hasil


class FalTTSProvider(TTSProvider):
    """Protokol fal.ai untuk model TTS (saat ini keluarga ElevenLabs di fal)."""

    def __init__(self, config: dict):
        super().__init__(config)
        # Kontrak config = SAMA dgn seluruh adaptor TTS (tts_api_key/tts_model/tts_voice yang
        # dikirim tts_engine._get_provider_config & model_tester) — bukan nama sendiri.
        self.api_key = (config.get("tts_api_key") or "").strip()
        # model_key katalog = endpoint fal, mis. "fal-ai/elevenlabs/tts/turbo-v2.5"
        self.model = (config.get("tts_model") or "").strip()
        # voice = identitas VENDOR (voice_catalog.vendor_voice_id, sudah diterjemahkan
        # build_tts_provider). Provider pakai apa adanya — NO map hardcode.
        self.voice = (config.get("tts_voice") or "").strip()
        self._word_timestamps: list[dict] | None = None

    def _voice_settings(self) -> dict:
        """Delivery efektif — LAPISAN & URUTAN IDENTIK ElevenLabs langsung (src/providers/tts/elevenlabs.py),
        sebab model di balik fal memang model ElevenLabs yang sama: suara yang sama HARUS terdengar sama
        lewat jalur mana pun. Urutan: bawaan-suara (voice_catalog.default_settings) ⊕ ekspresi-niche
        (niches.voice_expression; hanya style/stability, guard 0..1) ⊕ warisan-tenant (tts_voice_settings).
        Rentang nilai dijaga generik di hulu via tts_profiles.param_schema (§10.A), bukan dipaku di sini."""
        baseline = self.config.get("tts_voice_default_settings") or {}
        _expr_raw = self.config.get("niche_voice_expression") or {}
        _expr = ({k: float(v) for k, v in _expr_raw.items()
                  if k in ("style", "stability") and isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0}
                 if isinstance(_expr_raw, dict) else {})
        _vs_all = self.config.get("tts_voice_settings") or {}
        _override = _vs_all.get(self.config.get("niche") or "", {}) if isinstance(_vs_all, dict) else {}
        return {**baseline, **_expr, **(_override if isinstance(_override, dict) else {})}

    async def generate(self, text: str, output_path: Path) -> Path:
        if not self.api_key:
            raise TTSError("Suara lewat fal butuh API key fal (BYOK) — hubungkan akun fal di /integrations.")
        if not self.model:
            raise TTSError("Model TTS fal tidak ditentukan (channels.tts_model / katalog ai_models kosong).")

        payload: dict = {"text": text, "timestamps": True}
        if self.voice:
            payload["voice"] = self.voice
        # Nilai bawaan = ANGKA PERSIS ElevenLabs langsung → suara identik lintas jalur.
        vs = self._voice_settings()
        for kunci, bawaan in (("stability", 0.30), ("similarity_boost", 0.75),
                              ("style", 0.50), ("speed", 0.87)):
            try:
                payload[kunci] = float(vs.get(kunci, bawaan))
            except (TypeError, ValueError):
                payload[kunci] = bawaan

        req = urllib.request.Request(
            _BASE + self.model.lstrip("/"),
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"},
        )
        logger.info(f"[falTTS] model={self.model} voice={self.voice or '(bawaan)'} chars={len(text)} "
                    f"speed={payload['speed']} style={payload['style']} "
                    f"stability={payload['stability']} sim={payload['similarity_boost']}")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read()[:300].decode("utf-8", "replace")
            except Exception:
                pass
            raise TTSError(f"fal TTS gagal (HTTP {e.code}): {detail}") from e
        except Exception as e:
            raise TTSError(f"fal TTS gagal: {e}") from e

        url = ((out.get("audio") or {}).get("url") or "").strip()
        if not url:
            raise TTSError("fal TTS tidak mengembalikan berkas audio.")
        try:
            with urllib.request.urlopen(url, timeout=180) as r, open(output_path, "wb") as f:
                f.write(r.read())
        except Exception as e:
            raise TTSError(f"unduh audio fal gagal: {e}") from e

        self._word_timestamps = _karakter_ke_kata(out.get("timestamps") or [])
        size_kb = Path(output_path).stat().st_size / 1024
        logger.info(f"[falTTS] Generated: {Path(output_path).name} "
                    f"({size_kb:.1f} KB, {len(self._word_timestamps)} words)")
        return Path(output_path)

    def get_word_timestamps(self) -> list[dict] | None:
        return self._word_timestamps

    def provider_name(self) -> str:
        return "fal"

    def supports_word_timestamps(self) -> bool:
        # Penanda per-karakter dari fal digabung jadi per-kata di sini → presisi setara
        # ElevenLabs langsung (bukan estimasi seperti Edge TTS).
        return True
