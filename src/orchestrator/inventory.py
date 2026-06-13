"""
content_inventory CRUD — state buffer decouple producer/publisher (Phase 5.3).

Source-of-truth status video siap-tayang (DESAIN §12c). Producer: record_producing →
mark_ready (+ s3_key). Publisher: claim_oldest_ready (ready→publishing, anti-rebut) →
mark_published (+ hapus S3) / revert_to_ready (gagal). Pakai Supabase REST service_role
(RLS content_inventory). Multi-node klaim presisi (SKIP LOCKED) = refinement via RPC nanti.
"""

import os
from loguru import logger


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def record_producing(tenant_id: str, channel_id: str | None, niche: str | None,
                     metadata: dict | None = None) -> int | None:
    """Catat 1 item mulai diproduksi (status=producing). Return id."""
    row = {"tenant_id": tenant_id, "channel_id": channel_id, "niche": niche,
           "status": "producing", "metadata": metadata or {}}
    res = _sb().table("content_inventory").insert(row).execute()
    return res.data[0]["id"] if res.data else None


def mark_ready(inv_id: int, s3_key: str, target_slot=None, expires_at=None,
               metadata: dict | None = None) -> None:
    """Video selesai + ter-upload ke buffer → siap-tayang."""
    upd = {"status": "ready", "s3_key": s3_key, "produced_at": "now()"}
    if target_slot is not None:
        upd["target_slot"] = target_slot
    if expires_at is not None:
        upd["expires_at"] = expires_at
    if metadata is not None:
        upd["metadata"] = metadata
    # produced_at = now() via DB default tak bisa lewat REST string → pakai timestamp app-side
    upd.pop("produced_at", None)
    _sb().table("content_inventory").update(upd).eq("id", inv_id).execute()


def buffer_depth(channel_id: str, status: str = "ready") -> int:
    """Jumlah item pada status tertentu untuk channel (cek defisit buffer)."""
    res = _sb().table("content_inventory").select("id", count="exact").eq(
        "channel_id", channel_id).eq("status", status).execute()
    return res.count or 0


def claim_oldest_ready(channel_id: str) -> dict | None:
    """Ambil item ready tertua untuk channel → set status=publishing (anti-rebut via
    guard status). Return row atau None bila buffer kosong."""
    sb = _sb()
    res = sb.table("content_inventory").select("*").eq("channel_id", channel_id).eq(
        "status", "ready").order("target_slot", desc=False).order("produced_at", desc=False).limit(1).execute()
    if not res.data:
        return None
    row = res.data[0]
    # guard: hanya klaim bila masih 'ready' (cegah dobel antar-publisher)
    upd = sb.table("content_inventory").update({"status": "publishing"}).eq(
        "id", row["id"]).eq("status", "ready").execute()
    if not upd.data:
        return None  # keburu diklaim publisher lain
    return {**row, "status": "publishing"}


def mark_published(inv_id: int, metadata: dict | None = None) -> None:
    upd = {"status": "published"}
    if metadata is not None:
        upd["metadata"] = metadata
    _sb().table("content_inventory").update(upd).eq("id", inv_id).execute()


def mark_failed(inv_id: int, reason: str = "") -> None:
    _sb().table("content_inventory").update(
        {"status": "failed", "metadata": {"error": reason[:300]}}).eq("id", inv_id).execute()


def revert_to_ready(inv_id: int) -> None:
    """Publish gagal → kembalikan ke buffer untuk retry (jangan hapus aset)."""
    _sb().table("content_inventory").update({"status": "ready"}).eq("id", inv_id).execute()
