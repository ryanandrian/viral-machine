"use client";

import { useState } from "react";
import { Search, Clock, Info, AlertTriangle, CheckCircle } from "lucide-react";
import "./docs.css";

// A4 Docs — knowledge base. Artikel "Apa itu BYOK?" konten nyata; sisanya stub "sedang disusun" (jujur).
// Semua kontrol aktif: search filter tree · klik tree = pilih artikel · prev/next cycle · feedback thank-you.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

const TREE: [string, [string, string][]][] = [
  ["Getting Started", [["Memulai dengan MesinViral", "Getting started"], ["Apa itu BYOK?", "What is BYOK?"], ["Onboarding", "Onboarding"]]],
  ["Setup", [["Connect YouTube", "Connect YouTube"], ["API Keys", "API Keys"], ["Niches", "Niches"]]],
  ["Fitur", [["AI Engines", "AI Engines"], ["Schedule", "Schedule"], ["Analytics", "Analytics"], ["Self-Learning", "Self-Learning"], ["AI Slop Defense", "AI Slop Defense"]]],
  ["Lainnya", [["Billing", "Billing"], ["Troubleshooting", "Troubleshooting"], ["FAQ", "FAQ"]]],
];
const FLAT = TREE.flatMap(([, items]) => items.map(([id, en]) => ({ id, en })));
const BYOK = "Apa itu BYOK?";

export default function DocsPage() {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(BYOK);
  const [fb, setFb] = useState<null | "ya" | "tidak">(null);

  const idx = FLAT.findIndex((a) => a.id === active);
  const prev = idx > 0 ? FLAT[idx - 1] : null;
  const next = idx < FLAT.length - 1 ? FLAT[idx + 1] : null;
  const ql = q.trim().toLowerCase();

  return (
    <div className="dc">
      <aside className="dc-side">
        <div className="dc-search"><Search size={15} /><input placeholder="Cari dokumentasi…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <nav className="dc-tree">{TREE.map(([grp, items]) => {
          const vis = items.filter(([id, en]) => !ql || id.toLowerCase().includes(ql) || en.toLowerCase().includes(ql));
          if (vis.length === 0) return null;
          return <div className="dc-grp" key={grp}><div className="gt">{grp}</div>{vis.map(([id, en]) => <button key={en} className={`dc-tree-link${active === id ? " active" : ""}`} onClick={() => { setActive(id); setFb(null); }}><Bi id={id} en={en} /></button>)}</div>;
        })}</nav>
      </aside>

      <main className="dc-main">
        <div className="dc-bc"><Bi id="Dokumentasi" en="Docs" /> / <span className="secondary">{active}</span></div>
        {active === BYOK ? (<>
          <h1><Bi id="Apa itu BYOK?" en="What is BYOK?" /></h1>
          <div className="dc-meta"><span><Clock size={13} style={{ verticalAlign: -2 }} /> <Bi id="4 menit baca" en="4 min read" /></span></div>
          <div className="dc-body">
            <p><span data-id><b style={{ color: "var(--text-primary)" }}>BYOK (Bring Your Own Keys)</b> berarti Anda menggunakan API key milik Anda sendiri dari Anthropic, OpenAI, dan ElevenLabs. MesinViral tidak menyembunyikan biaya AI di balik markup — Anda membayar provider langsung dengan harga asli.</span><span data-en><b style={{ color: "var(--text-primary)" }}>BYOK</b> means you use your own API keys. MesinViral doesn&apos;t hide AI cost behind a markup — you pay providers directly at cost.</span></p>
            <h2><Bi id="Kenapa BYOK?" en="Why BYOK?" /></h2>
            <ul>
              <li><span data-id><b style={{ color: "var(--text-primary)" }}>Transparansi penuh</b> — biaya AI real-time per video.</span><span data-en><b style={{ color: "var(--text-primary)" }}>Full transparency</b> — real-time AI cost per video.</span></li>
              <li><span data-id><b style={{ color: "var(--text-primary)" }}>Tanpa markup</b> — bayar harga provider asli.</span><span data-en><b style={{ color: "var(--text-primary)" }}>No markup</b> — pay providers&apos; real prices.</span></li>
              <li><span data-id><b style={{ color: "var(--text-primary)" }}>Kontrol penuh</b> — atur budget sendiri.</span><span data-en><b style={{ color: "var(--text-primary)" }}>Full control</b> — set your own budget.</span></li>
            </ul>
            <div className="dc-callout info"><span><Info size={18} style={{ color: "var(--info)" }} /></span><div><span data-id>Keys dienkripsi <b style={{ color: "var(--text-primary)" }}>Fernet AES-128</b>, tak pernah di-log.</span><span data-en>Keys are <b style={{ color: "var(--text-primary)" }}>Fernet AES-128</b> encrypted, never logged.</span></div></div>
            <h2><Bi id="Cara setup" en="How to set up" /></h2>
            <p><span data-id>Tambahkan keys di <code>Config → AI Engines</code>, klik <b>Test koneksi</b> (validasi nyata) → Simpan.</span><span data-en>Add keys in <code>Config → AI Engines</code>, click <b>Test connection</b> (real validation) → Save.</span></p>
          </div>
        </>) : (
          <div className="dc-body">
            <h1>{active}</h1>
            <div className="dc-callout warn" style={{ marginTop: "1rem" }}><span><AlertTriangle size={18} style={{ color: "var(--warning)" }} /></span><div><Bi id="Dokumen ini sedang disusun. Sementara, lihat artikel BYOK atau hubungi support." en="This article is being written. Meanwhile, see the BYOK article or contact support." /></div></div>
          </div>
        )}
        <div className="dc-feedback"><span style={{ fontSize: "var(--text-sm)" }}>{fb ? <Bi id="Terima kasih atas masukan Anda!" en="Thanks for your feedback!" /> : <Bi id="Apakah artikel ini membantu?" en="Was this helpful?" />}</span>{!fb && <div style={{ display: "flex", gap: "0.5rem", marginLeft: "auto" }}><button className="btn btn-secondary btn-sm" onClick={() => setFb("ya")}><CheckCircle size={14} /> <Bi id="Ya" en="Yes" /></button><button className="btn btn-secondary btn-sm" onClick={() => setFb("tidak")}><Bi id="Tidak" en="No" /></button></div>}</div>
        <div className="dc-nav-links">
          {prev ? <button className="dc-nav-link" onClick={() => { setActive(prev.id); setFb(null); }}><div className="dir">← <Bi id="Sebelumnya" en="Previous" /></div><div className="ti">{prev.id}</div></button> : <span />}
          {next ? <button className="dc-nav-link next" onClick={() => { setActive(next.id); setFb(null); }}><div className="dir"><Bi id="Berikutnya" en="Next" /> →</div><div className="ti">{next.id}</div></button> : <span />}
        </div>
      </main>
    </div>
  );
}
