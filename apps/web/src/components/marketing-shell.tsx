"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Zap, Moon, Sun, Menu, Video, Send } from "lucide-react";

// Port MVMarketing (design-source/styles/marketing.js) → React. Nav + footer untuk halaman publik.
// Brand icons (youtube/telegram) tak ada di lucide → substitusi Video/Send.

const NAV_LINKS = [
  { id: "Fitur", en: "Features", href: "/#features" },
  { id: "Harga", en: "Pricing", href: "/pricing" },
  { id: "Demo", en: "Demo", href: "/demo" },
  { id: "Dokumentasi", en: "Docs", href: "#" },
  { id: "Blog", en: "Blog", href: "#" },
];

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export function MarketingShell({ children, active }: { children: React.ReactNode; active?: string }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [lang, setLang] = useState<"id" | "en">("id");
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved); document.documentElement.lang = saved;
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function switchLang(l: "id" | "en") { setLang(l); document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }

  const fcol = (titleId: string, titleEn: string, links: [string, string][]) => (
    <div className="mk-fcol">
      <div className="mk-ftitle"><Bi id={titleId} en={titleEn} /></div>
      {links.map(([i, e], k) => <a key={k} href="#"><Bi id={i} en={e} /></a>)}
    </div>
  );

  return (
    <>
      <header className={`mk-nav${scrolled ? " scrolled" : ""}`}>
        <div className="mk-nav-inner">
          <a href="/" className="mk-brand"><span className="mk-logo"><Zap size={17} color="#fff" /></span> MesinViral</a>
          <nav className={`mk-links${menuOpen ? " open" : ""}`}>
            {NAV_LINKS.map((l) => (
              <a key={l.id} href={l.href} className={active === l.id ? "active" : ""}><Bi id={l.id} en={l.en} /></a>
            ))}
          </nav>
          <div className="mk-actions">
            <div className="segmented">
              <button aria-selected={lang === "id"} onClick={() => switchLang("id")}>ID</button>
              <button aria-selected={lang === "en"} onClick={() => switchLang("en")}>EN</button>
            </div>
            <button className="btn btn-ghost btn-icon" aria-label="Theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {mounted && theme === "light" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <a href="/auth?view=login" className="btn btn-ghost"><Bi id="Masuk" en="Sign in" /></a>
            <a href="/auth?view=signup" className="btn btn-default"><Bi id="Mulai Gratis" en="Start free" /></a>
          </div>
          <button className="btn btn-ghost btn-icon mk-burger" aria-label="Menu" onClick={() => setMenuOpen((o) => !o)}><Menu size={20} /></button>
        </div>
      </header>

      {children}

      <footer className="mk-foot">
        <div className="mk-foot-inner">
          <div className="mk-foot-top">
            <div className="mk-fbrand">
              <a href="/" className="mk-brand"><span className="mk-logo"><Zap size={17} color="#fff" /></span> MesinViral</a>
              <p data-id>Mesin produksi video YouTube otomatis yang belajar dari channelmu sendiri.</p>
              <p data-en>The automated YouTube video machine that learns from your own channel.</p>
              <div className="mk-social">
                <a href="#" aria-label="YouTube"><Video size={18} /></a>
                <a href="#" aria-label="Telegram"><Send size={18} /></a>
              </div>
            </div>
            <div className="mk-fcols">
              {fcol("Produk", "Product", [["Fitur", "Features"], ["Harga", "Pricing"], ["Demo", "Demo"], ["Roadmap", "Roadmap"]])}
              {fcol("Resources", "Resources", [["Dokumentasi", "Docs"], ["Blog", "Blog"], ["Case Studies", "Case Studies"], ["API", "API"]])}
              {fcol("Perusahaan", "Company", [["Tentang", "About"], ["Kontak", "Contact"], ["Karir", "Careers"]])}
              {fcol("Legal", "Legal", [["Privacy", "Privacy"], ["Terms", "Terms"], ["Refund", "Refund"]])}
            </div>
          </div>
          <div className="mk-foot-bottom">
            <span>© 2026 MesinViral. <span data-id>Dibuat di Indonesia 🇮🇩</span><span data-en>Made in Indonesia 🇮🇩</span></span>
            <div className="mk-foot-meta">
              <a href="#"><span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--success)", display: "inline-block", marginRight: 5 }} /><Bi id="Semua sistem normal" en="All systems normal" /></a>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
