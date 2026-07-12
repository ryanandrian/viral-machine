"use client";

import { useState, useEffect, useCallback, type CSSProperties } from "react";
import { FileText, Plus, Trash2, Save, Eye } from "lucide-react";
import { Markdown } from "@/lib/md";
import { HelpLinksAdmin } from "@/components/admin/help-links-admin";

// Admin CMS — kelola Blog/Docs/Demo (DB-backed). Tulis markdown → publish → tampil di halaman publik.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Media = { kind: "cover" | "screen" | "poster" | "video" | "testimonial"; preview: "cover" | "wide" | "tall" | "avatar"; hintId: string; hintEn: string };
type Field = { k: string; label: string; type: "text" | "area" | "md" | "select" | "switch" | "number" | "image" | "video"; opts?: string[]; media?: Media };
const TABS: { key: string; table: string; label: string; fields: Field[]; title: (r: Row) => string }[] = [
  { key: "blog", table: "blog_posts", label: "Blog", title: (r) => (r.title as string) || "(baru)", fields: [
    { k: "title", label: "Judul (ID)", type: "text" }, { k: "title_en", label: "Judul (EN)", type: "text" },
    { k: "slug", label: "Slug", type: "text" }, { k: "category", label: "Kategori", type: "text" },
    { k: "cover", label: "Feature image (cover blog — kartu daftar + hero artikel)", type: "image", media: { kind: "cover", preview: "cover",
      hintId: "PNG/JPG, maks 5MB, rasio 16:9 — disarankan 1376×768 px (min lebar 720px). Tampil sebagai cover di daftar blog & gambar hero di halaman artikel. Tersimpan di S3 folder blog-cover/.",
      hintEn: "PNG/JPG, max 5MB, 16:9 ratio — recommended 1376×768 px (min width 720px). Shown as the list cover and the article hero image. Stored in S3 under blog-cover/." } },
    { k: "excerpt", label: "Ringkasan (ID)", type: "area" }, { k: "excerpt_en", label: "Ringkasan (EN)", type: "area" },
    { k: "body", label: "Isi (markdown, ID)", type: "md" }, { k: "status", label: "Status", type: "select", opts: ["draft", "published"] },
  ] },
  { key: "docs", table: "docs_articles", label: "Docs", title: (r) => (r.title as string) || "(baru)", fields: [
    { k: "title", label: "Judul (ID)", type: "text" }, { k: "title_en", label: "Judul (EN)", type: "text" },
    { k: "slug", label: "Slug", type: "text" }, { k: "grp", label: "Grup", type: "text" },
    { k: "body", label: "Isi (markdown)", type: "md" }, { k: "sort_order", label: "Urutan", type: "number" },
    { k: "status", label: "Status", type: "select", opts: ["draft", "published"] },
  ] },
  { key: "screens", table: "showcase_screens", label: "Showcase Layar", title: (r) => (r.title as string) || "(baru)", fields: [
    { k: "title", label: "Nama layar (ID)", type: "text" }, { k: "title_en", label: "Nama layar (EN)", type: "text" },
    { k: "caption", label: "Keterangan singkat (ID)", type: "area" }, { k: "caption_en", label: "Keterangan singkat (EN)", type: "area" },
    { k: "image_url", label: "Screenshot halaman tenant", type: "image", media: { kind: "screen", preview: "wide",
      hintId: "PNG/JPG, maks 5MB, lebar min 1000px (tangkap layar penuh halaman tenant). Tersimpan di S3 folder showcase-screens/.",
      hintEn: "PNG/JPG, max 5MB, min width 1000px (full tenant page screenshot). Stored in S3 under showcase-screens/." } },
    { k: "sort_order", label: "Urutan", type: "number" }, { k: "is_active", label: "Aktif", type: "switch" },
  ] },
  { key: "svideos", table: "showcase_videos", label: "Showcase Video", title: (r) => (r.title as string) || "(baru)", fields: [
    { k: "title", label: "Judul konten (ID)", type: "text" }, { k: "title_en", label: "Judul konten (EN)", type: "text" },
    { k: "niche_label", label: "Label niche (mis. Ocean Mystery)", type: "text" },
    { k: "description", label: "Keterangan singkat (ID)", type: "area" }, { k: "description_en", label: "Keterangan singkat (EN)", type: "area" },
    { k: "video_url", label: "Video contoh (hasil mesin)", type: "video", media: { kind: "video", preview: "tall",
      hintId: "MP4 (H.264) 9:16, maks 80MB. Tersimpan di S3 folder showcase-videos/.",
      hintEn: "MP4 (H.264) 9:16, max 80MB. Stored in S3 under showcase-videos/." } },
    { k: "poster_url", label: "Poster/thumbnail (opsional)", type: "image", media: { kind: "poster", preview: "tall",
      hintId: "PNG/JPG 9:16, lebar min 360px, maks 3MB. Tampil sebelum video di-play.",
      hintEn: "PNG/JPG 9:16, min width 360px, max 3MB. Shown before the video plays." } },
    { k: "sort_order", label: "Urutan", type: "number" }, { k: "is_active", label: "Aktif", type: "switch" },
  ] },
  // Testimoni = Case Studies (migr 0154). Konsistensi isi (kesepakatan owner 2026-07-12):
  // 1 kartu = 1 pilar produk & metrik yang MENGUKUR pilar itu · label channel TANPA angka
  // subscriber karangan · kutipan bebas angka volatil (angka hidup di kolom metrik).
  { key: "testimonials", table: "testimonials", label: "Testimoni", title: (r) => (r.person_name as string) || "(baru)", fields: [
    { k: "person_name", label: "Nama", type: "text" },
    { k: "channel_label", label: "Label channel/peran (mis. Misteri Samudra · niche misteri — tanpa angka subscriber)", type: "text" },
    { k: "quote", label: "Kutipan (ID) — bebas angka volatil", type: "area" }, { k: "quote_en", label: "Kutipan (EN)", type: "area" },
    { k: "metric_value", label: "Angka sorotan (mis. 5/hari)", type: "text" },
    { k: "metric_label", label: "Label angka (ID, mis. publish otomatis)", type: "text" }, { k: "metric_label_en", label: "Label angka (EN)", type: "text" },
    { k: "rating", label: "Rating (1-5)", type: "number" },
    { k: "photo_url", label: "Foto (opsional — tanpa foto: lingkaran inisial otomatis)", type: "image", media: { kind: "testimonial", preview: "avatar",
      hintId: "PNG/JPG persegi, min 200px, maks 3MB. Tersimpan di S3 folder testimonial-photos/.",
      hintEn: "Square PNG/JPG, min 200px, max 3MB. Stored in S3 under testimonial-photos/." } },
    { k: "avatar_color", label: "Warna inisial (hex, dipakai bila tanpa foto — mis. #1d4ed8)", type: "text" },
    { k: "slug", label: "Slug cerita (wajib bila isi cerita — alamat /case-studies/slug)", type: "text" },
    { k: "story_body", label: "Cerita lengkap (markdown, ID — opsional; terisi = kartu Case Study bisa diklik)", type: "md" },
    { k: "story_body_en", label: "Cerita lengkap (EN)", type: "md" },
    { k: "show_on_landing", label: "Tampil di halaman utama (seksi 'Dipercaya creator Indonesia')", type: "switch" },
    { k: "sort_order", label: "Urutan", type: "number" }, { k: "is_active", label: "Aktif", type: "switch" },
  ] },
];
const PREVIEW_STYLE: Record<string, CSSProperties> = {
  cover: { width: 363, height: 168 }, wide: { width: 480, height: 300 }, tall: { width: 168, height: 300 }, avatar: { width: 96, height: 96 },
};
type Row = Record<string, unknown> & { id?: string };

export default function AdminContentPage() {
  const [tab, setTab] = useState(0);
  const [rows, setRows] = useState<Row[]>([]);
  const [sel, setSel] = useState<Row | null>(null);
  const [preview, setPreview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  // Tab terakhir = "Tombol Help" ([D1] softcode) — UI khusus, bukan editor tabel generik.
  const isHelpTab = tab === TABS.length;
  const T = TABS[Math.min(tab, TABS.length - 1)];

  const load = useCallback(async () => {
    if (isHelpTab) return;
    const r = await fetch(`/api/admin/content?table=${T.table}`);
    if (r.ok) setRows((await r.json()).rows);
  }, [T.table, isHelpTab]);
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

  async function uploadMedia(f: Field, file: File) {
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    let url = "/api/admin/showcase/upload";
    if (f.media?.kind === "cover") { url = "/api/admin/content/upload-cover"; fd.append("slug", (sel?.slug as string) ?? ""); }
    else fd.append("kind", f.media?.kind ?? "screen");
    const r = await fetch(url, { method: "POST", body: fd });
    const j = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) { upd(f.k, j.public_url); setToast("Terunggah — jangan lupa Simpan"); }
    else setToast(`Gagal: ${j.error ?? r.status}`);
  }

  return (
    <div>
      <h1 style={{ fontSize: "1.375rem", marginBottom: ".25rem", display: "flex", alignItems: "center", gap: ".5rem" }}><FileText size={20} /> Content (CMS)</h1>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Kelola isi halaman Blog, Docs, dan Demo. Markdown → Publish → tampil publik." en="Manage Blog, Docs, and Demo content. Markdown → Publish → live." /></p>

      <div className="segmented" style={{ marginBottom: "1.25rem" }}>
        {TABS.map((t, i) => <button key={t.key} aria-selected={tab === i} onClick={() => setTab(i)}>{t.label}</button>)}
        <button aria-selected={isHelpTab} onClick={() => setTab(TABS.length)}>Tombol Help</button>
      </div>

      {isHelpTab ? <HelpLinksAdmin /> : (
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
                  {(f.type === "image" || f.type === "video") && (
                    <div style={{ display: "grid", gap: ".5rem" }}>
                      {(sel[f.k] as string) ? (
                        <div style={{ position: "relative", maxWidth: "100%", ...PREVIEW_STYLE[f.media?.preview ?? "cover"] }}>
                          {f.type === "video"
                            ? <video src={sel[f.k] as string} controls playsInline preload="metadata" style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: 8, border: "1px solid var(--border)", display: "block", background: "#000" }} />
                            /* eslint-disable-next-line @next/next/no-img-element */
                            : <img src={sel[f.k] as string} alt={f.label} style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: 8, border: "1px solid var(--border)", display: "block" }} />}
                          <button className="btn btn-ghost btn-sm" style={{ position: "absolute", top: 6, right: 6, color: "var(--danger)", background: "rgba(0,0,0,0.55)" }} onClick={() => upd(f.k, null)}><Trash2 size={12} /></button>
                        </div>
                      ) : <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum ada berkas." en="No file yet." /></div>}
                      <input className="input" type="file" accept={f.type === "video" ? "video/mp4" : "image/png,image/jpeg"} disabled={busy} onChange={(e) => { const fl = e.target.files?.[0]; if (fl) uploadMedia(f, fl); e.target.value = ""; }} />
                      {f.media && <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id={f.media.hintId} en={f.media.hintEn} /></div>}
                    </div>
                  )}
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
      )}
    </div>
  );
}
