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


def plan_display_name(sb, plan_type) -> str:
    """Nama paket yang DILIHAT pelanggan (plan_limits.display_name, admin-editable — Pilar 4:
    satu sumber nama utk SEMUA permukaan: item Snap, email, invoice). Fallback = key mentah."""
    if not sb or not plan_type:
        return str(plan_type or "")
    try:
        r = (sb.table("plan_limits").select("display_name")
             .eq("plan_type", plan_type).limit(1).execute())
        return str((r.data or [{}])[0].get("display_name") or plan_type)
    except Exception as e:
        logger.debug(f"[Limits] display_name {plan_type} gagal: {e}")
        return str(plan_type)


# ── Entitlement lain: gerbang aslinya di DATABASE, bukan di modul ini (Tahap 1 finalisasi_tier_plan,
#    2026-07-13 — 5 fungsi duplikat tanpa pemanggil dibuang dari sini):
#    • signup→trial            = trigger DB `handle_new_tenant` (migr 0028; durasi app_config)
#    • katalog niche per-tier  = RPC `set_channel_niche` + plan_limits.full_niche_catalog (migr 0124)
#    • ajukan niche custom     = RLS INSERT niche_requests + plan_limits.can_request_custom_niche (migr 0130)
#    • kuota LAHIR channel     = RLS INSERT channels vs plan_limits.max_channels (migr 0155)


def _channel_in_quota(sb, tenant_id, channel_id: str, quota: int) -> bool:
    """
    Gerbang JALAN kuota channel (finalisasi_tier_plan Tahap 1.2): hanya N channel TERTUA
    (N = max_channels paket) yang dilayani produksi/publish. Downgrade / keadaan-lama melebihi paket
    → channel di luar N berhenti dilayani TANPA menghapus data (upgrade → hidup lagi otomatis).
    Deterministik: urut created_at lalu id. Fail-OPEN saat error transient (lindungi channel sehat;
    gerbang KERAS pembuatan channel = RLS 0155).
    """
    if not sb or not tenant_id or not channel_id:
        return True
    try:
        res = (sb.table("channels").select("id")
               .eq("tenant_id", tenant_id)
               .order("created_at").order("id")
               .limit(max(1, int(quota))).execute())
        allowed = {str(r["id"]) for r in (res.data or [])}
        ok = str(channel_id) in allowed
        if not ok:
            logger.info(f"[Limits] ch={channel_id} di LUAR kuota paket ({quota} channel) tenant={tenant_id} — tidak dilayani")
        return ok
    except Exception as e:
        logger.warning(f"[Limits] cek kuota channel tenant={tenant_id} gagal ({e}) — fail-open")
        return True


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
    Resolusi gate untuk 1 channel: {can_produce, daily_cap, status, plan_type, in_quota}.
    Dipakai producer (skip bila not can_produce) + publisher (skip + bandingkan published_today vs daily_cap).
    can_produce = status membolehkan DAN channel dalam kuota paket (gerbang JALAN Tahap 1.2 —
    berlaku juga utk comp: kapasitas selalu ikut paket, caps comp = plan_type-nya).
    """
    from src.config.tenant_config import _get_plan_limits
    tid    = channel_row.get("tenant_id")
    trow   = _tenant_gate_row(sb, tid)
    status = trow.get("subscription_status") or "active"
    comp   = is_comp_account(trow)
    limits = _get_plan_limits() or {}
    quota  = channel_quota(trow, limits)
    in_q   = _channel_in_quota(sb, tid, str(channel_row.get("id") or ""), quota)
    return {
        # comp/developer (always-free) → SELALU producing. Trial = tier 'trial' (producing),
        # caps (1ch/1vid-hari) via plan_limits['trial'] di daily_publish_cap. trial_expired → blocked.
        "can_produce": (comp or can_produce(status)) and in_q,
        "daily_cap":   daily_publish_cap(trow, limits),
        "status":      status,
        "plan_type":   trow.get("plan_type") or "starter",
        "is_comp":     comp,
        "in_quota":    in_q,
        "channel_quota": quota,
    }
