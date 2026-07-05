import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// Gerakan Kamera per Adegan (Fase 2, level SYSTEM) — baca/tulis content_beats.motion_mode/motion_dir.
// Sumber tunggal kosakata + motion (0128/0129). Berlaku semua konten. Durasi TAK terpengaruh.

const MODES = ["fix", "cerdas"];
const DIRS = ["zoom_in", "zoom_out", "pan_lr", "pan_rl", "pan_ud", "pan_du", "pan_diag", "pan_diag_rev", "still"];

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data, error } = await admin.from("content_beats")
    .select("beat_key, sort_order, label_id, label_en, motion_mode, motion_dir")
    .eq("is_active", true).order("sort_order");
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ beats: data ?? [] });
}

export async function PATCH(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { beat_key, motion_mode, motion_dir } = await req.json().catch(() => ({}));
  if (!beat_key || typeof beat_key !== "string") return NextResponse.json({ error: "beat_key wajib" }, { status: 400 });
  // HOOK = adegan pembuka utama: terkunci fix zoom_in, tak boleh diubah (owner 2026-07-05).
  if (beat_key === "hook") return NextResponse.json({ error: "hook_locked" }, { status: 400 });
  const upd: Record<string, string> = {};
  if (motion_mode !== undefined) {
    if (!MODES.includes(motion_mode)) return NextResponse.json({ error: "invalid_mode" }, { status: 400 });
    upd.motion_mode = motion_mode;
  }
  if (motion_dir !== undefined) {
    if (!DIRS.includes(motion_dir)) return NextResponse.json({ error: "invalid_dir" }, { status: 400 });
    upd.motion_dir = motion_dir;
  }
  if (Object.keys(upd).length === 0) return NextResponse.json({ error: "no_fields" }, { status: 400 });
  const admin = createAdminClient();
  const { data, error } = await admin.from("content_beats")
    .update({ ...upd, updated_at: new Date().toISOString() }).eq("beat_key", beat_key).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "beats.motion.update", detail: { beat_key, ...upd } });
  return NextResponse.json({ ok: true, row: data });
}
