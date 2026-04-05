"""
Tenant Config Manager — jembatan antara Supabase dan pipeline.
Baca konfigurasi tenant dari Supabase tenant_configs,
inisialisasi provider yang sesuai, return TenantRunConfig siap pakai.

Fallback hierarchy:
  1. Supabase tenant_configs (sumber utama)
  2. Environment variables .env (fallback)
  3. Default values hardcode (last resort)
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# ──────────────────────────────────────────────────────────
# Niche Registry — Curated + Expandable
# Tambah niche baru di sini setelah dikonfigurasi penuh
# ──────────────────────────────────────────────────────────

AVAILABLE_NICHES = {
    "universe_mysteries",
    "fun_facts",
    "dark_history",
    "ocean_mysteries",
    # Tier 2 — coming soon:
    # "finance_money",
    # "motivational_psychology",
    # "tech_ai_facts",
    # "true_crime",
}

# Plan limits — dikontrol di sini, bukan di database
PLAN_LIMITS = {
    "starter": {"max_videos_per_day": 1,  "max_channels": 1},
    "pro":     {"max_videos_per_day": 3,  "max_channels": 3},
    "agency":  {"max_videos_per_day": 5,  "max_channels": 10},
}

# Publish slots optimal per jumlah video (UTC)
OPTIMAL_PUBLISH_SLOTS = {
    1: ["13:00"],
    2: ["13:00", "00:00"],
    3: ["09:00", "13:00", "00:00"],
    4: ["07:00", "11:00", "15:00", "00:00"],
    5: ["07:00", "10:00", "13:00", "17:00", "00:00"],
}


@dataclass
class TenantRunConfig:
    """
    Konfigurasi lengkap satu tenant untuk satu run pipeline.
    Sudah include provider instances yang siap dipakai.
    """
    # Identity
    tenant_id:   str
    plan_type:   str = "starter"

    # Pipeline settings
    niche:              str   = "universe_mysteries"
    language:           str   = "en"
    videos_per_day:     int   = 1
    max_videos_per_day: int   = 1
    publish_platforms:  list  = field(default_factory=lambda: ["youtube"])
    publish_slots:      list  = field(default_factory=lambda: ["13:00"])
    production_cron:    str   = "0 13 * * *"
    analytics_cron:     str   = "0 13 * * *"

    # Visual mode
    visual_mode:        str   = "video"
    # 'video'              → stock footage (Pexels/Getty/dll)
    # 'ai_image:dall-e-3'  → AI generated image + motion
    # 'ai_image:flux-schnell' → AI generated image + motion (cheaper)
    # 'ai_video:*'         → AI video generation (DISABLED v0.2)

    # Fase 6C fields
    script_min_viral_score: int            = 75
    script_max_retry:       int            = 3
    tts_voice_per_niche:    Optional[dict] = None
    music_enabled:          bool           = False
    music_volume:           float          = 0.10
    tts_voice_settings:     dict           = None
    niche_mode:             str            = "fixed"
    niche_pool:             list           = None

    # Fase 7 s71 — Provider fallback + billing behavior + multi-channel
    duplicate_lookback_days: int  = 30            # window duplicate check (hari)
    production_on_api_error: str  = "fallback"    # 'fallback' | 'stop_and_notify'
    tts_fallback_provider:   str  = "edge_tts"    # fallback jika primary TTS error
    visual_fallback_mode:    str  = "video"       # fallback jika primary visual error
    llm_script_fallback:     str  = "gpt-4o-mini" # fallback jika Claude error
    channel_group:           str  = "default"     # grup channel multi-tenant SaaS
    caption_style:          Optional[dict] = None
    hook_title_style:       Optional[dict] = None
    trailing_silence:       float          = 2.5
    niche_hashtags:         Optional[dict] = None

    # Developer tenant
    is_developer:       bool  = False
    discount_pct:       int   = 0
    auto_schedule:      bool  = True
    peak_region:        str   = "us"

    # Notifikasi Telegram (s81)
    telegram_enabled:   bool           = True
    telegram_chat_id:   Optional[str]  = None   # Per-tenant; fallback ke env TELEGRAM_CHAT_ID
    channel_name:       str            = ""     # Display name: "RAD The Explorer"

    # Loop Ending Video (s83)
    loop_ending_enabled:  bool  = True   # Tambah loop ending → watch time meningkat
    loop_ending_duration: float = 1.5   # Durasi loop clip yang ditambah di akhir (detik)

    # Niche Rotation (s84) — dipakai ScheduleManager Layer 2
    default_niche_rotation: list = field(default_factory=list)  # ["universe_mysteries", ...]
    niche_rotation_index:   int  = 0                            # posisi saat ini di rotasi

    # OAuth Token — multi-channel ready (s84d)
    # Konvensi: tokens/{channel_id}.json — satu file per channel
    # Fallback: token_youtube.json (backward compatible)
    youtube_token_path: str = ""  # diisi otomatis dari tenant_id jika kosong

    def get_youtube_token_path(self) -> str:
        """
        Resolve path token YouTube untuk channel ini.
        Priority: youtube_token_path (dari Supabase) → tokens/{tenant_id}.json → token_youtube.json
        """
        if self.youtube_token_path:
            return self.youtube_token_path
        per_channel = f"tokens/{self.tenant_id}.json"
        if os.path.exists(per_channel):
            return per_channel
        return "token_youtube.json"  # backward compatible fallback

    # Provider settings (raw config — provider diinisialisasi saat dibutuhkan)
    tts_provider:      str           = "edge_tts"
    tts_voice:         str           = "en-US-GuyNeural"
    tts_api_key:       Optional[str] = None

    visual_provider:   str           = "pexels"
    visual_max_clip_mb: int          = 50
    visual_api_key:    Optional[str] = None
    visual_ai_model:   Optional[str] = None

    llm_provider:      str           = "openai"
    llm_model:         str           = "gpt-4o-mini"
    llm_api_key:       Optional[str] = None

    def to_provider_config(self) -> dict:
        """
        Konversi ke dict yang dipakai oleh semua provider.
        Inject system API keys dari .env jika tenant tidak punya key sendiri.
        """
        return {
            # Identity
            "tenant_id": self.tenant_id,
            "niche":     self.niche,
            "language":  self.language,

            # TTS
            "tts_provider": self.tts_provider,
            "tts_voice":    self.tts_voice,
            "tts_api_key":  (
                self.tts_api_key
                or os.getenv("ELEVENLABS_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            ),

            # Visual
            "visual_provider":    self.visual_provider,
            "visual_max_clip_mb": self.visual_max_clip_mb,
            "visual_api_key":     (
                self.visual_api_key
                or os.getenv("PEXELS_API_KEY")
                or os.getenv("REPLICATE_API_TOKEN")
            ),
            "visual_ai_model": self.visual_ai_model,

            # LLM
            "llm_provider": self.llm_provider,
            "llm_model":    self.llm_model,
            "visual_mode":  self.visual_mode,
            "is_developer":  self.is_developer,
            "discount_pct":  self.discount_pct,
            "llm_api_key":  (
                self.llm_api_key
                or os.getenv("OPENAI_API_KEY")
            ),
        }

    def get_tts_provider(self):
        """Inisialisasi dan return TTS provider instance."""
        from src.providers.tts.edge_tts   import EdgeTTSProvider
        from src.providers.tts.elevenlabs import ElevenLabsProvider
        from src.providers.tts.openai_tts import OpenAITTSProvider

        cfg = self.to_provider_config()
        providers = {
            "edge_tts":    EdgeTTSProvider,
            "elevenlabs":  ElevenLabsProvider,
            "openai_tts":  OpenAITTSProvider,
        }
        cls = providers.get(self.tts_provider)
        if not cls:
            logger.warning(
                f"TTS provider '{self.tts_provider}' tidak dikenal — "
                f"fallback ke edge_tts"
            )
            cls = EdgeTTSProvider
        return cls(cfg)

    def get_visual_provider(self):
        """Inisialisasi dan return Visual provider instance."""
        from src.providers.visual.pexels   import PexelsProvider
        from src.providers.visual.ai_image import AIImageProvider
        from src.providers.visual.ai_video import AIVideoProvider

        cfg = self.to_provider_config()

        if self.visual_provider == "pexels":
            return PexelsProvider(cfg)
        elif self.visual_provider.startswith("ai_image:"):
            return AIImageProvider(cfg)
        elif self.visual_provider.startswith("ai_video:"):
            return AIVideoProvider(cfg)  # Akan raise VisualError — DISABLED
        else:
            logger.warning(
                f"Visual provider '{self.visual_provider}' tidak dikenal — "
                f"fallback ke pexels"
            )
            return PexelsProvider(cfg)

    def get_llm_provider(self):
        """Inisialisasi dan return LLM provider instance."""
        from src.providers.llm.openai import OpenAIProvider

        cfg = self.to_provider_config()
        providers = {
            "openai": OpenAIProvider,
        }
        cls = providers.get(self.llm_provider)
        if not cls:
            logger.warning(
                f"LLM provider '{self.llm_provider}' tidak dikenal — "
                f"fallback ke openai"
            )
            cls = OpenAIProvider
        return cls(cfg)


class TenantConfigManager:
    """
    Manager untuk load dan cache TenantRunConfig dari Supabase.

    Fallback hierarchy:
      1. Supabase tenant_configs
      2. Default values + env variables
    """

    def __init__(self):
        self._cache: dict[str, TenantRunConfig] = {}
        self._supabase = self._init_supabase()

    def _init_supabase(self):
        """Init Supabase client — return None jika tidak tersedia."""
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                return create_client(url, key)
            logger.warning("[TenantConfig] SUPABASE_URL/KEY tidak ada — pakai defaults")
            return None
        except Exception as e:
            logger.warning(f"[TenantConfig] Supabase init failed: {e} — pakai defaults")
            return None

    def load(self, tenant_id: str, use_cache: bool = True) -> TenantRunConfig:
        """
        Load TenantRunConfig untuk tenant_id tertentu.

        Args:
            tenant_id:  ID tenant (contoh: 'ryan_andrian')
            use_cache:  Pakai cache jika sudah pernah di-load (default: True)

        Returns:
            TenantRunConfig siap pakai
        """
        if use_cache and tenant_id in self._cache:
            return self._cache[tenant_id]

        config = self._load_from_supabase(tenant_id)
        if not config:
            logger.warning(
                f"[TenantConfig] tenant '{tenant_id}' tidak ada di Supabase — "
                f"pakai default config"
            )
            config = self._default_config(tenant_id)

        self._cache[tenant_id] = config
        return config

    def _load_from_supabase(self, tenant_id: str) -> Optional[TenantRunConfig]:
        """Load config dari Supabase. Return None jika gagal."""
        if not self._supabase:
            return None
        try:
            result = (
                self._supabase
                .table("tenant_configs")
                .select("*")
                .eq("tenant_id", tenant_id)
                .single()
                .execute()
            )
            if not result.data:
                return None

            row = result.data
            logger.info(
                f"[TenantConfig] Loaded from Supabase: {tenant_id} "
                f"| tts={row.get('tts_provider')} "
                f"| visual={row.get('visual_provider')} "
                f"| llm={row.get('llm_model')}"
            )

            # Validasi niche
            niche = row.get("niche", "universe_mysteries")
            if niche not in AVAILABLE_NICHES:
                logger.warning(
                    f"[TenantConfig] Niche '{niche}' tidak tersedia — "
                    f"fallback ke universe_mysteries"
                )
                niche = "universe_mysteries"

            # Validasi plan limits
            plan_type           = row.get("plan_type", "starter")
            limits              = PLAN_LIMITS.get(plan_type, PLAN_LIMITS["starter"])
            videos_per_day      = min(
                row.get("videos_per_day", 1),
                limits["max_videos_per_day"]
            )

            # Publish slots: dari DB atau otomatis berdasarkan videos_per_day
            publish_slots = row.get("publish_slots") or []
            if not publish_slots or row.get("auto_schedule", True):
                publish_slots = OPTIMAL_PUBLISH_SLOTS.get(videos_per_day, ["13:00"])

            return TenantRunConfig(
                tenant_id=tenant_id,
                plan_type=plan_type,
                niche=niche,
                language=row.get("language", "en"),
                videos_per_day=videos_per_day,
                max_videos_per_day=limits["max_videos_per_day"],
                publish_platforms=row.get("publish_platforms") or ["youtube"],
                publish_slots=publish_slots,
                production_cron=row.get("production_cron", "0 13 * * *"),
                analytics_cron=row.get("analytics_cron", "0 13 * * *"),
                auto_schedule=row.get("auto_schedule", True),
                peak_region=row.get("peak_region", "us"),
                tts_provider=row.get("tts_provider", "edge_tts"),
                tts_voice=row.get("tts_voice", "en-US-GuyNeural"),
                tts_api_key=row.get("tts_api_key"),
                visual_provider=row.get("visual_provider", "pexels"),
                visual_max_clip_mb=row.get("visual_max_clip_mb", 50),
                visual_api_key=row.get("visual_api_key"),
                visual_ai_model=row.get("visual_ai_model"),
                llm_provider=row.get("llm_provider", "openai"),
                llm_model=row.get("llm_model", "gpt-4o-mini"),
                llm_api_key=row.get("llm_api_key"),
                visual_mode=row.get("visual_mode", "video"),
                is_developer=row.get("is_developer", False),
                discount_pct=row.get("discount_pct", 0),
                script_min_viral_score=row.get("script_min_viral_score", 75),
                script_max_retry=row.get("script_max_retry", 3),
                tts_voice_per_niche=row.get("tts_voice_per_niche") if isinstance(row.get("tts_voice_per_niche"), dict) else None,
                music_enabled=row.get("music_enabled", False),
                music_volume=float(row.get("music_volume", 0.10)),
                tts_voice_settings=row.get("tts_voice_settings") or {},
                niche_mode=row.get("niche_mode", "fixed") or "fixed",
                niche_pool=list(row.get("niche_pool") or ["universe_mysteries"]),
                caption_style=row.get("caption_style") if isinstance(row.get("caption_style"), dict) else None,
                hook_title_style=row.get("hook_title_style") if isinstance(row.get("hook_title_style"), dict) else None,
                trailing_silence=float(row.get("trailing_silence") or 2.5),
                niche_hashtags=row.get("niche_hashtags") if isinstance(row.get("niche_hashtags"), dict) else None,
                duplicate_lookback_days = int(row.get("duplicate_lookback_days", 30) or 30),
                production_on_api_error = row.get("production_on_api_error", "fallback") or "fallback",
                tts_fallback_provider   = row.get("tts_fallback_provider", "edge_tts") or "edge_tts",
                visual_fallback_mode    = row.get("visual_fallback_mode", "video") or "video",
                llm_script_fallback     = row.get("llm_script_fallback", "gpt-4o-mini") or "gpt-4o-mini",
                channel_group           = row.get("channel_group", "default") or "default",
                # Telegram (s81)
                telegram_enabled        = row.get("telegram_enabled", True),
                telegram_chat_id        = row.get("telegram_chat_id") or None,
                channel_name            = row.get("channel_name", "") or "",
                # Loop Ending (s83)
                loop_ending_enabled     = row.get("loop_ending_enabled", True),
                loop_ending_duration    = float(row.get("loop_ending_duration") or 1.5),
                # Niche Rotation (s84)
                default_niche_rotation  = list(row.get("default_niche_rotation") or []),
                niche_rotation_index    = int(row.get("niche_rotation_index") or 0),
                # OAuth Token path (s84d) — opsional, auto-resolve jika kosong
                youtube_token_path      = row.get("youtube_token_path") or "",
            )

        except Exception as e:
            logger.error(f"[TenantConfig] Supabase load failed for '{tenant_id}': {e}")
            return None

    def _default_config(self, tenant_id: str) -> TenantRunConfig:
        """Default config dari environment variables — fallback terakhir."""
        return TenantRunConfig(
            tenant_id=tenant_id,
            plan_type="starter",
            niche="universe_mysteries",
            language="en",
            videos_per_day=1,
            max_videos_per_day=1,
            publish_platforms=["youtube"],
            publish_slots=["13:00"],
            production_cron="0 13 * * *",
            analytics_cron="0 13 * * *",
            script_min_viral_score=75,
            script_max_retry=3,
            music_enabled=False,
                music_volume=0.10,
                tts_voice_settings={},
                niche_mode="fixed",
                niche_pool=["universe_mysteries"],
            tts_voice_per_niche=None,
            caption_style=None,
            hook_title_style=None,
            trailing_silence=2.5,
            niche_hashtags=None,
            duplicate_lookback_days = 30,
            production_on_api_error = "fallback",
            tts_fallback_provider   = "edge_tts",
            visual_fallback_mode    = "video",
            llm_script_fallback     = "gpt-4o-mini",
            channel_group           = "default",
            # Telegram (s81)
            telegram_enabled        = True,
            telegram_chat_id        = None,
            channel_name            = "",
            # Loop Ending (s83)
            loop_ending_enabled     = True,
            loop_ending_duration    = 1.5,
            # Niche Rotation (s84)
            default_niche_rotation  = [],
            niche_rotation_index    = 0,
            # OAuth Token path (s84d)
            youtube_token_path      = "",
        )

    def invalidate_cache(self, tenant_id: str) -> None:
        """Hapus cache untuk tenant tertentu — paksa reload dari Supabase."""
        self._cache.pop(tenant_id, None)
        logger.info(f"[TenantConfig] Cache invalidated: {tenant_id}")


# Singleton instance — dipakai seluruh pipeline
_manager: Optional[TenantConfigManager] = None

def get_manager() -> TenantConfigManager:
    global _manager
    if _manager is None:
        _manager = TenantConfigManager()
    return _manager

def load_tenant_config(tenant_id: str) -> TenantRunConfig:
    """Shortcut untuk load config — dipakai dari pipeline.py."""
    return get_manager().load(tenant_id)


if __name__ == "__main__":
    # Quick test
    logger.info("Testing TenantConfigManager...")
    config = load_tenant_config("ryan_andrian")

    print(f"\n{'='*60}")
    print(f"TENANT CONFIG: {config.tenant_id}")
    print(f"{'='*60}")
    print(f"Plan          : {config.plan_type}")
    print(f"Niche         : {config.niche}")
    print(f"Language      : {config.language}")
    print(f"Videos/day    : {config.videos_per_day} (max: {config.max_videos_per_day})")
    print(f"Publish slots : {config.publish_slots}")
    print(f"Platforms     : {config.publish_platforms}")
    print(f"Peak region   : {config.peak_region}")
    print(f"TTS Provider  : {config.tts_provider} ({config.tts_voice})")
    print(f"Visual        : {config.visual_provider} (max {config.visual_max_clip_mb}MB)")
    print(f"LLM           : {config.llm_provider} / {config.llm_model}")
    print(f"Production    : {config.production_cron}")
    print(f"Analytics     : {config.analytics_cron}")
    print(f"{'='*60}")
