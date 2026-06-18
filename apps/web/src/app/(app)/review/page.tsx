"use client";

import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, Check, Trash2, Play, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// OPSI C (QC_CONTENT_ARCHITECTURE §3 / DESAIN §12d.F) — tinjau video 'ready_with_issues':
// lolos render tapi ada catatan QC (mis. durasi meleset). DI DOMAIN KITA (bukan auto-upload YouTube).
// Pakai  → RPC approve_inventory_item → promote ke 'ready' → Publisher publish saat SLOT (KUOTA berkurang
//          saat tayang → tutup cheat: hanya jadi publik via jalur kita yang ber-kuota).
// Buang  → RPC discard_inventory_item → janitor hapus aset S3.
// Read = anon + RLS (content_inventory_tenant_read scope auth.uid()). RPC = security-definer, scoped.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Item = {
  id: number;
  niche: string | null;
  created_at: string;
  metadata: {
    qc_reason?: string;
    recommendation?: string;
    duration_secs?: number;
    size_mb?: number;
    script?: { topic?: string; title?: string };
  } | null;
};

export default function ReviewPage() {
  const supabase = createClient();
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [preview, setPreview] = useState<Record<number, string>>({});
  const [previewBusy, setPreviewBusy] = useState<number | null>(null);

  async function loadPreview(id: number) {
    if (preview[id]) return;
    setPreviewBusy(id);
    try {
      const r = await fetch(`/api/review/preview?id=${id}`);
      const j = await r.json();
      if (r.ok && j.url) setPreview((p) => ({ ...p, [id]: j.url as string }));
      else setToast(`Preview gagal: ${j.error ?? r.status}`);
    } catch (e) {
      setToast(`Preview gagal: ${(e as Error).message}`);
    } finally {
      setPreviewBusy(null);
    }
  }

  const load = useCallback(async () => {
    const { data } = await supabase
      .from("content_inventory")
      .select("id, niche, created_at, metadata")
      .eq("status", "ready_with_issues")
      .order("created_at", { ascending: false });
    setItems((data as Item[]) ?? []);
    setLoading(false);
  }, [supabase]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2800);
    return () => clearTimeout(t);
  }, [toast]);

  async function act(id: number, kind: "approve" | "discard") {
    setBusy(id);
    const fn = kind === "approve" ? "approve_inventory_item" : "discard_inventory_item";
    const { error } = await supabase.rpc(fn, { p_inv_id: id });
    setBusy(null);
    if (error) { setToast(`Gagal: ${error.message}`); return; }
    setItems((arr) => arr.filter((x) => x.id !== id));
    setToast(kind === "approve"
      ? "Video disetujui — akan diterbitkan pada slot berikutnya (kuota berkurang saat tayang)."
      : "Video dibuang.");
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1><Bi id="Perlu Ditinjau" en="Needs Review" /></h1>
          <div className="muted" style={{ fontSize: "var(--text-sm)" }}>
            {loading
              ? "Memuat…"
              : <><b>{items.length}</b> video lolos render tapi ada catatan QC — Anda putuskan: pakai atau buang.</>}
          </div>
        </div>
      </div>

      {!loading && items.length === 0 && (
        <div className="card" style={{ padding: 24, textAlign: "center" }}>
          <span className="muted"><Bi id="Tidak ada video yang perlu ditinjau. 🎉" en="No videos need review. 🎉" /></span>
        </div>
      )}

      <div style={{ display: "grid", gap: 12 }}>
        {items.map((it) => {
          const m = it.metadata ?? {};
          const topic = m.script?.topic || m.script?.title || "(tanpa judul)";
          return (
            <div key={it.id} className="card" style={{ padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <AlertTriangle size={16} style={{ color: "var(--warning, #F59E0B)" }} />
                <b>{topic}</b>
                {it.niche && <span className="muted" style={{ fontSize: "var(--text-sm)" }}>· {it.niche}</span>}
              </div>
              <div className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: 4 }}>
                ❌ {m.qc_reason || "QC tak lolos"}
              </div>
              {m.recommendation && (
                <div style={{ fontSize: "var(--text-sm)", marginBottom: 8 }}>💡 {m.recommendation}</div>
              )}
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: 12 }}>
                {m.duration_secs != null && <>⏱ {Number(m.duration_secs).toFixed(1)}s · </>}
                {m.size_mb != null && <>💾 {m.size_mb} MB · </>}
                {new Date(it.created_at).toLocaleString()}
              </div>
              {preview[it.id] ? (
                <video controls preload="metadata" src={preview[it.id]}
                  style={{ width: "100%", maxWidth: 270, borderRadius: 8, marginBottom: 12, background: "#000", aspectRatio: "9 / 16" }} />
              ) : (
                <button className="btn btn-ghost btn-sm" disabled={previewBusy === it.id}
                  onClick={() => loadPreview(it.id)} style={{ marginBottom: 12 }}>
                  {previewBusy === it.id ? <Loader2 size={15} className="spin" /> : <Play size={15} />}
                  {" "}<Bi id="Preview video" en="Preview video" />
                </button>
              )}
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn" disabled={busy === it.id} onClick={() => act(it.id, "approve")}>
                  <Check size={16} /> <Bi id="Pakai (Terbitkan)" en="Use (Publish)" />
                </button>
                <button className="btn btn-ghost" disabled={busy === it.id} onClick={() => act(it.id, "discard")}>
                  <Trash2 size={16} /> <Bi id="Buang" en="Discard" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {toast && (
        <div className="toast" style={{ position: "fixed", bottom: 24, right: 24, zIndex: 50 }}>{toast}</div>
      )}
    </>
  );
}
