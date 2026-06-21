"use client";

import { Sparkles, TrendingUp, Clock, RefreshCw, HelpCircle, Zap, Target } from "lucide-react";
import "../app/(app)/insights/insights.css";

// Komponen bersama Self-Learning Insights (F2-13) — dipakai MAIN /insights (agregat) DAN tab
// Channel Detail (per-channel). Satu sumber render → nol duplikat.

export type Insights = { performance_grade: string; videos_analyzed: number; niche_weights: Record<string, number>; top_hooks: { hook: string; pattern: string; views: number; ctr: number }[]; avoid_patterns: string[]; computed_at: string; channels_count?: number };

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const prettyNiche = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function InsightsView({ insights: ins, loading, scopeLabel }: {
  insights: Insights | null; loading: boolean; scopeLabel?: { id: string; en: string };
}) {
  const weights = Object.entries(ins?.niche_weights ?? {}).sort((a, b) => b[1] - a[1]);
  const maxW = Math.max(0.001, ...weights.map((w) => w[1]));
  const hooks = (ins?.top_hooks ?? []).filter((h) => h.hook).slice(0, 6);
  const topNiche = weights[0], lowNiche = weights[weights.length - 1];
  const scopeTxt = scopeLabel ?? { id: "channel ini", en: "this channel" };

  return (
    <>
      <div className="hero-card">
        <div className="brain"><span className="ic"><Sparkles size={22} /></span>
          <h2><span data-id>Mesin sudah belajar dari <span style={{ color: "var(--accent)" }}>{ins?.videos_analyzed ?? 0} video</span> di {scopeTxt.id}</span><span data-en>The engine learned from <span style={{ color: "var(--accent)" }}>{ins?.videos_analyzed ?? 0} videos</span> in {scopeTxt.en}</span></h2>
          {ins && <span className="grade"><TrendingUp size={13} /> {prettyNiche(ins.performance_grade)}</span>}
        </div>
        <div className="meta">
          <span><Clock size={15} /> <Bi id="Komputasi terakhir" en="Last computed" />: {ins ? new Date(ins.computed_at).toLocaleString("id-ID") : "—"}</span>
          <span><RefreshCw size={15} /> <Bi id="Adaptasi: loop self-learning harian" en="Adaptation: daily self-learning loop" /></span>
        </div>
        <div className="stat-strip">
          <div className="s"><div className="v">{weights.length}</div><div className="l"><Bi id="Niche dibobot" en="Niches weighted" /></div></div>
          <div className="s"><div className="v">{hooks.length}</div><div className="l"><Bi id="Hook teratas" en="Top hooks" /></div></div>
          <div className="s"><div className="v">{ins?.avoid_patterns?.length ?? 0}</div><div className="l"><Bi id="Pola dihindari" en="Avoid patterns" /></div></div>
        </div>
      </div>

      <div className="layout">
        <div className="tl">
          {loading && <div className="muted" style={{ padding: "1.5rem" }}>Memuat…</div>}
          {!loading && !ins && <div className="muted" style={{ padding: "1.5rem" }}>Belum ada insight. Loop self-learning akan mengisi setelah cukup data.</div>}

          {topNiche && (
            <div className="ins"><div className="ins-card">
              <div className="ins-top"><span className="ins-type"><Target size={13} /> <Bi id="Performa Niche" en="Niche Performance" /></span></div>
              <div className="ins-title"><Bi id={`Niche "${prettyNiche(topNiche[0])}" paling diprioritaskan mesin (bobot ${(topNiche[1] * 100).toFixed(1)}%)`} en={`"${prettyNiche(topNiche[0])}" is the engine's top-weighted niche (${(topNiche[1] * 100).toFixed(1)}%)`} /></div>
              <div className="ins-chart" style={{ alignItems: "flex-end" }}>
                {weights.slice(0, 5).map(([n, w]) => (<div className="b" key={n} style={{ height: `${Math.round((w / maxW) * 100)}%`, background: n === topNiche[0] ? "var(--brand)" : "var(--surface-3)" }}><span className="cap">{prettyNiche(n).split(" ")[0]}</span></div>))}
              </div>
              <div className="ins-adapt"><span className="ic"><Zap size={15} /></span><div><b style={{ color: "var(--text-primary)" }}><Bi id="Adaptasi: " en="Adaptation: " /></b><Bi id={`Rotasi produksi condong ke "${prettyNiche(topNiche[0])}"; "${prettyNiche(lowNiche[0])}" paling rendah (${(lowNiche[1] * 100).toFixed(1)}%).`} en={`Production rotation favors "${prettyNiche(topNiche[0])}"; "${prettyNiche(lowNiche[0])}" lowest (${(lowNiche[1] * 100).toFixed(1)}%).`} /></div></div>
            </div></div>
          )}

          {hooks.length > 0 && (
            <div className="ins"><div className="ins-card">
              <div className="ins-top"><span className="ins-type"><Zap size={13} /> <Bi id="Hook teratas (engine view)" en="Top hooks (engine view)" /></span></div>
              <div className="ins-title"><Bi id="Hook dengan views tertinggi yang dipakai mesin sebagai referensi" en="Highest-view hooks the engine references" /></div>
              <div style={{ overflowX: "auto", marginTop: "0.75rem" }}><table className="tbl">
                <thead><tr><th>Hook</th><th>Pattern</th><th className="num">Views</th></tr></thead>
                <tbody>{hooks.map((h, i) => (<tr key={i}><td style={{ color: "var(--text-primary)" }}>{h.hook.slice(0, 50)}</td><td className="muted">{h.pattern || "—"}</td><td className="num">{h.views ?? 0}</td></tr>))}</tbody>
              </table></div>
            </div></div>
          )}

          {(ins?.avoid_patterns?.length ?? 0) > 0 && (
            <div className="ins"><div className="ins-card">
              <div className="ins-top"><span className="ins-type"><RefreshCw size={13} /> <Bi id="Pola dihindari" en="Avoid patterns" /></span></div>
              <div className="ins-title">{(ins!.avoid_patterns).join(", ")}</div>
            </div></div>
          )}
        </div>

        <div className="rail">
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.5rem" }}><HelpCircle size={15} /> <Bi id="Cara kerja" en="How it works" /></h3>
            <p className="muted" style={{ fontSize: "var(--text-xs)", lineHeight: 1.6, margin: "0 0 0.625rem" }}><Bi id="Loop harian menarik YouTube Analytics channelmu lalu menyesuaikan bobot niche & strategi hook. Diterapkan otomatis." en="A daily loop pulls your YouTube Analytics, then adjusts niche weights & hook strategy. Auto-applied." /></p>
            <div style={{ fontSize: "var(--text-xs)", padding: "0.625rem", background: "var(--bg-elevated)", borderRadius: "var(--r-md)", border: "1px solid var(--border-subtle)" }}><b style={{ color: "var(--text-primary)" }}><Bi id="Q: Belajar antar-channel?" en="Q: Learn across channels?" /></b><br /><span className="muted"><Bi id="Tidak — isolasi per-channel (RLS)." en="No — per-channel isolation (RLS)." /></span></div>
          </div>
        </div>
      </div>
    </>
  );
}
