"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Zap, Play, CheckCircle, Eye, Users, Calendar, ArrowRight, List, Gauge as GaugeIcon, DollarSign, Sparkles, Activity, Check, Loader2, X, ChevronRight, ExternalLink } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./dashboard.css";

// D1 Main Dashboard — Phase 9.3 (wired Supabase v2, anon + RLS). REAL: Recent Runs, Success Rate,
// Video-hari-ini, activity feed (production_runs); Compliance (channel_insights.compliance bila ada).
// Placeholder JUJUR (belum ada sumber): Views/Subs/Cost/Self-learning ("—"); Schedule = empty-state.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type RunSt = "completed" | "running" | "failed" | "queued";
function statusKey(s: string | null): RunSt {
  const v = (s || "").toLowerCase();
  if (v.includes("complete") || v === "published" || v === "success") return "completed";
  if (v.includes("fail") || v.includes("error")) return "failed";
  if (v.includes("run") || v.includes("produc") || v.includes("publish")) return "running";
  return "queued";
}
function fmtDur(secs: string | null) { const n = parseFloat(secs || ""); if (!isFinite(n) || n <= 0) return "—"; return n >= 60 ? `${Math.floor(n / 60)}m ${Math.round(n % 60)}s` : `${Math.round(n)}s`; }
function prettyNiche(k: string | null) { return (k || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }
function ago(iso: string) {
  try { const s = (Date.now() - new Date(iso).getTime()) / 1000; if (s < 60) return "baru saja"; if (s < 3600) return `${Math.floor(s / 60)} mnt`; if (s < 86400) return `${Math.floor(s / 3600)} jam`; return `${Math.floor(s / 86400)} hr`; } catch { return ""; }
}
const ST_MAP: Record<RunSt, { Icon: typeof Check; c: string; bg: string }> = {
  completed: { Icon: Check, c: "var(--success)", bg: "var(--success-soft)" },
  running: { Icon: Loader2, c: "var(--info)", bg: "var(--info-soft)" },
  failed: { Icon: X, c: "var(--error)", bg: "var(--error-soft)" },
  queued: { Icon: Loader2, c: "var(--text-muted)", bg: "var(--surface-2)" },
};

type RunRow = { id: string; topic: string | null; niche: string | null; status: string | null; elapsed_seconds: string | null; youtube_url: string | null; created_at: string };

function Gauge({ score }: { score: number }) {
  const r = 48, c = 2 * Math.PI * r, off = c * (1 - score / 100);
  const col = score >= 80 ? "#10B981" : score >= 60 ? "#F59E0B" : "#EF4444";
  return (
    <svg viewBox="0 0 120 120" width={116} height={116}>
      <circle cx={60} cy={60} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={9} />
      <circle cx={60} cy={60} r={r} fill="none" stroke={col} strokeWidth={9} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 60 60)" />
      <text x={60} y={64} textAnchor="middle" fontSize={28} fontWeight={700} fill="var(--text-primary)" fontFamily="Geist">{score}</text>
    </svg>
  );
}

function isToday(iso: string) { try { const d = new Date(iso), n = new Date(); return d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth() && d.getDate() === n.getDate(); } catch { return false; } }

export default function DashboardPage() {
  const [supabase] = useState(() => createClient());
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [handle, setHandle] = useState("");
  const [cap, setCap] = useState<number | null>(null);
  const [compliance, setCompliance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const [{ data: r }, { data: tc }, { data: ci }] = await Promise.all([
      supabase.from("production_runs").select("id,topic,niche,status,elapsed_seconds,youtube_url,created_at").order("created_at", { ascending: false }).limit(50),
      supabase.from("tenant_configs").select("display_handle,plan_type").maybeSingle(),
      supabase.from("channel_insights").select("compliance,computed_at").order("computed_at", { ascending: false }).limit(1),
    ]);
    setRuns((r as RunRow[]) ?? []);
    const t = tc as { display_handle?: string; plan_type?: string } | null;
    setHandle(t?.display_handle || "");
    if (t?.plan_type) { const { data: pl } = await supabase.from("plan_limits").select("max_videos_per_day").eq("plan_type", t.plan_type).maybeSingle(); setCap((pl as { max_videos_per_day?: number } | null)?.max_videos_per_day ?? null); }
    const comp = (ci as { compliance?: { score?: number } }[] | null)?.[0]?.compliance;
    if (comp && typeof comp.score === "number") setCompliance(comp.score);
    setLoading(false);
  }, [supabase]);

  useEffect(() => { load(); }, [load]);

  const recent = runs.slice(0, 5);
  const todayCount = runs.filter((r) => isToday(r.created_at) && statusKey(r.status) === "completed").length;
  const done = runs.filter((r) => statusKey(r.status) === "completed").length;
  const fail = runs.filter((r) => statusKey(r.status) === "failed").length;
  const successRate = done + fail > 0 ? Math.round((done / (done + fail)) * 100) : null;
  const today = new Date().toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <>
      <div className="greet">
        <div>
          <h1><Bi id={`Halo${handle ? ", " + handle : ""}`} en={`Hello${handle ? ", " + handle : ""}`} /></h1>
          <div className="sub"><span>{today}</span></div>
        </div>
        <a href="/channels" className="btn btn-secondary btn-lg"><Zap size={18} /> <Bi id="Kelola Kanal" en="Manage channels" /></a>
      </div>

      <div className="kpi-row">
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Play size={14} /> <Bi id="Video Hari Ini" en="Videos Today" /></span></div>
          <span className="kpi-value">{todayCount}{cap != null && <span className="muted" style={{ fontSize: "var(--text-xl)", fontWeight: 500 }}>/{cap}</span>}</span>
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><CheckCircle size={14} /> Success Rate</span></div>
          <span className="kpi-value">{successRate != null ? `${successRate}%` : "—"}</span>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{done}✓ · {fail}✗ ({runs.length} run)</span>
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Eye size={14} /> <Bi id="Total Views" en="Total Views" /></span></div>
          <span className="kpi-value">—</span>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="sumber analytics (9.4)" en="analytics source (9.4)" /></span>
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Users size={14} /> <Bi id="Subs" en="Subs" /></span></div>
          <span className="kpi-value">—</span>
        </div>
      </div>

      <div className="grid2">
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card">
            <div className="card-head">
              <h3 className="card-title"><Calendar size={16} /> <Bi id="Jadwal Hari Ini" en="Today's Schedule" /></h3>
              <Link href="/schedule" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat jadwal →" en="View schedule →" /></Link>
            </div>
            <div className="card-body" style={{ padding: "1.5rem", textAlign: "center" }}>
              <span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Belum ada jadwal aktif. Atur di layar Jadwal." en="No active schedule yet. Set one in Schedule." /></span>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <h3 className="card-title"><List size={16} /> <Bi id="Run Terbaru" en="Recent Runs" /></h3>
              <Link href="/runs" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat semua →" en="View all →" /></Link>
            </div>
            <div className="card-body" style={{ padding: "0.5rem 0.75rem" }}>
              {loading ? <div className="muted" style={{ padding: "1rem" }}><Bi id="Memuat…" en="Loading…" /></div>
                : recent.length === 0 ? <div className="muted" style={{ padding: "1rem" }}><Bi id="Belum ada run." en="No runs yet." /></div>
                : recent.map((r) => {
                  const st = statusKey(r.status); const m = ST_MAP[st];
                  return (
                    <Link key={r.id} href={`/runs/${r.id}`} className={`run-item${st === "failed" ? " failed" : ""}`}>
                      <span className="rstat" style={{ background: m.bg, color: m.c }}><m.Icon size={12} /></span>
                      <div style={{ minWidth: 0 }}>
                        <div className="rtopic">{r.topic || "(tanpa topik)"}</div>
                        <div className="rmeta"><span>{prettyNiche(r.niche)}</span><span>{fmtDur(r.elapsed_seconds)}</span></div>
                      </div>
                      <div className="rright">{r.youtube_url ? <ExternalLink size={13} /> : <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{ago(r.created_at)}</span>}<ChevronRight size={14} /></div>
                    </Link>
                  );
                })}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card">
            <div className="card-head"><h3 className="card-title"><GaugeIcon size={16} /> <Bi id="Skor Compliance" en="Compliance Score" /></h3></div>
            <div className="card-body compliance-wrap">
              {compliance != null
                ? <Gauge score={compliance} />
                : <div className="muted" style={{ padding: "1.5rem 0", textAlign: "center", fontSize: "var(--text-sm)" }}><Bi id="Belum cukup data — skor muncul setelah cukup video diproduksi." en="Not enough data — score appears after enough videos are produced." /></div>}
            </div>
            <div className="card-foot"><Link href="/compliance" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Detail compliance →" en="Compliance detail →" /></Link></div>
          </div>

          <div className="card card-pad">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 className="card-title"><DollarSign size={16} /> <Bi id="Biaya AI" en="AI Cost" /></h3>
              <span className="badge badge-outline">BYOK</span>
            </div>
            <p className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.75rem" }}><Bi id="Rincian biaya BYOK tampil setelah worker mencatat metadata produksi." en="BYOK cost breakdown appears once the worker records production metadata." /></p>
          </div>

          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Sparkles size={16} /> <Bi id="Self-Learning" en="Self-Learning" /></h3>
            <p className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Insight adaptasi muncul setelah analytics terkumpul (24-72j pasca-publish)." en="Adaptation insights appear once analytics accumulate (24-72h post-publish)." /></p>
            <div style={{ marginTop: "0.5rem" }}><Link href="/insights" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat insights →" en="View insights →" /></Link></div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <div className="card-head"><h3 className="card-title"><Activity size={16} /> <Bi id="Aktivitas Terbaru" en="Recent Activity" /></h3></div>
        <div className="card-body" style={{ padding: "0.5rem 1.25rem" }}>
          <div className="feed">
            {recent.length === 0 ? <div className="muted" style={{ padding: "0.75rem 0", fontSize: "var(--text-xs)" }}><Bi id="Belum ada aktivitas." en="No activity yet." /></div>
              : recent.map((r) => {
                const st = statusKey(r.status); const m = ST_MAP[st];
                return (
                  <div className="feed-item" key={r.id}>
                    <span className="fdot" style={{ background: m.c }} />
                    <span>Run #{r.id} · {st === "completed" ? "selesai" : st === "failed" ? "gagal" : st} · {prettyNiche(r.niche)}</span>
                    <span className="ftime">{ago(r.created_at)}</span>
                  </div>
                );
              })}
          </div>
        </div>
      </div>
    </>
  );
}
