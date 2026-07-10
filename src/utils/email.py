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
from email.utils import formatdate, make_msgid

from loguru import logger


def _from_domain(from_addr: str) -> str:
    """Ambil domain dari alamat From (utk Message-ID selaras domain → reputasi/DMARC). Default lumite.biz.id."""
    try:
        return (from_addr or "").split("@")[-1].strip().rstrip(">").strip() or "lumite.biz.id"
    except Exception:
        return "lumite.biz.id"


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
        # WAJIB (RFC 5322): tanpa Date + Message-ID, Gmail buang diam-diam (dianggap malformed/bot) → tak sampai, tak bounce.
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=_from_domain(c["from"]))
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


def _site_url() -> str:
    return os.getenv("APP_BASE_URL", "https://mesinviral.com").rstrip("/")


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
def notify_payment_receipt(tenant_id: str, plan_type: str, amount, sb=None, order_id: str | None = None) -> bool:
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    try:
        amt = f"Rp {int(amount):,}".replace(",", ".")
    except Exception:
        amt = str(amount)
    inv_en = f"\nInvoice / receipt: {_site_url()}/billing/invoice/{order_id}\n" if order_id else ""
    inv_id = f"\nInvoice / bukti bayar: {_site_url()}/billing/invoice/{order_id}\n" if order_id else ""
    return send_email(
        to, "Payment received / Pembayaran diterima — MesinViral",
        _bi(f"Hi,\n\nYour payment for the {plan_type} plan ({amt}) was successful. Your subscription is now ACTIVE.\n{inv_en}"
            f"Happy creating!\n\n— The MesinViral Team",
            f"Halo,\n\nPembayaran paket {plan_type} ({amt}) berhasil. Langganan Anda kini AKTIF.\n{inv_id}"
            f"Selamat berkarya!\n\n— Tim MesinViral"),
    )


def notify_payment_link(tenant_id: str, order_id: str, amount, redirect_url: str | None,
                        expiry_hours: int = 24, sb=None) -> bool:
    """Order Snap dibuat → email ber-brand 'Selesaikan pembayaran' + LINK Snap aktif (owner 2026-07-04:
    email resmi Midtrans TIDAK memuat link). Fail-soft; berlaku langganan & add-on niche."""
    to = tenant_email(tenant_id, sb)
    if not to or not redirect_url:
        return False
    try:
        amt = f"Rp {int(amount):,}".replace(",", ".")
    except Exception:
        amt = str(amount)
    return send_email(
        to, "Complete your payment / Selesaikan pembayaran Anda — MesinViral",
        _bi(f"Hi,\n\nYour MesinViral invoice ({amt}, order {order_id}) is waiting.\n"
            f"Complete it here (valid ~{expiry_hours}h):\n{redirect_url}\n\n"
            f"Changed your mind on the payment method? Just start again from the Billing page — "
            f"the old invoice is cancelled automatically.\n\n— The MesinViral Team",
            f"Halo,\n\nTagihan MesinViral Anda ({amt}, order {order_id}) menunggu diselesaikan.\n"
            f"Lanjutkan pembayaran di sini (berlaku ±{expiry_hours} jam):\n{redirect_url}\n\n"
            f"Ingin ganti metode pembayaran? Ulangi saja dari halaman Billing — tagihan lama otomatis dibatalkan.\n\n— Tim MesinViral"),
    )


def notify_trial_lapse(tenant_id: str, sb=None) -> bool:
    """Trial habis tanpa upgrade → ajak upgrade + minta feedback (lead marketing, DESAIN §3)."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    days = _cfg_int(sb, "trial_duration_days", 7)  # no-hardcode: durasi dari app_config
    up, sv = _upgrade_url(), _feedback_url(tenant_id, "trial_lapse")
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


def _trial_recap(tenant_id: str, sb=None) -> tuple[str, str]:
    """Recap pencapaian nyata tenant (n video terbit + total views latest-per-video, pola RPC 0056)
    untuk personalisasi pesan konversi. Return (kalimat_id, kalimat_en); ("","") bila nol/gagal (fail-soft)."""
    try:
        if sb is None:
            from supabase import create_client
            sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        vids = sb.table("videos").select("id", count="exact").eq("tenant_id", str(tenant_id)).eq("status", "published").execute()
        n = vids.count or 0
        if n <= 0:
            return "", ""
        views = 0
        try:
            # Latest-per-video, urutan PERSIS RPC 0056 (analytics_date desc nulls last, collected_at desc nulls last).
            # WAJIB paginasi: PostgREST cap 1000 baris/req — tanpa ini views undercount (ryan=7.220 baris, bug tertangkap audit 2026-07-11).
            latest: dict = {}
            page, PAGE = 0, 1000
            while page <= 50:  # pagar keras: 50k baris cukup utk tenant mana pun saat trial
                rows = (sb.table("video_analytics").select("video_id,views,analytics_date,collected_at")
                        .eq("tenant_id", str(tenant_id))
                        .order("analytics_date", desc=True, nullsfirst=False)
                        .order("collected_at", desc=True, nullsfirst=False)
                        .range(page * PAGE, page * PAGE + PAGE - 1)
                        .execute().data) or []
                for r in rows:
                    k = r.get("video_id")
                    if k and k not in latest:  # first-seen pada urutan DESC = snapshot TERBARU per video
                        latest[k] = int(r.get("views") or 0)
                if len(rows) < PAGE:
                    break
                page += 1
            views = sum(latest.values())
        except Exception:
            pass  # views opsional; jumlah video saja tetap bermakna
        v_id = f" dengan total {views:,} views".replace(",", ".") if views > 0 else ""
        v_en = f" with {views:,} total views" if views > 0 else ""
        return (f"Sejauh ini mesin sudah menerbitkan {n} video ke channel Anda{v_id} — sayang bila berhenti di sini.\n\n",
                f"So far the engine has published {n} videos to your channel{v_en} — a shame to stop here.\n\n")
    except Exception as e:
        logger.warning(f"[Email] recap trial {tenant_id} gagal (lanjut tanpa recap): {e}")
        return "", ""


def notify_trial_ending(tenant_id: str, days_left: int, sb=None) -> bool:
    """H-x SEBELUM trial habis → ajak upgrade + tawarkan beri masukan (skenario 1).
    Personalisasi recap-nilai (D1-F3, mandat owner 2026-07-11): sebut n video + views nyata bila ada."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    en_sisa = "tomorrow" if days_left <= 1 else f"in {days_left} days"
    id_sisa = "besok" if days_left <= 1 else f"dalam {days_left} hari"
    up, sv = _upgrade_url(), _feedback_url(tenant_id, "trial_ending")
    recap_id, recap_en = _trial_recap(tenant_id, sb)
    return send_email(
        to, "Your trial ends soon — upgrade / Trial Anda segera berakhir — MesinViral",
        _bi(f"Hi,\n\nYour trial ends {en_sisa}. {recap_en}Upgrade to keep producing content without interruption:\n{up}\n\n"
            f"Not a fit? Help us improve (1 min): {sv}\n\n— The MesinViral Team",
            f"Halo,\n\nMasa trial Anda berakhir {id_sisa}. {recap_id}Upgrade untuk terus memproduksi konten otomatis tanpa jeda:\n{up}\n\n"
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


# ── LIFECYCLE (B9): nurture trial-lapse + dunning suspended + blokir/hapus. Dwibahasa, fail-soft, config-driven. ──
def _feedback_url(tenant_id: str, source: str) -> str:
    """Link feedback + atribusi (?ref tenant, ?source) — 1-klik alasan churn (page prefill ?reason opsional)."""
    base = _survey_url()
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}ref={tenant_id}&source={source}"


def notify_nurture_step(tenant_id: str, step: int, lead_temp: str | None = None, sb=None,
                        offer_pct: int | None = None, offer_days: int | None = None,
                        reactivate_url: str | None = None) -> bool:
    """Email tangga NURTURE utk trial LAPSED (LIFECYCLE). Konten per-langkah (value→bukti-sosial→pengingat→
    peringatan-arsip→final). offer_pct>0 → sisipkan diskon comeback (urgensi offer_days). Fail-soft, dwibahasa."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    up = reactivate_url or _upgrade_url()
    sv = _feedback_url(tenant_id, "nurture")
    steps_en = {
        1: ("Still want your videos on autopilot?", "Your trial ended, but your channel setup is saved. Come back and keep producing viral-ready Shorts automatically."),
        2: ("See what creators do with MesinViral", "Creators like you ship 5+ videos a day and let the engine learn from their own channel. Your setup is one click away."),
        3: ("A quick nudge to pick up where you left off", "Your setup is still ready. Reactivate whenever you like."),
        4: ("Your account data will be archived soon", "We'll archive your inactive account soon. Reactivate now to keep your setup and history."),
        5: ("Last call before we close your setup", "This is the final reminder. Your channel setup is still here — for now."),
    }
    steps_id = {
        1: ("Masih mau video jalan otomatis?", "Trial Anda berakhir, tapi setelan channel Anda tersimpan. Kembali dan lanjutkan produksi Shorts siap-viral otomatis."),
        2: ("Lihat yang dilakukan kreator lain di MesinViral", "Kreator seperti Anda merilis 5+ video/hari dan membiarkan mesin belajar dari channel mereka sendiri. Setelan Anda tinggal satu klik."),
        3: ("Pengingat singkat untuk lanjut dari tempat Anda berhenti", "Setelan Anda masih siap. Aktifkan kapan pun Anda mau."),
        4: ("Data akun Anda akan segera diarsipkan", "Akun tidak aktif akan segera kami arsipkan. Aktifkan sekarang untuk menjaga setelan & riwayat Anda."),
        5: ("Panggilan terakhir sebelum setelan Anda kami tutup", "Ini pengingat terakhir. Setelan channel Anda masih ada — untuk saat ini."),
    }
    en_s, en_b = steps_en.get(step, steps_en[1])
    id_s, id_b = steps_id.get(step, steps_id[1])
    offer_en = offer_id = ""
    if offer_pct and offer_pct > 0:
        vd_en = f" (valid {offer_days} days)" if offer_days else ""
        vd_id = f" (berlaku {offer_days} hari)" if offer_days else ""
        offer_en = f"\n\n🎁 Comeback offer: {offer_pct}% off your first month{vd_en}."
        offer_id = f"\n\n🎁 Penawaran comeback: diskon {offer_pct}% bulan pertama{vd_id}."
    return send_email(
        to, f"{en_s} / {id_s} — MesinViral",
        _bi(f"Hi,\n\n{en_b}{offer_en}\n\nContinue:\n{up}\n\nNot a fit? Tell us why (1 min): {sv}\n\n— The MesinViral Team",
            f"Halo,\n\n{id_b}{offer_id}\n\nLanjutkan:\n{up}\n\nBelum cocok? Beri tahu alasannya (1 menit): {sv}\n\n— Tim MesinViral"),
    )


def notify_reactivation_offer(tenant_id: str, days_left_to_block: int, sb=None,
                              offer_pct: int | None = None, offer_days: int | None = None,
                              reactivate_url: str | None = None) -> bool:
    """Dunning saat SUSPENDED (pelanggan berbayar berhenti): produksi stop, ajak aktifkan lagi SEBELUM akun dikunci."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    up = reactivate_url or _upgrade_url()
    en_when = "soon" if days_left_to_block <= 1 else f"in about {days_left_to_block} days"
    id_when = "segera" if days_left_to_block <= 1 else f"dalam sekitar {days_left_to_block} hari"
    offer_en = offer_id = ""
    if offer_pct and offer_pct > 0:
        offer_en = f" Reactivate now and get {offer_pct}% off your first month back."
        offer_id = f" Aktifkan sekarang dan dapat diskon {offer_pct}% bulan pertama."
    return send_email(
        to, "Reactivate your account / Aktifkan kembali akun Anda — MesinViral",
        _bi(f"Hi,\n\nYour production is paused. Your account will be locked {en_when} if not reactivated, and your "
            f"data scheduled for deletion after that.{offer_en}\nReactivate:\n{up}\n\n— The MesinViral Team",
            f"Halo,\n\nProduksi Anda dijeda. Akun akan dikunci {id_when} bila tidak diaktifkan, dan data dijadwalkan "
            f"dihapus setelahnya.{offer_id}\nAktifkan:\n{up}\n\n— Tim MesinViral"),
    )


def notify_account_blocked(tenant_id: str, deletion_date: str, sb=None, reactivate_url: str | None = None) -> bool:
    """Akun DIKUNCI (blocked): beri tahu tanggal penghapusan data + cara aktifkan-lagi (data masih ada sampai tgl itu)."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    up = reactivate_url or _upgrade_url()
    return send_email(
        to, "Account locked — data deletion scheduled / Akun dikunci — data akan dihapus — MesinViral",
        _bi(f"Hi,\n\nYour account is now locked due to non-payment. Your data (channels, settings, history) is still "
            f"kept and scheduled for permanent deletion on {deletion_date}.\nReactivate before then to restore everything:\n{up}\n\n— The MesinViral Team",
            f"Halo,\n\nAkun Anda kini dikunci karena tidak ada pembayaran. Data Anda (channel, setelan, riwayat) masih "
            f"kami simpan dan dijadwalkan DIHAPUS permanen pada {deletion_date}.\nAktifkan sebelum tanggal itu untuk memulihkan semuanya:\n{up}\n\n— Tim MesinViral"),
    )


def notify_deletion_warning(tenant_id: str, days_left: int, deletion_date: str, sb=None,
                            reactivate_url: str | None = None) -> bool:
    """Peringatan H-x sebelum data DIHAPUS permanen (nol penghapusan diam-diam). Ajak aktifkan-lagi / unduh via admin."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    up = reactivate_url or _upgrade_url()
    en_when = "tomorrow" if days_left <= 1 else f"in {days_left} days"
    id_when = "besok" if days_left <= 1 else f"dalam {days_left} hari"
    return send_email(
        to, f"Final notice: your data will be deleted {en_when} / Data Anda akan dihapus {id_when} — MesinViral",
        _bi(f"Hi,\n\nThis is a reminder that your MesinViral data will be permanently deleted on {deletion_date} ({en_when}).\n"
            f"Reactivate now to keep everything:\n{up}\n\nNeed a copy of your data first? Reply to this email and we'll help.\n\n— The MesinViral Team",
            f"Halo,\n\nPengingat bahwa data MesinViral Anda akan DIHAPUS permanen pada {deletion_date} ({id_when}).\n"
            f"Aktifkan sekarang untuk menjaga semuanya:\n{up}\n\nButuh salinan data lebih dulu? Balas email ini, kami bantu.\n\n— Tim MesinViral"),
    )


def notify_data_deleted(tenant_id: str, sb=None) -> bool:
    """Konfirmasi data telah dihapus permanen (dikirim saat delete; email masih resolvable dari record minimal)."""
    to = tenant_email(tenant_id, sb)
    if not to:
        return False
    up = _upgrade_url()
    return send_email(
        to, "Your data has been deleted / Data Anda telah dihapus — MesinViral",
        _bi(f"Hi,\n\nAs scheduled, your MesinViral content data has been permanently deleted. Thank you for trying us.\n"
            f"You're always welcome back — start fresh anytime:\n{up}\n\n— The MesinViral Team",
            f"Halo,\n\nSesuai jadwal, data konten MesinViral Anda telah DIHAPUS permanen. Terima kasih telah mencoba kami.\n"
            f"Anda selalu kami sambut kembali — mulai lagi kapan saja:\n{up}\n\n— Tim MesinViral"),
    )
