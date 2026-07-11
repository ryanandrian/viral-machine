"use client";

import { useState, useEffect, useMemo } from "react";
import { Search, Clock, CheckCircle } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Markdown } from "@/lib/md";
import "./docs.css";

// A4 Docs — DB-backed (docs_articles, admin-managed via CMS). Tree dari grup + isi markdown. Hanya published.
type Doc = { slug: string; grp: string; grp_en: string | null; title: string; title_en: string | null; body: string; body_en: string | null; sort_order: number };

export default function DocsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [q, setQ] = useState("");
  const [active, setActive] = useState<string | null>(null);
  const [fb, setFb] = useState<null | "ya" | "tidak">(null);
  useEffect(() => {
    createClient().from("docs_articles").select("slug,grp,grp_en,title,title_en,body,body_en,sort_order").eq("status", "published").order("sort_order")
      .then(({ data }) => {
        const d = (data as Doc[]) ?? []; setDocs(d);
        // [D1] deep-link help kontekstual: /docs?a=<slug> langsung buka artikelnya (client-only,
        // tanpa useSearchParams → bebas kewajiban Suspense). Slug tak dikenal → fallback artikel pertama.
        const want = new URLSearchParams(window.location.search).get("a");
        const hit = want ? d.find((x) => x.slug === want) : null;
        if (hit) setActive(hit.slug); else if (d[0]) setActive(d[0].slug);
      });
  }, []);

  const ql = q.trim().toLowerCase();
  const groups = useMemo(() => {
    const m = new Map<string, Doc[]>();
    docs.filter((d) => !ql || d.title.toLowerCase().includes(ql) || (d.title_en ?? "").toLowerCase().includes(ql)).forEach((d) => { m.set(d.grp, [...(m.get(d.grp) ?? []), d]); });
    return [...m.entries()];
  }, [docs, ql]);
  const cur = docs.find((d) => d.slug === active) ?? null;
  const idx = docs.findIndex((d) => d.slug === active);
  const prev = idx > 0 ? docs[idx - 1] : null;
  const next = idx >= 0 && idx < docs.length - 1 ? docs[idx + 1] : null;

  return (
    <div className="dc">
      <aside className="dc-side">
        <div className="dc-search"><Search size={15} /><input placeholder="Cari dokumentasi…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <nav className="dc-tree">{groups.map(([grp, items]) => (
          <div className="dc-grp" key={grp}><div className="gt">{grp}</div>{items.map((d) => <button key={d.slug} className={`dc-tree-link${active === d.slug ? " active" : ""}`} onClick={() => { setActive(d.slug); setFb(null); }}><span data-id>{d.title}</span><span data-en>{d.title_en ?? d.title}</span></button>)}</div>
        ))}{docs.length === 0 && <div className="muted" style={{ padding: ".75rem", fontSize: "var(--text-xs)" }}>Memuat…</div>}</nav>
      </aside>

      <main className="dc-main">
        {cur ? (<>
          <div className="dc-bc">Docs / <span className="secondary">{cur.title}</span></div>
          <div className="dc-meta"><span><Clock size={13} style={{ verticalAlign: -2 }} /> Docs</span></div>
          <div className="dc-body"><span data-id><Markdown source={cur.body} /></span><span data-en><Markdown source={cur.body_en || cur.body} /></span></div>
          <div className="dc-feedback"><span style={{ fontSize: "var(--text-sm)" }}>{fb ? <span data-id>Terima kasih atas masukan!</span> : <span data-id>Apakah artikel ini membantu?</span>}{fb ? <span data-en>Thanks for your feedback!</span> : <span data-en>Was this helpful?</span>}</span>{!fb && <div style={{ display: "flex", gap: "0.5rem", marginLeft: "auto" }}><button className="btn btn-secondary btn-sm" onClick={() => setFb("ya")}><CheckCircle size={14} /> <span data-id>Ya</span><span data-en>Yes</span></button><button className="btn btn-secondary btn-sm" onClick={() => setFb("tidak")}><span data-id>Tidak</span><span data-en>No</span></button></div>}</div>
          <div className="dc-nav-links">
            {prev ? <button className="dc-nav-link" onClick={() => { setActive(prev.slug); setFb(null); }}><div className="dir">← Sebelumnya</div><div className="ti">{prev.title}</div></button> : <span />}
            {next ? <button className="dc-nav-link next" onClick={() => { setActive(next.slug); setFb(null); }}><div className="dir">Berikutnya →</div><div className="ti">{next.title}</div></button> : <span />}
          </div>
        </>) : <div className="muted" style={{ padding: "3rem", textAlign: "center" }}>Memuat dokumentasi…</div>}
      </main>
    </div>
  );
}
