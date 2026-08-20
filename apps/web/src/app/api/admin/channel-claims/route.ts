import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Klaim channel YouTube — SATU-SATUNYA jalur buka kuncian (CHANNEL_LOCK_ACTIVATION_PLAN §7).
// Tenant sengaja tidak diberi jalur: ketokan owner 2026-08-20 — memindahkan channel ke akun
// MesinViral lain hanya punya satu alasan sah, dan ketiganya (pemulihan akun · agensi menyerahkan
// ke klien · channel benar-benar dijual) diverifikasi manusia, bukan tombol tenant.

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("youtube_channel_claims")
    .select("yt_channel_id, tenant_id, yt_channel_title, claimed_at")
    .order("claimed_at", { ascending: false });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ rows: data ?? [] });
}

export async function DELETE(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const body = await req.json().catch(() => ({}));
  const id = String(body.yt_channel_id ?? "").trim();
  if (!id) return NextResponse.json({ error: "yt_channel_id wajib" }, { status: 400 });

  const admin = createAdminClient();
  const { data: before } = await admin
    .from("youtube_channel_claims").select("tenant_id, yt_channel_title")
    .eq("yt_channel_id", id).maybeSingle();
  if (!before) return NextResponse.json({ error: "klaim tidak ditemukan" }, { status: 404 });

  const { error } = await admin.from("youtube_channel_claims").delete().eq("yt_channel_id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  // Jejak WAJIB: siapa melepas, channel apa, dari tenant mana (dipakai saat sengketa kepemilikan).
  await admin.from("admin_audit").insert({
    admin_uid: g.user.id, action: "channel_claim.release",
    detail: { yt_channel_id: id, tenant_id_sebelumnya: before.tenant_id, title: before.yt_channel_title },
  });
  return NextResponse.json({ ok: true });
}
