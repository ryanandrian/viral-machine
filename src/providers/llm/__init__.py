"""
Factory LLM — DB-driven. Provider/model dipilih dari KATALOG Supabase
(ai_providers/ai_models, admin-managed), BUKAN registry hardcode di kode.
Kode hanya punya adapter per-protokol transport (lihat adapters.py).

Dipakai oleh tenant_config.get_llm_provider() dan providers/visual/ai_image.
"""

from src.providers.llm.base import LLMProvider, LLMError, parse_json_lenient
from src.providers.llm.adapters import ADAPTERS
from src.providers.llm import catalog

# Alias kompatibilitas kolom legacy llm_provider ('claude'/'gpt') -> provider_key
# katalog. HANYA untuk membaca config lama; bukan daftar provider (itu di DB).
_LEGACY_PROVIDER_ALIAS = {"claude": "anthropic", "gpt": "openai"}


def _resolve_provider_key(cfg: dict) -> str:
    """provider_key (referensi ai_providers) dari config tenant.
    Prioritas llm_library; fallback kolom legacy llm_provider (di-alias)."""
    lib = (cfg.get("llm_library") or "").strip().lower()
    if lib:
        return lib
    prov = (cfg.get("llm_provider") or "").strip().lower()
    return _LEGACY_PROVIDER_ALIAS.get(prov, prov)


def build_llm_provider(cfg: dict) -> LLMProvider:
    """Bangun adapter LLM dari katalog DB + key tenant. Semua keputusan provider
    berasal dari DB; pesan error pakai display_name dari DB (nol literal vendor)."""
    provider_key = _resolve_provider_key(cfg)
    if not provider_key:
        raise LLMError(
            "Provider LLM tenant belum dikonfigurasi (llm_library kosong)."
        )

    spec = catalog.get_providers().get(provider_key)
    if not spec:
        raise LLMError(
            f"Provider LLM '{provider_key}' tidak ada / non-aktif di katalog "
            f"(ai_providers). Tambahkan via admin."
        )

    adapter_cls = ADAPTERS.get(spec.get("adapter"))
    if not adapter_cls:
        raise LLMError(
            f"Adapter transport '{spec.get('adapter')}' belum didukung kode "
            f"untuk provider '{spec.get('display_name', provider_key)}'."
        )

    return adapter_cls(
        api_key=cfg.get("llm_api_key") or "",
        display_name=spec.get("display_name") or provider_key,
        base_url=spec.get("base_url"),
        param_schema=spec.get("request_param_schema") or {},
        # [2026-08-12] Identitas vendor diteruskan supaya penilai galat tahu TABEL siapa yang dipakai
        # (`galat_registry`). Nilainya sudah ada di sini — dipakai memilih adaptor & spec — hanya
        # belum pernah diserahkan ke bawah. Tanpa ini penilai menebak vendor dari nama tampilan.
        provider_key=provider_key,
    )


__all__ = [
    "LLMProvider",
    "LLMError",
    "parse_json_lenient",
    "ADAPTERS",
    "catalog",
    "build_llm_provider",
]
