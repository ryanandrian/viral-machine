"use client";

import { useState } from "react";
import { Download, FileText, Calendar, ChevronDown, Tv, Filter, Activity, BarChart3, Play, Target, Zap, Eye, TrendingUp, Users, DollarSign, ArrowUp, ArrowDown, Clock, Sparkles, Check } from "lucide-react";
import "./analytics.css";

// D6 Analytics — port dari design-source/Analytics.html (Hybrid). Sidebar "Analitik".
// Chart = SVG hand-drawn (views multi-line + CTR histogram) + bar CSS + heatmap deterministik (ganti Math.random).
// Mock deterministik (SSR-safe); nol wiring Supabase. Class prefix an- (anti bentrok CSS antar-route SPA).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const KPI: { Icon: typeof Play; lId: string; lEn: string; v: string; d: string; up: boolean }[] = [
  { Icon: Play, lId: "Video Published", lEn: "Videos Published", v: "128", d: "+12%", up: true },
  { Icon: Eye, lId: "Total Views", lEn: "Total Views", v: "342K", d: "+24%", up: true },
  { Icon: TrendingUp, lId: "Avg CTR", lEn: "Avg CTR", v: "7.1%", d: "+0.6%", up: true },
  { Icon: Activity, lId: "Avg Retensi", lEn: "Avg Retention", v: "58%", d: "-2%", up: false },
  { Icon: Users, lId: "Subs Gained", lEn: "Subs Gained", v: "+1.9K", d: "+18%", up: true },
  { Icon: DollarSign, lId: "Total Biaya AI", lEn: "Total AI Cost", v: "$43", d: "Rp 688K", up: true },
];

function ViewsChart() {
  const A = [12, 14, 13, 18, 16, 22, 20, 26, 24, 30, 28, 34], B = [20, 22, 21, 26, 28, 30, 34, 32, 40, 44, 42, 52], C = [6, 7, 6, 9, 8, 11, 10, 9, 12, 14, 13, 16];
  const W = 640, H = 230, pad = 12, max = Math.max(...A, ...B, ...C);
  const x = (i: number) => pad + i * (W - pad * 2) / (A.length - 1);
  const y = (v: number) => H - 22 - (v / max) * (H - 40);
  const line = (d: number[]) => d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(0)} ${y(v).toFixed(0)}`).join(" ");
  return (
    <svg id="views-chart" viewBox="0 0 640 230" style={{ width: "100%", height: "auto" }}>
      <defs><linearGradient id="an-ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6366F1" stopOpacity={0.25} /><stop offset="1" stopColor="#6366F1" stopOpacity={0} /></linearGradient></defs>
      {[0, 10, 20, 30, 40, 50].map((v) => (<g key={v}><line x1={pad} y1={y(v)} x2={W - pad} y2={y(v)} stroke="var(--grid-line)" /><text x={pad} y={y(v) - 3} fontSize={9} fill="var(--text-muted)" fontFamily="JetBrains Mono">{v}K</text></g>))}
      <path d={line(B)} fill="none" stroke="#10B981" strokeWidth={2} />
      <path d={line(C)} fill="none" stroke="#EC4899" strokeWidth={2} />
      <path d={`${line(A)} L${x(A.length - 1)} ${H - 22} L${pad} ${H - 22} Z`} fill="url(#an-ag)" />
      <path d={line(A)} fill="none" stroke="#6366F1" strokeWidth={2} />
    </svg>
  );
}

function CtrHist() {
  const bins: [string, number][] = [["2-4%", 8], ["4-6%", 22], ["6-8%", 38], ["8-10%", 24], ["10%+", 9]];
  const W = 300, H = 230, pad = 24, max = Math.max(...bins.map((b) => b[1])), bw = (W - pad * 2) / bins.length;
  return (
    <svg viewBox="0 0 300 230" style={{ width: "100%", height: "auto" }}>
      {bins.map(([l, v], i) => { const h = (v / max) * (H - 50), bx = pad + i * bw; return (
        <g key={l}>
          <rect x={bx + 6} y={H - 30 - h} width={bw - 12} height={h} rx={4} fill={i === 2 ? "#6366F1" : "var(--surface-3)"} />
          <text x={bx + bw / 2} y={H - 14} fontSize={9} fill="var(--text-muted)" textAnchor="middle" fontFamily="JetBrains Mono">{l}</text>
          <text x={bx + bw / 2} y={H - 36 - h} fontSize={10} fill="var(--text-secondary)" textAnchor="middle">{v}</text>
        </g>
      ); })}
    </svg>
  );
}

const NICHE: [string, string, number][] = [["Misteri Samudra", "#6366F1", 88], ["Fakta Menarik", "#10B981", 76], ["Sejarah Kelam", "#EC4899", 54], ["Misteri Alam Semesta", "#F59E0B", 41]];
const HOOK: [string, string, number][] = [["Gap question", "#10B981", 92], ["Surprise stat", "#6366F1", 71], ["Contrarian", "#6366F1", 63], ["Story bait", "#6366F1", 55], ["Time pressure", "#F59E0B", 34]];
const TV: [string, string, string, string, string][] = [
  ["Kapal Hilang di Segitiga Bermuda", "Misteri Samudra", "58.2K", "9.1%", "64%"],
  ["Kenapa Otak Lupa Mimpi?", "Fakta Menarik", "51.4K", "8.7%", "61%"],
  ["Suara Aneh Palung Mariana", "Misteri Samudra", "41.7K", "7.4%", "59%"],
  ["Penjara Bawah Tanah Romawi", "Sejarah Kelam", "33.5K", "6.9%", "55%"],
  ["Mengapa Kucing Takut Timun", "Fakta Menarik", "29.1K", "8.2%", "57%"],
];
const heatColor = (v: number) => `color-mix(in srgb, #6366F1 ${Math.round(v * 100)}%, var(--surface-2))`;
const DAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];
const SLOTS = ["08", "11", "14", "17", "20"];
// deterministik (ganti Math.random): pola stabil + slot 14:00 (idx2) & 20:00 (idx4) lebih panas
const heatVal = (di: number, si: number): number => {
  if (si === 2) return Math.min(1, 0.7 + ((di * 11) % 30) / 100);
  if (si === 4) return Math.min(1, 0.6 + ((di * 17) % 35) / 100);
  return 0.32 + ((di * 7 + si * 13) % 45) / 100;
};
const MOODS: [string, number][] = [["Tegang", 0.9], ["Misterius", 0.82], ["Epik", 0.7], ["Tenang", 0.45], ["Ceria", 0.38], ["Sedih", 0.3]];

type Ins = { tId: string; tEn: string; meta: string; applied: boolean };
const INS: Ins[] = [
  { tId: 'Niche <b>"Misteri Samudra"</b> perform <b>1.5× lebih baik</b> dari "Sejarah Kelam" — mesin menambah bobotnya.', tEn: 'Niche <b>"Ocean Mysteries"</b> performs <b>1.5× better</b> than "Dark History" — engine raised its weight.', meta: "23 video · p=0.96", applied: true },
  { tId: 'Hook <b>"time pressure"</b> under-perform — mesin men-deprioritize ke 5%.', tEn: 'Hook <b>"time pressure"</b> under-performs — engine deprioritized it to 5%.', meta: "18 video · p=0.91", applied: false },
  { tId: 'Slot publish <b>14:00 WIB</b> punya engagement 30% lebih tinggi — disarankan tambah slot.', tEn: 'The <b>14:00 WIB</b> slot has 30% higher engagement — adding a slot suggested.', meta: "42 video · p=0.94", applied: false },
];

export default function AnalyticsPage() {
  const [decision, setDecision] = useState<Record<number, "accepted" | "rejected">>({});

  return (
    <>
      <div className="an-head">
        <div>
          <h1>Analytics</h1>
          <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Performa lintas channel · 1–10 Juni 2026" en="Cross-channel performance · Jun 1–10, 2026" /></div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-secondary"><Download size={15} /> CSV</button>
          <button className="btn btn-secondary"><FileText size={15} /> <Bi id="Laporan PDF" en="PDF Report" /></button>
        </div>
      </div>

      <div className="an-filters">
        <div className="an-selbox"><Calendar size={14} /> 10 hari terakhir <ChevronDown size={14} /></div>
        <div className="an-selbox"><Tv size={14} /> <Bi id="3 channel" en="3 channels" /> <ChevronDown size={14} /></div>
        <div className="an-selbox"><Filter size={14} /> <Bi id="Semua niche" en="All niches" /> <ChevronDown size={14} /></div>
      </div>

      <div className="an-kpi-strip">
        {KPI.map((k) => (
          <div className="an-kpic" key={k.lId}><div className="l"><k.Icon size={13} /> <Bi id={k.lId} en={k.lEn} /></div><div className="v">{k.v}</div><div className={`d ${k.up ? "up" : "down"}`}>{k.up ? <ArrowUp size={11} /> : <ArrowDown size={11} />} {k.d}</div></div>
        ))}
      </div>

      <div className="an-grid">
        <div className="card">
          <div className="card-head"><h3 className="card-title"><Activity size={16} /> <Bi id="Views dari waktu ke waktu" en="Views over time" /></h3>
            <div className="an-legend"><span><i style={{ background: "#6366F1" }} />Misteri Samudra</span><span><i style={{ background: "#10B981" }} />Fakta</span><span><i style={{ background: "#EC4899" }} />Sejarah</span></div>
          </div>
          <div className="card-body"><ViewsChart /></div>
        </div>
        <div className="card">
          <div className="card-head"><h3 className="card-title"><BarChart3 size={16} /> <Bi id="Distribusi CTR" en="CTR distribution" /></h3></div>
          <div className="card-body"><CtrHist /></div>
        </div>
      </div>

      <div className="an-grid-3">
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Target size={16} /> <Bi id="Niche teratas" en="Top niches" /></h3>
          {NICHE.map(([n, c, v]) => (<div className="an-bar-row" key={n}><span className="lab">{n}</span><div className="an-bar-track"><span style={{ width: `${v}%`, background: c }} /></div><span className="val">{v}</span></div>))}
        </div>
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Zap size={16} /> <Bi id="Performa hook style" en="Hook style performance" /></h3>
          {HOOK.map(([n, c, v]) => (<div className="an-bar-row" key={n}><span className="lab">{n}</span><div className="an-bar-track"><span style={{ width: `${v}%`, background: c }} /></div><span className="val">{v}</span></div>))}
        </div>
      </div>

      <div className="an-grid-3">
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.25rem" }}><Clock size={16} /> <Bi id="Waktu publish × engagement" en="Publish time × engagement" /></h3>
          <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "1rem" }}><Bi id="Engagement rata-rata per slot waktu (WIB)" en="Avg engagement per time slot (WIB)" /></div>
          {DAYS.map((d, di) => (
            <div className="an-heat-row" key={d}><span className="ylab">{d}</span><div className="an-heat" style={{ gridTemplateColumns: `repeat(${SLOTS.length},1fr)` }}>{SLOTS.map((s, si) => (<div className="cell" key={s} style={{ background: heatColor(heatVal(di, si)) }} />))}</div></div>
          ))}
          <div className="an-heat-row"><span className="ylab" /><div className="an-heat-labels-x" style={{ gridTemplateColumns: `repeat(${SLOTS.length},1fr)` }}>{SLOTS.map((s) => (<span key={s}>{s}:00</span>))}</div></div>
        </div>
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.25rem" }}><Play size={16} /> <Bi id="Mood musik × performa" en="Music mood × performance" /></h3>
          <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "1rem" }}><Bi id="Skor performa rata-rata per mood" en="Avg performance score per mood" /></div>
          <div className="an-heat" style={{ gridTemplateColumns: "repeat(3,1fr)", gap: 6 }}>
            {MOODS.map(([m, v]) => (<div key={m} style={{ background: heatColor(v), borderRadius: "var(--r-md)", padding: "0.875rem 0.5rem", textAlign: "center" }}><div style={{ fontSize: "var(--text-lg)", fontWeight: 700, color: "#fff" }}>{Math.round(v * 100)}</div><div style={{ fontSize: "var(--text-xs)", color: "rgba(255,255,255,0.8)" }}>{m}</div></div>))}
          </div>
        </div>
      </div>

      <div className="an-grid" style={{ marginTop: "1rem" }}>
        <div className="card">
          <div className="card-head"><h3 className="card-title"><TrendingUp size={16} /> <Bi id="Video teratas" en="Top videos" /></h3><span className="card-sub">30 hari</span></div>
          <div style={{ overflowX: "auto" }}><table className="tbl">
            <thead><tr><th></th><th>Topic</th><th>Channel</th><th className="num">Views</th><th className="num">CTR</th><th className="num">Retensi</th></tr></thead>
            <tbody>{TV.map(([t, ch, v, c, r]) => (<tr key={t}><td><span className="an-vthumb" /></td><td style={{ color: "var(--text-primary)" }}>{t}</td><td className="muted">{ch}</td><td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{v}</b></td><td className="num muted">{c}</td><td className="num muted">{r}</td></tr>))}</tbody>
          </table></div>
        </div>
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Sparkles size={16} /> <Bi id="Insight Self-Learning" en="Self-Learning Insights" /></h3>
          {INS.map((x, i) => (
            <div className="an-insight" key={i}>
              <span className="ic"><TrendingUp size={16} /></span>
              <div className="body">
                <div className="t"><span data-id dangerouslySetInnerHTML={{ __html: x.tId }} /><span data-en dangerouslySetInnerHTML={{ __html: x.tEn }} /></div>
                <div className="meta">{x.meta}</div>
                <div className="acts">
                  {x.applied || decision[i] === "accepted"
                    ? <span className="badge badge-success"><span className="dot" />{x.applied ? <Bi id="Diterapkan otomatis" en="Auto-applied" /> : <Bi id="Diterima" en="Accepted" />}</span>
                    : decision[i] === "rejected"
                      ? <span className="badge badge-default"><Bi id="Ditolak" en="Rejected" /></span>
                      : <>
                          <button className="btn btn-default btn-sm" onClick={() => setDecision((s) => ({ ...s, [i]: "accepted" }))}><Check size={13} /> <Bi id="Terima" en="Accept" /></button>
                          <button className="btn btn-ghost btn-sm" onClick={() => setDecision((s) => ({ ...s, [i]: "rejected" }))}><Bi id="Tolak" en="Reject" /></button>
                        </>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
