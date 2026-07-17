import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { vault } from "@/lib/youtube";

// [B21] F3 — pendaftaran-mandiri reseller via tautan agen (SPEC 5f; PUBLIK).
// GET ?code= → validasi tautan (boolean + nama agen). POST → simpan calon status 'pending'
// (nomor rekening dienkripsi via vault). Akun login BARU dibuat saat agen MENYETUJUI (ketok F3).

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function resolveJoin(code: string) {
  if (!/^[A-Z0-9]{4,16}$/.test(code)) return null;
  const a = createAdminClient();
  const { data: sw } = await a.from("app_config").select("value").eq("key", "partner_program_enabled").limit(1);
  if (sw?.[0] && Number(sw[0].value) !== 1) return null;
  const { data: rows } = await a.from("agents").select("id,company_name,status").eq("join_code", code).limit(1);
  const ag = rows?.[0];
  return ag && ag.status === "active" ? ag : null;
}

export async function GET(req: Request) {
  const code = (new URL(req.url).searchParams.get("code") || "").trim().toUpperCase();
  const ag = await resolveJoin(code);
  return NextResponse.json(ag ? { valid: true, company: ag.company_name } : { valid: false });
}

export async function POST(req: Request) {
  const b = await req.json().catch(() => ({}));
  const lang = b.lang === "en" ? "en" : "id";
  const code = String(b.code ?? "").trim().toUpperCase();
  const ag = await resolveJoin(code);
  if (!ag) return NextResponse.json({ ok: false, msg: lang === "id" ? "Tautan pendaftaran tidak berlaku." : "This registration link is not valid." }, { status: 400 });
  const name = String(b.name ?? "").trim();
  const email = String(b.email ?? "").trim().toLowerCase();
  const phone = String(b.phone ?? "").trim();
  const bank_name = String(b.bank_name ?? "").trim();
  const account_no = String(b.account_no ?? "").trim();
  const holder = String(b.holder ?? "").trim();
  if (!name || !EMAIL_RE.test(email) || !bank_name || !account_no || !holder) {
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Lengkapi nama, email, dan data rekening." : "Complete your name, email, and bank details." }, { status: 400 });
  }
  if (!/^[0-9]{5,20}$/.test(account_no)) {
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Nomor rekening hanya angka (5-20 digit)." : "Account number must be 5-20 digits." }, { status: 400 });
  }
  const a = createAdminClient();
  // anti-dobel: email yang sama masih pending/aktif di agen ini → tolak jelas
  const { data: dup } = await a.from("resellers").select("id,status").eq("agent_id", ag.id).eq("email", email)
    .in("status", ["pending", "active"]).limit(1);
  if (dup && dup.length > 0) {
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Email ini sudah terdaftar (menunggu persetujuan / sudah aktif)." : "This email is already registered (pending or active)." }, { status: 400 });
  }
  const { data: rs, error } = await a.from("resellers").insert({
    agent_id: ag.id, name, email, phone: phone || null, status: "pending",
  }).select("id").single();
  if (error) return NextResponse.json({ ok: false, msg: error.message }, { status: 500 });
  // nomor rekening → terenkripsi via BE (satu otoritas kripto; SPEC §2.5)
  try {
    const r = await vault("/api/partner/op", { op: "reseller_bank_set", reseller_id: rs.id, bank_name, account_no, holder });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "bank_set gagal");
  } catch (e) {
    // gagal simpan rekening = pendaftaran dibatalkan UTUH (jangan setengah-jadi) + pesan jujur
    await a.from("resellers").delete().eq("id", rs.id);
    console.error("[reseller-register] bank_set gagal:", e);
    return NextResponse.json({ ok: false, msg: lang === "id" ? "Gagal menyimpan data rekening — coba lagi." : "Failed to store bank details — try again." }, { status: 500 });
  }
  return NextResponse.json({ ok: true, company: ag.company_name });
}
