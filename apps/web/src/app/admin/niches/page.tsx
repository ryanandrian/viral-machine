"use client";

import { useState, useEffect } from "react";
import { Calendar, Plus, X, ChevronDown, MoreVertical, Play, ImageIcon, Sparkles, Upload, Activity, Clock } from "lucide-react";
import "./niches.css";

// E2.3 Admin Niche Library — port dari design-source/Admin Niches.html (Hybrid). /admin/niches.
// Tabel niche + filter + 6-tab drawer (Identity/Voice/Visual/Music/Tag Pool/Access) + monthly release + pipeline + log.
// Mock deterministik (tag-count diganti dari Math.random); nol wiring Supabase. Prefix nl-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}
function Mood({ cols }: { cols: string[] }) {
  return <span className="nl-mood-mini">{cols.map((c) => <span key={c} style={{ background: c }} />)}</span>;
}

type Access = "public" | "pending" | "private";
const NICHES: [string, string, string[], Access, string, string, string, string][] = [
  ["Misteri Samudra", "ocean_mysteries", ["#082f49", "#0c4a6e", "#0ea5e9"], "public", "142", "3.2K", "2.3K", "—"],
  ["Sejarah Kelam", "dark_history", ["#450a0a", "#7f1d1d", "#dc2626"], "public", "98", "2.1K", "1.9K", "—"],
  ["Fakta Menarik", "fun_facts", ["#052e16", "#14532d", "#22c55e"], "public", "203", "4.1K", "3.1K", "—"],
  ["Misteri Alam Semesta", "universe_mysteries", ["#1e1b4b", "#312e81", "#4338ca"], "public", "76", "1.8K", "2.0K", "—"],
  ["Detektif Kripto", "crypto_detective", ["#14532d", "#15803d", "#22c55e"], "pending", "0", "—", "—", "—"],
  ["Misteri Medis", "medical_mystery", ["#4a044e", "#86198f", "#c026d3"], "pending", "0", "—", "—", "—"],
  ["Arsitektur Hilang", "lost_architecture", ["#1e3a8a", "#1d4ed8", "#3b82f6"], "private", "12", "1", "2.4K", "18 Sep 2026"],
];
function AccessBadge({ a }: { a: Access }) {
  if (a === "public") return <span className="badge badge-success"><span className="dot" />🌍 Public</span>;
  if (a === "pending") return <span className="badge badge-warning"><span className="dot" />📅 Pending</span>;
  return <span className="badge badge-brand">🔒 Private</span>;
}
const FILTERS: [string, string, string][] = [["all", "All", "All"], ["active", "Active", "Active"], ["pending", "Pending Rilis", "Pending"], ["private", "Private", "Private"], ["pipeline", "Public-90d", "Public-90d"], ["archived", "Archived", "Archived"]];
const DTABS = ["Identity", "Voice DNA", "Visual DNA", "Music + Scoring", "Tag Pool", "Access & Exclusivity"];
const REL: [string, string[], string, string][] = [["Detektif Kripto", ["#14532d", "#15803d", "#22c55e"], "1 Jul 2026", "Terjadwal"], ["Misteri Medis", ["#4a044e", "#86198f", "#c026d3"], "15 Jul 2026", "Terjadwal"], ["Arsitektur Hilang", ["#1e3a8a", "#1d4ed8", "#3b82f6"], "1 Agu 2026", "Draft"]];
const PIPE: [string, string, string, number][] = [["Detektif Kripto", "Riko Pratama", "30 Jun 2026", 19], ["Arsitektur Hilang", "Sarah Wibowo", "18 Sep 2026", 99]];
const LOG: [string, string][] = [["Niche 'crypto_detective' dijadwalkan rilis 1 Jul oleh admin@mesinviral", "2 jam lalu"], ["Tag pool 'ocean_mysteries' diperbarui (+3 tag) oleh admin@mesinviral", "1 hari lalu"], ["Niche 'lost_architecture' di-set private exclusive untuk Sarah Wibowo", "3 hari lalu"]];
const TAGS = ["kapal-hantu", "palung-laut", "makhluk-abisal", "kota-tenggelam", "arus-misterius", "pulau-hilang", "bangkai-kapal", "fenomena-laut", "legenda-pelaut", "dasar-samudra", "cahaya-laut", "suara-laut", "gua-bawah-laut", "harta-karun", "monster-laut", "ekspedisi", "sonar-misterius", "kedalaman"];
const tagCt = (i: number) => 3 + ((i * 13) % 40); // deterministik (ganti Math.random)
const TAGPERF: [string, number][] = [["kapal-hantu", 9.2], ["kota-tenggelam", 8.4], ["makhluk-abisal", 7.9], ["palung-laut", 7.1], ["harta-karun", 6.4]];

export default function AdminNichesPage() {
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [dtab, setDtab] = useState(0);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  const rows = NICHES.filter((n) => filter === "all" || n[3] === filter || (filter === "pipeline" && n[3] === "private"));

  return (
    <>
      <div className="nl-head">
        <div>
          <h1><Bi id="Niche Library" en="Niche Library" /></h1>
          <div className="nl-stat-line"><span><b>4</b> Active</span><span><b>2</b> <Bi id="Pending release" en="Pending release" /></span><span><b>1</b> Private exclusive</span><span><b>3</b> <Bi id="Public dari 90d" en="Public from 90d" /></span></div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-secondary"><Calendar size={15} /> <Bi id="Jadwal Rilis Bulanan" en="Monthly Release" /></button>
          <button className="btn btn-default"><Plus size={15} /> <Bi id="Niche Baru" en="New Niche" /></button>
        </div>
      </div>

      <div className="nl-filters"><div className="segmented">{FILTERS.map(([k, id, en]) => <button key={k} aria-selected={filter === k} onClick={() => setFilter(k)}><Bi id={id} en={en} /></button>)}</div></div>

      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl nl-tbl">
        <thead><tr><th><Bi id="Niche" en="Niche" /></th><th>Access</th><th className="num">Tenant</th><th className="num">Video</th><th className="num">Avg perf</th><th><Bi id="Exclusive s/d" en="Exclusive until" /></th></tr></thead>
        <tbody>{rows.map((n) => (
          <tr key={n[1]} onClick={() => { setOpen(true); setDtab(0); }}>
            <td><span style={{ color: "var(--text-primary)", fontWeight: 500 }}><Mood cols={n[2]} />{n[0]}</span> <span className="muted mono" style={{ fontSize: "0.6875rem" }}>{n[1]}</span></td>
            <td><AccessBadge a={n[3]} /></td><td className="num">{n[4]}</td><td className="num">{n[5]}</td><td className="num">{n[6]}</td><td className="muted" style={{ fontSize: "var(--text-xs)" }}>{n[7]}</td>
          </tr>
        ))}</tbody>
      </table></div></div>

      <div className="nl-section-title"><Calendar size={18} style={{ color: "var(--accent)" }} /> <Bi id="Jadwal Rilis Bulanan" en="Monthly Release Scheduler" /></div>
      <div className="card card-pad">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Rilis terjadwal & pengumuman email" en="Scheduled releases & email announcements" /></span>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)" }}><Bi id="Kirim email pengumuman" en="Send announcement email" /><span className="switch"><input type="checkbox" defaultChecked /><span className="track" /><span className="thumb" /></span></label>
        </div>
        <div className="nl-rel-grid">{REL.map(([n, cols, date, st]) => (
          <div className="nl-rel-card" key={n}><div className="mood">{cols.map((c) => <span key={c} style={{ background: c }} />)}</div><div style={{ padding: "0.875rem" }}><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{n}</div><div className="muted" style={{ fontSize: "var(--text-xs)", margin: "0.25rem 0 0.5rem", display: "flex", alignItems: "center", gap: ".3rem" }}><Calendar size={11} /> {date}</div><span className={`badge ${st === "Terjadwal" ? "badge-info" : "badge-default"}`}>{st}</span></div></div>
        ))}</div>
      </div>

      <div className="nl-section-title"><Clock size={18} style={{ color: "var(--accent)" }} /> <Bi id="Pipeline Eksklusivitas" en="Exclusivity Pipeline" /></div>
      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr><th>Niche</th><th><Bi id="Exclusive ke" en="Exclusive to" /></th><th><Bi id="Sampai" en="Until" /></th><th className="num"><Bi id="Sisa hari" en="Days left" /></th><th></th></tr></thead>
        <tbody>{PIPE.map(([n, t, until, days]) => (
          <tr key={n}><td style={{ color: "var(--text-primary)" }}>{n}</td><td>{t}</td><td className="muted">{until}</td><td className="num"><b style={{ color: days < 30 ? "var(--warning)" : "var(--text-primary)" }}>{days}</b></td><td><button className="btn btn-secondary btn-sm"><Bi id="Transisi ke public" en="Transition to public" /></button></td></tr>
        ))}</tbody>
      </table></div></div>

      <div className="card card-pad" style={{ marginTop: "1.5rem" }}>
        <h3 className="card-title" style={{ marginBottom: "0.875rem" }}><Activity size={16} /> <Bi id="Log aktivitas" en="Activity log" /></h3>
        {LOG.map(([t, time]) => (<div key={t} style={{ display: "flex", gap: "0.75rem", fontSize: "var(--text-sm)", padding: "0.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}><span style={{ color: "var(--text-secondary)" }}>{t}</span><span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{time}</span></div>))}
      </div>

      <div className={`nl-scrim${open ? " open" : ""}`} onClick={() => setOpen(false)} />
      <aside className={`nl-drawer${open ? " open" : ""}`}>
        <div className="nl-drawer-head">
          <span className="nl-mood-mini" style={{ width: 40, height: 28 }}><span style={{ background: "#082f49" }} /><span style={{ background: "#0c4a6e" }} /><span style={{ background: "#0ea5e9" }} /></span>
          <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}>Misteri Samudra</div><div className="muted mono" style={{ fontSize: "var(--text-xs)" }}>ocean_mysteries</div></div>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setOpen(false)}><X size={16} /></button>
        </div>
        <div className="nl-drawer-tabs">{DTABS.map((l, i) => <button key={l} className={`nl-dtab${dtab === i ? " active" : ""}`} onClick={() => setDtab(i)}>{l}</button>)}</div>
        <div className="nl-dpanel">
          {dtab === 0 && <>
            <div className="nl-fld"><label className="label">Niche key</label><input className="input input-mono" value="ocean_mysteries" disabled /></div>
            <div className="nl-fld" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}><div><label className="label">Display (ID)</label><input className="input" defaultValue="Misteri Samudra" /></div><div><label className="label">Display (EN)</label><input className="input" defaultValue="Ocean Mysteries" /></div></div>
            <div className="nl-fld"><label className="label">Description</label><textarea className="textarea" rows={2} defaultValue="Misteri laut dalam, makhluk abisal, dan fenomena samudra yang belum terpecahkan." /></div>
            <div className="nl-fld"><label className="label">Keywords</label><div className="nl-chip-pool">{["laut", "misteri", "samudra", "abisal"].map((k) => <span key={k} className="nl-chip">{k}</span>)}<span className="nl-chip" style={{ color: "var(--text-muted)" }}>+ tambah</span></div></div>
            <div className="nl-fld"><label className="label">Moodboard (3 image)</label><div className="nl-swrow"><span style={{ background: "#082f49" }} /><span style={{ background: "#0c4a6e" }} /><span style={{ background: "#0ea5e9" }} /><button className="btn btn-ghost btn-icon btn-sm"><Upload size={14} /></button></div></div>
            <div className="nl-fld" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)" }}>is_active</span><label className="switch"><input type="checkbox" defaultChecked /><span className="track" /><span className="thumb" /></label></div>
          </>}
          {dtab === 1 && <>
            <div className="nl-fld"><label className="label">voice_profile JSON</label><div className="nl-json">{`{\n  "default_voice": "Arya",\n  "stability": 0.5,\n  "style": 0.3,\n  "fallback": ["Galih", "Bima"]\n}`}</div></div>
            <button className="btn btn-secondary btn-sm"><Play size={14} /> <Bi id="Preview TTS" en="Preview TTS" /></button>
          </>}
          {dtab === 2 && <>
            <div className="nl-fld"><label className="label">visual_style JSON</label><div className="nl-json">{`{\n  "style": "cinematic dark",\n  "lighting": "volumetric fog",\n  "palette": ["#082f49", "#0c4a6e", "#0ea5e9"],\n  "aspect": "9:16"\n}`}</div></div>
            <button className="btn btn-secondary btn-sm"><ImageIcon size={14} /> <Bi id="Generate sample image" en="Generate sample image" /></button>
          </>}
          {dtab === 3 && <>
            <div className="nl-fld"><label className="label">mood_priority <span className="muted">(drag to reorder)</span></label>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>{["Misterius", "Tegang", "Epik"].map((m, i) => <div key={m} className="nl-radio-card" style={{ cursor: "grab" }}><MoreVertical size={14} /> {m} <span className="badge badge-default" style={{ marginLeft: "auto" }}>{i + 1}</span></div>)}</div></div>
            <div className="nl-fld"><label className="label">emotion_scoring_criteria</label><textarea className="textarea" rows={2} defaultValue="Skor tinggi untuk curiosity gap + awe. Penalti untuk konten yang terlalu menakutkan." /></div>
            <div className="nl-fld"><label className="label">default_hashtags</label><div className="nl-chip-pool">{["#misteri", "#laut", "#samudra"].map((h) => <span key={h} className="nl-chip">{h}</span>)}</div></div>
          </>}
          {dtab === 4 && <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.875rem" }}><span style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}><Bi id="Tag pool (24 tag)" en="Tag pool (24 tags)" /></span><button className="btn btn-ai btn-sm"><Sparkles size={13} /> <Bi id="Saran tag via AI" en="Suggest tags via AI" /></button></div>
            <div className="nl-chip-pool">{TAGS.map((t, i) => <span key={t} className="nl-chip">{t} <span className="ct">{tagCt(i)}</span></span>)}<span className="nl-chip" style={{ color: "var(--text-muted)" }}>+ tambah</span></div>
            <div className="card card-pad" style={{ marginTop: "1rem", background: "var(--bg)" }}><div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.5rem" }}><Bi id="CTR rata-rata per tag (top 5)" en="Avg CTR per tag (top 5)" /></div>
              {TAGPERF.map(([t, v]) => (<div key={t} style={{ display: "flex", alignItems: "center", gap: "0.625rem", fontSize: "var(--text-xs)", padding: "0.25rem 0" }}><span className="mono" style={{ width: 120, color: "var(--text-secondary)" }}>{t}</span><div style={{ flex: 1, height: 6, background: "var(--surface-2)", borderRadius: 99, overflow: "hidden" }}><span style={{ display: "block", height: "100%", width: `${v * 10}%`, background: "var(--brand)" }} /></div><span className="mono">{v}%</span></div>))}
            </div>
          </>}
          {dtab === 5 && <>
            <div className="nl-fld"><label className="label">access_type</label>
              <div className="nl-radio-card sel">🌍 Public</div>
              <div className="nl-radio-card">📅 <Bi id="Pending rilis" en="Release pending" /></div>
              <div className="nl-radio-card">🔒 Private Exclusive</div>
              <div className="nl-radio-card">⏳ Public-after-90d</div>
            </div>
            <div className="nl-fld" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}><div><label className="label">exclusive_until</label><input className="input" value="—" disabled /></div><div><label className="label">released_at</label><input className="input" value="12 Jan 2026" disabled /></div></div>
          </>}
        </div>
        <div style={{ padding: "1rem 1.25rem", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}><button className="btn btn-ghost" onClick={() => setOpen(false)}><Bi id="Batal" en="Cancel" /></button><button className="btn btn-default"><Bi id="Simpan" en="Save" /></button></div>
      </aside>
    </>
  );
}
