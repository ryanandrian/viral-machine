import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

// Status sistem PUBLIK (tab Status /about) — kondisi NYATA dari worker_heartbeats (sumber yang sama
// dengan admin System Health; ambang stale 60s identik). Menggantikan status dekorasi/palsu
// (keputusan owner 2026-07-04). Respons tanpa detail sensitif — hanya nama thread + up/stale.
export const dynamic = "force-dynamic";

const STALE_MS = 60_000;

export async function GET() {
  const a = createAdminClient();
  const { data, error } = await a.from("worker_heartbeats").select("worker_name,status,last_heartbeat_at");
  if (error) return NextResponse.json({ error: "unavailable" }, { status: 503 });
  const now = Date.now();
  const services = (data ?? []).map((w) => ({
    key: w.worker_name as string,
    up: w.status === "up" && now - new Date(w.last_heartbeat_at as string).getTime() < STALE_MS,
  }));
  const all_ok = services.length > 0 && services.every((s) => s.up);
  return NextResponse.json({ services, all_ok });
}
