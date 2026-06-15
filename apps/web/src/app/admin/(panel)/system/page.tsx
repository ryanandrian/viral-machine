"use client";

import { Activity, AlertTriangle, XCircle, Command } from "lucide-react";
import "./system.css";

// E3 Admin System Health — port dari design-source/Admin System.html (Hybrid). /admin/system.
// Chart = SVG line hand-drawn (data deterministik). Mock; nol wiring Supabase. Prefix sys-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const WORKERS: [string, "up" | "degraded", string, string][] = [
  ["worker-01", "up", "Run #312", "12s ago"], ["worker-02", "up", "Run #313", "3s ago"],
  ["worker-03", "up", "idle", "8s ago"], ["worker-04", "degraded", "Run #310 retry", "45s ago"],
];

function LineChart({ data, color, gid }: { data: number[]; color: string; gid: string }) {
  const W = 480, H = 160, pad = 10, max = Math.max(...data);
  const x = (i: number) => pad + i * (W - pad * 2) / (data.length - 1);
  const y = (v: number) => H - 18 - (v / max) * (H - 34);
  const line = data.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(0)} ${y(v).toFixed(0)}`).join(" ");
  return (
    <svg viewBox="0 0 480 160" style={{ width: "100%", height: "auto" }}>
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity={0.25} /><stop offset="1" stopColor={color} stopOpacity={0} /></linearGradient></defs>
      {[0, max / 2, max].map((v, i) => (<g key={i}><line x1={pad} y1={y(v)} x2={W - pad} y2={y(v)} stroke="var(--grid-line)" /><text x={pad} y={y(v) - 3} fontSize={9} fill="var(--text-muted)" fontFamily="JetBrains Mono">{Math.round(v)}</text></g>))}
      <path d={`${line} L${x(data.length - 1)} ${H - 18} L${pad} ${H - 18} Z`} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={color} strokeWidth={2} />
    </svg>
  );
}

const QUEUE = [12, 8, 15, 22, 18, 30, 42, 38, 28, 20, 14, 18, 24, 16, 10, 8, 12, 20, 32, 28, 18, 12, 8, 14];
const ERRORS = [0, 1, 0, 0, 2, 1, 0, 3, 1, 0, 0, 1, 0, 0, 2, 0, 1, 0, 0, 1, 0, 0, 0, 1];
const FAILS: [string, string, number][] = [["TTS timeout", "#ef4444", 42], ["Rate limit (429)", "#f59e0b", 28], ["Render error", "#6366F1", 18], ["Upload fail", "#71717a", 12]];
const DB: [string, string, string?][] = [["Connections", "42 / 100"], ["DB size", "3.2 GB"], ["Read latency", "12 ms", "ok"], ["Write latency", "28 ms", "ok"], ["Cache hit rate", "98.4%", "ok"]];

export default function AdminSystemPage() {
  return (
    <>
      <div className="sys-head">
        <div><h1>System Health</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Status worker, queue, dan database real-time" en="Real-time worker, queue, and database status" /></div></div>
        <span className="badge badge-success" style={{ height: "fit-content" }}><span className="dot" /><Bi id="Semua operasional" en="All operational" /></span>
      </div>

      <div className="sys-worker-grid">
        {WORKERS.map(([n, st, job, hb]) => { const c = st === "up" ? "var(--success)" : "var(--warning)"; return (
          <div className="sys-worker" key={n}><div className="top"><span className="wdot" style={{ background: c }} /><span className="nm">{n}</span><span className={`badge ${st === "up" ? "badge-success" : "badge-warning"}`} style={{ marginLeft: "auto", fontSize: "0.5625rem" }}>{st}</span></div>
            <div className="meta"><Bi id="Job saat ini" en="Current job" />: <b style={{ color: "var(--text-primary)" }}>{job}</b><br />heartbeat: {hb}</div></div>
        ); })}
      </div>

      <div className="sys-grid2">
        <div className="card"><div className="card-head"><h3 className="card-title"><Activity size={16} /> <Bi id="Kedalaman queue (24 jam)" en="Queue depth (24h)" /></h3></div><div className="card-body"><LineChart data={QUEUE} color="#6366F1" gid="sys-q" /></div></div>
        <div className="card"><div className="card-head"><h3 className="card-title"><AlertTriangle size={16} /> <Bi id="Error rate (24 jam)" en="Error rate (24h)" /></h3></div><div className="card-body"><LineChart data={ERRORS} color="#EF4444" gid="sys-e" /></div></div>
      </div>

      <div className="sys-grid2" style={{ marginTop: "1rem" }}>
        <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: "1rem" }}><XCircle size={16} /> <Bi id="Kegagalan pipeline per tipe" en="Pipeline failures by type" /></h3>
          {FAILS.map(([n, c, v]) => (<div className="sys-bar-row" key={n}><span className="lab">{n}</span><div className="track"><span style={{ width: `${v}%`, background: c }} /></div><span className="val">{v}%</span></div>))}
        </div>
        <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: "1rem" }}><Command size={16} /> <Bi id="Database (Supabase)" en="Database (Supabase)" /></h3>
          {DB.map(([k, v, ok]) => (<div className="sys-db-stat" key={k}><span className="muted">{k}</span><span style={ok ? { color: "var(--success)" } : undefined}>{v}</span></div>))}
        </div>
      </div>
    </>
  );
}
