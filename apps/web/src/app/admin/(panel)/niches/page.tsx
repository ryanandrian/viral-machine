"use client";

import { useState, useEffect, useCallback } from "react";
import { Calendar, Plus, X, Clock } from "lucide-react";
import "./niches.css";

// E2.3 Admin Niche Library (Phase 10.3) — DATA NYATA via /api/admin/niches (service_role).
// Identity + Access/Exclusivity editable; Voice/Visual/Music DNA = edit JSON; monthly-release + pipeline real.
// TAG POOL = placeholder jujur (epik pipeline Layer-2, belum dibangun — MULTI_FORMAT §0). Prefix nl-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Niche = {
  niche_id: string; name: string; keywords: unknown; default_hashtags: unknown; is_active: boolean; is_base: boolean;
  access_type: string; exclusive_to: string | null; exclusive_until: string | null; released_at: string | null;
  voice_profile: unknown; visual_style: unknown; mood_priority: unknown; emotion_scoring_criteria: string | null;
  video_count: number; tenant_count: number; avg_viral: number | null;
};
type Release = { id: string; niche_id: string; scheduled_at: string; status: string };

const DTABS = ["Identity", "Voice DNA", "Visual DNA", "Music + Scoring", "Tag Pool", "Access & Exclusivity"];
function AccessBadge({ a }: { a: string }) {
  if (a === "public") return <span className="badge badge-success"><span className="dot" />🌍 Public</span>;
  if (a === "pending") return <span className="badge badge-warning"><span className="dot" />📅 Pending</span>;
  return <span className="badge badge-brand">🔒 Private</span>;
}
const asArr = (v: unknown): string[] => Array.isArray(v) ? v as string[] : [];
const jstr = (v: unknown) => JSON.stringify(v ?? {}, null, 2);
const dateID = (iso: string | null) => iso ? new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "—";

export default function AdminNichesPage() {
  const [niches, setNiches] = useState<Niche[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [sel, setSel] = useState<string | null>(null);
  const [dtab, setDtab] = useState(0);
  const [edit, setEdit] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [sched, setSched] = useState<{ niche_id: string; date: string }>({ niche_id: "", date: "" });

  const load = useCallback(async () => {
    setLoading(true);
    const r = await fetch("/api/admin/niches");
    if (r.ok) { const j = await r.json(); setNiches(j.niches); setReleases(j.releases); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2400); return () => clearTimeout(t); }, [toast]);
  useEffect(() => { const k = (e: KeyboardEvent) => { if (e.key === "Escape") setSel(null); }; document.addEventListener("keydown", k); return () => document.removeEventListener("keydown", k); }, []);

  const view = niches.filter((n) => filter === "all" || (filter === "active" && n.access_type === "public" && n.is_active) || n.access_type === filter);
  const cur = sel ? niches.find((n) => n.niche_id === sel) ?? null : null;
  const pipeline = niches.filter((n) => n.exclusive_to);

  function openRow(id: string) {
    const n = niches.find((x) => x.niche_id === id); setSel(id); setDtab(0);
    setEdit(n ? {
      name: n.name, keywords: asArr(n.keywords).join(", "), default_hashtags: asArr(n.default_hashtags).join(", "),
      is_active: n.is_active, is_base: n.is_base, access_type: n.access_type, exclusive_to: n.exclusive_to ?? "",
      exclusive_until: n.exclusive_until ?? "", released_at: n.released_at ?? "",
      voice_profile: jstr(n.voice_profile), visual_style: jstr(n.visual_style), mood_priority: jstr(n.mood_priority),
      emotion_scoring_criteria: n.emotion_scoring_criteria ?? "",
    } : {});
  }

  async function save() {
    if (!cur) return;
    setBusy(true);
    const patch: Record<string, unknown> = {
      name: edit.name, is_active: edit.is_active, is_base: edit.is_base,
      access_type: edit.access_type, exclusive_to: (edit.exclusive_to as string) || null,
      exclusive_until: (edit.exclusive_until as string) || null, released_at: (edit.released_at as string) || null,
      emotion_scoring_criteria: edit.emotion_scoring_criteria,
      keywords: String(edit.keywords || "").split(",").map((s) => s.trim()).filter(Boolean),
      default_hashtags: String(edit.default_hashtags || "").split(",").map((s) => s.trim()).filter(Boolean),
    };
    for (const [k, v] of [["voice_profile", edit.voice_profile], ["visual_style", edit.visual_style], ["mood_priority", edit.mood_priority]] as const) {
      try { patch[k] = JSON.parse(v as string); } catch { /* skip invalid JSON */ }
    }
    const r = await fetch(`/api/admin/niches/${cur.niche_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
    setBusy(false);
    if (r.ok) { setToast("Tersimpan"); setSel(null); await load(); } else setToast("Gagal menyimpan");
  }
  async function testNiche(id: string) {
    setBusy(true);
    const r = await fetch(`/api/admin/niches/${id}/test`, { method: "POST" });
    setBusy(false);
    const j = await r.json().catch(() => ({}));
    setToast(r.ok ? "Test niche diantre (channel admin-test, private) — pantau di Runs/System Health" : `Gagal: ${j.error ?? r.status}`);
  }
  async function transition(id: string) {
    setBusy(true);
    const r = await fetch(`/api/admin/niches/${id}/transition`, { method: "POST" });
    setBusy(false);
    if (r.ok) { setToast("Niche → public"); await load(); } else setToast("Gagal");
  }
  async function scheduleRelease() {
    if (!sched.niche_id || !sched.date) return;
    setBusy(true);
    const r = await fetch("/api/admin/niche-releases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ niche_id: sched.niche_id, scheduled_at: sched.date }) });
    setBusy(false);
    if (r.ok) { setToast("Rilis dijadwalkan"); setSched({ niche_id: "", date: "" }); await load(); } else setToast("Gagal menjadwalkan");
  }

  return (
    <>
      <div className="nl-head">
        <div>
          <h1><Bi id="Niche Library" en="Niche Library" /></h1>
          <div className="nl-stat-line">
            <span><b>{niches.filter((n) => n.is_active).length}</b> Active</span>
            <span><b>{niches.filter((n) => n.access_type === "pending").length}</b> Pending</span>
            <span><b>{niches.filter((n) => n.access_type === "private").length}</b> Private</span>
            <span><b>{niches.filter((n) => n.is_base).length}</b> Base</span>
          </div>
        </div>
      </div>

      <div className="nl-filters"><div className="segmented">
        {[["all", "All"], ["active", "Active"], ["pending", "Pending"], ["private", "Private"]].map(([k, l]) => <button key={k} aria-selected={filter === k} onClick={() => setFilter(k)}>{l}</button>)}
      </div></div>

      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl nl-tbl">
        <thead><tr><th><Bi id="Niche" en="Niche" /></th><th>Access</th><th className="num">Tenant</th><th className="num">Video</th><th className="num">Avg score</th><th>Base</th><th><Bi id="Exclusive s/d" en="Exclusive until" /></th></tr></thead>
        <tbody>
          {loading && <tr><td colSpan={7} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
          {view.map((n) => (
            <tr key={n.niche_id} onClick={() => openRow(n.niche_id)} style={{ cursor: "pointer" }}>
              <td><span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{n.name}</span> <span className="muted mono" style={{ fontSize: "0.6875rem" }}>{n.niche_id}</span></td>
              <td><AccessBadge a={n.access_type} /></td>
              <td className="num">{n.tenant_count}</td><td className="num">{n.video_count}</td><td className="num">{n.avg_viral ?? "—"}</td>
              <td>{n.is_base ? <span className="badge badge-default">base</span> : "—"}</td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{dateID(n.exclusive_until)}</td>
            </tr>
          ))}
        </tbody>
      </table></div></div>

      <div className="nl-section-title"><Calendar size={18} style={{ color: "var(--accent)" }} /> <Bi id="Jadwal Rilis Bulanan" en="Monthly Release Scheduler" /></div>
      <div className="card card-pad">
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "end", marginBottom: "1rem" }}>
          <div><label className="label">Niche</label><select className="input" value={sched.niche_id} onChange={(e) => setSched({ ...sched, niche_id: e.target.value })}><option value="">— pilih —</option>{niches.map((n) => <option key={n.niche_id} value={n.niche_id}>{n.name}</option>)}</select></div>
          <div><label className="label">Tanggal rilis</label><input className="input" type="date" value={sched.date} onChange={(e) => setSched({ ...sched, date: e.target.value })} /></div>
          <button className="btn btn-default btn-sm" disabled={busy || !sched.niche_id || !sched.date} onClick={scheduleRelease}><Plus size={14} /> Jadwalkan</button>
        </div>
        {releases.length === 0 ? <div className="muted" style={{ fontSize: "var(--text-sm)" }}>Belum ada rilis terjadwal.</div> : (
          <div className="nl-rel-grid">{releases.map((r) => {
            const n = niches.find((x) => x.niche_id === r.niche_id);
            return <div className="nl-rel-card" key={r.id}><div style={{ padding: "0.875rem" }}><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{n?.name ?? r.niche_id}</div><div className="muted" style={{ fontSize: "var(--text-xs)", margin: "0.25rem 0 0.5rem", display: "flex", alignItems: "center", gap: ".3rem" }}><Calendar size={11} /> {dateID(r.scheduled_at)}</div><span className={`badge ${r.status === "scheduled" ? "badge-info" : "badge-default"}`}>{r.status}</span></div></div>;
          })}</div>
        )}
      </div>

      <div className="nl-section-title"><Clock size={18} style={{ color: "var(--accent)" }} /> <Bi id="Pipeline Eksklusivitas" en="Exclusivity Pipeline" /></div>
      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr><th>Niche</th><th><Bi id="Exclusive ke" en="Exclusive to" /></th><th><Bi id="Sampai" en="Until" /></th><th></th></tr></thead>
        <tbody>
          {pipeline.length === 0 && <tr><td colSpan={4} className="muted" style={{ padding: "1rem", textAlign: "center" }}>Tidak ada niche eksklusif aktif.</td></tr>}
          {pipeline.map((n) => (
            <tr key={n.niche_id}><td style={{ color: "var(--text-primary)" }}>{n.name}</td><td className="mono" style={{ fontSize: "var(--text-xs)" }}>{n.exclusive_to}</td><td className="muted">{dateID(n.exclusive_until)}</td><td><button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => transition(n.niche_id)}><Bi id="Transisi ke public" en="Transition to public" /></button></td></tr>
          ))}
        </tbody>
      </table></div></div>

      <div className={`nl-scrim${cur ? " open" : ""}`} onClick={() => setSel(null)} />
      <aside className={`nl-drawer${cur ? " open" : ""}`}>
        {cur && (<>
          <div className="nl-drawer-head">
            <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}>{cur.name}</div><div className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{cur.niche_id}</div></div>
            <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button>
          </div>
          <div className="nl-drawer-tabs">{DTABS.map((l, i) => <button key={l} className={`nl-dtab${dtab === i ? " active" : ""}`} onClick={() => setDtab(i)}>{l}</button>)}</div>
          <div className="nl-dpanel">
            {dtab === 0 && <>
              <div className="nl-fld"><label className="label">Niche key</label><input className="input input-mono" value={cur.niche_id} disabled /></div>
              <div className="nl-fld"><label className="label">Display name</label><input className="input" value={edit.name as string} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">Keywords (pisah koma)</label><textarea className="textarea" rows={2} value={edit.keywords as string} onChange={(e) => setEdit({ ...edit, keywords: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">Default hashtags (pisah koma)</label><textarea className="textarea" rows={2} value={edit.default_hashtags as string} onChange={(e) => setEdit({ ...edit, default_hashtags: e.target.value })} /></div>
              <div className="nl-fld" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)" }}>is_active</span><label className="switch"><input type="checkbox" checked={!!edit.is_active} onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
              <div className="nl-fld" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)" }}>is_base <span className="muted">(trial/starter only)</span></span><label className="switch"><input type="checkbox" checked={!!edit.is_base} onChange={(e) => setEdit({ ...edit, is_base: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
            </>}
            {dtab === 1 && <div className="nl-fld"><label className="label">voice_profile JSON</label><textarea className="textarea input-mono" rows={8} value={edit.voice_profile as string} onChange={(e) => setEdit({ ...edit, voice_profile: e.target.value })} /></div>}
            {dtab === 2 && <div className="nl-fld"><label className="label">visual_style JSON</label><textarea className="textarea input-mono" rows={8} value={edit.visual_style as string} onChange={(e) => setEdit({ ...edit, visual_style: e.target.value })} /></div>}
            {dtab === 3 && <>
              <div className="nl-fld"><label className="label">mood_priority JSON</label><textarea className="textarea input-mono" rows={5} value={edit.mood_priority as string} onChange={(e) => setEdit({ ...edit, mood_priority: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">emotion_scoring_criteria</label><textarea className="textarea" rows={3} value={edit.emotion_scoring_criteria as string} onChange={(e) => setEdit({ ...edit, emotion_scoring_criteria: e.target.value })} /></div>
            </>}
            {dtab === 4 && (
              <div className="card card-pad" style={{ background: "var(--bg)" }}>
                <div style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Tag Pool — belum tersedia</div>
                <div className="muted" style={{ fontSize: "var(--text-xs)", lineHeight: 1.6 }}>
                  Sistem tag (Layer-2) menyentuh <b>mesin produksi</b> (perlu <span className="mono">videos.topic_tags</span> + assignment di pipeline + insight per-tag) → dibangun sebagai <b>epik terpisah</b> (MULTI_FORMAT §0 / Phase 6.4 deferred), bukan bagian wiring admin ini.
                </div>
              </div>
            )}
            {dtab === 5 && <>
              <div className="nl-fld"><label className="label">access_type</label>
                {[["public", "🌍 Public"], ["pending", "📅 Pending rilis"], ["private", "🔒 Private Exclusive"]].map(([v, l]) => (
                  <div key={v} className={`nl-radio-card${edit.access_type === v ? " sel" : ""}`} style={{ cursor: "pointer" }} onClick={() => setEdit({ ...edit, access_type: v })}>{l}</div>
                ))}
              </div>
              <div className="nl-fld"><label className="label">exclusive_to (tenant_id)</label><input className="input input-mono" value={edit.exclusive_to as string} onChange={(e) => setEdit({ ...edit, exclusive_to: e.target.value })} placeholder="(kosong = tak eksklusif)" /></div>
              <div className="nl-fld" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div><label className="label">exclusive_until</label><input className="input" type="date" value={(edit.exclusive_until as string)?.slice(0, 10) ?? ""} onChange={(e) => setEdit({ ...edit, exclusive_until: e.target.value })} /></div>
                <div><label className="label">released_at</label><input className="input" type="date" value={(edit.released_at as string)?.slice(0, 10) ?? ""} onChange={(e) => setEdit({ ...edit, released_at: e.target.value })} /></div>
              </div>
            </>}
          </div>
          <div style={{ padding: "1rem 1.25rem", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setSel(null)}><Bi id="Batal" en="Cancel" /></button>
            <button className="btn btn-secondary" disabled={busy} onClick={() => testNiche(cur.niche_id)} title="Produksi 1 video uji di channel admin-test (private)"><Bi id="Test niche" en="Test niche" /></button>
            {dtab !== 4 && <button className="btn btn-default" disabled={busy} onClick={save}><Bi id="Simpan" en="Save" /></button>}
          </div>
        </>)}
      </aside>

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "var(--surface-raised, #1f2937)", color: "var(--text-primary)", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid var(--border)" }}>{toast}</div>}
    </>
  );
}
