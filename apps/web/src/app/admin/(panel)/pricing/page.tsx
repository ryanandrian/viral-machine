"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, Download, Plus, Command, Clock, RefreshCw, Shield, X, ChevronDown, Info, AlertTriangle, FileText, CheckCircle, Calendar } from "lucide-react";
import "./pricing.css";

// E5 Admin Pricing Config — port dari design-source/Admin Pricing.html (Hybrid). /admin/pricing.
// Single source of truth pricing_config (di sini angka MEMANG ditampilkan/diedit — editornya).
// Tabel inline-edit + quick-card + API panel + drawer 4-tab + toast. Mock; nol wiring Supabase. Prefix pr-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Cat = "Subscription" | "Add-on" | "One-time" | "Discount";
const ROWS: [string, string, Cat, string, string, boolean][] = [
  ["plan_starter", "Langganan Starter / bulan", "Subscription", "149.000", "931", true],
  ["plan_pro", "Langganan Pro / bulan", "Subscription", "349.000", "2181", true],
  ["plan_business", "Langganan Business / bulan", "Subscription", "699.000", "4369", true],
  ["custom_niche_public_90d", "Niche custom public (90d exclusive)", "Add-on", "299.000", "1869", true],
  ["custom_niche_private", "Niche custom permanen private", "Add-on", "1.499.000", "9369", true],
  ["voice_pack", "Voice pack premium", "Add-on", "199.000", "1244", true],
  ["niche_audit", "Channel & niche audit", "One-time", "349.000", "2181", true],
  ["concierge_setup", "Concierge setup", "One-time", "499.000", "3119", true],
  ["priority_queue", "Priority queue / bulan", "Add-on", "149.000", "931", true],
  ["annual_prepay_discount", "Diskon bayar tahunan", "Discount", "20%", "—", true],
  ["first_month_promo", "Promo bulan pertama", "Discount", "50%", "—", false],
];
const CAT_BADGE: Record<Cat, string> = { Subscription: "badge-brand", "Add-on": "badge-info", "One-time": "badge-default", Discount: "badge-success" };
const FILTERS: [Cat | "all", string][] = [["all", "All"], ["Subscription", "Subscription"], ["Add-on", "Add-on"], ["One-time", "One-time"], ["Discount", "Discount"]];
const DTABS = ["Pricing", "Schedule", "Audit Log", "Where Used"];

export default function AdminPricingPage() {
  const [filter, setFilter] = useState<Cat | "all">("all");
  const [sel, setSel] = useState<string | null>(null);
  const [dtab, setDtab] = useState(0);
  const [toast, setToast] = useState(false);
  const tt = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showToast = () => { setToast(true); if (tt.current) clearTimeout(tt.current); tt.current = setTimeout(() => setToast(false), 2200); };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSel(null); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  const rows = ROWS.filter((r) => filter === "all" || r[2] === filter);
  const r = sel ? ROWS.find((x) => x[0] === sel) : null;

  return (
    <>
      <div className="pr-head">
        <div>
          <h1><Bi id="Konfigurasi Harga" en="Pricing Configuration" /></h1>
          <div className="pr-stat-line"><span><b>25</b> entries</span><span><b>23</b> active</span><span><Bi id="Perubahan terakhir" en="Last change" /> <b>2 jam lalu</b> · admin@mesinviral</span></div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-secondary"><Upload size={15} /> Import CSV</button>
          <button className="btn btn-secondary"><Download size={15} /> Export</button>
          <button className="btn btn-default"><Plus size={15} /> <Bi id="Entry Baru" en="New Entry" /></button>
        </div>
      </div>

      <div className="pr-filters"><div className="segmented">{FILTERS.map(([k, l]) => <button key={k} aria-selected={filter === k} onClick={() => setFilter(k)}>{l}</button>)}</div></div>

      <div className="pr-layout">
        <div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl pr-tbl">
            <thead><tr><th>Key</th><th><Bi id="Deskripsi" en="Description" /></th><th>Cat</th><th className="num">IDR</th><th className="num">USD¢</th><th>Active</th></tr></thead>
            <tbody>{rows.map((row) => (
              <tr key={row[0]} onClick={() => { setSel(row[0]); setDtab(0); }}>
                <td className="key">{row[0]}</td><td className="muted" style={{ fontSize: "var(--text-xs)" }}>{row[1]}</td>
                <td><span className={`badge ${CAT_BADGE[row[2]]}`} style={{ fontSize: "0.625rem" }}>{row[2]}</span></td>
                <td className="num"><span className="pr-val-edit" contentEditable suppressContentEditableWarning onClick={(e) => e.stopPropagation()} onBlur={showToast}>{row[3]}</span></td>
                <td className="num"><span className="pr-val-edit" contentEditable suppressContentEditableWarning onClick={(e) => e.stopPropagation()} onBlur={showToast}>{row[4]}</span></td>
                <td><label className="switch" onClick={(e) => e.stopPropagation()}><input type="checkbox" defaultChecked={row[5]} /><span className="track" /><span className="thumb" /></label></td>
              </tr>
            ))}</tbody>
          </table></div></div>

          <h3 style={{ fontSize: "var(--text-lg)", fontWeight: 600, margin: "1.5rem 0 1rem" }}><Bi id="Edit cepat" en="Quick edit" /></h3>
          <div className="pr-quick-card">
            <h3><Bi id="Tier langganan" en="Subscription tiers" /></h3>
            <div className="pr-qrow"><span className="nm mono">plan_starter</span><input className="pr-val-edit" defaultValue="Rp 149.000" /><input className="pr-val-edit" defaultValue="$9.31" /></div>
            <div className="pr-qrow"><span className="nm mono">plan_pro</span><input className="pr-val-edit" defaultValue="Rp 349.000" /><input className="pr-val-edit" defaultValue="$21.81" /></div>
            <div className="pr-qrow"><span className="nm mono">plan_business</span><input className="pr-val-edit" defaultValue="Rp 699.000" /><input className="pr-val-edit" defaultValue="$43.69" /></div>
            <button className="btn btn-default btn-sm" style={{ marginTop: "0.75rem" }} onClick={showToast}><Bi id="Simpan semua" en="Save all" /></button>
          </div>
        </div>

        <aside className="pr-api-panel">
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Command size={15} /> API</h3>
            <div className="pr-api-doc">{`GET /api/pricing\n\n{\n  "plan_pro": {\n    "idr": 349000,\n    "usd_cents": 2181\n  },\n  ...\n}`}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.75rem", lineHeight: 1.6 }}><Clock size={12} style={{ verticalAlign: -2 }} /> <Bi id="Cache 5 menit · invalidate saat update" en="Cached 5 min · invalidate on update" /></div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "var(--text-xs)", color: "var(--success)", marginTop: "0.5rem" }}><RefreshCw size={12} /> <Bi id="Cache di-flush 14:23" en="Cache flushed 14:23" /></div>
          </div>
          <div className="card card-pad" style={{ marginTop: "1rem" }}>
            <h3 className="card-title" style={{ marginBottom: "0.5rem" }}><Shield size={15} /> RBAC</h3>
            <p className="muted" style={{ fontSize: "var(--text-xs)", lineHeight: 1.6, margin: 0 }}><Bi id="Hanya Super Admin yang bisa edit. Audit log terlihat oleh semua admin." en="Only Super Admin can edit. Audit log visible to all admins." /></p>
          </div>
        </aside>
      </div>

      <div className={`pr-scrim${r ? " open" : ""}`} onClick={() => setSel(null)} />
      <aside className={`pr-drawer${r ? " open" : ""}`}>
        {r && (<>
          <div className="pr-drawer-head"><div><div className="mono" style={{ fontWeight: 600 }}>{r[0]}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{r[1]}</div></div><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button></div>
          <div className="pr-drawer-tabs">{DTABS.map((l, i) => <button key={l} className={`pr-dtab${dtab === i ? " active" : ""}`} onClick={() => setDtab(i)}>{l}</button>)}</div>
          <div className="pr-dpanel">
            {dtab === 0 && <>
              <div style={{ marginBottom: "1rem" }}><label className="label">Key</label><input className="input input-mono" value={r[0]} disabled /></div>
              <div style={{ marginBottom: "1rem" }}><label className="label">Description</label><input className="input" defaultValue={r[1]} /></div>
              <div style={{ marginBottom: "1rem" }}><label className="label">Category</label><div className="selbox" style={{ display: "inline-flex", alignItems: "center", gap: ".5rem", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", padding: "0 .625rem", height: "2.125rem", fontSize: "var(--text-sm)", width: "fit-content", cursor: "pointer" }}>{r[2]} <ChevronDown size={14} /></div></div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}><div><label className="label">Value IDR</label><input className="input input-mono" defaultValue={r[3].replace(/\./g, "")} /></div><div><label className="label">Value USD cents</label><input className="input input-mono" defaultValue={r[4]} /></div></div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.875rem", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}><Info size={13} /> <Bi id="Kurs 16.000 IDR/USD" en="Rate 16,000 IDR/USD" /></div>
              <button className="btn btn-secondary btn-sm" style={{ marginTop: "0.5rem" }}><Bi id="Gunakan konversi otomatis" en="Use auto conversion" /></button>
              <div className="pr-impact"><span style={{ color: "var(--warning)", flex: "none" }}><AlertTriangle size={16} /></span><div><Bi id="Perubahan ini akan memengaruhi 47 tenant aktif. Konfirmasi sebelum aktivasi." en="This change will affect 47 active tenants. Confirm before activation." /></div></div>
            </>}
            {dtab === 1 && <>
              <div style={{ marginBottom: "1rem" }}><label className="label">Effective from</label><input className="input" defaultValue="2026-06-11 00:00" /></div>
              <div style={{ marginBottom: "1rem" }}><label className="label">Effective until</label><input className="input" placeholder="— (tanpa batas)" /></div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}><span style={{ fontSize: "var(--text-sm)" }}>Active</span><label className="switch"><input type="checkbox" defaultChecked /><span className="track" /><span className="thumb" /></label></div>
              <button className="btn btn-secondary btn-sm"><Calendar size={14} /> <Bi id="Jadwalkan bulan depan" en="Schedule for next month" /></button>
            </>}
            {dtab === 2 && [["Rp 329.000 → Rp 349.000", "15 Mei 2026"], ["Rp 299.000 → Rp 329.000", "2 Mar 2026"]].map(([ch, when]) => (
              <div key={ch} style={{ padding: "0.625rem 0", borderBottom: "1px solid var(--border-subtle)" }}><div className="mono" style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>{ch}</div><div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 2 }}>admin@mesinviral · {when} · <a href="#" style={{ color: "var(--brand)", textDecoration: "none" }}>Rollback</a></div></div>
            ))}
            {dtab === 3 && <>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.875rem" }}><Bi id="Layar yang me-reference key ini:" en="Screens referencing this key:" /></div>
              {["A2 Pricing", "C1 Onboarding", "D13 Billing", "D18 Niches"].map((s) => (<div key={s} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", padding: "0.4375rem 0", borderBottom: "1px solid var(--border-subtle)" }}><FileText size={14} /> {s}</div>))}
            </>}
          </div>
          <div style={{ padding: "1rem 1.25rem", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}><button className="btn btn-ghost" onClick={() => setSel(null)}><Bi id="Batal" en="Cancel" /></button><button className="btn btn-default" onClick={() => { setSel(null); showToast(); }}><Bi id="Simpan perubahan" en="Save changes" /></button></div>
        </>)}
      </aside>

      <div className={`pr-save-toast${toast ? " show" : ""}`}><span style={{ color: "var(--success)" }}><CheckCircle size={16} /></span> <Bi id="Tersimpan · cache di-flush" en="Saved · cache flushed" /></div>
    </>
  );
}
