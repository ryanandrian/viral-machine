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
        to, "Pembayaran diterima — MesinViral",
        f"Halo,\n\nPembayaran paket {plan_type} ({amt}) berhasil. Langganan Anda kini AKTIF.\n"
        f"Selamat berkarya!\n\n— Tim MesinViral",
    )


def notify_trial_lapse(tenant_id: str, sb=None) -> bool:
    """Trial habis tanpa upgrade → ajak upgrade + minta feedback (lead marketing, DESAIN §3)."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    return send_email(
        to, "Trial Anda selesai — lanjutkan dengan MesinViral",
        f"Halo,\n\nMasa trial 7 hari Anda telah berakhir. Upgrade untuk melanjutkan produksi konten otomatis.\n\n"
        f"Belum cocok? Bantu kami jadi lebih baik (1 menit): {_survey_url()}\n\nTerima kasih!\n\n— Tim MesinViral",
    )


def notify_suspend_warning(tenant_id: str, grace_days: int, sb=None) -> bool:
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    return send_email(
        to, "Perpanjangan langganan gagal — MesinViral",
        f"Halo,\n\nPembayaran perpanjangan belum berhasil. Produksi akan DIHENTIKAN dalam ~{grace_days} hari "
        f"jika langganan tidak diperbarui.\n\nPerbarui sekarang agar channel Anda tetap berjalan.\n\n— Tim MesinViral",
    )
