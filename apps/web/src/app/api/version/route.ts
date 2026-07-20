import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

// [Mitigasi muat-ulang otomatis, ketok owner 2026-07-20] Sumber kebenaran versi deployment =
// BUILD_ID Next (unik per `next build`). Tab lama membandingkan nilai ini dgn versi saat ia
// dimuat → beda = deploy baru telah terjadi → tawarkan "Muat ulang" (version-watcher.tsx).
// Akar insiden: tab terbuka melintasi deploy → chunk/Server Action lama → error sampai hard-reload
// (log mv-web 20-Jul: "Failed to find Server Action ... older deployment").

let _buildId: string | null = null;

function buildId(): string {
  if (_buildId) return _buildId;
  try {
    _buildId = readFileSync(join(process.cwd(), ".next", "BUILD_ID"), "utf8").trim();
  } catch {
    _buildId = "dev"; // mode dev / BUILD_ID tak ada — watcher tak akan pernah mismatch dgn 'dev'
  }
  return _buildId;
}

export const dynamic = "force-dynamic"; // jangan di-prerender — wajib jawaban runtime proses INI

export async function GET() {
  return NextResponse.json(
    { build: buildId() },
    { headers: { "Cache-Control": "no-store, must-revalidate" } },
  );
}
