"""Sumber-tunggal nilai-sah katalog AI (adapter/transport/enum) — CERMIN dari registry KODE ke DB.

Kenapa ada: form admin (FE) + validasi tulis (route.ts) butuh tahu nilai `adapter`/`auth_type`/
`component` yang BENAR-BENAR didukung mesin. Kebenaran itu ada di KODE (registry adapter), bukan di DB.
Modul ini mencerminkan registry kode → tabel `catalog_valid_values` saat startup service (webhook+worker).
Kode = kebenaran; DB = cermin yang di-refresh tiap restart → NOL drift, adapter baru muncul otomatis,
FE & validasi server baca dari satu tempat. (Owner 2026-07-07: "tuntas + antisipatif".)

Field yang dicerminkan:
  llm_adapter       — kunci ADAPTERS (build_llm_provider). Yang dibaca ai_providers.adapter jalur LLM.
  tts_adapter       — kunci _adapter_registry() TTS (tts_profiles.adapter).
  visual_transport  — kunci _TRANSPORTS visual (platform = provider_key).
  auth_type         — cara kunci: api_key (butuh token) / none (gratis, mis. edge).
  component         — jenis model yang didukung pipeline: llm/image/video/tts.
  pricing_unit:<jenis> — SATUAN HARGA yang sah untuk jenis model itu, dari DAFTAR SATUAN di
                      `src/billing/ai_cost.py` (SSOT: ARSITEKTUR_AI_PROVIDER_MODEL §7b). Layar
                      panel & layar tenant MEMBACA ini — jadi tak ada satu pun nama satuan/label
                      yang diketik di kode layar. [23-Agu] Sebelumnya pengetahuan itu diketik ulang
                      di 2 layar; salah satunya tak punya cabang video sehingga model video
                      menampilkan harga "/gambar" selama berbulan-bulan.
"""
from __future__ import annotations
import os
from typing import Dict, List, Tuple
from loguru import logger


def _service_sb():
    """Klien Supabase service_role (pola sama dgn webhook_app._sb / tenant_config)."""
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Konstanta STRUKTURAL (kapabilitas mesin — bukan config; single-source di kode).
AUTH_TYPES: List[Tuple[str, str]] = [
    ("api_key", "Perlu API token"),
    ("none",    "Gratis tanpa kunci"),
]
COMPONENTS: List[Tuple[str, str]] = [
    ("llm",   "Penulis naskah (LLM)"),
    ("tts",   "Pengisi suara (TTS)"),
    ("image", "Gambar (text-to-image)"),
    ("video", "Video (text-to-video)"),
]
# Tingkat kualitas model (produk) — set terhingga per tabel; single-source di kode → mirror.
MODEL_TIERS: List[Tuple[str, str]] = [
    ("basic", "Basic"), ("standard", "Standard"), ("premium", "Premium"), ("fast", "Fast"),
]
LANGUAGE_TIERS: List[Tuple[str, str]] = [
    ("official", "Official"), ("experimental", "Experimental"),
]
GENDERS: List[Tuple[str, str]] = [("male", "Male"), ("female", "Female")]
# Kelas TTS (format_catalog.tts_class): 'timed' (word-timeframe) | 'fast_fallback' (edge).
TTS_CLASSES: List[Tuple[str, str]] = [("timed", "Timed"), ("fast_fallback", "Fast fallback")]


def collect_valid_values() -> List[Dict[str, str]]:
    """Kumpulkan nilai-sah dari registry KODE + konstanta struktural. Import lazy (hindari sirkular)."""
    rows: List[Dict[str, str]] = []

    def _label(kind: str, key: str) -> str:
        return key.replace("_", " ").title()

    # LLM adapters (build_llm_provider)
    try:
        from src.providers.llm.adapters import ADAPTERS
        for k in sorted(ADAPTERS.keys()):
            rows.append({"field": "llm_adapter", "value": k, "label": _label("llm", k)})
    except Exception as e:
        logger.warning(f"[catalog_sync] registry LLM gagal dibaca: {e}")

    # TTS adapters (_adapter_registry)
    try:
        from src.providers.tts import _adapter_registry
        for k in sorted(_adapter_registry().keys()):
            rows.append({"field": "tts_adapter", "value": k, "label": _label("tts", k)})
    except Exception as e:
        logger.warning(f"[catalog_sync] registry TTS gagal dibaca: {e}")

    # Visual transports (_TRANSPORTS)
    try:
        from src.providers.visual.ai_image import AIImageProvider
        for k in sorted(AIImageProvider._TRANSPORTS.keys()):
            rows.append({"field": "visual_transport", "value": k, "label": _label("visual", k)})
    except Exception as e:
        logger.warning(f"[catalog_sync] registry visual gagal dibaca: {e}")

    for v, lbl in AUTH_TYPES:
        rows.append({"field": "auth_type", "value": v, "label": lbl})
    for v, lbl in COMPONENTS:
        rows.append({"field": "component", "value": v, "label": lbl})
    for v, lbl in MODEL_TIERS:
        rows.append({"field": "model_tier", "value": v, "label": lbl})
    for v, lbl in LANGUAGE_TIERS:
        rows.append({"field": "language_tier", "value": v, "label": lbl})
    for v, lbl in GENDERS:
        rows.append({"field": "gender", "value": v, "label": lbl})
    for v, lbl in TTS_CLASSES:
        rows.append({"field": "tts_class", "value": v, "label": lbl})

    # Satuan harga per jenis model — DITURUNKAN dari daftar, tak diketik ulang di sini.
    try:
        from src.billing.ai_cost import SATUAN_HARGA
        for sat in SATUAN_HARGA:
            rows.append({"field": f"pricing_unit:{sat.jenis}", "value": sat.kunci,
                         "label": sat.label})
    except Exception as e:
        logger.warning(f"[catalog_sync] daftar satuan harga gagal dibaca: {e}")
    return rows


def sync_catalog_valid_values(sb=None) -> dict:
    """Upsert nilai-sah kode → DB, lalu HAPUS baris usang (yang tak lagi ada di kode). Idempoten.
    Dipanggil saat startup service. Return ringkasan {synced, deleted}."""
    if sb is None:
        sb = _service_sb()
    rows = collect_valid_values()
    keys_now = {(r["field"], r["value"]) for r in rows}
    # Upsert (PK komposit field+value).
    sb.table("catalog_valid_values").upsert(rows, on_conflict="field,value").execute()
    # Hapus usang.
    deleted = 0
    try:
        existing = sb.table("catalog_valid_values").select("field,value").execute().data or []
        stale = [(e["field"], e["value"]) for e in existing if (e["field"], e["value"]) not in keys_now]
        for f, v in stale:
            sb.table("catalog_valid_values").delete().eq("field", f).eq("value", v).execute()
            deleted += 1
    except Exception as e:
        logger.warning(f"[catalog_sync] pembersihan usang gagal (non-fatal): {e}")
    logger.info(f"[catalog_sync] cermin nilai-sah: {len(rows)} disinkron, {deleted} usang dihapus")
    return {"synced": len(rows), "deleted": deleted}
