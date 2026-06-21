"use client";

import { ShieldCheck, CheckCircle, Info, Mic, Layers, Anchor, RefreshCw, AlertTriangle } from "lucide-react";
import "../app/(app)/compliance/compliance.css";

// Komponen bersama Compliance (F2-13) — dipakai MAIN /compliance (agregat) DAN tab Channel Detail
// (per-channel). Satu sumber render → nol duplikat. Menerima objek compliance berbentuk sama
// (score/status/dimensions/alert_below) dari RPC agregat ATAU channel_insights per-channel.

export type Compliance = { score: number | null; status: string; dimensions: Record<string, number | null>; alert_below: number; channels_count?: number };

const DIM_META: [string, string, string, typeof Mic][] = [
  ["niche_distribution", "Distribusi Niche", "Niche Distribution", Layers],
  ["hook_style_spread", "Variasi Hook", "Hook Variation", Anchor],
  ["voice_diversity", "Diversity Suara", "Voice Diversity", Mic],
  ["dup_freshness", "Anti-Duplikat", "Duplicate Freshness", RefreshCw],
  ["ai_disclosure", "AI Disclosure", "AI Disclosure", ShieldCheck],
];

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

function Gauge({ score }: { score: number | null }) {
  const r = 64, c = 2 * Math.PI * r, v = score ?? 0, off = c * (1 - v / 100);
  const col = score == null ? "var(--surface-3)" : v >= 80 ? "#10B981" : v >= 60 ? "#F59E0B" : "#EF4444";
  return (
    <svg viewBox="0 0 160 160" width={160} height={160}>
      <circle cx={80} cy={80} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={12} />
      {score != null && <circle cx={80} cy={80} r={r} fill="none" stroke={col} strokeWidth={12} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 80 80)" />}
      <text x={80} y={76} textAnchor="middle" fontSize={score == null ? 22 : 40} fontWeight={800} fill="var(--text-primary)" fontFamily="Geist">{score == null ? "—" : Math.round(score)}</text>
      <text x={80} y={98} textAnchor="middle" fontSize={12} fill="var(--text-muted)" fontFamily="Geist">/ 100</text>
    </svg>
  );
}

export function ComplianceView({ compliance: cmp, loading, hasRow, showEdu = true }: {
  compliance: Compliance | null; loading: boolean; hasRow: boolean; showEdu?: boolean;
}) {
  const insufficient = !cmp || cmp.status === "insufficient_data" || cmp.score == null;
  const statusLabel = !hasRow ? ["Belum ada data", "No data yet"] : insufficient ? ["Belum cukup data", "Insufficient data"] : (cmp!.score! >= 80 ? ["Sehat", "Healthy"] : cmp!.score! >= 60 ? ["Perlu perhatian", "Needs attention"] : ["Berisiko", "At risk"]);

  return (
    <>
      <div className="hero-row">
        <div className="gauge-card">
          <Gauge score={cmp?.score ?? null} />
          <div className="label"><Bi id={statusLabel[0]} en={statusLabel[1]} /></div>
          <div className="sub">{loading ? "Memuat…" : insufficient ? <Bi id="Skor penuh muncul setelah cukup video produksi terkumpul (analytics-scope harian)." en="Full score appears once enough production videos accumulate." /> : <Bi id="Dinilai aman dari risiko YouTube AI policy." en="Assessed safe from YouTube AI policy risk." />}</div>
        </div>
        <div className="card radar-card" style={{ padding: "1.25rem" }}>
          <div className="radar-legend">
            {DIM_META.map(([key, idL, enL]) => {
              const v = cmp?.dimensions?.[key];
              return (<div className="row" key={key}><span className="secondary"><Bi id={idL} en={enL} /></span><div className="bar"><span style={{ width: v != null ? `${v}%` : "0%", background: v == null ? "var(--surface-3)" : v >= 80 ? "var(--success)" : v >= 60 ? "var(--warning)" : "var(--error)" }} /></div><span className="v">{v != null ? `${Math.round(v)}%` : "—"}</span></div>);
            })}
          </div>
        </div>
      </div>

      <div className="dim-grid">
        {DIM_META.map(([key, idL, enL, Icon]) => {
          const v = cmp?.dimensions?.[key];
          const scoreColor = v == null ? "var(--text-muted)" : v >= 80 ? "var(--success)" : v >= 60 ? "var(--warning)" : "var(--error)";
          const NoteIcon = v == null ? Info : v >= 80 ? CheckCircle : AlertTriangle;
          const note = v == null
            ? { id: "Belum cukup data produksi untuk dimensi ini.", en: "Not enough production data for this dimension yet." }
            : v >= 80
              ? { id: "Dalam rentang sehat.", en: "Within healthy range." }
              : { id: "Di bawah target — diversity guard akan menyesuaikan.", en: "Below target — diversity guard will adjust." };
          return (
            <div className="card card-pad dim-card" key={key}>
              <div className="head"><span className="ic" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><Icon size={17} /></span><h3><Bi id={idL} en={enL} /></h3><span className="score" style={{ color: scoreColor }}>{v != null ? `${Math.round(v)}%` : "—"}</span></div>
              <div className={`dim-note ${v == null ? "" : v >= 80 ? "ok" : "warn"}`}>
                <span style={{ flex: "none" }}><NoteIcon size={14} /></span>
                <span><Bi id={note.id} en={note.en} /></span>
              </div>
            </div>
          );
        })}
      </div>

      {showEdu && (
        <div className="card card-pad" style={{ marginTop: "1rem" }}>
          <div className="edu">
            <div>
              <h3 style={{ fontSize: "var(--text-lg)", fontWeight: 600, margin: "0 0 0.5rem" }}><Bi id="📚 Kenapa ini penting?" en="📚 Why this matters" /></h3>
              <p className="muted" style={{ fontSize: "var(--text-sm)", lineHeight: 1.6, margin: 0, maxWidth: "60ch" }}><Bi id="YouTube memperketat AI content policy 2026. Output terlalu seragam berisiko demonetisasi. Compliance Score (5 dimensi) menjaga channelmu otomatis; alert bila < 60." en="YouTube tightened its 2026 AI content policy. Overly uniform output risks demonetization. The 5-dimension Compliance Score guards your channel automatically; alerts below 60." /></p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
