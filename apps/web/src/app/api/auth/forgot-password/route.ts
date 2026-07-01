import { NextResponse, type NextRequest } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { sendMail } from "@/lib/email/smtp";
import { renderResetEmail, type Lang } from "@/lib/email/templates";

export const runtime = "nodejs"; // butuh nodemailer + service_role (bukan edge)

// Reset password — DIKIRIM SENDIRI oleh mv-web (bukan email bawaan Supabase):
//  1. generate_link (service_role) → hashed_token (verification_type=recovery, terverifikasi empiris).
//  2. Bangun link berbasis token_hash → /auth/callback (verifyOtp) → JALAN DI SEMUA ALAT (tak perlu
//     browser yang sama; beda dgn PKCE ?code yang butuh code_verifier di alat asal).
//  3. Kirim email ber-brand bilingual via SMTP.
// Anti-enumeration: selalu balas 200 {ok:true} walau email tak terdaftar (tak bocorkan keberadaan akun).

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function originOf(req: NextRequest): string {
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  const proto = req.headers.get("x-forwarded-proto") ?? "https";
  return host ? `${proto}://${host}` : "https://mesinviral.com";
}

export async function POST(req: NextRequest) {
  const { email, lang: rawLang } = await req.json().catch(() => ({}));
  const lang: Lang = rawLang === "en" ? "en" : "id";

  if (!email || typeof email !== "string" || !EMAIL_RE.test(email.trim())) {
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Email tidak valid." : "Invalid email." }, { status: 400 });
  }
  const to = email.trim().toLowerCase();
  const origin = originOf(req);

  const admin = createAdminClient();
  const { data, error } = await admin.auth.admin.generateLink({
    type: "recovery",
    email: to,
    options: { redirectTo: origin },
  });

  // Email tak terdaftar / error non-kritis → diam-diam sukses (anti-enumeration). Log utk audit server.
  const hashedToken = data?.properties?.hashed_token;
  if (error || !hashedToken) {
    console.warn(`[forgot-password] generateLink tanpa token utk ${to}: ${error?.message ?? "no token"}`);
    return NextResponse.json({ ok: true });
  }

  const next = encodeURIComponent("/auth?view=reset");
  const link = `${origin}/auth/callback?token_hash=${encodeURIComponent(hashedToken)}&type=recovery&next=${next}`;
  const { subject, html, text } = renderResetEmail(lang, link);

  try {
    await sendMail(to, subject, html, text);
  } catch (e) {
    console.error(`[forgot-password] SMTP gagal utk ${to}:`, e);
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Gagal mengirim email. Coba lagi." : "Failed to send email. Try again." }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
