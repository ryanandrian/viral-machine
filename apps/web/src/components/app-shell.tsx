"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import {
  LayoutDashboard, Tv, List, BarChart3, Calendar, ShieldCheck, Sparkles,
  Command, Mic, Image as ImageIcon, CreditCard, Settings, HelpCircle,
  Menu, Search, Bell, ChevronsUpDown, Moon, Sun, ChevronRight,
} from "lucide-react";

// Port MVShell (design-source/styles/shell.js) → React. Sidebar + topbar.
// i18n sementara pakai pola desain: data-id/data-en + html[lang] (toggle client + localStorage).
// next-intl (routing) menyusul di langkah berikutnya.

type NavItem = {
  id: string; icon: React.ComponentType<{ size?: number }>;
  idL: string; en: string; href: string; badge?: string;
};
type NavEntry = { section: { id: string; en: string } } | NavItem;

const NAV: NavEntry[] = [
  { section: { id: "Menu", en: "Menu" } },
  { id: "dashboard", icon: LayoutDashboard, idL: "Beranda", en: "Dashboard", href: "/dashboard" },
  { id: "channels", icon: Tv, idL: "Kanal", en: "Channels", href: "/channels", badge: "3" },
  { id: "runs", icon: List, idL: "Produksi", en: "Runs", href: "/runs" },
  { id: "analytics", icon: BarChart3, idL: "Analitik", en: "Analytics", href: "/analytics" },
  { id: "schedule", icon: Calendar, idL: "Jadwal", en: "Schedule", href: "/schedule" },
  { id: "compliance", icon: ShieldCheck, idL: "Kepatuhan", en: "Compliance", href: "/compliance" },
  { id: "insights", icon: Sparkles, idL: "Wawasan", en: "Insights", href: "/insights" },
  { section: { id: "Konfigurasi", en: "Config" } },
  { id: "ai-engines", icon: Sparkles, idL: "Mesin AI", en: "AI Engines", href: "/config/ai-engines" },
  { id: "api-keys", icon: Command, idL: "API Keys", en: "API Keys", href: "/config/api-keys" },
  { id: "voice", icon: Mic, idL: "Suara", en: "Voice", href: "/config/voice" },
  { id: "visual", icon: ImageIcon, idL: "Visual", en: "Visual", href: "/config/visual" },
  { section: { id: "Akun", en: "Account" } },
  { id: "billing", icon: CreditCard, idL: "Tagihan", en: "Billing", href: "/billing" },
  // nav "Tim/Team" DIHAPUS — fitur team di-take-down untuk V2 (1 user=1 tenant, no multi-user — decisions_auth_rbac). Jangan tambah lagi s/d V3.
  { id: "settings", icon: Settings, idL: "Pengaturan", en: "Settings", href: "/settings" },
  { id: "support", icon: HelpCircle, idL: "Bantuan", en: "Support", href: "/support" },
];

function Bi({ id, en }: { id: string; en: string }) {
  return (<>
    <span data-id>{id}</span>
    <span data-en>{en}</span>
  </>);
}

export function AppShell({
  children,
  breadcrumb = [],
  tenant = { name: "Riko Pratama", plan: "Pro · 3 channel", initials: "RP" },
}: {
  children: React.ReactNode;
  breadcrumb?: { id: string; en?: string; href?: string }[];
  tenant?: { name: string; plan: string; initials: string };
}) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [lang, setLang] = useState<"id" | "en">("id");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved);
    document.documentElement.lang = saved;
  }, []);

  function switchLang(l: "id" | "en") {
    setLang(l);
    document.documentElement.lang = l;
    localStorage.setItem("mv-lang", l);
  }

  return (
    <div className={`app${collapsed ? " collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sb-top">
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 30, height: 30, objectFit: "contain", flex: "none" }} />
          <span className="sb-name">MesinViral</span>
        </div>
        <div className="sb-tenant" title="Ganti tenant">
          <span className="avatar">{tenant.initials}</span>
          <div className="sb-tenant-meta">
            <div className="nm">{tenant.name}</div>
            <div className="pl">{tenant.plan}</div>
          </div>
          <span className="sb-chev"><ChevronsUpDown size={14} /></span>
        </div>
        <nav className="sb-nav">
          {NAV.map((n, i) => {
            if ("section" in n) {
              return <div key={`s${i}`} className="sb-section-title">{n.section.id}</div>;
            }
            const Icon = n.icon;
            const active = pathname === n.href || pathname.startsWith(n.href + "/");
            return (
              <Link key={n.id} className={`sb-item${active ? " active" : ""}`} href={n.href} title={n.idL}>
                <Icon size={18} />
                <span className="sb-label"><Bi id={n.idL} en={n.en} /></span>
                {n.badge ? <span className="sb-badge">{n.badge}</span> : null}
              </Link>
            );
          })}
        </nav>
        <div className="sb-bottom">
          <a className="sb-item" href="/support"><HelpCircle size={18} />
            <span className="sb-label"><Bi id="Bantuan" en="Help" /></span>
          </a>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn btn-ghost btn-icon tb-toggle" aria-label="Toggle sidebar"
            onClick={() => setCollapsed((c) => !c)}><Menu size={18} /></button>
          <div className="breadcrumb">
            {breadcrumb.map((c, i) => {
              const last = i === breadcrumb.length - 1;
              return last
                ? <span key={i} className="cur"><Bi id={c.id} en={c.en || c.id} /></span>
                : <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: "0.4375rem" }}>
                    <Link href={c.href || "#"}><Bi id={c.id} en={c.en || c.id} /></Link><ChevronRight size={14} />
                  </span>;
            })}
          </div>
          <div className="tb-search">
            <Search size={15} />
            <span><Bi id="Cari atau jalankan perintah…" en="Search or run a command…" /></span>
            <kbd>⌘K</kbd>
          </div>
          <button className="btn btn-ghost btn-icon tb-icon" aria-label="Notifikasi">
            <span className="ind" /><Bell size={18} />
          </button>
          <div className="segmented">
            <button aria-selected={lang === "id"} onClick={() => switchLang("id")}>ID</button>
            <button aria-selected={lang === "en"} onClick={() => switchLang("en")}>EN</button>
          </div>
          <button className="btn btn-ghost btn-icon" aria-label="Tema"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {mounted && theme === "light" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <span className="avatar" title={tenant.name}>{tenant.initials}</span>
        </header>

        <main className="page"><div className="page-wide">{children}</div></main>
      </div>
    </div>
  );
}
