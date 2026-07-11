"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Play, Command, MonitorSmartphone, Clapperboard, ArrowRight } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { fetchTrialDays } from "@/lib/plans";
import "./showcase.css";

// Showcase (pengganti /demo, keputusan owner 2026-07-03): (1) screenshot halaman tenant (admin-managed,
// showcase_screens) SEBELUM (2) galeri contoh konten hasil mesin (showcase_videos, MP4 di S3, tanpa batas).
// Tanpa iframe/route internal — /demo lama menampilkan halaman login ke calon tenant (belum register).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
type Screen = { id: string; title: string | null; title_en: string | null; caption: string | null; caption_en: string | null; image_url: string };
type Video = { id: string; title: string | null; title_en: string | null; description: string | null; description_en: string | null; niche_label: string | null; video_url: string; poster_url: string | null };

export default function ShowcasePage() {
  const [screens, setScreens] = useState<Screen[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [trialDays, setTrialDays] = useState(7);
  // Tab per-niche (ketok owner 2026-07-11) — DINAMIS dari niche_label video aktif, pola identik kategori /blog.
  const [nicheTab, setNicheTab] = useState(0);
  useEffect(() => {
    fetchTrialDays().then(setTrialDays);
    const sb = createClient();
    sb.from("showcase_screens").select("id,title,title_en,caption,caption_en,image_url").eq("is_active", true).order("sort_order").then(({ data }) => setScreens((data as Screen[]) ?? []));
    sb.from("showcase_videos").select("id,title,title_en,description,description_en,niche_label,video_url,poster_url").eq("is_active", true).order("sort_order").then(({ data }) => setVideos((data as Video[]) ?? []));
  }, []);

  return (
    <>
      <div className="mk-container">
        <div className="sc-h">
          <span className="mk-kicker"><Play size={13} /> <Bi id="Lihat buktinya" en="See the proof" /></span>
          <h1><Bi id="MesinViral dalam aksi" en="MesinViral in action" /></h1>
          <p className="mk-lead mk-center"><Bi id="Tampilan asli di dalam mesin, dan contoh konten yang benar-benar dihasilkannya." en="Real screens from inside the engine, and real content it actually produced." /></p>
        </div>
      </div>

      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}>
          <span className="mk-kicker"><MonitorSmartphone size={13} /> <Bi id="Di dalam mesin" en="Inside the engine" /></span>
          <h2 className="mk-h2"><Bi id="Tampilan halaman tenant" en="What your workspace looks like" /></h2>
        </div>
        {screens.length === 0 ? <div className="mk-center muted" style={{ padding: "2rem" }}><Bi id="Screenshot segera hadir." en="Screenshots coming soon." /></div> : (
          <div className="sc-screens">{screens.map((s) => (
            <figure className="sc-shot" key={s.id} style={{ margin: 0 }}>
              <div className="sc-shot-bar"><div className="dots"><i /><i /><i /></div><div className="url"><Command size={12} /> app.mesinviral.com</div></div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={s.image_url} alt={s.title ?? "screenshot"} loading="lazy" />
              {(s.title || s.caption) && <figcaption className="cap">
                {s.title && <h3><Bi id={s.title} en={s.title_en ?? s.title} /></h3>}
                {s.caption && <p><Bi id={s.caption} en={s.caption_en ?? s.caption} /></p>}
              </figcaption>}
            </figure>
          ))}</div>
        )}
      </div></section>

      <section className="mk-section"><div className="mk-container">
        <div className="mk-center" style={{ marginBottom: "2rem" }}>
          <span className="mk-kicker"><Clapperboard size={13} /> <Bi id="Hasil kerja mesin" en="What the engine produces" /></span>
          <h2 className="mk-h2"><Bi id="Contoh konten yang dihasilkan" en="Real content, produced automatically" /></h2>
          <p className="mk-lead mk-center"><Bi id="Semua video di bawah dibuat penuh oleh mesin — naskah, suara, visual, sampai render." en="Every video below was fully machine-made — script, voice, visuals, and render." /></p>
        </div>
        {(() => {
          const NICHES = ["Semua", ...Array.from(new Set(videos.map((v) => v.niche_label).filter(Boolean)))] as string[];
          const shown = nicheTab === 0 ? videos : videos.filter((v) => v.niche_label === NICHES[nicheTab]);
          return <>
        {NICHES.length > 2 && (
          <div className="sc-cats">{NICHES.map((n, i) => (
            <button key={n} className={`sc-pill${nicheTab === i ? " sel" : ""}`} onClick={() => setNicheTab(i)}>
              {i === 0 ? <Bi id="Semua" en="All" /> : n}
            </button>
          ))}</div>
        )}
        {videos.length === 0 ? <div className="mk-center muted" style={{ padding: "2rem" }}><Bi id="Contoh konten segera hadir." en="Content examples coming soon." /></div> : (
          <div className="sc-videos">{shown.map((v) => (
            <div className="sc-vid" key={v.id}>
              <div className="phone">
                {v.niche_label && <span className="niche">{v.niche_label}</span>}
                <video src={v.video_url} poster={v.poster_url ?? undefined} controls playsInline preload="metadata" />
              </div>
              {(v.title || v.description) && <div className="vbody">
                {v.title && <h3><Bi id={v.title} en={v.title_en ?? v.title} /></h3>}
                {v.description && <p><Bi id={v.description} en={v.description_en ?? v.description} /></p>}
              </div>}
            </div>
          ))}</div>
        )}
          </>;
        })()}
      </div></section>

      <section className="mk-section-sm"><div className="mk-container">
        <div className="sc-cta">
          <h2><Bi id="Coba sekarang, gratis" en="Try it now, free" /></h2>
          <p className="mk-lead mk-center" style={{ marginBottom: "1.75rem" }}><Bi id={`Trial ${trialDays} hari. Tanpa kartu kredit.`} en={`${trialDays}-day trial. No credit card.`} /></p>
          <Link href="/auth?view=signup" className="btn btn-ai btn-xl"><Bi id="Mulai Gratis" en="Start Free" /> <ArrowRight size={18} /></Link>
        </div>
      </div></section>
    </>
  );
}
