"use client";

import { useEffect, useState } from "react";
import {
  Download, Zap, Tv, ChevronDown, Calendar, Filter, ChevronLeft, ChevronRight,
  MoreHorizontal, X, RefreshCw, ArrowRight, Check, Loader2, Clock, type LucideIcon,
} from "lucide-react";
import "./runs-list.css";

// D4 Runs List (PoC) — port dari design-source/Runs.html. Mock data deterministik
// (tanpa Math.random → aman hydration). Filter status + drawer slide-in → /runs/[id].

type StKey = "completed" | "running" | "failed" | "queued";
const CH = {
  ms: { name: "Misteri Samudra", niche: "Misteri Samudra", c: "#1d4ed8", i: "MS" },
  js: { name: "Jejak Kelam Sejarah", niche: "Sejarah Kelam", c: "#9f1239", i: "JS" },
  fb: { name: "Fakta Yang Bikin Mikir", niche: "Fakta Menarik", c: "#047857", i: "FB" },
} as const;
type ChKey = keyof typeof CH;

type Run = { id: number; ck: ChKey; topic: string; st: StKey; dur: string; views: string; start: string; cost: string };

const DATA: Run[] = [
  { id: 97, ck: "ms", topic: "Kapal Hilang di Segitiga Bermuda", st: "running", dur: "berjalan…", views: "—", start: "10 Jun · 14:02 WIB", cost: "—" },
  { id: 96, ck: "fb", topic: "Kenapa Otak Lupa Mimpi?", st: "queued", dur: "—", views: "—", start: "10 Jun · 13:48 WIB", cost: "—" },
  { id: 95, ck: "js", topic: "Penjara Bawah Tanah Romawi Kuno", st: "completed", dur: "1m 12s", views: "12.4K", start: "10 Jun · 13:15 WIB", cost: "$0.31" },
  { id: 94, ck: "ms", topic: "Suara Misterius dari Palung Mariana", st: "failed", dur: "timeout", views: "—", start: "10 Jun · 12:40 WIB", cost: "—" },
  { id: 93, ck: "fb", topic: "Mengapa Kucing Takut Timun", st: "completed", dur: "0m 58s", views: "33.1K", start: "10 Jun · 11:30 WIB", cost: "$0.28" },
  { id: 92, ck: "js", topic: "Suku yang Hilang di Amazon", st: "completed", dur: "1m 18s", views: "8.7K", start: "10 Jun · 10:55 WIB", cost: "$0.34" },
  { id: 91, ck: "ms", topic: "Kota Atlantis yang Tak Pernah Ditemukan", st: "completed", dur: "1m 05s", views: "21.9K", start: "10 Jun · 10:02 WIB", cost: "$0.30" },
  { id: 90, ck: "fb", topic: "Fakta Aneh tentang Madu", st: "completed", dur: "0m 52s", views: "14.2K", start: "10 Jun · 09:18 WIB", cost: "$0.27" },
  { id: 89, ck: "js", topic: "Ritual Terlarang Kekaisaran Maya", st: "completed", dur: "1m 21s", views: "9.3K", start: "10 Jun · 08:40 WIB", cost: "$0.35" },
  { id: 88, ck: "ms", topic: "Makhluk Raksasa Laut Dalam", st: "completed", dur: "1m 09s", views: "27.5K", start: "09 Jun · 19:30 WIB", cost: "$0.32" },
  { id: 87, ck: "fb", topic: "Kenapa Langit Malam Gelap", st: "completed", dur: "0m 49s", views: "11.8K", start: "09 Jun · 14:10 WIB", cost: "$0.26" },
  { id: 86, ck: "js", topic: "Wabah yang Hampir Memusnahkan Eropa", st: "completed", dur: "1m 15s", views: "18.0K", start: "09 Jun · 10:05 WIB", cost: "$0.33" },
  { id: 85, ck: "ms", topic: "Kenapa 95% Lautan Belum Dipetakan", st: "completed", dur: "1m 02s", views: "24.6K", start: "08 Jun · 19:22 WIB", cost: "$0.29" },
  { id: 84, ck: "fb", topic: "Hal yang Terjadi saat Kita Tidur", st: "completed", dur: "0m 57s", views: "16.4K", start: "08 Jun · 14:00 WIB", cost: "$0.28" },
];

const STATUS_TABS: { key: StKey | "all"; id: string; en: string }[] = [
  { key: "all", id: "Semua", en: "All" },
  { key: "completed", id: "Completed", en: "Completed" },
  { key: "running", id: "Running", en: "Running" },
  { key: "failed", id: "Failed", en: "Failed" },
  { key: "queued", id: "Queued", en: "Queued" },
];

function Badge({ st }: { st: StKey }) {
  const m: Record<StKey, [string, string]> = {
    completed: ["badge-success", "Completed"], running: ["badge-running", "Running"],
    failed: ["badge-error", "Failed"], queued: ["badge-default", "Queued"],
  };
  const [c, l] = m[st];
  return <span className={`badge ${c}`}><span className="dot" />{l}</span>;
}

const PL_NAMES = ["Trend Radar", "Topic Select", "Script", "Hook", "TTS", "Visual", "Render", "Publish"];
const STEP_ICON: Record<string, [string, string, LucideIcon]> = {
  done: ["var(--success)", "var(--success-soft)", Check],
  run: ["var(--info)", "var(--info-soft)", Loader2],
  fail: ["var(--error)", "var(--error-soft)", X],
  pend: ["var(--text-muted)", "var(--surface-2)", Clock],
};

export default function RunsListPage() {
  const [filter, setFilter] = useState<StKey | "all">("all");
  const [selected, setSelected] = useState<Run | null>(null);

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => { if (e.key === "Escape") setSelected(null); };
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, []);

  const rows = DATA.filter((d) => filter === "all" || d.st === filter);
  const done = DATA.filter((d) => d.st === "completed").length;
  const fail = DATA.filter((d) => d.st === "failed").length;

  function miniSteps(st: StKey) {
    const activeCount = st === "completed" ? 8 : st === "running" ? 6 : st === "failed" ? 5 : 0;
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
          <div className="sub" dangerouslySetInnerHTML={{ __html: `<b>${done}</b> run sukses · <b>${fail}</b> gagal hari ini` }} />
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-secondary"><Download size={15} /> Export CSV</button>
          <button className="btn btn-ai"><Zap size={15} /> <span data-id>Jalankan Sekarang</span><span data-en>Run Now</span></button>
        </div>
      </div>

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
              <th className="sortable num">Durasi</th><th className="sortable num">Views</th><th>Started</th><th></th>
            </tr></thead>
            <tbody>
              {rows.map((d) => {
                const c = CH[d.ck];
                return (
                  <tr key={d.id} onClick={() => setSelected(d)}>
                    <td><span className="runid">#{d.id}</span></td>
                    <td><span className="ch-cell"><span className="ch-dot" style={{ background: c.c }}>{c.i}</span>{c.name}</span></td>
                    <td><span className="muted">{c.niche}</span></td>
                    <td><div className="topic-cell">{d.topic}</div></td>
                    <td><Badge st={d.st} /></td>
                    <td className="num mono" style={{ fontSize: "var(--text-xs)" }}>{d.dur}</td>
                    <td className="num">{d.views !== "—" ? <b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{d.views}</b> : <span className="muted">—</span>}</td>
                    <td><span className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{d.start}</span></td>
                    <td><button className="btn btn-ghost btn-icon btn-sm" onClick={(e) => e.stopPropagation()}><MoreHorizontal size={14} /></button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="pager">
          <span>Menampilkan {rows.length} dari {DATA.length} run</span>
          <div className="pages">
            <button><ChevronLeft size={14} /></button>
            <button className="active">1</button><button>2</button><button>3</button>
            <button><ChevronRight size={14} /></button>
          </div>
        </div>
      </div>

      {/* drawer */}
      <div className={`scrim${selected ? " open" : ""}`} onClick={() => setSelected(null)} />
      <aside className={`drawer${selected ? " open" : ""}`}>
        {selected && (() => {
          const c = CH[selected.ck];
          return (
            <>
              <div className="drawer-head">
                <div>
                  <div className="runid">RUN #{selected.id}</div>
                  <div style={{ fontSize: "var(--text-lg)", fontWeight: 600, letterSpacing: "-0.01em", marginTop: 2 }}>{selected.topic}</div>
                  <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: 4 }}>{c.name} · {c.niche}</div>
                </div>
                <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSelected(null)}><X size={16} /></button>
              </div>
              <div className="drawer-body">
                <div><Badge st={selected.st} /></div>
                <div>
                  <div className="sec-label"><span data-id>Ringkasan</span><span data-en>Summary</span></div>
                  <div className="kv"><span className="k">Durasi</span><span className="v">{selected.dur}</span></div>
                  <div className="kv"><span className="k">Views (post-publish)</span><span className="v">{selected.views}</span></div>
                  <div className="kv"><span className="k">Biaya AI</span><span className="v">{selected.cost}</span></div>
                  <div className="kv"><span className="k">Mulai</span><span className="v">{selected.start}</span></div>
                </div>
                <div>
                  <div className="sec-label">Pipeline</div>
                  <div>{miniSteps(selected.st)}</div>
                </div>
              </div>
              <div className="drawer-foot">
                <a href={`/runs/${selected.id}`} className="btn btn-default" style={{ flex: 1 }}>
                  <span data-id>Buka run lengkap</span><span data-en>Open full run</span> <ArrowRight size={15} />
                </a>
                <button className="btn btn-secondary"><RefreshCw size={15} /></button>
              </div>
            </>
          );
        })()}
      </aside>
    </>
  );
}
