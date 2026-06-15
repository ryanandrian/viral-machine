"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Play, Command, ExternalLink, ArrowRight } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./demo.css";

// A3 Demo — tur produk DB-backed (demo_tours, admin-managed via CMS). iframe ke route internal nyata.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
type Tour = { id: string; label: string; label_en: string | null; href: string; heading: string | null; heading_en: string | null; caption: string | null; caption_en: string | null; bullets: string[]; bullets_en: string[] };

export default function DemoPage() {
  const [tours, setTours] = useState<Tour[]>([]);
  const [i, setI] = useState(0);
  useEffect(() => {
    createClient().from("demo_tours").select("id,label,label_en,href,heading,heading_en,caption,caption_en,bullets,bullets_en").eq("is_active", true).order("sort_order").then(({ data }) => setTours((data as Tour[]) ?? []));
  }, []);
  const t = tours[i];

  return (
    <>
      <div className="mk-container">
        <div className="dm-h">
          <span className="mk-kicker"><Play size={13} /> <Bi id="Lihat dalam aksi" en="See it in action" /></span>
          <h1><Bi id="MesinViral dalam aksi" en="MesinViral in action" /></h1>
          <p className="mk-lead mk-center"><Bi id="Jelajahi layar asli MesinViral langsung di bawah — bukan screenshot." en="Explore real MesinViral screens right below — not screenshots." /></p>
        </div>
        {t && (
          <div className="dm-video">
            <button className="dm-play" aria-label="Play" onClick={() => window.open(t.href, "_blank", "noopener")}><Play size={28} /></button>
            <div className="dm-vmeta"><Play size={14} /> <Bi id="Buka layar live" en="Open live screen" /></div>
          </div>
        )}
      </div>

      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}>
          <h2 className="mk-h2"><Bi id="Tur produk interaktif" en="Interactive product tour" /></h2>
        </div>
        {tours.length === 0 ? <div className="mk-center muted">Memuat tur…</div> : (<>
          <div className="dm-tabs">{tours.map((tr, idx) => <button key={tr.id} className={`dm-tab${i === idx ? " active" : ""}`} onClick={() => setI(idx)}>{tr.label}</button>)}</div>
          {t && (
            <div className="dm-stage">
              <div className="dm-browser">
                <div className="dm-browser-bar"><div className="dots"><i /><i /><i /></div><div className="dm-url"><Command size={12} /> app.mesinviral.com{t.href}</div></div>
                <div className="dm-frame"><iframe key={t.href} src={t.href} title="tour" scrolling="no" /></div>
              </div>
              <div className="dm-note">
                <h3><Bi id={t.heading ?? t.label} en={t.heading_en ?? t.label_en ?? t.label} /></h3>
                <p><Bi id={t.caption ?? ""} en={t.caption_en ?? t.caption ?? ""} /></p>
                {(t.bullets ?? []).map((a, ai) => <div className="dm-anno" key={ai}><span className="n">{ai + 1}</span><span><Bi id={a} en={(t.bullets_en ?? [])[ai] ?? a} /></span></div>)}
              </div>
            </div>
          )}
          {t && <div className="mk-center" style={{ marginTop: "1.5rem" }}><Link href={t.href} target="_blank" className="btn btn-secondary"><ExternalLink size={15} /> <Bi id="Buka layar ini di tab baru" en="Open this screen in a new tab" /></Link></div>}
        </>)}
      </div></section>

      <section className="mk-section-sm"><div className="mk-container">
        <div className="dm-cta">
          <h2><Bi id="Coba sekarang, gratis" en="Try it now, free" /></h2>
          <p className="mk-lead mk-center" style={{ marginBottom: "1.75rem" }}><Bi id="Trial 7 hari. Tanpa kartu kredit." en="7-day trial. No credit card." /></p>
          <Link href="/auth?view=signup" className="btn btn-ai btn-xl"><Bi id="Mulai Gratis" en="Start Free" /> <ArrowRight size={18} /></Link>
        </div>
      </div></section>
    </>
  );
}
