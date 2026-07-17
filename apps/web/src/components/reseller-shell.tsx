"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun, LogOut } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// [B21] F3 — rangka PORTAL RESELLER (cermin AgentShell; satu halaman, topbar sederhana, 1-nuansa).
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export function ResellerShell({ name, agent, status, children }: { name: string; agent: string; status: string; children: React.ReactNode }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    document.documentElement.lang = saved;
  }, []);
  function switchLang(l: "id" | "en") { document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }
  async function logout() {
    await createClient().auth.signOut();
    window.location.href = "/reseller/login";
  }
  return (
    <div style={{ minHeight: "100dvh", background: "var(--bg)" }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem",
        padding: "0.75rem 1.25rem", borderBottom: "1px solid var(--border)", background: "var(--surface-1)",
        position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", minWidth: 0 }}>
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 28, height: 28, objectFit: "contain", flex: "none" }} />
          <strong style={{ whiteSpace: "nowrap" }}>MesinViral <span style={{ color: "var(--brand)" }}>Partner</span></strong>
          <span className="badge badge-brand">RESELLER</span>
          <span className="badge badge-outline" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name} · {agent}</span>
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
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "1.5rem 1.25rem 3rem" }}>{children}</main>
    </div>
  );
}
