"use client";

import { useState, useEffect, useCallback } from "react";
import { Calendar, Plus, X, Clock, Sparkles, Check } from "lucide-react";
import { YT_CATEGORIES } from "@/lib/youtube-categories";
import "./niches.css";

// E2.3 Admin Niche Library (Phase 10.3) — DATA NYATA via /api/admin/niches (service_role).
// Identity + Access/Exclusivity editable; Voice/Visual/Music DNA = edit JSON; monthly-release + pipeline real.
// TAG POOL = placeholder jujur (epik pipeline Layer-2, belum dibangun — MULTI_FORMAT §0). Prefix nl-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Niche = {
  niche_id: string; name: string; keywords: unknown; default_hashtags: unknown; youtube_category_id: string | null; is_active: boolean; is_base: boolean;
  access_type: string; exclusive_to: string | null; exclusive_until: string | null; released_at: string | null;
  narration_persona: unknown; visual_style: unknown; mood_priority: unknown; emotion_scoring_criteria: string | null;
  image_quality_tags: unknown; image_negative_prompt: string | null; visual_fallbacks: unknown; section_timing: unknown; music_config: unknown;
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
  type NReq = { request_id: string; tenant_id: string; tenant_email: string | null; request_type: string; title: string; clues: Record<string, string>; status: string; created_at: string; niche_id: string | null };
  const [reqs, setReqs] = useState<NReq[]>([]);
  const [appr, setAppr] = useState<{ req: NReq; niche_id: string } | null>(null);
  // F3-01: buat niche baru dari nol (POST /api/admin/niches; detail diedit via drawer/PATCH).
  const [newN, setNewN] = useState<{ niche_id: string; name: string; is_base: boolean; access_type: string } | null>(null);
  async function createNiche() {
    if (!newN) return;
    setBusy(true);
    const r = await fetch("/api/admin/niches", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newN) });
    setBusy(false);
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setToast(`Niche dibuat: ${j.row?.niche_id ?? newN.niche_id}`); setNewN(null); await load(); }
    else setToast(j.error || "Gagal buat niche");
  }

  const load = useCallback(async () => {
    setLoading(true);
    const [r, rq] = await Promise.all([fetch("/api/admin/niches"), fetch("/api/admin/niche-requests")]);
    if (r.ok) { const j = await r.json(); setNiches(j.niches); setReleases(j.releases); }
    if (rq.ok) { const j = await rq.json(); setReqs(j.requests ?? []); }
    setLoading(false);
  }, []);

  async function processReq(request_id: string, action: "approve" | "reject", niche_id?: string) {
    setBusy(true);
    const r = await fetch("/api/admin/niche-requests", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id, action, niche_id }) });
    setBusy(false); setAppr(null);
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setToast(action === "approve" ? `Niche dibuat: ${j.niche_id}` : "Request ditolak"); await load(); }
    else setToast(j.error || "Gagal");
  }
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
      youtube_category_id: n.youtube_category_id ?? "",
      is_active: n.is_active, is_base: n.is_base, access_type: n.access_type, exclusive_to: n.exclusive_to ?? "",
      exclusive_until: n.exclusive_until ?? "", released_at: n.released_at ?? "",
      narration_persona: jstr(n.narration_persona), music_config: jstr(n.music_config), visual_style: jstr(n.visual_style), mood_priority: jstr(n.mood_priority),
      emotion_scoring_criteria: n.emotion_scoring_criteria ?? "",
      image_quality_tags: asArr(n.image_quality_tags).join(", "), image_negative_prompt: n.image_negative_prompt ?? "",
      visual_fallbacks: asArr(n.visual_fallbacks).join(", "), section_timing: jstr(n.section_timing),
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
      image_negative_prompt: (edit.image_negative_prompt as string) || null,
      keywords: String(edit.keywords || "").split(",").map((s) => s.trim()).filter(Boolean),
      default_hashtags: String(edit.default_hashtags || "").split(",").map((s) => s.trim()).filter(Boolean),
      image_quality_tags: String(edit.image_quality_tags || "").split(",").map((s) => s.trim()).filter(Boolean),
      visual_fallbacks: String(edit.visual_fallbacks || "").split(",").map((s) => s.trim()).filter(Boolean),
      youtube_category_id: (edit.youtube_category_id as string) || null,
    };
    for (const [k, v] of [["narration_persona", edit.narration_persona], ["music_config", edit.music_config], ["visual_style", edit.visual_style], ["mood_priority", edit.mood_priority], ["section_timing", edit.section_timing]] as const) {
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
        <button className="btn btn-default" onClick={() => setNewN({ niche_id: "", name: "", is_base: false, access_type: "public" })}><Plus size={15} /> <Bi id="Niche baru" en="New niche" /></button>
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

      <div className="nl-section-title"><Sparkles size={18} style={{ color: "var(--accent)" }} /> <Bi id="Pengajuan Custom Niche" en="Custom Niche Requests" /> {reqs.filter((r) => r.status === "pending").length > 0 && <span className="badge badge-info">{reqs.filter((r) => r.status === "pending").length} pending</span>}</div>
      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr><th>Tenant</th><th>Tipe</th><th><Bi id="Ide & clue" en="Idea & clues" /></th><th>Status</th><th></th></tr></thead>
        <tbody>
          {reqs.length === 0 && <tr><td colSpan={5} className="muted" style={{ padding: "1.25rem", textAlign: "center" }}><Bi id="Belum ada pengajuan." en="No requests yet." /></td></tr>}
          {reqs.map((r) => (
            <tr key={r.request_id}>
              <td style={{ fontSize: "var(--text-xs)" }}>{r.tenant_email ?? r.tenant_id.slice(0, 8)}</td>
              <td><span className={`badge ${r.request_type === "private" ? "badge-brand" : "badge-default"}`}>{r.request_type === "private" ? "🔒 Private" : "🌍 90d"}</span></td>
              <td style={{ maxWidth: 360 }}><div style={{ color: "var(--text-primary)", fontWeight: 500 }}>{r.title}</div><div className="muted" style={{ fontSize: "0.6875rem" }}>{[r.clues?.audience, r.clues?.references, r.clues?.viral_angle].filter(Boolean).join(" · ") || "—"}</div></td>
              <td><span className={`badge ${r.status === "pending" ? "badge-info" : r.status === "live" ? "badge-success" : "badge-default"}`}>{r.status}{r.niche_id ? ` · ${r.niche_id}` : ""}</span></td>
              <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                {r.status === "pending" && <>
                  <button className="btn btn-default btn-sm" disabled={busy} onClick={() => setAppr({ req: r, niche_id: r.title.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 40) })}><Check size={13} /> Approve</button>
                  <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => processReq(r.request_id, "reject")}>Tolak</button>
                </>}
              </td>
            </tr>
          ))}
        </tbody>
      </table></div></div>

      {appr && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setAppr(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card card-pad" style={{ maxWidth: 460, width: "100%" }}>
            <h3 className="card-title" style={{ marginBottom: ".75rem" }}><Bi id="Buat niche eksklusif" en="Create exclusive niche" /></h3>
            <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: ".75rem" }}>{appr.req.title} · {appr.req.request_type === "private" ? "permanen private" : "exclusive 90 hari → public"} · untuk {appr.req.tenant_email ?? appr.req.tenant_id.slice(0, 8)}</p>
            <label className="label">niche_id (slug a-z0-9_)</label>
            <input className="input input-mono" value={appr.niche_id} onChange={(e) => setAppr({ ...appr, niche_id: e.target.value })} />
            <div style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end", marginTop: "1rem" }}>
              <button className="btn btn-ghost" onClick={() => setAppr(null)}>Batal</button>
              <button className="btn btn-default" disabled={busy || !/^[a-z0-9_]+$/.test(appr.niche_id)} onClick={() => processReq(appr.req.request_id, "approve", appr.niche_id)}><Check size={14} /> Buat & tetapkan eksklusif</button>
            </div>
          </div>
        </div>
      )}

      {newN && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setNewN(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card card-pad" style={{ maxWidth: 460, width: "100%" }}>
            <h3 className="card-title" style={{ marginBottom: ".75rem" }}><Bi id="Niche baru" en="New niche" /></h3>
            <div className="nl-fld"><label className="label">niche_id (slug a-z0-9_)</label><input className="input input-mono" value={newN.niche_id} onChange={(e) => setNewN({ ...newN, niche_id: e.target.value })} placeholder="mis. dark_history" /></div>
            <div className="nl-fld"><label className="label"><Bi id="Nama tampilan" en="Display name" /></label><input className="input" value={newN.name} onChange={(e) => setNewN({ ...newN, name: e.target.value })} /></div>
            <div className="nl-fld"><label className="label">access_type</label><select className="input" value={newN.access_type} onChange={(e) => setNewN({ ...newN, access_type: e.target.value })}><option value="public">🌍 Public</option><option value="pending">📅 Pending</option><option value="private">🔒 Private</option></select></div>
            <label style={{ display: "flex", alignItems: "center", gap: ".5rem", fontSize: "var(--text-sm)", margin: ".4rem 0" }}><input type="checkbox" checked={newN.is_base} onChange={(e) => setNewN({ ...newN, is_base: e.target.checked })} /> is_base (trial/starter)</label>
            <div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".25rem 0 .5rem" }}><Bi id="Detail DNA (voice/visual/timing) diedit di drawer setelah dibuat." en="DNA detail (voice/visual/timing) edited in the drawer after creation." /></div>
            <div style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
              <button className="btn btn-ghost" onClick={() => setNewN(null)}>Batal</button>
              <button className="btn btn-default" disabled={busy || !/^[a-z0-9_]+$/.test(newN.niche_id)} onClick={createNiche}><Check size={14} /> <Bi id="Buat niche" en="Create niche" /></button>
            </div>
          </div>
        </div>
      )}

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
              <div className="nl-fld"><label className="label">Kategori YouTube <span className="muted" style={{ fontWeight: 400, fontSize: "var(--text-xs)" }}>(categoryId saat publish)</span></label><select className="input" value={(edit.youtube_category_id as string) ?? ""} onChange={(e) => setEdit({ ...edit, youtube_category_id: e.target.value })}><option value="">— pilih (default Education) —</option>{YT_CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
              <div className="nl-fld" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)" }}>is_active</span><label className="switch"><input type="checkbox" checked={!!edit.is_active} onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
              <div className="nl-fld" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)" }}>is_base <span className="muted">(trial/starter only)</span></span><label className="switch"><input type="checkbox" checked={!!edit.is_base} onChange={(e) => setEdit({ ...edit, is_base: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
            </>}
            {dtab === 1 && <>
              <div className="nl-fld"><label className="label">narration_persona JSON <span className="muted" style={{ fontWeight: 400, fontSize: "var(--text-xs)" }}>gaya/tone narasi (membentuk TEKS via LLM — BUKAN pemilih suara; voice = channel)</span></label><textarea className="textarea input-mono" rows={6} value={edit.narration_persona as string} onChange={(e) => setEdit({ ...edit, narration_persona: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">music_config JSON <span className="muted" style={{ fontWeight: 400, fontSize: "var(--text-xs)" }}>{'{"mode":"auto|random|fixed","mood":"…","track_id":"…"}'} — §3#24/§10.G (auto=ikut naskah · random=acak di mood · fixed=1 track)</span></label><textarea className="textarea input-mono" rows={3} value={edit.music_config as string} onChange={(e) => setEdit({ ...edit, music_config: e.target.value })} placeholder={'{"mode":"auto"}'} /></div>
            </>}
            {dtab === 2 && <>
              <div className="nl-fld"><label className="label">visual_style JSON</label><textarea className="textarea input-mono" rows={5} value={edit.visual_style as string} onChange={(e) => setEdit({ ...edit, visual_style: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">image_quality_tags <span className="muted" style={{ fontWeight: 400, fontSize: "var(--text-xs)" }}>(pisah koma)</span></label><textarea className="textarea" rows={2} value={edit.image_quality_tags as string} onChange={(e) => setEdit({ ...edit, image_quality_tags: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">image_negative_prompt</label><textarea className="textarea" rows={2} value={edit.image_negative_prompt as string} onChange={(e) => setEdit({ ...edit, image_negative_prompt: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">visual_fallbacks <span className="muted" style={{ fontWeight: 400, fontSize: "var(--text-xs)" }}>(pisah koma)</span></label><textarea className="textarea" rows={2} value={edit.visual_fallbacks as string} onChange={(e) => setEdit({ ...edit, visual_fallbacks: e.target.value })} /></div>
            </>}
            {dtab === 3 && <>
              <div className="nl-fld"><label className="label">mood_priority JSON</label><textarea className="textarea input-mono" rows={4} value={edit.mood_priority as string} onChange={(e) => setEdit({ ...edit, mood_priority: e.target.value })} /></div>
              <div className="nl-fld"><label className="label">section_timing JSON <span className="muted" style={{ fontWeight: 400, fontSize: "var(--text-xs)" }}>(durasi per-section, detik)</span></label><textarea className="textarea input-mono" rows={4} value={edit.section_timing as string} onChange={(e) => setEdit({ ...edit, section_timing: e.target.value })} /></div>
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
