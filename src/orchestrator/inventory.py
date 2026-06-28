"""
content_inventory CRUD — state buffer decouple producer/publisher (Phase 5.3).

Source-of-truth status video siap-tayang (DESAIN §12c). Producer: record_producing →
mark_ready (+ s3_key). Publisher: claim_oldest_ready (ready→publishing, anti-rebut) →
mark_published (+ hapus S3) / revert_to_ready (gagal). Pakai Supabase REST service_role
(RLS content_inventory). Multi-node klaim presisi (SKIP LOCKED) = refinement via RPC nanti.
"""

import os
from datetime import datetime, timedelta, timezone
from loguru import logger


def _default_expiry_iso() -> str:
    """TTL buffer 'ready' (config-driven BUFFER_TTL_HOURS, default 72j=3hr). PENJAGA KESEGARAN:
    konten lolos QC yang tak ter-publish dalam 72j → disapu janitor (jangan publish basi/tren lewat).
    Diperpendek 168→72 (2026-06-28): operasi normal tayang ~1 hari (FIFO + buffer dangkal); TTL = jaring
    pengaman agar TAKKAN publish konten basi >3 hari. Override per-kebutuhan via env BUFFER_TTL_HOURS."""
    hours = float(os.getenv("BUFFER_TTL_HOURS", "72"))
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _expiry_iso(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


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
    # produced_at = waktu produksi selesai (app-side ISO; "now()" string tak jalan via REST).
    # FIX 2026-06-28: dulu di-pop TANPA pengganti → produced_at selalu NULL → claim_oldest_ready acak.
    upd = {"status": "ready", "s3_key": s3_key, "produced_at": datetime.now(timezone.utc).isoformat()}
    if target_slot is not None:
        upd["target_slot"] = target_slot
    upd["expires_at"] = expires_at if expires_at is not None else _default_expiry_iso()
    if metadata is not None:
        upd["metadata"] = metadata
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
    # FIFO sungguhan: created_at SELALU terisi (produced_at bisa NULL utk baris lama pra-fix 2026-06-28).
    # Sebelumnya order by target_slot+produced_at (keduanya NULL utk item ready) → urutan ACAK → konten
    # lama (tren basi) terlewat. created_at = umur sebenarnya → tertua tayang lebih dulu.
    res = sb.table("content_inventory").select("*").eq("channel_id", channel_id).eq(
        "status", "ready").order("created_at", desc=False).limit(1).execute()
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
    """Hard-fail (crash, TANPA video) → status failed. Set expires_at (TTL) agar janitor menyapu
    (fix bug lama: failed ber-expires_at NULL tak pernah disapu = baris menumpuk). Config FAILED_TTL_HOURS."""
    _sb().table("content_inventory").update({
        "status": "failed",
        "metadata": {"error": reason[:300]},
        "expires_at": _expiry_iso(float(os.getenv("FAILED_TTL_HOURS", "24"))),
    }).eq("id", inv_id).execute()


def mark_ready_with_issues(inv_id: int, s3_key: str, reason: str = "",
                           recommendation: str = "", metadata: dict | None = None) -> None:
    """OPSI C: QC-fail TAPI video JADI → STOK untuk DITINJAU tenant (bukan dibuang, bukan auto-upload
    YouTube). Dihitung sebagai stok (rem alami). TTL ISSUE_REVIEW_TTL_HOURS → janitor auto-buang bila
    tak ditinjau. Aset video tetap di S3; tenant tinjau dari dashboard, approve→publish / buang."""
    md = dict(metadata or {})
    md["qc_reason"] = reason
    if recommendation:
        md["recommendation"] = recommendation
    _sb().table("content_inventory").update({
        "status": "ready_with_issues",
        "s3_key": s3_key,
        "metadata": md,
        "expires_at": _expiry_iso(float(os.getenv("ISSUE_REVIEW_TTL_HOURS", "72"))),
    }).eq("id", inv_id).execute()


def recent_nonready_streak(channel_id: str, limit: int = 12) -> int:
    """Hitung kegagalan BERUNTUN terbaru (failed + ready_with_issues) untuk channel — basis
    circuit-breaker §4b/F7. Streak putus saat ketemu 'ready'/'published'. Hanya baca (read-only)."""
    res = (_sb().table("content_inventory").select("status")
           .eq("channel_id", channel_id)
           .order("created_at", desc=True).limit(limit).execute())
    streak = 0
    for row in (res.data or []):
        if row["status"] in ("failed", "ready_with_issues"):
            streak += 1
        else:
            break
    return streak


def revert_to_ready(inv_id: int) -> None:
    """Publish gagal → kembalikan ke buffer untuk retry (jangan hapus aset)."""
    _sb().table("content_inventory").update({"status": "ready"}).eq("id", inv_id).execute()
