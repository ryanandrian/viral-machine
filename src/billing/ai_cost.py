"""
AI Cost (B2 BYOK cost-tracking, owner 2026-07-04) — konversi KONSUMSI (cost_meter) → USD.

Harga satuan = katalog `ai_models.pricing` (jsonb):
  {in_per_1m, out_per_1m, per_image, per_1m_chars, per_request_usd, source, synced_at}
  video ([B6] F2): {per_second_usd} ATAU {per_video_base_usd, base_seconds, per_extra_second_usd}
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
    br = {"llm": 0.0, "image": 0.0, "tts": 0.0, "video": 0.0}
    synced = None

    for model, u in (ai_usage.get("llm") or {}).items():
        p = prices.get(model)
        if not p:
            unpriced.append(model)
            continue
        # Tarif PER PERMINTAAN (mis. fal any-llm: $0,001 sekali panggil, berapa pun panjangnya).
        # Dicek DULU: model semacam ini tak punya harga per-token sama sekali, dan tanpa cabang ini
        # ia akan masuk daftar "tanpa harga" — biaya nyata tenant jadi tak terlihat.
        if p.get("per_request_usd") is not None:
            br["llm"] += float(u.get("calls", 0) or 0) * float(p["per_request_usd"])
            synced = synced or p.get("synced_at")
            continue
        if p.get("in_per_1m") is None and p.get("out_per_1m") is None:
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

    # SUARA — DUA satuan. Per-huruf (ElevenLabs, OpenAI tts-1) ATAU per-token (Gemini TTS: vendor
    # menagih token audio dan mengirim hitungannya sendiri di balasan; dicatat meter di `tts_tokens`).
    # Urutannya menentukan: per-huruf DULU, jadi model yang punya harga huruf TAK MUNGKIN terhitung
    # dua kali walau tokennya juga tercatat. Nol dari keduanya → JUJUR masuk daftar tanpa-harga
    # (haram menaksir token dari jumlah huruf — itu mengarang angka).
    _tts_tok = ai_usage.get("tts_tokens") or {}
    for model, chars in (ai_usage.get("tts") or {}).items():
        p = prices.get(model)
        if p and p.get("per_1m_chars") is not None:
            br["tts"] += (chars / 1e6) * float(p.get("per_1m_chars") or 0)
            synced = synced or p.get("synced_at")
            continue
        tok = _tts_tok.get(model) or {}
        if p and (tok.get("tokens_in") or tok.get("tokens_out")) and (
                p.get("in_per_1m") is not None or p.get("out_per_1m") is not None):
            br["tts"] += (float(tok.get("tokens_in", 0) or 0) / 1e6) * float(p.get("in_per_1m") or 0) \
                       + (float(tok.get("tokens_out", 0) or 0) / 1e6) * float(p.get("out_per_1m") or 0)
            synced = synced or p.get("synced_at")
            continue
        unpriced.append(model)

    # [B6] F2 — video-gen: per-detik ATAU basis-per-klip + detik-tambahan (mis. Kling $0.35/5s + $0.07/s).
    for model, u in (ai_usage.get("video") or {}).items():
        p = prices.get(model)
        secs  = float((u or {}).get("seconds", 0) or 0)
        clips = int((u or {}).get("clips", 0) or 0)
        if p and p.get("per_second_usd") is not None:
            br["video"] += secs * float(p["per_second_usd"])
        elif p and p.get("per_video_base_usd") is not None:
            base   = float(p["per_video_base_usd"])
            base_s = float(p.get("base_seconds") or 0)
            extra  = float(p.get("per_extra_second_usd") or 0)
            br["video"] += clips * base + max(0.0, secs - clips * base_s) * extra
        else:
            unpriced.append(model)
            continue
        synced = synced or p.get("synced_at")

    total = br["llm"] + br["image"] + br["tts"] + br["video"]
    return {
        "usd": round(total, 6),
        "breakdown": {k: round(v, 6) for k, v in br.items()},
        "unpriced": sorted(set(unpriced)),
        "priced_at": synced,
    }
