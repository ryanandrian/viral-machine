"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ArrowRight, Star } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Markdown } from "@/lib/md";
import { TestimonialAvatar, type Testimonial } from "@/components/testimonial-avatar";
import "../../blog/blog.css";
import "../../docs/docs.css"; // tipografi baca .dc-body (pelajaran fix blog 81cb11d: tanpa ini paragraf menggumpal)

// [Testimoni softcode 2026-07-12] Isi lengkap case study — tujuan kartu "Baca cerita" di /blog
// (menggantikan fosil link /docs). Rute terpisah dari /blog/[slug] agar slug tak mungkin bentrok.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

export default function CaseStudyPage() {
  const slug = useParams<{ slug: string }>()?.slug as string;
  const [row, setRow] = useState<Testimonial | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    createClient().from("testimonials").select("*").eq("slug", slug).not("story_body", "is", null).maybeSingle()
      .then(({ data }) => { setRow(data as Testimonial | null); setLoading(false); });
  }, [slug]);

  if (loading) return <div className="mk-container muted" style={{ padding: "4rem", textAlign: "center" }}>Memuat…</div>;
  if (!row) return (
    <div className="mk-container" style={{ padding: "4rem", textAlign: "center" }}>
      <p className="muted"><Bi id="Cerita tidak ditemukan." en="Story not found." /></p>
      <Link href="/blog" className="btn btn-secondary btn-sm" style={{ marginTop: "1rem" }}><ArrowLeft size={14} /> <Bi id="Kembali" en="Back" /></Link>
    </div>
  );

  return (
    <div className="mk-container" style={{ maxWidth: 760, paddingTop: "2rem", paddingBottom: "4rem" }}>
      <Link href="/blog" className="btn btn-ghost btn-sm" style={{ marginBottom: "1.25rem" }}><ArrowLeft size={14} /> Case Studies</Link>

      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
        <TestimonialAvatar t={row} size={56} />
        <div>
          <h1 style={{ fontSize: "var(--text-3xl)", fontWeight: 700, margin: 0 }}>{row.person_name}</h1>
          {row.channel_label && <div className="muted" style={{ fontSize: "var(--text-sm)" }}>{row.channel_label}</div>}
        </div>
        {row.metric_value && (
          <div style={{ marginLeft: "auto", textAlign: "right" }}>
            <div style={{ fontSize: "var(--text-2xl)", fontWeight: 800, color: "var(--brand)" }}>{row.metric_value}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id={row.metric_label ?? ""} en={row.metric_label_en ?? row.metric_label ?? ""} /></div>
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 2, marginBottom: "1rem" }}>
        {Array.from({ length: Math.min(5, Math.max(1, row.rating)) }).map((_, k) => <Star key={k} size={15} fill="#FBBF24" color="#FBBF24" />)}
      </div>

      <blockquote style={{ margin: "0 0 2rem", padding: "1rem 1.25rem", borderLeft: "3px solid var(--brand)", background: "var(--bg-elevated)", borderRadius: "0 var(--r-md) var(--r-md) 0", fontStyle: "italic", color: "var(--text-secondary)" }}>
        &quot;<Bi id={row.quote} en={row.quote_en ?? row.quote} />&quot;
      </blockquote>

      <div className="dc-body">
        <span data-id><Markdown source={row.story_body ?? ""} /></span>
        <span data-en><Markdown source={row.story_body_en || row.story_body || ""} /></span>
      </div>

      <div className="mk-center" style={{ marginTop: "3rem" }}>
        <Link href="/auth?view=signup" className="btn btn-ai btn-xl"><Bi id="Mulai Gratis" en="Start Free" /> <ArrowRight size={18} /></Link>
      </div>
    </div>
  );
}
