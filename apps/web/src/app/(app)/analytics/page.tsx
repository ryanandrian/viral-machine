"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Calendar, Activity, BarChart3, Play, Target, Zap, Eye, TrendingUp, Users, MessageSquare, Sparkles, ArrowRight } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./analytics.css";

// D6 Analytics (Phase 9.4) — DATA NYATA dari video_analytics (RLS auth.uid()). Dedupe latest per video_id
// (views kumulatif → max). KPIs/niche/top/CTR/views-line real; retensi/biaya/heatmap = jujur bila tak ada sumber.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const fmtK = (n: number) => n >= 1_000_000 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

type VA = { video_id: string; views: number; likes: number; comments: number; subscriber_gain: number; ctr: number; avg_view_pct: number; niche: string | null; title: string | null; hook_text: string | null; published_at: string | null };

function ViewsChart({ pts }: { pts: number[] }) {
  const W = 640, H = 230, pad = 12, max = Math.max(1, ...pts);
  const x = (i: number) => pad + i * (W - pad * 2) / Math.max(1, pts.length - 1);
  const y = (v: number) => H - 22 - (v / max) * (H - 40);
  const line = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(0)} ${y(v).toFixed(0)}`).join(" ");
  return (
    <svg viewBox="0 0 640 230" style={{ width: "100%", height: "auto" }}>
      <defs><linearGradient id="an-ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6366F1" stopOpacity={0.25} /><stop offset="1" stopColor="#6366F1" stopOpacity={0} /></linearGradient></defs>
      {[0, 0.5, 1].map((f) => { const v = max * f; return (<g key={f}><line x1={pad} y1={y(v)} x2={W - pad} y2={y(v)} stroke="var(--grid-line)" /><text x={pad} y={y(v) - 3} fontSize={9} fill="var(--text-muted)" fontFamily="JetBrains Mono">{fmtK(Math.round(v))}</text></g>); })}
      {pts.length > 1 && <><path d={`${line} L${x(pts.length - 1)} ${H - 22} L${pad} ${H - 22} Z`} fill="url(#an-ag)" /><path d={line} fill="none" stroke="#6366F1" strokeWidth={2} /></>}
    </svg>
  );
}
function CtrHist({ bins }: { bins: [string, number][] }) {
  const W = 300, H = 230, pad = 24, max = Math.max(1, ...bins.map((b) => b[1])), bw = (W - pad * 2) / bins.length;
  return (
    <svg viewBox="0 0 300 230" style={{ width: "100%", height: "auto" }}>
      {bins.map(([l, v], i) => { const h = (v / max) * (H - 50), bx = pad + i * bw; return (
        <g key={l}><rect x={bx + 6} y={H - 30 - h} width={bw - 12} height={h} rx={4} fill="#6366F1" /><text x={bx + bw / 2} y={H - 14} fontSize={9} fill="var(--text-muted)" textAnchor="middle" fontFamily="JetBrains Mono">{l}</text><text x={bx + bw / 2} y={H - 36 - h} fontSize={10} fill="var(--text-secondary)" textAnchor="middle">{v}</text></g>
      ); })}
    </svg>
  );
}

export default function AnalyticsPage() {
  const supabase = createClient();
  const [rows, setRows] = useState<VA[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.from("video_analytics").select("video_id, views, likes, comments, subscriber_gain, ctr, avg_view_pct, niche, title, hook_text, published_at").then(({ data }) => {
      // dedupe latest per video_id (views kumulatif → max)
      const byVid = new Map<string, VA>();
      (data ?? []).forEach((r) => { const cur = byVid.get(r.video_id); if (!cur || (r.views ?? 0) >= (cur.views ?? 0)) byVid.set(r.video_id, r as VA); });
      setRows([...byVid.values()]); setLoading(false);
    });
  }, [supabase]);

  const totalViews = rows.reduce((s, r) => s + (r.views ?? 0), 0);
  const totalLikes = rows.reduce((s, r) => s + (r.likes ?? 0), 0);
  const totalComments = rows.reduce((s, r) => s + (r.comments ?? 0), 0);
  const subs = rows.reduce((s, r) => s + (r.subscriber_gain ?? 0), 0);
  const ctrs = rows.filter((r) => (r.ctr ?? 0) > 0).map((r) => r.ctr);
  const avgCtr = ctrs.length ? (ctrs.reduce((a, b) => a + b, 0) / ctrs.length) : 0;
  const rets = rows.filter((r) => (r.avg_view_pct ?? 0) > 0).map((r) => r.avg_view_pct);
  const avgRet = rets.length ? Math.round(rets.reduce((a, b) => a + b, 0) / rets.length) : null;

  const KPI = [
    { Icon: Play, l: ["Video dianalisis", "Videos analyzed"], v: String(rows.length) },
    { Icon: Eye, l: ["Total Views", "Total Views"], v: fmtK(totalViews) },
    { Icon: TrendingUp, l: ["Avg CTR", "Avg CTR"], v: avgCtr ? `${avgCtr.toFixed(1)}%` : "—" },
    { Icon: Activity, l: ["Avg Retensi", "Avg Retention"], v: avgRet != null ? `${avgRet}%` : "—" },
    { Icon: Users, l: ["Subs", "Subs Gained"], v: `+${fmtK(subs)}` },
    { Icon: MessageSquare, l: ["Komentar", "Comments"], v: fmtK(totalComments) },
  ];

  // niche distribution (views), top videos, CTR bins, views-over-time (by published month)
  const nicheViews = new Map<string, number>();
  rows.forEach((r) => { if (r.niche) nicheViews.set(r.niche, (nicheViews.get(r.niche) ?? 0) + (r.views ?? 0)); });
  const nicheTop = [...nicheViews.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  const nicheMax = Math.max(1, ...nicheTop.map((n) => n[1]));
  const NCOL = ["#6366F1", "#10B981", "#EC4899", "#F59E0B", "#0ea5e9", "#a855f7"];

  const hookViews = new Map<string, number>();
  rows.forEach((r) => { if (r.hook_text) { const k = r.hook_text.slice(0, 40); hookViews.set(k, (hookViews.get(k) ?? 0) + (r.views ?? 0)); } });
  const hookTop = [...hookViews.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  const hookMax = Math.max(1, ...hookTop.map((h) => h[1]));

  const topVideos = [...rows].sort((a, b) => (b.views ?? 0) - (a.views ?? 0)).slice(0, 6);

  const binDefs: [string, (c: number) => boolean][] = [["0-2%", (c) => c < 2], ["2-4%", (c) => c >= 2 && c < 4], ["4-6%", (c) => c >= 4 && c < 6], ["6-8%", (c) => c >= 6 && c < 8], ["8%+", (c) => c >= 8]];
  const ctrBins: [string, number][] = binDefs.map(([l, f]) => [l, rows.filter((r) => f((r.ctr ?? 0))).length]);

  const monthViews = new Map<string, number>();
  rows.forEach((r) => { if (r.published_at) { const m = r.published_at.slice(0, 7); monthViews.set(m, (monthViews.get(m) ?? 0) + (r.views ?? 0)); } });
  const viewsLine = [...monthViews.entries()].sort().map((e) => e[1]);

  return (
    <>
      <div className="an-head">
        <div><h1>Analytics</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Performa channel dari data nyata" en="Real channel performance" /></div></div>
      </div>

      <div className="an-filters"><div className="an-selbox"><Calendar size={14} /> {loading ? "Memuat…" : `${rows.length} video`}</div></div>

      <div className="an-kpi-strip">
        {KPI.map((k, i) => (<div className="an-kpic" key={i}><div className="l"><k.Icon size={13} /> <Bi id={k.l[0]} en={k.l[1]} /></div><div className="v">{k.v}</div></div>))}
      </div>

      <div className="an-grid">
        <div className="card"><div className="card-head"><h3 className="card-title"><Activity size={16} /> <Bi id="Views per bulan" en="Views per month" /></h3></div><div className="card-body">{viewsLine.length > 1 ? <ViewsChart pts={viewsLine} /> : <div className="muted" style={{ padding: "2rem", textAlign: "center", fontSize: "var(--text-sm)" }}>Belum cukup rentang waktu.</div>}</div></div>
        <div className="card"><div className="card-head"><h3 className="card-title"><BarChart3 size={16} /> <Bi id="Distribusi CTR" en="CTR distribution" /></h3></div><div className="card-body"><CtrHist bins={ctrBins} />{!avgCtr && <div className="muted" style={{ fontSize: "var(--text-xs)", padding: "0 1rem 0.75rem" }}>CTR=0 mayoritas (analytics-scope belum di-fetch penuh — self-learning loop harian akan mengisi).</div>}</div></div>
      </div>

      <div className="an-grid-3">
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Target size={16} /> <Bi id="Niche teratas (views)" en="Top niches (views)" /></h3>
          {nicheTop.length === 0 ? <div className="muted" style={{ fontSize: "var(--text-sm)" }}>—</div> : nicheTop.map(([n, v], i) => (<div className="an-bar-row" key={n}><span className="lab">{n}</span><div className="an-bar-track"><span style={{ width: `${Math.round((v / nicheMax) * 100)}%`, background: NCOL[i % NCOL.length] }} /></div><span className="val">{fmtK(v)}</span></div>))}
        </div>
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Zap size={16} /> <Bi id="Hook teratas (views)" en="Top hooks (views)" /></h3>
          {hookTop.length === 0 ? <div className="muted" style={{ fontSize: "var(--text-sm)" }}>—</div> : hookTop.map(([n, v]) => (<div className="an-bar-row" key={n}><span className="lab" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n}</span><div className="an-bar-track"><span style={{ width: `${Math.round((v / hookMax) * 100)}%`, background: "#6366F1" }} /></div><span className="val">{fmtK(v)}</span></div>))}
        </div>
      </div>

      <div className="an-grid" style={{ marginTop: "1rem" }}>
        <div className="card">
          <div className="card-head"><h3 className="card-title"><TrendingUp size={16} /> <Bi id="Video teratas" en="Top videos" /></h3></div>
          <div style={{ overflowX: "auto" }}><table className="tbl">
            <thead><tr><th>Topic</th><th>Niche</th><th className="num">Views</th><th className="num">CTR</th></tr></thead>
            <tbody>
              {topVideos.length === 0 && <tr><td colSpan={4} className="muted" style={{ padding: "1rem", textAlign: "center" }}>{loading ? "Memuat…" : "Belum ada data."}</td></tr>}
              {topVideos.map((r) => (<tr key={r.video_id}><td style={{ color: "var(--text-primary)" }}>{r.title || r.video_id}</td><td className="muted">{r.niche || "—"}</td><td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{fmtK(r.views ?? 0)}</b></td><td className="num muted">{(r.ctr ?? 0) > 0 ? `${r.ctr.toFixed(1)}%` : "—"}</td></tr>))}
            </tbody>
          </table></div>
        </div>
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Sparkles size={16} /> <Bi id="Insight Self-Learning" en="Self-Learning Insights" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Adaptasi niche/hook per-channel ada di halaman Wawasan." en="Per-channel niche/hook adaptation lives on the Insights page." /></p>
          <Link href="/insights" className="btn btn-secondary btn-sm"><Bi id="Buka Wawasan" en="Open Insights" /> <ArrowRight size={14} /></Link>
        </div>
      </div>
    </>
  );
}
