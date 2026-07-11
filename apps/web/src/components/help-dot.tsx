"use client";

import { HelpCircle } from "lucide-react";
import { useHelpHref } from "@/lib/help-links";

// [D1] Ikon ? kontekstual — SATU komponen utk semua lokasi (PageHeader + anchor manual).
// Tujuan dibaca dari pemetaan DB (admin-managed) dgn fallback bawaan — lihat lib/help-links.ts.
export function HelpDot({ locationKey, size = 16, style }: {
  locationKey: string; size?: number; style?: React.CSSProperties;
}) {
  const href = useHelpHref(locationKey);
  return (
    <a href={href} target="_blank" rel="noopener"
      title="Panduan halaman ini / This page's guide" aria-label="Panduan / Help"
      style={{ display: "inline-flex", marginLeft: "0.5rem", verticalAlign: "middle", ...style }}>
      <HelpCircle size={size} style={{ color: "var(--text-muted)" }} />
    </a>
  );
}
