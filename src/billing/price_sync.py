"""
Price Sync (B2, owner 2026-07-04) — sinkron OTOMATIS harga satuan model AI dari feed komunitas
LiteLLM (dipakai luas industri, selalu di-update) → `ai_models.pricing`. Menjawab kekhawatiran owner:
tabel harga TANPA beban update manual.

- Berjalan harian (dipanggil buffer_janitor.run_once, guard app_config 'ai_price_synced_at').
- `pricing_locked=true` = override admin → TIDAK ditimpa (wajib utk model di luar feed, mis. ElevenLabs).
- Model aktif tanpa harga pasca-sinkron → WARNING log (FE Catalog juga menandai ⚠️).
Feed: harga per-token USD → dinormalkan per-1M (in_per_1m/out_per_1m), gambar per_image,
karakter per_1m_chars.
"""

import os
from datetime import datetime, timezone

import requests
from loguru import logger

FEED_URL = os.getenv(
    "AI_PRICE_FEED_URL",
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
)
SYNC_INTERVAL_HOURS = float(os.getenv("AI_PRICE_SYNC_HOURS", "24"))


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _feed_entry(feed: dict, model_id: str) -> dict | None:
    """Cari entri feed: kunci persis → varian umum berprefix provider (mis. 'elevenlabs/<id>').
    (Insiden 2026-07-04: prefix 'elevenlabs/' terlewat → EL dikira tak ada di feed — koreksi owner.)"""
    if model_id in feed:
        return feed[model_id]
    for pref in ("openai/", "anthropic/", "elevenlabs/", "replicate/", "azure/"):
        if pref + model_id in feed:
            return feed[pref + model_id]
    return None


def sync_prices(sb=None, force: bool = False) -> dict:
    """Tarik feed → update ai_models.pricing (skip pricing_locked). Return ringkasan."""
    sb = sb or _sb()

    # Guard harian via app_config (value=INTEGER epoch detik; admin bisa ubah interval via env)
    import time as _time
    if not force:
        try:
            r = sb.table("app_config").select("value").eq("key", "ai_price_synced_at").limit(1).execute()
            last = int(r.data[0]["value"]) if r.data else 0
            if last and (_time.time() - last) < SYNC_INTERVAL_HOURS * 3600:
                return {"skipped": True}
        except Exception:
            pass

    try:
        feed = requests.get(FEED_URL, timeout=30).json()
    except Exception as e:
        logger.warning(f"[price_sync] gagal tarik feed: {e}")
        return {"error": str(e)}

    rows = sb.table("ai_models").select("model_key, model_id, component, pricing, pricing_locked").execute().data or []
    now = datetime.now(timezone.utc).isoformat()
    updated, missing = 0, []
    for m in rows:
        if m.get("pricing_locked"):
            continue
        e = _feed_entry(feed, m.get("model_id") or m["model_key"])
        if not e:
            missing.append(m["model_key"])
            continue
        # mode image_generation (gpt-image-1 family): ditagih PER-TOKEN — output pakai
        # output_cost_per_image_token (token gambar), input pakai input_cost_per_token (token teks prompt).
        out_tok = e.get("output_cost_per_token") or e.get("output_cost_per_image_token")
        pricing = {
            "in_per_1m":    round(float(e["input_cost_per_token"]) * 1e6, 4) if e.get("input_cost_per_token") else None,
            "out_per_1m":   round(float(out_tok) * 1e6, 4) if out_tok else None,
            "per_image":    float(e["output_cost_per_image"]) if e.get("output_cost_per_image") else None,
            "per_1m_chars": round(float(e["input_cost_per_character"]) * 1e6, 4) if e.get("input_cost_per_character") else None,
            "source": "litellm", "synced_at": now,
        }
        if all(v is None for k, v in pricing.items() if k not in ("source", "synced_at")):
            missing.append(m["model_key"])
            continue
        sb.table("ai_models").update({"pricing": pricing}).eq("model_key", m["model_key"]).execute()
        updated += 1

    try:
        sb.table("app_config").upsert({"key": "ai_price_synced_at", "value": int(_time.time()),
                                       "description": "epoch detik sinkron harga model AI terakhir (price_sync)"}).execute()
    except Exception:
        pass

    if missing:
        logger.warning(f"[price_sync] model TANPA harga di feed (isi manual + pricing_locked di Catalog): {missing}")
    logger.info(f"[price_sync] harga model tersinkron: {updated} update, {len(missing)} tanpa-feed")
    return {"updated": updated, "missing": missing}
