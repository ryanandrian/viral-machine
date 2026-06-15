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


# ── Akses niche per-tier ("niche dasar", DESAIN §6) — admin set niches.is_base ──────
BASE_NICHE_TIERS = {"trial", "starter"}  # tier ini → HANYA niche is_base (niche dasar)


def is_base_tier(plan_type) -> bool:
    return (plan_type or "starter") in BASE_NICHE_TIERS


def base_niches(sb) -> list:
    """niche_id `is_base=true` & aktif (admin-editable via panel niches). Niche dasar utk trial/starter."""
    if not sb:
        return []
    try:
        res = sb.table("niches").select("niche_id").eq("is_active", True).eq("is_base", True).execute()
        return [r["niche_id"] for r in (res.data or [])]
    except Exception as e:
        logger.debug(f"[Limits] base_niches gagal: {e}")
        return []


def available_niches(sb, plan_type: str) -> list:
    """Niche INCLUDED per tier: trial/starter → is_base saja; pro/business → semua aktif (katalog).
    NB: ini niche katalog-included; pengajuan CUSTOM niche terpisah → can_request_custom_niche()."""
    if not sb:
        return []
    try:
        q = sb.table("niches").select("niche_id").eq("is_active", True)
        if is_base_tier(plan_type):
            q = q.eq("is_base", True)
        return [r["niche_id"] for r in (q.execute().data or [])]
    except Exception as e:
        logger.debug(f"[Limits] available_niches {plan_type} gagal: {e}")
        return []


def entitled_niches(sb, plan_type: str, tenant_id: str) -> list:
    """ENTITLEMENT niche penuh tenant = katalog-included per tier (available_niches)
    + niche custom/private MILIK tenant (`niches.exclusive_to = tenant_id`, aktif).
    Dipakai pemilihan niche channel mode='random' (= seluruh entitlement, [[decisions_niche_model]])."""
    base = available_niches(sb, plan_type)
    if not sb or not tenant_id:
        return base
    try:
        res = (sb.table("niches").select("niche_id")
               .eq("is_active", True).eq("exclusive_to", tenant_id).execute())
        mine = [r["niche_id"] for r in (res.data or [])]
    except Exception as e:
        logger.debug(f"[Limits] entitled_niches exclusive {tenant_id} gagal: {e}")
        mine = []
    # union jaga urutan stabil
    out = list(base)
    for n in mine:
        if n not in out:
            out.append(n)
    return out


def can_request_custom_niche(plan_type) -> bool:
    """
    Boleh AJUKAN custom niche (add-on berbayar: public-after-90d / private-permanent — [[decisions_niche_model]]).
    starter/pro/business = YA · trial = TIDAK. (Ini ENTITLEMENT pengajuan, bukan akses katalog included.)
    """
    return (plan_type or "starter") in {"starter", "pro", "business"}


# ── Trial = TIER 'trial' (BYOK, time-boxed 7 hari). Caps via plan_limits['trial'] (1ch/1vid-hari).
#    Durasi via app_config (admin-editable). Lapse → trial_expired (lead marketing). DESAIN §3. ─────
def trial_days() -> int:
    """Lama trial (hari) — ADMIN-EDITABLE via app_config (no-hardcode)."""
    from src.config.app_config import get_int
    return get_int("trial_duration_days", 7)


def start_trial(sb, tenant_id: str) -> dict:
    """
    Mulai trial (dipanggil saat signup, Phase 9). Set tier 'trial' + status 'trial' + anchor + period_end.
    Caps (1ch/1vid-hari) otomatis dari plan_limits['trial']. BYOK — tak ada platform key.
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=trial_days())
    sb.table("tenant_configs").update({
        "plan_type":           "trial",
        "subscription_status": "trial",
        "trial_started_at":    now.isoformat(),
        "current_period_end":  end.isoformat(),
    }).eq("tenant_id", tenant_id).execute()
    logger.info(f"[Limits] trial started tenant={tenant_id} → end {end.date()} (tier 'trial', caps dari plan_limits)")
    return {"trial_ends": end.isoformat()}


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
               .select("subscription_status,plan_type,videos_per_day,max_videos_per_day,is_developer,discount_pct,trial_started_at")
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
        # comp/developer (always-free) → SELALU producing. Trial = tier 'trial' (producing),
        # caps (1ch/1vid-hari) via plan_limits['trial'] di daily_publish_cap. trial_expired → blocked.
        "can_produce": comp or can_produce(status),
        "daily_cap":   daily_publish_cap(trow, limits),
        "status":      status,
        "plan_type":   trow.get("plan_type") or "starter",
        "is_comp":     comp,
    }
