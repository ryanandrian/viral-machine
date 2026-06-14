"use client";

import { useState, useEffect } from "react";
import { Download, Search, X, Bell, DollarSign, Pause, User } from "lucide-react";
import "./tenants.css";

// E1 Admin Tenants — port dari design-source/Admin Tenants.html (Hybrid). /admin/tenants.
// Tabel tenant + row-click → drawer detail. Mock deterministik (SSR-safe); nol wiring Supabase.
// Prefix class adm-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const COLORS = ["#1d4ed8", "#9f1239", "#047857", "#7c3aed", "#b45309", "#0891b2", "#be185d"];
type Status = "active" | "trial" | "suspended";
type Tenant = { name: string; email: string; plan: string; status: Status; mrr: string; joined: string; activity: string; av: string; channels: number };
const TENANTS: Tenant[] = [
  { name: "Riko Pratama", email: "riko@misterisamudra.id", plan: "Pro", status: "active", mrr: "Rp 548K", joined: "12 Jan 2026", activity: "2 jam lalu", av: "RP", channels: 3 },
  { name: "Sarah Wibowo", email: "sarah@agensikonten.id", plan: "Business", status: "active", mrr: "Rp 1.2JT", joined: "3 Feb 2026", activity: "15 menit lalu", av: "SW", channels: 8 },
  { name: "Dimas Aryo", email: "dimas@faktamikir.id", plan: "Pro", status: "active", mrr: "Rp 349K", joined: "22 Mar 2026", activity: "1 jam lalu", av: "DA", channels: 2 },
  { name: "Bagus Pratomo", email: "bagus@jejakkelam.id", plan: "Starter", status: "trial", mrr: "Rp 0", joined: "8 Jun 2026", activity: "30 menit lalu", av: "BP", channels: 1 },
  { name: "Lina Hartati", email: "lina@kontenviral.id", plan: "Starter", status: "active", mrr: "Rp 149K", joined: "15 Apr 2026", activity: "3 jam lalu", av: "LH", channels: 1 },
  { name: "Andi Saputra", email: "andi@shortsfactory.id", plan: "Business", status: "suspended", mrr: "Rp 0", joined: "5 Des 2025", activity: "12 hari lalu", av: "AS", channels: 6 },
  { name: "Maya Putri", email: "maya@ceritamaya.id", plan: "Pro", status: "trial", mrr: "Rp 0", joined: "9 Jun 2026", activity: "5 menit lalu", av: "MP", channels: 2 },
  { name: "Rendi Gunawan", email: "rendi@viralhub.id", plan: "Starter", status: "active", mrr: "Rp 149K", joined: "28 Feb 2026", activity: "1 hari lalu", av: "RG", channels: 1 },
];

function StBadge({ s }: { s: Status }) {
  if (s === "active") return <span className="badge badge-success"><span className="dot" />Active</span>;
  if (s === "trial") return <span className="badge badge-info"><span className="dot" />Trial</span>;
  return <span className="badge badge-error"><span className="dot" />Suspended</span>;
}
const FILTERS: [Status | "all", string, string][] = [["all", "Semua", "All"], ["active", "Active", "Active"], ["trial", "Trial", "Trial"], ["suspended", "Suspended", "Suspended"]];

export default function AdminTenantsPage() {
  const [filter, setFilter] = useState<Status | "all">("all");
  const [sel, setSel] = useState<number | null>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSel(null); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const rows = TENANTS.map((t, i) => ({ t, i })).filter(({ t }) => filter === "all" || t.status === filter);
  const t = sel !== null ? TENANTS[sel] : null;
  const c = sel !== null ? COLORS[sel % COLORS.length] : "";

  return (
    <>
      <div className="adm-head">
        <div><h1>Tenants</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Kelola semua akun pelanggan" en="Manage all customer accounts" /></div></div>
        <button className="btn btn-secondary"><Download size={15} /> Export</button>
      </div>

      <div className="adm-kpi-strip">
        <div className="adm-kpic"><div className="l"><Bi id="Total tenant" en="Total tenants" /></div><div className="v">312</div></div>
        <div className="adm-kpic"><div className="l">MRR</div><div className="v">Rp 87JT</div></div>
        <div className="adm-kpic"><div className="l"><Bi id="Trial aktif" en="Active trials" /></div><div className="v">47</div></div>
        <div className="adm-kpic"><div className="l">Churn (30d)</div><div className="v">2.1%</div></div>
      </div>

      <div className="adm-filters">
        <div className="segmented">{FILTERS.map(([k, id, en]) => <button key={k} aria-selected={filter === k} onClick={() => setFilter(k)}><Bi id={id} en={en} /></button>)}</div>
        <div className="adm-selbox"><Search size={14} /> <Bi id="Cari email…" en="Search email…" /></div>
      </div>

      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl adm-tbl">
        <thead><tr><th>Tenant</th><th>Plan</th><th>Status</th><th className="num">MRR</th><th><Bi id="Bergabung" en="Joined" /></th><th><Bi id="Aktivitas" en="Last activity" /></th></tr></thead>
        <tbody>{rows.map(({ t, i }) => (
          <tr key={t.email} onClick={() => setSel(i)}>
            <td><span className="adm-tn-cell"><span className="adm-tn-av" style={{ background: COLORS[i % COLORS.length] }}>{t.av}</span><div><div style={{ color: "var(--text-primary)", fontWeight: 500 }}>{t.name}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{t.email}</div></div></span></td>
            <td><span className={`badge ${t.plan === "Pro" ? "badge-brand" : "badge-default"}`}>{t.plan}</span></td>
            <td><StBadge s={t.status} /></td>
            <td className="num adm-mrr">{t.mrr}</td>
            <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{t.joined}</td>
            <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{t.activity}</td>
          </tr>
        ))}</tbody>
      </table></div></div>

      <div className={`adm-scrim${t ? " open" : ""}`} onClick={() => setSel(null)} />
      <aside className={`adm-drawer${t ? " open" : ""}`}>
        {t && (<>
          <div className="adm-drawer-head">
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <span className="adm-tn-av" style={{ width: 40, height: 40, fontSize: "var(--text-sm)", background: c }}>{t.av}</span>
              <div style={{ flex: 1 }}><div style={{ fontWeight: 600, fontSize: "var(--text-base)" }}>{t.name}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{t.email}</div></div>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button>
            </div>
            <div style={{ marginTop: "0.75rem" }}><StBadge s={t.status} /> <span className={`badge ${t.plan === "Pro" ? "badge-brand" : "badge-default"}`} style={{ marginLeft: "0.375rem" }}>{t.plan}</span></div>
          </div>
          <div className="adm-drawer-body">
            <div>
              <div className="adm-sec-label"><Bi id="Ringkasan" en="Summary" /></div>
              <div className="adm-kv"><span className="k">Plan</span><span className="v">{t.plan}</span></div>
              <div className="adm-kv"><span className="k">MRR</span><span className="v">{t.mrr}</span></div>
              <div className="adm-kv"><span className="k">Channels</span><span className="v">{t.channels}</span></div>
              <div className="adm-kv"><span className="k"><Bi id="Bergabung" en="Joined" /></span><span className="v">{t.joined}</span></div>
            </div>
            <div>
              <div className="adm-sec-label"><Bi id="Run terbaru" en="Recent runs" /></div>
              <div className="adm-mini-list">
                <div className="row"><span className="badge badge-success"><span className="dot" />OK</span><span>Kapal Hilang di Segitiga Bermuda</span><span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-xs)" }}>2j</span></div>
                <div className="row"><span className="badge badge-success"><span className="dot" />OK</span><span>Suara Aneh Palung Mariana</span><span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-xs)" }}>5j</span></div>
                <div className="row"><span className="badge badge-error"><span className="dot" />Fail</span><span>Pulau Hantu di Peta</span><span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-xs)" }}>6j</span></div>
              </div>
            </div>
            <div>
              <div className="adm-sec-label"><Bi id="Riwayat billing" en="Billing history" /></div>
              <div className="adm-mini-list">
                <div className="row"><span>INV-2026-06</span><span className="muted" style={{ marginLeft: "auto" }}>Rp 548K · <span style={{ color: "var(--success)" }}>Lunas</span></span></div>
                <div className="row"><span>INV-2026-05</span><span className="muted" style={{ marginLeft: "auto" }}>Rp 548K · <span style={{ color: "var(--success)" }}>Lunas</span></span></div>
              </div>
            </div>
            <div>
              <div className="adm-sec-label">Support</div>
              <div className="adm-mini-list"><div className="row"><span className="badge badge-warning"><span className="dot" />Open</span><span><Bi id="Pertanyaan billing" en="Billing question" /></span></div></div>
            </div>
          </div>
          <div className="adm-drawer-foot">
            <button className="btn btn-secondary btn-sm"><Bell size={14} /> <Bi id="Kirim email" en="Send email" /></button>
            <button className="btn btn-secondary btn-sm"><DollarSign size={14} /> <Bi id="Tambah kredit" en="Add credit" /></button>
            <button className="btn btn-secondary btn-sm" style={{ color: "var(--warning)" }}><Pause size={14} /> Suspend</button>
            <button className="btn btn-default btn-sm"><User size={14} /> Impersonate</button>
          </div>
        </>)}
      </aside>
    </>
  );
}
