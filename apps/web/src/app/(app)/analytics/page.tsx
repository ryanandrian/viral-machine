"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, BarChart3, Target, Zap, Eye, TrendingUp, Users, MessageSquare, Sparkles, ArrowRight, Film, Percent, Flame, ChevronDown } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/page-header";
import "./analytics.css";

// D6 Analytics — DATA NYATA via RPC server-side (0058): overview/by-niche/monthly/top-videos/learning.
// Fokus kreator pro: tumbuh? · apa yang berhasil (niche/hook/topik)? · video teratas. CTR DIBUANG (tak tersedia API).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const fmtK = (n: number) => n >= 1_000_000 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n ?? 0);
const pct = (v: number | null) => (v == null ? "—" : `${v}%`);
function ago(iso: string | null) { if (!iso) return "—"; try { const s = (Date.now() - new Date(iso).getTime()) / 1000; if (s < 3600) return `${Math.floor(s / 60)} mnt lalu`; if (s < 86400) return `${Math.floor(s / 3600)} jam lalu`; return `${Math.floor(s / 86400)} hr lalu`; } catch { return "—"; } }
function prettyNiche(k: string | null) { return (k || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }

type Overview = { videos: number; total_views: number; total_likes: number; total_comments: number; total_followers: number; avg_retention: number | null; avg_engagement: number | null; videos_30d: number; views_30d: number; retention_videos: number };
type NicheRow = { niche: string; videos: number; views: number; avg_retention: number | null; avg_engagement: number | null };
type TopVid = { video_id: string; title: string | null; niche: string | null; views: number; retention: number | null; engagement: number | null; published_at: string | null };
type Hook = { hook: string; views: number; avg_view_pct: number; pattern?: string; subscriber_gain?: number };
type Topic = { title: string; niche: string; views: number; avg_view_pct: number };
type Learn = { top_hooks: Hook[] | null; top_topics: Topic[] | null; avoid_patterns: unknown[] | null; performance_grade: string | null; computed_at: string | null };

function ViewsChart({ pts, labels }: { pts: number[]; labels: string[] }) {
  const W = 680, H = 220, pad = 30, max = Math.max(1, ...pts);
  const x = (i: number) => pad + i * (W - pad * 2) / Math.max(1, pts.length - 1);
  const y = (v: number) => H - 26 - (v / max) * (H - 48);
  const line = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(0)} ${y(v).toFixed(0)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }}>
      <defs><linearGradient id="an-ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6366F1" stopOpacity={0.25} /><stop offset="1" stopColor="#6366F1" stopOpacity={0} /></linearGradient></defs>
      {[0, 0.5, 1].map((f) => { const v = max * f; return (<g key={f}><line x1={pad} y1={y(v)} x2={W - pad} y2={y(v)} stroke="var(--grid-line)" /><text x={4} y={y(v) - 3} fontSize={9} fill="var(--text-muted)" fontFamily="JetBrains Mono">{fmtK(Math.round(v))}</text></g>); })}
      {pts.length > 1 && <><path d={`${line} L${x(pts.length - 1)} ${H - 26} L${pad} ${H - 26} Z`} fill="url(#an-ag)" /><path d={line} fill="none" stroke="#6366F1" strokeWidth={2} /></>}
      {pts.map((v, i) => (<circle key={i} cx={x(i)} cy={y(v)} r={2.5} fill="#6366F1" />))}
      {labels.map((l, i) => (i % Math.ceil(labels.length / 6 || 1) === 0 ? <text key={i} x={x(i)} y={H - 8} fontSize={9} fill="var(--text-muted)" textAnchor="middle" fontFamily="JetBrains Mono">{l.slice(2)}</text> : null))}
    </svg>
  );
}

export default function AnalyticsPage() {
  const [supabase] = useState(() => createClient());
  const [ov, setOv] = useState<Overview | null>(null);
  const [niches, setNiches] = useState<NicheRow[]>([]);
  const [monthly, setMonthly] = useState<{ month: string; views: number; videos: number }[]>([]);
  const [top, setTop] = useState<TopVid[]>([]);
  const [learn, setLearn] = useState<Learn | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<"views" | "retention" | "engagement">("views");

  useEffect(() => {
    (async () => {
      const [o, n, m, t, l] = await Promise.all([
        supabase.rpc("get_tenant_analytics_overview"),
        supabase.rpc("get_tenant_analytics_by_niche"),
        supabase.rpc("get_tenant_analytics_monthly"),
        supabase.rpc("get_tenant_top_videos"),
        supabase.rpc("get_tenant_learning"),
      ]);
      const orow = (Array.isArray(o.data) ? o.data[0] : o.data) as Overview | null;
      setOv(orow);
      setNiches((n.data as NicheRow[]) ?? []);
      setMonthly((m.data as { month: string; views: number; videos: number }[]) ?? []);
      setTop((t.data as TopVid[]) ?? []);
      setLearn((Array.isArray(l.data) ? l.data[0] : l.data) as Learn | null);
      setLoading(false);
    })();
  }, [supabase]);

  const KPI = ov ? [
    { Icon: Users, l: ["Followers", "Followers"], v: fmtK(ov.total_followers), sub: "YouTube" },
    { Icon: Eye, l: ["Total Views", "Total Views"], v: fmtK(ov.total_views), sub: "video MesinViral · semua channel" },
    { Icon: Percent, l: ["Avg Retensi", "Avg Retention"], v: pct(ov.avg_retention), sub: `${ov.retention_videos} video ber-data` },
    { Icon: TrendingUp, l: ["Avg Engagement", "Avg Engagement"], v: pct(ov.avg_engagement), sub: "like+komentar / views" },
    { Icon: Film, l: ["Video terbit", "Published videos"], v: fmtK(ov.videos), sub: "semua channel" },
    { Icon: MessageSquare, l: ["Komentar", "Comments"], v: fmtK(ov.total_comments), sub: `${fmtK(ov.total_likes)} likes` },
  ] : [];

  const nicheMaxV = Math.max(1, ...niches.map((n) => n.views));
  const topSorted = [...top].sort((a, b) => {
    const av = (a[sortKey] ?? -1) as number, bv = (b[sortKey] ?? -1) as number; return bv - av;
  }).slice(0, 12);
  const SortTh = ({ k, label }: { k: typeof sortKey; label: string }) => (
    <th className="num" style={{ cursor: "pointer", color: sortKey === k ? "var(--brand)" : undefined }} onClick={() => setSortKey(k)}>
      {label}{sortKey === k && <ChevronDown size={11} style={{ verticalAlign: -1, marginLeft: 2 }} />}
    </th>
  );
  const grade = learn?.performance_grade;
  // dedupe: top_hooks/top_topics dari analyzer bisa berisi duplikat teks sama → tampilkan unik (views tertinggi sudah di urutan awal).
  const uniqHooks = learn?.top_hooks ? Array.from(new Map(learn.top_hooks.filter((h) => h?.hook).map((h) => [h.hook, h])).values()) : [];
  const uniqTopics = learn?.top_topics ? Array.from(new Map(learn.top_topics.filter((t) => t?.title).map((t) => [t.title, t])).values()) : [];

  if (loading) return <div className="muted" style={{ padding: "3rem", textAlign: "center" }}><Bi id="Memuat analitik…" en="Loading analytics…" /></div>;

  if (!ov || ov.videos === 0) return (
    <>
      <PageHeader helpSlug="analytics" icon={BarChart3} title="Analytics" subtitle={<Bi id="Performa channel dari data nyata" en="Real channel performance" />} />
      <div className="card card-pad" style={{ textAlign: "center", padding: "3rem 1.5rem" }}>
        <BarChart3 size={32} style={{ color: "var(--text-muted)", marginBottom: "0.75rem" }} />
        <p className="muted"><Bi id="Belum ada data analitik. Muncul 24-72 jam setelah video pertama tayang." en="No analytics yet. Appears 24-72h after your first video goes live." /></p>
      </div>
    </>
  );

  return (
    <>
      <PageHeader helpSlug="analytics" icon={BarChart3} title="Analytics"
        subtitle={<><Bi id="Performa channel dari data nyata" en="Real channel performance" /> · <Bi id="diperbarui" en="updated" /> {ago(learn?.computed_at ?? null)}</>}
        action={grade ? <span className="badge" style={{ background: "var(--success-soft)", color: "var(--success)", textTransform: "capitalize" }}><Flame size={13} style={{ verticalAlign: -2 }} /> {grade}</span> : undefined} />

      <div className="an-kpi-strip">
        {KPI.map((k, i) => (
          <div className="an-kpic" key={i}>
            <div className="l"><k.Icon size={13} /> <Bi id={k.l[0]} en={k.l[1]} /></div>
            <div className="v">{k.v}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 2 }}>{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="an-grid">
        <div className="card">
          <div className="card-head"><h3 className="card-title"><Activity size={16} /> <Bi id="Views per bulan terbit" en="Views by publish month" /></h3></div>
          <div className="card-body">{monthly.length > 1 ? <ViewsChart pts={monthly.map((x) => x.views)} labels={monthly.map((x) => x.month)} /> : <div className="muted" style={{ padding: "2rem", textAlign: "center", fontSize: "var(--text-sm)" }}><Bi id="Belum cukup rentang waktu." en="Not enough time range yet." /></div>}</div>
        </div>
        <div className="card">
          <div className="card-head"><h3 className="card-title"><Target size={16} /> <Bi id="Performa per-niche" en="Performance by niche" /></h3></div>
          <div style={{ overflowX: "auto" }}><table className="tbl">
            <thead><tr><th><Bi id="Niche" en="Niche" /></th><th className="num"><Bi id="Video" en="Videos" /></th><th className="num">Views</th><th className="num"><Bi id="Retensi" en="Retention" /></th><th className="num">Engage</th></tr></thead>
            <tbody>
              {niches.map((n) => (
                <tr key={n.niche}>
                  <td><div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{prettyNiche(n.niche)}</div>
                    <div className="an-bar-track" style={{ marginTop: 4 }}><span style={{ width: `${Math.round((n.views / nicheMaxV) * 100)}%`, background: "#6366F1" }} /></div></td>
                  <td className="num muted">{n.videos}</td>
                  <td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{fmtK(n.views)}</b></td>
                  <td className="num muted">{pct(n.avg_retention)}</td>
                  <td className="num muted">{pct(n.avg_engagement)}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      </div>

      <div className="an-grid-3" style={{ marginTop: "1rem" }}>
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Zap size={16} /> <Bi id="Hook teratas" en="Top hooks" /></h3>
          {uniqHooks.length ? uniqHooks.slice(0, 5).map((h, i) => (
            <div key={i} style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{h.hook}</div>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 3, display: "flex", gap: "0.75rem" }}>
                {h.pattern && <span className="badge badge-outline" style={{ fontSize: "0.5625rem" }}>{h.pattern}</span>}
                <span>{fmtK(h.views)} views</span><span>{h.avg_view_pct}% retensi</span>
              </div>
            </div>
          )) : <div className="muted" style={{ fontSize: "var(--text-sm)" }}>—</div>}
        </div>
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Sparkles size={16} /> <Bi id="Topik teratas" en="Top topics" /></h3>
          {uniqTopics.length ? uniqTopics.slice(0, 5).map((t, i) => (
            <div key={i} style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{t.title}</div>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 3, display: "flex", gap: "0.75rem" }}>
                <span>{prettyNiche(t.niche)}</span><span>{fmtK(t.views)} views</span><span>{t.avg_view_pct}% retensi</span>
              </div>
            </div>
          )) : <div className="muted" style={{ fontSize: "var(--text-sm)" }}>—</div>}
        </div>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <div className="card-head">
          <h3 className="card-title"><TrendingUp size={16} /> <Bi id="Video teratas" en="Top videos" /></h3>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="klik kolom untuk urutkan" en="click column to sort" /></span>
        </div>
        <div style={{ overflowX: "auto" }}><table className="tbl">
          <thead><tr><th>Video</th><th><Bi id="Niche" en="Niche" /></th><SortTh k="views" label="Views" /><SortTh k="retention" label="Retensi" /><SortTh k="engagement" label="Engage" /></tr></thead>
          <tbody>
            {topSorted.map((r) => (
              <tr key={r.video_id}>
                <td style={{ color: "var(--text-primary)", maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  <a href={`https://youtu.be/${r.video_id}`} target="_blank" rel="noopener noreferrer" style={{ color: "inherit", textDecoration: "none" }}>{r.title || r.video_id}</a>
                </td>
                <td className="muted">{prettyNiche(r.niche)}</td>
                <td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{fmtK(r.views)}</b></td>
                <td className="num muted">{pct(r.retention)}</td>
                <td className="num muted">{pct(r.engagement)}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>

      {Array.isArray(learn?.avoid_patterns) && (learn!.avoid_patterns!.length > 0) && (
        <div className="card card-pad" style={{ marginTop: "1rem" }}>
          <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Bi id="Pola yang dihindari mesin" en="Patterns the engine avoids" /></h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {learn!.avoid_patterns!.slice(0, 12).map((p, i) => (<span key={i} className="badge badge-outline" style={{ fontSize: "var(--text-xs)" }}>{typeof p === "string" ? p : JSON.stringify(p)}</span>))}
          </div>
        </div>
      )}

      <div className="card card-pad" style={{ marginTop: "1rem", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
        <div><h3 className="card-title"><Sparkles size={16} /> <Bi id="Adaptasi otomatis" en="Auto-adaptation" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginTop: "0.5rem" }}><Bi id="Mesin memakai sinyal ini untuk memilih niche, hook, & topik berikutnya secara otomatis." en="The engine uses these signals to auto-pick your next niche, hook & topic." /></p></div>
        <Link href="/insights" className="btn btn-secondary btn-sm" style={{ flex: "none" }}><Bi id="Buka Wawasan" en="Open Insights" /> <ArrowRight size={14} /></Link>
      </div>
    </>
  );
}
