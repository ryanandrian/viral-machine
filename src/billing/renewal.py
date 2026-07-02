"""
Siklus langganan + SIKLUS-HIDUP LANJUTAN (Phase 8 + B9 LIFECYCLE) — SEMUA timing config-driven
(app_config, admin-editable, no-hardcode). SATU mesin (thread billing_renewal), non-redundan.

State: trial → trial_expired (nurture) · active → grace → suspended → blocked → deleted.
Reaktivasi (bayar) = webhook/reconciler (set active + reset penanda). Comp/developer EXEMPT.

Sumber kebenaran = LIFECYCLE_NURTURE_ARCHITECTURE.md (§1 state, §3 knob, §4 data, §5 mesin).
Notifikasi lengkap tiap fase; idempotent (penanda *_sent_at / nurture_step / deletion_warn_sent),
fail-soft per-tenant (error 1 tenant TAK menghentikan sweep). Dijalankan worker_decoupled sbg thread
(cadence BILLING_CHECK_INTERVAL_SEC, default 86400).
"""

import os
import math
import time
from datetime import datetime, timezone, timedelta

from loguru import logger

from src.billing.limits import is_comp_account


def _cfg(sb, key: str, default: int) -> int:
    """Angka dari app_config (admin-editable via System Configuration, no-hardcode). Gagal → default."""
    try:
        r = sb.table("app_config").select("value").eq("key", key).limit(1).execute()
        if r.data:
            return int(r.data[0]["value"])
    except Exception as e:
        logger.debug(f"[Billing] cfg {key} gagal: {e}")
    return default


def _ladder(sb, prefix: str, n: int, defaults: list) -> list:
    """Baca offset tangga (mis. nurture_step1..5_days / suspend_dunning1..5_days) dari app_config."""
    return [_cfg(sb, f"{prefix}{i}_days", defaults[i - 1]) for i in range(1, n + 1)]


def _parse_end(pe):
    if not pe:
        return None
    try:
        end = datetime.fromisoformat(str(pe).replace("Z", "+00:00"))
        return end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
    except Exception:
        return None


def _days_since(ts, now: datetime):
    """Hari (float) sejak timestamp ts (iso/tz) sampai now. None bila ts kosong/invalid."""
    d = _parse_end(ts)
    return None if not d else (now - d).total_seconds() / 86400.0


def _reactivate_url(tenant_id: str):
    """Link reaktivasi 1-klik (token HMAC via sign_state, reuse OAUTH_STATE_SECRET). None → email fallback ke /billing."""
    try:
        from src.billing.youtube_oauth import sign_state
        base = os.getenv("APP_BASE_URL", "https://mesinviral.com").rstrip("/")
        tok = sign_state(tenant_id, ret="/dashboard", ttl=90 * 86400)
        return f"{base}/reactivate?token={tok}"
    except Exception:
        return None


def next_status(row: dict, now: datetime, grace_days: int) -> str | None:
    """Status seharusnya berdasar current_period_end (jalur AKTIF). None = JANGAN ubah di sini.
    Comp/final(blocked/deleted/cancelled/trial_expired)/period-null → None (post-suspended ditangani sweep)."""
    if is_comp_account(row):
        return None
    status = row.get("subscription_status") or "active"
    if status in ("suspended", "blocked", "deleted", "cancelled", "trial_expired"):
        return None
    end = _parse_end(row.get("current_period_end"))
    if not end:
        return None
    if status == "trial":
        return None if now <= end else "trial_expired"
    if now <= end:
        return "active"
    if now <= end + timedelta(days=grace_days):
        return "grace"
    return "suspended"


# ── B9: segmentasi lead (dari perilaku NYATA) ───────────────────────────────
def _compute_lead_temp(sb, tenant_id: str) -> str:
    """🔥hot = sudah produksi (production_runs/videos) · 🌤️warm = ada channel/kredensial tapi belum produksi ·
    ❄️cold = nyaris tak setup. Dihitung sekali saat masuk trial_expired/suspended. Fail-soft → 'cold'."""
    try:
        for tbl in ("production_runs", "videos"):
            r = sb.table(tbl).select("id", count="exact", head=True).eq("tenant_id", tenant_id).execute()
            if (getattr(r, "count", None) or 0) > 0:
                return "hot"
        for tbl in ("channels", "tenant_youtube_accounts", "tenant_ai_accounts"):
            r = sb.table(tbl).select("id", count="exact", head=True).eq("tenant_id", tenant_id).execute()
            if (getattr(r, "count", None) or 0) > 0:
                return "warm"
    except Exception as e:
        logger.debug(f"[Billing] lead_temp {tenant_id} gagal: {e}")
    return "cold"


# ── B9: hard-delete (purge data + revoke token + aset S3) ────────────────────
# Urutan anak→induk (channels TERAKHIR). KEEP: payments (legal), tenant_configs (anonim), feedback_submissions (anonim).
_PURGE_TABLES = [
    "video_analytics", "channel_insights", "tts_delivery_samples", "pipeline_run_logs",
    "pipeline_queue", "production_runs", "content_inventory", "videos", "direct_jobs",
    "niche_requests", "music_library", "voice_catalog", "tenant_ai_accounts",
    "tenant_youtube_accounts", "support_tickets", "email_outbox", "channels",
]


def _hard_delete_tenant(sb, tenant_id: str) -> None:
    """UU PDP: cabut token YouTube → hapus aset S3 → purge tabel konten → anonimkan record sisa.
    Idempotent, fail-soft per-langkah. Sisakan: payments (legal), tenant_configs(deleted+strip PII), feedback(anonim)."""
    # 1) Revoke token YouTube di Google (sebelum hapus baris)
    try:
        from src.billing.youtube_oauth import revoke_tenant_tokens
        revoke_tenant_tokens(tenant_id)
    except Exception as e:
        logger.warning(f"[Billing] revoke token {tenant_id} gagal (lanjut): {e}")
    # 2) Aset S3 (video mentah {tenant}/ + logo brand-logo/{tenant}/)
    try:
        from src.utils import s3_buffer
        s3_buffer.delete_prefix(f"{tenant_id}/")
        s3_buffer.delete_prefix(f"brand-logo/{tenant_id}/")
    except Exception as e:
        logger.warning(f"[Billing] purge S3 {tenant_id} gagal (lanjut): {e}")
    # 3) Purge tabel konten (anak→induk; .eq tenant_id → baris global tenant_id NULL AMAN tak tersentuh)
    for tbl in _PURGE_TABLES:
        try:
            sb.table(tbl).delete().eq("tenant_id", tenant_id).execute()
        except Exception as e:
            logger.warning(f"[Billing] purge {tbl} {tenant_id} gagal (lanjut): {e}")
    # 4) Anonimkan record sisa (legal/anti-abuse)
    try:
        sb.table("feedback_submissions").update({"email": None}).eq("tenant_id", tenant_id).execute()
    except Exception:
        pass
    try:
        sb.table("tenant_configs").update({
            "subscription_status": "deleted", "display_handle": None, "telegram_chat_id": None,
        }).eq("tenant_id", tenant_id).execute()
    except Exception as e:
        logger.error(f"[Billing] set deleted {tenant_id} gagal: {e}")
    logger.info(f"[Billing] HARD-DELETE selesai tenant={tenant_id} (data purged, token revoked, record diminimalkan)")


def sweep_subscriptions(sb) -> dict:
    """Scan tenant_configs → reminder pra-habis + transisi status + NURTURE/dunning + blokir/hapus. Comp exempt."""
    grace_days = _cfg(sb, "billing_grace_days", 7)
    trial_rem  = _cfg(sb, "trial_reminder_days_before", 1)
    renew_rem  = _cfg(sb, "renewal_reminder_days_before", 3)
    nurture_on = _cfg(sb, "nurture_enabled", 1)
    susp_window = _cfg(sb, "suspend_window_days", 30)
    block_ret  = _cfg(sb, "block_retention_days", 30)
    disc_pct   = _cfg(sb, "winback_discount_pct", 0)
    disc_days  = _cfg(sb, "winback_discount_valid_days", 3)
    s3_purge_after = _cfg(sb, "s3_raw_purge_after_suspend_days", 0)
    nurture_steps = _ladder(sb, "nurture_step", 5, [2, 5, 9, 16, 30])
    dunning_steps = _ladder(sb, "suspend_dunning", 5, [0, 7, 14, 21, 28])
    warn_days = [_cfg(sb, "deletion_warn1_days", 30), _cfg(sb, "deletion_warn2_days", 7), _cfg(sb, "deletion_warn3_days", 1)]

    rows = (sb.table("tenant_configs")
            .select("tenant_id,subscription_status,current_period_end,is_developer,discount_pct,"
                    "trial_reminder_sent_at,renewal_reminder_sent_at,suspend_notified_at,"
                    "lead_temp,nurture_step,nurture_last_sent_at,suspended_at,blocked_at,"
                    "deletion_scheduled_at,raw_assets_purged_at,winback_offer_pct,winback_offer_expires_at,deletion_warn_sent")
            .execute().data) or []
    now = datetime.now(timezone.utc)
    changed = exempt = reminded = nurtured = deleted = 0

    from src.utils import email as mail

    for r in rows:
        if is_comp_account(r):
            exempt += 1
            continue
        tid = r["tenant_id"]
        cur = r.get("subscription_status") or "active"
        end = _parse_end(r.get("current_period_end"))
        ract = _reactivate_url(tid)   # link 1-klik utk email lifecycle (None → fallback /billing)

        try:
            # ── 1) REMINDER pra-habis (trial/active) — sekali per siklus via penanda ──
            if end and now < end:
                secs = (end - now).total_seconds()
                days_left = max(1, math.ceil(secs / 86400))
                if cur == "trial" and trial_rem > 0 and secs <= trial_rem * 86400 and not r.get("trial_reminder_sent_at"):
                    mail.notify_trial_ending(tid, days_left, sb)
                    sb.table("tenant_configs").update({"trial_reminder_sent_at": now.isoformat()}).eq("tenant_id", tid).execute()
                    reminded += 1
                elif cur == "active" and renew_rem > 0 and secs <= renew_rem * 86400 and not r.get("renewal_reminder_sent_at"):
                    mail.notify_renewal_reminder(tid, days_left, sb)
                    sb.table("tenant_configs").update({"renewal_reminder_sent_at": now.isoformat()}).eq("tenant_id", tid).execute()
                    reminded += 1

            # ── 2) TRANSISI status jalur AKTIF (trial_expired / grace / suspended) ──
            tgt = next_status(r, now, grace_days)
            if tgt and tgt != cur:
                upd = {"subscription_status": tgt}
                if tgt == "suspended":
                    upd["suspended_at"] = now.isoformat()
                if tgt == "trial_expired":
                    upd["lead_temp"] = _compute_lead_temp(sb, tid)
                    upd["nurture_step"] = 0
                sb.table("tenant_configs").update(upd).eq("tenant_id", tid).execute()
                logger.info(f"[Billing] {tid}: {cur} → {tgt}")
                changed += 1
                if tgt == "trial_expired":
                    mail.notify_trial_lapse(tid, sb)
                elif tgt == "grace":
                    mail.notify_suspend_warning(tid, grace_days, sb)
                elif tgt == "suspended" and not r.get("suspend_notified_at"):
                    mail.notify_suspended(tid, sb)
                    sb.table("tenant_configs").update({"suspend_notified_at": now.isoformat()}).eq("tenant_id", tid).execute()
                # refresh state lokal utk logika lanjutan di sweep yang sama
                cur = tgt
                r = {**r, **upd}

            # ── 3) NURTURE trial-lapse (tangga email, varian suhu, anti-dobel) ──
            if cur == "trial_expired" and nurture_on:
                since = _days_since(r.get("current_period_end"), now)   # anchor lapse = akhir trial
                if since is not None:
                    step_done = int(r.get("nurture_step") or 0)
                    due = 0
                    for i, off in enumerate(nurture_steps, start=1):
                        if since >= off:
                            due = i
                    if due > step_done and due >= 1:
                        offer_pct = offer_days = None
                        step_upd = {"nurture_step": due, "nurture_last_sent_at": now.isoformat()}
                        # langkah ke-3 (default) = tawaran diskon comeback bila diaktifkan admin
                        if due == 3 and disc_pct > 0:
                            offer_pct, offer_days = disc_pct, disc_days
                            step_upd["winback_offer_pct"] = disc_pct
                            step_upd["winback_offer_expires_at"] = (now + timedelta(days=disc_days)).isoformat()
                        if not r.get("lead_temp"):
                            step_upd["lead_temp"] = _compute_lead_temp(sb, tid)
                        mail.notify_nurture_step(tid, due, r.get("lead_temp"), sb, offer_pct=offer_pct, offer_days=offer_days, reactivate_url=ract)
                        # lead PANAS → alert admin utk outreach personal (Telegram)
                        if (step_upd.get("lead_temp") or r.get("lead_temp")) == "hot":
                            try:
                                from src.utils.telegram_notifier import TelegramNotifier
                                TelegramNotifier().notify_admin(f"🔥 Lead PANAS (trial-lapse) tenant <code>{tid}</code> — layak outreach personal (nurture step {due}).")
                            except Exception:
                                pass
                        sb.table("tenant_configs").update(step_upd).eq("tenant_id", tid).execute()
                        nurtured += 1

            # ── 4) SUSPENDED: dunning + purge S3 dini + transisi ke blocked ──
            elif cur == "suspended":
                sat = r.get("suspended_at")
                if not sat:   # backfill bila kosong (mis. transisi lama)
                    sb.table("tenant_configs").update({"suspended_at": now.isoformat()}).eq("tenant_id", tid).execute()
                    r["suspended_at"] = now.isoformat(); sat = r["suspended_at"]
                since = _days_since(sat, now) or 0.0
                # 4a) purge dini file video mentah S3 (video sudah aman di YouTube) — sekali
                if since >= s3_purge_after and not r.get("raw_assets_purged_at"):
                    try:
                        from src.utils import s3_buffer
                        s3_buffer.delete_prefix(f"{tid}/")
                    except Exception as e:
                        logger.warning(f"[Billing] purge dini S3 {tid} gagal: {e}")
                    sb.table("tenant_configs").update({"raw_assets_purged_at": now.isoformat()}).eq("tenant_id", tid).execute()
                    r["raw_assets_purged_at"] = now.isoformat()
                # 4b) dunning (tangga, reuse nurture_step sbg counter — status mutually-exclusive)
                step_done = int(r.get("nurture_step") or 0)
                due = 0
                for i, off in enumerate(dunning_steps, start=1):
                    if since >= off:
                        due = i
                if due > step_done and due >= 1:
                    left = max(1, math.ceil(susp_window - since))
                    offer_pct = disc_pct if disc_pct > 0 else None
                    mail.notify_reactivation_offer(tid, left, sb, offer_pct=offer_pct, offer_days=(disc_days if offer_pct else None), reactivate_url=ract)
                    sb.table("tenant_configs").update({"nurture_step": due, "nurture_last_sent_at": now.isoformat()}).eq("tenant_id", tid).execute()
                    nurtured += 1
                # 4c) transisi → blocked
                if since >= susp_window:
                    del_at = now + timedelta(days=block_ret)
                    sb.table("tenant_configs").update({
                        "subscription_status": "blocked", "blocked_at": now.isoformat(),
                        "deletion_scheduled_at": del_at.isoformat(), "nurture_step": 0, "deletion_warn_sent": 0,
                    }).eq("tenant_id", tid).execute()
                    mail.notify_account_blocked(tid, del_at.date().isoformat(), sb, reactivate_url=ract)
                    logger.info(f"[Billing] {tid}: suspended → blocked (hapus {del_at.date().isoformat()})")
                    changed += 1

            # ── 5) BLOCKED: peringatan hapus (H-30/7/1) + transisi ke deleted ──
            elif cur == "blocked":
                del_at = _parse_end(r.get("deletion_scheduled_at"))
                if del_at:
                    if now >= del_at:
                        # kirim konfirmasi SEBELUM purge (email masih resolvable), lalu hard-delete
                        try:
                            mail.notify_data_deleted(tid, sb)
                        except Exception:
                            pass
                        _hard_delete_tenant(sb, tid)
                        deleted += 1
                        changed += 1
                    else:
                        days_to_del = (del_at - now).total_seconds() / 86400.0
                        sent_mask = int(r.get("deletion_warn_sent") or 0)
                        for bit, wd in enumerate(warn_days):   # bit0=warn1(30), bit1=warn2(7), bit2=warn3(1)
                            if days_to_del <= wd and not (sent_mask & (1 << bit)):
                                mail.notify_deletion_warning(tid, max(1, math.ceil(days_to_del)), del_at.date().isoformat(), sb, reactivate_url=ract)
                                sent_mask |= (1 << bit)
                        if sent_mask != int(r.get("deletion_warn_sent") or 0):
                            sb.table("tenant_configs").update({"deletion_warn_sent": sent_mask}).eq("tenant_id", tid).execute()
        except Exception as e:
            logger.error(f"[Billing] sweep tenant {tid} error (lanjut): {e}")

    logger.info(f"[Billing] sweep: {len(rows)} tenant | changed={changed} reminded={reminded} nurtured={nurtured} deleted={deleted} comp-exempt={exempt}")
    return {"checked": len(rows), "changed": changed, "reminded": reminded, "nurtured": nurtured, "deleted": deleted, "exempt": exempt}


def run_forever(interval_seconds=None) -> None:
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    interval = int(interval_seconds or os.getenv("BILLING_CHECK_INTERVAL_SEC", "86400"))
    logger.info(f"[Billing] renewal+lifecycle sweep start | tiap {interval}s (reminder+transisi+nurture+blokir/hapus, config-driven, comp exempt)")
    while True:
        try:
            sweep_subscriptions(sb)
        except Exception as e:
            logger.error(f"[Billing] sweep error: {e}")
        time.sleep(interval)
