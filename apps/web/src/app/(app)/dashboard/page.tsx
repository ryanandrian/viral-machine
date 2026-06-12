"use client";

import { Zap, Play, CheckCircle, Eye, Users, ArrowUp, TrendingUp, Calendar, ExternalLink, ArrowRight, MoreVertical, List, Gauge as GaugeIcon, DollarSign, Sparkles, Activity, Check, Loader2, X, ChevronRight } from "lucide-react";
import "./dashboard.css";

// D1 Main Dashboard — port dari design-source/Main Dashboard.html (Hybrid).
// Hub utama pasca-login. Chart = SVG hand-drawn (spark + gauge), TANPA chart lib — konsisten D20.
// Data mock deterministik (SSR-safe, no Math.random). Data nyata = Supabase Phase 4+ (lihat guardrail v1/v2).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

// ---- sparkline (port dari logic data-spark di HTML) ----
function Spark({ data, color }: { data: number[]; color: string }) {
  const W = 120, H = 30, max = Math.max(...data), min = Math.min(...data);
  const x = (i: number) => i * (W / (data.length - 1));
  const y = (v: number) => H - 2 - ((v - min) / ((max - min) || 1)) * (H - 6);
  const line = data.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} width="100%" height={30}>
      <path d={line} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" />
      <circle cx={x(data.length - 1)} cy={y(data[data.length - 1])} r={2.6} fill={color} />
    </svg>
  );
}

// ---- gauge (final state, SSR-safe — tanpa animasi opacity:0) ----
function Gauge() {
  const score = 86, r = 48, c = 2 * Math.PI * r, off = c * (1 - score / 100);
  return (
    <svg viewBox="0 0 120 120" width={116} height={116}>
      <circle cx={60} cy={60} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={9} />
      <circle cx={60} cy={60} r={r} fill="none" stroke="#10B981" strokeWidth={9} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 60 60)" />
      <text x={60} y={58} textAnchor="middle" fontSize={28} fontWeight={700} fill="var(--text-primary)" fontFamily="Geist">{score}</text>
      <text x={60} y={76} textAnchor="middle" fontSize={10} fill="var(--text-muted)" fontFamily="Geist">/ 100 · Aman</text>
    </svg>
  );
}

type RunSt = "completed" | "running" | "failed";
const RUNS: { id: number; st: RunSt; topic: string; ch: string; dur: string; views: string }[] = [
  { id: 97, st: "completed", topic: "Kapal Hilang di Segitiga Bermuda", ch: "Misteri Samudra", dur: "1m 24s", views: "12.4K" },
  { id: 96, st: "completed", topic: "Penjara Bawah Tanah Romawi Kuno", ch: "Jejak Kelam Sejarah", dur: "1m 31s", views: "8.1K" },
  { id: 98, st: "running", topic: "Suara Misterius dari Palung Mariana", ch: "Misteri Samudra", dur: "berjalan…", views: "—" },
  { id: 94, st: "completed", topic: "Kenapa Otak Lupa Mimpi?", ch: "Fakta Yang Bikin Mikir", dur: "1m 12s", views: "21.7K" },
  { id: 95, st: "failed", topic: "Misteri Suku yang Hilang di Amazon", ch: "Jejak Kelam Sejarah", dur: "timeout TTS", views: "—" },
];
const ST_MAP: Record<RunSt, { Icon: typeof Check; c: string; bg: string }> = {
  completed: { Icon: Check, c: "var(--success)", bg: "var(--success-soft)" },
  running: { Icon: Loader2, c: "var(--info)", bg: "var(--info-soft)" },
  failed: { Icon: X, c: "var(--error)", bg: "var(--error-soft)" },
};

const FEED: { c: string; id: string; en: string; t: string }[] = [
  { c: "var(--info)", id: 'Run #98 dimulai — "Suara Misterius dari Palung Mariana"', en: 'Run #98 started — "Mysterious Sounds from Mariana Trench"', t: "baru saja" },
  { c: "var(--success)", id: "Run #97 dipublikasikan ke YouTube · 12.4K views", en: "Run #97 published to YouTube · 12.4K views", t: "3 mnt" },
  { c: "var(--accent)", id: 'Self-learning: bobot niche "Misteri Samudra" dinaikkan +12%', en: 'Self-learning: "Ocean Mysteries" niche weight raised +12%', t: "14 mnt" },
  { c: "var(--success)", id: "Run #96 selesai · Jejak Kelam Sejarah · 1m 31s", en: "Run #96 completed · Dark History · 1m 31s", t: "42 mnt" },
  { c: "var(--warning)", id: "Kuota OpenAI mendekati 80% budget bulanan", en: "OpenAI quota nearing 80% of monthly budget", t: "1 jam" },
  { c: "var(--error)", id: "Run #95 gagal · timeout ElevenLabs · dijadwalkan ulang", en: "Run #95 failed · ElevenLabs timeout · rescheduled", t: "1 jam" },
];

export default function DashboardPage() {
  return (
    <>
      {/* greeting */}
      <div className="greet">
        <div>
          <h1><Bi id="Selamat siang, Riko" en="Good afternoon, Riko" /></h1>
          <div className="sub">
            <span>Selasa, 10 Juni 2026</span>
            <span className="muted">·</span>
            <span className="worker"><span className="d" /><Bi id="Worker aktif" en="Worker live" /></span>
          </div>
        </div>
        <button className="btn btn-ai btn-lg"><Zap size={18} /> <Bi id="Jalankan Sekarang" en="Run Now" /></button>
      </div>

      {/* KPI */}
      <div className="kpi-row">
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Play size={14} /> <Bi id="Video Hari Ini" en="Videos Today" /></span></div>
          <span className="kpi-value">2<span className="muted" style={{ fontSize: "var(--text-xl)", fontWeight: 500 }}>/3</span></span>
          <Spark data={[6, 5, 7, 4, 6, 8, 7]} color="var(--brand)" />
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><CheckCircle size={14} /> Success Rate</span></div>
          <span className="kpi-value">95%</span>
          <span className="kpi-delta up"><ArrowUp size={12} /> +2% <span className="muted" style={{ color: "var(--text-muted)", fontWeight: 400 }}>vs kemarin</span></span>
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Eye size={14} /> <Bi id="Total Views Hari Ini" en="Views Today" /></span></div>
          <span className="kpi-value">1.2K</span>
          <Spark data={[3, 4, 4, 6, 5, 8, 11]} color="var(--success)" />
        </div>
        <div className="kpi">
          <div className="kpi-top"><span className="kpi-label"><Users size={14} /> <Bi id="Subs Hari Ini" en="Subs Today" /></span></div>
          <span className="kpi-value">+47</span>
          <span className="kpi-delta up"><TrendingUp size={12} /> +18% <span className="muted" style={{ color: "var(--text-muted)", fontWeight: 400 }}>7 hari</span></span>
        </div>
      </div>

      <div className="grid2">
        {/* LEFT */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card">
            <div className="card-head">
              <h3 className="card-title"><Calendar size={16} /> <Bi id="Jadwal Hari Ini" en="Today's Schedule" /></h3>
              <a href="/schedule" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat jadwal lengkap →" en="View full schedule →" /></a>
            </div>
            <div className="card-body" style={{ paddingTop: "0.5rem", paddingBottom: "0.5rem" }}>
              <div className="slot">
                <div><div className="time">10:00</div><div className="tz">WIB</div></div>
                <div><div className="topic">Kapal Hilang di Segitiga Bermuda</div><div className="ch">Misteri Samudra · short</div></div>
                <span className="badge badge-success"><span className="dot" />Done</span>
                <a href="/runs/97" className="btn btn-ghost btn-icon btn-sm"><ExternalLink size={14} /></a>
              </div>
              <div className="slot">
                <div><div className="time">14:00</div><div className="tz">WIB</div></div>
                <div><div className="topic">Suara Misterius dari Palung Mariana</div><div className="ch">Misteri Samudra · short</div></div>
                <span className="badge badge-running"><span className="dot" /><Bi id="Berjalan" en="Running" /></span>
                <a href="/runs/98" className="btn btn-ghost btn-icon btn-sm"><ArrowRight size={14} /></a>
              </div>
              <div className="slot">
                <div><div className="time">19:00</div><div className="tz">WIB</div></div>
                <div><div className="topic">Mengapa Kota Atlantis Tak Pernah Ditemukan</div><div className="ch">Misteri Samudra · short</div></div>
                <span className="badge badge-default"><span className="dot" />Pending</span>
                <button className="btn btn-ghost btn-icon btn-sm"><MoreVertical size={14} /></button>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <h3 className="card-title"><List size={16} /> <Bi id="Run Terbaru" en="Recent Runs" /></h3>
              <a href="/runs" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat semua →" en="View all →" /></a>
            </div>
            <div className="card-body" style={{ padding: "0.5rem 0.75rem" }}>
              {RUNS.map((r) => {
                const m = ST_MAP[r.st];
                return (
                  <a key={r.id} href={`/runs/${r.id}`} className={`run-item${r.st === "failed" ? " failed" : ""}`}>
                    <span className="rstat" style={{ background: m.bg, color: m.c }}><m.Icon size={12} /></span>
                    <div style={{ minWidth: 0 }}>
                      <div className="rtopic">{r.topic}</div>
                      <div className="rmeta"><span>{r.ch}</span><span>{r.dur}</span></div>
                    </div>
                    <div className="rright">
                      {r.views !== "—"
                        ? <span className="tnum">{r.views} <span className="muted">views</span></span>
                        : <span className="muted">{r.st === "running" ? "live" : ""}</span>}
                      <ChevronRight size={14} />
                    </div>
                  </a>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div className="card">
            <div className="card-head">
              <h3 className="card-title"><GaugeIcon size={16} /> <Bi id="Skor Compliance" en="Compliance Score" /></h3>
              <span className="card-sub">Misteri Samudra</span>
            </div>
            <div className="card-body compliance-wrap">
              <Gauge />
              <div className="comp-break">
                <div className="comp-row"><div className="top"><span className="muted"><Bi id="Diversity suara" en="Voice diversity" /></span><span className="v">92%</span></div><div className="progress"><span style={{ width: "92%", background: "var(--success)" }} /></div></div>
                <div className="comp-row"><div className="top"><span className="muted"><Bi id="Sebaran niche" en="Niche spread" /></span><span className="v">88%</span></div><div className="progress"><span style={{ width: "88%", background: "var(--success)" }} /></div></div>
                <div className="comp-row"><div className="top"><span className="muted"><Bi id="Sebaran hook" en="Hook spread" /></span><span className="v">81%</span></div><div className="progress"><span style={{ width: "81%", background: "var(--warning)" }} /></div></div>
              </div>
            </div>
            <div className="card-foot"><a href="/compliance" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat detail compliance →" en="View compliance detail →" /></a></div>
          </div>

          <div className="card card-pad">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.25rem" }}>
              <h3 className="card-title"><DollarSign size={16} /> <Bi id="Biaya AI Hari Ini" en="AI Cost Today" /></h3>
              <span className="badge badge-outline">BYOK</span>
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.5rem" }}>
              <span style={{ fontSize: "var(--text-4xl)", fontWeight: 700, letterSpacing: "-0.02em" }}>$4.20</span>
              <span className="muted" style={{ fontSize: "var(--text-sm)" }}>≈ Rp 67K</span>
            </div>
            <div className="cost-bar"><span style={{ background: "var(--anthropic)", width: "30%" }} /><span style={{ background: "var(--elevenlabs)", width: "25%" }} /><span style={{ background: "var(--openai)", width: "45%" }} /></div>
            <div className="cost-leg">
              <span><i style={{ background: "var(--anthropic)" }} />Anthropic 30%</span>
              <span><i style={{ background: "var(--elevenlabs)" }} />ElevenLabs 25%</span>
              <span><i style={{ background: "var(--openai)" }} />OpenAI 45%</span>
            </div>
            <hr className="hr" style={{ margin: "0.875rem 0 0.75rem" }} />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", marginBottom: 6 }}><span className="muted"><Bi id="Bulan ini" en="This month" /></span><span><b style={{ fontWeight: 600 }}>$112</b> <span className="muted">/ $500 budget</span></span></div>
            <div className="progress"><span style={{ width: "22%" }} /></div>
          </div>

          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.875rem" }}><Sparkles size={16} /> <Bi id="Status Self-Learning" en="Self-Learning Status" /></h3>
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.75rem" }}><Bi id="Tarikan analytics terakhir: 2 jam lalu" en="Last analytics pull: 2 hours ago" /></div>
            <div className="insight">
              <span className="ic"><TrendingUp size={18} /></span>
              <div className="t"><span data-id>Hook <b>&quot;gap question&quot;</b> perform <b>2.3× lebih baik</b> — mesin memprioritaskannya.</span><span data-en>The <b>&quot;gap question&quot;</b> hook performs <b>2.3× better</b> — the engine is prioritizing it.</span></div>
            </div>
            <div style={{ marginTop: "0.75rem" }}><a href="/insights" className="muted" style={{ fontSize: "var(--text-xs)", textDecoration: "none" }}><Bi id="Lihat semua insight →" en="View all insights →" /></a></div>
          </div>
        </div>
      </div>

      {/* activity feed */}
      <div className="card" style={{ marginTop: "1rem" }}>
        <div className="card-head"><h3 className="card-title"><Activity size={16} /> <Bi id="Aktivitas Langsung" en="Live Activity" /></h3><span className="badge badge-running"><span className="dot" />live</span></div>
        <div className="card-body" style={{ padding: "0.5rem 1.25rem" }}>
          <div className="feed">
            {FEED.map((f, i) => (
              <div className="feed-item" key={i}>
                <span className="fdot" style={{ background: f.c }} />
                <span data-id>{f.id}</span><span data-en>{f.en}</span>
                <span className="ftime">{f.t}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
