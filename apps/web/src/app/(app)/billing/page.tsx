"use client";

import { useState, useEffect } from "react";
import { Zap, CreditCard, FileText, Plus, X, DollarSign, Download, Mic, Wand2, HelpCircle, Gauge, ShieldCheck } from "lucide-react";
import "./billing.css";

// D13 Billing — port dari design-source/Billing.html (Hybrid). Sidebar "Tagihan".
// Pricing = {{pricing.*}} placeholder (no-hardcode); Xendit→Midtrans (keputusan final).
// Mock deterministik (SSR-safe); nol wiring Supabase. Webhook Midtrans = Phase 8.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const INV: [string, string, string][] = [
  ["INV-2026-06", "25 Jun 2026", "Rp 548K"], ["INV-2026-05", "25 Mei 2026", "Rp 548K"],
  ["INV-2026-04", "25 Apr 2026", "Rp 349K"], ["INV-2026-03", "25 Mar 2026", "Rp 349K"],
  ["INV-2026-02", "25 Feb 2026", "Rp 349K"], ["INV-2026-01", "25 Jan 2026", "Rp 149K"],
];

const CAT: { Icon: typeof Wand2; name: string; key: string; ex: string; descId: string; descEn: string }[] = [
  { Icon: Wand2, name: "Niche Pack", key: "{{pricing.custom_niche_public_90d}}", ex: "≈ Rp 299K", descId: "Niche kustom sesuai brief, 3–5 hari.", descEn: "Custom niche to your brief, 3–5 days." },
  { Icon: HelpCircle, name: "Concierge Setup", key: "{{pricing.concierge_setup}}", ex: "≈ Rp 499K", descId: "Tim kami setup channel & API untuk Anda.", descEn: "We set up your channel & APIs for you." },
  { Icon: Gauge, name: "Channel Audit", key: "{{pricing.niche_audit}}", ex: "≈ Rp 349K", descId: "Analisis mendalam + rekomendasi growth.", descEn: "Deep analysis + growth recommendations." },
  { Icon: ShieldCheck, name: "Extra Compliance", key: "—", ex: "≈ Rp 99K/bln", descId: "Monitoring compliance lebih ketat.", descEn: "Stricter compliance monitoring." },
];

export default function BillingPage() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <div className="bl-head">
        <h1>Billing</h1>
        <div className="sub"><Bi id="Kelola langganan, pembayaran, dan invoice" en="Manage subscription, payment, and invoices" /></div>
      </div>

      <div className="bl-grid2">
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* current plan */}
          <div className="plan-card">
            <div className="plan-top">
              <div>
                <div className="plan-name">Pro <span className="badge badge-brand">Most Popular</span></div>
                <div className="plan-price"><span className="dyn">{"{{pricing.plan_pro}}"}</span><small>/bln</small></div>
                <div className="price-ex">contoh nilai: Rp 349K · diperbarui dari pricing_config</div>
                <div className="muted" style={{ fontSize: "var(--text-sm)", marginTop: "0.5rem" }}><Bi id="Diperbarui otomatis 25 Juni 2026" en="Auto-renews June 25, 2026" /></div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <button className="btn btn-default"><Zap size={15} /> <Bi id="Upgrade ke Business" en="Upgrade to Business" /></button>
                <button className="btn btn-ghost btn-sm"><Bi id="Downgrade paket" en="Downgrade plan" /></button>
              </div>
            </div>
            <div className="usage-row">
              <div className="usage"><div className="top"><span className="secondary"><Bi id="Penggunaan channel" en="Channel usage" /></span><span className="v">1 / 3</span></div><div className="progress"><span style={{ width: "33%" }} /></div></div>
              <div className="usage"><div className="top"><span className="secondary"><Bi id="Video bulan ini" en="Videos this month" /></span><span className="v">45 / 900</span></div><div className="progress"><span style={{ width: "5%" }} /></div></div>
            </div>
          </div>

          {/* payment method */}
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "1rem" }}><CreditCard size={16} /> <Bi id="Metode pembayaran" en="Payment method" /></h3>
            <div className="pay-method">
              <span className="pay-logo">Midtrans</span>
              <div style={{ flex: 1 }}><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>BCA Virtual Account</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>•••• 8821 · <Bi id="kedaluwarsa 12/27" en="expires 12/27" /></div></div>
              <button className="btn btn-secondary btn-sm"><Bi id="Perbarui" en="Update" /></button>
            </div>
          </div>

          {/* invoices */}
          <div className="card">
            <div className="card-head"><h3 className="card-title"><FileText size={16} /> <Bi id="Riwayat invoice" en="Invoice history" /></h3><span className="card-sub">12 <Bi id="bulan terakhir" en="months" /></span></div>
            <div style={{ overflowX: "auto" }}><table className="tbl">
              <thead><tr><th>Invoice</th><th>Tanggal</th><th className="num">Jumlah</th><th>Status</th><th></th></tr></thead>
              <tbody>{INV.map(([id, d, amt]) => (
                <tr key={id}><td className="mono" style={{ color: "var(--text-primary)" }}>{id}</td><td className="muted">{d}</td><td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{amt}</b></td>
                  <td><span className="badge badge-success"><span className="dot" /><Bi id="Lunas" en="Paid" /></span></td>
                  <td><button className="btn btn-ghost btn-sm"><Download size={14} /> PDF</button></td></tr>
              ))}</tbody>
            </table></div>
          </div>
        </div>

        {/* right rail */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card card-pad">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.875rem" }}><h3 className="card-title"><Plus size={16} /> <Bi id="Add-ons aktif" en="Active add-ons" /></h3><button className="btn btn-secondary btn-sm" onClick={() => setOpen(true)}><Plus size={14} /></button></div>
            <div className="addon-active"><span className="ic"><Mic size={16} /></span><div style={{ flex: 1 }}><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>Voice Pack</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}><span className="mono">{"{{pricing.voice_pack}}"}</span> · <span className="price-ex">≈ Rp 199K</span></div></div><button className="btn btn-ghost btn-icon btn-sm"><X size={14} /></button></div>
            <div className="addon-active"><span className="ic"><Zap size={16} /></span><div style={{ flex: 1 }}><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>Priority Queue</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}><span className="mono">{"{{pricing.priority_queue}}"}</span>/bln · <span className="price-ex">≈ Rp 149K</span></div></div><button className="btn btn-ghost btn-icon btn-sm"><X size={14} /></button></div>
          </div>

          <div className="card card-pad">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.25rem" }}><h3 className="card-title"><DollarSign size={16} /> <Bi id="Biaya AI (BYOK)" en="AI Cost (BYOK)" /></h3><span className="badge badge-outline">BYOK</span></div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.75rem" }}><Bi id="Dibayar langsung ke provider — terpisah dari langganan." en="Paid directly to providers — separate from subscription." /></div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}><span style={{ fontSize: "var(--text-3xl)", fontWeight: 700, letterSpacing: "-0.02em" }}>$112</span><span className="muted" style={{ fontSize: "var(--text-sm)" }}>≈ Rp 1.79JT · bulan ini</span></div>
            <div className="bl-cost-bar"><span style={{ background: "var(--anthropic)", width: "28%" }} /><span style={{ background: "var(--elevenlabs)", width: "34%" }} /><span style={{ background: "var(--openai)", width: "38%" }} /></div>
            <div className="cost-leg">
              <div className="r"><span className="sw" style={{ background: "var(--anthropic)" }} />Anthropic<span className="amt">$31</span></div>
              <div className="r"><span className="sw" style={{ background: "var(--elevenlabs)" }} />ElevenLabs<span className="amt">$38</span></div>
              <div className="r"><span className="sw" style={{ background: "var(--openai)" }} />OpenAI<span className="amt">$43</span></div>
            </div>
            <hr className="hr" style={{ margin: "0.875rem 0 0.75rem" }} />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", marginBottom: 6 }}><span className="muted"><Bi id="Budget bulanan" en="Monthly budget" /></span><span><b>$112</b> <span className="muted">/ $500</span></span></div>
            <div className="progress"><span style={{ width: "22%" }} /></div>
          </div>
        </div>
      </div>

      {/* add-ons drawer */}
      <div className={`scrim${open ? " open" : ""}`} onClick={() => setOpen(false)} />
      <aside className={`drawer${open ? " open" : ""}`}>
        <div className="drawer-head"><h3 className="card-title"><Bi id="Katalog Add-on" en="Add-on catalog" /></h3><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setOpen(false)}><X size={16} /></button></div>
        <div className="drawer-body">
          {CAT.map(({ Icon, name, key, ex, descId, descEn }) => (
            <div className="addon-cat" key={name}><span className="ic"><Icon size={18} /></span><div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{name}</div>
              <div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".25rem 0 .5rem" }}><Bi id={descId} en={descEn} /></div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span><span className="mono" style={{ color: "var(--brand)" }}>{key}</span> <span className="price-ex">{ex}</span></span><button className="btn btn-outline btn-sm"><Bi id="Tambah" en="Add" /></button></div>
            </div></div>
          ))}
        </div>
      </aside>
    </>
  );
}
