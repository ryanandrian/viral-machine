"""
ElevenLabs TTS Provider — suara paling natural, berbayar.
Fase 6C s6c8 upgrade:
  - SDK v2.40.0: audio via audio_base_64 (bukan response.audio)
  - Word-level timestamps: gabung char-level → word-level
  - Voice di-resolve di config layer (channels.voice_key, §10.B FINAL); delivery override via tts_voice_settings
"""

import base64
from pathlib import Path

from loguru import logger

from src.providers.tts.base import TTSProvider, TTSError
from src.exceptions import ErrorClass


# [ERROR-MGMT 2026-07-18] Classifier transport ElevenLabs-DIRECT (SPEC AI_ERROR_MANAGEMENT_ARCHITECTURE.md
# §4 registry). HANYA kode terverifikasi dari log kita (16-Jun quota_exceeded, 17-Jul payment_issue).
# Kode belum-terbukti → UNKNOWN (aman). CATATAN: ElevenLabs-VIA-fal BUKAN di sini — itu milik adapter fal.
# [2026-08-12] TABEL KODE PINDAH ke `src/providers/galat_registry.py` (satu-satunya tempat pemetaan
# galat penyedia AI). Tabel lama hanya punya 3 kode dari sampel; dokumen resmi ElevenLabs menyebut
# jauh lebih banyak (`insufficient_credits` 402 · `concurrent_limit_exceeded` · `subscription_required`
# 403 · `voice_not_found` 404 · `system_busy` · `invalid_api_key`). Yang tinggal di sini: ANJURAN
# untuk tenant, karena kalimatnya khas komponen SUARA.
# Kalimat kurasi (dari pesan provider asli terverifikasi) — dipakai bila message terstruktur tak terbaca.
_EL_HUMAN = {
    ErrorClass.ACCOUNT_BILLING: "Langganan ElevenLabs bermasalah: pembayaran gagal/belum lunas. Selesaikan tagihan (invoice) di ElevenLabs, lalu Jalankan Ulang.",
    ErrorClass.QUOTA_EXHAUSTED: "Kredit ElevenLabs habis untuk permintaan ini. Isi ulang/upgrade paket di ElevenLabs, lalu Jalankan Ulang.",
}


def _classify_el_error(exc: Exception) -> tuple[ErrorClass, str | None]:
    """Galat SDK ElevenLabs → (ErrorClass, anjuran). Pembungkus tipis di atas registry tunggal.

    Kode dibaca dari body terstruktur bila ada, else dari teks. Pesan PENYEDIA diutamakan apa adanya
    (owner 08-Agu: jangan diterjemahkan); anjuran kita hanya dipakai bila penyedia tak berpesan.
    """
    from src.providers.galat_registry import golongkan

    detail = {}
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        d = body.get("detail")
        if isinstance(d, dict):
            detail = d
    blob = str(exc)
    kode = str(detail.get("code") or detail.get("status") or "") or None
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    pesan_penyedia = detail.get("message") if isinstance(detail.get("message"), str) else None

    p = golongkan("elevenlabs", status=status, kode=kode, teks=blob, pesan=pesan_penyedia)
    if p.kelas is ErrorClass.UNKNOWN and not p.milik_kita:
        return ErrorClass.UNKNOWN, pesan_penyedia
    return p.kelas, (pesan_penyedia or _EL_HUMAN.get(p.kelas))


def _chars_to_words(
    characters: list[str],
    start_times: list[float],
    end_times: list[float],
) -> list[dict]:
    """
    Konversi character-level timestamps → word-level timestamps.
    Gabungkan karakter non-spasi yang berurutan menjadi satu kata.
    """
    words      = []
    cur_word   = ""
    word_start = None
    word_end   = None

    for char, t_start, t_end in zip(characters, start_times, end_times):
        if char == " " or char == "":
            if cur_word:
                words.append({
                    "word":  cur_word,  # s71e: pertahankan tanda baca untuk smart grouping
                    "start": round(word_start, 3),
                    "end":   round(word_end, 3),
                })
                cur_word   = ""
                word_start = None
                word_end   = None
        else:
            if word_start is None:
                word_start = t_start
            cur_word += char
            word_end  = t_end

    # Flush kata terakhir
    if cur_word:
        words.append({
            "word":  cur_word,  # s71e: pertahankan tanda baca untuk smart grouping
            "start": round(word_start, 3),
            "end":   round(word_end, 3),
        })

    return [w for w in words if w["word"]]


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS — suara paling natural, word-level timestamps akurat.
    SDK v2.40.0: audio via audio_base_64, alignment via .characters.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        if not self.api_key:
            raise TTSError(
                "ElevenLabs membutuhkan API key. "
                "Set ELEVENLABS_API_KEY di .env atau tts_api_key di tenant_configs."
            )
        # F1-05: voice sudah ter-resolve di config layer (channels.voice_key → voice_catalog; niches.voice_* dibuang 0083).
        # Provider pakai apa adanya — NO map hardcode, NO fallback (gagal jujur bila kosong).
        self.voice = config.get("tts_voice")
        if not self.voice:
            raise TTSError(
                "ElevenLabs: voice belum ter-resolve. Set voice di Channel (channels.voice_key, §10.B FINAL)."
            )

        # POINT 1 (no-hardcode): model TTS dari config (channels.tts_model → katalog ai_models component='tts').
        # Sebelumnya `eleven_turbo_v2_5` DIPAKU di generate() → tenant tak bisa pilih model + biaya per-model
        # mustahil. Kini config-driven; default di-resolve di config layer (sort_order katalog). Gagal jujur bila kosong.
        self.model = (config.get("tts_model") or "").strip()
        if not self.model:
            raise TTSError(
                "ElevenLabs: model TTS belum ter-resolve. Set model di Channel (channels.tts_model) "
                "atau pastikan katalog ai_models punya model 'tts' aktif untuk provider 'elevenlabs'."
            )

        self._word_timestamps: list[dict] | None = None

    async def generate(self, text: str, output_path: Path) -> Path:
        """Generate audio + word-level timestamps via ElevenLabs API."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from elevenlabs.client import AsyncElevenLabs
        except ImportError:
            raise TTSError("elevenlabs tidak terinstall. Jalankan: python3.11 -m pip install elevenlabs")

        logger.info(f"[ElevenLabs] voice={self.voice} model={self.model} chars={len(text)}")

        try:
            from elevenlabs import VoiceSettings
            client = AsyncElevenLabs(api_key=self.api_key)
            niche  = self.config.get("niche") or ""

            # F1-05 (no-hardcode): baseline delivery = voice_catalog.default_settings (per voice,
            # di-inject config layer); override per-tenant via tts_voice_settings[niche] (mis. ryan speed 0.86).
            baseline      = self.config.get("tts_voice_default_settings", {}) or {}
            # [EKSPRESI VOKAL 2026-07-16] lapisan resmi per-NICHE (niches.voice_expression via editor
            # DNA admin+studio): hanya style/stability (speed = milik mesin durasi), guard 0..1.
            _expr_raw = self.config.get("niche_voice_expression") or {}
            _expr = {k: float(v) for k, v in _expr_raw.items()
                     if k in ("style", "stability") and isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0}                     if isinstance(_expr_raw, dict) else {}
            tts_vs_config = self.config.get("tts_voice_settings", {}) or {}
            _override     = tts_vs_config.get(niche, {}) if isinstance(tts_vs_config, dict) else {}
            # Urutan: bawaan-suara ⊕ ekspresi-niche ⊕ warisan-tenant. `speed` DIKELUARKAN dari lapisan
            # warisan — lihat catatan di bawah.
            niche_vs      = {**baseline, **_expr, **{k: v for k, v in _override.items() if k != "speed"}}
            # ── LAJU BICARA: HANYA dari baseline katalog, dan bawaannya 1,0 ──────────────────────────
            # DULU: `float(niche_vs.get("speed", 0.87))` — dua cacat sekaligus.
            #  (a) Bawaan 0,87 DITANAM DI KODE: suara ElevenLabs mana pun yang katalognya tak menyebut
            #      speed dibacakan 13% LEBIH LAMBAT dari rancangan suaranya, tanpa terlihat di layar
            #      mana pun. Kembaran persis cacat `+10%` di adaptor Edge, tapi ke arah yang justru
            #      dikeluhkan owner: "seperti orang malas".
            #  (b) Lapisan `tts_voice_settings[niche].speed` menang di atas segalanya, dan nilai lamanya
            #      masih ada di DB SETIAP tenant (0,83–0,93) — sisa lubang tempat solver durasi dulu
            #      menyuntikkan pengali kecepatan. Solvernya dicabut 31-Jul; jalur datanya tertinggal.
            # Akibat ketiga yang tak terlihat: sampel dengan speed≠1 DITOLAK penjaga kalibrasi (0184),
            # sehingga suara ElevenLabs tak akan pernah bisa mengkalibrasi dirinya — selamanya.
            from src.production.voice_delivery import RASIO_ALAMI, rasio_laju, rasio_teks
            if _override.get("speed") is not None:
                logger.warning(
                    f"[ElevenLabs] setelan lama tts_voice_settings[{niche}].speed="
                    f"{_override.get('speed')} DIABAIKAN — kecepatan suara bukan tuas durasi (aturan "
                    f"owner 2026-07-29); laju bicara hanya dari voice_catalog.default_settings.")
            from src.config.format_catalog import tts_speed_range as _rng
            _rasio = rasio_laju(baseline, _rng(self.config.get('tts_provider') or 'elevenlabs'))
            if abs(_rasio - RASIO_ALAMI) > 0.001:
                logger.warning(
                    f"[ElevenLabs] laju bicara {_rasio:.2f}× laju alami untuk voice={self.voice} "
                    f"(voice_catalog.default_settings.speed). Aturan owner: 1,0. "
                    f"{'Lebih LAMBAT' if _rasio < 1 else 'Lebih cepat'} dari rancangan suaranya.")
            voice_settings = VoiceSettings(
                stability        = float(niche_vs.get("stability",        0.30)),
                similarity_boost = float(niche_vs.get("similarity_boost", 0.75)),
                style            = float(niche_vs.get("style",            0.50)),
                speed            = _rasio,
            )
            self.effective_rate = rasio_teks(_rasio)
            source = "supabase" if tts_vs_config.get(niche) else "default"
            logger.info(
                f"[ElevenLabs] voice_settings [{source}] niche={niche}: "
                f"speed={voice_settings.speed} style={voice_settings.style} "
                f"stability={voice_settings.stability}"
            )
            response = await client.text_to_speech.convert_with_timestamps(
                voice_id=self.voice,
                text=text,
                model_id=self.model,
                output_format="mp3_44100_128",
                voice_settings=voice_settings,
            )

            # Decode audio dari base64 (SDK v2.40.0)
            if not response.audio_base_64:
                raise TTSError("ElevenLabs response: audio_base_64 kosong")

            audio_bytes = base64.b64decode(response.audio_base_64)
            output_path.write_bytes(audio_bytes)

            # Parse word-level timestamps dari character alignment
            al = response.alignment
            if al and al.characters and al.character_start_times_seconds:
                self._word_timestamps = _chars_to_words(
                    al.characters,
                    al.character_start_times_seconds,
                    al.character_end_times_seconds,
                )
                logger.info(
                    f"[ElevenLabs] ✅ {len(self._word_timestamps)} word timestamps "
                    f"(akurasi ~98%)"
                )
            else:
                self._word_timestamps = None
                logger.warning("[ElevenLabs] Alignment tidak tersedia — karaoke tidak akurat")

            size_kb = output_path.stat().st_size / 1024
            logger.info(f"[ElevenLabs] Generated: {output_path.name} ({size_kb:.1f} KB)")
            return output_path

        except TTSError:
            raise
        except Exception as e:
            # [ERROR-MGMT] klasifikasikan di transport (di sinilah kode EL pasti) → bawa error_class
            # + human_message terstruktur ke atas (ditelan tts_engine → dipropagasi via last_*).
            ec, human = _classify_el_error(e)
            raise TTSError(f"ElevenLabs generation failed: {e}", step="tts",
                           error_class=ec, human_message=human) from e

    def get_word_timestamps(self) -> list[dict] | None:
        return self._word_timestamps

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    @property
    def supports_word_timestamps(self) -> bool:
        return True
