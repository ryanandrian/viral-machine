"""
Buffer Janitor — jaga buffer S3 (Biznet) BERSIH, cegah sampah menumpuk (Phase 5.3).

Dua tugas (idempotent, aman dijalankan berkala):
  1. sweep_stale       : item content_inventory ABANDONED → hapus aset S3 + baris.
       • ready/failed yang lewat `expires_at`
       • producing yang NYANGKUT (created_at > PRODUCING_TTL_HOURS — render crash)
  2. reconcile_orphans : objek S3 yang TIDAK direferensikan baris inventory aktif
       (ready/producing/publishing) DAN lebih tua dari grace → hapus.

Grace period (ORPHAN_GRACE_MINUTES) mencegah penghapusan upload IN-FLIGHT
(producer upload → mark_ready ada jeda detik). Config-driven, no-hardcode.
Dipanggil worker_decoupled via thread `run_forever`.
"""

import os
import time
from datetime import datetime, timedelta, timezone

from loguru import logger

from src.utils import s3_buffer


def _sb():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def _parse(ts) -> datetime | None:
    """ISO timestamp (Supabase / boto3) → datetime tz-aware UTC."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _keys_of(row: dict) -> list:
    """Semua key S3 milik 1 baris inventory (video + thumbnail)."""
    keys = [row.get("s3_key"), (row.get("metadata") or {}).get("thumb_s3")]
    return [k for k in keys if k]


def sweep_stale(sb=None) -> dict:
    sb = sb or _sb()
    now = datetime.now(timezone.utc)
    producing_cutoff = now - timedelta(hours=float(os.getenv("PRODUCING_TTL_HOURS", "3")))

    rows = sb.table("content_inventory").select("*").in_(
        "status", ["ready", "ready_with_issues", "failed", "test"]).execute().data or []   # 'test' = video uji (TTL ±3 hari)
    stale = [r for r in rows if (_parse(r.get("expires_at")) or now + timedelta(days=3650)) < now]

    prod = sb.table("content_inventory").select("*").eq("status", "producing").execute().data or []
    stuck = [r for r in prod if (_parse(r.get("created_at")) or now) < producing_cutoff]

    deleted_assets = purged_rows = 0
    for r in stale + stuck:
        for k in _keys_of(r):
            s3_buffer.delete(k); deleted_assets += 1
        sb.table("content_inventory").delete().eq("id", r["id"]).execute()
        purged_rows += 1
        # TUTUP LOOP sinyal (owner 2026-07-10; simetris `discard_inventory_item`): item ready_with_issues
        # yang kedaluwarsa TTL = auto-dibuang → run asalnya WAJIB ikut padam (qc_failed → 'discarded'),
        # kalau tidak: angka "perlu ditinjau" (dashboard/Runs) menghitungnya SELAMANYA padahal
        # tak ada lagi yang bisa ditinjau. Fail-soft (jangan gagalkan sweep karena update ledger).
        if r.get("status") == "ready_with_issues":
            _rid = (r.get("metadata") or {}).get("run_id")
            if _rid:
                try:
                    sb.table("production_runs").update({"status": "discarded"}) \
                      .eq("run_id", _rid).eq("status", "qc_failed").execute()
                except Exception as e:
                    logger.warning(f"[janitor] padamkan sinyal run {_rid} gagal — non-fatal: {e}")
    if purged_rows:
        logger.info(f"[janitor] sweep_stale: {purged_rows} baris abandoned + {deleted_assets} aset S3 dihapus")
    return {"purged_rows": purged_rows, "deleted_assets": deleted_assets}


def reconcile_orphans(sb=None, grace_minutes=None) -> dict:
    sb = sb or _sb()
    grace = float(grace_minutes if grace_minutes is not None else os.getenv("ORPHAN_GRACE_MINUTES", "60"))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=grace)

    rows = sb.table("content_inventory").select("s3_key,metadata,status").in_(
        "status", ["ready", "ready_with_issues", "producing", "publishing", "test"]).execute().data or []   # 'test' dilindungi s/d TTL
    referenced = set()
    for r in rows:
        referenced.update(_keys_of(r))

    deleted = 0
    for key, _size, lm in s3_buffer.list_keys():
        if key in referenced:
            continue
        lm = _parse(lm)
        if lm and lm > cutoff:        # in-flight → lindungi (grace)
            continue
        s3_buffer.delete(key); deleted += 1
    if deleted:
        logger.info(f"[janitor] reconcile_orphans: {deleted} objek S3 yatim dihapus (grace={grace}m)")
    return {"deleted_orphans": deleted}


def prune_logs(sb) -> dict:
    """Retensi pipeline_run_logs — hapus log lebih tua dari LOG_RETENTION_DAYS (default 30 hari) →
    cegah tabel bloat. Live-tail (D5) hanya butuh log run baru; histori lama tak bernilai.
    Idempotent, best-effort (gagal tak ganggu janitor). Global (lintas-tenant, service_role)."""
    days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        res = sb.table("pipeline_run_logs").delete().lt("created_at", cutoff).execute()
        n = len(res.data or [])
        if n:
            logger.info(f"[janitor] prune_logs: {n} baris pipeline_run_logs >{days}hari dihapus")
        return {"logs_pruned": n}
    except Exception as e:
        logger.warning(f"[janitor] prune_logs gagal: {e}")
        return {"logs_pruned": 0}


def reap_stuck_direct_jobs(sb=None) -> dict:
    """Job direct 'producing' yang melewati batas-waktu (worker mati/hang saat run) → tandai 'failed'
    + alasan, supaya FE (TestNichePanel) lapor gagal bukan menggantung, dan tenant bisa uji ulang.
    TTL via env DIRECT_JOB_TTL_MINUTES (default 30; uji normal ~2-5 mnt). Konsisten pola janitor lain."""
    sb = sb or _sb()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=float(os.getenv("DIRECT_JOB_TTL_MINUTES", "30")))
    rows = sb.table("direct_jobs").select("id, started_at, created_at").eq("status", "producing").execute().data or []
    stuck = [r for r in rows if (_parse(r.get("started_at")) or _parse(r.get("created_at")) or now) < cutoff]
    for r in stuck:
        sb.table("direct_jobs").update({
            "status": "failed",
            "error": "Uji melewati batas waktu (proses macet). Silakan coba lagi.",
            "completed_at": now.isoformat(),
        }).eq("id", r["id"]).execute()
    if stuck:
        logger.info(f"[janitor] reap_stuck_direct_jobs: {len(stuck)} job direct macet → failed")
    return {"direct_reaped": len(stuck)}


def run_once(sb=None) -> dict:
    sb = sb or _sb()
    # B2: sinkron harian harga model AI (feed komunitas → ai_models.pricing; guard internal 24h). Fail-soft.
    try:
        from src.billing.price_sync import sync_prices
        sync_prices(sb)
    except Exception as e:
        logger.warning(f"[janitor] price_sync gagal (non-fatal): {e}")
    # Kurs USD→IDR harian (tampilan biaya BYOK; hormati usd_idr_rate_locked). Fail-soft.
    try:
        from src.billing.price_sync import sync_fx_rate
        sync_fx_rate(sb)
    except Exception as e:
        logger.warning(f"[janitor] sync kurs gagal (non-fatal): {e}")
    return {**sweep_stale(sb), **reconcile_orphans(sb), **reap_stuck_direct_jobs(sb), **prune_logs(sb)}


# ── ALARM PENYIMPANAN (P3 pasca-insiden S3 2026-07-13: NEO tersuspend 04:24, janitor gagal 12×
#    TANPA satu alarm pun — melanggar "gagal = beri tahu, bukan senyap"). Streak error storage
#    beruntun ≥ ambang → Telegram ADMIN (1× per cooldown, penanda system_state — tahan restart);
#    pulih → kabar pulih 1×. Knob infra via env (pola price_sync). ─────────────────────────────
_S3_ALARM_STREAK   = int(os.getenv("S3_ALARM_FAIL_STREAK", "2"))
_S3_ALARM_COOLDOWN = float(os.getenv("S3_ALARM_COOLDOWN_HOURS", "6")) * 3600
_s3_fail_streak = 0


def _state_epoch_get(sb, key: str) -> int:
    """Penanda epoch di system_state (pola price_sync — status mesin, BUKAN config admin)."""
    try:
        r = sb.table("system_state").select("value").eq("key", key).limit(1).execute()
        return int(r.data[0]["value"]) if r.data else 0
    except Exception:
        return 0


def _state_epoch_set(sb, key: str) -> None:
    try:
        sb.table("system_state").upsert({"key": key, "value": str(int(time.time())),
                                         "updated_at": datetime.now(timezone.utc).isoformat()}).execute()
    except Exception as e:
        logger.debug(f"[janitor] tulis system_state {key} gagal: {e}")


def _on_loop_error(sb, e: Exception) -> None:
    """Klasifikasi error storage (botocore) → naikkan streak → alarm admin ber-cooldown."""
    global _s3_fail_streak
    try:
        from botocore.exceptions import BotoCoreError, ClientError
        if not isinstance(e, (BotoCoreError, ClientError)):
            return
        _s3_fail_streak += 1
        if _s3_fail_streak < _S3_ALARM_STREAK:
            return
        if time.time() - _state_epoch_get(sb, "s3_failure_alerted_at") < _S3_ALARM_COOLDOWN:
            return
        from src.utils.telegram_notifier import TelegramNotifier
        TelegramNotifier().notify_admin(
            f"🛑 <b>Penyimpanan S3/NEO BERMASALAH</b> ({_s3_fail_streak}× gagal beruntun)\n"
            # [2026-08-12] DIBERSIHKAN + tak lagi dipotong senyap. Balasan galat S3 berbentuk XML
            # (`<Error><Code>…`); tanpa dibersihkan, Telegram MENOLAK seluruh pesan dan owner tidak
            # menerima apa pun — justru pada alarm paling penting (semua channel berhenti).
            f"💥 <code>{TelegramNotifier.aman(e)}</code>\n"
            f"⚠️ Produksi & publish SEMUA channel akan gagal sampai pulih — cek akun/endpoint NEO BiznetGio.")
        _state_epoch_set(sb, "s3_failure_alerted_at")
    except Exception as _ae:
        logger.debug(f"[janitor] alarm storage gagal (non-fatal): {_ae}")


def _on_loop_success(sb) -> None:
    """Streak sempat ≥ ambang lalu sukses → kabar PULIH sekali (streak reset by construction)."""
    global _s3_fail_streak
    if _s3_fail_streak >= _S3_ALARM_STREAK:
        try:
            from src.utils.telegram_notifier import TelegramNotifier
            TelegramNotifier().notify_admin("✅ <b>Penyimpanan S3/NEO PULIH</b> — janitor kembali normal; "
                                            "video tertunda akan diproses di slot berikutnya.")
        except Exception as _ae:
            logger.debug(f"[janitor] kabar pulih gagal (non-fatal): {_ae}")
    _s3_fail_streak = 0


def run_forever(interval_seconds=None) -> None:
    """Loop persisten janitor — dipanggil worker_decoupled sebagai thread."""
    sb = _sb()
    interval = int(interval_seconds or os.getenv("JANITOR_INTERVAL_SEC", "1800"))
    logger.info(f"[janitor] start | tiap {interval}s (sweep stale + reconcile orphan)")
    while True:
        try:
            run_once(sb)
            _on_loop_success(sb)
        except Exception as e:
            logger.error(f"[janitor] loop error: {e}")
            _on_loop_error(sb, e)
        time.sleep(interval)
