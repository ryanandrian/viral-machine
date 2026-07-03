import { NextResponse } from "next/server";
import { sendMail } from "@/lib/email/smtp";
import { createAdminClient } from "@/lib/supabase/admin";

// Form Kontak publik (tab Kontak /about) → kirim email dari SERVER via SMTP platform (bukan mailto:
// yang bergantung aplikasi email pengunjung). Tujuan = company_profile.email (admin-editable di
// /admin/company-profile) — keputusan owner 2026-07-04: NOL hardcode; ke depan bisa dialihkan ke bot.
export const runtime = "nodejs";

export async function POST(req: Request) {
  const b = await req.json().catch(() => ({}));
  const name = (b?.name ?? "").toString().slice(0, 120).trim();
  const email = (b?.email ?? "").toString().slice(0, 200).trim();
  const msg = (b?.msg ?? "").toString().slice(0, 4000).trim();
  if (!msg) return NextResponse.json({ error: "pesan kosong" }, { status: 400 });

  const { data: cp } = await createAdminClient().from("company_profile").select("email").limit(1).maybeSingle();
  const to = ((cp as { email?: string } | null)?.email ?? "").trim();
  if (!to) return NextResponse.json({ error: "kontak belum dikonfigurasi (Company Profile)" }, { status: 500 });
  const subject = `[Kontak] ${name || "Pengunjung situs"}`;
  const text = `Pesan dari form kontak mesinviral.com\n\nNama : ${name || "-"}\nEmail: ${email || "-"}\n\n${msg}`;
  const html = `<p><b>Pesan dari form kontak mesinviral.com</b></p><p>Nama: ${escapeHtml(name) || "-"}<br/>Email: ${escapeHtml(email) || "-"}</p><p style="white-space:pre-wrap">${escapeHtml(msg)}</p>`;
  try {
    await sendMail(to, subject, html, text);
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message || "gagal kirim" }, { status: 500 });
  }
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
