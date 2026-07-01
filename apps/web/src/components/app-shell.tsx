"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import {
  LayoutDashboard, Tv, List, BarChart3, Calendar, ShieldCheck, Sparkles, Palette, Target,
  CreditCard, Settings, HelpCircle,
  Menu, Moon, Sun, ChevronRight, LogOut, AlertTriangle, Globe,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// Port MVShell (design-source/styles/shell.js) → React. Sidebar + topbar.
// i18n sementara pakai pola desain: data-id/data-en + html[lang] (toggle client + localStorage).
// next-intl (routing) menyusul di langkah berikutnya.

type NavItem = {
  id: string; icon: React.ComponentType<{ size?: number }>;
  idL: string; en: string; href: string; badge?: string; gated?: boolean;
};
type NavEntry = { section: { id: string; en: string } } | NavItem;

const NAV: NavEntry[] = [
  { section: { id: "Menu", en: "Menu" } },
  { id: "dashboard", icon: LayoutDashboard, idL: "Beranda", en: "Dashboard", href: "/dashboard" },
  { id: "integrations", icon: Globe, idL: "Integrasi", en: "Integrations", href: "/integrations" },
  { id: "niches", icon: Target, idL: "Niche", en: "Niches", href: "/niches" },
  { id: "channels", icon: Tv, idL: "Kanal", en: "Channels", href: "/channels" },
  { id: "runs", icon: List, idL: "Produksi", en: "Runs", href: "/runs" },
  { id: "review", icon: AlertTriangle, idL: "Perlu Ditinjau", en: "Needs Review", href: "/review" },
  { id: "analytics", icon: BarChart3, idL: "Analitik", en: "Analytics", href: "/analytics" },
  { id: "schedule", icon: Calendar, idL: "Jadwal", en: "Schedule", href: "/schedule" },
  { id: "compliance", icon: ShieldCheck, idL: "Kepatuhan", en: "Compliance", href: "/compliance" },
  { id: "insights", icon: Sparkles, idL: "Wawasan", en: "Insights", href: "/insights" },
  { id: "niche-studio", icon: Palette, idL: "Niche Studio", en: "Niche Studio", href: "/niche-studio", gated: true },
  // Grup "Konfigurasi" DIPENSIUNKAN (F2-11, §10.F): AI-Engines/API-Keys → key per-channel (vault F2-09);
  // Voice/Visual → channel (F2-05); Niche → Niche Studio + picker channel; Notifikasi → Settings.
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
}: {
  children: React.ReactNode;
  breadcrumb?: { id: string; en?: string; href?: string }[];
}) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [supabase] = useState(() => createClient());
  const [collapsed, setCollapsed] = useState(false);
  const [lang, setLang] = useState<"id" | "en">("id");
  const [mounted, setMounted] = useState(false);
  const [tenant, setTenant] = useState<{ name: string; plan: string; initials: string }>({ name: "", plan: "", initials: "" });
  const [studioOK, setStudioOK] = useState(false);  // F2-10/F3-03: entitlement Niche Studio (gated nav)
  const [gate, setGate] = useState<{ status: string; daysLeft: number | null } | null>(null);  // banner billing gate

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved);
    document.documentElement.lang = saved;
    (async () => {
      const [{ data: tc }, { count }, { data: pls }] = await Promise.all([
        supabase.from("tenant_configs").select("display_handle,plan_type,subscription_status,current_period_end,is_developer,discount_pct").maybeSingle(),
        supabase.from("channels").select("id", { count: "exact", head: true }),
        supabase.from("plan_limits").select("plan_type,display_name,niche_studio"),
      ]);
      const t = tc as { display_handle?: string; plan_type?: string; subscription_status?: string; current_period_end?: string; is_developer?: boolean; discount_pct?: number } | null;
      const planType = t?.plan_type ?? "starter";
      const pl = (pls as { plan_type: string; display_name?: string; niche_studio?: boolean }[] | null)?.find((x) => x.plan_type === planType);
      setStudioOK(Boolean(pl?.niche_studio));   // tier-config (owner 2026-06-21): fasilitas per-tier dari plan_limits.niche_studio
      const h = (t?.display_handle || "").trim();
      const toks = h.split(/[^a-zA-Z0-9]+/).filter(Boolean);
      const initials = toks.slice(0, 2).map((s) => s[0].toUpperCase()).join("") || "T";
      const plan = pl?.display_name || (t?.plan_type ? t.plan_type.charAt(0).toUpperCase() + t.plan_type.slice(1) : "");  // nama tier config-driven
      const nCh = count ?? 0;
      setTenant({ name: h || "Tenant", plan: plan ? `${plan} · ${nCh} kanal` : `${nCh} kanal`, initials });
      // Banner billing-gate (comp/developer exempt). Trial → sisa hari; lapsed → CTA perbarui.
      const comp = Boolean(t?.is_developer) || ((t?.discount_pct ?? 0) >= 100);
      const st = t?.subscription_status, pe = t?.current_period_end;
      if (comp || !st) setGate(null);
      else if (st === "trial" && pe) setGate({ status: "trial", daysLeft: Math.max(0, Math.ceil((new Date(pe).getTime() - Date.now()) / 86400000)) });
      else if (["trial_expired", "grace", "suspended"].includes(st)) setGate({ status: st, daysLeft: null });
      else setGate(null);
    })();
  }, [supabase]);

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
        <div className="sb-tenant">
          <span className="avatar">{tenant.initials}</span>
          <div className="sb-tenant-meta">
            <div className="nm">{tenant.name}</div>
            <div className="pl">{tenant.plan}</div>
          </div>
        </div>
        <nav className="sb-nav">
          {NAV.map((n, i) => {
            if ("section" in n) {
              return <div key={`s${i}`} className="sb-section-title">{n.section.id}</div>;
            }
            if (n.gated && !studioOK) return null;  // Niche Studio: tampil hanya bila ber-entitlement
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
          <button
            className="sb-item"
            onClick={async () => { await createClient().auth.signOut(); window.location.href = "/auth"; }}
            style={{ width: "100%", background: "none", border: "none", fontFamily: "inherit" }}
          >
            <LogOut size={18} /><span className="sb-label"><Bi id="Keluar" en="Sign out" /></span>
          </button>
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
          <div style={{ marginLeft: "auto" }} />
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

        {gate && pathname !== "/billing" && (() => {
          const bg = gate.status === "suspended" ? "var(--danger, #ef4444)"
            : gate.status === "trial" ? "var(--brand, #6366F1)" : "var(--warning, #f59e0b)";
          const dl = gate.daysLeft;
          const msg = gate.status === "trial"
            ? <Bi id={`⏳ Trial berakhir ${dl != null && dl <= 1 ? "besok" : `dalam ${dl} hari`} — upgrade agar produksi tak terhenti.`} en={`⏳ Trial ends ${dl != null && dl <= 1 ? "tomorrow" : `in ${dl} days`} — upgrade to keep producing.`} />
            : gate.status === "trial_expired"
            ? <Bi id="Masa trial berakhir — produksi dijeda. Upgrade untuk melanjutkan." en="Trial ended — production paused. Upgrade to continue." />
            : gate.status === "grace"
            ? <Bi id="Pembayaran tertunggak — perbarui agar produksi tidak berhenti." en="Payment overdue — renew to keep producing." />
            : <Bi id="Produksi dihentikan — aktifkan kembali langganan Anda." en="Production paused — reactivate your subscription." />;
          const cta = gate.status === "suspended" ? { id: "Aktifkan", en: "Reactivate" }
            : gate.status === "grace" ? { id: "Perbarui", en: "Renew" } : { id: "Upgrade", en: "Upgrade" };
          return (
            <div style={{ background: bg, color: "#fff", padding: "0.55rem 1.25rem", display: "flex", alignItems: "center", justifyContent: "center", gap: "1rem", fontSize: "var(--text-sm)", flexWrap: "wrap" }}>
              <span>{msg}</span>
              <Link href="/billing" className="btn btn-sm" style={{ background: "#fff", color: "#111", fontWeight: 600, whiteSpace: "nowrap" }}><Bi id={cta.id} en={cta.en} /></Link>
            </div>
          );
        })()}

        <main className="page"><div className="page-wide">{children}</div></main>
      </div>
    </div>
  );
}
