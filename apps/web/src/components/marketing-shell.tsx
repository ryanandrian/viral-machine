"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Moon, Sun, Menu } from "lucide-react";

// Port MVMarketing (design-source/styles/marketing.js) → React. Nav + footer untuk halaman publik.
// Brand icons (youtube/telegram) tak ada di lucide → substitusi Video/Send.

const NAV_LINKS = [
  // Urutan: Harga SETELAH Showcase (permintaan owner 2026-07-11)
  { id: "Fitur", en: "Features", href: "/#features" },
  { id: "Showcase", en: "Showcase", href: "/showcase" },
  { id: "Harga", en: "Pricing", href: "/pricing" },
  { id: "Dokumentasi", en: "Docs", href: "/docs" },
  { id: "Blog", en: "Blog", href: "/blog" },
];

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export function MarketingShell({ children }: { children: React.ReactNode }) {
  // Highlight menu dari URL AKTUAL (dulu prop `active` hardcode "Fitur" di layout → semua halaman
  // menyorot Features). Anchor "/#..." = beranda; lainnya cocok prefix (mis. /blog/[slug] → Blog).
  const pathname = usePathname();
  const isActive = (href: string) =>
    href.startsWith("/#") ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [lang, setLang] = useState<"id" | "en">("id");
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  // Badge status footer = kondisi NYATA (/api/public/status, sumber sama tab Status & admin System
  // Health). null = belum/gagal dimuat → tampil netral "Status sistem" tanpa klaim (jujur).
  const [allOk, setAllOk] = useState<boolean | null>(null);
  // Identitas perusahaan di © = company_profile.legal_name (SUMBER RESMI, admin-editable
  // /admin/company-profile — mandat owner 2026-07-13: no-hardcode). null = belum termuat → © tanpa nama.
  const [legalName, setLegalName] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/public/status").then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((j) => setAllOk(Boolean(j.all_ok))).catch(() => setAllOk(null));
    // via PINTU RESMI whitelist (bukan tabel langsung — akses anon ke company_profile ditutup migr 0159)
    fetch("/api/public/company").then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((j) => setLegalName(j.legal_name ?? null)).catch(() => setLegalName(null));
  }, []);

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved); document.documentElement.lang = saved;
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function switchLang(l: "id" | "en") { setLang(l); document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }

  // [label_id, label_en, href]. href null = belum ada halaman → SEMBUNYIKAN (no link mati).
  const fcol = (titleId: string, titleEn: string, links: [string, string, string | null][]) => {
    const live = links.filter(([, , h]) => h);
    if (live.length === 0) return null;
    return (
      <div className="mk-fcol">
        <div className="mk-ftitle"><Bi id={titleId} en={titleEn} /></div>
        {live.map(([i, e, h], k) => <a key={k} href={h as string}><Bi id={i} en={e} /></a>)}
      </div>
    );
  };

  return (
    <>
      <header className={`mk-nav${scrolled ? " scrolled" : ""}`}>
        <div className="mk-nav-inner">
          <a href="/" className="mk-brand"><img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 30, height: 30, objectFit: "contain", flex: "none" }} /> MesinViral</a>
          <nav className={`mk-links${menuOpen ? " open" : ""}`}>
            {NAV_LINKS.map((l) => (
              <a key={l.id} href={l.href} className={isActive(l.href) ? "active" : ""}><Bi id={l.id} en={l.en} /></a>
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
              <a href="/" className="mk-brand"><img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 30, height: 30, objectFit: "contain", flex: "none" }} /> MesinViral</a>
              <p data-id>Mesin produksi video YouTube otomatis yang belajar dari channelmu sendiri.</p>
              <p data-en>The automated YouTube video machine that learns from your own channel.</p>
              {/* sosial disembunyikan s/d URL channel tersedia (no link mati) */}
            </div>
            <div className="mk-fcols">
              {fcol("Produk", "Product", [["Fitur", "Features", "/#features"], ["Harga", "Pricing", "/pricing"], ["Showcase", "Showcase", "/showcase"], ["Roadmap", "Roadmap", null]])}
              {fcol("Resources", "Resources", [["Dokumentasi", "Docs", "/docs"], ["Blog", "Blog", "/blog"], ["Case Studies", "Case Studies", null], ["API", "API", null]])}
              {fcol("Perusahaan", "Company", [["Tentang", "About", "/about"], ["Kontak", "Contact", "/about"], ["Karir", "Careers", null]])}
              {fcol("Legal", "Legal", [["Privacy", "Privacy", "/privacy"], ["Terms", "Terms", "/terms"], ["Refund", "Refund", null]])}
            </div>
          </div>
          <div className="mk-foot-bottom">
            {/* © = tahun BERJALAN otomatis + legal_name dari company_profile (no-hardcode, owner 2026-07-13) */}
            <span>© {new Date().getFullYear()} MesinViral.{legalName ? ` Provided By ${legalName}.` : ""}</span>
            <div className="mk-foot-meta">
              <a href="/about"><span style={{ width: 7, height: 7, borderRadius: "50%", background: allOk === null ? "var(--surface-3)" : allOk ? "var(--success)" : "var(--warning)", display: "inline-block", marginRight: 5 }} />{allOk === null ? <Bi id="Status sistem" en="System status" /> : allOk ? <Bi id="Semua sistem normal" en="All systems normal" /> : <Bi id="Sebagian layanan terganggu" en="Some services degraded" />}</a>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
