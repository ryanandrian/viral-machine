import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { vault } from "@/lib/youtube";
import { ADMIN_TEST_TID } from "@/lib/admin/test-readiness";

// Kredensial AI channel test (ADMIN) → vault POOL yang SAMA dgn tenant (tenant_id=admin_test_internal):
// simpan = VALIDASI NYATA ke penyedia (validate-early); kunci Fernet di sisi Python. Nol jalur duplikat.
export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  if (!b.provider_key || !b.key) return NextResponse.json({ error: "provider_key + key wajib" }, { status: 400 });
  try {
    const r = await vault("/api/credentials/ai", {
      tenant_id: ADMIN_TEST_TID, provider_key: String(b.provider_key),
      key: String(b.key), label: String(b.label ?? "Test Lab"),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}

export async function DELETE(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  if (!b.account_id) return NextResponse.json({ error: "account_id wajib" }, { status: 400 });
  try {
    const r = await vault("/api/credentials/ai/delete", { tenant_id: ADMIN_TEST_TID, account_id: String(b.account_id) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) return NextResponse.json({ error: j.error || "gagal" }, { status: 502 });
    return NextResponse.json(j);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "vault unreachable" }, { status: 502 });
  }
}
