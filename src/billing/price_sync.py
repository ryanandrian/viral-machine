"""
Price Sync (B2 + ketahanan, owner 2026-07-04) — sinkron OTOMATIS harga satuan model AI →
`ai_models.pricing`. Tabel harga TANPA beban update manual, DENGAN pengaman:

- Sumber UTAMA: feed komunitas LiteLLM. FALLBACK: API resmi OpenRouter (khusus LLM) bila feed
  gagal/entri tak ada. Keduanya machine-readable — TANPA scraping HTML rapuh. URL via env (replaceable).
- `pricing_locked=true` = override admin → TIDAK ditimpa (harga resmi owner, mis. ElevenLabs).
- SANITY-GUARD: harga baru berubah > AI_PRICE_SANITY_FACTOR (default 3×) dari harga lama → DITAHAN di
  `pricing_pending` + Telegram admin — admin Terapkan/Abaikan di Catalog (kasus nyata: feed EL $180 vs resmi $100).
- ALARM BASI: sinkron macet > AI_PRICE_STALE_DAYS (default 7) → Telegram admin (1×/hari) — matinya
  sumber KETAHUAN, bukan senyap. Feed mati ≠ rusak: harga terakhir tetap dipakai (beku + ber-cap tanggal).
- Berjalan harian via buffer_janitor.run_once (guard app_config 'ai_price_synced_at' epoch).
"""

import os
import time as _time
from datetime import datetime, timezone

import requests
from loguru import logger

FEED_URL = os.getenv(
    "AI_PRICE_FEED_URL",
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
)
FALLBACK_URL = os.getenv("AI_PRICE_FALLBACK_URL", "https://openrouter.ai/api/v1/models")
SYNC_INTERVAL_HOURS = float(os.getenv("AI_PRICE_SYNC_HOURS", "24"))
SANITY_FACTOR = float(os.getenv("AI_PRICE_SANITY_FACTOR", "3"))
STALE_DAYS = float(os.getenv("AI_PRICE_STALE_DAYS", "7"))


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _feed_entry(feed: dict, model_id: str) -> dict | None:
    """Cari entri feed LiteLLM: kunci persis → varian berprefix provider (mis. 'elevenlabs/<id>').
    (Insiden 2026-07-04: prefix 'elevenlabs/' terlewat → EL dikira tak ada di feed — koreksi owner.)"""
    if model_id in feed:
        return feed[model_id]
    for pref in ("openai/", "anthropic/", "elevenlabs/", "replicate/", "azure/"):
        if pref + model_id in feed:
            return feed[pref + model_id]
    return None


def _openrouter_map() -> dict:
    """FALLBACK resmi (LLM saja): OpenRouter /models → {model_id: {in_per_1m, out_per_1m}}.
    id OpenRouter berbentuk 'vendor/model_id' → dipetakan by suffix."""
    out = {}
    try:
        data = requests.get(FALLBACK_URL, timeout=30).json().get("data") or []
        for e in data:
            mid = str(e.get("id") or "").split("/")[-1]
            pr = e.get("pricing") or {}
            pin, pout = float(pr.get("prompt") or 0), float(pr.get("completion") or 0)
            if mid and (pin > 0 or pout > 0):
                out[mid] = {"in_per_1m": round(pin * 1e6, 4), "out_per_1m": round(pout * 1e6, 4)}
    except Exception as e:
        logger.warning(f"[price_sync] fallback OpenRouter gagal: {e}")
    return out


def _to_pricing(e: dict, now: str) -> dict:
    """Normalisasi entri LiteLLM → skema pricing kita. (gpt-image-1 family = PER-TOKEN:
    output pakai output_cost_per_image_token, input pakai input_cost_per_token.)"""
    out_tok = e.get("output_cost_per_token") or e.get("output_cost_per_image_token")
    return {
        "in_per_1m":    round(float(e["input_cost_per_token"]) * 1e6, 4) if e.get("input_cost_per_token") else None,
        "out_per_1m":   round(float(out_tok) * 1e6, 4) if out_tok else None,
        "per_image":    float(e["output_cost_per_image"]) if e.get("output_cost_per_image") else None,
        "per_1m_chars": round(float(e["input_cost_per_character"]) * 1e6, 4) if e.get("input_cost_per_character") else None,
        "source": "litellm", "synced_at": now,
    }


def _sanity_violation(old: dict | None, new: dict) -> str | None:
    """Perubahan drastis (> SANITY_FACTOR× naik/turun) pada field mana pun → alasan (str), aman → None."""
    if not old:
        return None
    for k in ("in_per_1m", "out_per_1m", "per_image", "per_1m_chars"):
        o, n = old.get(k), new.get(k)
        if o and n and float(o) > 0 and float(n) > 0:
            ratio = float(n) / float(o)
            if ratio > SANITY_FACTOR or ratio < 1 / SANITY_FACTOR:
                return f"{k}: {o} → {n} ({ratio:.1f}×)"
    return None


def _notify_admin(text: str) -> None:
    try:
        from src.utils.telegram_notifier import TelegramNotifier
        TelegramNotifier().notify_admin(text)
    except Exception:
        pass


def _check_staleness(sb, rows: list) -> None:
    """Alarm basi: model non-locked ber-synced_at lebih tua dari STALE_DAYS → Telegram admin (1×/hari)."""
    try:
        cutoff = _time.time() - STALE_DAYS * 86400
        stale = []
        for m in rows:
            p = m.get("pricing") or {}
            if m.get("pricing_locked") or not p.get("synced_at"):
                continue
            try:
                ts = datetime.fromisoformat(str(p["synced_at"]).replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if ts < cutoff:
                stale.append(m["model_key"])
        if not stale:
            return
        r = sb.table("app_config").select("value").eq("key", "ai_price_stale_alerted_at").limit(1).execute()
        last = int(r.data[0]["value"]) if r.data else 0
        if _time.time() - last < 86400:
            return
        _notify_admin(f"⚠️ <b>Harga model AI BASI</b> (&gt;{int(STALE_DAYS)} hari tanpa sinkron): "
                      f"<code>{', '.join(stale)}</code>\nSumber feed kemungkinan bermasalah — cek Catalog → AI Models.")
        sb.table("app_config").upsert({"key": "ai_price_stale_alerted_at", "value": int(_time.time()),
                                       "description": "epoch alarm harga-basi terakhir (price_sync)"}).execute()
    except Exception as e:
        logger.debug(f"[price_sync] cek staleness gagal: {e}")


def sync_prices(sb=None, force: bool = False) -> dict:
    """Tarik feed (LiteLLM → fallback OpenRouter utk LLM) → update ai_models.pricing.
    Skip pricing_locked; perubahan drastis → pricing_pending (keputusan admin). Return ringkasan."""
    sb = sb or _sb()

    if not force:
        try:
            r = sb.table("app_config").select("value").eq("key", "ai_price_synced_at").limit(1).execute()
            last = int(r.data[0]["value"]) if r.data else 0
            if last and (_time.time() - last) < SYNC_INTERVAL_HOURS * 3600:
                return {"skipped": True}
        except Exception:
            pass

    rows = sb.table("ai_models").select("model_key, model_id, component, pricing, pricing_locked, pricing_pending").execute().data or []

    feed = None
    try:
        feed = requests.get(FEED_URL, timeout=30).json()
    except Exception as e:
        logger.warning(f"[price_sync] feed utama gagal: {e} — coba fallback OpenRouter (LLM saja)")

    orm = None   # lazy: fallback OpenRouter di-fetch hanya bila dibutuhkan
    now = datetime.now(timezone.utc).isoformat()
    updated, held, missing = 0, [], []

    for m in rows:
        if m.get("pricing_locked"):
            continue
        pricing = None
        e = _feed_entry(feed, m.get("model_id") or m["model_key"]) if feed else None
        if e:
            pricing = _to_pricing(e, now)
            if all(v is None for k, v in pricing.items() if k not in ("source", "synced_at")):
                pricing = None
        if pricing is None and m.get("component") == "llm":
            if orm is None:
                orm = _openrouter_map()
            fo = orm.get(m.get("model_id") or m["model_key"])
            if fo:
                pricing = {**fo, "per_image": None, "per_1m_chars": None, "source": "openrouter", "synced_at": now}
        if pricing is None:
            missing.append(m["model_key"])
            continue

        # SANITY-GUARD: perubahan drastis → tahan di pricing_pending (admin putuskan), JANGAN terapkan.
        reason = _sanity_violation(m.get("pricing"), pricing)
        if reason:
            sb.table("ai_models").update({"pricing_pending": {**pricing, "reason": reason}}).eq("model_key", m["model_key"]).execute()
            held.append(f"{m['model_key']} ({reason})")
            continue
        sb.table("ai_models").update({"pricing": pricing, "pricing_pending": None}).eq("model_key", m["model_key"]).execute()
        updated += 1

    if feed is not None or updated:
        try:
            sb.table("app_config").upsert({"key": "ai_price_synced_at", "value": int(_time.time()),
                                           "description": "epoch detik sinkron harga model AI terakhir (price_sync)"}).execute()
        except Exception:
            pass

    if held:
        _notify_admin("⚠️ <b>Usulan harga model DITAHAN</b> (berubah drastis — konfirmasi di Catalog → AI Models):\n"
                      + "\n".join(f"• <code>{h}</code>" for h in held))
        logger.warning(f"[price_sync] usulan harga DITAHAN (sanity-guard): {held}")
    if missing:
        logger.warning(f"[price_sync] model TANPA harga di semua sumber (isi manual + lock di Catalog): {missing}")
    logger.info(f"[price_sync] tersinkron: {updated} update, {len(held)} ditahan, {len(missing)} tanpa-sumber")

    _check_staleness(sb, rows)
    return {"updated": updated, "held": held, "missing": missing}
