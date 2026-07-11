import type { ReactNode, ComponentType, CSSProperties } from "react";
import { HelpCircle } from "lucide-react";
import "./page-header.css";

// Header halaman SERAGAM (acuan: page Wawasan) — dipakai SEMUA main page (kecuali Beranda).
// Satu sumber → ikon + judul besar + subtitle identik di mana pun. `action` = elemen kanan opsional
// (mis. tombol Tambah / badge). Ikon diwarnai hitam (var(--text-primary)) via CSS .pg-header h1 svg.
// helpSlug ([D1] 2026-07-11) = help kontekstual: ikon ? kecil → artikel panduan halaman ini (tab baru).
export function PageHeader({ icon: Icon, title, subtitle, action, helpSlug }: {
  icon?: ComponentType<{ size?: number; style?: CSSProperties }>;
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  helpSlug?: string;
}) {
  return (
    <div className="pg-header">
      <div className="pg-header-text">
        <h1>
          {Icon ? <Icon size={26} /> : null}{title}
          {helpSlug ? (
            <a href={`/docs?a=${helpSlug}`} target="_blank" rel="noopener"
              title="Panduan halaman ini / This page's guide" aria-label="Panduan / Help"
              style={{ display: "inline-flex", marginLeft: "0.5rem", verticalAlign: "middle" }}>
              <HelpCircle size={16} style={{ color: "var(--text-muted)" }} />
            </a>
          ) : null}
        </h1>
        {subtitle ? <div className="pg-sub">{subtitle}</div> : null}
      </div>
      {action ? <div className="pg-header-action">{action}</div> : null}
    </div>
  );
}
