"use client";

import { useState } from "react";
import { Sparkles, TrendingUp, ChevronDown, Clock, RefreshCw, Settings, XCircle, HelpCircle, Zap, Info, Check } from "lucide-react";
import "./insights.css";

// D21 Self-Learning Insights — port dari design-source/Insights.html (Hybrid). Moat #1 produk.
// Timeline insight filterable + accept interaktif + rail override + riwayat adaptasi. Chart = bar CSS (bukan lib).
// Mock deterministik (SSR-safe). Data nyata = engine Self-Learning Phase 6+ (lihat guardrail v1/v2).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Status = "applied" | "pending" | "rejected";
type Insight = {
  cat: string; typeId: string; typeEn: string; date: string;
  titleId: string; titleEn: string; chart: [string, number, string][];
  adaptId: string; adaptEn: string; conf: string; status: Status;
};

const FILTERS: [string, string, string][] = [
  ["all", "Semua", "All"], ["niche", "Performa Niche", "Niche"], ["hook", "Hook Patterns", "Hooks"],
  ["topic", "Topic Clusters", "Topics"], ["time", "Publish Time", "Time"], ["music", "Music Mood", "Music"],
];

const INS: Insight[] = [
  { cat: "hook", typeId: "Hook Pattern", typeEn: "Hook Pattern", date: "2 jam lalu",
    titleId: 'Hook "gap question" perform 2.3× lebih baik dari rata-rata', titleEn: '"Gap question" hook performs 2.3× better than average',
    chart: [["gap", 92, "var(--accent)"], ["avg", 40, "var(--surface-3)"]],
    adaptId: 'Mesin akan memprioritaskan "gap question" di 60% video baru (sebelumnya 25%).', adaptEn: 'Engine will prioritize "gap question" in 60% of new videos (was 25%).',
    conf: "Berdasarkan 23 video · p=0.97", status: "applied" },
  { cat: "niche", typeId: "Performa Niche", typeEn: "Niche Performance", date: "1 hari lalu",
    titleId: 'Niche "Misteri Samudra" 1.5× lebih baik dari "Sejarah Kelam"', titleEn: '"Ocean Mysteries" niche 1.5× better than "Dark History"',
    chart: [["Samudra", 75, "var(--brand)"], ["Sejarah", 50, "var(--surface-3)"]],
    adaptId: 'Bobot "Misteri Samudra" dinaikkan +12% di rotasi jadwal.', adaptEn: '"Ocean Mysteries" weight raised +12% in schedule rotation.',
    conf: "Berdasarkan 41 video · p=0.96", status: "applied" },
  { cat: "time", typeId: "Waktu Publish", typeEn: "Publish Time", date: "2 hari lalu",
    titleId: "Slot 14:00 WIB punya engagement 30% lebih tinggi", titleEn: "14:00 WIB slot has 30% higher engagement",
    chart: [["10:00", 55, "var(--surface-3)"], ["14:00", 85, "var(--accent)"], ["19:00", 62, "var(--surface-3)"]],
    adaptId: "Disarankan tambah 1 slot di 14:00 WIB.", adaptEn: "Suggested adding 1 slot at 14:00 WIB.",
    conf: "Berdasarkan 42 video · p=0.94", status: "pending" },
  { cat: "hook", typeId: "Hook Pattern", typeEn: "Hook Pattern", date: "4 hari lalu",
    titleId: 'Hook "time pressure" under-perform di channel ini', titleEn: '"Time pressure" hook under-performs on this channel',
    chart: [["time", 28, "var(--error)"], ["avg", 55, "var(--surface-3)"]],
    adaptId: 'Mesin men-deprioritize "time pressure" ke 5%.', adaptEn: 'Engine deprioritized "time pressure" to 5%.',
    conf: "Berdasarkan 18 video · p=0.91", status: "rejected" },
];

const HIST: [string, string, string, Status, string][] = [
  ["8 Jun", 'Hook "gap question" +2.3×', "Prioritas 25%→60%", "applied", "+18% CTR"],
  ["6 Jun", "Niche Samudra > Sejarah", "Bobot +12%", "applied", "+1.5× views"],
  ["3 Jun", 'Music "tegang" perform', "Mood priority naik", "applied", "+9% retensi"],
  ["1 Jun", 'Hook "time pressure" lemah', "Deprioritize 5%", "rejected", "—"],
];

function StatusBadge({ s, accepted }: { s: Status; accepted?: boolean }) {
  if (accepted) return <span className="badge badge-success status"><span className="dot" /><Bi id="Diterima" en="Accepted" /></span>;
  if (s === "applied") return <span className="badge badge-success status"><span className="dot" /><Bi id="Diterapkan otomatis" en="Auto-applied" /></span>;
  if (s === "pending") return <span className="badge badge-warning status"><span className="dot" /><Bi id="Menunggu review" en="Pending review" /></span>;
  return <span className="badge badge-default status"><Bi id="Ditolak" en="Rejected" /></span>;
}

export default function InsightsPage() {
  const [filter, setFilter] = useState("all");
  const [accepted, setAccepted] = useState<number[]>([]);
  const items = INS.map((x, i) => ({ x, i })).filter(({ x }) => filter === "all" || x.cat === filter);

  return (
    <>
      <div className="page-head">
        <div>
          <h1><Sparkles size={26} style={{ color: "var(--accent)" }} /> Self-Learning Insights</h1>
          <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Apa yang mesin pelajari dari channelmu" en="What the engine has learned from your channel" /></div>
        </div>
        <div style={{ display: "flex", gap: "0.625rem", alignItems: "center" }}>
          <span className="grade"><TrendingUp size={13} /> Optimizing</span>
          <div className="ch-sel"><span className="dot-ch">MS</span> Misteri Samudra <ChevronDown size={14} /></div>
        </div>
      </div>

      <div className="hero-card">
        <div className="brain"><span className="ic"><Sparkles size={22} /></span>
          <h2><span data-id>Mesin sudah belajar dari <span style={{ color: "var(--accent)" }}>87 video</span> di channel ini</span><span data-en>The engine has learned from <span style={{ color: "var(--accent)" }}>87 videos</span> on this channel</span></h2>
        </div>
        <div className="meta">
          <span><Clock size={15} /> <Bi id="Tarikan analytics terakhir: 2 jam lalu" en="Last pull: 2 hours ago" /></span>
          <span><RefreshCw size={15} /> <Bi id="Adaptasi berikutnya: Senin 07:00 WIB" en="Next adaptation: Mon 07:00 WIB" /></span>
        </div>
        <div className="stat-strip">
          <div className="s"><div className="v">3</div><div className="l"><Bi id="Penyesuaian bobot niche" en="Niche weight adjustments" /></div></div>
          <div className="s"><div className="v">5</div><div className="l"><Bi id="Adaptasi hook" en="Hook adaptations" /></div></div>
          <div className="s"><div className="v">12</div><div className="l"><Bi id="Cluster topik ditemukan" en="Topic clusters discovered" /></div></div>
        </div>
      </div>

      <div className="filters">
        {FILTERS.map(([k, id, en]) => (
          <button key={k} className={`fpill${filter === k ? " sel" : ""}`} onClick={() => setFilter(k)}><Bi id={id} en={en} /></button>
        ))}
      </div>

      <div className="layout">
        <div className="tl">
          {items.map(({ x, i }) => {
            const isAccepted = accepted.includes(i);
            return (
              <div className="ins" key={i}><div className="ins-card">
                <div className="ins-top"><span className="ins-type"><Sparkles size={13} /> <Bi id={x.typeId} en={x.typeEn} /></span><span className="ins-date">{x.date}</span></div>
                <div className="ins-title"><Bi id={x.titleId} en={x.titleEn} /></div>
                <div className="ins-chart">{x.chart.map(([l, v, c]) => (<div className="b" key={l} style={{ height: `${v}%`, background: c }}><span className="cap">{l}</span></div>))}</div>
                <div className="ins-adapt"><span className="ic"><Zap size={15} /></span><div><b style={{ color: "var(--text-primary)" }}><Bi id="Adaptasi: " en="Adaptation: " /></b><Bi id={x.adaptId} en={x.adaptEn} /></div></div>
                <div className="ins-conf"><Info size={13} /> {x.conf}</div>
                <div className="ins-acts">
                  {x.status === "pending" && !isAccepted
                    ? <>
                        <button className="btn btn-default btn-sm" onClick={() => setAccepted((a) => [...a, i])}><Check size={13} /> <Bi id="Terima" en="Accept" /></button>
                        <button className="btn btn-ghost btn-sm"><Bi id="Tolak" en="Reject" /></button>
                        <button className="btn btn-ghost btn-icon btn-sm"><HelpCircle size={13} /></button>
                      </>
                    : <button className="btn btn-ghost btn-sm"><RefreshCw size={13} /> <Bi id="Tinjau" en="Review" /></button>}
                  <StatusBadge s={x.status} accepted={isAccepted} />
                </div>
              </div></div>
            );
          })}
        </div>

        <div className="rail">
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.875rem" }}><Settings size={15} /> <Bi id="Override manual" en="Manual override" /></h3>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginBottom: "0.75rem" }}><Bi id="Atur sendiri pembelajaran (power user)." en="Tune the learnings yourself (power users)." /></div>
            <div style={{ marginBottom: "0.875rem" }}><div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", marginBottom: "0.375rem" }}><span className="secondary"><Bi id={'Bobot "Misteri Samudra"'} en={'"Ocean Mysteries" weight'} /></span><span className="mono">+12%</span></div><input type="range" className="slider" min={0} max={100} defaultValue={62} style={{ width: "100%", accentColor: "var(--accent)" }} /></div>
            <div style={{ marginBottom: "0.875rem" }}><div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", marginBottom: "0.375rem" }}><span className="secondary"><Bi id={'Prioritas hook "gap question"'} en={'"gap question" hook priority'} /></span><span className="mono">60%</span></div><input type="range" className="slider" min={0} max={100} defaultValue={60} style={{ width: "100%", accentColor: "var(--accent)" }} /></div>
            <hr className="hr" style={{ margin: "0.875rem 0" }} />
            <button className="btn btn-outline btn-sm" style={{ width: "100%", color: "var(--error)", borderColor: "color-mix(in srgb,var(--error) 40%,transparent)" }}><XCircle size={14} /> <Bi id="Reset semua pembelajaran" en="Reset all learning" /></button>
          </div>
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.5rem" }}><HelpCircle size={15} /> <Bi id="Cara kerja" en="How it works" /></h3>
            <p className="muted" style={{ fontSize: "var(--text-xs)", lineHeight: 1.6, margin: "0 0 0.625rem" }}><Bi id="Setiap minggu mesin menarik YouTube Analytics channelmu dan menyesuaikan strategi produksi." en="Each week the engine pulls your YouTube Analytics and adjusts production strategy." /></p>
            <div style={{ fontSize: "var(--text-xs)", padding: "0.625rem", background: "var(--bg-elevated)", borderRadius: "var(--r-md)", border: "1px solid var(--border-subtle)" }}><b style={{ color: "var(--text-primary)" }}><Bi id="Q: Belajar antar-channel?" en="Q: Learn across channels?" /></b><br /><span className="muted"><Bi id="Tidak — isolasi per-channel. Data satu channel tidak bocor ke channel lain." en="No — per-channel isolation. One channel's data never leaks to another." /></span></div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1.5rem" }}>
        <div className="card-head"><h3 className="card-title"><Clock size={16} /> <Bi id="Riwayat adaptasi" en="History of adaptations" /></h3></div>
        <div style={{ overflowX: "auto" }}><table className="tbl">
          <thead><tr><th>Tanggal</th><th>Insight</th><th><Bi id="Adaptasi" en="Adaptation" /></th><th>Status</th><th className="num"><Bi id="Dampak (14h)" en="Impact (14d)" /></th></tr></thead>
          <tbody>{HIST.map(([d, ins, ad, st, imp]) => (
            <tr key={d + ins}><td className="muted">{d}</td><td style={{ color: "var(--text-primary)" }}>{ins}</td><td className="muted">{ad}</td>
              <td>{st === "applied" ? <span className="badge badge-success"><span className="dot" />Applied</span> : <span className="badge badge-default">Rejected</span>}</td>
              <td className="num" style={{ color: imp !== "—" ? "var(--success)" : "var(--text-muted)" }}>{imp}</td></tr>
          ))}</tbody>
        </table></div>
      </div>
    </>
  );
}
