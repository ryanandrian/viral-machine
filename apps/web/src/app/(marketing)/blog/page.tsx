"use client";

import { useState } from "react";
import Link from "next/link";
import { Tv } from "lucide-react";
import "./blog.css";

// A5 Blog + Case Studies — port dari design-source/Blog.html (Hybrid). /blog. Toggle blog/cases + filter kategori.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const CATS = ["Semua", "Tips Growth", "AI Updates", "Case Studies", "Product News"];
const GRAD = ["linear-gradient(135deg,#1e3a8a,#6366F1)", "linear-gradient(135deg,#7f1d1d,#ec4899)", "linear-gradient(135deg,#064e3b,#10b981)", "linear-gradient(135deg,#4c1d95,#8b5cf6)", "linear-gradient(135deg,#0c4a6e,#0ea5e9)", "linear-gradient(135deg,#78350f,#f59e0b)"];
const POSTS: [string, string, string, string, string, string, string, string][] = [
  ["Tips Growth", "7 hook pattern yang bikin Shorts viral di 2026", "7 hook patterns that make Shorts go viral in 2026", "Analisis 1.000+ video viral: pola hook mana yang konsisten menahan penonton di 3 detik pertama.", "Analyzing 1,000+ viral videos: which hook patterns reliably hold viewers in the first 3 seconds.", "RP", "#1d4ed8", "5 menit"],
  ["AI Updates", "Claude Sonnet 4.6 untuk script: apa yang berubah", "Claude Sonnet 4.6 for scripts: what changed", "Update model terbaru dan dampaknya pada kualitas naskah faceless channel Anda.", "The latest model update and its impact on your faceless channel scripts.", "DA", "#047857", "4 menit"],
  ["Product News", "Memperkenalkan AI Slop Defense Engine", "Introducing the AI Slop Defense Engine", "Bagaimana diversity engine kami melindungi channel dari YouTube AI policy 2026.", "How our diversity engine protects channels from YouTube AI policy 2026.", "SW", "#9f1239", "6 menit"],
  ["Tips Growth", "Jam publish optimal untuk audiens Indonesia", "Optimal publish times for Indonesian audiences", "Data dari ribuan video: slot mana yang menghasilkan engagement tertinggi.", "Data from thousands of videos: which slots drive the highest engagement.", "RP", "#7c3aed", "3 menit"],
  ["Case Studies", "Dari 2 ke 5 video/hari tanpa hire editor", "From 2 to 5 videos/day without hiring an editor", "Perjalanan Misteri Samudra scaling produksi dengan mesin otomatis.", "How Misteri Samudra scaled production with the automation engine.", "RP", "#0c4a6e", "7 menit"],
  ["AI Updates", "BYOK: kenapa transparansi biaya AI penting", "BYOK: why AI cost transparency matters", "Membandingkan model BYOK kami dengan markup tersembunyi kompetitor.", "Comparing our BYOK model against competitor hidden markups.", "DA", "#b45309", "5 menit"],
];
const NAMES: Record<string, string> = { RP: "Riko", DA: "Dimas", SW: "Sarah", FB: "Fajar", JS: "Joko" };
const CASES: [string, string, string, string, string, string][] = [
  ["Misteri Samudra", "Faceless ocean mystery channel", "2.3×", "views dalam 60 hari", "MS", "#1d4ed8"],
  ["Fakta Yang Bikin Mikir", "Educational facts channel", "32.7K", "subs (dari 4K)", "FB", "#047857"],
  ["Jejak Kelam Sejarah", "Dark history storytelling", "5/hari", "auto-publish konsisten", "JS", "#9f1239"],
  ["Sarah Wibowo Agency", "Mengelola 8 channel klien", "8", "channel dari 1 dashboard", "SW", "#7c3aed"],
];

export default function BlogPage() {
  const [view, setView] = useState<"blog" | "cases">("blog");
  const [cat, setCat] = useState(0);
  const cases = view === "cases";
  return (
    <div className="mk-container">
      <div className="blg-h">
        <span className="mk-kicker">{cases ? <Bi id="Cerita sukses" en="Success stories" /> : <Bi id="Wawasan & cerita" en="Insights & stories" />}</span>
        <h1>{cases ? "Case Studies" : "Blog"}</h1>
        <p className="mk-lead mk-center">{cases ? <Bi id="Cerita sukses creator yang scaling dengan MesinViral." en="Success stories from creators scaling with MesinViral." /> : <Bi id="Tips growth, update AI, dan cerita sukses creator." en="Growth tips, AI updates, and creator success stories." />}</p>
      </div>

      <div className="blg-view-toggle"><div className="segmented"><button aria-selected={!cases} onClick={() => setView("blog")}>Blog</button><button aria-selected={cases} onClick={() => setView("cases")}>Case Studies</button></div></div>

      {!cases ? <>
        <div className="blg-cats">{CATS.map((c, i) => <button key={c} className={`blg-pill${cat === i ? " sel" : ""}`} onClick={() => setCat(i)}>{c}</button>)}</div>
        <div className="blg-grid">{POSTS.map(([c, t, ten, ex, exen, av, col, rt], i) => (
          <Link href="/docs" className="blg-post" key={t}>
            <div className="cover" style={{ background: GRAD[i % GRAD.length] }}><span className="cat">{c}</span></div>
            <div className="pbody"><h3><Bi id={t} en={ten} /></h3><p><Bi id={ex} en={exen} /></p>
              <div className="pmeta"><span className="av" style={{ background: col }}>{av}</span><span>{NAMES[av]}</span><span>·</span><span>10 Jun 2026</span><span>·</span><span>{rt}</span></div>
            </div>
          </Link>
        ))}</div>
      </> : (
        <div className="blg-cs-grid">{CASES.map(([name, desc, metric, ml, av, col]) => (
          <Link href="/docs" className="blg-cs" key={name}><div className="thumb"><Tv size={32} /></div>
            <div className="csbody"><div className="ch">{desc}</div><h3>{name}</h3><div className="metric">{metric}</div><div className="ml">{ml}</div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "1rem", fontSize: "var(--text-xs)", color: "var(--brand)" }}><Bi id="Baca cerita" en="Read story" /> →</div>
            </div></Link>
        ))}</div>
      )}
      <div style={{ height: "4rem" }} />
    </div>
  );
}
