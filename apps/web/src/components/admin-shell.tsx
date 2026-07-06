"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import {
  Users, HelpCircle, Activity, List, Target, DollarSign, LogOut, UserCog, FlaskConical, FileText,
  Menu, Search, Moon, Sun, ChevronRight, SlidersHorizontal, CreditCard, MessageSquare, Building2,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// Port MVAdmin (design-source/styles/admin-shell.js) → React. admin.mesinviral.com.
// Reuse app-shell.css (.app/.sidebar/.sb-*/.topbar). Nav admin distinct + badge ADMIN amber.

type NavItem = { id: string; icon: React.ComponentType<{ size?: number }>; idL: string; en: string; href: string; badge?: string };
type NavEntry = { section: { id: string; en: string } } | NavItem;

const NAV: NavEntry[] = [
  { section: { id: "Operasi", en: "Operations" } },
  { id: "tenants", icon: Users, idL: "Tenant", en: "Tenants", href: "/admin/tenants" },
  { id: "billing", icon: CreditCard, idL: "Pembayaran", en: "Payments", href: "/admin/billing" },
  { id: "app-config", icon: SlidersHorizontal, idL: "Konfigurasi Sistem", en: "System Configuration", href: "/admin/app-config" },
  { id: "company-profile", icon: Building2, idL: "Profil Perusahaan", en: "Company Profile", href: "/admin/company-profile" },
  { id: "support", icon: HelpCircle, idL: "Dukungan", en: "Support", href: "/admin/support" },
  { id: "feedback", icon: MessageSquare, idL: "Masukan", en: "Feedback", href: "/admin/feedback" },
  { id: "system", icon: Activity, idL: "Kesehatan Sistem", en: "System Health", href: "/admin/system" },
  { id: "content", icon: FileText, idL: "Konten (CMS)", en: "Content (CMS)", href: "/admin/content" },
  { section: { id: "Katalog", en: "Catalog" } },
  { id: "catalog", icon: List, idL: "Katalog", en: "Catalog", href: "/admin/catalog" },
  { id: "niches", icon: Target, idL: "Pustaka Niche", en: "Niche Library", href: "/admin/niches" },
  { id: "pricing", icon: DollarSign, idL: "Konfigurasi Harga", en: "Pricing Config", href: "/admin/pricing" },
  { id: "test-lab", icon: FlaskConical, idL: "Test Lab", en: "Test Lab", href: "/admin/test-lab" },
];

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [navOpen, setNavOpen] = useState(false);  // drawer mobile (≤1024px) — sama dgn AppShell
  const [lang, setLang] = useState<"id" | "en">("id");
  const [mounted, setMounted] = useState(false);
  const [supportCount, setSupportCount] = useState(0);
  // ── Palet pencarian global (⌘K) — dulu elemen dekoratif mati (temuan owner 2026-07-06) ──
  const router = useRouter();
  const [palOpen, setPalOpen] = useState(false);
  const [palQ, setPalQ] = useState("");
  const [palData, setPalData] = useState<{ tenants: { id: string; handle: string }[]; niches: { id: string; name: string }[] } | null>(null);
  const openPal = () => { setPalOpen(true); setPalQ(""); if (!palData) {
    Promise.all([fetch("/api/admin/tenants").then((r) => r.ok ? r.json() : null), fetch("/api/admin/niches").then((r) => r.ok ? r.json() : null)])
      .then(([t, n]) => setPalData({
        tenants: ((t?.tenants ?? []) as { tenant_id: string; handle?: string | null; email?: string | null; display_handle?: string | null }[]).map((x) => ({ id: x.tenant_id, handle: x.handle || x.email || x.display_handle || x.tenant_id.slice(0, 8) })),
        niches: ((n?.niches ?? []) as { niche_id: string; name: string }[]).map((x) => ({ id: x.niche_id, name: x.name })),
      })).catch(() => setPalData({ tenants: [], niches: [] }));
  } };
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPal(); }
      if (e.key === "Escape") setPalOpen(false);
    };
    document.addEventListener("keydown", k); return () => document.removeEventListener("keydown", k);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [palData]);
  const palGo = (href: string) => { setPalOpen(false); router.push(href); };
  const palResults = (() => {
    if (!palOpen) return [] as { group: string; label: string; href: string }[];
    const ql = palQ.trim().toLowerCase();
    const menu = NAV.filter((e): e is NavItem => !("section" in e))
      .filter((m) => !ql || m.idL.toLowerCase().includes(ql) || m.en.toLowerCase().includes(ql))
      .map((m) => ({ group: "Menu", label: m.idL, href: m.href }));
    if (!ql) return menu.slice(0, 8);
    const tenants = (palData?.tenants ?? []).filter((t) => t.handle.toLowerCase().includes(ql) || t.id.toLowerCase().includes(ql))
      .slice(0, 5).map((t) => ({ group: "Tenant", label: t.handle, href: `/admin/tenants?q=${encodeURIComponent(t.handle)}` }));
    const niches = (palData?.niches ?? []).filter((n) => n.name.toLowerCase().includes(ql) || n.id.toLowerCase().includes(ql))
      .slice(0, 5).map((n) => ({ group: "Niche", label: n.name, href: `/admin/niches?q=${encodeURIComponent(n.name)}` }));
    return [...menu.slice(0, 4), ...tenants, ...niches];
  })();

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved);
    document.documentElement.lang = saved;
  }, []);

  // Badge Dukungan = jumlah tiket BELUM selesai (open+pending) dari API — no-hardcode. Gagal → 0 (badge hilang).
  useEffect(() => {
    fetch("/api/admin/support")
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => { const c = j?.counts; if (c) setSupportCount((c.open ?? 0) + (c.pending ?? 0)); })
      .catch(() => {});
  }, []);

  // Tutup drawer mobile tiap pindah halaman
  useEffect(() => { setNavOpen(false); }, [pathname]);

  function switchLang(l: "id" | "en") {
    setLang(l);
    document.documentElement.lang = l;
    localStorage.setItem("mv-lang", l);
  }

  const active = NAV.find((n) => "id" in n && (pathname === n.href || pathname.startsWith(n.href + "/"))) as Extract<NavEntry, { id: string }> | undefined;

  return (
    <div className={`app${collapsed && !navOpen ? " collapsed" : ""}${navOpen ? " nav-open" : ""}`}>
      {navOpen && <div className="nav-scrim" onClick={() => setNavOpen(false)} />}
      <aside className="sidebar">
        <div className="sb-top">
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 30, height: 30, objectFit: "contain", flex: "none" }} />
          <span className="sb-name">MesinViral</span>
          <span className="badge" style={{ background: "var(--warning-soft)", color: "var(--warning)", fontSize: "0.5625rem", padding: "2px 5px", marginLeft: 2 }}>ADMIN</span>
        </div>
        <nav className="sb-nav" style={{ marginTop: "0.5rem" }}>
          {NAV.map((n, i) => {
            if ("section" in n) return <div key={`s${i}`} className="sb-section-title">{n.section.id}</div>;
            const Icon = n.icon;
            const isActive = pathname === n.href || pathname.startsWith(n.href + "/");
            const badge = n.id === "support" ? (supportCount > 0 ? String(supportCount) : undefined) : n.badge;
            return (
              <Link key={n.id} className={`sb-item${isActive ? " active" : ""}`} href={n.href} title={n.idL}>
                <Icon size={18} />
                <span className="sb-label"><Bi id={n.idL} en={n.en} /></span>
                {badge ? <span className="sb-badge" style={{ background: "var(--warning)", color: "#000" }}>{badge}</span> : null}
              </Link>
            );
          })}
        </nav>
        <div className="sb-bottom">
          <Link className={`sb-item${pathname.startsWith("/admin/account") ? " active" : ""}`} href="/admin/account" title="Akun">
            <UserCog size={18} /><span className="sb-label"><Bi id="Akun" en="Account" /></span>
          </Link>
          <button
            className="sb-item"
            onClick={async () => { await createClient().auth.signOut(); window.location.href = "/admin/login"; }}
            style={{ width: "100%", background: "none", border: "none", fontFamily: "inherit" }}
          >
            <LogOut size={18} /><span className="sb-label"><Bi id="Keluar" en="Sign out" /></span>
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn btn-ghost btn-icon tb-toggle" aria-label="Toggle sidebar" onClick={() => {
            if (window.matchMedia("(max-width: 1024px)").matches) setNavOpen((o) => !o);
            else setCollapsed((c) => !c);
          }}><Menu size={18} /></button>
          <div className="breadcrumb">
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.4375rem" }}><a href="/admin/tenants">Admin</a><ChevronRight size={14} /></span>
            <span className="cur">{active ? <Bi id={active.idL} en={active.en} /> : null}</span>
          </div>
          <div className="tb-search" role="button" tabIndex={0} style={{ cursor: "pointer" }} onClick={openPal}
               onKeyDown={(e) => { if (e.key === "Enter") openPal(); }}>
            <Search size={15} />
            <span><Bi id="Cari tenant, niche, menu…" en="Search tenants, niches, menu…" /></span>
            <kbd>⌘K</kbd>
          </div>
          <div className="segmented">
            <button aria-selected={lang === "id"} onClick={() => switchLang("id")}>ID</button>
            <button aria-selected={lang === "en"} onClick={() => switchLang("en")}>EN</button>
          </div>
          <button className="btn btn-ghost btn-icon" aria-label="Tema" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {mounted && theme === "light" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <span className="avatar" style={{ background: "var(--warning-soft)", color: "var(--warning)" }} title="Admin">AD</span>
        </header>

        {palOpen && (
          <div onClick={(e) => { if (e.target === e.currentTarget) setPalOpen(false); }}
               style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", zIndex: 90, display: "flex", justifyContent: "center", paddingTop: "12vh" }}>
            <div className="card" style={{ width: "min(520px, 92vw)", height: "fit-content", maxHeight: "60vh", display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "0.75rem 1rem", borderBottom: "1px solid var(--border-subtle)" }}>
                <Search size={16} style={{ color: "var(--text-muted)" }} />
                <input autoFocus className="input" style={{ border: "none", boxShadow: "none", background: "transparent", flex: 1 }}
                       placeholder="Cari tenant, niche, atau menu…" value={palQ} onChange={(e) => setPalQ(e.target.value)}
                       onKeyDown={(e) => { if (e.key === "Enter" && palResults[0]) palGo(palResults[0].href); }} />
                <kbd style={{ fontSize: ".625rem", color: "var(--text-muted)" }}>Esc</kbd>
              </div>
              <div style={{ overflowY: "auto", padding: ".4rem" }}>
                {palResults.length === 0 && <div className="muted" style={{ padding: "1rem", fontSize: "var(--text-sm)", textAlign: "center" }}>Tidak ada hasil.</div>}
                {palResults.map((r, i) => (
                  <button key={r.group + r.href + i} onClick={() => palGo(r.href)}
                          style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", textAlign: "left", padding: ".55rem .75rem",
                                   background: "none", border: "none", borderRadius: "var(--r-md)", cursor: "pointer", color: "var(--text-primary)", fontSize: "var(--text-sm)" }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg)")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "none")}>
                    <span className="badge badge-default" style={{ fontSize: ".575rem", minWidth: 46, justifyContent: "center" }}>{r.group}</span>
                    {r.label}
                  </button>))}
              </div>
            </div>
          </div>
        )}
        <main className="page"><div className="page-wide">{children}</div></main>
      </div>
    </div>
  );
}
