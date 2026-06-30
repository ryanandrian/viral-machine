import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";

// E2.3 — antrian pengajuan custom niche (niche_requests). Lifecycle A-Z (CUSTOM_NICHE_REQUEST_FLOW.md):
//   reject     : pending → rejected
//   accept     : pending → awaiting_payment  (+ email tagihan)
//   mark_paid  : awaiting_payment → in_progress (+ BUAT niche is_active=false, exclusive_to tenant) (+ email bayar diterima)
//   deliver    : in_progress → delivered (+ aktifkan niche is_active=true + delivery_note) (+ email serah-terima)
// Email = antre ke email_outbox (dispatcher Python yang kirim). Pembayaran live (Midtrans) = §7 doc, MENYUSUL —
//   "mark_paid" = jalur concierge interim (admin tandai lunas) sampai checkout Midtrans disambung.

export async function GET() {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const admin = createAdminClient();
  const { data: reqs, error } = await admin.from("niche_requests").select("*").order("created_at", { ascending: false });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  const emails: Record<string, string> = {};
  try {
    const { data: us } = await admin.auth.admin.listUsers();
    (us?.users ?? []).forEach((u) => { if (u.id && u.email) emails[u.id] = u.email; });
  } catch { /* best-effort */ }
  return NextResponse.json({ requests: (reqs ?? []).map((r) => ({ ...r, tenant_email: emails[r.tenant_id] ?? null })) });
}

const rupiah = (n: number) => `Rp ${Number(n).toLocaleString("id-ID")}`;

export async function POST(req: Request) {
  const g = await requireSuperAdmin();
  if (g.error) return g.error;
  const b = await req.json().catch(() => ({}));
  const admin = createAdminClient();
  const { data: r } = await admin.from("niche_requests").select("*").eq("request_id", b.request_id).single();
  if (!r) return NextResponse.json({ error: "request tak ditemukan" }, { status: 404 });
  const now = new Date().toISOString();
  const action = String(b.action || "");
  const typeLabel = r.request_type === "private" ? "Privat permanen" : "Publik (90 hari eksklusif)";

  const enqueue = (subject: string, body: string) =>
    admin.from("email_outbox").insert({ tenant_id: r.tenant_id, subject, body });
  const audit = (act: string, detail: Record<string, unknown>) =>
    admin.from("admin_audit").insert({ admin_uid: g.user.id, action: act, target_tenant: r.tenant_id, detail });

  // ── Tolak ──
  if (action === "reject") {
    await admin.from("niche_requests").update({ status: "rejected", admin_note: b.admin_note ?? null, updated_at: now }).eq("request_id", r.request_id);
    await audit("niche_request.reject", { request_id: r.request_id });
    return NextResponse.json({ ok: true });
  }

  // ── Terima untuk diproses → menunggu pembayaran (+ tagihan) ──
  if (action === "accept") {
    if (r.status !== "pending") return NextResponse.json({ error: `status saat ini '${r.status}', bukan 'pending'` }, { status: 409 });
    await admin.from("niche_requests").update({ status: "awaiting_payment", admin_note: b.admin_note ?? null, updated_at: now }).eq("request_id", r.request_id);
    const { data: pc } = await admin.from("pricing_config").select("value_idr").eq("key", r.price_key).maybeSingle();
    const amt = pc?.value_idr ? rupiah(pc.value_idr as number) : "(lihat aplikasi)";
    await enqueue(`Tagihan niche custom — ${r.title}`,
      `Halo,\n\nPesanan niche custom "${r.title}" (${typeLabel}) telah kami terima untuk diproses.\n` +
      `Tagihan: ${amt}.\nTim akan menghubungi Anda untuk pembayaran. Setelah lunas, niche mulai kami kerjakan.\n\n— Tim MesinViral`);
    await audit("niche_request.accept", { request_id: r.request_id });
    return NextResponse.json({ ok: true });
  }

  // ── Tandai lunas (interim concierge) → in_progress + BUAT niche (belum aktif) (+ konfirmasi bayar) ──
  if (action === "mark_paid") {
    if (r.status !== "awaiting_payment") return NextResponse.json({ error: `status saat ini '${r.status}', bukan 'awaiting_payment'` }, { status: 409 });
    const niche_id = String(b.niche_id ?? "").trim();
    if (!/^[a-z0-9_]+$/.test(niche_id)) return NextResponse.json({ error: "niche_id slug invalid (a-z0-9_)" }, { status: 400 });
    const exclusive_until = r.request_type === "public_90d" ? new Date(Date.now() + 90 * 864e5).toISOString() : null;
    const { error: ne } = await admin.from("niches").insert({
      niche_id, name: r.title, is_active: false, is_base: false,
      access_type: "private", exclusive_to: r.tenant_id, exclusive_until, origin: "request",
    });
    if (ne) return NextResponse.json({ error: `buat niche gagal: ${ne.message}` }, { status: 500 });
    await admin.from("niche_requests").update({ status: "in_progress", niche_id, paid_at: now, updated_at: now }).eq("request_id", r.request_id);
    await enqueue(`Pembayaran diterima — ${r.title}`,
      `Halo,\n\nPembayaran untuk niche custom "${r.title}" sudah kami terima. Tim mulai menyiapkan niche Anda sekarang.\n` +
      `Anda akan kami beri tahu via email saat niche siap untuk dievaluasi.\n\n— Tim MesinViral`);
    await audit("niche_request.mark_paid", { request_id: r.request_id, niche_id });
    return NextResponse.json({ ok: true, niche_id });
  }

  // ── Serahkan → delivered + aktifkan niche + masa evaluasi (+ serah-terima) ──
  if (action === "deliver") {
    if (r.status !== "in_progress") return NextResponse.json({ error: `status saat ini '${r.status}', bukan 'in_progress'` }, { status: 409 });
    if (!r.niche_id) return NextResponse.json({ error: "niche belum dibuat (mark_paid dulu)" }, { status: 400 });
    const { error: ue } = await admin.from("niches").update({ is_active: true }).eq("niche_id", r.niche_id);
    if (ue) return NextResponse.json({ error: `aktivasi niche gagal: ${ue.message}` }, { status: 500 });
    const delivery_note = (b.delivery_note ?? "").toString().trim() || null;
    await admin.from("niche_requests").update({ status: "delivered", delivered_at: now, delivery_note, reminder_sent_at: null, updated_at: now }).eq("request_id", r.request_id);
    const { data: cfg } = await admin.from("app_config").select("value").eq("key", "niche_eval_window_days").maybeSingle();
    const days = (cfg?.value as number) ?? 3;
    await enqueue(`Niche custom siap — ${r.title}`,
      `Halo,\n\nNiche custom "${r.title}" sudah JADI dan aktif di akun Anda.\n` +
      (delivery_note ? `Video contoh / catatan tim: ${delivery_note}\n` : "") +
      `Silakan cek di menu Niche (Pustaka Niche). Anda punya ${days} hari untuk evaluasi:\n` +
      `• Jika sudah sesuai → tekan "Terima & Selesaikan".\n• Bila perlu perbaikan → tekan "Minta perbaikan".\n` +
      `Lewat ${days} hari tanpa masukan, pesanan otomatis dianggap selesai.\n\n— Tim MesinViral`);
    await audit("niche_request.deliver", { request_id: r.request_id, niche_id: r.niche_id });
    return NextResponse.json({ ok: true });
  }

  return NextResponse.json({ error: "action invalid" }, { status: 400 });
}
