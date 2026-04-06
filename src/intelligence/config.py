import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TenantConfig:
    """Konfigurasi per tenant — setiap user punya instance ini"""
    tenant_id: str
    niche: str = "universe_mysteries"
    language: str = "en"
    target_audience: str = "global"
    videos_per_day: int = 1
    platforms: list = field(default_factory=lambda: ["youtube"])
    posting_hour: int = 8
    style: str = "educational_entertaining"
    hook_style: str = "question"
    video_duration: int = 58

@dataclass
class SystemConfig:
    """Konfigurasi mesin (platform) — bukan milik tenant.
    Hanya berisi infra yang dioperasikan platform: Supabase, R2, Redis.
    API key tenant (OpenAI, Anthropic, ElevenLabs, dll) disimpan di tenant_configs Supabase.
    """
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))
    r2_endpoint: str = field(default_factory=lambda: os.getenv("R2_ENDPOINT", ""))
    r2_access_key: str = field(default_factory=lambda: os.getenv("R2_ACCESS_KEY", ""))
    r2_secret_key: str = field(default_factory=lambda: os.getenv("R2_SECRET_KEY", ""))
    r2_bucket: str = field(default_factory=lambda: os.getenv("R2_BUCKET", "viral-machine"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

NICHES = {
    "universe_mysteries": {
        "name": "Universe Mysteries",
        "keywords": ["space", "universe", "galaxy", "black hole", "nasa", "cosmos", "astronomy"],
        "style": "mysterious and awe-inspiring",
        "target_emotion": "wonder and curiosity",
        "hook_templates": [
            "Scientists just discovered something that changes everything...",
            "This is what exists beyond the observable universe...",
            "NASA captured something they can't explain...",
        ]
    },
    "fun_facts": {
        "name": "Mind-Blowing Facts",
        "keywords": ["did you know", "facts", "amazing", "incredible", "surprising", "world record"],
        "style": "energetic and surprising",
        "target_emotion": "surprise and excitement",
        "hook_templates": [
            "Did you know that...",
            "This fact will blow your mind...",
            "Most people don't know this, but...",
        ]
    },
    "dark_history": {
        "name": "Dark History",
        "keywords": ["history", "mystery", "ancient", "secret", "civilization", "unsolved"],
        "style": "dramatic and intriguing",
        "target_emotion": "intrigue and suspense",
        "hook_templates": [
            "This historical secret was hidden for centuries...",
            "The real story behind this event is terrifying...",
            "History books never told you this...",
        ]
    },
    "ocean_mysteries": {
        "name": "Ocean Mysteries",
        "keywords": ["ocean", "deep sea", "marine", "underwater", "creature", "abyss"],
        "style": "mysterious and fascinating",
        "target_emotion": "fascination and fear",
        "hook_templates": [
            "Something massive lives in the deep ocean...",
            "Scientists found this at the bottom of the sea...",
            "This creature shouldn't exist, but it does...",
        ]
    }
}

VIRAL_SCORE_WEIGHTS = {
    "search_volume": 0.25,
    "trend_momentum": 0.25,
    "emotional_trigger": 0.20,
    "competition_gap": 0.15,
    "evergreen_potential": 0.15
}

system_config = SystemConfig()
