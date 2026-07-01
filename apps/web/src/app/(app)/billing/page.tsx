"use client";

import { useCallback, useEffect, useState } from "react";
import { Zap, CreditCard, FileText, Plus, X, DollarSign, ShieldCheck } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/page-header";
import "./billing.css";

// D13 Billing — Phase 9.3 (wired Supabase v2, anon + RLS). Plan/status/usage = NYATA
// (tenant_configs + channels + production_runs); HARGA dari pricing_config (no-hardcode);
// invoice dari payments (RLS); add-on katalog dari pricing_config. Comp account (is_developer
// / discount≥100) ditandai gratis. Snap checkout = GATE cutover (butuh backend webhook_app).
// BYOK cost = placeholder (belum ada sumber metadata produksi).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
function fmtIDR(n: number | null | undefined) { return n == null ? "—" : `Rp ${Number(n).toLocaleString("id-ID")}`; }
const PLAN_LABEL: Record<string, string> = { trial: "Trial", starter: "Starter", pro: "Pro", business: "Business" };

type Pricing = { key: string; value_idr: number; description: string; category: string };
type Payment = { order_id: string; plan_type: string | null; gross_amount: number | null; currency: string | null; status: string | null; created_at: string };

export default function BillingPage() {
  const [supabase] = useState(() => createClient());
  const [drawer, setDrawer] = useState<null | "plan" | "addon">(null);
  const [paying, setPaying] = useState<string | null>(null);
  const [payErr, setPayErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState<{ plan_type: string; subscription_status: string; current_period_end: string | null; is_developer: boolean; discount_pct: number } | null>(null);
  const [prices, setPrices] = useState<Record<string, Pricing>>({});
  const [addons, setAddons] = useState<Pricing[]>([]);
  const [maxCh, setMaxCh] = useState<number | null>(null);
  const [maxVid, setMaxVid] = useState<number | null>(null);
  const [chUsed, setChUsed] = useState(0);
  const [vidMonth, setVidMonth] = useState(0);
  const [invoices, setInvoices] = useState<Payment[]>([]);

  const load = useCallback(async () => {
    const monthStart = (() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1).toISOString(); })();
    const [{ data: tc }, { data: pc }, { count: chCount }, { count: vidCount }, { data: pay }] = await Promise.all([
      supabase.from("tenant_configs").select("plan_type,subscription_status,current_period_end,is_developer,discount_pct").maybeSingle(),
      supabase.from("pricing_config").select("key,value_idr,description,category").eq("active", true),
      supabase.from("channels").select("id", { count: "exact", head: true }),
      supabase.from("production_runs").select("id", { count: "exact", head: true }).gte("created_at", monthStart),
      supabase.from("payments").select("order_id,plan_type,gross_amount,currency,status,created_at").order("created_at", { ascending: false }).limit(12),
    ]);
    const t = tc as typeof plan; setPlan(t);
    const pmap: Record<string, Pricing> = {}; const ad: Pricing[] = [];
    (pc as Pricing[] ?? []).forEach((p) => { pmap[p.key] = p; if (p.category === "add_on" || p.category === "one_time") ad.push(p); });
    setPrices(pmap); setAddons(ad);
    setChUsed(chCount ?? 0); setVidMonth(vidCount ?? 0);
    setInvoices((pay as Payment[]) ?? []);
    if (t?.plan_type) {
      const { data: pl } = await supabase.from("plan_limits").select("max_channels,max_videos_per_day").eq("plan_type", t.plan_type).maybeSingle();
      const l = pl as { max_channels?: number; max_videos_per_day?: number } | null;
      setMaxCh(l?.max_channels ?? null); setMaxVid(l?.max_videos_per_day ?? null);
    }
    setLoading(false);
  }, [supabase]);

  useEffect(() => {
    load();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setDrawer(null); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [load]);

  async function checkout(plan_type: string) {
    setPayErr(null); setPaying(plan_type);
    try {
      const res = await fetch("/api/billing/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plan_type }) });
      const j = await res.json().catch(() => ({}));
      if (res.ok && j.redirect_url) { window.location.href = j.redirect_url; return; }
      setPayErr(j.error || "Gagal memulai pembayaran."); setPaying(null);
    } catch { setPayErr("Gagal terhubung. Coba lagi."); setPaying(null); }
  }

  const comp = !!plan && (plan.is_developer || (plan.discount_pct ?? 0) >= 100);
  const planName = plan ? (PLAN_LABEL[plan.plan_type] ?? plan.plan_type) : "—";
  const planPrice = plan ? prices[`plan_${plan.plan_type}`]?.value_idr : null;
  const monthCap = maxVid != null ? maxVid * 30 : null;

  return (
    <>
      <PageHeader icon={CreditCard} title="Billing" subtitle={<Bi id="Kelola langganan, pembayaran, dan invoice" en="Manage subscription, payment, and invoices" />} />

      {loading ? <div className="muted" style={{ padding: "2rem" }}><Bi id="Memuat…" en="Loading…" /></div> : (
      <div className="bl-grid2">
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* current plan */}
          <div className="plan-card">
            <div className="plan-top">
              <div>
                <div className="plan-name">{planName} {comp ? <span className="badge badge-success">Comp · Developer</span> : <span className={`badge ${plan?.subscription_status === "active" ? "badge-success" : "badge-warning"}`}>{plan?.subscription_status}</span>}</div>
                {comp
                  ? <div className="muted" style={{ fontSize: "var(--text-sm)", marginTop: "0.5rem" }}><Bi id="Akun komplimen / developer — gratis selamanya, tanpa tagihan." en="Complimentary / developer account — free forever, no billing." /></div>
                  : <>
                      <div className="plan-price">{fmtIDR(planPrice)}<small>/bln</small></div>
                      <div className="muted" style={{ fontSize: "var(--text-sm)", marginTop: "0.5rem" }}>{plan?.current_period_end ? <>Periode berakhir {new Date(plan.current_period_end).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}</> : <Bi id="Tidak ada periode aktif" en="No active period" />}</div>
                    </>}
              </div>
              {!comp && (
                <button className="btn btn-default" onClick={() => setDrawer("plan")}><Zap size={15} /> <Bi id="Ubah paket" en="Change plan" /></button>
              )}
            </div>
            <div className="usage-row">
              <div className="usage"><div className="top"><span className="secondary"><Bi id="Penggunaan channel" en="Channel usage" /></span><span className="v">{chUsed} / {maxCh ?? "—"}</span></div><div className="progress"><span style={{ width: `${maxCh ? Math.min(100, (chUsed / maxCh) * 100) : 0}%` }} /></div></div>
              <div className="usage"><div className="top"><span className="secondary"><Bi id="Video bulan ini" en="Videos this month" /></span><span className="v">{vidMonth} / {monthCap ?? "—"}</span></div><div className="progress"><span style={{ width: `${monthCap ? Math.min(100, (vidMonth / monthCap) * 100) : 0}%` }} /></div></div>
            </div>
          </div>

          {/* payment method */}
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "1rem" }}><CreditCard size={16} /> <Bi id="Metode pembayaran" en="Payment method" /></h3>
            {comp
              ? <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Tidak diperlukan — akun gratis." en="Not required — free account." /></div>
              : <div className="pay-method">
                  <span className="pay-logo">Midtrans</span>
                  <div style={{ flex: 1 }}><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}><Bi id="Belum ada metode tersimpan" en="No method saved yet" /></div><div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Dipilih saat checkout (VA / e-wallet / kartu / QRIS)" en="Chosen at checkout (VA / e-wallet / card / QRIS)" /></div></div>
                </div>}
          </div>

          {/* invoices */}
          <div className="card">
            <div className="card-head"><h3 className="card-title"><FileText size={16} /> <Bi id="Riwayat invoice" en="Invoice history" /></h3></div>
            {invoices.length === 0
              ? <div className="card-body" style={{ padding: "1.5rem", textAlign: "center" }}><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Belum ada invoice." en="No invoices yet." /></span></div>
              : <div style={{ overflowX: "auto" }}><table className="tbl">
                  <thead><tr><th>Order</th><th>Tanggal</th><th className="num">Jumlah</th><th>Status</th></tr></thead>
                  <tbody>{invoices.map((p) => (
                    <tr key={p.order_id}><td className="mono" style={{ color: "var(--text-primary)" }}>{p.order_id}</td><td className="muted">{new Date(p.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}</td><td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{fmtIDR(p.gross_amount)}</b></td>
                      <td><span className={`badge ${(p.status || "").includes("settle") || (p.status || "").includes("capture") || p.status === "paid" ? "badge-success" : "badge-default"}`}><span className="dot" />{p.status}</span></td></tr>
                  ))}</tbody>
                </table></div>}
          </div>
        </div>

        {/* right rail */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card card-pad">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.875rem" }}><h3 className="card-title"><Plus size={16} /> <Bi id="Add-ons" en="Add-ons" /></h3><button className="btn btn-secondary btn-sm" onClick={() => setDrawer("addon")}><Plus size={14} /></button></div>
            <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Belum ada add-on aktif. Lihat katalog →" en="No active add-ons. Browse catalog →" /></div>
          </div>

          <div className="card card-pad">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.25rem" }}><h3 className="card-title"><DollarSign size={16} /> <Bi id="Biaya AI (BYOK)" en="AI Cost (BYOK)" /></h3><span className="badge badge-outline">BYOK</span></div>
            <p className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.75rem" }}><Bi id="Dibayar langsung ke provider — terpisah dari langganan. Rincian tampil setelah worker mencatat metadata produksi." en="Paid directly to providers — separate from subscription. Breakdown appears once the worker records production metadata." /></p>
          </div>
        </div>
      </div>
      )}

      {/* drawer: pilih paket (Ubah paket) ATAU katalog add-on — SATU drawer, dua mode (reuse) */}
      <div className={`scrim${drawer ? " open" : ""}`} onClick={() => setDrawer(null)} />
      <aside className={`drawer${drawer ? " open" : ""}`}>
        <div className="drawer-head"><h3 className="card-title">{drawer === "plan" ? <Bi id="Pilih paket" en="Choose a plan" /> : <Bi id="Katalog Add-on" en="Add-on catalog" />}</h3><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setDrawer(null)}><X size={16} /></button></div>
        <div className="drawer-body">
          {payErr && <div style={{ color: "var(--danger, #ef4444)", fontSize: "var(--text-sm)", marginBottom: ".75rem" }}>{payErr}</div>}
          {drawer === "plan" ? (
            <>
              <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Pembayaran aman via Midtrans (VA / e-wallet / kartu / QRIS). Langganan berlaku 30 hari." en="Secure payment via Midtrans (VA / e-wallet / card / QRIS). Subscription lasts 30 days." /></p>
              {["starter", "pro", "business"].map((tier) => {
                const p = prices[`plan_${tier}`]; if (!p) return null;
                const isCurrent = plan?.plan_type === tier && plan?.subscription_status === "active";
                return (
                  <div className="addon-cat" key={tier}><span className="ic"><Zap size={18} /></span><div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{PLAN_LABEL[tier]} {isCurrent && <span className="badge badge-success"><Bi id="Aktif" en="Active" /></span>}</div>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: ".5rem" }}>
                      <span style={{ color: "var(--brand)", fontWeight: 600 }}>{fmtIDR(p.value_idr)}<small>/bln</small></span>
                      <button className="btn btn-default btn-sm" disabled={paying !== null} onClick={() => checkout(tier)}>{paying === tier ? "…" : <Bi id="Pilih & bayar" en="Choose & pay" />}</button>
                    </div>
                  </div></div>
                );
              })}
            </>
          ) : (
            addons.length === 0 ? <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Belum ada add-on di katalog." en="No add-ons in catalog." /></div>
            : addons.map((a) => (
              <div className="addon-cat" key={a.key}><span className="ic"><ShieldCheck size={18} /></span><div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{a.description || a.key}</div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: ".5rem" }}><span style={{ color: "var(--brand)", fontWeight: 600 }}>{fmtIDR(a.value_idr)}</span><a className="btn btn-outline btn-sm" href="/niches"><Bi id="Pesan di Pustaka Niche" en="Order in Niche Library" /></a></div>
              </div></div>
            ))
          )}
        </div>
      </aside>
    </>
  );
}
