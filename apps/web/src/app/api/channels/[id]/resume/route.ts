import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

// [B24 §10c] JALUR BUKA rem channel — memulihkan produksi TANPA memproduksi apa pun.
//
// Rem darurat (3 produksi gagal beruntun) dulu hanya bisa dilepas oleh "Jalankan ulang" yang sukses.
// Setelah gerbang uji dipasang, tombol itu terkunci untuk tenant masa tenggang dan tenant masa coba
// yang jatah ujinya habis — padahal produksi rutin KEDUANYA sengaja tetap dibiarkan jalan. Tanpa
// endpoint ini mereka terjebak: mesin berhenti, pemulihnya dikunci.
//
// Aman diberikan: melepas rem tidak memanggil AI, tidak merender, tidak mengunggah. Gerbang kesiapan
// channel & gerbang langganan tetap berlaku sesudahnya; bila sebabnya belum diperbaiki, rem menyala
// lagi setelah 3 kegagalan berikutnya.
//
// Gerbang yang dipakai = PRODUKSI (bukan uji): yang produksinya boleh, boleh memulihkan.

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  // Kepemilikan ditegakkan RLS: klien ber-sesi hanya melihat channel miliknya sendiri.
  const { data: ch } = await supabase
    .from("channels").select("id, production_paused").eq("id", id).maybeSingle();
  if (!ch) return NextResponse.json({ error: "channel tak ditemukan / bukan milik Anda" }, { status: 404 });

  const { data: boleh, error: gErr } = await supabase.rpc("tenant_produce_allowed", { p_tenant_id: user.id });
  if (gErr) {
    console.error("[channels/resume] gerbang produksi gagal:", gErr.message);
    return NextResponse.json({ error: "GATE:gate_unavailable" }, { status: 503 });
  }
  if (!boleh) return NextResponse.json({ error: "GATE:subscription" }, { status: 403 });

  if (!ch.production_paused) return NextResponse.json({ ok: true, resumed: 0, already: true });

  const admin = createAdminClient();
  const { data: n, error } = await admin.rpc("tenant_resume_channels", {
    p_tenant_id: user.id, p_channel_id: id,
  });
  if (error) {
    console.error("[channels/resume] lepas rem gagal:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  return NextResponse.json({ ok: true, resumed: Number(n ?? 0) });
}
