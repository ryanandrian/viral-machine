import { NextResponse, type NextRequest } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { sendMail } from "@/lib/email/smtp";
import { renderConfirmEmail, type Lang } from "@/lib/email/templates";

export const runtime = "nodejs";

// Pendaftaran — email konfirmasi DIKIRIM SENDIRI (ber-brand, dwibahasa, token_hash lintas-alat) via
// admin.generateLink(type=signup) → BUKAN email default Supabase (English + PKCE rapuh lintas-alat).
// Idempotent utk user unconfirmed (dipakai signup + kirim-ulang). Provisioning trial via trigger 0028.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function originOf(req: NextRequest): string {
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  const proto = req.headers.get("x-forwarded-proto") ?? "https";
  return host ? `${proto}://${host}` : "https://mesinviral.com";
}

export async function POST(req: NextRequest) {
  const { email, password, lang: rawLang } = await req.json().catch(() => ({}));
  const lang: Lang = rawLang === "en" ? "en" : "id";
  if (!email || typeof email !== "string" || !EMAIL_RE.test(email.trim()) || !password || String(password).length < 8) {
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Email/password tidak valid." : "Invalid email/password." }, { status: 400 });
  }
  const to = email.trim().toLowerCase();
  const admin = createAdminClient();
  const { data, error } = await admin.auth.admin.generateLink({ type: "signup", email: to, password: String(password) });
  const props = data?.properties as { hashed_token?: string; verification_type?: string } | undefined;
  if (error || !props?.hashed_token) {
    const m = (error?.message || "").toLowerCase();
    if (m.includes("registered") || m.includes("already")) {
      return NextResponse.json({ ok: false, msg: lang === "id" ? "Email sudah terdaftar. Silakan masuk." : "Email already registered. Please sign in." }, { status: 409 });
    }
    console.error("[signup] generateLink gagal:", error?.message);
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Gagal mendaftar. Coba lagi." : "Signup failed. Try again." }, { status: 500 });
  }
  const next = encodeURIComponent("/auth?view=verified");
  const link = `${originOf(req)}/auth/callback?token_hash=${encodeURIComponent(props.hashed_token)}&type=${props.verification_type}&next=${next}`;
  const { subject, html, text } = renderConfirmEmail(lang, link);
  try {
    await sendMail(to, subject, html, text);
  } catch (e) {
    console.error("[signup] SMTP gagal:", e);
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Akun dibuat, tapi email gagal terkirim. Coba 'Kirim ulang'." : "Account created but email failed. Try 'Resend'." }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
