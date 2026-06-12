"use client";

import { ShieldCheck, ChevronDown, CheckCircle, AlertTriangle, Info, RefreshCw, Activity, Zap, Play, Mic, Layers, Anchor } from "lucide-react";
import "./compliance.css";

// D20 Compliance (PoC) — port dari design-source/Compliance.html. Semua chart = SVG hand-drawn
// (gauge/radar/donut/trend), TANPA chart lib. Data mock deterministik. Skor nyata = engine Phase 6+.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

// ---- gauge ----
function Gauge() {
  const score = 87, r = 64, c = 2 * Math.PI * r, off = c * (1 - score / 100);
  return (
    <svg viewBox="0 0 160 160" width={160} height={160}>
      <circle cx={80} cy={80} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={12} />
      <circle cx={80} cy={80} r={r} fill="none" stroke="#10B981" strokeWidth={12} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 80 80)" />
      <text x={80} y={76} textAnchor="middle" fontSize={40} fontWeight={800} fill="var(--text-primary)" fontFamily="Geist">{score}</text>
      <text x={80} y={98} textAnchor="middle" fontSize={12} fill="var(--text-muted)" fontFamily="Geist">/ 100</text>
    </svg>
  );
}

// ---- radar ----
const RADAR_AXES: [string, number][] = [["Diversity suara", 95], ["Sebaran niche", 85], ["Variasi hook", 90], ["Anti-duplikat", 95], ["AI disclosure", 100]];
function Radar() {
  const cx = 100, cy = 100, R = 78, n = RADAR_AXES.length;
  const pt = (i: number, val: number): [number, number] => { const a = -Math.PI / 2 + (i * 2 * Math.PI) / n; return [cx + Math.cos(a) * R * val / 100, cy + Math.sin(a) * R * val / 100]; };
  const poly = (val: number) => RADAR_AXES.map((_, i) => pt(i, val).join(",")).join(" ");
  return (
    <svg viewBox="0 0 220 200" width={220} height={200}>
      {[100, 75, 50, 25].map((g) => <polygon key={g} points={poly(g)} fill="none" stroke="var(--grid-line)" strokeWidth={1} />)}
      {RADAR_AXES.map((_, i) => { const [x, y] = pt(i, 100); return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--grid-line)" />; })}
      <polygon points={poly(100)} fill="none" stroke="var(--border-strong)" strokeDasharray="3 3" />
      <polygon points={RADAR_AXES.map((a, i) => pt(i, a[1]).join(",")).join(" ")} fill="color-mix(in srgb,#10B981 20%,transparent)" stroke="#10B981" strokeWidth={2} />
      {RADAR_AXES.map((a, i) => { const [x, y] = pt(i, a[1]); return <circle key={i} cx={x} cy={y} r={3} fill="#10B981" />; })}
    </svg>
  );
}

// ---- donut ----
function Donut({ data }: { data: [string, string, number][] }) {
  const r = 32, cx = 45, cy = 45, C = 2 * Math.PI * r;
  let off = 0;
  const arcs = data.map(([, col, p], i) => { const len = C * p / 100; const node = <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={col} strokeWidth={11} strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} transform={`rotate(-90 ${cx} ${cy})`} />; off += len; return node; });
  return (
    <div className="donut-wrap">
      <svg viewBox="0 0 90 90" width={90} height={90}>{arcs}</svg>
      <div className="donut-leg">
        {data.map(([n, col, p]) => (<div className="r" key={n}><span className="sw" style={{ background: col }} /><span className="muted">{n}</span><span className="p">{p}%</span></div>))}
      </div>
    </div>
  );
}

// ---- trend ----
function Trend() {
  const d = [72, 74, 73, 76, 75, 71, 68, 74, 78, 80, 79, 82, 81, 84, 83, 85, 86, 84, 87];
  const W = 480, H = 150, pad = 10, min = 60, max = 100;
  const x = (i: number) => pad + i * (W - pad * 2) / (d.length - 1);
  const y = (v: number) => H - 20 - ((v - min) / (max - min)) * (H - 36);
  const line = d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(0)} ${y(v).toFixed(0)}`).join(" ");
  return (
    <svg viewBox="0 0 480 150" style={{ width: "100%", height: "auto" }}>
      {([["#10B981", 80, 100], ["#F59E0B", 60, 80]] as [string, number, number][]).map(([col, a, b], i) => <rect key={i} x={pad} y={y(b)} width={W - pad * 2} height={y(a) - y(b)} fill={col} opacity={0.05} />)}
      <line x1={pad} y1={y(80)} x2={W - pad} y2={y(80)} stroke="var(--success)" strokeDasharray="3 3" opacity={0.5} />
      <path d={line} fill="none" stroke="#10B981" strokeWidth={2} />
      <circle cx={x(d.length - 1)} cy={y(d[d.length - 1])} r={3.5} fill="#10B981" />
      <text x={pad + 2} y={y(80) - 4} fontSize={9} fill="var(--success)" fontFamily="JetBrains Mono">target 80</text>
    </svg>
  );
}

const HOOKS: [string, string, number][] = [["Gap question", "#10B981", 30], ["Surprise stat", "#6366F1", 24], ["Contrarian", "#6366F1", 21], ["Story bait", "#6366F1", 20], ["Time pressure", "#F59E0B", 5]];
const DUPS: [string, number][] = [["kapal-hilang-bermuda", 78], ["palung-mariana-suara", 52], ["kota-atlantis", 41]];
const ACTIONS: [string, string][] = [
  ['Voice rotation didominasi "Arya" (24% video) — disarankan tambah voice female.', 'Voice rotation dominated by "Arya" (24%) — add a female voice.'],
  ['Niche "Sejarah Kelam" over-produced (45% 7 hari) — sesuaikan jadwal.', '"Dark History" over-produced (45% in 7 days) — adjust schedule.'],
];

export default function CompliancePage() {
  return (
    <>
      <div className="cmp-head">
        <div>
          <h1><ShieldCheck size={26} style={{ color: "var(--success)" }} /> Compliance Score</h1>
          <div className="sub"><Bi id="AI Slop Defense · diperbarui 2 jam lalu" en="AI Slop Defense · updated 2 hours ago" /></div>
        </div>
        <div className="ch-sel"><span className="dot-ch">MS</span> Misteri Samudra <ChevronDown size={14} /></div>
      </div>

      {/* hero */}
      <div className="hero-row">
        <div className="gauge-card">
          <Gauge />
          <div className="label"><Bi id="Sehat" en="Healthy" /></div>
          <div className="sub"><Bi id="Channel Anda aman dari risiko YouTube AI policy 2026." en="Your channel is safe from YouTube's 2026 AI policy risk." /></div>
        </div>
        <div className="card radar-card">
          <Radar />
          <div className="radar-legend">
            {RADAR_AXES.map(([n, v]) => (
              <div className="row" key={n}><span className="secondary">{n}</span><div className="bar"><span style={{ width: `${v}%`, background: v >= 90 ? "var(--success)" : v >= 80 ? "var(--warning)" : "var(--error)" }} /></div><span className="v">{v}%</span></div>
            ))}
          </div>
        </div>
      </div>

      {/* per-dimension */}
      <div className="dim-grid">
        <div className="card card-pad dim-card">
          <div className="head"><span className="ic" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><Mic size={17} /></span><h3><Bi id="Diversity Suara" en="Voice Diversity" /></h3><span className="score" style={{ color: "var(--success)" }}>95%</span></div>
          <Donut data={[["Arya", "#6366F1", 24], ["Sari", "#10B981", 19], ["Bima", "#F59E0B", 17], ["Dewi", "#EC4899", 16], ["Lainnya", "#71717A", 24]]} />
          <div className="dim-note ok"><span style={{ flex: "none" }}><CheckCircle size={14} /></span><span><Bi id="7 voice dirotasi (target ≥5). Optional: tambah 2 voice female untuk balance gender." en="7 voices rotated (target ≥5). Optional: add 2 female voices for gender balance." /></span></div>
        </div>
        <div className="card card-pad dim-card">
          <div className="head"><span className="ic" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><Layers size={17} /></span><h3><Bi id="Distribusi Niche" en="Niche Distribution" /></h3><span className="score" style={{ color: "var(--warning)" }}>85%</span></div>
          <Donut data={[["Sejarah Kelam", "#EC4899", 45], ["Misteri Samudra", "#6366F1", 33], ["Fakta Menarik", "#10B981", 22]]} />
          <div className="dim-note warn"><span style={{ flex: "none" }}><AlertTriangle size={14} /></span><span><Bi id={'Niche "Sejarah Kelam" over-produced (45% 7 hari terakhir) — diversity guard akan merotasi.'} en={'"Dark History" over-produced (45% last 7 days) — diversity guard will rotate.'} /></span></div>
        </div>
        <div className="card card-pad dim-card">
          <div className="head"><span className="ic" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><Anchor size={17} /></span><h3><Bi id="Variasi Hook" en="Hook Variation" /></h3><span className="score" style={{ color: "var(--success)" }}>90%</span></div>
          <div>{HOOKS.map(([n, col, v]) => (<div className="bar-row" key={n}><span className="lab">{n}</span><div className="track"><span style={{ width: `${v * 2.5}%`, background: col }} /></div><span className="mono">{v}%</span></div>))}</div>
          <div className="dim-note ok"><span style={{ flex: "none" }}><Info size={14} /></span><span><Bi id="Tambah variety di pattern 'time pressure' (hanya 5%)." en="Add variety to the 'time pressure' pattern (only 5%)." /></span></div>
        </div>
        <div className="card card-pad dim-card">
          <div className="head"><span className="ic" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><RefreshCw size={17} /></span><h3><Bi id="Deteksi Duplikat" en="Duplicate Detection" /></h3><span className="score" style={{ color: "var(--success)" }}>95%</span></div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.5rem" }}><Bi id="Slug duplikat terakhir: 27 hari lalu" en="Last duplicate slug: 27 days ago" /></div>
          <div>{DUPS.map(([a, sim]) => (<div className="dup-item" key={a}><span style={{ color: "var(--text-primary)" }} className="mono">{a}</span><span className="dup-sim" style={{ color: sim >= 70 ? "var(--warning)" : "var(--text-muted)" }}>{sim}%</span></div>))}</div>
        </div>
      </div>

      {/* AI disclosure + trend */}
      <div className="dim-grid" style={{ marginTop: "1rem" }}>
        <div className="card card-pad dim-card">
          <div className="head"><span className="ic" style={{ background: "var(--success-soft)", color: "var(--success)" }}><ShieldCheck size={17} /></span><h3>AI Disclosure</h3><span className="score" style={{ color: "var(--success)" }}>100%</span></div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0.5rem 0" }}>
            <span style={{ fontSize: "var(--text-sm)" }}><Bi id="Tag AI disclosure di semua video" en="AI disclosure tag on all videos" /></span>
            <label className="switch"><input type="checkbox" defaultChecked /><span className="track" /><span className="thumb" /></label>
          </div>
          <div className="dim-note ok"><span style={{ flex: "none" }}><CheckCircle size={14} /></span><span><Bi id="284 video ditandai AI-generated sesuai YouTube self-identification. Audit log bersih." en="284 videos marked AI-generated per YouTube self-identification. Clean audit log." /></span></div>
        </div>
        <div className="card">
          <div className="card-head"><h3 className="card-title"><Activity size={16} /> <Bi id="Tren Compliance (90 hari)" en="Compliance Trend (90 days)" /></h3></div>
          <div className="card-body"><Trend /></div>
        </div>
      </div>

      {/* action items */}
      <div className="card card-pad" style={{ marginTop: "1rem" }}>
        <h3 className="card-title" style={{ marginBottom: "1rem" }}><Zap size={16} /> <Bi id="Item tindakan" en="Action items" /></h3>
        <div>
          {ACTIONS.map(([idT, enT], i) => (
            <div className="action-item" key={i}>
              <span className="ic"><AlertTriangle size={15} /></span>
              <div className="body">
                <div style={{ fontSize: "var(--text-sm)" }}><Bi id={idT} en={enT} /></div>
                <div className="acts"><button className="btn btn-default btn-sm"><Bi id="Terapkan perbaikan" en="Apply fix" /></button><button className="btn btn-ghost btn-sm"><Bi id="Tunda" en="Snooze" /></button><button className="btn btn-ghost btn-sm"><Bi id="Abaikan" en="Dismiss" /></button></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* educational */}
      <div className="card card-pad" style={{ marginTop: "1rem" }}>
        <div className="edu">
          <div className="edu-video"><div className="play"><Play size={18} /></div></div>
          <div>
            <h3 style={{ fontSize: "var(--text-lg)", fontWeight: 600, margin: "0 0 0.5rem" }}><Bi id="📚 Kenapa ini penting?" en="📚 Why this matters" /></h3>
            <p className="muted" style={{ fontSize: "var(--text-sm)", lineHeight: 1.6, margin: "0 0 0.75rem", maxWidth: "60ch" }}><Bi id="YouTube memperketat AI content policy di 2026. Channel dengan output terlalu seragam berisiko demonetisasi. Compliance Score menjaga channelmu tetap aman secara otomatis." en="YouTube tightened its AI content policy in 2026. Channels with overly uniform output risk demonetization. Compliance Score keeps your channel safe automatically." /></p>
            <a href="#" className="link" style={{ color: "var(--brand)", fontSize: "var(--text-sm)", textDecoration: "none" }}><Bi id="Pelajari YouTube AI policy 2026" en="Learn about YouTube AI policy 2026" /> →</a>
          </div>
        </div>
      </div>
    </>
  );
}
