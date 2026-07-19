// Template email transaksional MesinViral — world-class, bilingual (ID/EN), in-code (satu sumber
// kebenaran, ter-version-control). Dipakai untuk auth email yang KITA kirim sendiri via SMTP (bukan
// email bawaan Supabase) → brand penuh + jalan di semua alat (link berbasis token_hash).
//
// Layout email = table-based + inline CSS (wajib utk kompatibilitas klien email: Gmail/Outlook/Apple
// Mail). Sertakan versi teks (plain) utk deliverability. Warna brand diselaraskan dgn situs.

export type Lang = "id" | "en";

const BRAND = "#6366F1";
const BRAND_DARK = "#4F46E5";
const INK = "#1F2430";
const MUTED = "#6B7280";
const BG = "#F4F5FB";
const CARD = "#FFFFFF";
const BORDER = "#E6E8F0";
const LOGO_URL = "https://mesinviral.com/mesinviral_logo512.png";
const SITE_URL = "https://mesinviral.com";
const SUPPORT = "mesinviral@lumite.biz.id";

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

type ShellParts = {
  lang: Lang;
  preview: string;
  heading: string;
  intro: string;
  ctaLabel: string;
  ctaUrl: string;
  fallbackLabel: string;
  security: string;
};

// Shell HTML bersama — konsisten utk semua template.
function shell(p: ShellParts): string {
  const year = 2026;
  const tagline = p.lang === "id"
    ? "Mesin produksi konten YouTube Shorts otomatis."
    : "Automated YouTube Shorts production engine.";
  const footerHelp = p.lang === "id"
    ? `Butuh bantuan? Balas email ini atau hubungi <a href="mailto:${SUPPORT}" style="color:${BRAND};text-decoration:none;">${SUPPORT}</a>.`
    : `Need help? Reply to this email or contact <a href="mailto:${SUPPORT}" style="color:${BRAND};text-decoration:none;">${SUPPORT}</a>.`;
  const orCopy = p.lang === "id"
    ? "Atau salin & tempel tautan ini di browser Anda:"
    : "Or copy and paste this link into your browser:";
  const safeUrl = esc(p.ctaUrl);

  return `<!doctype html>
<html lang="${p.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>${esc(p.heading)}</title>
</head>
<body style="margin:0;padding:0;background:${BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">${esc(p.preview)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${BG};padding:32px 12px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:${CARD};border:1px solid ${BORDER};border-radius:16px;overflow:hidden;">
      <tr><td style="padding:28px 32px 8px 32px;" align="left">
        <a href="${SITE_URL}" style="text-decoration:none;">
          <img src="${LOGO_URL}" width="32" height="32" alt="MesinViral" style="vertical-align:middle;border-radius:8px;">
          <span style="vertical-align:middle;font-size:18px;font-weight:700;color:${INK};margin-left:8px;">MesinViral</span>
        </a>
      </td></tr>
      <tr><td style="padding:12px 32px 0 32px;">
        <h1 style="margin:0 0 10px 0;font-size:22px;line-height:1.3;color:${INK};font-weight:700;">${esc(p.heading)}</h1>
        <p style="margin:0 0 24px 0;font-size:15px;line-height:1.6;color:${MUTED};">${esc(p.intro)}</p>
        <table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="border-radius:10px;background:${BRAND};background-image:linear-gradient(135deg,${BRAND},${BRAND_DARK});">
          <a href="${safeUrl}" style="display:inline-block;padding:13px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:10px;">${esc(p.ctaLabel)}</a>
        </td></tr></table>
        <p style="margin:24px 0 6px 0;font-size:13px;line-height:1.5;color:${MUTED};">${esc(orCopy)}</p>
        <p style="margin:0 0 24px 0;font-size:13px;line-height:1.5;word-break:break-all;"><a href="${safeUrl}" style="color:${BRAND};text-decoration:none;">${safeUrl}</a></p>
        <div style="border-top:1px solid ${BORDER};margin:8px 0 20px 0;"></div>
        <p style="margin:0 0 24px 0;font-size:13px;line-height:1.5;color:${MUTED};">${esc(p.security)}</p>
      </td></tr>
      <tr><td style="padding:20px 32px 28px 32px;border-top:1px solid ${BORDER};background:#FAFBFF;">
        <p style="margin:0 0 6px 0;font-size:13px;color:${INK};font-weight:600;">MesinViral</p>
        <p style="margin:0 0 10px 0;font-size:12px;color:${MUTED};">${esc(tagline)}</p>
        <p style="margin:0 0 10px 0;font-size:12px;line-height:1.5;color:${MUTED};">${footerHelp}</p>
        <p style="margin:0;font-size:11px;color:#9AA1B1;">© ${year} MesinViral · <a href="${SITE_URL}/privacy" style="color:#9AA1B1;">Privasi</a> · <a href="${SITE_URL}/terms" style="color:#9AA1B1;">Ketentuan</a></p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>`;
}

function textVersion(heading: string, intro: string, ctaLabel: string, url: string, security: string, lang: Lang): string {
  const orCopy = lang === "id" ? "Buka tautan berikut:" : "Open this link:";
  return `${heading}\n\n${intro}\n\n${ctaLabel} — ${orCopy}\n${url}\n\n${security}\n\n— MesinViral · ${SITE_URL}\n${SUPPORT}`;
}

export type RenderedEmail = { subject: string; html: string; text: string };

// ── Reset password ───────────────────────────────────────────────────────────
export function renderResetEmail(lang: Lang, actionUrl: string): RenderedEmail {
  const t = lang === "id"
    ? {
        subject: "Atur ulang kata sandi MesinViral Anda",
        preview: "Tautan untuk membuat kata sandi baru — berlaku sementara demi keamanan.",
        heading: "Atur ulang kata sandi",
        intro: "Kami menerima permintaan untuk mengatur ulang kata sandi akun MesinViral Anda. Klik tombol di bawah untuk membuat kata sandi baru.",
        cta: "Buat kata sandi baru",
        fallback: "Atau salin tautan ini:",
        security: "Tautan ini akan kedaluwarsa demi keamanan dan hanya bisa dipakai sekali. Jika Anda tidak meminta ini, abaikan email ini — kata sandi Anda tidak berubah.",
      }
    : {
        subject: "Reset your MesinViral password",
        preview: "A link to set a new password — expires soon for your security.",
        heading: "Reset your password",
        intro: "We received a request to reset the password for your MesinViral account. Click the button below to set a new password.",
        cta: "Set a new password",
        fallback: "Or copy this link:",
        security: "This link expires for your security and can be used only once. If you didn't request this, you can safely ignore this email — your password won't change.",
      };
  return {
    subject: t.subject,
    html: shell({ lang, preview: t.preview, heading: t.heading, intro: t.intro, ctaLabel: t.cta, ctaUrl: actionUrl, fallbackLabel: t.fallback, security: t.security }),
    text: textVersion(t.heading, t.intro, t.cta, actionUrl, t.security, lang),
  };
}

// ── Konfirmasi pendaftaran (signup) ────────────────────────────────────────────
export function renderConfirmEmail(lang: Lang, actionUrl: string): RenderedEmail {
  const t = lang === "id"
    ? {
        subject: "Konfirmasi email — aktifkan akun MesinViral Anda",
        preview: "Satu langkah lagi: konfirmasi email untuk mengaktifkan akun Anda.",
        heading: "Konfirmasi email Anda",
        intro: "Terima kasih telah mendaftar di MesinViral. Klik tombol di bawah untuk mengaktifkan akun dan mulai memproduksi konten otomatis.",
        cta: "Konfirmasi email",
        fallback: "Atau salin tautan ini:",
        security: "Jika Anda tidak membuat akun MesinViral, abaikan email ini.",
      }
    : {
        subject: "Confirm your email — activate your MesinViral account",
        preview: "One more step: confirm your email to activate your account.",
        heading: "Confirm your email",
        intro: "Thanks for signing up for MesinViral. Click the button below to activate your account and start producing content automatically.",
        cta: "Confirm email",
        fallback: "Or copy this link:",
        security: "If you didn't create a MesinViral account, you can safely ignore this email.",
      };
  return {
    subject: t.subject,
    html: shell({ lang, preview: t.preview, heading: t.heading, intro: t.intro, ctaLabel: t.cta, ctaUrl: actionUrl, fallbackLabel: t.fallback, security: t.security }),
    text: textVersion(t.heading, t.intro, t.cta, actionUrl, t.security, lang),
  };
}

// ── [B21] Undangan portal agen (MesinViral Partner) ───────────────────────────
export function renderAgentInviteEmail(lang: Lang, actionUrl: string, companyName: string): RenderedEmail {
  const t = lang === "id"
    ? {
        subject: `Akses portal MesinViral Partner untuk ${companyName}`,
        preview: "Aktifkan akses portal agen Anda — pantau komisi & pelanggan bawaan Anda.",
        heading: "Selamat datang di MesinViral Partner",
        intro: `Anda ditunjuk sebagai PIC portal agen untuk ${companyName}. Klik tombol di bawah untuk membuat kata sandi dan masuk ke dasbor Anda — pelanggan bawaan, komisi berjalan, dan riwayat pencairan, semuanya transparan.`,
        cta: "Aktifkan akses portal",
        fallback: "Atau salin tautan ini:",
        security: "Tautan ini kedaluwarsa demi keamanan dan hanya bisa dipakai sekali. Jika Anda tidak merasa bermitra dengan MesinViral, abaikan email ini.",
      }
    : {
        subject: `Your MesinViral Partner portal access for ${companyName}`,
        preview: "Activate your partner portal — track commissions & referred customers.",
        heading: "Welcome to MesinViral Partner",
        intro: `You've been designated as the portal PIC for ${companyName}. Click below to set your password and access your dashboard — referred customers, running commissions, and payout history, fully transparent.`,
        cta: "Activate portal access",
        fallback: "Or copy this link:",
        security: "This link expires for your security and can only be used once. If you're not a MesinViral partner, you can safely ignore this email.",
      };
  return {
    subject: t.subject,
    html: shell({ lang, preview: t.preview, heading: t.heading, intro: t.intro, ctaLabel: t.cta, ctaUrl: actionUrl, fallbackLabel: t.fallback, security: t.security }),
    text: textVersion(t.heading, t.intro, t.cta, actionUrl, t.security, lang),
  };
}

// ── [B21-F3] Undangan portal reseller ─────────────────────────────────────────
// [B21 MGM §9a.5, ketok 2026-07-19] Tenant existing DITAUTKAN jadi reseller (satu login):
// email "portal aktif" — TANPA link set-password (akunnya sudah hidup; recovery = salah pesan).
export function renderResellerLinkedEmail(lang: Lang, portalUrl: string, agentCompany: string): RenderedEmail {
  const t = lang === "id"
    ? {
        subject: `Anda disetujui sebagai reseller ${agentCompany} — portal Anda sudah aktif`,
        preview: "Pendaftaran reseller Anda disetujui — masuk dengan akun MesinViral Anda yang sudah ada.",
        heading: "Selamat, Anda resmi jadi reseller!",
        intro: `${agentCompany} menyetujui pendaftaran reseller Anda di program MesinViral Partner. Karena Anda sudah punya akun MesinViral, tidak perlu membuat kata sandi baru — cukup masuk dengan akun Anda yang biasa (email/Google yang sama), lalu buka portal reseller untuk melihat kode unik, pelanggan bawaan, dan komisi Anda.`,
        cta: "Buka portal reseller",
        fallback: "Atau salin tautan ini:",
        security: "Akses dashboard MesinViral Anda tidak berubah — portal reseller adalah wilayah tambahan pada akun yang sama. Jika Anda tidak pernah mendaftar sebagai reseller, hubungi kami.",
      }
    : {
        subject: `You're approved as a reseller for ${agentCompany} — your portal is active`,
        preview: "Your reseller registration is approved — sign in with your existing MesinViral account.",
        heading: "Congratulations, you're officially a reseller!",
        intro: `${agentCompany} approved your reseller registration in the MesinViral Partner program. Since you already have a MesinViral account, there's no new password to set — just sign in as usual (same email/Google), then open the reseller portal to see your unique code, referred customers, and commissions.`,
        cta: "Open reseller portal",
        fallback: "Or copy this link:",
        security: "Your MesinViral dashboard access is unchanged — the reseller portal is an additional area on the same account. If you never registered as a reseller, please contact us.",
      };
  return {
    subject: t.subject,
    html: shell({ lang, preview: t.preview, heading: t.heading, intro: t.intro, ctaLabel: t.cta, ctaUrl: portalUrl, fallbackLabel: t.fallback, security: t.security }),
    text: textVersion(t.heading, t.intro, t.cta, portalUrl, t.security, lang),
  };
}

export function renderResellerInviteEmail(lang: Lang, actionUrl: string, agentCompany: string): RenderedEmail {
  const t = lang === "id"
    ? {
        subject: `Anda disetujui sebagai reseller ${agentCompany} — aktifkan akses Anda`,
        preview: "Pendaftaran reseller Anda disetujui — buat kata sandi dan mulai pantau komisi Anda.",
        heading: "Selamat, Anda resmi jadi reseller!",
        intro: `${agentCompany} menyetujui pendaftaran reseller Anda di program MesinViral Partner. Klik tombol di bawah untuk membuat kata sandi — dasbor Anda menampilkan kode unik, pelanggan bawaan, dan komisi Anda setiap bulan.`,
        cta: "Aktifkan akses reseller",
        fallback: "Atau salin tautan ini:",
        security: "Tautan ini kedaluwarsa demi keamanan dan hanya bisa dipakai sekali. Jika Anda tidak pernah mendaftar sebagai reseller, abaikan email ini.",
      }
    : {
        subject: `You're approved as a reseller for ${agentCompany} — activate your access`,
        preview: "Your reseller registration is approved — set a password and track your commissions.",
        heading: "Congratulations, you're officially a reseller!",
        intro: `${agentCompany} approved your reseller registration in the MesinViral Partner program. Click below to set your password — your dashboard shows your unique code, referred customers, and monthly commissions.`,
        cta: "Activate reseller access",
        fallback: "Or copy this link:",
        security: "This link expires for your security and can only be used once. If you never registered as a reseller, you can safely ignore this email.",
      };
  return {
    subject: t.subject,
    html: shell({ lang, preview: t.preview, heading: t.heading, intro: t.intro, ctaLabel: t.cta, ctaUrl: actionUrl, fallbackLabel: t.fallback, security: t.security }),
    text: textVersion(t.heading, t.intro, t.cta, actionUrl, t.security, lang),
  };
}
