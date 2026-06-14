"""
Publisher — ambil video ready dari buffer → publish saat SLOT (Phase 5.3, DESAIN §12c).

RINGAN (~5 dtk upload, no CPU). Slot **timezone-aware tenant** → ini sekaligus **FIX Bug 1**
(dispatcher lama treat publish_slots sebagai UTC). Loop tiap 30s. Buffer kosong saat slot →
skip + Telegram (no silent degradation). Publish gagal → revert ke ready + retry.
"""

import os
import time
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger

from src.orchestrator import inventory
from src.utils import s3_buffer


def slot_due(publish_slots: list, tz_name: str, now_utc: datetime, window_sec: int = 90):
    """Return datetime slot (tz tenant) yang JATUH TEMPO sekarang, atau None.
    FIX Bug 1: bandingkan jam slot di TIMEZONE TENANT, bukan UTC."""
    if not publish_slots:
        return None
    try:
        tz = ZoneInfo(tz_name or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    now_local = now_utc.astimezone(tz)
    for s in publish_slots:
        try:
            hh, mm = [int(x) for x in str(s).split(":")[:2]]
        except Exception:
            continue
        slot_dt = now_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        # jatuh tempo bila now dalam [slot, slot+window]
        if timedelta(0) <= (now_local - slot_dt) <= timedelta(seconds=window_sec):
            return slot_dt
    return None


def _already_handled(sb, channel_id: str, slot_dt: datetime) -> bool:
    """Dedup: sudah ada item publishing/published utk slot ini (cegah dobel antar-cycle)."""
    lo = (slot_dt - timedelta(minutes=3)).isoformat()
    hi = (slot_dt + timedelta(minutes=5)).isoformat()
    res = (sb.table("content_inventory").select("id", count="exact")
           .eq("channel_id", channel_id).in_("status", ["publishing", "published"])
           .gte("target_slot", lo).lte("target_slot", hi).execute())
    return (res.count or 0) > 0


def _tenant_timezone(sb, tenant_id: str) -> str:
    try:
        r = sb.table("tenant_configs").select("timezone").eq("tenant_id", tenant_id).limit(1).execute()
        return (r.data[0].get("timezone") if r.data else None) or "UTC"
    except Exception:
        return "UTC"


def publish_due_for_channel(sb, channel_row: dict, now_utc: datetime | None = None) -> str | None:
    """Cek slot channel; bila jatuh tempo → ambil ready → publish dari buffer. Return status."""
    now_utc = now_utc or datetime.now(ZoneInfo("UTC"))
    tenant_id  = channel_row["tenant_id"]
    channel_id = str(channel_row.get("id") or "default")
    tz = _tenant_timezone(sb, tenant_id)
    slot_dt = slot_due(channel_row.get("publish_slots") or [], tz, now_utc)
    if slot_dt is None:
        return None
    if _already_handled(sb, channel_id, slot_dt):
        return "already_handled"

    item = inventory.claim_oldest_ready(channel_id)
    if not item:
        logger.warning(f"[Publisher] Buffer KOSONG slot {slot_dt} ch={channel_id} — skip + Telegram")
        _notify(tenant_id, f"⚠️ Buffer kosong, slot {slot_dt:%H:%M} dilewati (channel {channel_id})")
        return "buffer_empty"

    # tandai target_slot (dedup) + publish dari buffer
    sb.table("content_inventory").update({"target_slot": slot_dt.isoformat()}).eq("id", item["id"]).execute()
    try:
        _publish_from_buffer(sb, channel_row, item)
        inventory.mark_published(item["id"])
        # Buang SEMUA aset buffer (video + thumbnail) — cegah .jpg/.mp4 orphan menumpuk.
        for k in (item.get("s3_key"), (item.get("metadata") or {}).get("thumb_s3")):
            if k:
                s3_buffer.delete(k)
        logger.info(f"[Publisher] published ch={channel_id} inv={item['id']} (buffer dibersihkan)")
        return "published"
    except Exception as e:
        inventory.revert_to_ready(item["id"])           # kembalikan ke buffer utk retry
        logger.error(f"[Publisher] publish gagal inv={item['id']} ({e}) — revert ready")
        _notify(tenant_id, f"❌ Publish gagal (channel {channel_id}), akan diulang: {e}")
        return "failed"


def _publish_from_buffer(sb, channel_row: dict, item: dict) -> None:
    """Download video+thumbnail dari S3 → publish via youtube_publisher (reuse). Raise bila gagal."""
    from src.intelligence.config import tenant_config_from_channel
    from src.distribution.youtube_publisher import YouTubePublisher

    meta = item.get("metadata") or {}
    script = meta.get("script") or {}
    tc = tenant_config_from_channel(channel_row, niche=item.get("niche") or channel_row.get("niche"))

    tmp = tempfile.mkdtemp()
    video_path = os.path.join(tmp, "video.mp4")
    s3_buffer.download(item["s3_key"], video_path)
    thumb_path = ""
    if meta.get("thumb_s3"):
        thumb_path = os.path.join(tmp, "thumb.jpg")
        s3_buffer.download(meta["thumb_s3"], thumb_path)

    yt = YouTubePublisher().publish(video_path, script, tc,
                                    thumbnail_path=thumb_path, content_type="short")
    if not yt.get("video_id"):
        raise RuntimeError(yt.get("error", "YouTube publish gagal"))
    _notify(channel_row["tenant_id"], f"✅ Published: {yt.get('url')}")


def _notify(tenant_id: str, msg: str) -> None:
    # Log dulu; wiring ke TelegramNotifier (pesan generik per-event) = refinement saat cutover.
    logger.info(f"[Publisher][{tenant_id}] {msg}")


def run_forever(idle_seconds: int = 30) -> None:
    """Loop persisten Publisher (§12c) — cek slot tiap 30s (granularity menit)."""
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    logger.info("[Publisher] start | cek slot tiap 30s (timezone-aware)")
    while True:
        try:
            channels = sb.table("channels").select("*").eq("is_active", True).execute().data or []
            for ch in channels:
                publish_due_for_channel(sb, ch)
        except Exception as e:
            logger.error(f"[Publisher] loop error: {e}")
        time.sleep(idle_seconds)
