"""
Gerbang aktivasi channel (F1-08 / kredensial per-channel 2026-06-24).

Channel READY (boleh diaktifkan + diproduksi) bila SEMUA lengkap & valid PER-CHANNEL:
  niche · penyedia+model+kunci tiap elemen (LLM/TTS/Visual, provider-aware) · voice · YouTube OAuth.

SUMBER KEBENARAN TUNGGAL = fungsi DB `channel_missing(channels)` (via RPC `channel_missing_by_id`).
Worker, RPC FE, dan trigger DB pakai LOGIKA YANG SAMA PERSIS → akar bug "BE vs DB beda lapisan" hilang.

NO-FALLBACK (§3.8): channel tak lengkap → tak produksi (bukan produksi pakai default diam-diam).
Dipakai producer (skip channel non-ready) — FAIL-OPEN saat cek ERROR transient (lindungi channel sehat).
"""

from loguru import logger


def channel_readiness(sb, ch: dict) -> dict:
    """Return {ready: bool, missing: [str], check_failed: bool}.
    check_failed=True → cek tak tuntas (error transient) → producer FAIL-OPEN (jangan skip channel sehat)."""
    cid = str(ch.get("id") or ch.get("channel_id") or "")
    if not cid:
        return {"ready": False, "missing": ["akses/channel"], "check_failed": True}
    try:
        r = sb.rpc("channel_missing_by_id", {"p_channel_id": cid}).execute()
        missing = list(r.data or [])
        return {"ready": len(missing) == 0, "missing": missing, "check_failed": False}
    except Exception as e:
        logger.warning(f"[Readiness] cek channel {cid} gagal: {e}")
        return {"ready": False, "missing": [], "check_failed": True}
