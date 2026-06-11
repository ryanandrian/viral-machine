"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft, Tv, Tag, Calendar, Clock, RefreshCw, Download, Upload, ExternalLink,
  Search, Pause, Play, FileText, Send,
  Radar, Target, Sparkles, AudioLines, Image as ImageIcon, Film,
  Check, Loader2, X, type LucideIcon,
} from "lucide-react";
import "./run-detail.css";

// D5 Run Detail (PoC) — port dari design-source/Run Detail.html.
// Mock data + simulasi live (pipeline state + log streaming). Backend (Supabase Realtime) menyusul.
// Ikon pipeline custom (pl-*) dipetakan ke lucide; brand provider (Anthropic/ElevenLabs/OpenAI)
// pakai kotak warna+inisial (lucide tak punya brand mark).

type StepState = "completed" | "running" | "pending" | "failed";
type Prov = { color: string; letter: string; label: string };
type Step = {
  icon: LucideIcon; id: string; en: string; subId: string; subEn: string;
  dur: string; state: StepState; prov?: Prov; progress?: number;
};
type Lvl = "INFO" | "OK" | "WARN" | "ERR" | "STEP";
type Line = { ts: string; lvl: Lvl; msg: string; isNew?: boolean };

const P = {
  anthropic: (label: string): Prov => ({ color: "var(--anthropic)", letter: "A", label }),
  elevenlabs: (label: string): Prov => ({ color: "var(--elevenlabs)", letter: "11", label }),
  openai: (label: string): Prov => ({ color: "var(--openai)", letter: "AI", label }),
};

const INITIAL_STEPS: Step[] = [
  { icon: Radar, id: "Trend Radar", en: "Trend Radar", subId: "240 topik tren dipindai", subEn: "240 trending topics scanned", dur: "8s", state: "completed" },
  { icon: Target, id: "Topic Select", en: "Topic Select", subId: "Emotion score 8.7/10", subEn: "Emotion score 8.7/10", dur: "4s", state: "completed" },
  { icon: FileText, id: "Script Generate", en: "Script Generate", subId: "412 kata · 3 hook", subEn: "412 words · 3 hooks", dur: "18s", state: "completed", prov: P.anthropic("Claude Sonnet 4.6") },
  { icon: Sparkles, id: "Hook Optimize", en: "Hook Optimize", subId: "Hook 'gap question' dipilih", subEn: "'Gap question' hook chosen", dur: "6s", state: "completed", prov: P.anthropic("Claude Haiku 4.5") },
  { icon: AudioLines, id: "TTS Audio", en: "TTS Audio", subId: "58s audio · voice Arya", subEn: "58s audio · voice Arya", dur: "22s", state: "completed", prov: P.elevenlabs("Multilingual v2") },
  { icon: ImageIcon, id: "Visual Assemble", en: "Visual Assemble", subId: "6 klip dibuat", subEn: "6 clips generated", dur: "running", state: "running", prov: P.openai("gpt-image-1-mini"), progress: 55 },
  { icon: Film, id: "Video Render", en: "Video Render", subId: "Compose & encode", subEn: "Compose & encode", dur: "—", state: "pending" },
  { icon: Upload, id: "Publish YouTube", en: "Publish YouTube", subId: "Upload + metadata", subEn: "Upload + metadata", dur: "—", state: "pending" },
];

const SEED: Line[] = [
  ["14:02:01", "STEP", "── Trend Radar ──"], ["14:02:01", "INFO", "Memindai 240 topik tren dari 6 kategori"],
  ["14:02:08", "OK", "Topik kandidat: 12 · skor tertinggi 8.7"], ["14:02:09", "STEP", "── Topic Select ──"],
  ["14:02:09", "INFO", 'Topik terpilih: "Kapal Hilang di Segitiga Bermuda"'], ["14:02:13", "OK", "Emotion score 8.7/10 · curiosity gap terdeteksi"],
  ["14:02:14", "STEP", "── Script Generate (Claude Sonnet 4.6) ──"], ["14:02:14", "INFO", "Prompt 1.2K token · target 60 detik"],
  ["14:02:28", "WARN", "Retry 1× karena rate-limit Anthropic (429)"], ["14:02:32", "OK", "Script: 412 kata · 3 hook variant dihasilkan"],
  ["14:02:33", "STEP", "── Hook Optimize (Claude Haiku 4.5) ──"], ["14:02:39", "OK", "Hook 'gap question' dipilih (prediksi CTR 8.9%)"],
  ["14:02:40", "STEP", "── TTS Audio (ElevenLabs Multilingual v2) ──"], ["14:03:02", "OK", "Audio 58.2s di-render · 0.94 MB"],
  ["14:03:03", "STEP", "── Visual Assemble (gpt-image-1-mini) ──"], ["14:03:06", "INFO", "Klip 1/6: kapal di laut berkabut … OK"],
  ["14:03:09", "INFO", "Klip 2/6: peta Segitiga Bermuda … OK"], ["14:03:12", "INFO", "Klip 3/6: radar AL 1945 … OK"],
].map(([ts, lvl, msg]) => ({ ts, lvl: lvl as Lvl, msg }));

type Meta = { step?: number; start?: boolean; done?: boolean; filesize?: string; published?: boolean; finished?: boolean };
const STREAM: { line: Line; meta?: Meta }[] = [
  { line: { ts: "14:03:15", lvl: "INFO", msg: "Klip 4/6: pesawat lenyap … OK" } },
  { line: { ts: "14:03:18", lvl: "INFO", msg: "Klip 5/6: gelombang laut malam … OK" } },
  { line: { ts: "14:03:21", lvl: "INFO", msg: "Klip 6/6: pertanyaan penutup … OK" } },
  { line: { ts: "14:03:22", lvl: "OK", msg: "6/6 klip selesai · diversity check lolos" }, meta: { step: 5, done: true } },
  { line: { ts: "14:03:23", lvl: "STEP", msg: "── Video Render ──" }, meta: { step: 6, start: true } },
  { line: { ts: "14:03:23", lvl: "INFO", msg: "Menyusun timeline · audio + 6 klip + captions" } },
  { line: { ts: "14:03:26", lvl: "INFO", msg: "Encode H.264 1080×1920 @30fps" } },
  { line: { ts: "14:03:34", lvl: "OK", msg: "Render selesai · 0:58 · 8.4 MB" }, meta: { step: 6, done: true, filesize: "8.4 MB" } },
  { line: { ts: "14:03:35", lvl: "STEP", msg: "── Publish YouTube ──" }, meta: { step: 7, start: true } },
  { line: { ts: "14:03:40", lvl: "INFO", msg: "Set judul, deskripsi, 8 hashtag, thumbnail" } },
  { line: { ts: "14:03:42", lvl: "OK", msg: "Published ✓ youtu.be/dQw4w9 · status: public" }, meta: { step: 7, done: true, published: true } },
  { line: { ts: "14:03:42", lvl: "STEP", msg: "✓ Run #97 selesai · 1m 41s · $0.34" }, meta: { finished: true } },
];

const DONE_DUR = ["", "", "", "", "", "12s", "11s", "7s"];

function NodeIcon({ step }: { step: Step }) {
  if (step.state === "pending") { const I = step.icon; return <I size={18} />; }
  if (step.state === "running") return <Loader2 size={18} />;
  if (step.state === "failed") return <X size={18} />;
  return <Check size={18} />;
}

export default function RunDetailPage() {
  const [steps, setSteps] = useState<Step[]>(INITIAL_STEPS);
  const [lines, setLines] = useState<Line[]>(SEED);
  const [selected, setSelected] = useState<number | null>(null);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState("");
  const [finished, setFinished] = useState(false);
  const [thumbReady, setThumbReady] = useState(false);
  const [filesize, setFilesize] = useState("—");
  const [published, setPublished] = useState(false);
  const [totalDur, setTotalDur] = useState("1m 18s");

  const pausedRef = useRef(paused);
  pausedRef.current = paused;
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let si = 0;
    let timer: ReturnType<typeof setTimeout>;
    const run = () => {
      if (si >= STREAM.length) return;
      if (pausedRef.current) { timer = setTimeout(run, 600); return; }
      const { line, meta } = STREAM[si++];
      setLines((prev) => [...prev, { ...line, isNew: true }]);
      if (meta) {
        if (meta.step != null && meta.done) {
          setSteps((p) => p.map((s, i) => i === meta.step ? { ...s, state: "completed", dur: DONE_DUR[meta.step!] || "10s" } : s));
        }
        if (meta.step != null && meta.start) {
          setSteps((p) => p.map((s, i) => i === meta.step ? { ...s, state: "running", dur: "running" } : s));
        }
        if (meta.step === 5 && meta.done) setThumbReady(true);
        if (meta.filesize) setFilesize(meta.filesize);
        if (meta.published) setPublished(true);
        if (meta.finished) {
          setSteps((p) => p.map((s, i) => i === 7 ? { ...s, state: "completed", dur: "7s" } : s));
          setFinished(true);
          setTotalDur("1m 41s");
        }
      }
      const delay = line.lvl === "STEP" ? 700 : 900 + Math.random() * 900;
      timer = setTimeout(run, delay);
    };
    timer = setTimeout(run, 1800);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!paused && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [lines, paused]);

  const completed = steps.filter((s) => s.state === "completed").length;
  const q = filter.toLowerCase();
  const shown = q ? lines.filter((l) => `${l.ts} ${l.lvl} ${l.msg}`.toLowerCase().includes(q)) : lines;

  return (
    <>
      <div className="run-head">
        <a className="back-link" href="/runs"><ArrowLeft size={15} /><span data-id>Kembali ke Runs</span><span data-en>Back to runs</span></a>
        <div className="run-head-main">
          <div className="run-title-block">
            <span className="run-no">RUN #97</span>
            <h1 className="run-title">Kapal Hilang di Segitiga Bermuda</h1>
            <div className="run-meta">
              <span className="mi"><Tv size={15} /> Misteri Samudra</span>
              <span className="mi"><Tag size={15} /> Niche: Misteri Samudra</span>
              <span className="mi"><Calendar size={15} /> 10 Jun 2026 · 14:02 WIB</span>
              <span className="mi"><Clock size={15} /> {totalDur}</span>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", alignItems: "flex-end" }}>
            <span className={`status-lg ${finished ? "badge-success" : "badge-running"}`}>
              <span className="dot" style={{ width: 7, height: 7, borderRadius: "50%", background: "currentColor" }} />
              {finished ? <><span data-id>Selesai</span><span data-en>Completed</span></> : <><span data-id>Sedang berjalan</span><span data-en>Running</span></>}
            </span>
            <div className="run-actions">
              <button className="btn btn-secondary btn-sm"><RefreshCw size={15} /> <span data-id>Jalankan ulang</span><span data-en>Re-run</span></button>
              <button className="btn btn-secondary btn-sm"><Download size={15} /> <span data-id>Unduh log</span><span data-en>Download log</span></button>
              <button className={`btn btn-sm ${published ? "btn-outline" : "btn-secondary"}`} disabled={!published} style={{ color: "var(--yt)" }}>
                <ExternalLink size={15} /> <span data-id>Buka YouTube</span><span data-en>Open YouTube</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="run-grid">
        {/* LEFT: pipeline */}
        <div className="card card-pad">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
            <h3 className="rail-title" style={{ margin: 0 }}><span data-id>Pipeline · 8 langkah</span><span data-en>Pipeline · 8 steps</span></h3>
            <span className="badge badge-brand">{completed} / 8</span>
          </div>
          <div className="pl">
            {steps.map((s, i) => (
              <div key={i} className={`pl-step${selected === i ? " sel" : ""}`} data-state={s.state} onClick={() => setSelected(i)}>
                <div className="pl-marker"><span className="pl-node"><NodeIcon step={s} /></span><span className="pl-line" /></div>
                <div className="pl-body">
                  <div className="pl-row1">
                    <span className="pl-name" data-id>{s.id}</span><span className="pl-name" data-en>{s.en}</span>
                    <span className="pl-dur">{s.dur === "running" ? <span style={{ color: "var(--st-running)" }}>berjalan…</span> : s.dur}</span>
                  </div>
                  <div className="pl-sub">
                    {s.prov && (
                      <span className="pl-provider" style={{ color: s.prov.color }}>
                        <span style={{ width: 8, height: 8, borderRadius: 2, background: s.prov.color, display: "inline-block" }} />
                        <span style={{ color: "var(--text-secondary)" }}>{s.prov.label}</span>
                      </span>
                    )}
                    <span data-id>{s.subId}</span><span data-en>{s.subEn}</span>
                  </div>
                  {s.state === "running" && s.progress != null && (
                    <div className="pl-progress"><span style={{ width: `${s.progress}%` }} /></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER: log */}
        <div className="card log-card">
          <div className="log-toolbar">
            <div className="log-search"><Search size={13} /><input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter log…" /></div>
            <button className="btn btn-ghost btn-sm" onClick={() => setPaused((p) => !p)}>
              {paused ? <Play size={14} /> : <Pause size={14} />} <span>{paused ? "Lanjut" : "Jeda"}</span>
            </button>
            <button className="btn btn-ghost btn-icon btn-sm tip" data-tip="Download full log"><Download size={14} /></button>
          </div>
          <div className="log-body" ref={logRef}>
            {shown.map((l, i) => (
              <div key={i} className={`log-line lvl-${l.lvl}${l.isNew ? " new" : ""}`}>
                <span className="log-ts">{l.ts}</span><span className="log-lvl">{l.lvl}</span><span className="log-msg">{l.msg}</span>
              </div>
            ))}
          </div>
          <div className="log-foot">
            <span className="live-dot" style={{ background: finished ? "var(--success)" : "var(--st-running)", animationPlayState: paused ? "paused" : "running" }} />
            <span>{finished ? "Selesai · output lengkap" : paused ? "Dijeda" : "Live · mengikuti output"}</span>
            <span style={{ marginLeft: "auto" }}>{lines.length} baris</span>
          </div>
        </div>

        {/* RIGHT: rail */}
        <div className="rail">
          <div className="card card-pad">
            <h3 className="rail-title"><span data-id>Output</span><span data-en>Output</span></h3>
            <div className="thumb">
              {!thumbReady && (
                <div className="pending-overlay"><ImageIcon size={26} />
                  <span style={{ fontSize: "var(--text-xs)" }} data-id>Menunggu hook frame…</span>
                  <span style={{ fontSize: "var(--text-xs)" }} data-en>Awaiting hook frame…</span>
                </div>
              )}
              <div className="vignette" />
              <div className="hook-text">Kenapa kapal ini hilang tanpa jejak?</div>
            </div>
            <div style={{ marginTop: "0.875rem" }}>
              <div className="meta-row"><span className="k">Durasi video</span><span className="v">0:58</span></div>
              <div className="meta-row"><span className="k">Resolusi</span><span className="v">1080×1920</span></div>
              <div className="meta-row"><span className="k">Ukuran file</span><span className="v">{filesize}</span></div>
              <div className="meta-row"><span className="k">Views</span><span className="v">{published ? "0 (baru)" : "—"}</span></div>
            </div>
            <hr className="hr" style={{ margin: "0.75rem 0" }} />
            <details>
              <summary style={{ cursor: "pointer", fontSize: "var(--text-xs)", color: "var(--text-secondary)", listStyle: "none", display: "flex", alignItems: "center", gap: "0.375rem" }}>
                <FileText size={14} /> <span data-id>Preview script</span><span data-en>Script preview</span>
              </summary>
              <p style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", lineHeight: 1.6, margin: "0.625rem 0 0" }}>
                Tahun 1945, lima pesawat Angkatan Laut AS lenyap di area ini. Tak ada puing. Tak ada sinyal. Hanya keheningan… Apa yang sebenarnya terjadi di Segitiga Bermuda?
              </p>
            </details>
          </div>

          <div className="card card-pad">
            <h3 className="rail-title"><span data-id>Rincian biaya</span><span data-en>Cost breakdown</span></h3>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
              <span style={{ fontSize: "var(--text-3xl)", fontWeight: 700, letterSpacing: "-0.02em" }}>$0.34</span>
              <span className="muted" style={{ fontSize: "var(--text-sm)" }}>≈ Rp 5.500</span>
            </div>
            <div className="cost-bar">
              <span style={{ background: "var(--anthropic)", width: "21%" }} />
              <span style={{ background: "var(--elevenlabs)", width: "53%" }} />
              <span style={{ background: "var(--openai)", width: "26%" }} />
            </div>
            <div className="cost-legend">
              <div className="cost-item"><span className="sw" style={{ background: "var(--anthropic)" }} /><span className="nm">Claude</span><span className="amt">$0.07</span></div>
              <div className="cost-item"><span className="sw" style={{ background: "var(--elevenlabs)" }} /><span className="nm">ElevenLabs</span><span className="amt">$0.18</span></div>
              <div className="cost-item"><span className="sw" style={{ background: "var(--openai)" }} /><span className="nm">OpenAI</span><span className="amt">$0.09</span></div>
            </div>
          </div>

          <div className="card card-pad">
            <h3 className="rail-title"><span data-id>AI providers</span><span data-en>AI providers</span></h3>
            {[
              { p: P.anthropic("Claude Sonnet 4.6"), task: "Script generate" },
              { p: P.anthropic("Claude Haiku 4.5"), task: "Hook & utility" },
              { p: P.elevenlabs("Multilingual v2"), task: "Voice: Arya · TTS" },
              { p: P.openai("gpt-image-1-mini"), task: "Visual assemble" },
            ].map((x, i) => (
              <div className="prov-item" key={i}>
                <span className="prov-ic" style={{ background: x.p.color, color: "#fff" }}>{x.p.letter}</span>
                <div className="prov-meta"><div className="nm">{x.p.label}</div><div className="task">{x.task}</div></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* telegram */}
      {finished && (
        <div className="tg-card">
          <h3 className="rail-title"><span data-id>Notifikasi Telegram terkirim</span><span data-en>Telegram notification sent</span></h3>
          <div className="tg-bubble">
            <div className="tg-head"><span className="tg-av"><Send size={16} /></span><span className="tg-name">MesinViral Bot</span><span className="tg-time">14:03 WIB</span></div>
            <div className="tg-body">✅ <b>Run #97 published</b><br />Misteri Samudra · &quot;Kapal Hilang di Segitiga Bermuda&quot;<br />⏱ 1m 24s · 💰 $0.34 · 🎬 0:58<br />🔗 youtu.be/dQw4w9</div>
          </div>
        </div>
      )}
    </>
  );
}
