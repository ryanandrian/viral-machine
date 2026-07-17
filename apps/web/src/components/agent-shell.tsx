"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Moon, Sun, LogOut, LayoutDashboard, Users, HelpCircle } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// [B21] F2 — rangka PORTAL AGEN "MesinViral Partner" (K2 owner). Satu halaman → topbar sederhana
// (tanpa sidebar), token & komponen design system yang sama (1-nuansa §3.9). Dwibahasa via
// data-id/data-en (tokens.css) + toggle mv-lang persis pola auth/app-shell.
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export function AgentShell({ company, status, children }: { company: string; status: string; children: React.ReactNode }) {
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    document.documentElement.lang = saved;
  }, []);
  function switchLang(l: "id" | "en") { document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }
  async function logout() {
    await createClient().auth.signOut();
    window.location.href = "/agent/login";
  }
  return (
    <div style={{ minHeight: "100dvh", background: "var(--bg)" }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem",
        padding: "0.75rem 1.25rem", borderBottom: "1px solid var(--border)", background: "var(--surface-1)",
        position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", minWidth: 0 }}>
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 28, height: 28, objectFit: "contain", flex: "none" }} />
          <strong style={{ whiteSpace: "nowrap" }}>MesinViral <span style={{ color: "var(--brand)" }}>Partner</span></strong>
          <span className="badge badge-outline" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{company}</span>
          {status !== "active" && <span className="badge badge-error"><Bi id="Ditangguhkan" en="Suspended" /></span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.375rem", flex: "none" }}>
          <button className="btn btn-outline btn-sm" onClick={() => switchLang("id")}>ID</button>
          <button className="btn btn-outline btn-sm" onClick={() => switchLang("en")}>EN</button>
          {mounted && (
            <button className="btn btn-outline btn-sm" aria-label="Theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
            </button>
          )}
          <button className="btn btn-outline btn-sm" onClick={logout}><LogOut size={14} /> <Bi id="Keluar" en="Sign out" /></button>
        </div>
      </header>
      <nav style={{ display: "flex", gap: "0.375rem", maxWidth: 1080, margin: "0 auto", padding: "0.75rem 1.25rem 0" }}>
        <Link className={`btn btn-sm ${pathname === "/agent" ? "btn-default" : "btn-outline"}`} href="/agent"><LayoutDashboard size={13} /> <Bi id="Dasbor" en="Dashboard" /></Link>
        <Link className={`btn btn-sm ${pathname.startsWith("/agent/resellers") ? "btn-default" : "btn-outline"}`} href="/agent/resellers"><Users size={13} /> Reseller</Link>
        {/* Panduan agen — dokumen HTML di tab baru (mandat owner: Help dalam portal, bukan file lepas) */}
        <a className="btn btn-sm btn-outline" href="/panduan/agen.html" target="_blank" rel="noopener noreferrer" style={{ marginLeft: "auto" }}><HelpCircle size={13} /> <Bi id="Panduan" en="Guide" /></a>
      </nav>
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "1rem 1.25rem 3rem" }}>{children}</main>
    </div>
  );
}
