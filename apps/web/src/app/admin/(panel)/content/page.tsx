"use client";

import { useState, useEffect, useCallback } from "react";
import { FileText, Plus, Trash2, Save, Eye } from "lucide-react";
import { Markdown } from "@/lib/md";

// Admin CMS — kelola Blog/Docs/Demo (DB-backed). Tulis markdown → publish → tampil di halaman publik.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Field = { k: string; label: string; type: "text" | "area" | "md" | "select" | "switch" | "number"; opts?: string[] };
const TABS: { key: string; table: string; label: string; fields: Field[]; title: (r: Row) => string }[] = [
  { key: "blog", table: "blog_posts", label: "Blog", title: (r) => (r.title as string) || "(baru)", fields: [
    { k: "title", label: "Judul (ID)", type: "text" }, { k: "title_en", label: "Judul (EN)", type: "text" },
    { k: "slug", label: "Slug", type: "text" }, { k: "category", label: "Kategori", type: "text" },
    { k: "excerpt", label: "Ringkasan (ID)", type: "area" }, { k: "excerpt_en", label: "Ringkasan (EN)", type: "area" },
    { k: "body", label: "Isi (markdown, ID)", type: "md" }, { k: "status", label: "Status", type: "select", opts: ["draft", "published"] },
  ] },
  { key: "docs", table: "docs_articles", label: "Docs", title: (r) => (r.title as string) || "(baru)", fields: [
    { k: "title", label: "Judul (ID)", type: "text" }, { k: "title_en", label: "Judul (EN)", type: "text" },
    { k: "slug", label: "Slug", type: "text" }, { k: "grp", label: "Grup", type: "text" },
    { k: "body", label: "Isi (markdown)", type: "md" }, { k: "sort_order", label: "Urutan", type: "number" },
    { k: "status", label: "Status", type: "select", opts: ["draft", "published"] },
  ] },
  { key: "demo", table: "demo_tours", label: "Demo", title: (r) => (r.label as string) || "(baru)", fields: [
    { k: "label", label: "Label (ID)", type: "text" }, { k: "label_en", label: "Label (EN)", type: "text" },
    { k: "href", label: "Route internal (mis. /dashboard)", type: "text" },
    { k: "heading", label: "Heading", type: "text" }, { k: "caption", label: "Caption", type: "area" },
    { k: "sort_order", label: "Urutan", type: "number" }, { k: "is_active", label: "Aktif", type: "switch" },
  ] },
];
type Row = Record<string, unknown> & { id?: string };

export default function AdminContentPage() {
  const [tab, setTab] = useState(0);
  const [rows, setRows] = useState<Row[]>([]);
  const [sel, setSel] = useState<Row | null>(null);
  const [preview, setPreview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const T = TABS[tab];

  const load = useCallback(async () => {
    const r = await fetch(`/api/admin/content?table=${T.table}`);
    if (r.ok) setRows((await r.json()).rows);
  }, [T.table]);
  useEffect(() => { setSel(null); load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2200); return () => clearTimeout(t); }, [toast]);

  function newRow() { setSel({ status: "draft", is_active: true } as Row); setPreview(false); }
  async function save() {
    if (!sel) return; setBusy(true);
    const method = sel.id ? "PATCH" : "POST";
    const body = sel.id ? { table: T.table, id: sel.id, patch: sel } : { table: T.table, row: sel };
    const r = await fetch("/api/admin/content", { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    setBusy(false);
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setToast("Tersimpan"); setSel(j.row); await load(); } else setToast(`Gagal: ${j.error ?? r.status}`);
  }
  async function del() {
    if (!sel?.id || !confirm("Hapus item ini?")) return; setBusy(true);
    const r = await fetch("/api/admin/content", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: T.table, id: sel.id }) });
    setBusy(false);
    if (r.ok) { setToast("Dihapus"); setSel(null); await load(); } else setToast("Gagal hapus");
  }
  const upd = (k: string, v: unknown) => setSel((s) => ({ ...(s as Row), [k]: v }));

  return (
    <div>
      <h1 style={{ fontSize: "1.375rem", marginBottom: ".25rem", display: "flex", alignItems: "center", gap: ".5rem" }}><FileText size={20} /> Content (CMS)</h1>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Kelola isi halaman Blog, Docs, dan Demo. Markdown → Publish → tampil publik." en="Manage Blog, Docs, and Demo content. Markdown → Publish → live." /></p>

      <div className="segmented" style={{ marginBottom: "1.25rem" }}>{TABS.map((t, i) => <button key={t.key} aria-selected={tab === i} onClick={() => setTab(i)}>{t.label}</button>)}</div>

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1.25rem", alignItems: "start" }}>
        <div className="card" style={{ padding: ".5rem" }}>
          <button className="btn btn-default btn-sm" style={{ width: "100%", marginBottom: ".5rem" }} onClick={newRow}><Plus size={14} /> <Bi id="Baru" en="New" /></button>
          {rows.map((r) => (
            <div key={r.id as string} onClick={() => { setSel(r); setPreview(false); }} style={{ padding: ".5rem .625rem", borderRadius: 8, cursor: "pointer", display: "flex", alignItems: "center", gap: ".5rem", background: sel?.id === r.id ? "var(--surface-2)" : undefined }}>
              <span style={{ flex: 1, fontSize: "var(--text-sm)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{T.title(r)}</span>
              {"status" in r && <span className={`badge ${r.status === "published" ? "badge-success" : "badge-default"}`} style={{ fontSize: "0.5625rem" }}>{r.status as string}</span>}
              {"is_active" in r && <span className={`badge ${r.is_active ? "badge-success" : "badge-default"}`} style={{ fontSize: "0.5625rem" }}>{r.is_active ? "aktif" : "off"}</span>}
            </div>
          ))}
          {rows.length === 0 && <div className="muted" style={{ padding: ".75rem", fontSize: "var(--text-xs)", textAlign: "center" }}>Belum ada.</div>}
        </div>

        <div className="card card-pad">
          {!sel ? <div className="muted" style={{ textAlign: "center", padding: "2rem" }}><Bi id="Pilih item atau buat Baru." en="Select an item or create New." /></div> : (
            <div style={{ display: "grid", gap: ".875rem" }}>
              {T.fields.map((f) => (
                <div key={f.k}>
                  <label className="label">{f.label}{f.type === "md" && <button className="btn btn-ghost btn-sm" style={{ marginLeft: ".5rem", padding: "0 .4rem" }} onClick={() => setPreview((p) => !p)}><Eye size={12} /> {preview ? "Edit" : "Preview"}</button>}</label>
                  {f.type === "text" && <input className="input" value={(sel[f.k] as string) ?? ""} onChange={(e) => upd(f.k, e.target.value)} />}
                  {f.type === "number" && <input className="input" type="number" value={(sel[f.k] as number) ?? 0} onChange={(e) => upd(f.k, parseInt(e.target.value, 10) || 0)} />}
                  {f.type === "area" && <textarea className="input" rows={2} value={(sel[f.k] as string) ?? ""} onChange={(e) => upd(f.k, e.target.value)} />}
                  {f.type === "select" && <div className="radio-row">{f.opts!.map((o) => <span key={o} className={`radio-pill${sel[f.k] === o ? " sel" : ""}`} onClick={() => upd(f.k, o)}>{o}</span>)}</div>}
                  {f.type === "switch" && <label className="switch"><input type="checkbox" checked={!!sel[f.k]} onChange={(e) => upd(f.k, e.target.checked)} /><span className="track" /><span className="thumb" /></label>}
                  {f.type === "md" && (preview
                    ? <div className="card card-pad" style={{ background: "var(--bg)", maxHeight: 360, overflow: "auto" }}><Markdown source={(sel[f.k] as string) ?? ""} /></div>
                    : <textarea className="input input-mono" rows={12} value={(sel[f.k] as string) ?? ""} onChange={(e) => upd(f.k, e.target.value)} placeholder="# Judul&#10;&#10;**tebal** · *miring* · `kode` · - list · [link](https://...)" />)}
                </div>
              ))}
              <div style={{ display: "flex", gap: ".5rem", alignItems: "center" }}>
                <button className="btn btn-default" disabled={busy} onClick={save}><Save size={14} /> <Bi id="Simpan" en="Save" /></button>
                {sel.id && <button className="btn btn-ghost" style={{ color: "var(--danger)" }} disabled={busy} onClick={del}><Trash2 size={14} /> <Bi id="Hapus" en="Delete" /></button>}
                {toast && <span className="muted" style={{ fontSize: "var(--text-xs)", marginLeft: "auto" }}>{toast}</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
