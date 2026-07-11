"use client";

import { useState, useEffect, useCallback } from "react";
import { ExternalLink, RotateCcw } from "lucide-react";
import { HELP_LOCATIONS, DEFAULT_HELP } from "@/lib/help-links";

// [D1] Admin — kelola pemetaan tombol Help kontekstual (help_links, migr 0153).
// Dropdown HANYA artikel published (anti-human-error di titik input; server memvalidasi ulang).
// Auto-save saat pilih (pola §3.6) · status = hasil CEK REALITA otomatis, bukan catatan manual.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
type Doc = { slug: string; title: string; title_en: string | null; grp: string; status: string };
type LinkRow = { location_key: string; article_slug: string };

export function HelpLinksAdmin() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [links, setLinks] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await fetch("/api/admin/help-links");
    if (r.ok) {
      const j = await r.json();
      setDocs((j.docs as Doc[]) ?? []);
      setLinks(Object.fromEntries(((j.links as LinkRow[]) ?? []).map((l) => [l.location_key, l.article_slug])));
    }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!savedKey) return; const t = setTimeout(() => setSavedKey(null), 2000); return () => clearTimeout(t); }, [savedKey]);

  const published = docs.filter((d) => d.status === "published");
  const pubSet = new Set(published.map((d) => d.slug));

  async function setLink(key: string, slug: string) {
    setErr(null);
    const prev = links;
    setLinks({ ...links, [key]: slug }); // optimistis; rollback bila gagal
    const r = await fetch("/api/admin/help-links", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ location_key: key, article_slug: slug }) });
    if (r.ok) setSavedKey(key);
    else { setLinks(prev); const j = await r.json().catch(() => ({})); setErr(j.error === "article_not_published" ? "Artikel tujuan tidak published." : `Gagal menyimpan (${j.error ?? r.status}).`); }
  }
  async function reset(key: string) {
    setErr(null);
    const r = await fetch("/api/admin/help-links", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ location_key: key }) });
    if (r.ok) { const { [key]: _drop, ...rest } = links; setLinks(rest); setSavedKey(key); }
    else setErr("Gagal reset.");
  }

  if (loading) return <div className="muted" style={{ padding: "2rem", textAlign: "center" }}>Memuat…</div>;

  const groups = [...new Map(HELP_LOCATIONS.map((l) => [l.group.id, l.group])).values()];
  return (
    <div className="card card-pad">
      <p className="muted" style={{ fontSize: "var(--text-sm)", margin: "0 0 1rem" }}>
        <Bi id="Atur artikel panduan yang dibuka tiap tombol ? di panel tenant. Pilihan tersimpan otomatis & langsung berlaku (tanpa deploy). Baris tanpa pilihan memakai bawaan sistem."
            en="Set which guide article each ? button in the tenant panel opens. Choices save automatically & apply instantly (no deploy). Rows without a choice use the system default." />
      </p>
      {err && <p style={{ color: "var(--error)", fontSize: "var(--text-sm)" }}>{err}</p>}
      {groups.map((g) => (
        <div key={g.id} style={{ marginBottom: "1.25rem" }}>
          <div className="label" style={{ textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "var(--text-xs)", marginBottom: ".5rem" }}><Bi id={g.id} en={g.en} /></div>
          {HELP_LOCATIONS.filter((l) => l.group.id === g.id).map((l) => {
            const overridden = l.key in links;
            const eff = links[l.key] ?? l.defaultSlug;
            const broken = overridden && !pubSet.has(links[l.key]); // di-set lalu artikelnya di-unpublish → runtime pakai bawaan
            return (
              <div key={l.key} style={{ display: "flex", alignItems: "center", gap: ".625rem", padding: ".4rem 0", borderBottom: "1px solid var(--border-subtle)", flexWrap: "wrap" }}>
                <span style={{ width: 250, fontSize: "var(--text-sm)" }}>? <Bi id={l.label.id} en={l.label.en} /></span>
                <select className="input" style={{ maxWidth: 320, flex: 1 }} value={pubSet.has(eff) ? eff : ""} onChange={(e) => e.target.value && setLink(l.key, e.target.value)}>
                  {!pubSet.has(eff) && <option value="">({eff} — tidak published)</option>}
                  {published.map((d) => <option key={d.slug} value={d.slug}>{d.title}{DEFAULT_HELP[l.key] === d.slug ? " (bawaan)" : ""} · {d.grp}</option>)}
                </select>
                <a href={`/docs?a=${broken ? l.defaultSlug : eff}`} target="_blank" rel="noopener" className="btn btn-ghost btn-sm" title="Pratinjau / Preview" aria-label="Pratinjau"><ExternalLink size={13} /></a>
                {broken
                  ? <span className="badge badge-warning" style={{ fontSize: "0.5625rem" }}><Bi id="artikel tidak published — memakai bawaan" en="article unpublished — using default" /></span>
                  : <span className="badge badge-success" style={{ fontSize: "0.5625rem" }}>✓</span>}
                {overridden && <button className="btn btn-ghost btn-sm" title="Reset ke bawaan / Reset to default" onClick={() => reset(l.key)}><RotateCcw size={12} /> <Bi id="bawaan" en="default" /></button>}
                {savedKey === l.key && <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="✓ Tersimpan" en="✓ Saved" /></span>}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
