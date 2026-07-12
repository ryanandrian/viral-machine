"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Tv } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { TestimonialAvatar, type Testimonial } from "@/components/testimonial-avatar";
import "./blog.css";
type Post = { slug: string; title: string; title_en: string | null; excerpt: string | null; excerpt_en: string | null; category: string | null; published_at: string | null; cover: string | null };

// A5 Blog + Case Studies — port dari design-source/Blog.html (Hybrid). /blog. Toggle blog/cases + filter kategori.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const GRAD = ["linear-gradient(135deg,#1e3a8a,#6366F1)", "linear-gradient(135deg,#7f1d1d,#ec4899)", "linear-gradient(135deg,#064e3b,#10b981)", "linear-gradient(135deg,#4c1d95,#8b5cf6)", "linear-gradient(135deg,#0c4a6e,#0ea5e9)", "linear-gradient(135deg,#78350f,#f59e0b)"];
// CASES hardcode DIBUANG 2026-07-12 → tabel `testimonials` (admin: Content → Testimoni; migr 0154)

export default function BlogPage() {
  const [view, setView] = useState<"blog" | "cases">("blog");
  const [cat, setCat] = useState(0);
  const [posts, setPosts] = useState<Post[]>([]);
  const [caseRows, setCaseRows] = useState<Testimonial[]>([]);
  useEffect(() => {
    const sb = createClient();
    sb.from("blog_posts").select("slug,title,title_en,excerpt,excerpt_en,category,published_at,cover").eq("status", "published").order("published_at", { ascending: false }).then(({ data }) => setPosts((data as Post[]) ?? []));
    // Case studies = testimonials (RLS publik hanya baris aktif). Ber-cerita (slug+story) → kartu bisa diklik.
    sb.from("testimonials").select("*").order("sort_order").then(({ data }) => setCaseRows((data as Testimonial[]) ?? []));
  }, []);
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
            <div className="cover" style={p.cover ? { background: `url(${JSON.stringify(p.cover)}) center/cover no-repeat` } : { background: GRAD[i % GRAD.length] }}>{p.category && <span className="cat">{p.category}</span>}</div>
            <div className="pbody"><h3><Bi id={p.title} en={p.title_en ?? p.title} /></h3><p><Bi id={p.excerpt ?? ""} en={p.excerpt_en ?? p.excerpt ?? ""} /></p>
              <div className="pmeta"><span>{p.published_at ? new Date(p.published_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : ""}</span></div>
            </div>
          </Link>
        ))}</div>
        )}
      </> : (
        caseRows.length === 0 ? <div className="mk-center muted" style={{ padding: "2rem" }}><Bi id="Cerita segera hadir." en="Stories coming soon." /></div> :
        <div className="blg-cs-grid">{caseRows.map((t) => {
          const hasStory = !!(t.slug && t.story_body);
          const inner = (<>
            <div className="thumb">{t.photo_url ? <TestimonialAvatar t={t} size={72} /> : <Tv size={32} />}</div>
            <div className="csbody"><div className="ch">{t.channel_label}</div><h3>{t.person_name}</h3>
              {t.metric_value && <><div className="metric">{t.metric_value}</div><div className="ml"><Bi id={t.metric_label ?? ""} en={t.metric_label_en ?? t.metric_label ?? ""} /></div></>}
              {hasStory && <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "1rem", fontSize: "var(--text-xs)", color: "var(--brand)" }}><Bi id="Selengkapnya" en="More" /> →</div>}
            </div></>);
          return hasStory
            ? <Link href={`/case-studies/${t.slug}`} className="blg-cs" key={t.id}>{inner}</Link>
            : <div className="blg-cs" key={t.id} style={{ cursor: "default" }}>{inner}</div>;
        })}</div>
      )}
      <div style={{ height: "4rem" }} />
    </div>
  );
}
