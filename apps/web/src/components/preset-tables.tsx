"use client";

// PresetTables — 2 tabel preset durasi (segmentasi + glosarium), SINGLE-SOURCE dari DB
// (duration_presets + beat_glossary, anon client + RLS public-read). Dipakai di:
//   • tenant  : channel detail (selectable → pilih channels.duration_preset)
//   • admin   : read-only (panduan)
// Dwibahasa via pola <Bi> (span data-id/data-en, toggle oleh shell). Kolom "Segmentasi" diturunkan
// dari beats (key penuh) → beat_glossary.term (nama-pendek) → "hook-core-cta" — tak ada hardcode.

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Preset = {
  seconds: number; visual_beats: number | null; beats: string[] | null;
  use_case: string | null; use_case_en: string | null; render_mode: string | null;
};
type Term = {
  beat_key: string; term: string | null; label_id: string; label_en: string;
  desc_id: string; desc_en: string; sort_order: number;
};

export default function PresetTables({
  selectable = false, selectedSeconds = null, onSelect,
}: {
  selectable?: boolean; selectedSeconds?: number | null; onSelect?: (s: number) => void;
}) {
  const [supabase] = useState(() => createClient());
  const [presets, setPresets] = useState<Preset[]>([]);
  const [terms, setTerms] = useState<Term[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const { data: p } = await supabase.from("duration_presets")
        .select("seconds,visual_beats,beats,use_case,use_case_en,render_mode")
        .eq("is_active", true).order("seconds");
      const { data: g } = await supabase.from("beat_glossary")
        .select("beat_key,term,label_id,label_en,desc_id,desc_en,sort_order")
        .order("sort_order");
      setPresets((p ?? []) as Preset[]);
      setTerms((g ?? []) as Term[]);
      setLoading(false);
    })();
  }, [supabase]);

  const termOf = (bk: string) => terms.find((t) => t.beat_key === bk)?.term ?? bk;
  const seg = (beats: string[] | null) => (beats ?? []).map(termOf).join("-");

  if (loading) return <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Memuat preset…" en="Loading presets…" /></div>;

  const th: React.CSSProperties = { textAlign: "left", padding: "0.5rem 0.6rem", fontSize: "var(--text-xs)", color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" };
  const td: React.CSSProperties = { padding: "0.5rem 0.6rem", fontSize: "var(--text-sm)", borderBottom: "1px solid var(--border)", verticalAlign: "top" };
  const mono: React.CSSProperties = { ...td, fontFamily: "var(--font-mono, ui-monospace, monospace)", fontSize: "var(--text-xs)" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* TABEL 1 — Segmentasi per preset */}
      <div>
        <div className="label" style={{ marginBottom: "0.4rem" }}>
          <Bi id="Pilihan durasi & segmentasi konten" en="Duration & content segmentation" />
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 560 }}>
            <thead><tr>
              {selectable && <th style={th}></th>}
              <th style={th}><Bi id="Durasi" en="Duration" /></th>
              <th style={th}>Beat</th>
              <th style={th}><Bi id="Segmentasi" en="Segments" /></th>
              <th style={th}><Bi id="Cocok untuk" en="Best for" /></th>
              <th style={th}>Render</th>
            </tr></thead>
            <tbody>
              {presets.map((p) => {
                const sel = selectable && selectedSeconds === p.seconds;
                return (
                  <tr key={p.seconds}
                      onClick={selectable ? () => onSelect?.(p.seconds) : undefined}
                      style={{ cursor: selectable ? "pointer" : "default", background: sel ? "var(--accent-soft, rgba(99,102,241,0.10))" : undefined }}>
                    {selectable && <td style={td}><input type="radio" checked={sel} readOnly aria-label={`${p.seconds}s`} /></td>}
                    <td style={{ ...td, fontWeight: 600, whiteSpace: "nowrap" }}>{p.seconds}s</td>
                    <td style={td}>{p.visual_beats}</td>
                    <td style={mono}>{seg(p.beats)}</td>
                    <td style={td}><Bi id={p.use_case ?? ""} en={p.use_case_en ?? p.use_case ?? ""} /></td>
                    <td style={{ ...td, whiteSpace: "nowrap" }}>{p.render_mode}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* TABEL 2 — Glosarium bagian video (penjelasan istilah segmentasi) */}
      <div>
        <div className="label" style={{ marginBottom: "0.4rem" }}>
          <Bi id="Glosarium bagian video" en="Video parts glossary" />
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 480 }}>
            <thead><tr>
              <th style={th}><Bi id="Istilah" en="Term" /></th>
              <th style={th}><Bi id="Bagian" en="Part" /></th>
              <th style={th}><Bi id="Penjelasan" en="Description" /></th>
            </tr></thead>
            <tbody>
              {terms.map((t) => (
                <tr key={t.beat_key}>
                  <td style={mono}>{t.term ?? t.beat_key}</td>
                  <td style={{ ...td, fontWeight: 600, whiteSpace: "nowrap" }}><Bi id={t.label_id} en={t.label_en} /></td>
                  <td style={td}><Bi id={t.desc_id} en={t.desc_en} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
