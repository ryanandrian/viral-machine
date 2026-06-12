"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ExternalLink, Settings, Zap, Activity, BarChart3, Play, Sparkles, Calendar, ChevronDown,
  AlertTriangle, ArrowRight, Check, Loader2, X, Mic, Target, type LucideIcon,
} from "lucide-react";
import "./channel-detail.css";

// D3 Channel Detail — port dari design-source/Channel Detail.html (Hybrid). /channels/[id].
// 5 tab (Overview/Runs/Analytics/Schedule/Settings). Chart = SVG hand-drawn (perf dual-area + donut),
// bar CSS (hooks). Mock deterministik (SSR-safe); nol wiring Supabase. Class prefix cd- (anti bentrok global).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const HEADER: Record<string, { name: string; initials: string; color: string; handle: string }> = {
  "1": { name: "Misteri Samudra", initials: "MS", color: "#1d4ed8", handle: "@misterisamudra" },
  "2": { name: "Fakta Yang Bikin Mikir", initials: "FB", color: "#047857", handle: "@faktabikinmikir" },
  "3": { name: "Jejak Kelam Sejarah", initials: "JS", color: "#9f1239", handle: "@jejakkelam" },
};

function PerfChart() {
  const views = [3.1, 3.4, 3.2, 4.0, 3.8, 4.6, 4.2, 5.1, 4.8, 5.6, 5.2, 6.1, 5.8, 6.8, 6.4, 7.2, 6.9, 7.8, 7.4, 8.6];
  const watch = [1.8, 2.0, 1.9, 2.4, 2.2, 2.8, 2.5, 3.0, 2.8, 3.3, 3.1, 3.6, 3.4, 4.0, 3.8, 4.3, 4.0, 4.6, 4.3, 5.0];
  const W = 640, H = 220, pad = 10, max = Math.max(...views, ...watch);
  const x = (i: number) => pad + i * (W - pad * 2) / (views.length - 1);
  const y = (v: number) => H - 24 - (v / max) * (H - 44);
  const path = (d: number[]) => d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  return (
    <svg viewBox="0 0 640 220" style={{ width: "100%", height: "auto" }}>
      <defs><linearGradient id="cd-pv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6366F1" stopOpacity={0.3} /><stop offset="1" stopColor="#6366F1" stopOpacity={0} /></linearGradient></defs>
      {[0, 2, 4, 6, 8].map((v) => (
        <g key={v}><line x1={pad} y1={y(v)} x2={W - pad} y2={y(v)} stroke="var(--grid-line)" strokeWidth={1} /><text x={pad} y={y(v) - 3} fontSize={9} fill="var(--text-muted)" fontFamily="JetBrains Mono">{v}K</text></g>
      ))}
      <path d={`${path(views)} L${x(views.length - 1)} ${H - 24} L${pad} ${H - 24} Z`} fill="url(#cd-pv)" />
      <path d={path(views)} fill="none" stroke="#6366F1" strokeWidth={2.2} />
      <path d={path(watch)} fill="none" stroke="#8B5CF6" strokeWidth={2} />
      <circle cx={x(views.length - 1)} cy={y(views[views.length - 1])} r={3.5} fill="#6366F1" />
    </svg>
  );
}

function Donut() {
  const data: [string, string, number][] = [["Misteri Samudra", "#6366F1", 52], ["Fakta Menarik", "#10B981", 31], ["Misteri Alam Semesta", "#F59E0B", 17]];
  const r = 44, cx = 60, cy = 60, C = 2 * Math.PI * r; let off = 0;
  const arcs = data.map(([n, c, p]) => { const len = C * p / 100; const seg = <circle key={n} cx={cx} cy={cy} r={r} fill="none" stroke={c} strokeWidth={14} strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} transform={`rotate(-90 ${cx} ${cy})`} />; off += len; return seg; });
  return (
    <div className="cd-donut-wrap">
      <svg viewBox="0 0 120 120" width={120} height={120}>{arcs}<text x={60} y={58} textAnchor="middle" fontSize={18} fontWeight={700} fill="var(--text-primary)" fontFamily="Geist">284</text><text x={60} y={74} textAnchor="middle" fontSize={9} fill="var(--text-muted)" fontFamily="Geist">video</text></svg>
      <div className="cd-donut-leg">{data.map(([n, c, p]) => (<div className="row" key={n}><span className="sw" style={{ background: c }} /><span className="muted">{n}</span><span className="pct">{p}%</span></div>))}</div>
    </div>
  );
}

const TABS: [string, string, string][] = [["overview", "Overview", "Overview"], ["runs", "Runs", "Runs"], ["analytics", "Analytics", "Analytics"], ["schedule", "Jadwal", "Schedule"], ["settings", "Pengaturan", "Settings"]];
const TV: [string, string, string][] = [["Kapal Hilang di Segitiga Bermuda", "58.2K", "9.1%"], ["Suara Aneh dari Palung Mariana", "41.7K", "7.4%"], ["Kota Atlantis yang Hilang", "33.5K", "8.2%"], ["Makhluk Raksasa Laut Dalam", "28.9K", "6.6%"], ["95% Lautan Belum Dipetakan", "22.1K", "5.9%"]];
const HOOKS: [string, string, number][] = [["Gap question", "#10B981", 92], ["Time pressure", "#6366F1", 64], ["Bold claim", "#6366F1", 58], ["Number list", "#F59E0B", 41], ["Direct address", "#71717A", 28]];
type RunSt = "completed" | "running" | "failed";
const CR: [RunSt, string, string, string][] = [["completed", "Kapal Hilang di Segitiga Bermuda", "1m 24s", "58.2K"], ["completed", "Suara Aneh dari Palung Mariana", "1m 31s", "41.7K"], ["running", "Kota Bawah Laut yang Hilang", "berjalan…", "—"], ["completed", "Makhluk Raksasa Laut Dalam", "1m 18s", "28.9K"], ["failed", "Pulau Hantu di Peta", "timeout", "—"]];
const SM: Record<RunSt, { Icon: LucideIcon; c: string; bg: string }> = { completed: { Icon: Check, c: "var(--success)", bg: "var(--success-soft)" }, running: { Icon: Loader2, c: "var(--info)", bg: "var(--info-soft)" }, failed: { Icon: X, c: "var(--error)", bg: "var(--error-soft)" } };
const CS: [string, string, string, boolean][] = [["10:00", "Misteri Samudra", "short", true], ["14:00", "Fakta Menarik", "short", true], ["19:00", "Auto rotation", "short", false]];

export default function ChannelDetailPage() {
  const params = useParams<{ id: string }>();
  const h = HEADER[(params?.id as string)] ?? HEADER["1"];
  const [tab, setTab] = useState("overview");

  return (
    <>
      <div className="cd-header">
        <span className="cd-logo-lg" style={{ background: h.color }}>{h.initials}</span>
        <div className="cd-h-meta">
          <h1>{h.name} <span className="badge badge-success" style={{ fontSize: "var(--text-xs)" }}><span className="dot" />Active</span></h1>
          <a href="#" className="cd-yt-link"><span className="yt" /> youtube.com/{h.handle} <ExternalLink size={13} /></a>
          <div className="cd-kpi-strip">
            <div className="item"><div className="v">284</div><div className="l"><Bi id="Total video" en="Total videos" /></div></div>
            <div className="item"><div className="v">12.4K</div><div className="l">Subscribers</div></div>
            <div className="item"><div className="v">186K</div><div className="l"><Bi id="Views bulan ini" en="Views this month" /></div></div>
            <div className="item"><div className="v">6.8%</div><div className="l"><Bi id="Avg engagement" en="Avg engagement" /></div></div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-secondary" onClick={() => setTab("settings")}><Settings size={15} /> <Bi id="Pengaturan" en="Settings" /></button>
          <button className="btn btn-ai"><Zap size={15} /> <Bi id="Jalankan" en="Run" /></button>
        </div>
      </div>

      <div className="cd-tabs">
        {TABS.map(([k, id, en]) => <button key={k} className={`cd-tab${tab === k ? " active" : ""}`} onClick={() => setTab(k)}><Bi id={id} en={en} /></button>)}
      </div>

      {tab === "overview" && <>
        <div className="cd-grid2">
          <div className="card">
            <div className="card-head">
              <h3 className="card-title"><Activity size={16} /> <Bi id="Performa" en="Performance" /></h3>
              <div className="cd-legend"><span><i style={{ background: "#6366F1" }} />Views</span><span><i style={{ background: "#8B5CF6" }} />Watch time</span></div>
            </div>
            <div className="card-body"><PerfChart /></div>
          </div>
          <div className="card">
            <div className="card-head"><h3 className="card-title"><BarChart3 size={16} /> <Bi id="Distribusi niche" en="Niche distribution" /></h3></div>
            <div className="card-body">
              <Donut />
              <div className="cd-rec"><span style={{ color: "var(--accent)", flex: "none" }}><Sparkles size={16} /></span><div><b style={{ color: "var(--text-primary)" }}><Bi id="Rekomendasi mesin: " en="Engine suggests: " /></b><Bi id={'naikkan porsi "Misteri Samudra" +10% — perform 1.5× lebih baik.'} en={'raise "Ocean Mysteries" by +10% — performing 1.5× better.'} /></div></div>
            </div>
          </div>
        </div>
        <div className="cd-grid2b" style={{ marginTop: "1rem" }}>
          <div className="card">
            <div className="card-head"><h3 className="card-title"><Play size={16} /> <Bi id="Video teratas (30 hari)" en="Top videos (30d)" /></h3></div>
            <div style={{ overflowX: "auto" }}><table className="tbl">
              <thead><tr><th></th><th>Topic</th><th className="num">Views</th><th className="num">CTR</th></tr></thead>
              <tbody>{TV.map(([t, v, c]) => (<tr key={t}><td><span className="cd-vthumb" /></td><td style={{ color: "var(--text-primary)", fontWeight: 450 }}>{t}</td><td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{v}</b></td><td className="num muted">{c}</td></tr>))}</tbody>
            </table></div>
          </div>
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "1rem" }}><Target size={16} /> <Bi id="Performa hook style" en="Hook style performance" /></h3>
            {HOOKS.map(([n, c, v]) => (<div className="cd-bar-row" key={n}><span className="lab">{n}</span><div className="cd-bar-track"><span style={{ width: `${v}%`, background: c }} /></div><span className="val">{v}</span></div>))}
          </div>
        </div>
      </>}

      {tab === "runs" && (
        <div className="card"><div className="card-body" style={{ padding: "0.5rem 0.75rem" }}>
          {CR.map(([st, t, d, v]) => { const m = SM[st]; return (
            <Link key={t} href="/runs/97" className="cd-run-item">
              <span className="rs" style={{ background: m.bg, color: m.c }}><m.Icon size={12} /></span>
              <div><div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>{t}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{d}</div></div>
              <span className={v !== "—" ? "" : "muted"} style={{ fontSize: "var(--text-xs)" }}>{v !== "—" ? `${v} views` : ""}</span>
            </Link>
          ); })}
        </div>
          <div className="card-foot"><Link href="/runs" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat semua runs channel ini →" en="View all runs for this channel →" /></Link></div>
        </div>
      )}

      {tab === "analytics" && (
        <div className="card card-pad" style={{ textAlign: "center", padding: "3rem" }}>
          <div style={{ color: "var(--text-muted)", marginBottom: "0.75rem", display: "flex", justifyContent: "center" }}><BarChart3 size={32} /></div>
          <p className="muted"><Bi id="Tab analytics per-channel — chart mendalam (retention, CTR distribution, publish-time heatmap)." en="Per-channel analytics — deep charts (retention, CTR distribution, publish-time heatmap)." /></p>
          <Link href="/analytics" className="btn btn-secondary btn-sm" style={{ marginTop: "0.75rem" }}><Bi id="Buka Analytics lengkap" en="Open full Analytics" /> <ArrowRight size={14} /></Link>
        </div>
      )}

      {tab === "schedule" && (
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Calendar size={16} /> <Bi id={`Slot harian — ${h.name}`} en={`Daily slots — ${h.name}`} /></h3>
          {CS.map(([tm, nc, ct, on]) => (
            <div className="cd-sched-row" key={tm}><div style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{tm}<span className="muted" style={{ fontSize: "0.625rem" }}> WIB</span></div>
              <div><div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>{nc}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{ct}</div></div>
              <label className="switch"><input type="checkbox" defaultChecked={on} /><span className="track" /><span className="thumb" /></label></div>
          ))}
        </div>
      )}

      {tab === "settings" && (
        <div className="card card-pad" style={{ maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Bi id="Pengaturan channel" en="Channel settings" /></h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div><label className="label"><Bi id="Nama channel" en="Channel name" /></label><input className="input" defaultValue={h.name} /></div>
            <div><label className="label"><Bi id="Bahasa konten" en="Content language" /></label>
              <div className="selbox" style={{ width: "fit-content", display: "inline-flex", alignItems: "center", gap: "0.5rem", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", padding: "0 0.625rem", height: "2.125rem", fontSize: "var(--text-sm)", cursor: "pointer" }}>🇮🇩 Bahasa Indonesia <ChevronDown size={14} /></div>
              <div style={{ marginTop: "0.625rem", padding: "0.625rem 0.875rem", background: "var(--warning-soft)", border: "1px solid color-mix(in srgb,var(--warning) 25%,transparent)", display: "flex", gap: "0.5rem", borderRadius: "var(--r-md)" }}><AlertTriangle size={14} style={{ color: "var(--warning)", flex: "none" }} /><span style={{ fontSize: "var(--text-xs)" }}><Bi id="Mengubah bahasa hanya berlaku untuk video baru — video lama tidak diproduksi ulang. Pilihan voice akan ikut berubah." en="Changing the language applies to new videos only — existing videos aren't re-produced. Available voices will change too." /></span></div>
            </div>
            <div><label className="label">Niche aktif</label><div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}><span className="badge badge-brand">Misteri Samudra ×</span><span className="badge badge-brand">Fakta Menarik ×</span><button className="btn btn-secondary btn-sm">+ Niche</button></div></div>
            <div><label className="label">Voice default</label><div className="selbox" style={{ width: "fit-content", display: "inline-flex", alignItems: "center", gap: "0.5rem", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", padding: "0 0.625rem", height: "2.125rem", fontSize: "var(--text-sm)", cursor: "pointer" }}><Mic size={14} /> Arya · Multilingual v2 <ChevronDown size={14} /></div></div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}><button className="btn btn-ghost"><Bi id="Batal" en="Cancel" /></button><button className="btn btn-default"><Bi id="Simpan" en="Save" /></button></div>
          </div>
        </div>
      )}
    </>
  );
}
