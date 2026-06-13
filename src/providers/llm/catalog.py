"""
Loader katalog AI (ai_providers + ai_models) dari Supabase — config-driven,
admin-managed. Mirror pola get_niches (REST anon key + cache in-memory TTL).

Katalog = SUMBER KEBENARAN provider/model yang tersedia. Super-admin tambah
provider/model lewat DB (tanpa redeploy) → langsung jadi pilihan tenant.
"""

import os
import time

from loguru import logger

_TTL_SECONDS = 300
_CACHE: dict = {"providers": None, "models": None, "ts": 0.0}


def _load_from_supabase() -> tuple[dict, dict]:
    try:
        from supabase import create_client
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(f"supabase-py tidak terinstall: {e}") from e

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not (url and key):
        raise RuntimeError("SUPABASE_URL/KEY tidak tersedia di environment")

    sb = create_client(url, key)
    providers = {
        r["provider_key"]: r
        for r in sb.table("ai_providers").select("*").eq("is_active", True).execute().data
    }
    models = {
        r["model_key"]: r
        for r in sb.table("ai_models").select("*").eq("is_active", True).execute().data
    }
    return providers, models


def _refresh() -> None:
    providers, models = _load_from_supabase()
    _CACHE.update(providers=providers, models=models, ts=time.time())
    logger.info(
        f"[ai_catalog] loaded {len(providers)} providers, {len(models)} models dari Supabase"
    )


def _fresh(value) -> bool:
    return value is not None and (time.time() - _CACHE["ts"]) <= _TTL_SECONDS


def get_providers() -> dict:
    """dict provider_key -> row ai_providers (aktif). Cached TTL 5 menit."""
    if not _fresh(_CACHE["providers"]):
        _refresh()
    return _CACHE["providers"]


def get_models() -> dict:
    """dict model_key -> row ai_models (aktif). Cached TTL 5 menit."""
    if not _fresh(_CACHE["models"]):
        _refresh()
    return _CACHE["models"]


def invalidate() -> None:
    """Reset cache — dipanggil saat admin update katalog."""
    _CACHE.update(providers=None, models=None, ts=0.0)
