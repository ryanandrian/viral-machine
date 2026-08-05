"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Zap, CheckCircle, Eye, ThumbsUp, Users, Calendar, List, Gauge as GaugeIcon, DollarSign, Sparkles, Activity, Check, Loader2, X, ChevronRight, ExternalLink, AlertTriangle, ArrowRight } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { effectiveStatus, ChannelStatusBadge, type Eff } from "@/lib/channel-status";
import { LearningDeltaChip } from "@/components/learning-curve-card";
import "./dashboard.css";

// D1 Main Dashboard — Phase 9.3 (wired Supabase v2, anon + RLS). DATA NYATA:
//  • Success Rate + breakdown all-time (production_runs).
//  • Total Views/Likes/Followers YouTube tenant-wide → RPC get_tenant_youtube_totals (snapshot terbaru/video; followers = channels.subscriber_count).
//  • Jadwal Hari Ini = channels.publish_slots (zona tenant). Compliance = channel_insights.compliance.
//  • Auto-refresh SMOOTH: realtime production_runs (debounce) + re-fetch saat tab aktif (tanpa spinner).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type RunSt = "completed" | "running" | "failed" | "review" | "queued";
function statusKey(s: string | null): RunSt {
  const v = (s || "").toLowerCase();
  if (v.includes("complete") || v === "published" || v === "success") return "completed";
  if (v === "qc_failed" || v.includes("ready_with_issues") || v.includes("review")) return "review";
  if (v.includes("fail") || v.includes("error")) return "failed";
  if (v.includes("run") || v.includes("produc") || v.includes("publish")) return "running";
  return "queued";
}
function fmtDur(secs: string | null) { const n = parseFloat(secs || ""); if (!isFinite(n) || n <= 0) return "—"; return n >= 60 ? `${Math.floor(n / 60)}m ${Math.round(n % 60)}s` : `${Math.round(n)}s`; }
function fmtN(n: number) { return n.toLocaleString("id-ID"); }
function prettyNiche(k: string | null) { return (k || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }
function ago(iso: string) {
  try { const s = (Date.now() - new Date(iso).getTime()) / 1000; if (s < 60) return "baru saja"; if (s < 3600) return `${Math.floor(s / 60)} mnt`; if (s < 86400) return `${Math.floor(s / 3600)} jam`; return `${Math.floor(s / 86400)} hr`; } catch { return ""; }
}
const ST_MAP: Record<RunSt, { Icon: typeof Check; c: string; bg: string }> = {
  completed: { Icon: Check, c: "var(--success)", bg: "var(--success-soft)" },
  running: { Icon: Loader2, c: "var(--info)", bg: "var(--info-soft)" },
  failed: { Icon: X, c: "var(--error)", bg: "var(--error-soft)" },
  review: { Icon: Loader2, c: "var(--warning, #F59E0B)", bg: "var(--warning-soft, rgba(245,158,11,.12))" },
  queued: { Icon: Loader2, c: "var(--text-muted)", bg: "var(--surface-2)" },
};

type RunRow = { id: string; topic: string | null; niche: string | null; status: string | null; elapsed_seconds: string | null; youtube_url: string | null; created_at: string };
type Stats = { made: number; success: number; failed: number; review: number };
type Yt = { views: number; likes: number; followers: number };
type Slot = { name: string; times: string[] };

function Gauge({ score }: { score: number }) {
  const r = 48, c = 2 * Math.PI * r, off = c * (1 - score / 100);
  const col = score >= 80 ? "#10B981" : score >= 60 ? "#F59E0B" : "#EF4444";
  return (
    <svg viewBox="0 0 120 120" width={116} height={116}>
      <circle cx={60} cy={60} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={9} />
      <circle cx={60} cy={60} r={r} fill="none" stroke={col} strokeWidth={9} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 60 60)" />
      <text x={60} y={64} textAnchor="middle" fontSize={26} fontWeight={700} fill="var(--text-primary)" fontFamily="Geist">{score}</text>
    </svg>
  );
}

export default function DashboardPage() {
  const [supabase] = useState(() => createClient());
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [handle, setHandle] = useState("");
  const [tz, setTz] = useState("Asia/Jakarta");
  const [compliance, setCompliance] = useState<number | null>(null);
  const [insights, setInsights] = useState<{ videosAnalyzed: number; lastLearned: string | null; topNiche: string | null; channels: number } | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [yt, setYt] = useState<Yt | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  // D1-F2 (mandat owner 2026-07-11): kartu kondisional channel perlu-perhatian (incomplete/halted) —
  // reuse effectiveStatus + RPC channel_readiness (sumber SAMA dgn /channels, anti-drift). Hilang saat semua sehat.
  const [attn, setAttn] = useState<{ id: string; name: string; eff: Eff }[]>([]);
  const [noChannel, setNoChannel] = useState(false);
  const [loading, setLoading] = useState(true);
  // B2 BYOK cost-tracking: total biaya AI 30 hari (Σ run_metadata.cost.usd × kurs app_config) — REAL.
  const [aiCost, setAiCost] = useState<{ idr: number; usd: number; videos: number; rate: number } | null>(null);

  const load = useCallback(async () => {
    const since30 = new Date(Date.now() - 30 * 864e5).toISOString();
    const [
      { data: r }, { data: tc }, ins, totals, { data: chs },
      made, success, failed, review, { data: costRows }, { data: rateRow },
    ] = await Promise.all([
      supabase.from("production_runs").select("id,topic,niche,status,elapsed_seconds,youtube_url,created_at").order("created_at", { ascending: false }).limit(50),
      supabase.from("tenant_configs").select("display_handle,timezone,subscription_status").maybeSingle(),
      supabase.rpc("get_tenant_insights_summary"),
      supabase.rpc("get_tenant_youtube_totals"),
      supabase.from("channels").select("id,channel_name,publish_slots,is_active,production_paused,production_paused_reason"),
      supabase.from("production_runs").select("id", { count: "exact", head: true }),
      supabase.from("production_runs").select("id", { count: "exact", head: true }).in("status", ["success", "completed", "published"]),
      supabase.from("production_runs").select("id", { count: "exact", head: true }).in("status", ["failed", "error"]),
      supabase.from("production_runs").select("id", { count: "exact", head: true }).in("status", ["qc_failed", "ready_with_issues"]),
      supabase.from("production_runs").select("run_metadata").gte("created_at", since30).order("created_at", { ascending: true }).order("run_id", { ascending: true }).range(0, 999),
      supabase.from("app_config").select("value").eq("key", "usd_idr_rate").maybeSingle(),
    ]);
    setRuns((r as RunRow[]) ?? []);
    const t = tc as { display_handle?: string; timezone?: string; subscription_status?: string } | null;
    setHandle(t?.display_handle || "");
    if (t?.timezone) setTz(t.timezone);
    const insRow = (Array.isArray(ins.data) ? ins.data[0] : ins.data) as { channels_count?: number; compliance_avg?: number; videos_analyzed?: number; last_learned?: string; top_niche?: string } | null;
    setCompliance(insRow && insRow.compliance_avg != null ? Number(insRow.compliance_avg) : null);
    setInsights(insRow && (insRow.channels_count ?? 0) > 0
      ? { videosAnalyzed: Number(insRow.videos_analyzed) || 0, lastLearned: insRow.last_learned || null, topNiche: insRow.top_niche || null, channels: Number(insRow.channels_count) || 0 }
      : null);
    const tot = (Array.isArray(totals.data) ? totals.data[0] : totals.data) as { total_views?: number; total_likes?: number; total_followers?: number } | null;
    if (tot) setYt({ views: Number(tot.total_views) || 0, likes: Number(tot.total_likes) || 0, followers: Number(tot.total_followers) || 0 });
    setStats({ made: made.count ?? 0, success: success.count ?? 0, failed: failed.count ?? 0, review: review.count ?? 0 });
    const channels = (chs as { id: string; channel_name: string; publish_slots: string[] | null; is_active: boolean; production_paused: boolean | null; production_paused_reason: string | null }[] | null) ?? [];
    setSlots(channels.filter((c) => c.is_active && c.publish_slots && c.publish_slots.length)
      .map((c) => ({ name: c.channel_name, times: [...(c.publish_slots || [])].sort() })));
    // D1-F2: deteksi channel perlu-perhatian — readiness HANYA utk kandidat (hemat; halted tak butuh RPC).
    setNoChannel(channels.length === 0);
    const cand = channels.filter((c) => c.production_paused || !c.is_active);
    const rd: Record<string, { ready: boolean; missing: string[] } | null> = {};
    await Promise.all(cand.filter((c) => !c.production_paused).map(async (c) => {
      try { const { data } = await supabase.rpc("channel_readiness", { p_channel_id: c.id }); rd[c.id] = (data as { ready: boolean; missing: string[] }) ?? null; } catch { rd[c.id] = null; }
    }));
    setAttn(cand
      .map((c) => ({ id: c.id, name: c.channel_name || "Channel", eff: effectiveStatus(c, t?.subscription_status ?? null, rd[c.id] ?? null) }))
      .filter((x) => x.eff.key === "incomplete" || x.eff.key === "halted"));
    // Biaya AI 30 hari: hanya run yg PUNYA cost (produksi pasca-fitur); label jujur di kartu.
    // Paginasi (urutan stabil created_at+run_id; cap 8 hal = 8k run/30hr, cukup 10ch×24vid; audit 2026-07-11).
    type CostRow = { run_metadata?: { cost?: { usd?: number } } };
    let allCost = (costRows as CostRow[] | null) ?? [];
    for (let cp = 1; allCost.length === cp * 1000 && cp < 8; cp++) {
      const { data: more } = await supabase.from("production_runs").select("run_metadata").gte("created_at", since30)
        .order("created_at", { ascending: true }).order("run_id", { ascending: true }).range(cp * 1000, cp * 1000 + 999);
      allCost = allCost.concat((more as CostRow[] | null) ?? []);
      if (!more || (more as CostRow[]).length < 1000) break;
    }
    const rate = Number((rateRow as { value?: number } | null)?.value) || 16500;
    let usd = 0, nCost = 0;
    allCost.forEach((row) => {
      const u = row.run_metadata?.cost?.usd;
      if (typeof u === "number" && u > 0) { usd += u; nCost += 1; }
    });
    setAiCost(nCost > 0 ? { idr: usd * rate, usd, videos: nCost, rate } : null);
    setLoading(false);
  }, [supabase]);

  // Mount + auto-refresh SMOOTH (realtime production_runs debounced + re-fetch saat tab aktif).
  const debRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    load();
    const reload = () => { if (debRef.current) clearTimeout(debRef.current); debRef.current = setTimeout(() => load(), 400); };
    const ch = supabase.channel("rt-dashboard")
      .on("postgres_changes", { event: "*", schema: "public", table: "production_runs" }, reload)
      // Kartu status F2 + Jadwal Hari Ini ikut segar SEKETIKA saat channel berubah (pola terbukti rt-channels; fix pelanggaran world-class 2026-07-11)
      .on("postgres_changes", { event: "*", schema: "public", table: "channels" }, reload)
      .subscribe();
    const onVis = () => { if (document.visibilityState === "visible") load(); };
    document.addEventListener("visibilitychange", onVis);
    return () => { if (debRef.current) clearTimeout(debRef.current); supabase.removeChannel(ch); document.removeEventListener("visibilitychange", onVis); };
  }, [load, supabase]);

  const recent = runs.slice(0, 5);
  const rate = stats && stats.success + stats.failed > 0 ? Math.round((stats.success / (stats.success + stats.failed)) * 100) : null;
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

      {/* D1-F2: kartu kondisional — muncul HANYA saat ada channel belum-siap/dihentikan; hilang permanen saat sehat */}
      {!loading && noChannel && (
        <div className="card" style={{ marginBottom: "1rem", border: "1px solid color-mix(in srgb,var(--warning) 45%,transparent)" }}>
          <div className="card-body" style={{ padding: "0.875rem 1.25rem", display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <AlertTriangle size={18} style={{ color: "var(--warning)", flexShrink: 0 }} />
            <span style={{ fontSize: "var(--text-sm)", flex: 1, minWidth: 200 }}><Bi id="Channel pertama Anda belum selesai disiapkan — mesin belum bisa produksi." en="Your first channel isn't set up yet — the engine can't produce." /></span>
            <Link href="/onboarding" className="btn btn-default btn-sm"><Bi id="Lanjutkan setup" en="Continue setup" /> <ArrowRight size={14} /></Link>
          </div>
        </div>
      )}
      {!loading && attn.length > 0 && (
        <div className="card" style={{ marginBottom: "1rem", border: "1px solid color-mix(in srgb,var(--warning) 45%,transparent)" }}>
          <div className="card-head"><h3 className="card-title"><AlertTriangle size={16} style={{ color: "var(--warning)" }} /> <Bi id="Channel perlu perhatian" en="Channels need attention" /></h3></div>
          <div className="card-body" style={{ padding: "0.25rem 1.25rem 0.75rem" }}>
            {attn.map((a) => (
              <div key={a.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.5rem 0", borderBottom: "1px solid var(--border-subtle)", flexWrap: "wrap" }}>
                <span style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{a.name}</span>
                <ChannelStatusBadge eff={a.eff} />
                <span className="muted" style={{ fontSize: "var(--text-xs)", flex: 1, minWidth: 180 }}>
                  {a.eff.reason || (a.eff.key === "halted"
                    ? <Bi id="Dihentikan otomatis oleh sistem — buka channel untuk memulihkan." en="Automatically halted — open the channel to recover." />
                    : <Bi id="Konfigurasi/kredensial belum lengkap." en="Config/credentials incomplete." />)}
                </span>
                <Link href={`/channels/${a.id}`} className="btn btn-secondary btn-sm">
                  {a.eff.key === "halted" ? <Bi id="Pulihkan" en="Recover" /> : <Bi id="Lengkapi" en="Complete" />} <ChevronRight size={14} />
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="kpi-row">
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><CheckCircle size={14} /> Success Rate</span></div>
          <span className="kpi-value">{rate != null ? `${rate}%` : "—"}</span>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
            {/* Rincian BUKU-BESAR: dibuat = sukses + gagal + ber-catatan. Keempatnya WAJIB dari
                `production_runs` — jangan pernah mengambil salah satunya dari antrean `/review`
                (tabel lain, isi lain) atau jumlahnya tak lagi cocok. Label "perlu ditinjau" dicabut
                05-Agu: nama itu milik ANTREAN yang menunggu keputusan, bukan buku-besar riwayat. */}
            {stats ? <>{fmtN(stats.made)} <Bi id="dibuat" en="made" /> · {fmtN(stats.success)} <Bi id="sukses" en="succeeded" /> · {fmtN(stats.failed)} <Bi id="gagal" en="failed" />{stats.review > 0 ? <> · {fmtN(stats.review)} <Bi id="ada catatan QC" en="with QC note" /></> : null}</> : "—"}
          </span>
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Eye size={14} /> <Bi id="Total Views YouTube" en="Total YouTube Views" /></span></div>
          <span className="kpi-value">{yt ? fmtN(yt.views) : "—"}</span>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="seluruh channel" en="all channels" /></span>
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><ThumbsUp size={14} /> <Bi id="Total Likes YouTube" en="Total YouTube Likes" /></span></div>
          <span className="kpi-value">{yt ? fmtN(yt.likes) : "—"}</span>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="seluruh channel" en="all channels" /></span>
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Users size={14} /> <Bi id="Total Followers YouTube" en="Total YouTube Followers" /></span></div>
          <span className="kpi-value">{yt && yt.followers > 0 ? fmtN(yt.followers) : "—"}</span>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{yt && yt.followers > 0 ? <Bi id="seluruh channel" en="all channels" /> : <Bi id="diperbarui ≤24 jam" en="updates ≤24h" />}</span>
        </div>
      </div>

      <div className="grid2">
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card">
            <div className="card-head">
              <h3 className="card-title"><Calendar size={16} /> <Bi id="Jadwal Hari Ini" en="Today's Schedule" /></h3>
              <Link href="/schedule" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat jadwal →" en="View schedule →" /></Link>
            </div>
            <div className="card-body" style={{ padding: slots.length ? "0.5rem 1.25rem 1rem" : "1.5rem", textAlign: slots.length ? "left" : "center" }}>
              {slots.length === 0
                ? <span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Belum ada jadwal aktif. Atur di layar Jadwal." en="No active schedule yet. Set one in Schedule." /></span>
                : <>
                  {slots.map((s) => (
                    <div key={s.name} style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid var(--border-subtle)", gap: "1rem" }}>
                      <span style={{ fontSize: "var(--text-sm)", color: "var(--text-secondary)", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.name}</span>
                      <span style={{ fontSize: "var(--text-sm)", fontWeight: 600, fontFamily: "var(--font-mono)", flex: "none" }}>{s.times.join(" · ")}</span>
                    </div>
                  ))}
                  <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.5rem" }}>Zona {tz}</div>
                </>}
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
              <h3 className="card-title"><DollarSign size={16} /> <Bi id="Biaya AI (30 hari)" en="AI Cost (30 days)" /></h3>
              <span className="badge badge-outline">BYOK</span>
            </div>
            {aiCost ? (<>
              <div style={{ fontSize: "var(--text-2xl)", fontWeight: 700, marginTop: "0.5rem" }}>Rp {Math.round(aiCost.idr).toLocaleString("id-ID")}</div>
              <p className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.25rem" }}>
                <Bi id={`${aiCost.videos} produksi · rata-rata Rp ${Math.round(aiCost.idr / aiCost.videos).toLocaleString("id-ID")}/video — dibayar ke provider via kunci AI-mu (bukan ke kami); konsumsi terukur nyata × harga resmi provider (kurs ${aiCost.rate.toLocaleString("id-ID")}).`}
                    en={`${aiCost.videos} productions · avg Rp ${Math.round(aiCost.idr / aiCost.videos).toLocaleString("id-ID")}/video — paid to providers via your own keys; measured usage × official provider prices.`} />
              </p>
            </>) : (
              <p className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.75rem" }}><Bi id="Belum ada data — biaya nyata per video tercatat otomatis mulai produksi berikutnya." en="No data yet — real per-video cost is recorded automatically from the next production." /></p>
            )}
          </div>

          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Sparkles size={16} /> <Bi id="Self-Learning" en="Self-Learning" /></h3>
            {insights ? (
              <>
                <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "var(--text-lg)" }}>{fmtN(insights.videosAnalyzed)}</div>
                    <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="video dipelajari" en="videos learned" /></div>
                  </div>
                  {insights.topNiche && (
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "var(--text-lg)" }}>{prettyNiche(insights.topNiche)}</div>
                      <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="niche teratas" en="top niche" /></div>
                    </div>
                  )}
                </div>
                <p className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.625rem" }}>
                  {insights.channels > 1 ? `${insights.channels} kanal · ` : ""}<Bi id="terakhir belajar" en="last learned" /> {insights.lastLearned ? ago(insights.lastLearned) : "—"}
                </p>
                {/* [B17-F0] chip delta Kurva Belajar (1 baris; dormant bila data <2 minggu) */}
                <LearningDeltaChip />
                <div style={{ marginTop: "0.5rem" }}><Link href="/insights" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat insights →" en="View insights →" /></Link></div>
              </>
            ) : (
              <>
                <p className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Insight adaptasi muncul setelah analytics terkumpul (24-72j pasca-publish)." en="Adaptation insights appear once analytics accumulate (24-72h post-publish)." /></p>
                <div style={{ marginTop: "0.5rem" }}><Link href="/insights" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat insights →" en="View insights →" /></Link></div>
              </>
            )}
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
                // ReactNode, bukan string: ketiga label ini dulu terkunci bahasa Indonesia meski layar
                // berbahasa Inggris (§3.5 dwibahasa wajib) — diperbaiki bersama pencabutan nama antrean.
                const lbl = st === "completed" ? <Bi id="selesai" en="completed" />
                  : st === "failed" ? <Bi id="gagal" en="failed" />
                  : st === "review" ? <Bi id="ada catatan QC" en="QC note" />
                  : <>{st}</>;
                return (
                  <div className="feed-item" key={r.id}>
                    <span className="fdot" style={{ background: m.c }} />
                    <span>Run #{r.id} · {lbl} · {prettyNiche(r.niche)}</span>
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
