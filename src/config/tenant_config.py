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
import time
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# ──────────────────────────────────────────────────────────
# Niche Registry — fully Supabase-driven via get_niches()
# Tidak ada hardcode di sini. Admin tambah/nonaktifkan niche via tabel niches di Supabase.

# Plan limits — Supabase-driven (tabel plan_limits) = ADMIN-EDITABLE (channel + video/hari per tier,
# tunable lihat-kondisi-pasar tanpa redeploy). Fallback HANYA bila Supabase down (safety net, bukan hardcode caps).
_PLAN_LIMITS_FALLBACK = {
    "trial":    {"max_videos_per_day": 1, "max_channels": 1},
    "starter":  {"max_videos_per_day": 1, "max_channels": 1},
    "pro":      {"max_videos_per_day": 3, "max_channels": 3},
    "business": {"max_videos_per_day": 5, "max_channels": 10},
}
_plan_limits_cache: Optional[dict] = None


def _get_plan_limits() -> dict:
    """Load plan limits dari Supabase tabel plan_limits. Cache per-process."""
    global _plan_limits_cache
    if _plan_limits_cache is not None:
        return _plan_limits_cache
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            sb     = create_client(url, key)
            result = sb.table("plan_limits").select("*").execute()
            if result.data:
                limits = {
                    row["plan_type"]: {
                        "max_videos_per_day": row.get("max_videos_per_day", 1),
                        "max_channels":       row.get("max_channels", 1),
                    }
                    for row in result.data if row.get("plan_type")
                }
                if limits:
                    _plan_limits_cache = limits
                    logger.info(f"[PlanLimits] Loaded from Supabase: {list(limits.keys())}")
                    return _plan_limits_cache
    except Exception as e:
        logger.error(f"[PlanLimits] Supabase load GAGAL ({e}) — pakai fallback SEMENTARA "
                     f"(caps darurat, BISA BASI vs admin); TIDAK di-cache → coba lagi panggilan berikutnya")
    # JANGAN cache fallback (Tahap 5.1d finalisasi_tier_plan): blip transient tak boleh membekukan
    # caps hardcoded selamanya — begitu Supabase pulih, panggilan berikut memuat nilai admin terkini.
    return _PLAN_LIMITS_FALLBACK

# FOSIL DIHAPUS ([B3] 2026-07-05, approval owner): OPTIMAL_PUBLISH_SLOTS + auto-slot per-tenant.
# Jadwal publish NYATA = per-CHANNEL `channels.publish_slots` (zona tenant) — dibaca publisher.py;
# jalur per-tenant ini terbukti NOL pemakai (grep: tak ada konsumen TenantRunConfig.publish_slots).


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
    niche:              str   = ""   # diset dari DB; '' → fail-loud (no global default)
    niche_fallback:     Optional[str] = None  # Phase 1.2: fallback PILIHAN tenant (bukan global mystery)
    language:           str   = "en-US"  # bahasa KONTEN (locale BCP-47) — overlay dari channels.content_language
    videos_per_day:     int   = 1
    max_videos_per_day: int   = 1
    publish_platforms:  list  = field(default_factory=lambda: ["youtube"])
    # publish_slots + auto_schedule DIHAPUS ([B3] 2026-07-05) — fosil per-tenant; jadwal nyata = channels.publish_slots
    timezone:           str   = "UTC"
    production_cron:    str   = "0 13 * * *"
    analytics_cron:     str   = "0 13 * * *"

    # Visual mode (GENERATOR AI saja; stock footage Pexels = fosil v1, dibuang 2026-06-24)
    visual_mode:        str   = ""
    # 'ai_image:gpt-image-1-mini' → AI generated image + motion
    # 'ai_image:cf-flux-schnell' → AI generated image + motion (Cloudflare, gratis harian)
    # 'ai_video:*'               → AI video generation (DISABLED v0.2)

    # Fase 6C fields
    script_min_viral_score: int            = 75
    script_max_retry:       int            = 3
    music_enabled:          bool           = False
    music_volume:           float          = 0.10
    music_default_mood:     Optional[str]  = None   # Phase 1.5: fallback mood; kosong → any-active (no global default)
    tts_voice_settings:     dict           = None
    niche_mode:             str            = "fixed"
    niche_pool:             list           = None

    # Fase 7 s71 — multi-channel
    duplicate_lookback_days: int  = 30            # window duplicate check (hari)
    channel_group:           str  = "default"     # grup channel multi-tenant SaaS
    caption_style:          Optional[dict] = None
    hook_title_style:       Optional[dict] = None
    trailing_silence:       float          = 2.5
    niche_hashtags:         Optional[dict] = None

    # Niche data dari tabel niches (loaded dinamis dari Supabase)
    niche_visual_style:     dict = field(default_factory=dict)
    niche_visual_fallbacks: list = field(default_factory=list)

    # Developer tenant
    is_developer:       bool  = False
    discount_pct:       int   = 0
    peak_region:        str   = "us"

    # Notifikasi Telegram (s81)
    telegram_enabled:   bool           = True
    telegram_chat_id:   Optional[str]  = None   # Per-tenant (DB) — WAJIB; no fallback env (kosong=notif skip)
    channel_name:       str            = ""     # Display name: "RAD The Explorer"

    # Loop Ending Video (s83)
    loop_ending_enabled:  bool  = True   # Tambah loop ending → watch time meningkat
    loop_ending_duration: float = 1.5   # Durasi loop clip yang ditambah di akhir (detik)

    # Niche Rotation (s84) — dipakai ScheduleManager Layer 2
    default_niche_rotation: list = field(default_factory=list)  # ["universe_mysteries", ...]
    niche_rotation_index:   int  = 0                            # posisi saat ini di rotasi

    # Jenis konten — Short Form vs Long Form (s92)
    # 'short' → YouTube Shorts, portrait 9:16
    # 'long'  → YouTube regular, landscape 16:9 (belum diimplementasi)
    content_type: str = "short"

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
    tts_model:         Optional[str] = None   # F1-05: model TTS opsional (mis. openai tts-1/tts-1-hd); None → default engine
    tts_voice_default_settings: Optional[dict] = None   # F1-05: default_settings voice dari voice_catalog (baseline delivery; no-hardcode)
    voice_delivery_wps: Optional[float] = None          # F5-01: pace PER-VOICE (voice_catalog.delivery_wps). None → fallback tts_profiles[provider]. Guard [1.0,4.0].
    tts_api_key:       Optional[str] = None

    visual_api_key:    Optional[str] = None
    visual_ai_model:   Optional[str] = None
    image_quality:     str           = "low"

    llm_provider:      str           = ""   # legacy flat (back-compat); sumber kebenaran = llm_library
    llm_model:         str           = ""   # legacy flat (back-compat); sumber kebenaran = llm_models
    llm_api_key:       Optional[str] = None
    llm_library:       Optional[str]  = None  # Phase 1.1: 'anthropic'|'openai'. None → derive dari llm_provider
    llm_models:        Optional[dict] = None  # Phase 1.1 per-task: script/utility/rewrite/analyzer/fallback

    def to_provider_config(self) -> dict:
        """
        Konversi ke dict yang dipakai oleh semua provider.
        Keys dari tenant DB only — tidak ada env fallback (DESIGN.md).
        """
        return {
            # Identity
            "tenant_id": self.tenant_id,
            "niche":     self.niche,
            "niche_fallback": self.niche_fallback or "",
            "language":  self.language,

            # TTS
            "tts_provider": self.tts_provider,
            "tts_voice":    self.tts_voice,
            "tts_model":    self.tts_model or "",
            "tts_voice_default_settings": self.tts_voice_default_settings or {},
            "tts_api_key":  self.tts_api_key or "",

            # Visual
            "visual_api_key":         self.visual_api_key or "",
            "visual_ai_model":        self.visual_ai_model,
            "image_quality":          self.image_quality,
            "niche_visual_style":     self.niche_visual_style,
            "niche_visual_fallbacks": self.niche_visual_fallbacks,

            # LLM
            "llm_provider":  self.effective_llm_provider(),
            "llm_model":     self.llm_model_for("script"),
            "llm_api_key":   self.llm_api_key or "",
            "llm_library":   self.llm_library or "",
            "llm_models":    self.llm_models or {},
            "visual_mode":   self.visual_mode,
            "is_developer":  self.is_developer,
            "discount_pct":  self.discount_pct,
        }

    # F5-06: get_tts_provider() & get_visual_provider() DIHAPUS — vestigial (tak dipanggil di mana pun;
    # dispatch nyata via build_tts_provider / build_visual_provider). get_llm_provider tetap (DIPAKAI).

    def get_llm_provider(self):
        """Return LLMProvider instance via factory tunggal (config-driven).
        Pemilihan provider berdasarkan llm_library/llm_provider — lihat
        src/providers/llm/__init__.py (sumber tunggal registry)."""
        from src.providers.llm import build_llm_provider
        return build_llm_provider(self.to_provider_config())

    def effective_llm_provider(self) -> str:
        """Routing key provider ('claude'|'openai') — Phase 1.1.
        Prioritas llm_library; fallback ke kolom flat legacy llm_provider."""
        lib = (self.llm_library or "").lower()
        if lib in ("anthropic", "claude"):
            return "claude"
        if lib in ("openai", "gpt"):
            return "openai"
        p = (self.llm_provider or "").lower()
        if p in ("claude", "anthropic"):
            return "claude"
        if p in ("openai", "gpt"):
            return "openai"
        return ""  # tak terkonfigurasi → factory/caller fail-loud (TANPA default provider)

    def llm_model_for(self, task: str) -> str:
        """Model untuk task tertentu (script/utility/rewrite/analyzer/fallback) — Phase 1.1.
        Prioritas llm_models[task]; fallback ke kolom flat legacy llm_model."""
        if isinstance(self.llm_models, dict) and self.llm_models.get(task):
            return self.llm_models[task]
        if self.llm_model:
            return self.llm_model
        return ""  # llm_models & llm_model kosong → fail-loud di adapter (TANPA model hardcode)

    def niche_or_fallback(self) -> str:
        """Niche efektif tenant — TANPA default global. Urutan: niche_fallback
        (pilihan tenant) → niche → niche_pool[0]. Kosong semua → '' (caller fail-loud,
        no-silent-degradation). Niche dijamin ada di hulu (onboarding/schedule gate)."""
        for cand in (self.niche_fallback, self.niche):
            if cand and str(cand).strip():
                return cand
        if self.niche_pool:
            return self.niche_pool[0]
        return ""

    def missing_credentials(self) -> list[str]:
        """Phase 4.5: daftar key WAJIB yang belum diisi, per provider terpilih tenant.
        Dipakai pipeline utk fail-loud SEBELUM produksi (35 mnt). Provider gratis
        (edge_tts) tak perlu key. YouTube OAuth dicek di publish (pool tenant_youtube_accounts)."""
        missing = []
        if not (self.llm_api_key or "").strip():
            missing.append(f"llm_api_key (LLM: {self.effective_llm_provider() or '?'})")
        if (self.tts_provider or "") in ("elevenlabs", "openai_tts") and not (self.tts_api_key or "").strip():
            missing.append(f"tts_api_key ({self.tts_provider})")
        if (self.visual_mode or "").startswith(("ai_image:", "ai_video:")) and not (self.visual_api_key or "").strip():
            missing.append("visual_api_key (AI visual generation)")
        return missing


class TenantConfigManager:
    """
    Manager untuk load dan cache TenantRunConfig dari Supabase.

    Fallback hierarchy:
      1. Supabase tenant_configs
      2. Default values + env variables
    """

    # Umur cache config (detik). Worker hidup berhari-hari — tanpa kedaluwarsa, perubahan setelan
    # tenant/channel di DB tidak pernah terbaca sampai restart (insiden live 2026-07-08: ganti
    # penyedia naskah berkali-kali via UI, produksi tetap memakai setelan pertama yang ter-cache).
    _CACHE_TTL_S = 120

    def __init__(self):
        self._cache: dict[str, tuple[TenantRunConfig, float]] = {}
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

    def load(self, tenant_id: str, channel_id: str | None = None,
             niche: str | None = None, use_cache: bool = True) -> TenantRunConfig:
        """
        Load TenantRunConfig untuk tenant_id tertentu.

        Args:
            tenant_id:  ID tenant (contoh: 'ryan_andrian')
            channel_id: bila diberi → overlay kolom per-channel `channels` (F1-05: model/voice/
                        caption/visual/music/quality) DI ATAS config tenant. None → murni per-tenant
                        (BACKWARD-COMPATIBLE: pemanggil lama tak berubah).
            niche:      niche RUN ini (untuk resolusi voice default per niche×provider). None → rc.niche.
            use_cache:  Pakai cache jika sudah pernah di-load (default: True)

        Returns:
            TenantRunConfig siap pakai (sudah ter-overlay channel bila channel_id diberi)
        """
        cache_key = f"{tenant_id}|{channel_id or '-'}|{niche or '-'}"
        if use_cache:
            hit = self._cache.get(cache_key)
            if hit and (time.time() - hit[1]) < self._CACHE_TTL_S:
                return hit[0]

        config = self._load_from_supabase(tenant_id)
        if not config:
            logger.warning(
                f"[TenantConfig] tenant '{tenant_id}' tidak ada di Supabase — "
                f"pakai default config"
            )
            config = self._default_config(tenant_id)

        if channel_id:
            try:
                self._apply_channel_overlay(config, channel_id, niche)
            except Exception as e:
                logger.warning(f"[TenantConfig] overlay channel gagal (ch={channel_id}): {e} — pakai config tenant")

        self._cache[cache_key] = (config, time.time())
        return config

    # Kolom channels per-channel (F1-04) → field TenantRunConfig. Hanya overlay bila NOT NULL
    # (NULL = belum dikonfigurasi → pakai nilai tenant; transisi aman).
    _CHANNEL_OVERLAY_FIELDS = [
        "llm_model", "llm_library", "tts_provider", "tts_model",
        "visual_mode", "image_quality", "caption_style", "niche_hashtags",
        "music_enabled", "music_volume", "music_default_mood",
        "script_min_viral_score", "script_max_retry",
    ]

    def _apply_channel_overlay(self, config: "TenantRunConfig", channel_id: str, niche: str | None) -> None:
        """F1-05/§10.B FINAL: overlay config per-channel + resolusi voice = `channels.voice_key` SAJA
        (voice = CHANNEL; niche provider-agnostik tanpa voice). Key BYOK & plan TETAP dari tenant.
        Mutasi `config` in-place (instance fresh per cache_key → tak ada shared-mutation)."""
        if not self._supabase:
            return
        res = self._supabase.table("channels").select("*").eq("id", channel_id).limit(1).execute()
        ch = (res.data or [None])[0]
        if not ch:
            logger.warning(f"[TenantConfig] channel {channel_id} tak ditemukan — overlay dilewati")
            return
        tenant_llm_library = (getattr(config, "llm_library", None) or "").strip().lower()
        for f in self._CHANNEL_OVERLAY_FIELDS:
            v = ch.get(f)
            if v is not None:
                setattr(config, f, v)
        # [B11] G3 (Batch 2.3a) — KOHERENSI penyedia↔model naskah: bila channel memilih penyedia
        # BERBEDA dari tenant, routing per-task tenant (`llm_models` = model milik penyedia tenant)
        # WAJIB gugur → semua task pakai model pilihan channel (`llm_model`, sudah ter-overlay).
        # Tanpa ini model penyedia lama disodorkan ke penyedia baru → 404 "model is not found"
        # (insiden live 2026-07-08, channel ke-2 ryan). Channel se-penyedia dgn tenant → routing
        # per-task tenant tetap dipakai (perilaku channel-1 tidak berubah).
        ch_lib = (ch.get("llm_library") or "").strip().lower()
        if ch_lib and tenant_llm_library and ch_lib != tenant_llm_library:
            if (ch.get("llm_model") or "").strip():
                config.llm_models = None
                logger.info(f"[TenantConfig] channel {channel_id}: penyedia naskah channel ({ch_lib}) "
                            f"≠ tenant ({tenant_llm_library}) → semua task pakai model channel '{config.llm_model}'")
            else:
                logger.error(f"[TenantConfig] channel {channel_id}: llm_library={ch_lib} tanpa llm_model — "
                             f"model tenant milik penyedia lain ({tenant_llm_library}); produksi akan gagal jujur.")
        # [B11] Batch 1.5 — nama channel utk notifikasi Telegram = PER-CHANNEL (channels.channel_name),
        # bukan tenant_configs.channel_name (dulu: semua channel tenant berlabel sama di notif).
        if ch.get("channel_name"):
            config.channel_name = ch["channel_name"]
        # Bahasa KONTEN per-channel → field `language` (nama kolom channel ≠ nama field, jadi di luar
        # loop overlay). NULL (channel lama) → biarkan default en-US = perilaku lama.
        if ch.get("content_language"):
            config.language = ch["content_language"]
        # POINT 1 (no-hardcode model TTS): bila channel set tts_provider tapi tts_model kosong →
        # pakai DEFAULT katalog (ai_models component='tts', provider channel, sort_order terkecil aktif).
        # Adapter (elevenlabs/openai) jadi nol-hardcode model; channel baru tetap jalan tanpa paksa-isi.
        if getattr(config, "tts_provider", None) and not (getattr(config, "tts_model", None) or "").strip():
            try:
                dm = self._supabase.table("ai_models").select("model_key") \
                    .eq("component", "tts").eq("provider_key", config.tts_provider) \
                    .eq("is_active", True).order("sort_order").limit(1).execute()
                if dm.data:
                    config.tts_model = dm.data[0]["model_key"]
            except Exception as e:
                logger.warning(f"[TenantConfig] resolve default tts_model gagal ({config.tts_provider}): {e}")
        # Resolusi VOICE (PER-CHANNEL, §10.B FINAL owner 2026-06-23): voice = channels.voice_key
        # (1 channel = 1 voice). NO-FALLBACK ke niche (niche provider-agnostik, tak punya voice).
        vkey = ch.get("voice_key")
        if vkey:
            config.tts_voice = vkey
            # default_settings voice (baseline delivery, no-hardcode) dari voice_catalog.
            try:
                vc = self._supabase.table("voice_catalog").select("default_settings, delivery_wps").eq("voice_key", vkey).limit(1).execute()
                if vc.data:
                    config.tts_voice_default_settings = vc.data[0].get("default_settings") or {}
                    # F5-01: pace per-voice (override engine). NULL → biarkan None → estimator fallback ke provider.
                    config.voice_delivery_wps = vc.data[0].get("delivery_wps")
            except Exception as e:
                logger.warning(f"[TenantConfig] load default_settings/pace voice {vkey} gagal: {e}")
        # KUNCI per-elemen = POOL tenant (tenant_ai_accounts, status='valid'), provider-aware (owner 2026-06-24).
        # Penyedia tiap elemen: LLM=llm_library · TTS=tts_provider · Visual=penyedia model di visual_mode.
        # NO-FALLBACK: tak ada di pool / invalid → kunci kosong → produksi gagal jujur (tak pinjam apa pun).
        self._set_key_from_pool(config, config.tenant_id, getattr(config, "llm_library", None),  "llm_api_key",    ch.get("llm_account_id"))
        self._set_key_from_pool(config, config.tenant_id, getattr(config, "tts_provider", None),  "tts_api_key",    ch.get("tts_account_id"))
        self._set_key_from_pool(config, config.tenant_id, self._visual_provider(config),          "visual_api_key", ch.get("visual_account_id"))
        logger.info(f"[TenantConfig] overlay ch={channel_id}: tts={config.tts_provider}/{config.tts_voice} "
                    f"llm={config.llm_model} visual={config.visual_mode}")

    def _visual_provider(self, config: "TenantRunConfig") -> Optional[str]:
        """Penyedia visual dari model di visual_mode (ai_image:/ai_video:<model> → ai_models.provider_key)."""
        vm = getattr(config, "visual_mode", "") or ""
        mkey = vm.split(":", 1)[1] if ":" in vm else ""
        if not mkey or not self._supabase:
            return None
        try:
            r = self._supabase.table("ai_models").select("provider_key").eq("model_key", mkey).limit(1).execute()
            row = (r.data or [None])[0]
            return row.get("provider_key") if row else None
        except Exception:
            return None

    def _set_key_from_pool(self, config: "TenantRunConfig", tenant_id: str, provider: Optional[str],
                           key_attr: str, account_id: Optional[str] = None) -> None:
        """Set key elemen dari POOL tenant_ai_accounts (Fernet). Model VENDOR/key-group (CHANNEL_LOCK final 2026-06-25):
        Prioritas (1) AKUN yg DITUGASKAN channel (account_id, harus status='valid'); (2) fallback AUTO = akun tunggal
        valid utk VENDOR (key_group) penyedia itu — `openai_tts` pakai kunci vendor `openai` (1 kunci OpenAI utk GPT+TTS+image).
        NO-FALLBACK lain → '' (produksi gagal jujur)."""
        if not provider or not self._supabase:
            setattr(config, key_attr, "")
            return
        try:
            from src.utils.crypto import decrypt
            row = None
            if account_id:
                r = (self._supabase.table("tenant_ai_accounts").select("key_enc,status")
                     .eq("id", account_id).eq("tenant_id", tenant_id).limit(1).execute())
                cand = (r.data or [None])[0]
                row = cand if (cand and cand.get("status") == "valid") else None  # ditugaskan tapi tak valid → no-fallback
            if not row:
                kg = provider  # vendor key-group; openai_tts → openai
                pr = self._supabase.table("ai_providers").select("key_group").eq("provider_key", provider).limit(1).execute()
                if pr.data and pr.data[0].get("key_group"):
                    kg = pr.data[0]["key_group"]
                r = (self._supabase.table("tenant_ai_accounts").select("key_enc")
                     .eq("tenant_id", tenant_id).eq("key_group", kg).eq("status", "valid")
                     .order("validated_at", desc=True).limit(1).execute())
                row = (r.data or [None])[0]
            setattr(config, key_attr, (decrypt(row["key_enc"]) if row and row.get("key_enc") else "") or "")
        except Exception as e:
            logger.error(f"[TenantConfig] resolve pool key provider={provider} acct={account_id} gagal: {e} — kosong (no-fallback)")
            setattr(config, key_attr, "")

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
                f"| visual_mode={row.get('visual_mode')} "
                f"| llm={row.get('llm_model')}"
            )

            # Validasi niche
            niche = row.get("niche") or ""
            # Validasi niche dari registry (Supabase-driven, no hardcode)
            try:
                from src.intelligence.config import get_niches
                registry      = get_niches()
                active_niches = [k for k, v in registry.items() if v.get("is_active", True)]
                if niche not in registry:
                    fallback = active_niches[0] if active_niches else niche
                    logger.warning(
                        f"[TenantConfig] Niche '{niche}' tidak ada di registry — "
                        f"fallback ke '{fallback}'"
                    )
                    niche = fallback
                elif not registry[niche].get("is_active", True):
                    fallback = active_niches[0] if active_niches else niche
                    logger.warning(
                        f"[TenantConfig] Niche '{niche}' nonaktif — "
                        f"fallback ke '{fallback}'"
                    )
                    niche = fallback
            except Exception as _ne:
                logger.warning(f"[TenantConfig] Validasi niche gagal ({_ne}) — pakai niche as-is")

            # Load niche visual data dari tabel niches (dynamic, no hardcode)
            niche_visual_style     = {}
            niche_visual_fallbacks = []
            try:
                niche_row = (
                    self._supabase
                    .table("niches")
                    .select("visual_style, visual_fallbacks")
                    .eq("niche_id", niche)
                    .single()
                    .execute()
                )
                if niche_row.data:
                    niche_visual_style     = niche_row.data.get("visual_style") or {}
                    niche_visual_fallbacks = niche_row.data.get("visual_fallbacks") or []
                    logger.debug(f"[TenantConfig] Niche visual data loaded: {niche}")
            except Exception as e:
                logger.warning(f"[TenantConfig] Gagal load niche visual data: {e}")

            # Validasi plan limits — dari Supabase, bukan hardcode
            plan_type           = row.get("plan_type", "starter")
            _limits_map         = _get_plan_limits()
            limits              = _limits_map.get(plan_type, _limits_map.get("starter", {"max_videos_per_day": 1, "max_channels": 1}))
            videos_per_day      = min(
                row.get("videos_per_day", 1),
                limits["max_videos_per_day"]
            )

            return TenantRunConfig(
                tenant_id=tenant_id,
                plan_type=plan_type,
                niche=niche,
                # Bahasa KONTEN = per-CHANNEL (channels.content_language via _apply_channel_overlay).
                # (Fosil row.get("language") DIBUANG 2026-07-05 — tenant_configs tak pernah punya kolom itu.)
                language="en-US",
                videos_per_day=videos_per_day,
                max_videos_per_day=limits["max_videos_per_day"],
                publish_platforms=row.get("publish_platforms") or ["youtube"],
                timezone=row.get("timezone", "UTC") or "UTC",
                production_cron=row.get("production_cron", "0 13 * * *"),
                analytics_cron=row.get("analytics_cron", "0 13 * * *"),
                peak_region=row.get("peak_region", "us"),
                tts_provider=row.get("tts_provider", "edge_tts"),
                tts_voice=row.get("tts_voice", "en-US-GuyNeural"),
                tts_api_key=None,     # kunci = PER-CHANNEL (channels.tts_key_enc via overlay); no-fallback
                visual_api_key=None,  # kunci = PER-CHANNEL (channels.visual_key_enc via overlay); no-fallback
                visual_ai_model=row.get("visual_ai_model"),
                image_quality=row.get("image_quality", "low"),
                llm_provider=row.get("llm_provider"),
                llm_model=row.get("llm_model"),
                llm_api_key=None,     # kunci = PER-CHANNEL (channels.llm_key_enc via overlay); no-fallback
                llm_library=row.get("llm_library"),
                llm_models=row.get("llm_models") if isinstance(row.get("llm_models"), dict) else None,
                visual_mode=row.get("visual_mode", "") or "",
                is_developer=row.get("is_developer", False),
                discount_pct=row.get("discount_pct", 0),
                script_min_viral_score=row.get("script_min_viral_score", 75),
                script_max_retry=row.get("script_max_retry", 3),
                music_enabled=row.get("music_enabled", False),
                music_volume=float(row.get("music_volume", 0.10)),
                music_default_mood=row.get("music_default_mood"),
                tts_voice_settings=row.get("tts_voice_settings") or {},
                niche_mode=row.get("niche_mode", "fixed") or "fixed",
                niche_pool=list(row.get("niche_pool") or []),
                niche_fallback=row.get("niche_fallback"),
                caption_style=row.get("caption_style") if isinstance(row.get("caption_style"), dict) else None,
                hook_title_style=row.get("hook_title_style") if isinstance(row.get("hook_title_style"), dict) else None,
                trailing_silence=float(row.get("trailing_silence") or 2.5),
                niche_hashtags=row.get("niche_hashtags") if isinstance(row.get("niche_hashtags"), dict) else None,
                duplicate_lookback_days = int(row.get("duplicate_lookback_days", 30) or 30),
                channel_group           = row.get("channel_group", "default") or "default",
                niche_visual_style      = niche_visual_style,
                niche_visual_fallbacks  = niche_visual_fallbacks,
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
            niche="",
            language="en-US",
            videos_per_day=1,
            max_videos_per_day=1,
            publish_platforms=["youtube"],
            timezone="UTC",
            production_cron="0 13 * * *",
            analytics_cron="0 13 * * *",
            script_min_viral_score=75,
            script_max_retry=3,
            music_enabled=False,
                music_volume=0.10,
                music_default_mood=None,
                tts_voice_settings={},
                niche_mode="fixed",
                niche_pool=[],
            caption_style=None,
            hook_title_style=None,
            trailing_silence=2.5,
            niche_hashtags=None,
            duplicate_lookback_days = 30,
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
        """Hapus cache tenant (semua channel/niche) — paksa reload dari Supabase.
        Kunci cache = komposit "tenant|channel|niche", jadi hapus per-prefix (pop kunci
        tenant polos tidak pernah cocok — bug lama, tak pernah menghapus apa pun)."""
        gone = [k for k in self._cache if k.split("|", 1)[0] == tenant_id]
        for k in gone:
            self._cache.pop(k, None)
        logger.info(f"[TenantConfig] Cache invalidated: {tenant_id} ({len(gone)} entri)")


# Singleton instance — dipakai seluruh pipeline
_manager: Optional[TenantConfigManager] = None

def get_manager() -> TenantConfigManager:
    global _manager
    if _manager is None:
        _manager = TenantConfigManager()
    return _manager

def load_tenant_config(tenant_id: str, channel_id: str | None = None,
                       niche: str | None = None) -> TenantRunConfig:
    """Shortcut untuk load config — dipakai dari pipeline.py + komponen.
    channel_id → overlay per-channel (F1-05); None → murni per-tenant (backward-compatible)."""
    return get_manager().load(tenant_id, channel_id=channel_id, niche=niche)


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
    print(f"Platforms     : {config.publish_platforms}")
    print(f"Peak region   : {config.peak_region}")
    print(f"TTS Provider  : {config.tts_provider} ({config.tts_voice})")
    print(f"Visual        : {config.visual_mode}")
    print(f"LLM           : {config.llm_provider} / {config.llm_model}")
    print(f"Production    : {config.production_cron}")
    print(f"Analytics     : {config.analytics_cron}")
    print(f"{'='*60}")
