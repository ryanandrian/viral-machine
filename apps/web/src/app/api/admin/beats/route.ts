import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// content_beats (level SYSTEM, sumber tunggal kosakata beat 0128/0129) — SATU pintu tulis:
// • motion_mode/motion_dir = Gerakan Kamera per Adegan (halaman System Configuration). Durasi TAK terpengaruh.
// • weight/weight_locked   = Bobot antar-adegan (Catalog > Durasi, [DURASI-F5] 2026-07-16): porsi kata
//   narasi; mesin (align_beat_weights) menyelaraskan berkala — weight_locked=true = mesin tak menyentuh.

const MODES = ["fix", "cerdas"];
const DIRS = ["zoom_in", "zoom_out", "pan_lr", "pan_rl", "pan_ud", "pan_du", "pan_diag", "pan_diag_rev", "still"];
const W_MIN = 1, W_MAX = 30;   // pagar bobot (nilai kanonik 2–15; ruang wajar tanpa bisa ekstrem)

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data, error } = await admin.from("content_beats")
    .select("beat_key, sort_order, label_id, label_en, motion_mode, motion_dir, weight, weight_locked")
    .eq("is_active", true).order("sort_order");
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ beats: data ?? [] });
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { beat_key, motion_mode, motion_dir, weight, weight_locked } = await req.json().catch(() => ({}));
  if (!beat_key || typeof beat_key !== "string") return NextResponse.json({ error: "beat_key wajib" }, { status: 400 });
  // HOOK: gerakan kamera terkunci fix zoom_in (owner 2026-07-05) — guard KHUSUS kolom motion;
  // bobot hook TETAP boleh diatur ([DURASI-F5]; dulu ditolak total → bobot hook tak bisa disentuh).
  if (beat_key === "hook" && (motion_mode !== undefined || motion_dir !== undefined))
    return NextResponse.json({ error: "hook_locked" }, { status: 400 });
  const upd: Record<string, string | number | boolean> = {};
  if (motion_mode !== undefined) {
    if (!MODES.includes(motion_mode)) return NextResponse.json({ error: "invalid_mode" }, { status: 400 });
    upd.motion_mode = motion_mode;
  }
  if (motion_dir !== undefined) {
    if (!DIRS.includes(motion_dir)) return NextResponse.json({ error: "invalid_dir" }, { status: 400 });
    upd.motion_dir = motion_dir;
  }
  if (weight !== undefined) {
    const w = Number(weight);
    if (!Number.isInteger(w) || w < W_MIN || w > W_MAX)
      return NextResponse.json({ error: "invalid_weight", hint: `bulat ${W_MIN}–${W_MAX}` }, { status: 400 });
    upd.weight = w;
  }
  if (weight_locked !== undefined) {
    if (typeof weight_locked !== "boolean") return NextResponse.json({ error: "invalid_weight_locked" }, { status: 400 });
    upd.weight_locked = weight_locked;
  }
  if (Object.keys(upd).length === 0) return NextResponse.json({ error: "no_fields" }, { status: 400 });
  const admin = createAdminClient();
  const { data, error } = await admin.from("content_beats")
    .update({ ...upd, updated_at: new Date().toISOString() }).eq("beat_key", beat_key).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "beats.update", detail: { beat_key, ...upd } });
  return NextResponse.json({ ok: true, row: data });
}
