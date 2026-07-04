"""
AI Cost (B2 BYOK cost-tracking, owner 2026-07-04) — konversi KONSUMSI (cost_meter) → USD.

Harga satuan = katalog `ai_models.pricing` (jsonb):
  {in_per_1m, out_per_1m, per_image, per_1m_chars, source, synced_at}
Diisi otomatis oleh price_sync (feed komunitas LiteLLM, harian) — admin bisa OVERRIDE
(pricing_locked=true → sinkron tak menimpa; wajib utk provider di luar feed, mis. ElevenLabs).

Kejujuran: angka = "konsumsi terukur × harga katalog per synced_at" — BUKAN membaca invoice tenant
(tak ada API-nya). Model tanpa harga → komponen ditandai unpriced (FE tampil jujur, bukan Rp 0 palsu).
"""

import os
from loguru import logger


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _pricing_map(sb=None) -> dict:
    """model_key & model_id → pricing dict (dua kunci → cocok apa pun yang tercatat meter)."""
    sb = sb or _sb()
    rows = sb.table("ai_models").select("model_key, model_id, pricing").execute().data or []
    out = {}
    for r in rows:
        p = r.get("pricing")
        if isinstance(p, dict) and p:
            out[r["model_key"]] = p
            if r.get("model_id"):
                out[r["model_id"]] = p
    return out


def compute_cost_usd(ai_usage: dict, sb=None) -> dict | None:
    """Hitung biaya USD dari ringkasan cost_meter. Return
    {usd, breakdown:{llm,image,tts}, unpriced:[model...], priced_at} — None bila usage kosong."""
    if not ai_usage:
        return None
    try:
        prices = _pricing_map(sb)
    except Exception as e:
        logger.warning(f"[ai_cost] baca pricing gagal: {e}")
        return None

    total, unpriced = 0.0, []
    br = {"llm": 0.0, "image": 0.0, "tts": 0.0}
    synced = None

    for model, u in (ai_usage.get("llm") or {}).items():
        p = prices.get(model)
        if not p or (p.get("in_per_1m") is None and p.get("out_per_1m") is None):
            unpriced.append(model)
            continue
        c = (u.get("tokens_in", 0) / 1e6) * float(p.get("in_per_1m") or 0) \
          + (u.get("tokens_out", 0) / 1e6) * float(p.get("out_per_1m") or 0)
        br["llm"] += c
        synced = synced or p.get("synced_at")

    for model, n in (ai_usage.get("image") or {}).items():
        p = prices.get(model)
        # Model image ber-tagih TOKEN (gpt-image-1 family): tokennya sudah dihitung di bucket llm —
        # hitungan gambar di sini murni info tampilan, BUKAN unpriced.
        if p and p.get("per_image") is None and model in (ai_usage.get("llm") or {}):
            continue
        if not p or p.get("per_image") is None:
            unpriced.append(model)
            continue
        br["image"] += n * float(p.get("per_image") or 0)
        synced = synced or p.get("synced_at")

    for model, chars in (ai_usage.get("tts") or {}).items():
        p = prices.get(model)
        if not p or p.get("per_1m_chars") is None:
            unpriced.append(model)
            continue
        br["tts"] += (chars / 1e6) * float(p.get("per_1m_chars") or 0)
        synced = synced or p.get("synced_at")

    total = br["llm"] + br["image"] + br["tts"]
    return {
        "usd": round(total, 6),
        "breakdown": {k: round(v, 6) for k, v in br.items()},
        "unpriced": sorted(set(unpriced)),
        "priced_at": synced,
    }
