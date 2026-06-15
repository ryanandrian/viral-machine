"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Tv } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./blog.css";
type Post = { slug: string; title: string; title_en: string | null; excerpt: string | null; excerpt_en: string | null; category: string | null; published_at: string | null };

// A5 Blog + Case Studies — port dari design-source/Blog.html (Hybrid). /blog. Toggle blog/cases + filter kategori.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const GRAD = ["linear-gradient(135deg,#1e3a8a,#6366F1)", "linear-gradient(135deg,#7f1d1d,#ec4899)", "linear-gradient(135deg,#064e3b,#10b981)", "linear-gradient(135deg,#4c1d95,#8b5cf6)", "linear-gradient(135deg,#0c4a6e,#0ea5e9)", "linear-gradient(135deg,#78350f,#f59e0b)"];
const CASES: [string, string, string, string, string, string][] = [
  ["Misteri Samudra", "Faceless ocean mystery channel", "2.3×", "views dalam 60 hari", "MS", "#1d4ed8"],
  ["Fakta Yang Bikin Mikir", "Educational facts channel", "32.7K", "subs (dari 4K)", "FB", "#047857"],
  ["Jejak Kelam Sejarah", "Dark history storytelling", "5/hari", "auto-publish konsisten", "JS", "#9f1239"],
  ["Sarah Wibowo Agency", "Mengelola 8 channel klien", "8", "channel dari 1 dashboard", "SW", "#7c3aed"],
];

export default function BlogPage() {
  const [view, setView] = useState<"blog" | "cases">("blog");
  const [cat, setCat] = useState(0);
  const [posts, setPosts] = useState<Post[]>([]);
  useEffect(() => { createClient().from("blog_posts").select("slug,title,title_en,excerpt,excerpt_en,category,published_at").eq("status", "published").order("published_at", { ascending: false }).then(({ data }) => setPosts((data as Post[]) ?? [])); }, []);
  const CATS = ["Semua", ...Array.from(new Set(posts.map((p) => p.category).filter(Boolean)))] as string[];
  const cases = view === "cases";
  const shown = cat === 0 ? posts : posts.filter((p) => p.category === CATS[cat]);
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
        {shown.length === 0 ? <div className="mk-center muted" style={{ padding: "2rem" }}>Belum ada artikel.</div> : (
        <div className="blg-grid">{shown.map((p, i) => (
          <Link href={`/blog/${p.slug}`} className="blg-post" key={p.slug}>
            <div className="cover" style={{ background: GRAD[i % GRAD.length] }}>{p.category && <span className="cat">{p.category}</span>}</div>
            <div className="pbody"><h3><Bi id={p.title} en={p.title_en ?? p.title} /></h3><p><Bi id={p.excerpt ?? ""} en={p.excerpt_en ?? p.excerpt ?? ""} /></p>
              <div className="pmeta"><span>{p.published_at ? new Date(p.published_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : ""}</span></div>
            </div>
          </Link>
        ))}</div>
        )}
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
