"use client";

import { useState, useEffect, useCallback } from "react";
import { Palette, Plus, X, Check, Loader2 } from "lucide-react";
import { YT_CATEGORIES } from "@/lib/youtube-categories";
import { PageHeader } from "@/components/page-header";

// F3-03 / F2-10 — Niche Studio (tenant Business+, GATED). Buat/edit niche CUSTOM PRIVATE sendiri
// via /api/niches/mine (server-enforce: private + exclusive_to=tenant + gating min-rank).
// Hanya kelas GLOBAL (components.css) + inline — TANPA css scoped (hindari bug Turbopack lintas-route).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const muted: React.CSSProperties = { fontSize: "var(--text-sm)", color: "var(--text-secondary)" };
const asArr = (v: unknown): string => Array.isArray(v) ? (v as string[]).join(", ") : "";
const jstr = (v: unknown) => JSON.stringify(v ?? {}, null, 2);

type Niche = { niche_id: string; name: string; is_active: boolean; access_type: string; [k: string]: unknown };
type Edit = Record<string, string | boolean>;

export default function NicheStudioPage() {
  const [gated, setGated] = useState<boolean | null>(null);  // null=loading, false=tak ber-entitlement
  const [niches, setNiches] = useState<Niche[]>([]);
  const [sel, setSel] = useState<Niche | null>(null);
  const [edit, setEdit] = useState<Edit>({});
  const [newN, setNewN] = useState<{ niche_id: string; name: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await fetch("/api/niches/mine");
    if (r.status === 403) { setGated(false); return; }
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setGated(true); setNiches(j.niches ?? []); }
    else { setToast(j.error || "Gagal memuat"); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

  function openEdit(n: Niche) {
    setSel(n);
    setEdit({
      name: n.name ?? "", is_active: !!n.is_active,
      keywords: asArr(n.keywords), default_hashtags: asArr(n.default_hashtags),
      youtube_category_id: (n.youtube_category_id as string) ?? "",
      narration_persona: jstr(n.narration_persona), music_config: jstr(n.music_config),
      visual_style: jstr(n.visual_style), image_quality_tags: asArr(n.image_quality_tags),
      image_negative_prompt: (n.image_negative_prompt as string) ?? "", visual_fallbacks: asArr(n.visual_fallbacks),
      mood_priority: jstr(n.mood_priority), section_timing: jstr(n.section_timing),
      emotion_scoring_criteria: (n.emotion_scoring_criteria as string) ?? "",
    });
  }

  async function createNiche() {
    if (!newN || !/^[a-z0-9_]+$/.test(newN.niche_id)) return;
    setBusy(true);
    const r = await fetch("/api/niches/mine", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newN) });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { setToast(`Niche dibuat: ${newN.niche_id}`); setNewN(null); await load(); }
    else setToast(j.error || "Gagal buat niche");
  }

  async function save() {
    if (!sel) return;
    setBusy(true);
    const patch: Record<string, unknown> = {
      niche_id: sel.niche_id, name: edit.name, is_active: edit.is_active,
      emotion_scoring_criteria: edit.emotion_scoring_criteria,
      image_negative_prompt: (edit.image_negative_prompt as string) || null,
      keywords: String(edit.keywords || "").split(",").map((s) => s.trim()).filter(Boolean),
      default_hashtags: String(edit.default_hashtags || "").split(",").map((s) => s.trim()).filter(Boolean),
      youtube_category_id: (edit.youtube_category_id as string) || null,
      image_quality_tags: String(edit.image_quality_tags || "").split(",").map((s) => s.trim()).filter(Boolean),
      visual_fallbacks: String(edit.visual_fallbacks || "").split(",").map((s) => s.trim()).filter(Boolean),
    };
    for (const k of ["narration_persona", "music_config", "visual_style", "mood_priority", "section_timing"]) {
      try { patch[k] = JSON.parse(edit[k] as string); } catch { /* skip JSON invalid */ }
    }
    const r = await fetch("/api/niches/mine", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { setToast("Tersimpan"); setSel(null); await load(); } else setToast(j.error || "Gagal menyimpan");
  }

  const fld = (key: string, label: { id: string; en: string }, mono = false, rows = 2) => (
    <div className="fld"><label className="label"><Bi id={label.id} en={label.en} /></label>
      <textarea className={`textarea${mono ? " input-mono" : ""}`} rows={rows} value={edit[key] as string} onChange={(e) => setEdit({ ...edit, [key]: e.target.value })} /></div>
  );

  return (
    <>
      <PageHeader icon={Palette} title="Niche Studio"
        subtitle={<Bi id="Buat & sesuaikan niche custom PRIVAT milik Anda (DNA: voice/visual/musik/timing)." en="Create & tune your own PRIVATE custom niches (DNA: voice/visual/music/timing)." />}
        action={gated ? <button className="btn btn-default" onClick={() => setNewN({ niche_id: "", name: "" })}><Plus size={15} /> <Bi id="Niche baru" en="New niche" /></button> : undefined} />

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
              <button className="btn btn-secondary btn-sm" style={{ marginTop: "0.75rem" }} onClick={() => openEdit(n)}><Bi id="Edit DNA" en="Edit DNA" /></button>
            </div>
          ))}
        </div>
      )}

      {/* Editor */}
      {sel && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setSel(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", justifyContent: "flex-end" }}>
          <aside className="card" style={{ width: "min(560px,100%)", height: "100%", overflowY: "auto", borderRadius: 0, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
              <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}>{sel.name || sel.niche_id}</div><div className="muted" style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}>{sel.niche_id}</div></div>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button>
            </div>
            <div className="fld"><label className="label"><Bi id="Nama tampilan" en="Display name" /></label><input className="input" value={edit.name as string} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></div>
            {fld("keywords", { id: "Keywords (pisah koma)", en: "Keywords (comma)" })}
            {fld("default_hashtags", { id: "Default hashtags (pisah koma)", en: "Default hashtags (comma)" })}
            <div className="fld"><label className="label"><Bi id="Kategori YouTube" en="YouTube category" /></label>
              <select className="input" value={(edit.youtube_category_id as string) ?? ""} onChange={(e) => setEdit({ ...edit, youtube_category_id: e.target.value })}>
                <option value="">— pilih (default Education) —</option>
                {YT_CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></div>
            <div style={{ borderTop: "1px solid var(--border-subtle)", margin: "0.75rem 0", paddingTop: "0.5rem", fontWeight: 600, fontSize: "var(--text-sm)" }}>Narrasi DNA <span style={{ fontWeight: 400, fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>(suara dipilih di Channel)</span></div>
            {fld("narration_persona", { id: "narration_persona JSON (gaya/tone narasi)", en: "narration_persona JSON (narration style/tone)" }, true, 5)}
            <div style={{ borderTop: "1px solid var(--border-subtle)", margin: "0.75rem 0", paddingTop: "0.5rem", fontWeight: 600, fontSize: "var(--text-sm)" }}>Musik DNA <span style={{ fontWeight: 400, fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>(library per-mood; auto/random/fixed)</span></div>
            {fld("music_config", { id: 'music_config JSON: {"mode":"auto|random|fixed","mood":"…","track_id":"…"}', en: 'music_config JSON: {"mode":"auto|random|fixed","mood":"…","track_id":"…"}' }, true, 3)}
            <div style={{ borderTop: "1px solid var(--border-subtle)", margin: "0.75rem 0", paddingTop: "0.5rem", fontWeight: 600, fontSize: "var(--text-sm)" }}>Visual DNA</div>
            {fld("visual_style", { id: "visual_style JSON", en: "visual_style JSON" }, true, 4)}
            {fld("image_quality_tags", { id: "image_quality_tags (pisah koma)", en: "image_quality_tags (comma)" })}
            {fld("image_negative_prompt", { id: "image_negative_prompt", en: "image_negative_prompt" })}
            {fld("visual_fallbacks", { id: "visual_fallbacks (pisah koma)", en: "visual_fallbacks (comma)" })}
            <div style={{ borderTop: "1px solid var(--border-subtle)", margin: "0.75rem 0", paddingTop: "0.5rem", fontWeight: 600, fontSize: "var(--text-sm)" }}>Mood + Scoring</div>
            {fld("mood_priority", { id: "mood_priority JSON", en: "mood_priority JSON" }, true, 3)}
            {fld("section_timing", { id: "section_timing JSON", en: "section_timing JSON" }, true, 3)}
            {fld("emotion_scoring_criteria", { id: "emotion_scoring_criteria", en: "emotion_scoring_criteria" }, false, 3)}
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", margin: "0.5rem 0" }}>
              <span className="switch"><input type="checkbox" checked={!!edit.is_active} onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })} /><span className="track" /><span className="thumb" /></span>
              <Bi id="Aktif" en="Active" />
            </label>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
              <button className="btn btn-ghost" onClick={() => setSel(null)}><Bi id="Batal" en="Cancel" /></button>
              <button className="btn btn-default" disabled={busy} onClick={save}>{busy ? <Loader2 size={15} className="spin" /> : <><Check size={15} /> <Bi id="Simpan" en="Save" /></>}</button>
            </div>
          </aside>
        </div>
      )}

      {/* Create modal */}
      {newN && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setNewN(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card card-pad" style={{ maxWidth: 440, width: "100%" }}>
            <h3 style={{ marginBottom: ".75rem" }}><Bi id="Niche custom baru" en="New custom niche" /></h3>
            <div className="fld"><label className="label">niche_id (slug a-z0-9_)</label><input className="input input-mono" value={newN.niche_id} onChange={(e) => setNewN({ ...newN, niche_id: e.target.value })} placeholder="mis. my_dark_tales" /></div>
            <div className="fld"><label className="label"><Bi id="Nama tampilan" en="Display name" /></label><input className="input" value={newN.name} onChange={(e) => setNewN({ ...newN, name: e.target.value })} /></div>
            <div style={muted}><Bi id="DNA (voice/visual/timing) diedit setelah dibuat." en="DNA (voice/visual/timing) edited after creation." /></div>
            <div style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end", marginTop: "1rem" }}>
              <button className="btn btn-ghost" onClick={() => setNewN(null)}><Bi id="Batal" en="Cancel" /></button>
              <button className="btn btn-default" disabled={busy || !/^[a-z0-9_]+$/.test(newN.niche_id)} onClick={createNiche}><Check size={14} /> <Bi id="Buat" en="Create" /></button>
            </div>
          </div>
        </div>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 90, background: "var(--surface-raised,#1f2937)", color: "var(--text-primary)", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid var(--border)" }}>{toast}</div>}
    </>
  );
}
