"use client";

import { Sparkles, TrendingUp, Clock, RefreshCw, HelpCircle, Zap, Target, Brain, Layers, Trophy, ArrowUp, ArrowDown } from "lucide-react";
import "../app/(app)/insights/insights.css";

// Komponen bersama Self-Learning Insights (F2-13) — dipakai MAIN /insights (agregat) DAN tab
// Channel Detail (per-channel). Satu sumber render → nol duplikat. UI pakai kelas design-system
// yang ada (.ins-card/.tbl/.progress/.ins-chart) — TANPA komponen/gaya baru.
// Menampilkan apa yang mesin PELAJARI & PAKAI: niche weights, formula adaptif (bobot dimensi viral),
// performa jenis konten, topik pemenang, hook teratas (teks penuh + retensi + subscriber).

export type Insights = {
  performance_grade: string; videos_analyzed: number; niche_weights: Record<string, number>;
  top_hooks: { hook: string; pattern: string; views: number; ctr?: number; avg_view_pct?: number; subscriber_gain?: number }[];
  avoid_patterns: string[]; computed_at: string; channels_count?: number;
  content_type_perf?: Record<string, { avg_view_pct: number; avg_views: number; count: number; retention_count?: number }> | null;
  top_topics?: { title: string; niche?: string; views: number; subscriber_gain?: number; avg_view_pct?: number; composite_score?: number }[] | null;
};

// Formula adaptif (S3-A) — tenant_configs.viral_score_weights. Tenant-wide (per akun, bukan per-channel).
export type LearnedWeights = { weights: Record<string, number>; correlations?: Record<string, number>; videos_analyzed?: number; alpha?: number } | null;

// Bobot baseline = SATU sumber kebenaran (selaras src/intelligence/config.py VIRAL_SCORE_WEIGHTS).
// Diekspor agar run-detail (breakdown skor) pakai ulang — nol duplikat.
export const BASELINE_WEIGHTS: Record<string, number> = { search_volume: 0.25, trend_momentum: 0.25, emotional_trigger: 0.20, competition_gap: 0.15, evergreen_potential: 0.15 };
export const DIM_LABEL: Record<string, { id: string; en: string }> = {
  search_volume:       { id: "Volume pencarian",         en: "Search volume" },
  trend_momentum:      { id: "Momentum tren",            en: "Trend momentum" },
  emotional_trigger:   { id: "Pemicu emosi",             en: "Emotional trigger" },
  competition_gap:     { id: "Celah persaingan",         en: "Competition gap" },
  evergreen_potential: { id: "Potensi awet (evergreen)", en: "Evergreen potential" },
};

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const prettyNiche = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
const fmtNum = (n: number) => (n ?? 0).toLocaleString("id-ID");

export function InsightsView({ insights: ins, loading, scopeLabel, learnedWeights }: {
  insights: Insights | null; loading: boolean; scopeLabel?: { id: string; en: string }; learnedWeights?: LearnedWeights;
}) {
  const weights = Object.entries(ins?.niche_weights ?? {}).sort((a, b) => b[1] - a[1]);
  const maxW = Math.max(0.001, ...weights.map((w) => w[1]));
  // Dedup defensif by teks hook (sumber sudah dedup; lindungi data lama + gabungan lintas channel).
  const hooks = (() => {
    const seen = new Set<string>(); const out: NonNullable<Insights["top_hooks"]> = [];
    for (const h of ins?.top_hooks ?? []) { const k = (h.hook || "").trim().toLowerCase(); if (!k || seen.has(k)) continue; seen.add(k); out.push(h); }
    return out.slice(0, 6);
  })();
  const topNiche = weights[0], lowNiche = weights[weights.length - 1];
  const scopeTxt = scopeLabel ?? { id: "channel ini", en: "this channel" };

  // #2 Formula adaptif: urut bobot desc; tampil hanya jika sudah-belajar (cukup data & beda dari baseline).
  const lw = learnedWeights?.weights ? learnedWeights : null;
  const learnedRows = lw ? Object.entries(lw.weights).sort((a, b) => b[1] - a[1]) : [];
  const learnedMaxW = Math.max(0.001, ...learnedRows.map((w) => w[1]));
  const hasLearned = !!lw && (lw.videos_analyzed ?? 0) >= 20 &&
    learnedRows.some(([d, w]) => Math.abs(w - (BASELINE_WEIGHTS[d] ?? 0)) > 0.02);

  // #3 Performa jenis konten: urut retensi desc (hanya yg punya data retensi nyata).
  // Kecualikan kunci yang juga niche (content_type kosong → BE infer ke nama niche) — niche sudah
  // punya kartu sendiri, jadi kartu ini fokus ke JENIS konten asli (mystery/listicle/question/...).
  const nicheKeys = new Set(Object.keys(ins?.niche_weights ?? {}));
  const ctRows = Object.entries(ins?.content_type_perf ?? {})
    .filter(([k, v]) => v && (v.retention_count ?? 0) > 0 && !nicheKeys.has(k))
    .sort((a, b) => b[1].avg_view_pct - a[1].avg_view_pct);

  // #4 Topik pemenang: dedup defensif by judul.
  const topics = (() => {
    const seen = new Set<string>(); const out: NonNullable<Insights["top_topics"]> = [];
    for (const t of ins?.top_topics ?? []) { const k = (t.title || "").trim().toLowerCase(); if (!k || seen.has(k)) continue; seen.add(k); out.push(t); }
    return out.slice(0, 6);
  })();

  // warna retensi (selaras pola channels/page: override background span .progress)
  const retColor = (pct: number) => pct >= 60 ? "var(--success)" : pct >= 40 ? "var(--warning)" : "var(--error)";

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
          <div className="s"><div className="v">{ctRows.length}</div><div className="l"><Bi id="Jenis konten" en="Content types" /></div></div>
          <div className="s"><div className="v">{hooks.length}</div><div className="l"><Bi id="Hook teratas" en="Top hooks" /></div></div>
        </div>
      </div>

      <div className="layout">
        <div className="tl">
          {loading && <div className="muted" style={{ padding: "1.5rem" }}>Memuat…</div>}
          {!loading && !ins && <div className="muted" style={{ padding: "1.5rem" }}>Belum ada insight. Loop self-learning akan mengisi setelah cukup data.</div>}

          {/* #2 FORMULA ADAPTIF — apa yang mesin pelajari paling menentukan sukses */}
          {hasLearned && (
            <div className="ins"><div className="ins-card">
              <div className="ins-top"><span className="ins-type"><Brain size={13} /> <Bi id="Formula yang dipelajari mesin" en="What the engine learned" /></span><span className="ins-date">{learnedWeights?.videos_analyzed ?? 0} <Bi id="video" en="videos" /></span></div>
              <div className="ins-title"><Bi id={`Mesin menemukan "${DIM_LABEL[learnedRows[0][0]]?.id ?? learnedRows[0][0]}" paling menentukan video sukses channelmu`} en={`The engine found "${DIM_LABEL[learnedRows[0][0]]?.en ?? learnedRows[0][0]}" matters most for your winning videos`} /></div>
              <table className="tbl">
                <thead><tr><th><Bi id="Sinyal penilaian" en="Scoring signal" /></th><th><Bi id="Bobot mesin" en="Engine weight" /></th><th className="num"><Bi id="vs baseline" en="vs baseline" /></th></tr></thead>
                <tbody>{learnedRows.map(([dim, w]) => {
                  const base = BASELINE_WEIGHTS[dim] ?? 0; const up = w >= base + 0.005, down = w < base - 0.005;
                  return (<tr key={dim}>
                    <td style={{ color: "var(--text-primary)" }}>{DIM_LABEL[dim] ? <Bi id={DIM_LABEL[dim].id} en={DIM_LABEL[dim].en} /> : prettyNiche(dim)}</td>
                    <td><div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><div className="progress" style={{ flex: 1, minWidth: 70 }}><span style={{ width: `${Math.round((w / learnedMaxW) * 100)}%`, background: dim === learnedRows[0][0] ? "var(--brand)" : "var(--surface-3)" }} /></div><span className="num" style={{ width: 34, color: "var(--text-primary)", fontWeight: 600 }}>{(w * 100).toFixed(0)}%</span></div></td>
                    <td className="num" style={{ color: up ? "var(--success)" : down ? "var(--text-muted)" : "var(--text-secondary)" }}>{up ? <ArrowUp size={12} /> : down ? <ArrowDown size={12} /> : null} {(base * 100).toFixed(0)}%</td>
                  </tr>);
                })}</tbody>
              </table>
              <div className="ins-adapt"><span className="ic"><Zap size={15} /></span><div><b style={{ color: "var(--text-primary)" }}><Bi id="Adaptasi: " en="Adaptation: " /></b><Bi id="Mesin menaikkan bobot sinyal yang terbukti berkorelasi dengan performa nyata channelmu, lalu memakainya saat memilih topik." en="The engine raises the weight of signals proven to correlate with your real performance, then uses them when picking topics." /></div></div>
            </div></div>
          )}

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

          {/* #3 PERFORMA JENIS KONTEN */}
          {ctRows.length > 0 && (
            <div className="ins"><div className="ins-card">
              <div className="ins-top"><span className="ins-type"><Layers size={13} /> <Bi id="Performa per jenis konten" en="Content type performance" /></span></div>
              <div className="ins-title"><Bi id="Jenis konten yang paling menahan penonton (retensi rata-rata)" en="Which content types retain viewers best (avg retention)" /></div>
              <table className="tbl">
                <thead><tr><th><Bi id="Jenis konten" en="Content type" /></th><th><Bi id="Retensi" en="Retention" /></th><th className="num"><Bi id="Video" en="Videos" /></th></tr></thead>
                <tbody>{ctRows.slice(0, 6).map(([ct, v]) => (<tr key={ct}>
                  <td style={{ color: "var(--text-primary)" }}>{prettyNiche(ct)}</td>
                  <td><div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}><div className="progress" style={{ flex: 1, minWidth: 70 }}><span style={{ width: `${Math.min(100, v.avg_view_pct)}%`, background: retColor(v.avg_view_pct) }} /></div><span className="num" style={{ width: 34, color: retColor(v.avg_view_pct), fontWeight: 600 }}>{v.avg_view_pct.toFixed(0)}%</span></div></td>
                  <td className="num">{v.count}</td>
                </tr>))}</tbody>
              </table>
            </div></div>
          )}

          {/* #4 TOPIK PEMENANG */}
          {topics.length > 0 && (
            <div className="ins"><div className="ins-card">
              <div className="ins-top"><span className="ins-type"><Trophy size={13} /> <Bi id="Topik pemenang" en="Winning topics" /></span></div>
              <div className="ins-title"><Bi id="Topik dengan views + pertumbuhan subscriber terbaik" en="Topics with the best views + subscriber growth" /></div>
              <div style={{ overflowX: "auto" }}><table className="tbl">
                <thead><tr><th><Bi id="Judul" en="Title" /></th><th className="num">Views</th><th className="num">+Sub</th><th className="num"><Bi id="Retensi" en="Retention" /></th></tr></thead>
                <tbody>{topics.map((t, i) => (<tr key={i}>
                  <td style={{ color: "var(--text-primary)" }}>{t.title}</td>
                  <td className="num">{fmtNum(t.views ?? 0)}</td>
                  <td className="num" style={{ color: (t.subscriber_gain ?? 0) > 0 ? "var(--success)" : "var(--text-muted)" }}>{(t.subscriber_gain ?? 0) > 0 ? `+${t.subscriber_gain}` : "—"}</td>
                  <td className="num">{t.avg_view_pct != null ? `${Math.min(100, t.avg_view_pct).toFixed(0)}%` : "—"}</td>
                </tr>))}</tbody>
              </table></div>
            </div></div>
          )}

          {/* #1 HOOK TERATAS — teks penuh + retensi + subscriber */}
          {hooks.length > 0 && (
            <div className="ins"><div className="ins-card">
              <div className="ins-top"><span className="ins-type"><Zap size={13} /> <Bi id="Hook teratas (engine view)" en="Top hooks (engine view)" /></span></div>
              <div className="ins-title"><Bi id="Hook berperforma terbaik yang dipakai mesin sebagai referensi" en="Best-performing hooks the engine references" /></div>
              <div style={{ overflowX: "auto" }}><table className="tbl">
                <thead><tr><th>Hook</th><th>Pattern</th><th className="num"><Bi id="Retensi" en="Retention" /></th><th className="num">Views</th><th className="num">+Sub</th></tr></thead>
                <tbody>{hooks.map((h, i) => (<tr key={i}>
                  <td style={{ color: "var(--text-primary)", minWidth: 220 }}>{h.hook}</td>
                  <td className="muted">{h.pattern || "—"}</td>
                  <td className="num">{h.avg_view_pct != null ? `${Math.min(100, h.avg_view_pct).toFixed(0)}%` : "—"}</td>
                  <td className="num">{fmtNum(h.views ?? 0)}</td>
                  <td className="num" style={{ color: (h.subscriber_gain ?? 0) > 0 ? "var(--success)" : "var(--text-muted)" }}>{(h.subscriber_gain ?? 0) > 0 ? `+${h.subscriber_gain}` : "—"}</td>
                </tr>))}</tbody>
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
            <p className="muted" style={{ fontSize: "var(--text-xs)", lineHeight: 1.6, margin: "0 0 0.625rem" }}><Bi id="Loop harian menarik YouTube Analytics channelmu lalu menyesuaikan bobot niche, formula skor & strategi hook. Diterapkan otomatis ke produksi berikutnya." en="A daily loop pulls your YouTube Analytics, then adjusts niche weights, the scoring formula & hook strategy. Auto-applied to the next productions." /></p>
            <div style={{ fontSize: "var(--text-xs)", padding: "0.625rem", background: "var(--bg-elevated)", borderRadius: "var(--r-md)", border: "1px solid var(--border-subtle)" }}><b style={{ color: "var(--text-primary)" }}><Bi id="Q: Belajar antar-channel?" en="Q: Learn across channels?" /></b><br /><span className="muted"><Bi id="Tidak — tiap channel belajar dari datanya sendiri (isolasi per-channel)." en="No — each channel learns from its own data (per-channel isolation)." /></span></div>
          </div>
        </div>
      </div>
    </>
  );
}
