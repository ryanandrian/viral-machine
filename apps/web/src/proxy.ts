// Root proxy (Next 16 — eks-"middleware"; konvensi di-rename 2026-06-16). Refresh sesi Supabase +
// proteksi route (redirect /auth bila no session, gate /admin super-admin) via updateSession.
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function proxy(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  // Skip aset statis; jalankan di route lain (refresh session).
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
