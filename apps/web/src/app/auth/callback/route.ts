// Auth callback (Phase 9.1) — tukar PKCE `code` / `token_hash` jadi session cookie server-side.
// @supabase/ssr default = PKCE: link verify-email / reset / OAuth balik dgn `?code=` (atau
// `?token_hash=&type=` utk template email-OTP). Tanpa exchange ini, SSR/middleware tak lihat session.
// Pola kanonik Supabase App Router (Next 16 route handler). Lihat PHASE9_FRONTEND_WIRING.md §9.1.
import { NextResponse, type NextRequest } from "next/server";
import { cookies } from "next/headers";
import type { EmailOtpType } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { vault } from "@/lib/youtube";   // pemanggil internal FE→mesin yang sudah ada (x-internal-secret)

// [B21 fix 27-Agu] Umur maksimum akun (detik) yang masih dianggap "baru lahir" saat callback jalan.
//
// KENAPA PAGAR INI WAJIB. Halaman ini berjalan SETIAP KALI orang masuk lewat Google — bukan hanya
// saat mendaftar. Tanpa pagar umur, agen bisa mengirim tautan `?ref=KODE`-nya kepada tenant yang
// SUDAH ADA, tenant itu masuk, dan komisinya diklaim — melanggar SSOT §1b: "atribusi terkunci
// permanen sejak daftar · tidak ada klaim belakangan, tidak ada rebutan".
//
// Angkanya dari DATA NYATA (diukur 27-Agu, bukan ditebak): akun yang baru mendaftar berselisih
// 0 detik antara "dibuat" dan "masuk terakhir"; `andarini.nadia` berselisih 17 HARI. Satu putaran
// pilih-akun Google selesai dalam belasan detik, jadi 120 detik longgar tapi tetap sempit.
// Angka mati, sengaja: ia bukan nilai bisnis (tak menyentuh harga/kuota/mutu) — ia batas teknis
// satu putaran OAuth.
const UMUR_AKUN_BARU_DETIK = 120;

/** [B21 fix 27-Agu] Tulis atribusi agen untuk pendaftar BARU yang datang lewat pintu OAuth.
 *
 *  Keabsahan kode TIDAK dinilai di sini — dipinjam dari pemeriksa yang sudah ada
 *  (`/api/partner/check`, semantik sama dengan jalur signup email) supaya aturannya tetap hidup di
 *  SATU tempat (SSOT §5g.2). Dua tempat menilai = dua aturan yang bisa bergeser.
 *
 *  Gagal-lunak terhadap pengguna (masuknya TIDAK boleh dibatalkan karena urusan komisi), tapi
 *  TIDAK senyap: kegagalan menulis dialarmkan ke admin — sebab cacat 27-Agu baru ketahuan dari
 *  komplen agen, justru karena kegagalan atribusi cuma masuk jejak audit yang nol pembaca. */
async function tulisAtribusiOAuth(origin: string): Promise<void> {
  const jar = await cookies();
  const titipan = jar.get("mv_ref")?.value;
  if (!titipan) return;                       // tanpa kode = bukan bawaan siapa pun (SSOT §1b)
  jar.set("mv_ref", "", { maxAge: 0, path: "/" });   // sekali pakai, apa pun hasilnya

  const kode = decodeURIComponent(titipan).trim().toUpperCase();
  const admin = createAdminClient();
  let tenantId = "";
  try {
    const supa = await createClient();
    const { data: sesi } = await supa.auth.getUser();
    const u = sesi?.user;
    if (!u) return;
    tenantId = u.id;

    // PAGAR §1b — hanya akun yang BARU lahir. Akun lama = klaim belakangan, ditolak.
    const umurDetik = (Date.now() - new Date(u.created_at).getTime()) / 1000;
    if (!(umurDetik >= 0 && umurDetik <= UMUR_AKUN_BARU_DETIK)) return;

    // Keabsahan kode: pemeriksa yang SUDAH ADA (satu aturan).
    const r = await fetch(`${origin}/api/partner/check?code=${encodeURIComponent(kode)}`, {
      cache: "no-store",
    });
    const { valid } = (await r.json()) as { valid?: boolean };
    if (!valid) return;

    const { data: pc } = await admin.from("partner_codes")
      .select("code,agent_id,reseller_id,used_count").eq("code", kode).limit(1);
    const row = pc?.[0];
    if (!row) return;

    // Sekali tulis, tak bisa menimpa (pola persis jalur signup email; sejak migr 0217 pagarnya
    // ditegakkan DATABASE juga — UPDATE/DELETE ditolak trigger).
    const { data: insd, error } = await admin.from("tenant_attribution")
      .upsert({ tenant_id: tenantId, agent_id: row.agent_id, reseller_id: row.reseller_id,
                code: row.code },
              { onConflict: "tenant_id", ignoreDuplicates: true }).select("tenant_id");
    if (error) throw error;
    if (insd && insd.length > 0) {
      await admin.from("partner_codes")
        .update({ used_count: (row.used_count ?? 0) + 1 }).eq("code", row.code);
    }
  } catch (e) {
    console.error("[callback] atribusi partner GAGAL:", e);
    // BERISIK, bukan senyap: jejak audit (seperti jalur email) + alarm admin.
    await admin.from("admin_audit").insert({
      admin_uid: tenantId || null, action: "partner.attach_failed",
      detail: { code: kode, tenant_id: tenantId, jalur: "oauth", error: String(e) },
    }).then(() => {}, () => {});
    // Alarm ke admin lewat jalur internal yang SUDAH ADA (`/api/partner/op` + notify_admin),
    // bukan rute baru — nol pintu tambahan.
    await vault("/api/partner/op", {
      op: "atribusi_gagal", code: kode, tenant_id: tenantId, jalur: "oauth", error: String(e),
    }).catch(() => {});
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/dashboard";
  const safeNext = next.startsWith("/") ? next : "/dashboard"; // cegah open-redirect

  // Next.js 16 di belakang reverse-proxy me-resolve `new URL(request.url).origin` ke alamat bind
  // server (localhost:3000), MENGABAIKAN header Host → semua redirect callback nyasar ke localhost.
  // origin publik HARUS diambil dari header yang dikirim nginx (proxy_set_header Host $host).
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? new URL(request.url).host;
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const origin = `${proto}://${host}`;

  const supabase = await createClient();

  // Akun baru tanpa channel → /onboarding, bukan /dashboard (hanya bila next masih default /dashboard).
  const resolveDest = async (): Promise<string> => {
    if (safeNext !== "/dashboard") return safeNext;
    // Non-produksi (trial habis/suspend) → /billing (pintu upgrade), bukan terjebak onboarding.
    const { data: tc } = await supabase.from("tenant_configs").select("subscription_status").maybeSingle();
    const st = (tc as { subscription_status?: string } | null)?.subscription_status;
    if (st === "trial_expired" || st === "suspended") return "/billing";
    const { count } = await supabase.from("channels").select("id", { count: "exact", head: true });
    return (count ?? 0) > 0 ? "/dashboard" : "/onboarding";
  };

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      await tulisAtribusiOAuth(origin);   // [B21 fix 27-Agu] kode rujukan pintu OAuth
      return NextResponse.redirect(`${origin}${await resolveDest()}`);
    }
    return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent(error.message)}`);
  }
  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    if (!error) return NextResponse.redirect(`${origin}${await resolveDest()}`);
    return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent(error.message)}`);
  }
  return NextResponse.redirect(`${origin}/auth?view=login&error=${encodeURIComponent("Link tidak valid atau kedaluwarsa.")}`);
}
