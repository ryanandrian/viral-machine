"""
Tier-gating + Subscription-state gate (Phase 8a, DESAIN §4 billing / §8 scheduler-gate).

Monetisasi inti: **unpaid → STOP produksi & publish.** Status langganan ↔ scheduler:
  • producing-allowed  = {active, trial, grace}  → produksi + publish jalan
  • {suspended, cancelled} → DIHENTIKAN (producer skip, publisher skip) — no compute, no publish.

Tier caps dari `plan_limits` (DB, config-driven, admin-tunable):
  • daily_publish_cap = batas publish/hari/channel = min(videos_per_day tenant, plan max ceiling)
  • channel_quota     = max_channels paket (enforcement di channel-create / onboarding, P9-10)

Dipakai: `producer` (gate produksi) + `publisher` (gate + cap harian). Fail-OPEN ke 'active'
untuk tenant lama tanpa kolom (back-compat); status invalid → treat non-producing (aman).
"""

import os
from datetime import datetime, timezone

from loguru import logger

# Status yang BOLEH produksi/publish (domain states, §4). Sisanya = stop.
PRODUCING_STATUSES = {"active", "trial", "grace"}


def can_produce(subscription_status) -> bool:
    """True bila status mengizinkan produksi/publish. None/kosong → 'active' (back-compat tenant lama)."""
    return (subscription_status or "active") in PRODUCING_STATUSES


def is_comp_account(tenant_row: dict) -> bool:
    """
    Comp/internal account = GRATIS SELAMANYA, bypass siklus billing (DESAIN: akun developer owner).
    Sumber: is_developer=True ATAU discount_pct>=100. Implikasi: SELALU producing, TAK PERNAH
    suspended/expired/ditagih, current_period_end boleh null (perpetual). Renewal-checker WAJIB exempt ini.
    """
    if tenant_row.get("is_developer"):
        return True
    try:
        return int(tenant_row.get("discount_pct") or 0) >= 100
    except Exception:
        return False


def daily_publish_cap(tenant_row: dict, plan_limits: dict) -> int:
    """Batas publish per hari per channel = min(rate pilihan tenant, ceiling paket). Min 1."""
    plan      = tenant_row.get("plan_type") or "starter"
    plan_cap  = int((plan_limits.get(plan) or {}).get("max_videos_per_day", 1) or 1)
    tenant_rate = tenant_row.get("videos_per_day") or tenant_row.get("max_videos_per_day") or plan_cap
    return max(1, min(int(tenant_rate), plan_cap))


def channel_quota(tenant_row: dict, plan_limits: dict) -> int:
    """Max channel per paket (enforcement di channel-create/onboarding — P9-10)."""
    plan = tenant_row.get("plan_type") or "starter"
    return int((plan_limits.get(plan) or {}).get("max_channels", 1) or 1)


def published_today_count(sb, channel_id: str) -> int:
    """Jumlah video PUBLISHED hari ini (UTC) untuk channel — utk enforce cap harian."""
    if not sb or not channel_id:
        return 0
    try:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        res = (sb.table("videos").select("id", count="exact")
               .eq("channel_id", channel_id).eq("status", "published")
               .gte("published_at", start).execute())
        return res.count or 0
    except Exception as e:
        logger.debug(f"[Limits] published_today ch={channel_id} gagal: {e}")
        return 0


def _tenant_gate_row(sb, tenant_id: str) -> dict:
    """Ambil field gate dari tenant_configs. Fail-soft → {} (caller perlakukan back-compat)."""
    if not sb or not tenant_id:
        return {}
    try:
        res = (sb.table("tenant_configs")
               .select("subscription_status,plan_type,videos_per_day,max_videos_per_day,is_developer,discount_pct")
               .eq("tenant_id", tenant_id).limit(1).execute())
        return (res.data or [{}])[0]
    except Exception as e:
        logger.debug(f"[Limits] tenant_gate {tenant_id} gagal: {e}")
        return {}


def gate_for_channel(sb, channel_row: dict) -> dict:
    """
    Resolusi gate untuk 1 channel: {can_produce, daily_cap, status, plan_type}.
    Dipakai producer (skip bila not can_produce) + publisher (skip + bandingkan published_today vs daily_cap).
    """
    from src.config.tenant_config import _get_plan_limits
    tid    = channel_row.get("tenant_id")
    trow   = _tenant_gate_row(sb, tid)
    status = trow.get("subscription_status") or "active"
    comp   = is_comp_account(trow)
    limits = _get_plan_limits() or {}
    return {
        # comp/developer (always-free) → SELALU producing, lepas dari status langganan.
        "can_produce": comp or can_produce(status),
        "daily_cap":   daily_publish_cap(trow, limits),
        "status":      status,
        "plan_type":   trow.get("plan_type") or "starter",
        "is_comp":     comp,
    }
