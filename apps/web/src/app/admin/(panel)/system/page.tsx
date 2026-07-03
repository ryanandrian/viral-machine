import { Activity, AlertTriangle, XCircle, Command, Server } from "lucide-react";
import { createAdminClient } from "@/lib/supabase/admin";
import "./system.css";

// E3 System Health (Phase 10.8) — SERVER COMPONENT, data NYATA via service_role (gated (panel)/layout).
// Stok buffer dari content_inventory (arsitektur v2: producer jaga stok, BUKAN queue — pipeline_queue=fosil v1,
// jangan tampilkan); error dari production_runs (24h via filter query + count exact → tahan >1000 baris);
// workers dari worker_heartbeats (kosong di dev=jujur).
export const dynamic = "force-dynamic";

// Status content_inventory yang DIHITUNG producer sbg stok (producer.py plan_and_submit):
// ready + ready_with_issues + producing (rem alami anti-runaway); publishing = sedang diambil publisher.
const STOCK_STATUSES = ["ready", "ready_with_issues", "producing", "publishing"];

function LineChart({ data, color, gid }: { data: number[]; color: string; gid: string }) {
  const W = 480, H = 160, pad = 10, max = Math.max(1, ...data);
  const x = (i: number) => pad + i * (W - pad * 2) / Math.max(1, data.length - 1);
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

function categorize(msg: string | null): string {
  const m = (msg || "").toLowerCase();
  if (/timeout|tts/.test(m)) return "TTS/timeout";
  if (/429|rate.?limit/.test(m)) return "Rate limit (429)";
  if (/render|ffmpeg/.test(m)) return "Render error";
  if (/upload|youtube/.test(m)) return "Upload fail";
  if (/visual|clip|image/.test(m)) return "Visual/gambar";
  if (/topic|topik|niche/.test(m)) return "Topik/niche";
  if (/durasi|duration|qc/.test(m)) return "Durasi/QC";
  return "Lainnya";
}
const FAIL_COLOR: Record<string, string> = { "TTS/timeout": "#ef4444", "Rate limit (429)": "#f59e0b", "Render error": "#6366F1", "Upload fail": "#71717a", "Visual/gambar": "#8b5cf6", "Topik/niche": "#0ea5e9", "Durasi/QC": "#10b981", "Lainnya": "#a1a1aa" };

export default async function AdminSystemPage() {
  const a = createAdminClient();
  const since24h = new Date(Date.now() - 24 * 3.6e6).toISOString();
  const [hb, inv, chRows, runs24, failedRows, runsTotal, runsFailed, runsSuccess, vids, analytics, channels, direct] = await Promise.all([
    a.from("worker_heartbeats").select("*").order("worker_name"),
    a.from("content_inventory").select("channel_id, status").in("status", STOCK_STATUSES),
    a.from("channels").select("id, channel_name, buffer_depth").eq("is_active", true).order("channel_name").limit(24),
    a.from("production_runs").select("created_at, status").gte("created_at", since24h),
    a.from("production_runs").select("error_message").eq("status", "failed").order("created_at", { ascending: false }).limit(500),
    a.from("production_runs").select("id", { count: "exact", head: true }),
    a.from("production_runs").select("id", { count: "exact", head: true }).eq("status", "failed"),
    a.from("production_runs").select("id", { count: "exact", head: true }).eq("status", "success"),
    a.from("videos").select("id", { count: "exact", head: true }),
    a.from("video_analytics").select("id", { count: "exact", head: true }),
    a.from("channels").select("id", { count: "exact", head: true }),
    a.from("direct_jobs").select("status, job_type, created_at").order("created_at", { ascending: false }).limit(50),
  ]);
  const djRows = direct.data ?? [];
  const dj = { pending: djRows.filter((d) => d.status === "pending").length, producing: djRows.filter((d) => d.status === "producing").length, published: djRows.filter((d) => d.status === "published").length, failed: djRows.filter((d) => d.status === "failed").length };

  const now = Date.now();
  const hourly = (rows: { created_at: string }[], pred: (r: never) => boolean = () => true) => {
    const buckets = new Array(24).fill(0);
    (rows ?? []).forEach((r) => {
      if (!pred(r as never)) return;
      const diffH = (now - new Date(r.created_at).getTime()) / 3.6e6;
      if (diffH >= 0 && diffH < 24) buckets[23 - Math.floor(diffH)]++;
    });
    return buckets;
  };
  const run24Rows = runs24.data ?? [];
  const errorSeries = hourly(run24Rows as { created_at: string }[], (r: { status: string }) => r.status === "failed");
  const failed24 = run24Rows.filter((r) => r.status === "failed").length;

  // Stok buffer per channel aktif (angka yang SAMA dgn yang dipakai producer utk defisit).
  const invRows = inv.data ?? [];
  const stockByChannel = invRows.reduce((m: Record<string, Record<string, number>>, r) => {
    (m[r.channel_id] ??= {})[r.status] = (m[r.channel_id][r.status] ?? 0) + 1; return m;
  }, {});
  const activeChannels = chRows.data ?? [];
  const readyTotal = invRows.filter((r) => r.status === "ready").length;

  const failedAll = runsFailed.count ?? 0;
  const totalAll = runsTotal.count ?? 0;
  const failRows = failedRows.data ?? [];
  const failByType = failRows.reduce((m: Record<string, number>, r) => { const c = categorize(r.error_message); m[c] = (m[c] ?? 0) + 1; return m; }, {});
  const failTotal = failRows.length || 1;
  const errRate = totalAll ? Math.round((failedAll / totalAll) * 100) : 0;

  const workers = hb.data ?? [];
  const STALE_MS = 60_000;
  const liveWorkers = workers.filter((w) => now - new Date(w.last_heartbeat_at).getTime() < STALE_MS && w.status === "up");
  const allOk = workers.length > 0 && liveWorkers.length === workers.length;

  const DB: [string, string][] = [
    ["Videos", String(vids.count ?? 0)], ["Production runs", String(totalAll)],
    ["Analytics rows", String(analytics.count ?? 0)], ["Channels", String(channels.count ?? 0)],
    ["Stok siap tayang (ready)", String(readyTotal)],
  ];

  return (
    <>
      <div className="sys-head">
        <div><h1>System Health</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi /></div></div>
        {workers.length === 0
          ? <span className="badge badge-warning" style={{ height: "fit-content" }}><span className="dot" />Worker belum aktif</span>
          : <span className={`badge ${allOk ? "badge-success" : "badge-warning"}`} style={{ height: "fit-content" }}><span className="dot" />{allOk ? "Semua operasional" : "Sebagian degraded"}</span>}
      </div>

      {workers.length === 0 ? (
        <div className="card card-pad" style={{ display: "flex", alignItems: "center", gap: "0.75rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          <Server size={18} /> <span>Belum ada heartbeat worker. Worker v2 (<span className="mono">worker_decoupled.py</span>) menulis heartbeat tiap ~15s saat aktif/cutover.</span>
        </div>
      ) : (
        <div className="sys-worker-grid">
          {workers.map((w) => { const live = now - new Date(w.last_heartbeat_at).getTime() < STALE_MS && w.status === "up"; const c = live ? "var(--success)" : "var(--warning)"; const ago = Math.round((now - new Date(w.last_heartbeat_at).getTime()) / 1000); return (
            <div className="sys-worker" key={w.worker_name}><div className="top"><span className="wdot" style={{ background: c }} /><span className="nm">{w.worker_name}</span><span className={`badge ${live ? "badge-success" : "badge-warning"}`} style={{ marginLeft: "auto", fontSize: "0.5625rem" }}>{live ? "up" : "stale"}</span></div>
              <div className="meta">node: <b style={{ color: "var(--text-primary)" }}>{w.node ?? "—"}</b><br />heartbeat: {ago}s lalu</div></div>
          ); })}
        </div>
      )}

      <div className="sys-grid2">
        <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: "1rem" }}><Activity size={16} /> Stok buffer per channel · {readyTotal} ready</h3>
          {activeChannels.length === 0 ? <div className="muted" style={{ fontSize: "var(--text-sm)" }}>Belum ada channel aktif.</div> :
            activeChannels.map((ch) => {
              const s = stockByChannel[ch.id] ?? {};
              const stok = (s["ready"] ?? 0) + (s["ready_with_issues"] ?? 0) + (s["producing"] ?? 0);
              const target = ch.buffer_depth ?? null;
              const pct = target ? Math.min(100, Math.round((stok / target) * 100)) : (stok > 0 ? 100 : 0);
              const detail = [s["ready"] ? `${s["ready"]} ready` : "", s["ready_with_issues"] ? `${s["ready_with_issues"]} perlu tinjau` : "", s["producing"] ? `${s["producing"]} produksi` : "", s["publishing"] ? `${s["publishing"]} publish` : ""].filter(Boolean).join(" · ") || "kosong";
              return (
                <div key={ch.id} style={{ marginBottom: "0.75rem" }}>
                  <div className="sys-bar-row"><span className="lab">{ch.channel_name}</span><div className="track"><span style={{ width: `${pct}%`, background: pct >= 100 ? "var(--success)" : pct > 0 ? "#f59e0b" : "#ef4444" }} /></div><span className="val">{stok}{target ? `/${target}` : ""}</span></div>
                  <div className="muted" style={{ fontSize: "var(--text-xs)", paddingLeft: 2 }}>{detail}</div>
                </div>
              );
            })}
        </div>
        <div className="card"><div className="card-head"><h3 className="card-title"><AlertTriangle size={16} /> Run gagal per jam (24h) · {failed24} dlm 24h · {errRate}% all-time ({failedAll}/{totalAll})</h3></div><div className="card-body"><LineChart data={errorSeries} color="#EF4444" gid="sys-e" /></div></div>
      </div>

      <div className="sys-grid2" style={{ marginTop: "1rem" }}>
        <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: "1rem" }}><XCircle size={16} /> Pipeline failures by type ({failedAll} total)</h3>
          {failRows.length === 0 ? <div className="muted" style={{ fontSize: "var(--text-sm)" }}>Tidak ada kegagalan tercatat.</div> :
            Object.entries(failByType).sort((x, y) => y[1] - x[1]).map(([n, v]) => { const pct = Math.round((v / failTotal) * 100); return (<div className="sys-bar-row" key={n}><span className="lab">{n}</span><div className="track"><span style={{ width: `${pct}%`, background: FAIL_COLOR[n] ?? "#a1a1aa" }} /></div><span className="val">{pct}%</span></div>); })}
        </div>
        <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: "1rem" }}><Command size={16} /> Database (skala data) · {runsSuccess.count ?? 0} runs sukses</h3>
          {DB.map(([k, v]) => (<div className="sys-db-stat" key={k}><span className="muted">{k}</span><span>{v}</span></div>))}
        </div>
      </div>

      <div className="card card-pad" style={{ marginTop: "1rem" }}>
        <h3 className="card-title" style={{ marginBottom: "1rem" }}><Server size={16} /> Direct Jobs (on-demand) · {djRows.length} terbaru</h3>
        <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
          {([["Antre", dj.pending, "var(--info)"], ["Berjalan", dj.producing, "var(--warning)"], ["Selesai", dj.published, "var(--success)"], ["Gagal", dj.failed, "var(--error)"]] as [string, number, string][]).map(([l, n, c]) => (
            <div key={l}><div style={{ fontSize: "var(--text-2xl)", fontWeight: 700, color: c }}>{n}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{l}</div></div>
          ))}
        </div>
      </div>
    </>
  );
}

function Bi() { return (<><span data-id>Status worker, queue, dan database</span><span data-en>Worker, queue, and database status</span></>); }
