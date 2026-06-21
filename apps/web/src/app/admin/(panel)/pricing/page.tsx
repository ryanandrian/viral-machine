"use client";

import { useState, useEffect, useCallback } from "react";
import { Command, Clock, Shield, X, Info, AlertTriangle, FileText, CheckCircle, RotateCcw } from "lucide-react";
import "./pricing.css";

// E5 Admin Pricing (Phase 10.2) — SUMBER HARGA seluruh sistem. DATA NYATA via /api/admin/* (service_role).
// pricing_config inline-edit + drawer (Pricing/Schedule/Audit-rollback/Where-used) + plan_limits + app_config.
// Prefix pr-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type PRow = {
  key: string; value_idr: number; value_usd_cents: number | null; description: string | null;
  category: string | null; active: boolean; effective_from: string | null; effective_until: string | null;
  updated_by: string | null; updated_at: string;
};
type PlanLimit = { plan_type: string; max_videos_per_day: number; max_channels: number; display_name: string | null; niche_studio: boolean; sort_order: number };
type AuditRow = { id: string; old_value: PRow | null; new_value: PRow; changed_by: string | null; changed_at: string };

const CAT_BADGE: Record<string, string> = { subscription: "badge-brand", add_on: "badge-info", one_time: "badge-default", discount: "badge-success" };
const fmtIDR = (n: number) => (n ?? 0).toLocaleString("id-ID");
// (App Config dipindah ke halaman khusus /admin/app-config — tak lagi di sini.)

export default function AdminPricingPage() {
  const [pricing, setPricing] = useState<PRow[]>([]);
  const [planLimits, setPlanLimits] = useState<PlanLimit[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [sel, setSel] = useState<string | null>(null);
  const [dtab, setDtab] = useState(0);
  const [edit, setEdit] = useState<Partial<PRow>>({});
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    const r = await fetch("/api/admin/pricing");
    if (!r.ok) { setErr(`Gagal memuat (${r.status})`); setLoading(false); return; }
    const j = await r.json();
    setPricing(j.pricing); setPlanLimits(j.plan_limits); setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2400); return () => clearTimeout(t); }, [toast]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSel(null); };
    document.addEventListener("keydown", onKey); return () => document.removeEventListener("keydown", onKey);
  }, []);

  const cats = Array.from(new Set(pricing.map((p) => p.category).filter(Boolean))) as string[];
  const view = pricing.filter((p) => filter === "all" || p.category === filter);
  const cur = sel ? pricing.find((p) => p.key === sel) ?? null : null;

  function openRow(key: string) {
    const row = pricing.find((p) => p.key === key);
    setSel(key); setDtab(0); setEdit(row ? { ...row } : {}); setAudit([]);
  }
  useEffect(() => {
    if (sel && dtab === 2) fetch(`/api/admin/pricing/${sel}/audit`).then((r) => r.ok ? r.json() : { audit: [] }).then((j) => setAudit(j.audit));
  }, [sel, dtab]);

  async function patchPricing(key: string, body: Partial<PRow>) {
    setBusy(true);
    const r = await fetch(`/api/admin/pricing/${encodeURIComponent(key)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    setBusy(false);
    if (r.ok) { setToast("Tersimpan"); await load(); } else setToast("Gagal menyimpan");
    return r.ok;
  }
  async function rollback(key: string, audit_id: string) {
    setBusy(true);
    const r = await fetch(`/api/admin/pricing/${encodeURIComponent(key)}/rollback`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ audit_id }) });
    setBusy(false);
    if (r.ok) { setToast("Rollback diterapkan"); await load(); fetch(`/api/admin/pricing/${sel}/audit`).then((x) => x.json()).then((j) => setAudit(j.audit)); } else setToast("Gagal rollback");
  }
  async function patchPlanLimit(plan: string, body: Partial<PlanLimit>) {
    const r = await fetch(`/api/admin/plan-limits/${plan}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (r.ok) { setToast("Caps tersimpan"); await load(); } else setToast("Gagal");
  }

  return (
    <>
      <div className="pr-head">
        <div>
          <h1><Bi id="Konfigurasi Harga" en="Pricing Configuration" /></h1>
          <div className="pr-stat-line">
            <span><b>{pricing.length}</b> entries</span>
            <span><b>{pricing.filter((p) => p.active).length}</b> active</span>
            <span style={{ color: "var(--success)", fontWeight: 500 }}><Bi id="✓ Tersimpan otomatis — tanpa tombol Save (saat klik ke luar field / ubah toggle)" en="✓ Auto-saved — no Save button (on blur / toggle change)" /></span>
          </div>
        </div>
      </div>

      <div className="pr-filters"><div className="segmented">
        <button aria-selected={filter === "all"} onClick={() => setFilter("all")}>All</button>
        {cats.map((c) => <button key={c} aria-selected={filter === c} onClick={() => setFilter(c)}>{c}</button>)}
      </div></div>

      <div className="pr-layout">
        <div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl pr-tbl">
            <thead><tr><th>Key</th><th><Bi id="Deskripsi" en="Description" /></th><th>Cat</th><th className="num">IDR</th><th className="num">USD¢</th><th>Active</th></tr></thead>
            <tbody>
              {loading && <tr><td colSpan={6} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
              {err && <tr><td colSpan={6} style={{ padding: "1.5rem", textAlign: "center", color: "var(--danger)" }}>{err}</td></tr>}
              {view.map((row) => (
                <tr key={row.key} onClick={() => openRow(row.key)} style={{ cursor: "pointer" }}>
                  <td className="key">{row.key}</td>
                  <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{row.description}</td>
                  <td><span className={`badge ${CAT_BADGE[row.category ?? ""] ?? "badge-default"}`} style={{ fontSize: "0.625rem" }}>{row.category}</span></td>
                  <td className="num"><span className="pr-val-edit" contentEditable suppressContentEditableWarning onClick={(e) => e.stopPropagation()} onBlur={(e) => { const v = parseInt(e.currentTarget.textContent?.replace(/\D/g, "") || "0", 10); if (v !== row.value_idr) patchPricing(row.key, { value_idr: v }); }}>{fmtIDR(row.value_idr)}</span></td>
                  <td className="num"><span className="pr-val-edit" contentEditable suppressContentEditableWarning onClick={(e) => e.stopPropagation()} onBlur={(e) => { const v = parseInt(e.currentTarget.textContent?.replace(/\D/g, "") || "0", 10); if (v !== (row.value_usd_cents ?? 0)) patchPricing(row.key, { value_usd_cents: v }); }}>{row.value_usd_cents ?? "—"}</span></td>
                  <td><label className="switch" onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={row.active} onChange={(e) => patchPricing(row.key, { active: e.target.checked })} /><span className="track" /><span className="thumb" /></label></td>
                </tr>
              ))}
            </tbody>
          </table></div></div>

          <h3 style={{ fontSize: "var(--text-lg)", fontWeight: 600, margin: "1.5rem 0 1rem" }}><Bi id="Paket (tier) — admin-editable, no-hardcode" en="Plans (tiers) — admin-editable, no-hardcode" /></h3>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
            <thead><tr>
              <th><Bi id="Nama tampil" en="Display name" /></th><th>Key</th>
              <th className="num"><Bi id="Video/hari" en="Videos/day" /></th><th className="num">Channel</th>
              <th><Bi id="Niche Studio" en="Niche Studio" /></th>
            </tr></thead>
            <tbody>
              {[...planLimits].sort((a, b) => a.sort_order - b.sort_order).map((pl) => (
                <tr key={pl.plan_type}>
                  <td><input className="input" style={{ height: "2rem", maxWidth: 160 }} defaultValue={pl.display_name ?? pl.plan_type} title="Nama yang dilihat pelanggan" onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== (pl.display_name ?? "")) patchPlanLimit(pl.plan_type, { display_name: v }); }} /></td>
                  <td className="mono muted" style={{ fontSize: "var(--text-xs)" }}>{pl.plan_type}</td>
                  <td className="num"><input className="input" type="number" min={0} style={{ height: "2rem", width: "4.75rem" }} defaultValue={pl.max_videos_per_day} onBlur={(e) => { const n = parseInt(e.target.value, 10); if (Number.isInteger(n) && n !== pl.max_videos_per_day) patchPlanLimit(pl.plan_type, { max_videos_per_day: n }); }} /></td>
                  <td className="num"><input className="input" type="number" min={0} style={{ height: "2rem", width: "4.75rem" }} defaultValue={pl.max_channels} onBlur={(e) => { const n = parseInt(e.target.value, 10); if (Number.isInteger(n) && n !== pl.max_channels) patchPlanLimit(pl.plan_type, { max_channels: n }); }} /></td>
                  <td><label className="switch" title="Fasilitas Niche Studio"><input type="checkbox" checked={!!pl.niche_studio} onChange={(e) => patchPlanLimit(pl.plan_type, { niche_studio: e.target.checked })} /><span className="track" /><span className="thumb" /></label></td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", margin: "0.625rem 0 0" }}><Bi id="Harga/bln tiap tier diatur di tabel pricing_config di atas (plan_starter/pro/business)." en="Per-tier monthly price is edited in the pricing_config table above (plan_starter/pro/business)." /></div>
        </div>

        <aside className="pr-api-panel">
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Command size={15} /> API</h3>
            <div className="pr-api-doc">{`pricing_config\n→ landing (A2)\n→ onboarding (C4)\n→ billing (D13)`}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.75rem", lineHeight: 1.6 }}><Clock size={12} style={{ verticalAlign: -2 }} /> <Bi id="Edit langsung berlaku (public-read)" en="Edits apply immediately (public-read)" /></div>
          </div>
          <div className="card card-pad" style={{ marginTop: "1rem" }}>
            <h3 className="card-title" style={{ marginBottom: "0.5rem" }}><Shield size={15} /> RBAC</h3>
            <p className="muted" style={{ fontSize: "var(--text-xs)", lineHeight: 1.6, margin: 0 }}><Bi id="Hanya Super Admin (service_role) yang bisa edit. Tiap perubahan tercatat di pricing_audit." en="Only Super Admin can edit. Every change logged to pricing_audit." /></p>
          </div>
        </aside>
      </div>

      <div className={`pr-scrim${cur ? " open" : ""}`} onClick={() => setSel(null)} />
      <aside className={`pr-drawer${cur ? " open" : ""}`}>
        {cur && (<>
          <div className="pr-drawer-head"><div><div className="mono" style={{ fontWeight: 600 }}>{cur.key}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{cur.description}</div></div><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button></div>
          <div className="pr-drawer-tabs">{["Pricing", "Schedule", "Audit Log", "Where Used"].map((l, i) => <button key={l} className={`pr-dtab${dtab === i ? " active" : ""}`} onClick={() => setDtab(i)}>{l}</button>)}</div>
          <div className="pr-dpanel">
            {dtab === 0 && <>
              <div style={{ marginBottom: "1rem" }}><label className="label">Key</label><input className="input input-mono" value={cur.key} disabled /></div>
              <div style={{ marginBottom: "1rem" }}><label className="label">Description</label><input className="input" value={edit.description ?? ""} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div><label className="label">Value IDR</label><input className="input input-mono" type="number" value={edit.value_idr ?? 0} onChange={(e) => setEdit({ ...edit, value_idr: parseInt(e.target.value, 10) })} /></div>
                <div><label className="label">Value USD cents</label><input className="input input-mono" type="number" value={edit.value_usd_cents ?? 0} onChange={(e) => setEdit({ ...edit, value_usd_cents: parseInt(e.target.value, 10) })} /></div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.875rem", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}><Info size={13} /> <Bi id="USD¢ manual (set sesuai kurs)" en="USD¢ manual (set per FX rate)" /></div>
              <div className="pr-impact"><span style={{ color: "var(--warning)", flex: "none" }}><AlertTriangle size={16} /></span><div><Bi id="Perubahan berlaku langsung ke landing, onboarding, billing." en="Change applies immediately to landing, onboarding, billing." /></div></div>
            </>}
            {dtab === 1 && <>
              <div style={{ marginBottom: "1rem" }}><label className="label">Effective from</label><input className="input" type="text" value={edit.effective_from ?? ""} onChange={(e) => setEdit({ ...edit, effective_from: e.target.value })} placeholder="ISO ts" /></div>
              <div style={{ marginBottom: "1rem" }}><label className="label">Effective until</label><input className="input" type="text" value={edit.effective_until ?? ""} onChange={(e) => setEdit({ ...edit, effective_until: e.target.value || null })} placeholder="— (tanpa batas)" /></div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}><span style={{ fontSize: "var(--text-sm)" }}>Active</span><label className="switch"><input type="checkbox" checked={edit.active ?? false} onChange={(e) => setEdit({ ...edit, active: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
            </>}
            {dtab === 2 && <>
              {audit.length === 0 && <div className="muted" style={{ fontSize: "var(--text-xs)" }}>Belum ada riwayat perubahan.</div>}
              {audit.map((a) => (
                <div key={a.id} style={{ padding: "0.625rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                  <div className="mono" style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>Rp {fmtIDR(a.old_value?.value_idr ?? 0)} → Rp {fmtIDR(a.new_value?.value_idr ?? 0)}</div>
                  <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 2 }}>{a.changed_by} · {new Date(a.changed_at).toLocaleString("id-ID")} {a.old_value && <button className="btn btn-ghost btn-sm" style={{ padding: "0 .4rem" }} disabled={busy} onClick={() => rollback(cur.key, a.id)}><RotateCcw size={12} /> Rollback</button>}</div>
                </div>
              ))}
            </>}
            {dtab === 3 && <>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.875rem" }}><Bi id="Layar yang me-reference pricing_config:" en="Screens referencing pricing_config:" /></div>
              {["A2 Pricing (landing)", "C4 Onboarding", "D13 Billing"].map((s) => (<div key={s} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", padding: "0.4375rem 0", borderBottom: "1px solid var(--border-subtle)" }}><FileText size={14} /> {s}</div>))}
            </>}
          </div>
          <div style={{ padding: "1rem 1.25rem", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setSel(null)}><Bi id="Batal" en="Cancel" /></button>
            {(dtab === 0 || dtab === 1) && <button className="btn btn-default" disabled={busy} onClick={async () => { const ok = await patchPricing(cur.key, edit); if (ok) setSel(null); }}><Bi id="Simpan perubahan" en="Save changes" /></button>}
          </div>
        </>)}
      </aside>

      <div className={`pr-save-toast${toast ? " show" : ""}`}><span style={{ color: "var(--success)" }}><CheckCircle size={16} /></span> {toast}</div>
    </>
  );
}
