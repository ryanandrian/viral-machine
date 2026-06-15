import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

const EDITABLE = [
  "name", "keywords", "style", "target_emotion", "hook_templates", "default_hashtags",
  "is_active", "is_base", "visual_style", "visual_fallbacks", "mood_priority", "voice_profile",
  "emotion_scoring_criteria", "section_timing", "image_quality_tags", "image_negative_prompt",
  "access_type", "exclusive_to", "exclusive_until", "released_at", "release_scheduled_at",
];

// PATCH niches[niche_id] (PHASE10 §2). Whitelist (jangan ubah niche_id PK). + admin_audit.
export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  const patch: Record<string, unknown> = {};
  for (const k of EDITABLE) if (k in body) patch[k] = body[k];
  if (Object.keys(patch).length === 0) return NextResponse.json({ error: "no_editable_fields" }, { status: 400 });

  const admin = createAdminClient();
  const { data, error } = await admin.from("niches").update(patch).eq("niche_id", id).select("*").single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  await admin.from("admin_audit").insert({ admin_uid: g.user.id, action: "niche.update", detail: { niche_id: id, fields: Object.keys(patch) } });
  return NextResponse.json({ ok: true, row: data });
}
