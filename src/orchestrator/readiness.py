"""
F1-08 (REMEDIASI §10.E.7): Gerbang aktivasi channel.

Channel READY (boleh diaktifkan + diproduksi) bila SEMUA lengkap & valid:
  niche · model tiap elemen (LLM/TTS/visual) · voice (resolvable) · credential per provider · YouTube OAuth.

Dipakai:
  - Producer (skip channel non-ready) — FAIL-OPEN pada error-cek (lindungi channel sehat dari error transient).
  - FE (checklist sisa + tombol Aktifkan) via RPC nanti (FASE 2).

NO-FALLBACK selaras §3.8: channel tak lengkap → tak produksi (bukan produksi pakai default diam-diam).
"""

from loguru import logger


def _youtube_connected(sb, ch: dict) -> bool:
    """True bila ada refresh token YouTube untuk channel (channel_credentials) atau tenant (fallback legacy)."""
    cid = str(ch.get("id") or "")
    tid = ch.get("tenant_id")
    r = sb.table("channel_credentials").select("google_refresh_token_enc").eq("channel_id", cid).limit(1).execute()
    if r.data and r.data[0].get("google_refresh_token_enc"):
        return True
    r2 = sb.table("tenant_credentials").select("google_refresh_token_enc").eq("tenant_id", tid).limit(1).execute()
    return bool(r2.data and r2.data[0].get("google_refresh_token_enc"))


def channel_readiness(sb, ch: dict) -> dict:
    """Return {ready: bool, missing: [str], check_failed: bool}.
    check_failed=True → cek tak tuntas (error transient) → producer FAIL-OPEN (jangan skip channel sehat)."""
    missing: list[str] = []
    check_failed = False

    niche = ch.get("niche")
    if not niche:
        missing.append("niche")
    if not ch.get("llm_model"):
        missing.append("model LLM")
    if not ch.get("tts_provider"):
        missing.append("model/voice TTS")
    vm = ch.get("visual_mode") or ""
    if not vm:
        missing.append("mode visual")

    # Voice (PER-CHANNEL, §10.B FINAL owner 2026-06-23): channels.voice_key WAJIB
    # (voice = channel, 1/channel; NO fallback ke niche — niche provider-agnostik).
    if not ch.get("voice_key"):
        missing.append("voice")

    # Credential per provider (key = per-tenant).
    try:
        from src.config.tenant_config import load_tenant_config
        rc = load_tenant_config(ch["tenant_id"])
        if not (rc.llm_api_key or "").strip():
            missing.append("API key LLM")
        if ch.get("tts_provider") in ("elevenlabs", "openai_tts") and not (rc.tts_api_key or "").strip():
            missing.append("API key TTS")
        if (vm.startswith("ai_image:") or vm.startswith("ai_video:")) and not (rc.visual_api_key or "").strip():
            missing.append("API key visual")
    except Exception as e:
        logger.warning(f"[Readiness] cek credential gagal: {e}")
        check_failed = True

    # YouTube OAuth.
    try:
        if not _youtube_connected(sb, ch):
            missing.append("koneksi YouTube")
    except Exception as e:
        logger.warning(f"[Readiness] cek YouTube OAuth gagal: {e}")
        check_failed = True

    return {"ready": (len(missing) == 0 and not check_failed), "missing": missing, "check_failed": check_failed}
