import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { vault } from "@/lib/youtube";

// LIFECYCLE (B9) — HAPUS PERMANEN tenant. Logika hapus (revoke token YouTube ke Google + purge S3 +
// purge tabel konten + anonimkan sisa) ADA di worker Python `_hard_delete_tenant` (renewal.py) — TAK
// bisa ditulis ulang di TS (butuh klien Google/S3). Dipanggil lewat vault → webhook internal
// (pola identik checkout billing). Dicatat admin_audit. Irreversible → FE wajib ConfirmDialog dulu.
export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;

  const res = await vault("/api/admin/lifecycle/hard-delete", { tenant_id: id });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    return NextResponse.json({ error: `hard_delete_failed: ${t.slice(0, 200)}` }, { status: 502 });
  }

  const admin = createAdminClient();
  await admin.from("admin_audit").insert({
    admin_uid: g.user.id, action: "tenant.lifecycle.hard_delete", target_tenant: id, detail: {},
  });
  return NextResponse.json({ ok: true });
}
