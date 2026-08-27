import { NextResponse, type NextRequest } from "next/server";
import { vault } from "@/lib/youtube";   // pemanggil internal FE→mesin yang sudah ada
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

// [B21] Validasi kode agen/reseller (SPEC 5a): format + aktif + induk aktif + saklar program.
// Kembalikan baris kode valid, atau null (tanpa kode), atau melempar string pesan-tolak dwibahasa.
async function resolveRefCode(admin: ReturnType<typeof createAdminClient>, refCode: unknown, lang: Lang) {
  if (!refCode || typeof refCode !== "string" || !refCode.trim()) return null;
  const code = refCode.trim().toUpperCase();
  const bad = lang === "id" ? "Kode agen/reseller tidak dikenal. Kosongkan bila tidak punya." : "Partner code not recognized. Leave empty if you don't have one.";
  if (!/^[A-Z0-9]{4,12}$/.test(code)) throw bad;
  const { data: sw } = await admin.from("app_config").select("value").eq("key", "partner_program_enabled").limit(1);
  if (sw?.[0] && Number(sw[0].value) !== 1) throw bad; // program mati → kode baru ditolak (kenop admin)
  const { data: rows } = await admin.from("partner_codes")
    .select("code,owner_kind,agent_id,reseller_id,active,used_count").eq("code", code).limit(1);
  const pc = rows?.[0];
  if (!pc?.active) throw bad;
  const { data: ag } = await admin.from("agents").select("status").eq("id", pc.agent_id).limit(1);
  if (ag?.[0]?.status !== "active") throw bad; // suspend agen = cascade kode mati (SPEC §5g.6)
  if (pc.owner_kind === "reseller") {
    const { data: rs } = await admin.from("resellers").select("status").eq("id", pc.reseller_id).limit(1);
    if (rs?.[0]?.status !== "active") throw bad;
  }
  return pc;
}

export async function POST(req: NextRequest) {
  const { email, password, lang: rawLang, refCode } = await req.json().catch(() => ({}));
  const lang: Lang = rawLang === "en" ? "en" : "id";
  if (!email || typeof email !== "string" || !EMAIL_RE.test(email.trim()) || !password || String(password).length < 8) {
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Email/password tidak valid." : "Invalid email/password." }, { status: 400 });
  }
  const to = email.trim().toLowerCase();
  const admin = createAdminClient();
  // [B21] tolak kode tak dikenal SEBELUM akun dibuat (anti-error di titik input, §3.1)
  let pc: Awaited<ReturnType<typeof resolveRefCode>> = null;
  try {
    pc = await resolveRefCode(admin, refCode, lang);
  } catch (m) {
    return NextResponse.json({ ok: false, msg: String(m) }, { status: 400 });
  }
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
  // [B21] KUNCI ATRIBUSI — sekali tulis, permanen (SPEC §1b). Idempotent utk kirim-ulang
  // (upsert ignoreDuplicates); used_count naik HANYA saat baris benar-benar baru (beku §5g.2).
  // Gagal tulis = dicatat ke admin_audit (jejak utk dibereskan) — pendaftaran user TIDAK dibatalkan.
  const uid = data?.user?.id;
  if (pc && uid) {
    try {
      const { data: insd, error: attErr } = await admin.from("tenant_attribution")
        .upsert({ tenant_id: uid, agent_id: pc.agent_id, reseller_id: pc.reseller_id, code: pc.code },
                { onConflict: "tenant_id", ignoreDuplicates: true }).select("tenant_id");
      if (attErr) throw attErr;
      if (insd && insd.length > 0) {
        await admin.from("partner_codes").update({ used_count: (pc.used_count ?? 0) + 1 }).eq("code", pc.code);
      }
    } catch (e) {
      console.error("[signup] atribusi partner GAGAL:", e);
      await admin.from("admin_audit").insert({
        admin_uid: uid, action: "partner.attach_failed",
        detail: { code: pc.code, tenant_id: uid, error: String(e) },
      }).then(() => {}, () => {});
      // [27-Agu] BERISIK, bukan hanya jejak audit. Cacat pintu Google baru ketahuan dari KOMPLEN
      // AGEN justru karena satu-satunya catatan kegagalan masuk ke admin_audit yang nol pembaca.
      // Jalur email diberi alarm yang sama supaya kelas itu tak bisa senyap di pintu mana pun.
      await vault("/api/partner/op", {
        op: "atribusi_gagal", code: pc.code, tenant_id: uid, jalur: "email", error: String(e),
      }).catch(() => {});
    }
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
