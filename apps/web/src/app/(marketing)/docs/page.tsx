"use client";

import { Search, Clock, Info, AlertTriangle } from "lucide-react";
import "./docs.css";

// A4 Docs — port dari design-source/Docs.html (Hybrid). /docs. Tree + artikel + TOC. Static content.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const TREE: [string, [string, string, boolean][]][] = [
  ["Getting Started", [["Memulai dengan MesinViral", "Getting started", false], ["Apa itu BYOK?", "What is BYOK?", true], ["Onboarding", "Onboarding", false]]],
  ["Setup", [["Connect YouTube", "Connect YouTube", false], ["API Keys", "API Keys", false], ["Niches", "Niches", false]]],
  ["Fitur", [["AI Engines", "AI Engines", false], ["Schedule", "Schedule", false], ["Analytics", "Analytics", false], ["Self-Learning", "Self-Learning", false], ["AI Slop Defense", "AI Slop Defense", false]]],
  ["Lainnya", [["Billing", "Billing", false], ["Troubleshooting", "Troubleshooting", false], ["FAQ", "FAQ", false]]],
];

export default function DocsPage() {
  return (
    <div className="dc">
      <aside className="dc-side">
        <div className="dc-search"><Search size={15} /><input placeholder="Cari dokumentasi…" /><kbd>⌘K</kbd></div>
        <nav className="dc-tree">{TREE.map(([grp, items]) => (
          <div className="dc-grp" key={grp}><div className="gt">{grp}</div>{items.map(([id, en, act]) => <a key={en} href="#" className={act ? "active" : ""}><Bi id={id} en={en} /></a>)}</div>
        ))}</nav>
      </aside>

      <main className="dc-main">
        <div className="dc-bc"><Bi id="Dokumentasi" en="Docs" /> / Getting Started / <span className="secondary"><Bi id="Apa itu BYOK?" en="What is BYOK?" /></span></div>
        <h1><Bi id="Apa itu BYOK?" en="What is BYOK?" /></h1>
        <div className="dc-meta"><span><Clock size={13} style={{ verticalAlign: -2 }} /> <Bi id="4 menit baca" en="4 min read" /></span><span><Bi id="Diperbarui 8 Juni 2026" en="Updated June 8, 2026" /></span></div>
        <div className="dc-body">
          <p><span data-id><b style={{ color: "var(--text-primary)" }}>BYOK (Bring Your Own Keys)</b> berarti Anda menggunakan API key milik Anda sendiri dari Anthropic, OpenAI, dan ElevenLabs. MesinViral tidak menyembunyikan biaya AI di balik markup — Anda membayar provider langsung dengan harga asli, dan melihat setiap rupiah secara transparan.</span><span data-en><b style={{ color: "var(--text-primary)" }}>BYOK (Bring Your Own Keys)</b> means you use your own API keys from Anthropic, OpenAI, and ElevenLabs. MesinViral doesn&apos;t hide AI cost behind a markup — you pay providers directly at cost, and see every rupiah transparently.</span></p>
          <h2 id="kenapa"><Bi id="Kenapa BYOK?" en="Why BYOK?" /></h2>
          <p><Bi id="Model BYOK memberi Anda tiga keuntungan utama:" en="The BYOK model gives you three key advantages:" /></p>
          <ul>
            <li><span data-id><b style={{ color: "var(--text-primary)" }}>Transparansi penuh</b> — lihat biaya AI real-time per video di dashboard.</span><span data-en><b style={{ color: "var(--text-primary)" }}>Full transparency</b> — see real-time AI cost per video in the dashboard.</span></li>
            <li><span data-id><b style={{ color: "var(--text-primary)" }}>Tanpa markup</b> — bayar harga provider asli, kira-kira Rp 75 per video.</span><span data-en><b style={{ color: "var(--text-primary)" }}>No markup</b> — pay providers&apos; actual prices, roughly Rp 75 per video.</span></li>
            <li><span data-id><b style={{ color: "var(--text-primary)" }}>Kontrol penuh</b> — atur budget bulanan dan batas pemakaian sendiri.</span><span data-en><b style={{ color: "var(--text-primary)" }}>Full control</b> — set your own monthly budget and usage limits.</span></li>
          </ul>
          <div className="dc-callout info"><span><Info size={18} style={{ color: "var(--info)" }} /></span><div><span data-id>Keys Anda dienkripsi dengan <b style={{ color: "var(--text-primary)" }}>Fernet AES-128</b> dan tidak pernah disimpan dalam log. Hanya dipakai saat runtime produksi.</span><span data-en>Your keys are encrypted with <b style={{ color: "var(--text-primary)" }}>Fernet AES-128</b> and never stored in logs. Used only at production runtime.</span></div></div>
          <h2 id="setup"><Bi id="Cara setup" en="How to set up" /></h2>
          <p><span data-id>Tambahkan keys Anda di <code>Config → API Keys</code>. Setiap key bisa di-test koneksinya sebelum disimpan:</span><span data-en>Add your keys in <code>Config → API Keys</code>. Each key can be connection-tested before saving:</span></p>
          <pre><code>{`1. Buka Config → API Keys\n2. Klik "Tambah key" untuk provider\n3. Tempel API key Anda\n4. Klik "Test koneksi" → tunggu ✓ hijau\n5. Simpan`}</code></pre>
          <h2 id="biaya"><Bi id="Estimasi biaya" en="Cost estimate" /></h2>
          <p><span data-id>Untuk 5 video/hari, estimasi biaya AI sekitar <b style={{ color: "var(--text-primary)" }}>$51/bulan (~Rp 816K)</b>, dibagi antara Claude (script), ElevenLabs (suara), dan OpenAI (visual). Gunakan kalkulator di halaman Harga untuk simulasi.</span><span data-en>For 5 videos/day, estimated AI cost is about <b style={{ color: "var(--text-primary)" }}>$51/month (~Rp 816K)</b>, split between Claude (script), ElevenLabs (voice), and OpenAI (visual). Use the calculator on the Pricing page to simulate.</span></p>
          <div className="dc-callout warn"><span><AlertTriangle size={18} style={{ color: "var(--warning)" }} /></span><div><span data-id>Selama trial 7 hari Anda bisa pakai kredensial platform (fitur terbatas). Keys wajib lengkap setelah trial berakhir.</span><span data-en>During the 7-day trial you can use platform credentials (limited features). Keys are required after the trial ends.</span></div></div>
          <div className="dc-feedback"><span style={{ fontSize: "var(--text-sm)" }}><Bi id="Apakah artikel ini membantu?" en="Was this helpful?" /></span><div style={{ display: "flex", gap: "0.5rem", marginLeft: "auto" }}><button className="btn btn-secondary btn-sm"><Bi id="Ya" en="Yes" /></button><button className="btn btn-secondary btn-sm"><Bi id="Tidak" en="No" /></button></div></div>
          <div className="dc-nav-links">
            <a href="#" className="dc-nav-link"><div className="dir">← <Bi id="Sebelumnya" en="Previous" /></div><div className="ti"><Bi id="Memulai dengan MesinViral" en="Getting started" /></div></a>
            <a href="#" className="dc-nav-link next"><div className="dir"><Bi id="Berikutnya" en="Next" /> →</div><div className="ti"><Bi id="Setup API Keys" en="Set up API Keys" /></div></a>
          </div>
        </div>
      </main>

      <aside className="dc-toc">
        <div className="tt">Daftar isi</div>
        <a href="#kenapa" className="active"><Bi id="Kenapa BYOK?" en="Why BYOK?" /></a>
        <a href="#setup"><Bi id="Cara setup" en="How to set up" /></a>
        <a href="#biaya"><Bi id="Estimasi biaya" en="Cost estimate" /></a>
      </aside>
    </div>
  );
}
