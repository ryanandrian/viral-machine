"""
Registry adaptor TTS — per PROTOKOL transport (mirror pola providers/llm).

Dispatch TTS TIDAK lagi hardcode di tts_engine/tenant_config (if-elif di banyak tempat) — semua
lewat `build_tts_provider(provider_key, config)` yang resolve PROTOKOL dari DB (`tts_profiles.adapter`,
migr 0080) → kelas adaptor di `_adapter_registry()`.

Tambah provider TTS pada protokol yang SAMA = cukup baris DB (tts_profiles + voice_catalog) tanpa koding.
Protokol benar-benar baru (mis. Typecast/Fish) = tambah 1 adaptor di sini + daftarkan di DB.
"""

from src.providers.tts.base import TTSProvider, TTSError

# provider_key legacy → adapter (fallback bila tts_profiles.adapter NULL/belum ter-migrasi). NON-BREAKING.
_LEGACY_ADAPTER = {"elevenlabs": "elevenlabs", "openai_tts": "openai_speech", "edge_tts": "edge"}


def _adapter_registry() -> dict:
    """Registry PROTOKOL transport TTS (kode). Key = `tts_profiles.adapter`.
    Lazy import (hindari circular import saat modul provider meng-import balik)."""
    from src.providers.tts.elevenlabs import ElevenLabsProvider
    from src.providers.tts.openai_tts import OpenAITTSProvider
    from src.providers.tts.edge_tts   import EdgeTTSProvider
    from src.providers.tts.gemini_tts import GeminiTTSProvider
    from src.providers.tts.fal_tts    import FalTTSProvider
    return {
        "fal_tts":       FalTTSProvider,       # protokol fal.ai (model ElevenLabs via fal; penanda per-karakter)
        "elevenlabs":    ElevenLabsProvider,   # protokol ElevenLabs convert_with_timestamps
        "openai_speech": OpenAITTSProvider,    # protokol OpenAI audio.speech (kompatibel vendor lain via base_url)
        "edge":          EdgeTTSProvider,      # protokol Microsoft Edge Communicate (gratis)
        "gemini_speech": GeminiTTSProvider,    # protokol Google generateContent AUDIO (kunci sama dgn LLM Gemini)
    }


def build_tts_provider(provider_key: str, config: dict) -> TTSProvider:
    """Bangun provider TTS dari katalog DB (`tts_profiles.adapter`) + config tenant — DB-driven,
    NO hardcode-dispatch, NO silent fallback (selaras §3.8). Mirror `build_llm_provider`.
    provider_key kosong / adaptor protokol belum didukung kode → gagal JUJUR (TTSError)."""
    if not provider_key:
        raise TTSError("Provider TTS belum dikonfigurasi (channel.tts_provider kosong).")
    from src.config.format_catalog import tts_adapter
    adapter = tts_adapter(provider_key) or _LEGACY_ADAPTER.get(provider_key)
    cls = _adapter_registry().get(adapter)
    if not cls:
        raise TTSError(
            f"Adaptor TTS protokol '{adapter}' (provider '{provider_key}') belum didukung kode. "
            f"Daftarkan adaptor di src/providers/tts + set tts_profiles.adapter (admin)."
        )
    return cls(config)


__all__ = ["TTSProvider", "TTSError", "build_tts_provider"]
