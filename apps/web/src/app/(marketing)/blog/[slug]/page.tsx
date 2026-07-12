"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Clock } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Markdown } from "@/lib/md";
import "../blog.css";
// FIX 2026-07-12 (keluhan owner "paragraf menggumpal"): halaman ini memakai kelas .dc-body
// tapi gayanya hidup di docs.css yang TIDAK pernah diimpor di route blog → tipografi artikel
// (margin paragraf, line-height 1.75, ritme h2, list) mati total. Impor = mengaktifkannya.
import "../../docs/docs.css";

type Post = { title: string; title_en: string | null; body: string; body_en: string | null; category: string | null; published_at: string | null; cover: string | null };

export default function BlogArticle() {
  const slug = useParams<{ slug: string }>()?.slug as string;
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    createClient().from("blog_posts").select("title,title_en,body,body_en,category,published_at,cover").eq("slug", slug).eq("status", "published").maybeSingle()
      .then(({ data }) => { setPost(data as Post | null); setLoading(false); });
  }, [slug]);

  if (loading) return <div className="mk-container muted" style={{ padding: "4rem", textAlign: "center" }}>Memuat…</div>;
  if (!post) return (
    <div className="mk-container" style={{ padding: "4rem", textAlign: "center" }}>
      <p className="muted">Artikel tidak ditemukan.</p>
      <Link href="/blog" className="btn btn-secondary btn-sm" style={{ marginTop: "1rem" }}><ArrowLeft size={14} /> Blog</Link>
    </div>
  );

  return (
    <div className="mk-container" style={{ maxWidth: 760, paddingTop: "2rem", paddingBottom: "4rem" }}>
      <Link href="/blog" className="btn btn-ghost btn-sm" style={{ marginBottom: "1rem" }}><ArrowLeft size={14} /> Blog</Link>
      {post.category && <span className="mk-kicker">{post.category}</span>}
      <h1 style={{ fontSize: "var(--text-3xl)", fontWeight: 700, margin: "0.5rem 0" }}><span data-id>{post.title}</span><span data-en>{post.title_en ?? post.title}</span></h1>
      <div className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1.5rem" }}><Clock size={13} style={{ verticalAlign: -2 }} /> {post.published_at ? new Date(post.published_at).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) : ""}</div>
      {/* Hero: feature image 16:9 (1376×768) — setelah judul+tanggal, sebelum isi (keputusan owner 2026-07-12). */}
      {post.cover && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img src={post.cover} alt={post.title} style={{ width: "100%", aspectRatio: "1376 / 768", objectFit: "cover", borderRadius: "var(--r-xl)", border: "1px solid var(--border)", display: "block", margin: "0 0 1.75rem" }} />
      )}
      <div className="dc-body"><span data-id><Markdown source={post.body} /></span><span data-en><Markdown source={post.body_en || post.body} /></span></div>
    </div>
  );
}
