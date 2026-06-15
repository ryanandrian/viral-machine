"use client";

import { useState } from "react";
import Link from "next/link";
import { Play, Command, ExternalLink, ArrowRight, LayoutDashboard, Zap, Tv, List } from "lucide-react";
import "./demo.css";

// A3 Demo — port dari design-source/Demo.html (Hybrid). /demo. Tur produk pakai iframe ke route NYATA internal.
// Mock; nol wiring Supabase. Prefix dm-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Tour = { Icon: typeof Zap; lId: string; lEn: string; url: string; href: string; hId: string; hEn: string; pId: string; pEn: string; aId: string[]; aEn: string[] };
const TOURS: Tour[] = [
  { Icon: LayoutDashboard, lId: "Dashboard", lEn: "Dashboard", url: "app.mesinviral.com/dashboard", href: "/dashboard", hId: "Satu layar, semua kendali", hEn: "One screen, full control", pId: "KPI harian, jadwal, biaya AI, dan compliance score — langsung terlihat begitu login.", pEn: "Daily KPIs, schedule, AI cost, and compliance score — visible the moment you log in.", aId: ["KPI real-time dengan sparkline", "Jadwal & run terbaru", "Biaya AI BYOK transparan"], aEn: ["Real-time KPIs with sparklines", "Schedule & recent runs", "Transparent BYOK AI cost"] },
  { Icon: Zap, lId: "Pipeline Live", lEn: "Live Pipeline", url: "app.mesinviral.com/runs/97", href: "/runs/97", hId: "Pipeline berjalan real-time", hEn: "Pipeline running in real time", pId: "Lihat 8 langkah produksi berjalan dengan log tail langsung — fitur yang tidak ada di kompetitor.", pEn: "Watch all 8 production steps run with a live log tail — a feature no competitor has.", aId: ["Timeline 8 langkah dengan status live", "Log tail color-coded + filter", "Rincian biaya & provider AI"], aEn: ["8-step timeline with live status", "Color-coded log tail + filter", "Cost & AI provider breakdown"] },
  { Icon: Tv, lId: "Channels", lEn: "Channels", url: "app.mesinviral.com/channels", href: "/channels", hId: "Kelola banyak channel", hEn: "Manage multiple channels", pId: "Pantau semua channel dari satu tempat — statistik, status, dan tren views 30 hari.", pEn: "Monitor every channel in one place — stats, status, and 30-day view trends.", aId: ["Kartu channel dengan mini-chart", "Indikator kuota paket", "Status setup per channel"], aEn: ["Channel cards with mini-charts", "Plan quota indicator", "Per-channel setup status"] },
  { Icon: List, lId: "Runs", lEn: "Runs", url: "app.mesinviral.com/runs", href: "/runs", hId: "Riwayat produksi lengkap", hEn: "Full production history", pId: "Filter ratusan run per status & channel, buka drawer detail untuk inspeksi cepat.", pEn: "Filter hundreds of runs by status & channel, open a detail drawer for quick inspection.", aId: ["Tabel runs dengan filter", "Drawer detail per run", "Quick stats harian"], aEn: ["Runs table with filters", "Per-run detail drawer", "Daily quick stats"] },
];

export default function DemoPage() {
  const [i, setI] = useState(0);
  const t = TOURS[i];
  return (
    <>
      <div className="mk-container">
        <div className="dm-h">
          <span className="mk-kicker"><Play size={13} /> <Bi id="Lihat dalam aksi" en="See it in action" /></span>
          <h1><Bi id="MesinViral dalam 2 menit" en="MesinViral in 2 minutes" /></h1>
          <p className="mk-lead mk-center"><Bi id="Tonton walk-through singkat, lalu jelajahi produk aslinya langsung di bawah." en="Watch a short walk-through, then explore the real product right below." /></p>
        </div>
        <div className="dm-video">
          <button className="dm-play" aria-label="Play" onClick={() => window.open(t.href, "_blank", "noopener")}><Play size={28} /></button>
          <div className="dm-vmeta"><Play size={14} /> <Bi id="Walk-through produk · 2:14" en="Product walk-through · 2:14" /></div>
        </div>
      </div>

      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}>
          <h2 className="mk-h2"><Bi id="Tur produk interaktif" en="Interactive product tour" /></h2>
          <p className="mk-lead mk-center"><Bi id="Klik tab untuk menjelajah layar asli MesinViral — bukan screenshot." en="Click a tab to explore the real MesinViral screens — not screenshots." /></p>
        </div>
        <div className="dm-tabs">{TOURS.map((tr, idx) => <button key={tr.lEn} className={`dm-tab${i === idx ? " active" : ""}`} onClick={() => setI(idx)}><tr.Icon size={16} /> <Bi id={tr.lId} en={tr.lEn} /></button>)}</div>
        <div className="dm-stage">
          <div className="dm-browser">
            <div className="dm-browser-bar"><div className="dots"><i /><i /><i /></div><div className="dm-url"><Command size={12} /> {t.url}</div></div>
            <div className="dm-frame"><iframe key={t.href} src={t.href} title="tour" scrolling="no" /></div>
          </div>
          <div className="dm-note">
            <h3><Bi id={t.hId} en={t.hEn} /></h3>
            <p><Bi id={t.pId} en={t.pEn} /></p>
            {t.aId.map((a, ai) => <div className="dm-anno" key={ai}><span className="n">{ai + 1}</span><span><Bi id={t.aId[ai]} en={t.aEn[ai]} /></span></div>)}
          </div>
        </div>
        <div className="mk-center" style={{ marginTop: "1.5rem" }}><Link href={t.href} target="_blank" className="btn btn-secondary"><ExternalLink size={15} /> <Bi id="Buka layar ini di tab baru" en="Open this screen in a new tab" /></Link></div>
      </div></section>

      <section className="mk-section-sm"><div className="mk-container">
        <div className="dm-cta">
          <h2><Bi id="Coba sekarang, gratis" en="Try it now, free" /></h2>
          <p className="mk-lead mk-center" style={{ marginBottom: "1.75rem" }}><Bi id="5 video gratis di trial 7 hari. Tanpa kartu kredit." en="5 free videos in a 7-day trial. No credit card." /></p>
          <Link href="/auth?view=signup" className="btn btn-ai btn-xl"><Bi id="Mulai Gratis" en="Start Free" /> <ArrowRight size={18} /></Link>
        </div>
      </div></section>
    </>
  );
}
