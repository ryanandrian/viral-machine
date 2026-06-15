"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Clock } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Markdown } from "@/lib/md";
import "../blog.css";

type Post = { title: string; title_en: string | null; body: string; body_en: string | null; category: string | null; published_at: string | null };

export default function BlogArticle() {
  const slug = useParams<{ slug: string }>()?.slug as string;
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    createClient().from("blog_posts").select("title,title_en,body,body_en,category,published_at").eq("slug", slug).eq("status", "published").maybeSingle()
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
      <div className="dc-body"><span data-id><Markdown source={post.body} /></span><span data-en><Markdown source={post.body_en || post.body} /></span></div>
    </div>
  );
}
