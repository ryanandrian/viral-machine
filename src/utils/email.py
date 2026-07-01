"""
Email transaksional via SMTP (Phase 8c, DESAIN §8). stdlib `smtplib` — NOL dependency baru.

Config-driven dari env (SMTP_HOST/PORT/USER/PASS/FROM, gitignored). Email tenant di-resolve via
**Supabase Auth admin API** (service_role) — email ada di `auth.users`, bukan tenant_configs (opsi A).

⛔ **Email = layer notifikasi NON-ESENSIAL.** Kegagalan kirim TAK BOLEH menggagalkan billing
(webhook/renewal) → `send_email` tak pernah raise; semua call-site fail-soft. Idempotensi diatur
pemanggil (kirim hanya saat TRANSISI status, bukan tiap sweep/retry webhook).
"""

import os
import smtplib
import ssl
from email.message import EmailMessage

from loguru import logger


def _cfg() -> dict:
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "465") or 465),
        "user": os.getenv("SMTP_USER"),
        "pass": os.getenv("SMTP_PASS"),
        "from": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER"),
    }


def send_email(to: str, subject: str, body: str, html: str | None = None) -> bool:
    """Kirim 1 email (fail-soft). Return True bila terkirim. Tak pernah raise."""
    c = _cfg()
    if not (c["host"] and c["user"] and c["pass"] and to):
        logger.warning(f"[Email] config/penerima tak lengkap — skip (to={to!r} subj={subject!r})")
        return False
    try:
        msg = EmailMessage()
        msg["From"] = c["from"]; msg["To"] = to; msg["Subject"] = subject
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")
        ctx = ssl.create_default_context()
        if c["port"] == 465:
            with smtplib.SMTP_SSL(c["host"], c["port"], timeout=30, context=ctx) as s:
                s.login(c["user"], c["pass"]); s.send_message(msg)
        else:
            with smtplib.SMTP(c["host"], c["port"], timeout=30) as s:
                s.starttls(context=ctx); s.login(c["user"], c["pass"]); s.send_message(msg)
        logger.info(f"[Email] terkirim → {to} | {subject!r}")
        return True
    except Exception as e:
        logger.warning(f"[Email] gagal kirim → {to}: {type(e).__name__}: {e}")
        return False


def tenant_email(tenant_id: str, sb=None) -> str | None:
    """Resolve email tenant via Supabase Auth admin API (service_role). None bila gagal (fail-soft)."""
    if not tenant_id:
        return None
    try:
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        resp = sb.auth.admin.get_user_by_id(str(tenant_id))
        user = getattr(resp, "user", None) or resp
        return getattr(user, "email", None)
    except Exception as e:
        logger.warning(f"[Email] resolve email tenant {tenant_id} gagal: {e}")
        return None


def _survey_url() -> str:
    return os.getenv("TRIAL_SURVEY_URL", "https://mesinviral.com/feedback")


def _upgrade_url() -> str:
    return os.getenv("UPGRADE_URL", "https://mesinviral.com/billing")


def _cfg_int(sb, key: str, default: int) -> int:
    """Baca angka dari app_config (admin-editable, no-hardcode). Gagal → default."""
    try:
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        r = sb.table("app_config").select("value").eq("key", key).limit(1).execute()
        if r.data:
            return int(r.data[0]["value"])
    except Exception:
        pass
    return default


def _bi(en: str, id_: str) -> str:
    """Body email DWIBAHASA (world-class): Inggris di atas, Indonesia di bawah, dipisah garis."""
    return f"{en}\n\n──────────────────────────\n\n{id_}"


# ── Notifikasi billing (fail-soft; dipanggil dari webhook/renewal) ───────────
def notify_payment_receipt(tenant_id: str, plan_type: str, amount, sb=None) -> bool:
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    try:
        amt = f"Rp {int(amount):,}".replace(",", ".")
    except Exception:
        amt = str(amount)
    return send_email(
        to, "Payment received / Pembayaran diterima — MesinViral",
        _bi(f"Hi,\n\nYour payment for the {plan_type} plan ({amt}) was successful. Your subscription is now ACTIVE.\n"
            f"Happy creating!\n\n— The MesinViral Team",
            f"Halo,\n\nPembayaran paket {plan_type} ({amt}) berhasil. Langganan Anda kini AKTIF.\n"
            f"Selamat berkarya!\n\n— Tim MesinViral"),
    )


def notify_trial_lapse(tenant_id: str, sb=None) -> bool:
    """Trial habis tanpa upgrade → ajak upgrade + minta feedback (lead marketing, DESAIN §3)."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    days = _cfg_int(sb, "trial_duration_days", 7)  # no-hardcode: durasi dari app_config
    up, sv = _upgrade_url(), _survey_url()
    return send_email(
        to, "Your trial has ended / Trial Anda selesai — MesinViral",
        _bi(f"Hi,\n\nYour {days}-day trial has ended. Upgrade to keep producing content automatically:\n{up}\n\n"
            f"Not a fit? Help us improve (1 min): {sv}\n\n— The MesinViral Team",
            f"Halo,\n\nMasa trial {days} hari Anda telah berakhir. Upgrade untuk melanjutkan produksi konten otomatis:\n{up}\n\n"
            f"Belum cocok? Bantu kami jadi lebih baik (1 menit): {sv}\n\n— Tim MesinViral"),
    )


def notify_suspend_warning(tenant_id: str, grace_days: int, sb=None) -> bool:
    """GRACE: periode habis, mesin masih jalan ~grace_days lagi (dunning). Ajak perpanjang."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    up = _upgrade_url()
    return send_email(
        to, "Renewal failed — action needed / Perpanjangan gagal — MesinViral",
        _bi(f"Hi,\n\nYour renewal payment hasn't gone through. Production will STOP in ~{grace_days} days unless "
            f"your subscription is renewed.\nRenew now to keep your channels running:\n{up}\n\n— The MesinViral Team",
            f"Halo,\n\nPembayaran perpanjangan belum berhasil. Produksi akan DIHENTIKAN dalam ~{grace_days} hari "
            f"jika langganan tidak diperbarui.\nPerbarui sekarang agar channel Anda tetap berjalan:\n{up}\n\n— Tim MesinViral"),
    )


def notify_trial_ending(tenant_id: str, days_left: int, sb=None) -> bool:
    """H-x SEBELUM trial habis → ajak upgrade + tawarkan beri masukan (skenario 1)."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    en_sisa = "tomorrow" if days_left <= 1 else f"in {days_left} days"
    id_sisa = "besok" if days_left <= 1 else f"dalam {days_left} hari"
    up, sv = _upgrade_url(), _survey_url()
    return send_email(
        to, "Your trial ends soon — upgrade / Trial Anda segera berakhir — MesinViral",
        _bi(f"Hi,\n\nYour trial ends {en_sisa}. Upgrade to keep producing content without interruption:\n{up}\n\n"
            f"Not a fit? Help us improve (1 min): {sv}\n\n— The MesinViral Team",
            f"Halo,\n\nMasa trial Anda berakhir {id_sisa}. Upgrade untuk terus memproduksi konten otomatis tanpa jeda:\n{up}\n\n"
            f"Belum cocok? Bantu kami jadi lebih baik (1 menit): {sv}\n\n— Tim MesinViral"),
    )


def notify_renewal_reminder(tenant_id: str, days_left: int, sb=None) -> bool:
    """H-x SEBELUM langganan berbayar habis → ajak perpanjang (bayar bulan berikutnya)."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    en_sisa = "tomorrow" if days_left <= 1 else f"in {days_left} days"
    id_sisa = "besok" if days_left <= 1 else f"dalam {days_left} hari"
    up = _upgrade_url()
    return send_email(
        to, "Your subscription ends soon — renew / Langganan Anda segera berakhir — MesinViral",
        _bi(f"Hi,\n\nYour MesinViral subscription ends {en_sisa}. Renew to keep your channels producing without "
            f"interruption:\n{up}\n\n— The MesinViral Team",
            f"Halo,\n\nLangganan MesinViral Anda berakhir {id_sisa}. Perpanjang agar channel Anda tetap berproduksi "
            f"tanpa jeda:\n{up}\n\n— Tim MesinViral"),
    )


def notify_suspended(tenant_id: str, sb=None) -> bool:
    """SUSPENDED: masa tenggang lewat → produksi DIHENTIKAN. Ajak aktifkan lagi."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    up = _upgrade_url()
    return send_email(
        to, "Production paused — reactivate / Produksi dihentikan — MesinViral",
        _bi(f"Hi,\n\nYour subscription has ended and the grace period has passed, so your channels' production has "
            f"been PAUSED.\nReactivate anytime by renewing your subscription:\n{up}\n\n— The MesinViral Team",
            f"Halo,\n\nLangganan Anda berakhir dan masa tenggang telah lewat, jadi produksi channel Anda kami "
            f"HENTIKAN sementara.\nAktifkan kembali kapan saja dengan memperbarui langganan:\n{up}\n\n— Tim MesinViral"),
    )
