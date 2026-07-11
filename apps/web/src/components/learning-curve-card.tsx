"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { TrendingUp, ArrowUp, ArrowDown } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "../app/(app)/insights/insights.css";

// [B17-F0] Kurva Belajar — komponen bersama DUA SKOP (pola InsightsView): per-channel
// (/channels/[id] tab Wawasan, prop channelId) & seluruh-channel (/insights, tanpa channelId).
// Sumber = RPC get_channel_learning_curve (migr 0150): kohort minggu-PUBLISH, retensi = snapshot
// terbaru per video, views = ber-jendela N hari pertama (anti bias-umur, §2c PROGRAM_BUKTI).
// Garis penanda "mesin disehatkan" + daftar metrik toggle = app_config (no-hardcode).
// UI: primitives eksisting saja (.card/.segmented/.ins-chart + token CSS + pola Bi) — nol library baru.

type CurvePoint = {
  week_start: string; videos: number;
  retention_avg: number | null; retention_n: number;
  views7d_avg: number | null; views7d_n: number;
};
type MetricKey = "retention" | "views7d";

const METRIC_LABEL: Record<MetricKey, { id: string; en: string }> = {
  retention: { id: "Retensi", en: "Retention" },
  views7d:   { id: "Views 7 hari", en: "7-day views" },
};

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const fmtNum = (n: number) => Math.round(n).toLocaleString("id-ID");

function metricValue(p: CurvePoint, m: MetricKey): number | null {
  return m === "retention" ? (p.retention_n > 0 ? p.retention_avg : null) : (p.views7d_n > 0 ? p.views7d_avg : null);
}

// Delta minggu-terakhir-berdata vs minggu berdata sebelumnya (dipakai kartu + chip dashboard — satu rumus).
function computeDelta(points: CurvePoint[], m: MetricKey): { curr: number; deltaPct: number | null; week: string } | null {
  const series = points.map((p) => ({ w: p.week_start, v: metricValue(p, m) })).filter((x): x is { w: string; v: number } => x.v != null);
  if (series.length === 0) return null;
  const curr = series[series.length - 1], prev = series.length > 1 ? series[series.length - 2] : null;
  return { curr: curr.v, week: curr.w, deltaPct: prev && prev.v > 0 ? ((curr.v - prev.v) / prev.v) * 100 : null };
}

function useCurve(channelId?: string) {
  const supabase = useMemo(() => createClient(), []);
  const [points, setPoints] = useState<CurvePoint[] | null>(null);
  const [markerDate, setMarkerDate] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<MetricKey[]>(["retention", "views7d"]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    (async () => {
      const { data } = await supabase.rpc("get_channel_learning_curve", channelId ? { p_channel_id: channelId } : {});
      const { data: cfg } = await supabase.from("app_config").select("key,value_text")
        .in("key", ["learning_curve_marker_date", "learning_curve_metrics"]);
      if (!alive) return;
      setPoints(Array.isArray(data) ? (data as CurvePoint[]) : []);
      for (const row of (cfg as { key: string; value_text: string | null }[] | null) ?? []) {
        if (row.key === "learning_curve_marker_date" && row.value_text?.match(/^\d{4}-\d{2}-\d{2}$/)) setMarkerDate(row.value_text);
        if (row.key === "learning_curve_metrics" && row.value_text) {
          try {
            const arr = (JSON.parse(row.value_text) as string[]).filter((k): k is MetricKey => k === "retention" || k === "views7d");
            if (arr.length > 0) setMetrics(arr);
          } catch { /* fail-soft: default metrics */ }
        }
      }
      setLoading(false);
    })();
    return () => { alive = false; };
  }, [supabase, channelId]);
  return { points, markerDate, metrics, loading };
}

export function LearningCurveCard({ channelId, scopeLabel }: { channelId?: string; scopeLabel: { id: string; en: string } }) {
  const { points, markerDate, metrics, loading } = useCurve(channelId);
  const [metric, setMetric] = useState<MetricKey | null>(null);
  const m: MetricKey = metric ?? metrics[0];

  if (loading) return (
    <div className="card card-pad" style={{ marginBottom: "1rem" }}>
      <h3 className="card-title"><TrendingUp size={16} /> <Bi id="Kurva Belajar" en="Learning Curve" /></h3>
      <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>Memuat…</p>
    </div>
  );
  const pts = points ?? [];

  // Empty state (spec §2b): kurva bermakna butuh ≥2 kohort minggu.
  if (pts.length < 2) return (
    <div className="card card-pad" style={{ marginBottom: "1rem" }}>
      <h3 className="card-title"><TrendingUp size={16} /> <Bi id="Kurva Belajar" en="Learning Curve" /></h3>
      <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
        <Bi id="Kurva muncul setelah 2 minggu pertama — mesin sedang mengumpulkan pelajaran."
            en="The curve appears after the first 2 weeks — the engine is still gathering lessons." />
      </p>
    </div>
  );

  const maxV = Math.max(0.001, ...pts.map((p) => metricValue(p, m) ?? 0));
  // Garis penanda: SETELAH bar minggu yang MEMUAT tanggal penanda (minggu pasca-garis = era mesin-sehat penuh).
  const markerAfterIdx = markerDate
    ? pts.findIndex((p) => p.week_start <= markerDate && markerDate < addDays(p.week_start, 7))
    : -1;
  const delta = computeDelta(pts, m);
  const capStep = Math.max(1, Math.ceil(pts.length / 8)); // label tanggal tiap N bar agar tak berdesakan

  return (
    <div className="card card-pad" style={{ marginBottom: "1rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem", flexWrap: "wrap", marginBottom: "0.25rem" }}>
        <h3 className="card-title" style={{ margin: 0 }}><TrendingUp size={16} /> <Bi id={`Kurva Belajar — ${scopeLabel.id}`} en={`Learning Curve — ${scopeLabel.en}`} /></h3>
        {metrics.length > 1 && (
          <div className="segmented">
            {metrics.map((k) => (
              <button key={k} aria-selected={m === k} onClick={() => setMetric(k)}>
                <Bi id={METRIC_LABEL[k].id} en={METRIC_LABEL[k].en} />
              </button>
            ))}
          </div>
        )}
      </div>
      <p className="muted" style={{ fontSize: "var(--text-xs)", margin: "0 0 0.875rem" }}>
        <Bi id="Video BUATAN tiap minggu — makin pintar mesin, makin tinggi batangnya (bukan tabungan views video lama)."
            en="Videos MADE each week — the smarter the engine, the taller the bar (not old videos piling up views)." />
      </p>

      <div className="ins-chart" style={{ alignItems: "flex-end", height: 72 }}>
        {pts.map((p, i) => {
          const v = metricValue(p, m);
          const afterMarker = markerAfterIdx >= 0 && i > markerAfterIdx;
          return (
            // wrapper WAJIB height:100% — tinggi % batang butuh acuan pasti (audit per-widget 2026-07-11)
            <div key={p.week_start} style={{ flex: 1, height: "100%", display: "flex", alignItems: "flex-end" }}>
              <div className="b" style={{
                flex: 1,
                height: v != null ? `${Math.max(6, Math.round((v / maxV) * 100))}%` : "2px",
                background: v == null ? "var(--border-subtle)" : afterMarker ? "var(--brand)" : "var(--surface-3)",
                minHeight: 2,
              }} title={`${p.week_start} · ${p.videos} video${v != null ? ` · ${m === "retention" ? `${v.toFixed(1)}%` : fmtNum(v)}` : ""}`}>
                {i % capStep === 0 && <span className="cap">{shortWeek(p.week_start)}</span>}
              </div>
              {markerAfterIdx === i && <div style={{ width: 0, borderLeft: "2px dashed var(--brand)", height: "100%", marginLeft: "0.35rem" }} aria-hidden />}
            </div>
          );
        })}
      </div>

      {markerAfterIdx >= 0 && markerDate && (
        <p className="muted" style={{ fontSize: "var(--text-xs)", margin: "0 0 0.5rem" }}>
          <span style={{ color: "var(--brand)" }}>┊</span> {shortDate(markerDate)} — <Bi id="mesin disehatkan; minggu setelah garis = era belajar penuh" en="engine tuned; weeks after the line = full-learning era" />
        </p>
      )}

      {delta && (
        <p style={{ fontSize: "var(--text-sm)", margin: 0, color: "var(--text-primary)" }}>
          <Bi id="Minggu terakhir: rata-rata " en="Latest week: average " />
          <b>{m === "retention" ? `${delta.curr.toFixed(1)}%` : fmtNum(delta.curr)}</b>{" "}
          <Bi id={m === "retention" ? "retensi/video" : "views 7-hari/video"} en={m === "retention" ? "retention/video" : "7-day views/video"} />
          {delta.deltaPct != null && (
            <span style={{ marginLeft: "0.5rem", color: delta.deltaPct >= 0 ? "var(--success)" : "var(--text-muted)", fontWeight: 600 }}>
              {delta.deltaPct >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />} {Math.abs(delta.deltaPct).toFixed(0)}% <Bi id="vs minggu sebelumnya" en="vs prior week" />
            </span>
          )}
        </p>
      )}
    </div>
  );
}

// Chip 1-baris utk kartu Self-Learning dashboard (skop seluruh-channel; klik → /insights).
// Dormant-aman: tanpa data pembanding 2 minggu → tidak render apa pun.
export function LearningDeltaChip() {
  const { points, metrics, loading } = useCurve(undefined);
  if (loading || !points) return null;
  const delta = computeDelta(points, metrics[0]);
  if (!delta || delta.deltaPct == null) return null;
  const up = delta.deltaPct >= 0;
  return (
    <div style={{ marginTop: "0.5rem" }}>
      <Link href="/insights" style={{ fontSize: "var(--text-xs)", textDecoration: "none", color: up ? "var(--success)" : "var(--text-muted)", fontWeight: 600 }}>
        {up ? <ArrowUp size={12} /> : <ArrowDown size={12} />} {Math.abs(delta.deltaPct).toFixed(0)}%{" "}
        <Bi id={`${METRIC_LABEL[metrics[0]].id.toLowerCase()} vs minggu sebelumnya`} en={`${METRIC_LABEL[metrics[0]].en.toLowerCase()} vs prior week`} />
      </Link>
    </div>
  );
}

function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
function shortWeek(iso: string): string { const [, mo, da] = iso.split("-"); return `${Number(da)}/${Number(mo)}`; }
function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("id-ID", { day: "numeric", month: "short", timeZone: "UTC" });
}
