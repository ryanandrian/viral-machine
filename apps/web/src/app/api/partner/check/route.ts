import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

// [B21] Cek-hidup kode agen/reseller utk form daftar (publik; HANYA mengembalikan boolean —
// tidak membocorkan pemilik/data apa pun). Semantik = resolveRefCode signup (satu aturan).
export async function GET(req: Request) {
  const code = (new URL(req.url).searchParams.get("code") || "").trim().toUpperCase();
  if (!/^[A-Z0-9]{4,12}$/.test(code)) return NextResponse.json({ valid: false });
  const admin = createAdminClient();
  try {
    const { data: sw } = await admin.from("app_config").select("value").eq("key", "partner_program_enabled").limit(1);
    if (sw?.[0] && Number(sw[0].value) !== 1) return NextResponse.json({ valid: false });
    const { data: rows } = await admin.from("partner_codes")
      .select("owner_kind,agent_id,reseller_id,active").eq("code", code).limit(1);
    const pc = rows?.[0];
    if (!pc?.active) return NextResponse.json({ valid: false });
    const { data: ag } = await admin.from("agents").select("status").eq("id", pc.agent_id).limit(1);
    if (ag?.[0]?.status !== "active") return NextResponse.json({ valid: false });
    if (pc.owner_kind === "reseller") {
      const { data: rs } = await admin.from("resellers").select("status").eq("id", pc.reseller_id).limit(1);
      if (rs?.[0]?.status !== "active") return NextResponse.json({ valid: false });
    }
    return NextResponse.json({ valid: true });
  } catch {
    return NextResponse.json({ valid: false }); // gagal-cek = tidak memvalidasi (server tetap gerbang akhir)
  }
}
