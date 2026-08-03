"""
content_inventory CRUD — state buffer decouple producer/publisher (Phase 5.3).

Source-of-truth status video siap-tayang (DESAIN §12c). Producer: record_producing →
mark_ready (+ s3_key). Publisher: claim_oldest_ready (ready→publishing, anti-rebut) →
mark_published (+ hapus S3) / revert_to_ready (gagal). Pakai Supabase REST service_role
(RLS content_inventory). Multi-node klaim presisi (SKIP LOCKED) = refinement via RPC nanti.
"""

import os
from datetime import datetime, timedelta, timezone


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


def mark_test(inv_id: int, s3_key: str, qc_passed: bool = True, reason: str = "",
              metadata: dict | None = None) -> None:
    """Video TEST tanpa-publish (NICHE_DNA F5, owner 2026-07-04): status='test' — TIDAK PERNAH diklaim
    publisher (claim hanya 'ready') dan TIDAK mengotori antrean /review. TTL default buffer → janitor
    menyapu baris + aset S3 (±3 hari). Ditonton dari drawer niche (admin/Studio) via presigned URL."""
    md = dict(metadata or {})
    md["test"] = True
    md["qc_passed"] = qc_passed
    if reason:
        md["qc_reason"] = reason
    _sb().table("content_inventory").update({
        "status": "test", "s3_key": s3_key,
        "produced_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": _default_expiry_iso(),
        "metadata": md,
    }).eq("id", inv_id).execute()


def mark_failed(inv_id: int, reason: str = "") -> None:
    """Hard-fail (crash, TANPA video) → status failed. Set expires_at (TTL) agar janitor menyapu
    (fix bug lama: failed ber-expires_at NULL tak pernah disapu = baris menumpuk). Config FAILED_TTL_HOURS."""
    _sb().table("content_inventory").update({
        "status": "failed",
        "metadata": {"error": reason[:300]},
        "expires_at": _expiry_iso(float(os.getenv("FAILED_TTL_HOURS", "24"))),
    }).eq("id", inv_id).execute()


def mark_ready_with_issues(inv_id: int, s3_key: str, reason: str = "",
                           recommendation: str = "", metadata: dict | None = None,
                           reason_code: str | None = None,
                           reason_params: dict | None = None) -> None:
    """OPSI C: QC-fail TAPI video JADI → STOK untuk DITINJAU tenant (bukan dibuang, bukan auto-upload
    YouTube). Dihitung sebagai stok (rem alami). TTL ISSUE_REVIEW_TTL_HOURS → janitor auto-buang bila
    tak ditinjau. Aset video tetap di S3; tenant tinjau dari dashboard, approve→publish / buang."""
    md = dict(metadata or {})
    md["qc_reason"] = reason
    # KODE + PARAMETER agar layar tenant bisa menampilkan alasan DWIBAHASA (§3.5). Teks `qc_reason`
    # tetap ditulis sebagai cadangan → baris lama & kode lama berperilaku persis sama (nol regresi).
    if reason_code:
        md["qc_reason_code"] = reason_code
        md["qc_reason_params"] = reason_params or {}
    if recommendation:
        md["recommendation"] = recommendation
    _sb().table("content_inventory").update({
        "status": "ready_with_issues",
        "s3_key": s3_key,
        "metadata": md,
        "expires_at": _expiry_iso(float(os.getenv("ISSUE_REVIEW_TTL_HOURS", "72"))),
    }).eq("id", inv_id).execute()


def recent_nonready_streak(channel_id: str, limit: int = 12, sejak: str | None = None) -> int:
    """Hitung kegagalan BERUNTUN terbaru untuk channel — basis circuit-breaker §4b/F7.
    Sumber = production_runs (buku besar SEMUA run: buffer + direct/"Jalankan Ulang" + test).
    Dulu membaca content_inventory (jalur buffer SAJA) → run direct sukses tidak memutus
    streak: channel di-pause ULANG tiap siklus producer + alarm 🛑 palsu berulang, padahal
    video barusan terbit (insiden live 2026-07-08, channel ke-2 ryan).
    failed/qc_failed = gagal; success = streak putus; lainnya (discarded) netral.

    `sejak` (migr 0197) = `channels.production_resumed_at`. Kegagalan SEBELUM titik pemulihan
    TIDAK dihitung. Tanpa ini, melepas rem tak ada gunanya: kegagalan hari sebelumnya masih
    terhitung, siklus penjadwal berikutnya membaca streak lama dan langsung mengerem lagi —
    tenant melihat channelnya "dipulihkan lalu mati lagi" berulang-ulang (dilaporkan owner
    2026-08-03 pada BISIK NUSANTARA; log membuktikan rem menyala 2× tanpa SATU PUN percobaan
    produksi baru). Pola identik dengan insiden 8-Jul di atas — sebab berbeda, akibat sama.
    """
    q = (_sb().table("production_runs").select("status")
         .eq("channel_id", channel_id))
    if sejak:
        q = q.gt("created_at", sejak)
    res = q.order("created_at", desc=True).limit(limit).execute()
    streak = 0
    for row in (res.data or []):
        st = row["status"]
        if st in ("failed", "qc_failed"):
            streak += 1
        elif st == "success":
            break
    return streak


def latest_failure(channel_id: str, sejak: str | None = None) -> dict | None:
    """[ERROR-MGMT] {error_class, error_message} run TERBARU channel BILA run itu gagal (failed/
    qc_failed). Sumber = production_runs (SAMA dgn recent_nonready_streak → konsisten). Dipakai
    circuit-breaker untuk REM SEGERA pada error non-retryable (billing/kuota) + pesan manusiawi.
    Return None bila run terbaru sukses/kosong → jatuh ke jalur streak biasa (aman).

    `sejak` (migr 0197) WAJIB sama dengan yang dipakai `recent_nonready_streak` — keduanya membaca
    periode yang sama. Bila tidak, rem-cepat bisa menghukum berdasarkan kegagalan dari periode yang
    sudah ditutup pemulihan, sementara hitungan streak sudah memaafkannya: dua pengambil keputusan
    membaca dunia yang berbeda.
    """
    q = (_sb().table("production_runs").select("status,error_class,error_message")
         .eq("channel_id", channel_id))
    if sejak:
        q = q.gt("created_at", sejak)
    res = q.order("created_at", desc=True).limit(1).execute()
    row = (res.data or [None])[0]
    if not row or row.get("status") not in ("failed", "qc_failed"):
        return None
    return {"error_class": row.get("error_class"), "error_message": row.get("error_message")}


def revert_to_ready(inv_id: int) -> None:
    """Publish gagal → kembalikan ke buffer untuk retry (jangan hapus aset)."""
    _sb().table("content_inventory").update({"status": "ready"}).eq("id", inv_id).execute()
