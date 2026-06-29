import type { ReactNode, ComponentType, CSSProperties } from "react";
import "./page-header.css";

// Header halaman SERAGAM (acuan: page Wawasan) — dipakai SEMUA main page (kecuali Beranda).
// Satu sumber → ikon + judul besar + subtitle identik di mana pun. `action` = elemen kanan opsional
// (mis. tombol Tambah / badge). Ikon diwarnai hitam (var(--text-primary)) via CSS .pg-header h1 svg.
export function PageHeader({ icon: Icon, title, subtitle, action }: {
  icon?: ComponentType<{ size?: number; style?: CSSProperties }>;
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="pg-header">
      <div className="pg-header-text">
        <h1>{Icon ? <Icon size={26} /> : null}{title}</h1>
        {subtitle ? <div className="pg-sub">{subtitle}</div> : null}
      </div>
      {action ? <div className="pg-header-action">{action}</div> : null}
    </div>
  );
}
