"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft, Tag, Calendar, Clock, RefreshCw, ExternalLink, Search, Pause, Play,
  Radar, Target, FileText, Sparkles, AudioLines, Image as ImageIcon, Film, Upload,
  Check, Loader2, X, AlertTriangle, Eye, Trash2, type LucideIcon,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { BASELINE_WEIGHTS, DIM_LABEL } from "@/components/insights-view";
import { PesanGalat } from "@/components/gate-message";
import "./run-detail.css";

// Dwibahasa: dua span, CSS menyembunyikan yang tak dipakai (pola `Bi` seluruh aplikasi, §3.5).
function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

// Urutan dimensi skor viral (selaras src/intelligence/config.py).
const SCORE_DIMS = ["search_volume", "trend_momentum", "emotional_trigger", "competition_gap", "evergreen_potential"];

// D5 Run Detail — Phase 9.3 (wired Supabase v2, anon + RLS). Header + log = data NYATA.
// Log: fetch pipeline_run_logs by queue_id + REALTIME subscribe (live-tail). Pipeline 8-step =
// derivasi dari status + step yang muncul di log (BUKAN simulasi fabricated). Cost/providers
// dari run_metadata bila ada, else "—". (pipeline_run_logs kosong di dev = worker idle → empty-state.)

type StepState = "completed" | "running" | "pending" | "failed";
type LogRow = { id: number | string; level: string | null; step: string | null; category: string | null; message: string | null; created_at: string };
type RunRow = {
  id: string; queue_id: string | number | null; run_id: string | null; channel_id: string | null; topic: string | null; niche: string | null;
  run_metadata?: { video_title?: string } | null;   // judul AKHIR video (samakan dgn YouTube; fallback topik)
  status: string | null; youtube_url: string | null; viral_score: number | null; elapsed_seconds: string | null;
  error_message: string | null; llm_provider: string | null; created_at: string;
};

function statusKey(s: string | null): "completed" | "running" | "failed" | "queued" | "review" | "discarded" {
  const v = (s || "").toLowerCase();
  if (v.includes("complete") || v === "published" || v === "success") return "completed";
  // discarded = tenant sudah Buang konten cacat (resolved) → bukan "perlu ditinjau". Cek sebelum qc_fail/fail.
  if (v.includes("discard")) return "discarded";
  // qc_failed / ready_with_issues = PRODUK JADI + catatan QC → "Perlu Ditinjau" (cek SEBELUM 'fail').
  if (v.includes("qc_fail") || v.includes("ready_with_issues") || v.includes("issue")) return "review";
  if (v.includes("fail") || v.includes("error")) return "failed";
  if (v.includes("run") || v.includes("produc") || v.includes("publish")) return "running";
  return "queued";
}
function prettyNiche(k: string | null) { return (k || "—").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }
function fmtDur(secs: string | null) { const n = parseFloat(secs || ""); if (!isFinite(n) || n <= 0) return "—"; return n >= 60 ? `${Math.floor(n / 60)}m ${Math.round(n % 60)}s` : `${Math.round(n)}s`; }
function lvlClass(level: string | null, category: string | null): string {
  if ((category || "").toLowerCase() === "step") return "STEP";
  const v = (level || "").toLowerCase();
  if (v.includes("succ") || v === "ok") return "OK";
  if (v.includes("warn")) return "WARN";
  if (v.includes("err") || v.includes("crit")) return "ERR";
  return "INFO";
}
function hhmmss(iso: string) { try { return new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" }); } catch { return ""; } }

const STEP_DEFS: { key: string; icon: LucideIcon; id: string; en: string }[] = [
  { key: "trend", icon: Radar, id: "Trend Radar", en: "Trend Radar" },
  { key: "topic", icon: Target, id: "Topic Select", en: "Topic Select" },
  { key: "script", icon: FileText, id: "Script", en: "Script" },
  { key: "hook", icon: Sparkles, id: "Hook", en: "Hook" },
  { key: "tts", icon: AudioLines, id: "TTS Audio", en: "TTS Audio" },
  { key: "visual", icon: ImageIcon, id: "Visual", en: "Visual" },
  { key: "render", icon: Film, id: "Render", en: "Render" },
  { key: "publish", icon: Upload, id: "Publish", en: "Publish" },
];

function NodeIcon({ state, icon: I }: { state: StepState; icon: LucideIcon }) {
  if (state === "pending") return <I size={18} />;
  if (state === "running") return <Loader2 size={18} />;
  if (state === "failed") return <X size={18} />;
  return <Check size={18} />;
}

export default function RunDetailPage() {
  const id = (useParams<{ id: string }>()?.id) as string;
  const [supabase] = useState(() => createClient());
  const [run, setRun] = useState<RunRow | null>(null);
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState("");
  const logRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(paused); pausedRef.current = paused;
  // ReactNode, bukan string: ketiga pesannya dulu terkunci bahasa Indonesia meski layar berbahasa
  // Inggris ([B24] sekalian, §3.5 dwibahasa wajib).
  const [retryMsg, setRetryMsg] = useState<React.ReactNode | null>(null);
  // #5 breakdown skor viral: dimensi mentah (videos.topic_scores by run_id) × bobot adaptif (tenant_configs).
  const [dims, setDims] = useState<Record<string, number> | null>(null);
  const [scoreW, setScoreW] = useState<Record<string, number> | null>(null);

  // Jalankan ulang run yang gagal — direct_job retry (mis. setelah beli kredit AI).
  // [B24 §10a pintu 3] Tombol ini menulis LANGSUNG dari browser ke tabel antrean — tidak melewati
  // kode server kita sama sekali. Penjaga sesungguhnya = aturan akses tabel `direct_jobs`. Pemeriksaan
  // di bawah HANYA agar tenant membaca kalimat manusiawi, bukan pesan teknis "row-level security".
  // Kalau keduanya sempat tak sinkron (status berubah di antara dua panggilan), aturan tabel tetap
  // menang dan pesannya kita terjemahkan dari kode galatnya.
  async function retry() {
    if (!run?.channel_id) {
      setRetryMsg(<Bi id="Channel untuk produksi ini tak diketahui — tak bisa dijalankan ulang."
                      en="The channel for this run is unknown — cannot re-run." />);
      return;
    }
    setRetryMsg(null);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setRetryMsg(<Bi id="Sesi Anda tidak valid. Muat ulang halaman." en="Your session is invalid. Reload the page." />); return; }

    const { data: g } = await supabase.rpc("tenant_test_gate", { p_tenant_id: user.id });
    const gate = (Array.isArray(g) ? g[0] : g) as { allowed?: boolean; reason?: string; used?: number; max?: number } | null;
    if (gate && gate.allowed === false) {
      setRetryMsg(<PesanGalat text={gate.reason === "trial_quota"
        ? `GATE:trial_quota:${gate.used ?? 0}:${gate.max ?? 0}` : `GATE:${gate.reason}`} />);
      return;
    }

    const { error } = await supabase.from("direct_jobs").insert({
      tenant_id: user.id, channel_id: run.channel_id, job_type: "retry",
      source_run_id: run.run_id, niche: run.niche, requested_by: user.id,
    });
    if (!error) {
      setRetryMsg(<Bi id="Diantre ulang — pantau di daftar Produksi (Antre → Berjalan)."
                      en="Re-queued — follow it in the Runs list (Queued → Running)." />);
    } else if (error.code === "42501") {
      // Ditolak aturan akses tabel = gerbang uji. Tampilkan sebagai penolakan langganan, bukan galat teknis.
      setRetryMsg(<PesanGalat text="GATE:subscription" />);
    } else {
      setRetryMsg(<span><Bi id="Gagal: " en="Failed: " />{error.message}</span>);
    }
  }

  const load = useCallback(async () => {
    const { data } = await supabase.from("production_runs")
      .select("id,queue_id,run_id,channel_id,topic,niche,status,youtube_url,viral_score,elapsed_seconds,error_message,llm_provider,created_at,run_metadata")
      .eq("id", id).maybeSingle();
    const r = data as RunRow | null;
    setRun(r);
    // live-tail: log pipeline di-key oleh run_id → UTAMAKAN run_id (queue_id fallback).
    let q = supabase.from("pipeline_run_logs").select("id,level,step,category,message,created_at");
    if (r?.run_id) q = q.eq("run_id", r.run_id);
    else if (r?.queue_id != null) q = q.eq("queue_id", String(r.queue_id));
    else q = null as never;
    if (q) { const { data: lg } = await q.order("created_at", { ascending: true }).limit(2000); setLogs((lg as LogRow[]) ?? []); }
    // #5: dimensi skor via RPC satu-pintu (videos → fallback content_inventory) + bobot adaptif tenant.
    if (r?.run_id) {
      const { data: ts } = await supabase.rpc("get_run_topic_scores", { p_run_id: r.run_id });
      const t = ts as Record<string, number> | null;
      setDims(t && SCORE_DIMS.every((d) => typeof t[d] === "number") ? t : null);
    } else { setDims(null); }
    const { data: tc } = await supabase.from("tenant_configs").select("viral_score_weights").maybeSingle();
    setScoreW((tc as { viral_score_weights?: { weights?: Record<string, number> } } | null)?.viral_score_weights?.weights ?? null);
    setLoading(false);
  }, [supabase, id]);

  useEffect(() => { load(); }, [load]);

  // REALTIME live-tail: by queue_id (scheduled) ATAU run_id (direct job). RLS men-scope tenant.
  useEffect(() => {
    const col = run?.run_id ? "run_id" : run?.queue_id != null ? "queue_id" : null;
    const val = run?.run_id ? run.run_id : run?.queue_id != null ? String(run.queue_id) : null;
    if (!col || !val) return;
    const chan = supabase.channel(`rt-logs-${val}`)
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "pipeline_run_logs", filter: `${col}=eq.${val}` },
        (payload) => { setLogs((prev) => [...prev, payload.new as LogRow]); })
      .subscribe();
    return () => { supabase.removeChannel(chan); };
  }, [supabase, run?.queue_id, run?.run_id]);

  useEffect(() => { if (!pausedRef.current && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [logs]);

  if (loading) return <div className="muted" style={{ padding: "3rem", textAlign: "center" }}><span data-id>Memuat run…</span><span data-en>Loading run…</span></div>;
  if (!run) return (
    <div style={{ padding: "3rem", textAlign: "center" }}>
      <p className="muted"><span data-id>Run tidak ditemukan atau bukan milik Anda.</span><span data-en>Run not found or not yours.</span></p>
      <a href="/runs" className="btn btn-secondary btn-sm" style={{ marginTop: "0.75rem" }}><ArrowLeft size={14} /> Runs</a>
    </div>
  );

  const st = statusKey(run.status);
  const seen = new Set(logs.map((l) => { const s = (l.step || "").toLowerCase(); return STEP_DEFS.find((d) => s.includes(d.key))?.key; }).filter(Boolean) as string[]);
  // review = produk JADI (semua langkah selesai KECUALI publish — masih di buffer/ditinjau).
  const stepState = (key: string): StepState =>
    st === "completed" ? "completed"
    : st === "review" ? (key === "publish" ? "pending" : "completed")
    : seen.has(key) ? "completed" : "pending";
  const completed = STEP_DEFS.filter((d) => stepState(d.key) === "completed").length;
  const q = filter.toLowerCase();
  const shown = q ? logs.filter((l) => `${l.level} ${l.step} ${l.message}`.toLowerCase().includes(q)) : logs;
  // #5 komposisi skor viral: tiap dimensi (0-100) × bobot adaptif → kontribusi; urut kontribusi desc.
  const W = scoreW ?? BASELINE_WEIGHTS;
  const brk = dims ? SCORE_DIMS.map((d) => { const score = dims[d]; const weight = W[d] ?? BASELINE_WEIGHTS[d]; return { d, score, weight, contrib: score * weight }; }).sort((a, b) => b.contrib - a.contrib) : [];
  const brkTotal = brk.reduce((s, r) => s + r.contrib, 0);

  return (
    <>
      <div className="run-head">
        <a className="back-link" href="/runs"><ArrowLeft size={15} /><span data-id>Kembali ke Runs</span><span data-en>Back to runs</span></a>
        <div className="run-head-main">
          <div className="run-title-block">
            <span className="run-no">RUN #{run.id}</span>
            <h1 className="run-title">{run.run_metadata?.video_title || run.topic || "(tanpa judul)"}</h1>
            <div className="run-meta">
              <span className="mi"><Tag size={15} /> {prettyNiche(run.niche)}</span>
              <span className="mi"><Calendar size={15} /> {(() => { try { return new Date(run.created_at).toLocaleString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); } catch { return run.created_at; } })()}</span>
              <span className="mi"><Clock size={15} /> {fmtDur(run.elapsed_seconds)}</span>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", alignItems: "flex-end" }}>
            <span className={`status-lg ${st === "completed" ? "badge-success" : st === "review" ? "badge-warning" : st === "failed" ? "badge-error" : st === "running" ? "badge-running" : "badge-default"}`}>
              <span className="dot" style={{ width: 7, height: 7, borderRadius: "50%", background: "currentColor" }} />
              {st === "completed" ? <><span data-id>Selesai</span><span data-en>Completed</span></> : st === "review" ? <><span data-id>Perlu Ditinjau</span><span data-en>Needs Review</span></> : st === "discarded" ? <><span data-id>Dibuang</span><span data-en>Discarded</span></> : st === "failed" ? <><span data-id>Gagal</span><span data-en>Failed</span></> : st === "running" ? <><span data-id>Berjalan</span><span data-en>Running</span></> : <><span data-id>Antre</span><span data-en>Queued</span></>}
            </span>
            {/* Tempat tinjau (owner 2026-07-10): run direct qc_failed = video PRIVAT di YouTube (tombol
                "Buka YouTube" di bawah); run terjadwal = halaman /review (bila item masih hidup). */}
            {st === "review" && (
              <span className="muted" style={{ fontSize: "var(--text-xs)", textAlign: "right" }}>
                {run.youtube_url
                  ? <><span data-id>Tinjau videonya di YouTube Studio (terunggah privat) — tombol di bawah.</span><span data-en>Review the video in YouTube Studio (uploaded private) — button below.</span></>
                  : <><span data-id>Tinjau di <a className="link" href="/review">halaman Review</a> (bila masih tersedia — item usang dibuang otomatis).</span><span data-en>Review on the <a className="link" href="/review">Review page</a> (if still available — stale items auto-expire).</span></>}
              </span>
            )}
            <div className="run-actions">
              <button className="btn btn-secondary btn-sm" onClick={load}><RefreshCw size={15} /> <span data-id>Muat ulang</span><span data-en>Refresh</span></button>
              {run.youtube_url
                ? <a className="btn btn-outline btn-sm" style={{ color: "var(--yt)" }} href={run.youtube_url} target="_blank" rel="noreferrer"><ExternalLink size={15} /> <span data-id>Buka YouTube</span><span data-en>Open YouTube</span></a>
                : <button className="btn btn-secondary btn-sm" disabled style={{ color: "var(--yt)" }}><ExternalLink size={15} /> <span data-id>Buka YouTube</span><span data-en>Open YouTube</span></button>}
            </div>
          </div>
        </div>
      </div>

      {st === "review" && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", flexWrap: "wrap", padding: "0.875rem 1.25rem", background: "var(--warning-soft)", border: "1px solid color-mix(in srgb,var(--warning) 30%,transparent)", borderRadius: "var(--r-md)", marginBottom: "1rem" }}>
          <AlertTriangle size={16} style={{ color: "var(--warning)", flex: "none" }} />
          <span style={{ fontSize: "var(--text-sm)", flex: 1 }}><b><span data-id>Produk berhasil dibuat</span><span data-en>Product was produced</span></b> — <span data-id>ada catatan QC</span><span data-en>QC note</span>: {run.error_message || "—"}. <span data-id>Tinjau (pakai/buang) di halaman Perlu Ditinjau.</span><span data-en>Review (use/discard) on the Needs Review page.</span></span>
          <a href="/review" className="btn btn-secondary btn-sm"><Eye size={14} /> <span data-id>Tinjau</span><span data-en>Review</span></a>
        </div>
      )}

      {st === "discarded" && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", flexWrap: "wrap", padding: "0.875rem 1.25rem", background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: "var(--r-md)", marginBottom: "1rem" }}>
          <Trash2 size={16} style={{ color: "var(--text-muted)", flex: "none" }} />
          <span style={{ fontSize: "var(--text-sm)", flex: 1 }}><b><span data-id>Sudah dibuang</span><span data-en>Discarded</span></b> — <span data-id>konten ini Anda tolak saat tinjauan QC dan tidak dipublikasikan.</span><span data-en>you rejected this during QC review; it was not published.</span> {run.error_message ? <><span data-id>Catatan QC</span><span data-en>QC note</span>: {run.error_message}.</> : null}</span>
        </div>
      )}

      {st === "failed" && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", flexWrap: "wrap", padding: "0.875rem 1.25rem", background: "var(--error-soft)", border: "1px solid color-mix(in srgb,var(--error) 30%,transparent)", borderRadius: "var(--r-md)", marginBottom: "1rem" }}>
          <AlertTriangle size={16} style={{ color: "var(--error)", flex: "none" }} />
          <span style={{ fontSize: "var(--text-sm)", flex: 1 }}>{run.error_message || "Produksi gagal."}</span>
          <button className="btn btn-secondary btn-sm" onClick={retry} disabled={!run.channel_id} title={run.channel_id ? "Produksi ulang job ini" : "Channel tak diketahui"}><RefreshCw size={14} /> <span data-id>Jalankan ulang</span><span data-en>Re-run</span></button>
          {retryMsg && <span style={{ flexBasis: "100%", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>{retryMsg}</span>}
        </div>
      )}

      <div className="run-grid">
        {/* LEFT: pipeline (derivasi status/log) */}
        <div className="card card-pad">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
            <h3 className="rail-title" style={{ margin: 0 }}><span data-id>Pipeline · 8 langkah</span><span data-en>Pipeline · 8 steps</span></h3>
            <span className="badge badge-brand">{completed} / 8</span>
          </div>
          <div className="pl">
            {STEP_DEFS.map((s, i) => {
              const stt = stepState(s.key);
              return (
                <div key={i} className="pl-step" data-state={stt}>
                  <div className="pl-marker"><span className="pl-node"><NodeIcon state={stt} icon={s.icon} /></span><span className="pl-line" /></div>
                  <div className="pl-body"><div className="pl-row1"><span className="pl-name" data-id>{s.id}</span><span className="pl-name" data-en>{s.en}</span></div></div>
                </div>
              );
            })}
          </div>
        </div>

        {/* CENTER: log NYATA + realtime */}
        <div className="card log-card">
          <div className="log-toolbar">
            <div className="log-search"><Search size={13} /><input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter log…" /></div>
            <button className="btn btn-ghost btn-sm" onClick={() => setPaused((p) => !p)}>{paused ? <Play size={14} /> : <Pause size={14} />} <span>{paused ? "Lanjut" : "Jeda"}</span></button>
          </div>
          <div className="log-body" ref={logRef}>
            {shown.length === 0
              ? <div className="muted" style={{ padding: "1.5rem", fontSize: "var(--text-sm)" }}><span data-id>Belum ada log untuk run ini. Log live muncul saat worker memproduksi.</span><span data-en>No logs for this run yet. Live logs appear while the worker produces.</span></div>
              : shown.map((l, i) => (
                <div key={l.id ?? i} className={`log-line lvl-${lvlClass(l.level, l.category)}`}>
                  <span className="log-ts">{hhmmss(l.created_at)}</span><span className="log-lvl">{lvlClass(l.level, l.category)}</span><span className="log-msg">{l.message}</span>
                </div>
              ))}
          </div>
          <div className="log-foot">
            <span className="live-dot" style={{ background: st === "running" ? "var(--st-running)" : "var(--success)", animationPlayState: paused ? "paused" : "running" }} />
            <span>{st === "running" ? (paused ? "Dijeda" : "Live · mengikuti output") : "Log historis"}</span>
            <span style={{ marginLeft: "auto" }}>{logs.length} baris</span>
          </div>
        </div>

        {/* RIGHT: rail (jujur) */}
        <div className="rail">
          <div className="card card-pad">
            <h3 className="rail-title"><span data-id>Output</span><span data-en>Output</span></h3>
            <div className="meta-row"><span className="k">Viral score</span><span className="v">{run.viral_score ?? "—"}</span></div>
            <div className="meta-row"><span className="k"><span data-id>Waktu proses</span><span data-en>Process time</span></span><span className="v">{fmtDur(run.elapsed_seconds)}</span></div>
            <div className="meta-row"><span className="k">YouTube</span><span className="v">{run.youtube_url ? <a className="link" href={run.youtube_url} target="_blank" rel="noreferrer">buka</a> : "—"}</span></div>
            <div className="meta-row"><span className="k">LLM</span><span className="v">{run.llm_provider || "—"}</span></div>
          </div>
          <div className="card card-pad">
            <h3 className="rail-title"><span data-id>Komposisi skor viral</span><span data-en>Viral score breakdown</span></h3>
            {brk.length > 0 ? (
              <>
                <p className="muted" style={{ fontSize: "var(--text-xs)", margin: "0 0 0.75rem", lineHeight: 1.5 }}>
                  <span data-id>Skor disusun dari 5 sinyal, masing-masing dikali bobot yang dipelajari mesin.</span>
                  <span data-en>The score is built from 5 signals, each times the engine-learned weight.</span>
                </p>
                {brk.map((r) => (
                  <div key={r.d} style={{ marginBottom: "0.625rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", marginBottom: "0.25rem" }}>
                      <span style={{ color: "var(--text-secondary)" }}>{DIM_LABEL[r.d] ? <><span data-id>{DIM_LABEL[r.d].id}</span><span data-en>{DIM_LABEL[r.d].en}</span></> : r.d}</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>+{r.contrib.toFixed(1)}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <div className="progress" style={{ flex: 1 }}><span style={{ width: `${Math.min(100, r.score)}%` }} /></div>
                      <span className="muted" style={{ fontSize: "0.65rem", whiteSpace: "nowrap" }}>{r.score} × {(r.weight * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
                <div className="meta-row" style={{ borderTop: "1px solid var(--border)", marginTop: "0.5rem", paddingTop: "0.5rem" }}>
                  <span className="k"><span data-id>Total skor</span><span data-en>Total score</span></span>
                  <span className="v" style={{ fontSize: "var(--text-sm)", fontWeight: 700 }}>{brkTotal.toFixed(1)}</span>
                </div>
                {run.viral_score != null && Math.abs(brkTotal - Number(run.viral_score)) >= 1.5 && (
                  <p className="muted" style={{ fontSize: "0.65rem", margin: "0.4rem 0 0", lineHeight: 1.45 }}>
                    <span data-id>Tercatat saat produksi: {run.viral_score}. Selisih kecil = formula mesin terus belajar.</span>
                    <span data-en>Recorded at production: {run.viral_score}. Small gap = the engine keeps learning.</span>
                  </p>
                )}
              </>
            ) : (
              <p className="muted" style={{ fontSize: "var(--text-xs)", margin: 0, lineHeight: 1.5 }}>
                <span data-id>Rincian belum tersedia untuk run ini (tidak ada data dimensi skor).</span>
                <span data-en>Breakdown not available for this run (no score dimension data).</span>
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
