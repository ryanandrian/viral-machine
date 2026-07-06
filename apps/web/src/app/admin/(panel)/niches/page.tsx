"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, X, Clock, Sparkles, Check, Search, ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import NicheDnaEditor, { type NicheRow } from "@/components/niche-dna-editor";
import TestNichePanel from "@/components/test-niche-panel";
import "./niches.css";

// E2.3 Admin Niche Library (Phase 10.3) — DATA NYATA via /api/admin/niches (service_role).
// Identity + Access/Exclusivity editable; Voice/Visual/Music DNA = edit JSON; pipeline eksklusivitas real.
// "Jadwal Rilis Bulanan" DIHAPUS TUNTAS 2026-07-04 (owner): penjadwal tanpa eksekutor (tak ada worker/cron
// yang merilis pada tanggalnya) → niche 'pending' tersembunyi selamanya = jebakan; tabel niche_releases 0 baris.
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
// Drawer 2 tab (2026-07-04): DNA = editor bersama admin+tenant (NicheDnaEditor, nol JSON mentah);
// Access = kontrol admin (is_active/is_base/access/exclusive). Tag Pool = epik terpisah (deferred).
const DTABS = ["DNA", "Access & Exclusivity"];
function AccessBadge({ a }: { a: string }) {
  if (a === "public") return <span className="badge badge-success"><span className="dot" />🌍 Public</span>;
  return <span className="badge badge-brand">🔒 Private</span>;
}
const dateID = (iso: string | null) => iso ? new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "—";

export default function AdminNichesPage() {
  const [niches, setNiches] = useState<Niche[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  useEffect(() => { const v = new URLSearchParams(window.location.search).get("q"); if (v) setQ(v); }, []);
  // Sorting kolom: klik header = asc → desc → reset (default: nama abjad).
  const [sort, setSort] = useState<{ key: "name" | "tenant" | "video" | "score"; dir: 1 | -1 } | null>(null);
  const cycleSort = (key: "name" | "tenant" | "video" | "score") =>
    setSort((s) => (!s || s.key !== key) ? { key, dir: 1 } : s.dir === 1 ? { key, dir: -1 } : null);
  const [sel, setSel] = useState<string | null>(null);
  const [dtab, setDtab] = useState(0);
  const [edit, setEdit] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  type NReq = { request_id: string; tenant_id: string; tenant_email: string | null; request_type: string; title: string; clues: Record<string, string>; status: string; created_at: string; niche_id: string | null };
  const [reqs, setReqs] = useState<NReq[]>([]);
  const [actModal, setActModal] = useState<{ req: NReq; action: "mark_paid" | "deliver"; note: string } | null>(null);
  // F3-01: buat niche baru dari nol (POST /api/admin/niches; detail diedit via drawer/PATCH).
  const [newN, setNewN] = useState<{ niche_id: string; name: string; is_base: boolean; access_type: string; template_niche_id?: string } | null>(null);
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
    if (r.ok) { const j = await r.json(); setNiches(j.niches); }
    if (rq.ok) { const j = await rq.json(); setReqs(j.requests ?? []); }
    setLoading(false);
  }, []);

  async function processReq(request_id: string, action: string, extra?: { niche_id?: string; delivery_note?: string }) {
    setBusy(true);
    const r = await fetch("/api/admin/niche-requests", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id, action, ...(extra || {}) }) });
    setBusy(false); setActModal(null);
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setToast("Tersimpan"); await load(); }
    else setToast(j.error || "Gagal");
  }
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2400); return () => clearTimeout(t); }, [toast]);
  useEffect(() => { const k = (e: KeyboardEvent) => { if (e.key === "Escape") setSel(null); }; document.addEventListener("keydown", k); return () => document.removeEventListener("keydown", k); }, []);

  const view = (() => {
    const ql = q.trim().toLowerCase();
    const out = niches.filter((n) =>
      (filter === "all" || (filter === "active" && n.access_type === "public" && n.is_active) || n.access_type === filter)
      && (!ql || n.name.toLowerCase().includes(ql) || n.niche_id.toLowerCase().includes(ql)));
    if (sort) {
      const d = sort.dir;
      out.sort((a, b) =>
        sort.key === "name" ? d * a.name.localeCompare(b.name)
        : sort.key === "tenant" ? d * (a.tenant_count - b.tenant_count)
        : sort.key === "video" ? d * (a.video_count - b.video_count)
        : d * ((a.avg_viral ?? -1) - (b.avg_viral ?? -1)));
    }
    return out;
  })();
  const cur = sel ? niches.find((n) => n.niche_id === sel) ?? null : null;
  const pipeline = niches.filter((n) => n.exclusive_to);

  function openRow(id: string) {
    const n = niches.find((x) => x.niche_id === id); setSel(id); setDtab(0);
    // edit = HANYA field Access & status (DNA ditangani NicheDnaEditor — editor bersama admin+tenant).
    setEdit(n ? {
      is_active: n.is_active, is_base: n.is_base, access_type: n.access_type, exclusive_to: n.exclusive_to ?? "",
      exclusive_until: n.exclusive_until ?? "", released_at: n.released_at ?? "",
    } : {});
  }

  async function saveDna(patch: Record<string, unknown>) {
    if (!cur) return { ok: false };
    setBusy(true);
    const r = await fetch(`/api/admin/niches/${cur.niche_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { setToast("DNA tersimpan"); setSel(null); await load(); return { ok: true }; }
    setToast(j.error === "dna_invalid" ? "Ada isian tidak valid" : (j.error || "Gagal menyimpan"));
    return { ok: false, fields: j.fields };
  }

  async function saveAccess() {
    if (!cur) return;
    setBusy(true);
    const patch: Record<string, unknown> = {
      is_active: edit.is_active, is_base: edit.is_base,
      access_type: edit.access_type, exclusive_to: (edit.exclusive_to as string) || null,
      exclusive_until: (edit.exclusive_until as string) || null, released_at: (edit.released_at as string) || null,
    };
    const r = await fetch(`/api/admin/niches/${cur.niche_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
    setBusy(false);
    if (r.ok) { setToast("Akses tersimpan"); setSel(null); await load(); } else setToast("Gagal menyimpan");
  }
  async function transition(id: string) {
    setBusy(true);
    const r = await fetch(`/api/admin/niches/${id}/transition`, { method: "POST" });
    setBusy(false);
    if (r.ok) { setToast("Niche → public"); await load(); } else setToast("Gagal");
  }
  return (
    <>
      <div className="nl-head">
        <div>
          <h1><Bi id="Niche Library" en="Niche Library" /></h1>
          <div className="nl-stat-line">
            <span><b>{niches.filter((n) => n.is_active).length}</b> Active</span>
            <span><b>{niches.filter((n) => n.access_type === "private").length}</b> Private</span>
            <span><b>{niches.filter((n) => n.is_base).length}</b> Base</span>
          </div>
        </div>
        <button className="btn btn-default" onClick={() => setNewN({ niche_id: "", name: "", is_base: false, access_type: "public" })}><Plus size={15} /> <Bi id="Niche baru" en="New niche" /></button>
      </div>

      <div className="nl-filters" style={{ display: "flex", gap: ".625rem", alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ position: "relative", minWidth: 240 }}>
          <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", pointerEvents: "none" }} />
          <input className="input" style={{ paddingLeft: 32 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari niche / niche_id…" />
        </div>
        <div className="segmented">
        {[["all", "All"], ["active", "Active"], ["private", "Private"]].map(([k, l]) => <button key={k} aria-selected={filter === k} onClick={() => setFilter(k)}>{l}</button>)}
      </div></div>

      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl nl-tbl">
        <thead><tr>
          <th onClick={() => cycleSort("name")} style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }} aria-sort={sort?.key === "name" ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Bi id="Niche" en="Niche" />{sort?.key === "name" ? (sort.dir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} style={{ opacity: .35 }} />}</span></th>
          <th>Status</th><th>Access</th>
          {([["tenant", "Tenant"], ["video", "Video"], ["score", "Avg score"]] as ["tenant" | "video" | "score", string][]).map(([k, l]) => (
            <th key={k} className="num" onClick={() => cycleSort(k)} style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }} aria-sort={sort?.key === k ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>{l}{sort?.key === k ? (sort.dir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} style={{ opacity: .35 }} />}</span></th>))}
          <th>Base</th><th><Bi id="Exclusive s/d" en="Exclusive until" /></th>
        </tr></thead>
        <tbody>
          {loading && <tr><td colSpan={8} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
          {!loading && view.length === 0 && <tr><td colSpan={8} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}><Bi id="Tidak ada niche yang cocok." en="No matching niche." /></td></tr>}
          {view.map((n) => (
            <tr key={n.niche_id} onClick={() => openRow(n.niche_id)} style={{ cursor: "pointer" }}>
              <td><span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{n.name}</span> <span className="muted mono" style={{ fontSize: "0.6875rem" }}>{n.niche_id}</span></td>
              <td>{n.is_active
                ? <span className="badge badge-success"><span className="dot" />Aktif</span>
                : <span className="badge badge-warning"><span className="dot" />Nonaktif</span>}</td>
              <td><AccessBadge a={n.access_type} /></td>
              <td className="num">{n.tenant_count}</td><td className="num">{n.video_count}</td><td className="num">{n.avg_viral ?? "—"}</td>
              <td>{n.is_base ? <span className="badge badge-default">base</span> : "—"}</td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{dateID(n.exclusive_until)}</td>
            </tr>
          ))}
        </tbody>
      </table></div></div>
      {!loading && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".5rem" }}>{view.length} niche</div>}

      <div className="nl-section-title"><Sparkles size={18} style={{ color: "var(--accent)" }} /> <Bi id="Pengajuan Custom Niche" en="Custom Niche Requests" /> {reqs.filter((r) => r.status === "pending").length > 0 && <span className="badge badge-info">{reqs.filter((r) => r.status === "pending").length} pending</span>}</div>
      <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.75rem", lineHeight: 1.6 }}>
        <Bi id="Alur: 1) Terima (kirim tagihan ke tenant) → 2) Tandai lunas (niche dibuat, BELUM aktif) → 3) klik niche_id untuk isi DNA-nya (drawer) → 4) Serahkan (niche aktif + email + masa evaluasi tenant). Tenant lalu Terima/Minta-perbaikan."
          en="Flow: 1) Accept (sends invoice) → 2) Mark paid (niche created, INACTIVE) → 3) click the niche_id to fill its DNA (drawer) → 4) Deliver (activates niche + email + tenant evaluation). Tenant then Accepts/Requests revision." />
      </div>
      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr><th>Tenant</th><th>Tipe</th><th><Bi id="Ide & clue" en="Idea & clues" /></th><th>Status</th><th></th></tr></thead>
        <tbody>
          {reqs.length === 0 && <tr><td colSpan={5} className="muted" style={{ padding: "1.25rem", textAlign: "center" }}><Bi id="Belum ada pengajuan." en="No requests yet." /></td></tr>}
          {reqs.map((r) => (
            <tr key={r.request_id}>
              <td style={{ fontSize: "var(--text-xs)" }}>{r.tenant_email ?? r.tenant_id.slice(0, 8)}</td>
              <td><span className={`badge ${r.request_type === "private" ? "badge-brand" : "badge-default"}`}>{r.request_type === "private" ? "🔒 Private" : "🌍 90d"}</span></td>
              <td style={{ maxWidth: 360 }}><div style={{ color: "var(--text-primary)", fontWeight: 500 }}>{r.title}</div><div className="muted" style={{ fontSize: "0.6875rem" }}>{[r.clues?.audience, r.clues?.references, r.clues?.viral_angle].filter(Boolean).join(" · ") || "—"}</div></td>
              <td><span className={`badge ${r.status === "closed" || r.status === "live" ? "badge-success" : r.status === "rejected" || r.status === "cancelled" ? "badge-default" : r.status === "awaiting_payment" ? "badge-warning" : "badge-info"}`}>{r.status}</span>{r.niche_id ? <button className="btn btn-ghost btn-sm mono" style={{ fontSize: "0.6875rem", marginLeft: ".35rem", padding: "0 .35rem", height: "1.5rem" }} title="Buka editor DNA niche" onClick={() => openRow(r.niche_id!)}>{r.niche_id} ✎</button> : null}</td>
              <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                {r.status === "pending" && <>
                  <button className="btn btn-default btn-sm" disabled={busy} onClick={() => processReq(r.request_id, "accept")}><Check size={13} /> Terima</button>
                  <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => processReq(r.request_id, "reject")}>Tolak</button>
                </>}
                {r.status === "awaiting_payment" && <div><button className="btn btn-default btn-sm" disabled={busy} onClick={() => setActModal({ req: r, action: "mark_paid", note: "" })}>Tandai lunas</button><div className="muted" style={{ fontSize: "0.625rem", marginTop: 2 }}>bila bayar offline</div></div>}
                {r.status === "in_progress" && <div><button className="btn btn-default btn-sm" disabled={busy} onClick={() => setActModal({ req: r, action: "deliver", note: "" })}>Serahkan</button><div className="muted" style={{ fontSize: "0.625rem", marginTop: 2 }}>isi DNA dulu (klik {r.niche_id})</div></div>}
                {r.status === "delivered" && <span className="muted" style={{ fontSize: "0.6875rem" }}>menunggu evaluasi tenant</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table></div></div>

      {actModal && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setActModal(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card card-pad" style={{ maxWidth: 480, width: "100%" }}>
            {actModal.action === "mark_paid" ? <>
              <h3 className="card-title" style={{ marginBottom: ".5rem" }}><Bi id="Tandai lunas (bayar offline)" en="Mark paid (offline)" /></h3>
              <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: ".75rem" }}>{actModal.req.title} · {actModal.req.request_type === "private" ? "permanen private" : "exclusive 90 hari → public"} · {actModal.req.tenant_email ?? actModal.req.tenant_id.slice(0, 8)}. <Bi id="Niche dibuat OTOMATIS (belum aktif) — lalu isi DNA via drawer Niche Library & Serahkan. Pakai ini HANYA bila bayar di luar Midtrans; bayar via Midtrans memajukan status otomatis." en="The niche is created AUTOMATICALLY (inactive) — then fill its DNA via the Niche Library drawer & Deliver. Use this ONLY for payments outside Midtrans; paying via Midtrans advances the status automatically." /></p>
              <div style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end", marginTop: "1rem" }}>
                <button className="btn btn-ghost" onClick={() => setActModal(null)}><Bi id="Batal" en="Cancel" /></button>
                <button className="btn btn-default" disabled={busy} onClick={() => processReq(actModal.req.request_id, "mark_paid")}><Check size={14} /> <Bi id="Tandai lunas & buat niche" en="Mark paid & create niche" /></button>
              </div>
            </> : <>
              <h3 className="card-title" style={{ marginBottom: ".5rem" }}><Bi id="Serahkan niche ke tenant" en="Deliver niche to tenant" /></h3>
              <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: ".75rem" }}>Pastikan DNA niche <b>{actModal.req.niche_id}</b> sudah diisi (Niche Library). Menyerahkan akan <b>mengaktifkan</b> niche + kirim email serah-terima + mulai masa evaluasi tenant.</p>
              <label className="label"><Bi id="Tautan video contoh / catatan (opsional)" en="Sample video link / note (optional)" /></label>
              <textarea className="textarea" rows={3} value={actModal.note} onChange={(e) => setActModal({ ...actModal, note: e.target.value })} placeholder="mis. https://youtube.com/shorts/... (video uji dari Test niche)" />
              <div style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end", marginTop: "1rem" }}>
                <button className="btn btn-ghost" onClick={() => setActModal(null)}>Batal</button>
                <button className="btn btn-default" disabled={busy} onClick={() => processReq(actModal.req.request_id, "deliver", { delivery_note: actModal.note })}><Check size={14} /> Serahkan & aktifkan</button>
              </div>
            </>}
          </div>
        </div>
      )}

      {newN && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setNewN(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card card-pad" style={{ maxWidth: 460, width: "100%" }}>
            <h3 className="card-title" style={{ marginBottom: ".75rem" }}><Bi id="Niche baru" en="New niche" /></h3>
            <div className="nl-fld"><label className="label">niche_id (slug a-z0-9_)</label><input className="input input-mono" value={newN.niche_id} onChange={(e) => setNewN({ ...newN, niche_id: e.target.value })} placeholder="mis. dark_history" /></div>
            <div className="nl-fld"><label className="label"><Bi id="Nama tampilan" en="Display name" /></label><input className="input" value={newN.name} onChange={(e) => setNewN({ ...newN, name: e.target.value })} /></div>
            <div className="nl-fld"><label className="label">access_type</label><select className="input" value={newN.access_type} onChange={(e) => setNewN({ ...newN, access_type: e.target.value })}><option value="public">🌍 Public</option><option value="private">🔒 Private</option></select></div>
            <label style={{ display: "flex", alignItems: "center", gap: ".5rem", fontSize: "var(--text-sm)", margin: ".4rem 0" }}><input type="checkbox" checked={newN.is_base} onChange={(e) => setNewN({ ...newN, is_base: e.target.checked })} /> is_base (trial/starter)</label>
            <div className="nl-fld"><label className="label"><Bi id="Mulai dari template" en="Start from template" /></label>
              <select className="input" value={newN.template_niche_id ?? ""} onChange={(e) => setNewN({ ...newN, template_niche_id: e.target.value })}>
                <option value="">— kosong / blank —</option>
                {niches.filter((n) => n.is_base).map((n) => <option key={n.niche_id} value={n.niche_id}>{n.name}</option>)}
              </select>
              <div className="muted" style={{ fontSize: "0.6875rem", marginTop: ".25rem" }}><Bi id="Gaya narasi/visual/musik/struktur di-copy sebagai titik awal (keywords TIDAK — spesifik topik)." en="Narration/visual/music/structure copied as a start (keywords NOT — topic-specific)." /></div>
            </div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".25rem 0 .5rem" }}><Bi id="Detail DNA disempurnakan di drawer setelah dibuat." en="DNA detail refined in the drawer after creation." /></div>
            <div style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
              <button className="btn btn-ghost" onClick={() => setNewN(null)}>Batal</button>
              <button className="btn btn-default" disabled={busy || !/^[a-z0-9_]+$/.test(newN.niche_id)} onClick={createNiche}><Check size={14} /> <Bi id="Buat niche" en="Create niche" /></button>
            </div>
          </div>
        </div>
      )}

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
          <div style={{ padding: "0.75rem 1.25rem 0" }}>
            <TestNichePanel key={cur.niche_id}
              getUrl={`/api/admin/niches/${cur.niche_id}/test`}
              postUrl={`/api/admin/niches/${cur.niche_id}/test`}
              confirmMessage={<Bi id="Mesin akan memproduksi 1 video uji NYATA memakai kredensial AI admin (ada biaya provider). TIDAK dipublish ke YouTube — hasil bisa ditonton di panel ini dan otomatis terhapus dari penyimpanan setelah ±3 hari." en="The engine will produce 1 REAL test video using the admin AI credentials (real provider cost). It is NOT published to YouTube — watch the result in this panel; storage is auto-cleaned after ~3 days." />} />
          </div>
          <div className="nl-drawer-tabs">{DTABS.map((l, i) => <button key={l} className={`nl-dtab${dtab === i ? " active" : ""}`} onClick={() => setDtab(i)}>{l}</button>)}</div>
          <div className="nl-dpanel">
            {dtab === 0 && <NicheDnaEditor key={cur.niche_id} niche={cur as unknown as NicheRow} onSave={saveDna} busy={busy} />}
            {dtab === 1 && <>
              <div className="nl-fld" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)" }}>is_active</span><label className="switch"><input type="checkbox" checked={!!edit.is_active} onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
              <div className="nl-fld" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)" }}>is_base <span className="muted">(trial/starter only)</span></span><label className="switch"><input type="checkbox" checked={!!edit.is_base} onChange={(e) => setEdit({ ...edit, is_base: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
              <div className="nl-fld"><label className="label">access_type</label>
                {[["public", "🌍 Public"], ["private", "🔒 Private Exclusive"]].map(([v, l]) => (
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
            {dtab === 1 && <button className="btn btn-default" disabled={busy} onClick={saveAccess}><Bi id="Simpan akses" en="Save access" /></button>}
          </div>
        </>)}
      </aside>

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "#1f2937", color: "#fff", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)", boxShadow: "0 6px 20px rgba(0,0,0,0.35)", fontSize: "var(--text-sm)" }}>{toast}</div>}
    </>
  );
}
