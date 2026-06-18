"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Download, Zap, Tv, ChevronDown, Calendar, Filter, ChevronLeft, ChevronRight,
  MoreHorizontal, X, RefreshCw, ArrowRight, Check, Loader2, Clock, type LucideIcon,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./runs-list.css";

// D4 Runs List — Phase 9.3 (wired Supabase v2, anon + RLS). Baca production_runs NYATA
// (ryan ~99 row). status filter client-side. views/cost = "—" (production_runs tak punya
// kolom views/cost — sumber = video_analytics, di-wire 9.4). Pipeline mini-step = derivasi
// dari status (bukan data fabricated). Drawer → /runs/[id] (D5).

type StKey = "completed" | "running" | "failed" | "queued" | "review";
function statusKey(s: string | null): StKey {
  const v = (s || "").toLowerCase();
  if (v.includes("complete") || v === "published" || v === "success") return "completed";
  // qc_failed / ready_with_issues = PRODUK JADI tapi ada catatan QC → "Perlu Ditinjau", BUKAN gagal.
  // WAJIB dicek sebelum 'fail' (qc_failed mengandung "fail").
  if (v.includes("qc_fail") || v.includes("ready_with_issues") || v.includes("issue")) return "review";
  if (v.includes("fail") || v.includes("error")) return "failed";
  if (v.includes("run") || v.includes("produc") || v.includes("publish")) return "running";
  return "queued";
}

type RunRow = {
  id: string; channel_id: string | null; niche: string | null; topic: string | null;
  status: string | null; elapsed_seconds: string | null; youtube_url: string | null;
  viral_score: number | null; created_at: string;
};

function fmtDur(secs: string | null, st: StKey) {
  if (st === "running") return "berjalan…";
  if (st === "queued") return "—";
  const n = parseFloat(secs || "");
  if (!isFinite(n) || n <= 0) return st === "failed" ? "—" : "—";
  return n >= 60 ? `${Math.floor(n / 60)}m ${Math.round(n % 60)}s` : `${Math.round(n)}s`;
}
function fmtWhen(iso: string) {
  try { return new Date(iso).toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
}
function prettyNiche(k: string | null) { return (k || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }

const STATUS_TABS: { key: StKey | "all"; id: string; en: string }[] = [
  { key: "all", id: "Semua", en: "All" }, { key: "completed", id: "Completed", en: "Completed" },
  { key: "running", id: "Running", en: "Running" }, { key: "review", id: "Perlu Ditinjau", en: "Needs Review" },
  { key: "failed", id: "Failed", en: "Failed" },
  { key: "queued", id: "Queued", en: "Queued" },
];

function Badge({ st }: { st: StKey }) {
  const m: Record<StKey, [string, string]> = { completed: ["badge-success", "Completed"], running: ["badge-running", "Running"], review: ["badge-warning", "Perlu Ditinjau"], failed: ["badge-error", "Failed"], queued: ["badge-default", "Queued"] };
  const [c, l] = m[st];
  return <span className={`badge ${c}`}><span className="dot" />{l}</span>;
}

const PL_NAMES = ["Trend Radar", "Topic Select", "Script", "Hook", "TTS", "Visual", "Render", "Publish"];
const STEP_ICON: Record<string, [string, string, LucideIcon]> = {
  done: ["var(--success)", "var(--success-soft)", Check], run: ["var(--info)", "var(--info-soft)", Loader2],
  fail: ["var(--error)", "var(--error-soft)", X], pend: ["var(--text-muted)", "var(--surface-2)", Clock],
};

export default function RunsListPage() {
  const [supabase] = useState(() => createClient());
  const [data, setData] = useState<RunRow[]>([]);
  const [chMap, setChMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StKey | "all">("all");
  const [selected, setSelected] = useState<RunRow | null>(null);
  const [direct, setDirect] = useState<{ id: string; status: string; job_type: string; niche: string | null }[]>([]);

  const load = useCallback(async () => {
    const [{ data: runs }, { data: chs }, { data: dj }] = await Promise.all([
      supabase.from("production_runs").select("id,channel_id,niche,topic,status,elapsed_seconds,youtube_url,viral_score,created_at").order("created_at", { ascending: false }).limit(100),
      supabase.from("channels").select("id,channel_name"),
      supabase.from("direct_jobs").select("id,status,job_type,niche").in("status", ["pending", "producing"]).order("created_at", { ascending: false }),
    ]);
    setDirect(dj ?? []);
    setData((runs as RunRow[]) ?? []);
    const m: Record<string, string> = {};
    (chs as { id: string; channel_name: string | null }[] ?? []).forEach((c) => { m[c.id] = c.channel_name || "Channel"; });
    setChMap(m);
    setLoading(false);
  }, [supabase]);

  function exportCsv() {
    const head = ["id", "channel", "niche", "topic", "status", "viral_score", "youtube_url", "created_at"];
    const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const rows = data.map((r) => [r.id, chMap[r.channel_id ?? ""] ?? "", r.niche ?? "", r.topic ?? "", r.status ?? "", r.viral_score ?? "", r.youtube_url ?? "", r.created_at].map(esc).join(","));
    const blob = new Blob([[head.join(","), ...rows].join("\n")], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `runs-${new Date().toISOString().slice(0, 10)}.csv`; a.click(); URL.revokeObjectURL(a.href);
  }

  useEffect(() => {
    load();
    const onEsc = (e: KeyboardEvent) => { if (e.key === "Escape") setSelected(null); };
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [load]);

  const rows = data.filter((d) => filter === "all" || statusKey(d.status) === filter);
  const done = data.filter((d) => statusKey(d.status) === "completed").length;
  const fail = data.filter((d) => statusKey(d.status) === "failed").length;

  function miniSteps(st: StKey) {
    // review = produk JADI (7 langkah produksi selesai), hanya Publish belum (masih di buffer/ditinjau).
    const activeCount = st === "completed" ? 8 : st === "review" ? 7 : st === "running" ? 6 : st === "failed" ? 5 : 0;
    return PL_NAMES.map((name, i) => {
      let stt = i < activeCount - 1 ? "done" : i === activeCount - 1 ? (st === "failed" ? "fail" : st === "running" ? "run" : "done") : "pend";
      if (st === "completed") stt = "done";
      const [col, bg, Icon] = STEP_ICON[stt];
      return (
        <div className="mini-step" key={i}>
          <span className="n" style={{ background: bg, color: col }}><Icon size={13} /></span>
          <span style={{ color: "var(--text-primary)" }}>{name}</span>
          {stt === "fail" && <span className="badge badge-error" style={{ marginLeft: "auto" }}><span className="dot" />error</span>}
        </div>
      );
    });
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Runs</h1>
          <div className="sub" dangerouslySetInnerHTML={{ __html: `<b>${done}</b> run sukses · <b>${fail}</b> gagal` }} />
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-secondary" disabled={!data.length} onClick={exportCsv}><Download size={15} /> Export CSV</button>
        </div>
      </div>

      {direct.length > 0 && (
        <div className="card card-pad" style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: ".75rem", flexWrap: "wrap" }}>
          <Zap size={15} style={{ color: "var(--accent)" }} />
          <span style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}><span data-id>Produksi langsung</span><span data-en>Direct produce</span></span>
          {direct.map((d) => (
            <span key={d.id} className={`badge ${d.status === "producing" ? "badge-warning" : "badge-info"}`} style={{ fontSize: "0.6875rem" }}>
              <span className="dot" />{d.status === "producing" ? "Berjalan" : "Antre"} · {d.job_type}{d.niche ? ` · ${prettyNiche(d.niche)}` : ""}
            </span>
          ))}
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}><span data-id>diproses worker → progress muncul di sini</span><span data-en>processed by worker → progress appears here</span></span>
        </div>
      )}

      <div className="filters">
        <div className="segmented">
          {STATUS_TABS.map((t) => (
            <button key={t.key} aria-selected={filter === t.key} onClick={() => setFilter(t.key)}>
              <span data-id>{t.id}</span><span data-en>{t.en}</span>
            </button>
          ))}
        </div>
        <div className="selbox"><Tv size={14} /> <span data-id>Semua channel</span><span data-en>All channels</span> <ChevronDown size={14} /></div>
        <div className="selbox"><Calendar size={14} /> 7 hari terakhir <ChevronDown size={14} /></div>
        <div className="selbox"><Filter size={14} /> Niche <ChevronDown size={14} /></div>
      </div>

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr>
              <th>ID</th><th>Channel</th><th>Niche</th><th>Topic</th><th>Status</th>
              <th className="num">Durasi</th><th className="num">Views</th><th>Started</th><th></th>
            </tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} className="muted" style={{ textAlign: "center", padding: "2rem" }}><span data-id>Memuat runs…</span><span data-en>Loading runs…</span></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={9} className="muted" style={{ textAlign: "center", padding: "2rem" }}><span data-id>Belum ada run.</span><span data-en>No runs yet.</span></td></tr>
              ) : rows.map((d) => {
                const st = statusKey(d.status);
                return (
                  <tr key={d.id} onClick={() => setSelected(d)}>
                    <td><span className="runid">#{d.id}</span></td>
                    <td><span className="ch-cell muted">{d.channel_id ? (chMap[d.channel_id] ?? "—") : "—"}</span></td>
                    <td><span className="muted">{prettyNiche(d.niche)}</span></td>
                    <td><div className="topic-cell">{d.topic || <span className="muted">—</span>}</div></td>
                    <td><Badge st={st} /></td>
                    <td className="num mono" style={{ fontSize: "var(--text-xs)" }}>{fmtDur(d.elapsed_seconds, st)}</td>
                    <td className="num"><span className="muted">—</span></td>
                    <td><span className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{fmtWhen(d.created_at)}</span></td>
                    <td><button className="btn btn-ghost btn-icon btn-sm" onClick={(e) => e.stopPropagation()}><MoreHorizontal size={14} /></button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="pager">
          <span>Menampilkan {rows.length} dari {data.length} run</span>
        </div>
      </div>

      {/* drawer */}
      <div className={`scrim${selected ? " open" : ""}`} onClick={() => setSelected(null)} />
      <aside className={`drawer${selected ? " open" : ""}`}>
        {selected && (() => {
          const st = statusKey(selected.status);
          return (
            <>
              <div className="drawer-head">
                <div>
                  <div className="runid">RUN #{selected.id}</div>
                  <div style={{ fontSize: "var(--text-lg)", fontWeight: 600, letterSpacing: "-0.01em", marginTop: 2 }}>{selected.topic || "(tanpa topik)"}</div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: 4 }}>{(selected.channel_id && chMap[selected.channel_id]) || "—"} · {prettyNiche(selected.niche)}</div>
                </div>
                <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSelected(null)}><X size={16} /></button>
              </div>
              <div className="drawer-body">
                <div><Badge st={st} /></div>
                <div>
                  <div className="sec-label"><span data-id>Ringkasan</span><span data-en>Summary</span></div>
                  <div className="kv"><span className="k">Durasi</span><span className="v">{fmtDur(selected.elapsed_seconds, st)}</span></div>
                  <div className="kv"><span className="k">Viral score</span><span className="v">{selected.viral_score ?? "—"}</span></div>
                  <div className="kv"><span className="k">YouTube</span><span className="v">{selected.youtube_url ? <a href={selected.youtube_url} target="_blank" rel="noreferrer" className="link">buka</a> : "—"}</span></div>
                  <div className="kv"><span className="k">Mulai</span><span className="v">{fmtWhen(selected.created_at)}</span></div>
                </div>
                <div>
                  <div className="sec-label">Pipeline</div>
                  <div>{miniSteps(st)}</div>
                </div>
              </div>
              <div className="drawer-foot">
                <a href={`/runs/${selected.id}`} className="btn btn-default" style={{ flex: 1 }}>
                  <span data-id>Buka run lengkap</span><span data-en>Open full run</span> <ArrowRight size={15} />
                </a>
                <button className="btn btn-secondary" onClick={load}><RefreshCw size={15} /></button>
              </div>
            </>
          );
        })()}
      </aside>
    </>
  );
}
