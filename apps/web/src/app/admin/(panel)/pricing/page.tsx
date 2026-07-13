"use client";

import { useState, useEffect, useCallback } from "react";
import { Command, Clock, Shield, X, Info, AlertTriangle, FileText, CheckCircle, RotateCcw } from "lucide-react";
import "./pricing.css";

// E5 Admin Pricing (Phase 10.2 + Tahap 3 finalisasi_tier_plan 2026-07-13) — SUMBER HARGA seluruh
// sistem. DATA NYATA via /api/admin/* (service_role). pricing_config inline-edit + tambah-entri +
// drawer (Pricing/Audit-rollback/Where-used; tab Schedule DIBUANG — jadwal tak pernah dibaca sistem)
// + plan_limits (caps + tuas paket + NARASI marketing per-tier, keputusan owner). Prefix pr-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type PRow = {
  key: string; value_idr: number; value_usd_cents: number | null; description: string | null;
  category: string | null; active: boolean; effective_from: string | null; effective_until: string | null;
  updated_by: string | null; updated_at: string;
};
type Feature = { id: string; en: string };
type PlanLimit = {
  plan_type: string; max_videos_per_day: number; max_channels: number; display_name: string | null;
  niche_studio: boolean; sort_order: number;
  // Tahap 3: tuas paket + narasi marketing (admin-editable, keputusan owner 2026-07-13)
  full_niche_catalog: boolean; can_request_custom_niche: boolean; is_popular: boolean;
  tagline_id: string | null; tagline_en: string | null; marketing_features: Feature[] | null;
};
type AuditRow = { id: string; old_value: PRow | null; new_value: PRow; changed_by: string | null; changed_at: string };

// Kategori sesuai DATA nyata pricing_config (Tahap 3 — badge fiktif add_on/discount dibuang).
const CAT_BADGE: Record<string, string> = { subscription: "badge-brand", one_time: "badge-default" };
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
  // Tambah entri harga (Tahap 3.3) — utk add-on masa depan tanpa SQL.
  const [showNew, setShowNew] = useState(false);
  const [nw, setNw] = useState({ key: "", idr: "", category: "one_time", description: "" });
  // Editor NARASI per-paket (Tahap 3.1) — draft lokal, simpan per-blur/aksi (auto-save).
  const [selPlan, setSelPlan] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ tagline_id: string; tagline_en: string; features: Feature[] }>({ tagline_id: "", tagline_en: "", features: [] });

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
    if (sel && dtab === 1) fetch(`/api/admin/pricing/${sel}/audit`).then((r) => r.ok ? r.json() : { audit: [] }).then((j) => setAudit(j.audit));
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
    if (r.ok) { setToast("Tersimpan"); await load(); } else setToast("Gagal");
    return r.ok;
  }
  async function createEntry() {
    setBusy(true);
    const r = await fetch("/api/admin/pricing", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: nw.key.trim(), value_idr: parseInt(nw.idr, 10), category: nw.category.trim(), description: nw.description.trim() }) });
    setBusy(false);
    if (r.ok) { setToast("Entri dibuat"); setShowNew(false); setNw({ key: "", idr: "", category: "one_time", description: "" }); await load(); }
    else setToast(r.status === 409 ? "Key sudah ada" : "Key/nilai tidak valid");
  }
  function openPlanNarasi(pl: PlanLimit) {
    setSelPlan(pl.plan_type);
    setDraft({ tagline_id: pl.tagline_id ?? "", tagline_en: pl.tagline_en ?? "", features: [...(pl.marketing_features ?? [])] });
  }
  async function saveNarasi(plan: string, d: typeof draft) {
    // Baris kosong disaring (server menolak id kosong — anti-sampah); EN kosong = ikut ID (fallback server).
    const clean = d.features.filter((f) => f.id.trim());
    await patchPlanLimit(plan, { tagline_id: d.tagline_id, tagline_en: d.tagline_en, marketing_features: clean });
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
        <button className="btn btn-default" onClick={() => setShowNew(!showNew)}><Bi id="+ Tambah entri" en="+ Add entry" /></button>
      </div>

      {/* Form tambah entri harga (Tahap 3.3) — validasi keras di server (key snake_case unik, IDR ≥ 0) */}
      {showNew && (
        <div className="card card-pad" style={{ marginBottom: "1rem", display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr 1.6fr auto", gap: ".6rem", alignItems: "end" }}>
          <div><label className="label">Key</label><input className="input input-mono" placeholder="voice_pack_premium" value={nw.key} onChange={(e) => setNw({ ...nw, key: e.target.value })} /></div>
          <div><label className="label">IDR</label><input className="input input-mono" type="number" min={0} placeholder="99000" value={nw.idr} onChange={(e) => setNw({ ...nw, idr: e.target.value })} /></div>
          <div><label className="label"><Bi id="Kategori" en="Category" /></label><input className="input" list="pr-cats" value={nw.category} onChange={(e) => setNw({ ...nw, category: e.target.value })} /><datalist id="pr-cats">{cats.map((c) => <option key={c} value={c} />)}</datalist></div>
          <div><label className="label"><Bi id="Deskripsi" en="Description" /></label><input className="input" value={nw.description} onChange={(e) => setNw({ ...nw, description: e.target.value })} /></div>
          <button className="btn btn-default" disabled={busy || !nw.key.trim() || !nw.idr} onClick={createEntry}><Bi id="Tambah" en="Add" /></button>
        </div>
      )}

      <div className="pr-filters"><div className="segmented">
        <button aria-selected={filter === "all"} onClick={() => setFilter("all")}>All</button>
        {cats.map((c) => <button key={c} aria-selected={filter === c} onClick={() => setFilter(c)}>{c}</button>)}
      </div></div>

      <div className="pr-layout">
        <div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl pr-tbl">
            <thead><tr><th>Key</th><th><Bi id="Deskripsi" en="Description" /></th><th>Cat</th><th className="num">IDR</th><th>Active</th></tr></thead>
            <tbody>
              {loading && <tr><td colSpan={5} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
              {err && <tr><td colSpan={5} style={{ padding: "1.5rem", textAlign: "center", color: "var(--danger)" }}>{err}</td></tr>}
              {view.map((row) => (
                <tr key={row.key} onClick={() => openRow(row.key)} style={{ cursor: "pointer" }}>
                  <td className="key">{row.key}</td>
                  <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{row.description}</td>
                  <td><span className={`badge ${CAT_BADGE[row.category ?? ""] ?? "badge-default"}`} style={{ fontSize: "0.625rem" }}>{row.category}</span></td>
                  <td className="num"><span className="pr-val-edit" contentEditable suppressContentEditableWarning onClick={(e) => e.stopPropagation()} onBlur={(e) => { const v = parseInt(e.currentTarget.textContent?.replace(/\D/g, "") || "0", 10); if (v !== row.value_idr) patchPricing(row.key, { value_idr: v }); }}>{fmtIDR(row.value_idr)}</span></td>
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
              <th title="Akses SEMUA niche publik (bukan hanya niche dasar)"><Bi id="Katalog penuh" en="Full catalog" /></th>
              <th title="Boleh memesan niche custom berbayar"><Bi id="Niche custom" en="Custom niche" /></th>
              <th title='Badge "Most Popular" di kartu harga'><Bi id="Populer" en="Popular" /></th>
              <th><Bi id="Narasi" en="Narrative" /></th>
            </tr></thead>
            <tbody>
              {[...planLimits].sort((a, b) => a.sort_order - b.sort_order).map((pl) => (
                <tr key={pl.plan_type}>
                  <td><input className="input" style={{ height: "2rem", maxWidth: 160 }} defaultValue={pl.display_name ?? pl.plan_type} title="Nama yang dilihat pelanggan" onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== (pl.display_name ?? "")) patchPlanLimit(pl.plan_type, { display_name: v }); }} /></td>
                  <td className="mono muted" style={{ fontSize: "var(--text-xs)" }}>{pl.plan_type}</td>
                  <td className="num"><input className="input" type="number" min={0} style={{ height: "2rem", width: "4.75rem" }} defaultValue={pl.max_videos_per_day} onBlur={(e) => { const n = parseInt(e.target.value, 10); if (Number.isInteger(n) && n !== pl.max_videos_per_day) patchPlanLimit(pl.plan_type, { max_videos_per_day: n }); }} /></td>
                  <td className="num"><input className="input" type="number" min={0} style={{ height: "2rem", width: "4.75rem" }} defaultValue={pl.max_channels} onBlur={(e) => { const n = parseInt(e.target.value, 10); if (Number.isInteger(n) && n !== pl.max_channels) patchPlanLimit(pl.plan_type, { max_channels: n }); }} /></td>
                  <td><label className="switch" title="Fasilitas Niche Studio"><input type="checkbox" checked={!!pl.niche_studio} onChange={(e) => patchPlanLimit(pl.plan_type, { niche_studio: e.target.checked })} /><span className="track" /><span className="thumb" /></label></td>
                  <td><label className="switch"><input type="checkbox" checked={!!pl.full_niche_catalog} onChange={(e) => patchPlanLimit(pl.plan_type, { full_niche_catalog: e.target.checked })} /><span className="track" /><span className="thumb" /></label></td>
                  <td><label className="switch"><input type="checkbox" checked={!!pl.can_request_custom_niche} onChange={(e) => patchPlanLimit(pl.plan_type, { can_request_custom_niche: e.target.checked })} /><span className="track" /><span className="thumb" /></label></td>
                  <td><label className="switch"><input type="checkbox" checked={!!pl.is_popular} onChange={(e) => patchPlanLimit(pl.plan_type, { is_popular: e.target.checked })} /><span className="track" /><span className="thumb" /></label></td>
                  <td><button className="btn btn-secondary btn-sm" onClick={() => openPlanNarasi(pl)}><Bi id="Edit" en="Edit" /> ({(pl.marketing_features ?? []).length})</button></td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", margin: "0.625rem 0 0" }}><Bi id="Harga/bln tiap tier diatur di tabel pricing_config di atas (plan_starter/pro/business)." en="Per-tier monthly price is edited in the pricing_config table above (plan_starter/pro/business)." /></div>
        </div>

        <aside className="pr-api-panel">
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Command size={15} /> <Bi id="Dipakai di mana" en="Where it's used" /></h3>
            <div className="muted" style={{ fontSize: "var(--text-xs)", lineHeight: 1.8 }}>
              <div><span className="mono">plan_*</span> → <Bi id="harga paket di Landing & halaman Harga publik, Billing tenant, dan checkout Midtrans" en="plan prices on the public Landing & Pricing pages, tenant Billing, and Midtrans checkout" /></div>
              <div style={{ marginTop: ".4rem" }}><span className="mono">custom_niche_*</span> → <Bi id="harga add-on niche di Pustaka Niche tenant + tagihan pesanan" en="niche add-on price in the tenant Niche picker + order invoices" /></div>
            </div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.75rem", lineHeight: 1.6 }}><Clock size={12} style={{ verticalAlign: -2 }} /> <Bi id="Perubahan langsung berlaku ke semua halaman itu — tanpa deploy." en="Changes apply to all those pages instantly — no deploy." /></div>
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
          {/* Tab Schedule DIBUANG (Tahap 3 §3b-8 ratifikasi owner): effective_from/until tak pernah dibaca
              sistem mana pun — tuas jadwal yang bohong; satu saklar Active = jujur & cukup. */}
          <div className="pr-drawer-tabs">{["Pricing", "Audit Log", "Where Used"].map((l, i) => <button key={l} className={`pr-dtab${dtab === i ? " active" : ""}`} onClick={() => setDtab(i)}>{l}</button>)}</div>
          <div className="pr-dpanel">
            {dtab === 0 && <>
              <div style={{ marginBottom: "1rem" }}><label className="label">Key</label><input className="input input-mono" value={cur.key} disabled /></div>
              <div style={{ marginBottom: "1rem" }}><label className="label">Description</label><input className="input" value={edit.description ?? ""} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", alignItems: "end" }}>
                <div><label className="label">Value IDR</label><input className="input input-mono" type="number" value={edit.value_idr ?? 0} onChange={(e) => setEdit({ ...edit, value_idr: parseInt(e.target.value, 10) })} /></div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: "0.4rem" }}><span style={{ fontSize: "var(--text-sm)" }}>Active</span><label className="switch"><input type="checkbox" checked={edit.active ?? false} onChange={(e) => setEdit({ ...edit, active: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
              </div>
              <div className="pr-impact"><span style={{ color: "var(--warning)", flex: "none" }}><AlertTriangle size={16} /></span><div><Bi id="Perubahan berlaku langsung ke landing, onboarding, billing." en="Change applies immediately to landing, onboarding, billing." /></div></div>
            </>}
            {dtab === 1 && <>
              {audit.length === 0 && <div className="muted" style={{ fontSize: "var(--text-xs)" }}>Belum ada riwayat perubahan.</div>}
              {audit.map((a) => (
                <div key={a.id} style={{ padding: "0.625rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                  <div className="mono" style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>Rp {fmtIDR(a.old_value?.value_idr ?? 0)} → Rp {fmtIDR(a.new_value?.value_idr ?? 0)}</div>
                  <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 2 }}>{a.changed_by} · {new Date(a.changed_at).toLocaleString("id-ID")} {a.old_value && <button className="btn btn-ghost btn-sm" style={{ padding: "0 .4rem" }} disabled={busy} onClick={() => rollback(cur.key, a.id)}><RotateCcw size={12} /> Rollback</button>}</div>
                </div>
              ))}
            </>}
            {dtab === 2 && <>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.875rem" }}><Bi id="Layar yang me-reference pricing_config:" en="Screens referencing pricing_config:" /></div>
              {["A2 Pricing (landing)", "C4 Onboarding", "D13 Billing"].map((s) => (<div key={s} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", padding: "0.4375rem 0", borderBottom: "1px solid var(--border-subtle)" }}><FileText size={14} /> {s}</div>))}
            </>}
          </div>
          <div style={{ padding: "1rem 1.25rem", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setSel(null)}><Bi id="Batal" en="Cancel" /></button>
            {dtab === 0 && <button className="btn btn-default" disabled={busy} onClick={async () => { const ok = await patchPricing(cur.key, edit); if (ok) setSel(null); }}><Bi id="Simpan perubahan" en="Save changes" /></button>}
          </div>
        </>)}
      </aside>

      {/* Drawer NARASI per-paket (Tahap 3.1, keputusan owner 2026-07-13): tagline dwibahasa + baris
          fitur kualitatif [{id,en}]. ANGKA fakta (channel/video-hari/Niche Studio) TIDAK di sini —
          tetap otomatis dari kolom kuota. Auto-save per aksi/blur (pola halaman ini). */}
      <div className={`pr-scrim${selPlan ? " open" : ""}`} onClick={() => setSelPlan(null)} />
      <aside className={`pr-drawer${selPlan ? " open" : ""}`}>
        {selPlan && (() => {
          const pl = planLimits.find((p) => p.plan_type === selPlan);
          if (!pl) return null;
          const save = (d: typeof draft) => { setDraft(d); saveNarasi(selPlan, d); };
          return (<>
            <div className="pr-drawer-head"><div><div style={{ fontWeight: 600 }}><Bi id={`Narasi paket ${pl.display_name ?? selPlan}`} en={`${pl.display_name ?? selPlan} plan narrative`} /></div><div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Tampil di kartu harga (marketing) — angka kuota tetap otomatis dari kolom paket" en="Shown on pricing cards (marketing) — quota numbers stay automatic from plan columns" /></div></div><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSelPlan(null)}><X size={16} /></button></div>
            <div className="pr-dpanel">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}>
                <div><label className="label"><Bi id="Slogan (ID)" en="Tagline (ID)" /></label><input className="input" value={draft.tagline_id} onChange={(e) => setDraft({ ...draft, tagline_id: e.target.value })} onBlur={() => saveNarasi(selPlan, draft)} /></div>
                <div><label className="label"><Bi id="Slogan (EN)" en="Tagline (EN)" /></label><input className="input" value={draft.tagline_en} onChange={(e) => setDraft({ ...draft, tagline_en: e.target.value })} onBlur={() => saveNarasi(selPlan, draft)} /></div>
              </div>
              <label className="label"><Bi id="Baris fitur (maks 12; urutan = urutan tampil)" en="Feature lines (max 12; order = display order)" /></label>
              {draft.features.map((f, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto auto auto", gap: ".4rem", marginBottom: ".4rem" }}>
                  <input className="input" style={{ height: "2rem" }} placeholder="Teks ID" value={f.id} onChange={(e) => { const fs = [...draft.features]; fs[i] = { ...fs[i], id: e.target.value }; setDraft({ ...draft, features: fs }); }} onBlur={() => saveNarasi(selPlan, draft)} />
                  <input className="input" style={{ height: "2rem" }} placeholder="Text EN" value={f.en} onChange={(e) => { const fs = [...draft.features]; fs[i] = { ...fs[i], en: e.target.value }; setDraft({ ...draft, features: fs }); }} onBlur={() => saveNarasi(selPlan, draft)} />
                  <button className="btn btn-ghost btn-sm" disabled={i === 0} title="Naik" onClick={() => { const fs = [...draft.features]; [fs[i - 1], fs[i]] = [fs[i], fs[i - 1]]; save({ ...draft, features: fs }); }}>↑</button>
                  <button className="btn btn-ghost btn-sm" disabled={i === draft.features.length - 1} title="Turun" onClick={() => { const fs = [...draft.features]; [fs[i + 1], fs[i]] = [fs[i], fs[i + 1]]; save({ ...draft, features: fs }); }}>↓</button>
                  <button className="btn btn-ghost btn-sm" title="Hapus baris" onClick={() => { const fs = draft.features.filter((_, x) => x !== i); save({ ...draft, features: fs }); }}><X size={13} /></button>
                </div>
              ))}
              <button className="btn btn-secondary btn-sm" disabled={draft.features.length >= 12} onClick={() => setDraft({ ...draft, features: [...draft.features, { id: "", en: "" }] })}><Bi id="+ Tambah baris" en="+ Add line" /></button>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".75rem" }}><Bi id="Baris kosong tidak tersimpan. Perubahan tersimpan otomatis saat klik ke luar field / aksi." en="Empty lines are not saved. Changes auto-save on blur / action." /></div>
            </div>
          </>);
        })()}
      </aside>

      <div className={`pr-save-toast${toast ? " show" : ""}`}><span style={{ color: "var(--success)" }}><CheckCircle size={16} /></span> {toast}</div>
    </>
  );
}
