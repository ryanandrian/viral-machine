"use client";

import { useState, useEffect, useCallback } from "react";
import { Palette, Plus, X, Check } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import NicheDnaEditor, { type NicheRow } from "@/components/niche-dna-editor";
import TestNichePanel from "@/components/test-niche-panel";

// F3-03 / F2-10 — Niche Studio (tenant Business+, GATED) — DIROMBAK 2026-07-04 (kesepakatan owner):
// editor DNA per-field BERSAMA dgn admin (components/niche-dna-editor) — NOL JSON mentah, preset
// "pilih dulu, sunting kalau mau", validasi jujur. Niche baru = wizard TEMPLATE (copy DNA base).
// Server tetap enforce: private + exclusive_to=tenant + origin='studio' + gating plan.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const muted: React.CSSProperties = { fontSize: "var(--text-sm)", color: "var(--text-secondary)" };

type Niche = NicheRow & { name: string; is_active: boolean };
type Tpl = { niche_id: string; name: string };

export default function NicheStudioPage() {
  const [gated, setGated] = useState<boolean | null>(null);
  const [niches, setNiches] = useState<Niche[]>([]);
  const [templates, setTemplates] = useState<Tpl[]>([]);
  const [sel, setSel] = useState<Niche | null>(null);
  const [active, setActive] = useState(true);
  const [newN, setNewN] = useState<{ niche_id: string; name: string; template_niche_id: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await fetch("/api/niches/mine");
    if (r.status === 403) { setGated(false); return; }
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setGated(true); setNiches(j.niches ?? []); setTemplates(j.templates ?? []); }
    else setToast(j.error || "Gagal memuat");
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

  async function createNiche() {
    if (!newN || !/^[a-z0-9_]+$/.test(newN.niche_id)) return;
    setBusy(true);
    const r = await fetch("/api/niches/mine", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newN) });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { setToast(`Niche dibuat: ${newN.niche_id}`); setNewN(null); await load(); if (j.row) { setSel(j.row as Niche); setActive(true); } }
    else setToast(j.error || "Gagal buat niche");
  }

  async function saveDna(patch: Record<string, unknown>) {
    if (!sel) return { ok: false };
    setBusy(true);
    const r = await fetch("/api/niches/mine", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ niche_id: sel.niche_id, is_active: active, ...patch }) });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { setToast("DNA tersimpan"); setSel(null); await load(); return { ok: true }; }
    setToast(j.error === "dna_invalid" ? "Ada isian tidak valid" : (j.error || "Gagal menyimpan"));
    return { ok: false, fields: j.fields };
  }

  return (
    <>
      <PageHeader helpKey="niche-studio" icon={Palette} title="Niche Studio"
        subtitle={<Bi id="Buat & sesuaikan niche custom PRIVAT milik Anda (DNA: narasi/visual/musik/struktur)." en="Create & tune your own PRIVATE custom niches (DNA: narration/visual/music/structure)." />}
        action={gated ? <button className="btn btn-default" onClick={() => setNewN({ niche_id: "", name: "", template_niche_id: templates[0]?.niche_id ?? "" })}><Plus size={15} /> <Bi id="Niche baru" en="New niche" /></button> : undefined} />

      {gated === null && <div style={{ ...muted, padding: "2rem", textAlign: "center" }}><Bi id="Memuat…" en="Loading…" /></div>}

      {gated === false && (
        <div className="card card-pad" style={{ maxWidth: 560, textAlign: "center", padding: "2.5rem" }}>
          <Palette size={32} style={{ color: "var(--accent)", margin: "0 auto 0.75rem" }} />
          <h3 style={{ marginBottom: "0.5rem" }}><Bi id="Niche Studio — fitur paket Business" en="Niche Studio — Business plan feature" /></h3>
          <p style={muted}><Bi id="Buat niche custom DNA sendiri tersedia di paket Business+. Tier lain bisa request niche khusus dari pemilih niche di channel." en="Building your own custom-DNA niches is available on Business+. Other tiers can request a custom niche from the channel niche picker." /></p>
        </div>
      )}

      {gated && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: "0.875rem", maxWidth: 880 }}>
          {niches.length === 0 && <div style={{ ...muted }}><Bi id="Belum ada niche custom. Klik “Niche baru”." en="No custom niches yet. Click “New niche”." /></div>}
          {niches.map((n) => (
            <div className="card card-pad" key={n.niche_id}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                <span style={{ fontWeight: 600, color: "var(--text-primary)", flex: 1 }}>{n.name || n.niche_id}</span>
                <span className="badge badge-brand" style={{ fontSize: "0.625rem" }}>🔒 private</span>
              </div>
              <div className="muted" style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}>{n.niche_id}</div>
              <button className="btn btn-secondary btn-sm" style={{ marginTop: "0.75rem" }} onClick={() => { setSel(n); setActive(!!n.is_active); }}><Bi id="Edit DNA" en="Edit DNA" /></button>
            </div>
          ))}
        </div>
      )}

      {/* Editor drawer — komponen DNA bersama */}
      {sel && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setSel(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", justifyContent: "flex-end" }}>
          <aside className="card" style={{ width: "min(640px,100%)", height: "100%", overflowY: "auto", borderRadius: 0, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
              <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}>{sel.name || sel.niche_id}</div><div className="muted" style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}>{sel.niche_id}</div></div>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", marginRight: ".75rem" }}>
                <span className="switch"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /><span className="track" /><span className="thumb" /></span>
                <Bi id="Aktif" en="Active" />
              </label>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button>
            </div>
            <TestNichePanel key={sel.niche_id}
              getUrl={`/api/niches/mine/test?niche_id=${sel.niche_id}`}
              postUrl="/api/niches/mine/test"
              postBody={{ niche_id: sel.niche_id }}
              confirmMessage={<Bi id="Mesin akan memproduksi 1 video uji NYATA memakai kredensial AI & channel ANDA sendiri (biaya provider ditanggung kunci Anda/BYOK). TIDAK dipublish ke YouTube & TIDAK memakai kuota — hasil ditonton di panel ini, otomatis terhapus setelah ±3 hari." en="The engine will produce 1 REAL test video using YOUR OWN AI credentials & channel (provider cost on your keys/BYOK). NOT published to YouTube & no quota used — watch here; auto-cleaned after ~3 days." />} />
            <NicheDnaEditor niche={sel} onSave={saveDna} busy={busy} onCancel={() => setSel(null)} />
          </aside>
        </div>
      )}

      {/* Create modal — wizard template */}
      {newN && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setNewN(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card card-pad" style={{ maxWidth: 460, width: "100%" }}>
            <h3 style={{ marginBottom: ".75rem" }}><Bi id="Niche custom baru" en="New custom niche" /></h3>
            <div className="fld"><label className="label">niche_id (slug a-z0-9_)</label><input className="input input-mono" value={newN.niche_id} onChange={(e) => setNewN({ ...newN, niche_id: e.target.value })} placeholder="mis. my_dark_tales" /></div>
            <div className="fld"><label className="label"><Bi id="Nama tampilan" en="Display name" /></label><input className="input" value={newN.name} onChange={(e) => setNewN({ ...newN, name: e.target.value })} /></div>
            <div className="fld"><label className="label"><Bi id="Mulai dari template" en="Start from template" /></label>
              <select className="input" value={newN.template_niche_id} onChange={(e) => setNewN({ ...newN, template_niche_id: e.target.value })}>
                <option value="">— kosong / blank —</option>
                {templates.map((t) => <option key={t.niche_id} value={t.niche_id}>{t.name}</option>)}
              </select>
              <div className="muted" style={{ fontSize: "0.6875rem", marginTop: ".25rem" }}><Bi id="Gaya narasi/visual/musik/struktur di-copy sebagai titik awal — kata kunci topik tetap Anda isi sendiri." en="Narration/visual/music/structure styles are copied as a starting point — topic keywords stay yours to fill." /></div>
            </div>
            <div style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end", marginTop: "1rem" }}>
              <button className="btn btn-ghost" onClick={() => setNewN(null)}><Bi id="Batal" en="Cancel" /></button>
              <button className="btn btn-default" disabled={busy || !/^[a-z0-9_]+$/.test(newN.niche_id)} onClick={createNiche}><Check size={14} /> <Bi id="Buat" en="Create" /></button>
            </div>
          </div>
        </div>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 90, background: "#1f2937", color: "#fff", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)", boxShadow: "0 6px 20px rgba(0,0,0,0.35)", fontSize: "var(--text-sm)" }}>{toast}</div>}
    </>
  );
}
