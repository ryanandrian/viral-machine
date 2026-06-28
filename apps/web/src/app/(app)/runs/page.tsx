"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Download, Zap, ChevronLeft, ChevronRight, Search,
  Eye, X, RefreshCw, ArrowRight, Check, Loader2, Clock, Play, Trash2, type LucideIcon,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import ConfirmDialog from "@/components/confirm-dialog";
import "./runs-list.css";

// D4 Runs List — Phase 9.3 (wired Supabase v2, anon + RLS). Baca production_runs NYATA
// (ryan ~99 row). status filter client-side. views/cost = "—" (production_runs tak punya
// kolom views/cost — sumber = video_analytics, di-wire 9.4). Pipeline mini-step = derivasi
// dari status (bukan data fabricated). Drawer → /runs/[id] (D5).

type StKey = "completed" | "failed" | "review" | "discarded";
function statusKey(s: string | null): StKey {
  const v = (s || "").toLowerCase();
  if (v.includes("complete") || v === "published" || v === "success") return "completed";
  // discarded = tenant Buang konten cacat (resolved) → BUKAN "perlu ditinjau". Cek sebelum qc_fail/fail.
  if (v.includes("discard")) return "discarded";
  // qc_failed / ready_with_issues = PRODUK JADI tapi ada catatan QC → "Perlu Ditinjau", BUKAN gagal.
  // WAJIB dicek sebelum 'fail' (qc_failed mengandung "fail").
  if (v.includes("qc_fail") || v.includes("ready_with_issues") || v.includes("issue")) return "review";
  if (v.includes("fail") || v.includes("error")) return "failed";
  return "completed";  // production_runs = ledger terminal (success/failed/qc_failed/discarded); fallback aman
}

type RunRow = {
  id: string; run_id: string | null; channel_id: string | null; niche: string | null; topic: string | null;
  status: string | null; elapsed_seconds: string | null; youtube_url: string | null;
  youtube_video_id: string | null; viral_score: number | null; created_at: string;
};
const fmtK = (n: number) => n >= 1_000_000 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

function fmtDur(secs: string | null) {
  const n = parseFloat(secs || "");
  if (!isFinite(n) || n <= 0) return "—";
  return n >= 60 ? `${Math.floor(n / 60)}m ${Math.round(n % 60)}s` : `${Math.round(n)}s`;
}
function fmtWhen(iso: string) {
  try { return new Date(iso).toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
}
function prettyNiche(k: string | null) { return (k || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }

const STATUS_TABS: { key: StKey | "all" | "queued"; id: string; en: string }[] = [
  { key: "all", id: "Semua", en: "All" }, { key: "completed", id: "Completed", en: "Completed" },
  { key: "review", id: "Perlu Ditinjau", en: "Needs Review" },
  { key: "failed", id: "Failed", en: "Failed" },
  { key: "discarded", id: "Dibuang", en: "Discarded" },
  { key: "queued", id: "Menunggu publish", en: "Awaiting publish" },
];

function Badge({ st }: { st: StKey }) {
  const m: Record<StKey, [string, string, string]> = { completed: ["badge-success", "Selesai", "Completed"], review: ["badge-warning", "Perlu Ditinjau", "Needs Review"], failed: ["badge-error", "Gagal", "Failed"], discarded: ["badge-default", "Dibuang", "Discarded"] };
  const [c, idL, enL] = m[st];
  return <span className={`badge ${c}`}><span className="dot" /><span data-id>{idL}</span><span data-en>{enL}</span></span>;
}

const PL_NAMES = ["Trend Radar", "Topic Select", "Script", "Hook", "TTS", "Visual", "Render", "Publish"];
const STEP_ICON: Record<string, [string, string, LucideIcon]> = {
  done: ["var(--success)", "var(--success-soft)", Check], run: ["var(--info)", "var(--info-soft)", Loader2],
  fail: ["var(--error)", "var(--error-soft)", X], pend: ["var(--text-muted)", "var(--surface-2)", Clock],
};

export default function RunsListPage() {
  const [supabase] = useState(() => createClient());
  const [data, setData] = useState<RunRow[]>([]);
  const [queue, setQueue] = useState<{ id: number; niche: string | null; channel_id: string | null; runId: string | null; topic: string | null; created_at: string; duration: number | null; viralScore: number | null; grade: string | null }[]>([]);  // content_inventory.ready (menunggu publish)
  const [pvBusy, setPvBusy] = useState<number | null>(null);  // tombol Pratinjau antrean
  const [pvMsg, setPvMsg] = useState<string | null>(null);
  const [confirmCfg, setConfirmCfg] = useState<null | { title: ReactNode; message: ReactNode; confirmLabel: ReactNode; onConfirm: () => void }>(null);
  const [chMap, setChMap] = useState<Record<string, string>>({});
  const [views, setViews] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StKey | "all" | "queued">("all");
  const [selected, setSelected] = useState<RunRow | null>(null);
  const [direct, setDirect] = useState<{ id: string; status: string; job_type: string; niche: string | null }[]>([]);
  const [q, setQ] = useState("");
  const [chFilter, setChFilter] = useState("all");
  const [nicheFilter, setNicheFilter] = useState("all");
  const [days, setDays] = useState<"7" | "30" | "all">("all");
  const [page, setPage] = useState(0);
  const PAGE = 25;

  const load = useCallback(async () => {
    const [{ data: runs }, { data: chs }, { data: dj }, vw, { data: ci }] = await Promise.all([
      supabase.from("production_runs").select("id,run_id,channel_id,niche,topic,status,elapsed_seconds,youtube_url,youtube_video_id,viral_score,created_at").order("created_at", { ascending: false }).limit(2000),
      supabase.from("channels").select("id,channel_name"),
      supabase.from("direct_jobs").select("id,status,job_type,niche").in("status", ["pending", "producing"]).order("created_at", { ascending: false }),
      supabase.rpc("get_tenant_video_views"),
      supabase.from("content_inventory").select("id,niche,channel_id,metadata,created_at").eq("status", "ready").order("created_at", { ascending: true }),
    ]);
    setDirect(dj ?? []);
    setData((runs as RunRow[]) ?? []);
    setQueue(((ci as { id: number; niche: string | null; channel_id: string | null; metadata: { run_id?: string; script?: { title?: string; topic?: string }; duration_secs?: number; viral_score?: number; insights_grade?: string } | null; created_at: string }[]) ?? []).map((q) => ({
      id: q.id, niche: q.niche, channel_id: q.channel_id, created_at: q.created_at,
      runId: q.metadata?.run_id ?? null,
      // Samakan dgn daftar Runs (yg pakai production_runs.topic) → 1 konten = 1 nama di kedua tempat.
      topic: q.metadata?.script?.topic || q.metadata?.script?.title || null,
      duration: q.metadata?.duration_secs ?? null,
      viralScore: q.metadata?.viral_score ?? null,
      grade: q.metadata?.insights_grade ?? null,
    })));
    const m: Record<string, string> = {};
    (chs as { id: string; channel_name: string | null }[] ?? []).forEach((c) => { m[c.id] = c.channel_name || "Channel"; });
    setChMap(m);
    const vm: Record<string, number> = {};
    (vw.data as { video_id: string; views: number }[] ?? []).forEach((v) => { vm[v.video_id] = Number(v.views) || 0; });
    setViews(vm);
    setLoading(false);
  }, [supabase]);

  // Pratinjau video buffer (review-only) — presigned URL S3 via endpoint yg sama dgn /review.
  async function previewQueue(id: number) {
    setPvMsg(null); setPvBusy(id);
    try {
      const r = await fetch(`/api/review/preview?id=${id}`);
      const j = await r.json();
      if (r.ok && j.url) window.open(j.url as string, "_blank", "noopener");
      else setPvMsg(`Pratinjau gagal: ${j.error ?? r.status}`);
    } catch (e) {
      setPvMsg(`Pratinjau gagal: ${(e as Error).message}`);
    } finally {
      setPvBusy(null);
    }
  }

  // Buang konten 'ready' dari antrean (konten basi) — janitor hapus S3, producer auto-isi ulang yg segar.
  function askDiscardQueue(id: number) {
    setConfirmCfg({
      title: <><span data-id>Buang konten ini dari antrean?</span><span data-en>Discard this from the queue?</span></>,
      message: <><span data-id>Video dihapus &amp; tidak akan tayang. Mesin otomatis memproduksi konten baru yang lebih segar menggantikannya.</span><span data-en>The video is deleted and won&apos;t publish. The engine auto-produces a fresher replacement.</span></>,
      confirmLabel: <><span data-id>Ya, buang</span><span data-en>Yes, discard</span></>,
      onConfirm: async () => {
        const { error } = await supabase.rpc("discard_ready_item", { p_inv_id: id });
        setConfirmCfg(null);
        if (error) setPvMsg(`Gagal membuang: ${error.message}`);
        else load();
      },
    });
  }

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
  useEffect(() => { setPage(0); }, [filter, q, chFilter, nicheFilter, days]);

  // Run yang kontennya masih di antrean publish (content_inventory.ready) punya tab "Menunggu publish"
  // sendiri → jangan dihitung/ditampilkan ganda di Completed/All.
  const readyRunIds = new Set(queue.map((q) => q.runId).filter(Boolean) as string[]);
  const inQueue = (d: RunRow) => !!(d.run_id && readyRunIds.has(d.run_id));
  const done = data.filter((d) => !inQueue(d) && statusKey(d.status) === "completed").length;
  const fail = data.filter((d) => statusKey(d.status) === "failed").length;
  const nicheOpts = Array.from(new Set(data.map((d) => d.niche).filter(Boolean))) as string[];
  const ql = q.trim().toLowerCase();
  const cutoff = days === "all" ? 0 : Date.now() - parseInt(days) * 86400000;
  const queueShown = queue.filter((q) =>
    (chFilter === "all" || q.channel_id === chFilter) &&
    (nicheFilter === "all" || q.niche === nicheFilter) &&
    (!ql || `${q.topic ?? ""} ${prettyNiche(q.niche)}`.toLowerCase().includes(ql)));
  const filtered = data.filter((d) =>
    !inQueue(d) &&
    (filter === "all" || statusKey(d.status) === filter) &&
    (chFilter === "all" || d.channel_id === chFilter) &&
    (nicheFilter === "all" || d.niche === nicheFilter) &&
    (days === "all" || (() => { try { return new Date(d.created_at).getTime() >= cutoff; } catch { return true; } })()) &&
    (!ql || `${d.id} ${d.topic ?? ""} ${prettyNiche(d.niche)}`.toLowerCase().includes(ql))
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE));
  const pg = Math.min(page, pageCount - 1);
  const paged = filtered.slice(pg * PAGE, pg * PAGE + PAGE);

  function miniSteps(st: StKey) {
    // review = produk JADI (7 langkah produksi selesai), hanya Publish belum (masih di buffer/ditinjau).
    const activeCount = st === "completed" ? 8 : st === "review" ? 7 : st === "discarded" ? 7 : st === "failed" ? 5 : 0;
    return PL_NAMES.map((name, i) => {
      let stt = i < activeCount - 1 ? "done" : i === activeCount - 1 ? (st === "failed" ? "fail" : "done") : "pend";
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
        <div className="selbox" style={{ gap: "0.4rem" }}><Search size={14} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari ID / topik / niche…" style={{ border: "none", background: "transparent", outline: "none", color: "inherit", font: "inherit", width: 160 }} /></div>
        <select className="selbox" value={chFilter} onChange={(e) => setChFilter(e.target.value)} title="Channel">
          <option value="all">Semua channel</option>
          {Object.entries(chMap).map(([id, nm]) => <option key={id} value={id}>{nm}</option>)}
        </select>
        <select className="selbox" value={days} onChange={(e) => setDays(e.target.value as "7" | "30" | "all")} title="Rentang waktu">
          <option value="all">Semua waktu</option>
          <option value="7">7 hari terakhir</option>
          <option value="30">30 hari terakhir</option>
        </select>
        <select className="selbox" value={nicheFilter} onChange={(e) => setNicheFilter(e.target.value)} title="Niche">
          <option value="all">Semua niche</option>
          {nicheOpts.map((n) => <option key={n} value={n}>{prettyNiche(n)}</option>)}
        </select>
      </div>

      {filter === "queued" && (
        <div className="card">
          {pvMsg && <div className="card-pad" style={{ paddingBottom: 0 }}><p style={{ fontSize: "var(--text-xs)", color: "var(--error)", margin: 0 }}>{pvMsg}</p></div>}
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead><tr><th>Topik</th><th>Channel</th><th>Niche</th><th className="num">Durasi</th><th className="num">Skor viral</th><th>Grade</th><th>Diproduksi</th><th></th></tr></thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={8} className="muted" style={{ textAlign: "center", padding: "2rem" }}><span data-id>Memuat…</span><span data-en>Loading…</span></td></tr>
                ) : queueShown.length === 0 ? (
                  <tr><td colSpan={8} className="muted" style={{ textAlign: "center", padding: "2rem" }}><span data-id>Tidak ada konten menunggu publish.</span><span data-en>No content awaiting publish.</span></td></tr>
                ) : queueShown.map((q) => (
                  <tr key={q.id}>
                    <td><div className="topic-cell">{q.topic || <span className="muted">—</span>}</div></td>
                    <td><span className="ch-cell muted">{q.channel_id ? (chMap[q.channel_id] ?? "—") : "—"}</span></td>
                    <td><span className="muted">{prettyNiche(q.niche)}</span></td>
                    <td className="num mono" style={{ fontSize: "var(--text-xs)" }}>{q.duration != null ? `${Math.round(q.duration)}s` : "—"}</td>
                    <td className="num">{q.viralScore != null ? <b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{Math.round(q.viralScore)}</b> : <span className="muted">—</span>}</td>
                    <td>{q.grade ? <span className="muted" style={{ textTransform: "capitalize" }}>{q.grade}</span> : <span className="muted">—</span>}</td>
                    <td><span className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{fmtWhen(q.created_at)}</span></td>
                    <td><div style={{ display: "flex", gap: "0.35rem", justifyContent: "flex-end" }}>
                      <button className="btn btn-ghost btn-sm" disabled={pvBusy === q.id} onClick={() => previewQueue(q.id)} title="Pratinjau video sebelum tayang">{pvBusy === q.id ? <Loader2 size={14} /> : <Play size={14} />} <span data-id>Pratinjau</span><span data-en>Preview</span></button>
                      <button className="btn btn-ghost btn-sm" onClick={() => askDiscardQueue(q.id)} title="Buang konten ini (mesin produksi ulang yang segar)"><Trash2 size={14} /> <span data-id>Buang</span><span data-en>Discard</span></button>
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {filter !== "queued" && (
      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr>
              <th>ID</th><th>Channel</th><th>Niche</th><th>Topic</th><th>Status</th>
              <th className="num" title="Waktu proses produksi">Proses</th><th className="num">Views</th><th>Started</th><th></th>
            </tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} className="muted" style={{ textAlign: "center", padding: "2rem" }}><span data-id>Memuat runs…</span><span data-en>Loading runs…</span></td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={9} className="muted" style={{ textAlign: "center", padding: "2rem" }}><span data-id>Tidak ada run cocok filter.</span><span data-en>No runs match filters.</span></td></tr>
              ) : paged.map((d) => {
                const st = statusKey(d.status);
                return (
                  <tr key={d.id} onClick={() => setSelected(d)}>
                    <td><span className="runid">#{d.id}</span></td>
                    <td><span className="ch-cell muted">{d.channel_id ? (chMap[d.channel_id] ?? "—") : "—"}</span></td>
                    <td><span className="muted">{prettyNiche(d.niche)}</span></td>
                    <td><div className="topic-cell">{d.topic || <span className="muted">—</span>}</div></td>
                    <td><Badge st={st} /></td>
                    <td className="num mono" style={{ fontSize: "var(--text-xs)" }}>{fmtDur(d.elapsed_seconds)}</td>
                    <td className="num">{d.youtube_video_id && views[d.youtube_video_id] != null ? <b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{fmtK(views[d.youtube_video_id])}</b> : <span className="muted">—</span>}</td>
                    <td><span className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{fmtWhen(d.created_at)}</span></td>
                    <td><a href={`/runs/${d.id}`} className="btn btn-ghost btn-icon btn-sm" onClick={(e) => e.stopPropagation()} title="Lihat detail"><Eye size={14} /></a></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="pager">
          <span>Halaman {pg + 1} / {pageCount} · {filtered.length} run</span>
          <div style={{ display: "flex", gap: "0.4rem", marginLeft: "auto" }}>
            <button className="btn btn-secondary btn-sm" disabled={pg <= 0} onClick={() => setPage(pg - 1)}><ChevronLeft size={14} /></button>
            <button className="btn btn-secondary btn-sm" disabled={pg >= pageCount - 1} onClick={() => setPage(pg + 1)}><ChevronRight size={14} /></button>
          </div>
        </div>
      </div>
      )}

      <ConfirmDialog
        open={!!confirmCfg}
        title={confirmCfg?.title}
        message={confirmCfg?.message}
        confirmLabel={confirmCfg?.confirmLabel}
        confirmClass="btn-destructive"
        onConfirm={() => confirmCfg?.onConfirm()}
        onCancel={() => setConfirmCfg(null)}
      />

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
                  <div className="kv"><span className="k">Durasi</span><span className="v">{fmtDur(selected.elapsed_seconds)}</span></div>
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
