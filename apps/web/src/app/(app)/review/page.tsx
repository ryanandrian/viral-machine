"use client";

import { useState, useEffect, useCallback, type ReactNode } from "react";
import { AlertTriangle, Check, Trash2, Play, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/page-header";
import ConfirmDialog from "@/components/confirm-dialog";

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
  const [toast, setToast] = useState<ReactNode | null>(null);
  // Anti-salah-sentuh (owner 2026-07-10: tombol kesenggol langsung eksekusi — insiden nyata):
  // kedua aksi WAJIB lewat ConfirmDialog (komponen sama dgn 5 permukaan destruktif lain — koherensi §3.2).
  const [confirmCfg, setConfirmCfg] = useState<null | { title: ReactNode; message: ReactNode; confirmLabel: ReactNode; confirmClass: string; onConfirm: () => void }>(null);
  const [preview, setPreview] = useState<Record<number, string>>({});
  const [previewBusy, setPreviewBusy] = useState<number | null>(null);

  async function loadPreview(id: number) {
    if (preview[id]) return;
    setPreviewBusy(id);
    try {
      const r = await fetch(`/api/review/preview?id=${id}`);
      const j = await r.json();
      if (r.ok && j.url) setPreview((p) => ({ ...p, [id]: j.url as string }));
      else setToast(<Bi id={`Pratinjau gagal: ${j.error ?? r.status}`} en={`Preview failed: ${j.error ?? r.status}`} />);
    } catch (e) {
      setToast(<Bi id={`Pratinjau gagal: ${(e as Error).message}`} en={`Preview failed: ${(e as Error).message}`} />);
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
    setConfirmCfg(null);
    if (error) { setToast(<Bi id={`Gagal: ${error.message}`} en={`Failed: ${error.message}`} />); return; }
    setItems((arr) => arr.filter((x) => x.id !== id));
    setToast(kind === "approve"
      ? <Bi id="Video disetujui — akan diterbitkan pada slot berikutnya (kuota berkurang saat tayang)." en="Video approved — it will publish at the next slot (quota is used when it goes live)." />
      : <Bi id="Video dibuang." en="Video discarded." />);
  }

  // Konfirmasi SEBELUM eksekusi — sebut judul video agar tenant yakin objeknya benar.
  function askAct(it: Item, kind: "approve" | "discard") {
    const name = it.metadata?.script?.title || it.metadata?.script?.topic || "";
    setConfirmCfg(kind === "approve" ? {
      title: <Bi id="Pakai video ini?" en="Use this video?" />,
      message: <Bi id={`"${name}" masuk antrean tayang dan akan terbit ke YouTube pada slot berikutnya (kuota harian terpakai saat tayang).`} en={`"${name}" joins the publish queue and will go live on YouTube at the next slot (daily quota is used when it airs).`} />,
      confirmLabel: <Bi id="Ya, pakai & terbitkan" en="Yes, use & publish" />,
      confirmClass: "btn-default",
      onConfirm: () => act(it.id, "approve"),
    } : {
      title: <Bi id="Buang video ini?" en="Discard this video?" />,
      message: <Bi id={`"${name}" dihapus permanen dan tidak akan tayang. Mesin otomatis memproduksi konten baru yang lebih segar menggantikannya.`} en={`"${name}" is permanently deleted and won't publish. The engine auto-produces a fresher replacement.`} />,
      confirmLabel: <Bi id="Ya, buang" en="Yes, discard" />,
      confirmClass: "btn-destructive",
      onConfirm: () => act(it.id, "discard"),
    });
  }

  return (
    <>
      <PageHeader icon={AlertTriangle} title={<Bi id="Perlu Ditinjau" en="Needs Review" />}
        subtitle={loading ? <Bi id="Memuat…" en="Loading…" /> : <><b>{items.length}</b> <Bi id="video lolos render tapi ada catatan QC — Anda putuskan: pakai atau buang." en="videos rendered fine but have QC notes — you decide: use or discard." /></>} />

      {!loading && items.length === 0 && (
        <div className="card" style={{ padding: 24, textAlign: "center" }}>
          <span className="muted"><Bi id="Tidak ada video yang perlu ditinjau. 🎉" en="No videos need review. 🎉" /></span>
        </div>
      )}

      <div style={{ display: "grid", gap: 12 }}>
        {items.map((it) => {
          const m = it.metadata ?? {};
          // Judul AKHIR dulu (identik YouTube/Runs — 1 konten = 1 nama), fallback topik.
          const topic: ReactNode = m.script?.title || m.script?.topic || <Bi id="(tanpa judul)" en="(untitled)" />;
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
                <button className="btn" disabled={busy === it.id} onClick={() => askAct(it, "approve")}>
                  <Check size={16} /> <Bi id="Pakai (Terbitkan)" en="Use (Publish)" />
                </button>
                <button className="btn btn-ghost" disabled={busy === it.id} onClick={() => askAct(it, "discard")}>
                  <Trash2 size={16} /> <Bi id="Buang" en="Discard" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <ConfirmDialog
        open={!!confirmCfg}
        title={confirmCfg?.title}
        message={confirmCfg?.message}
        confirmLabel={confirmCfg?.confirmLabel}
        cancelLabel={<Bi id="Batal" en="Cancel" />}
        confirmClass={confirmCfg?.confirmClass}
        busy={busy !== null}
        onConfirm={() => confirmCfg?.onConfirm()}
        onCancel={() => setConfirmCfg(null)}
      />

      {toast && (
        <div className="toast" style={{ position: "fixed", bottom: 24, right: 24, zIndex: 50 }}>{toast}</div>
      )}
    </>
  );
}
