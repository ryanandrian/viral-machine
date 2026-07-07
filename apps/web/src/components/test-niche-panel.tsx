"use client";

import { useState, useEffect, useCallback, useRef, type ReactNode } from "react";
import { FlaskConical, Loader2, RefreshCw } from "lucide-react";
import ConfirmDialog from "@/components/confirm-dialog";

// Panel TEST NICHE tanpa-publish — SATU card: tombol + konfirmasi + progres stepper NYATA + hasil video
// (aturan UX owner 2026-07-04: status & tombol aksi SATU tempat, terbaca tenant awam).
// Dipakai ADMIN (Pustaka Niche, API /api/admin/niches/[id]/test) & TENANT (Niche Studio, /api/niches/mine/test).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type TestRun = { status: string; qc_passed: boolean | null; viral_score: number | null; topic: string | null; elapsed_seconds: number | null; error_message: string | null; youtube_video_id?: string | null; youtube_url?: string | null };
type TestProgress = { step: number; total: number; label: string; last_log: string };
export type TestInfo = { id: string; status: string; error: string | null; created_at: string; completed_at: string | null; run: TestRun | null; video_url: string | null; progress: TestProgress | null };

const dateID = (iso: string | null) => iso ? new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "—";

export default function TestNichePanel({ getUrl, postUrl, postBody, confirmMessage, title, runLabel, renderResult, onComplete, hideRefresh, hideSummary }: {
  getUrl: string;                       // GET → { test }
  postUrl: string;                      // POST → enqueue
  postBody?: Record<string, unknown>;   // body POST (tenant kirim niche_id)
  confirmMessage: ReactNode;            // pesan biaya/konsekuensi (beda admin vs tenant)
  title?: ReactNode;                    // judul panel (default: Test niche). Konteks channel: "Uji produksi".
  runLabel?: ReactNode;                 // label tombol jalankan (default: Jalankan test).
  renderResult?: (test: TestInfo) => ReactNode;  // slot hasil khusus konteks (channel: tautan YT Studio + status recover). Default: preview buffer.
  onComplete?: (test: TestInfo) => void;         // dipanggil sekali saat test selesai (done/failed) → mis. segarkan banner channel.
  hideRefresh?: boolean;                          // konteks channel: sembunyikan tombol segarkan (panel sudah auto-update).
  hideSummary?: (test: TestInfo) => boolean;      // konteks channel: true → ringkasan hasil terminal (badge/skor/tanggal) ikut hilang (Tutup = SEMUA info hasil hilang). Status berjalan tak terpengaruh.
}) {
  const [test, setTest] = useState<TestInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await fetch(getUrl);
    setLoading(false);
    if (r.ok) { const j = await r.json(); setTest(j.test); }
  }, [getUrl]);
  useEffect(() => { setTest(null); load(); }, [load]);
  useEffect(() => {
    if (!test || !["pending", "producing"].includes(test.status)) return;
    const t = setInterval(load, 5_000);
    return () => clearInterval(t);
  }, [test, load]);
  // onComplete: panggil SEKALI saat test beralih dari berjalan → selesai (done/failed). Konteks channel
  // memakainya untuk menyegarkan banner status (recover). Tak fire bila load pertama sudah terminal.
  const prevStatus = useRef<string | null>(null);
  useEffect(() => {
    if (test && ["done", "published", "qc_failed", "failed"].includes(test.status) &&
        prevStatus.current && ["pending", "producing"].includes(prevStatus.current)) {
      onComplete?.(test);
    }
    prevStatus.current = test?.status ?? null;
  }, [test, onComplete]);

  async function run() {
    setBusy(true); setErr(null);
    const r = await fetch(postUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(postBody ?? {}) });
    const j = await r.json().catch(() => ({}));
    setBusy(false); setConfirm(false);
    if (r.ok) await load();
    else setErr(j.error ?? `gagal (${r.status})`);
  }

  const running = !!test && ["pending", "producing"].includes(test.status);
  // Status SUKSES = done (test_nopub) ATAU published (test channel = upload privat YouTube). Keduanya terminal-sukses.
  const succeeded = !!test && ["done", "published"].includes(test.status);
  // Ringkasan hasil terminal disembunyikan bila konteks memintanya (ditutup tenant / usang) — BUKAN saat berjalan.
  const summaryQuiet = !!test && !running && !!hideSummary?.(test);

  return (
    <div style={{ padding: "0.75rem 1rem", border: "1px solid var(--border-subtle)", borderRadius: "var(--r-md)", background: "var(--bg)", marginBottom: "1rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: ".5rem", fontSize: "var(--text-xs)" }}>
        <FlaskConical size={13} style={{ color: "var(--accent)" }} />
        <strong style={{ fontSize: "var(--text-xs)" }}>{title ?? <Bi id="Test niche (tanpa publish)" en="Niche test (no publish)" />}</strong>
        {test && !summaryQuiet && (<>
          <span className={`badge ${succeeded && test.run?.qc_passed ? "badge-success" : succeeded ? "badge-warning" : test.status === "failed" ? "badge-error" : "badge-info"}`} style={{ fontSize: "0.5625rem" }}>
            {succeeded ? (test.run?.qc_passed ? "QC lolos" : "QC ada catatan") : test.status === "failed" ? "gagal" : test.status === "producing" ? "berjalan…" : "antre"}
          </span>
          {test.run?.viral_score != null && <span className="muted">skor {test.run.viral_score}</span>}
          <span className="muted">{dateID(test.created_at)}</span>
        </>)}
        <span style={{ marginLeft: "auto", display: "inline-flex", gap: ".35rem" }}>
          {!hideRefresh && <button className="btn btn-ghost btn-icon btn-sm" title="Segarkan" disabled={loading} onClick={load}><RefreshCw size={12} /></button>}
          <button className="btn btn-secondary btn-sm" disabled={busy || loading || running} onClick={() => setConfirm(true)}>
            {running ? <><Loader2 size={13} className="spin" /> <Bi id="Berjalan…" en="Running…" /></> : <><FlaskConical size={13} /> {runLabel ?? <Bi id="Jalankan test" en="Run test" />}</>}
          </button>
        </span>
      </div>

      {running && (
        <div style={{ marginTop: ".6rem" }}>
          {test?.progress && test.progress.step > 0 ? (<>
            <div style={{ display: "flex", alignItems: "center", gap: ".5rem", fontSize: "var(--text-xs)", marginBottom: ".35rem" }}>
              <Loader2 size={11} className="spin" style={{ color: "var(--accent)" }} />
              <span style={{ fontWeight: 600 }}><Bi id={`Langkah ${test.progress.step}/${test.progress.total}`} en={`Step ${test.progress.step}/${test.progress.total}`} /></span>
              <span className="muted">{test.progress.label}</span>
            </div>
            <div style={{ height: 5, borderRadius: 3, background: "var(--surface-2)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${Math.round((test.progress.step / Math.max(1, test.progress.total)) * 100)}%`, background: "var(--accent)", transition: "width .6s ease" }} />
            </div>
            {test.progress.last_log && <div className="muted mono" style={{ fontSize: "0.625rem", marginTop: ".35rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{test.progress.last_log}</div>}
          </>) : (
            <div className="muted" style={{ fontSize: "var(--text-xs)", display: "flex", alignItems: "center", gap: ".4rem" }}><Loader2 size={11} className="spin" /> <Bi id="Menunggu giliran mesin…" en="Waiting for an engine slot…" /></div>
          )}
        </div>
      )}

      {err && <div style={{ fontSize: "var(--text-xs)", marginTop: ".35rem", color: "var(--danger)" }}>{err}</div>}
      {renderResult && test ? renderResult(test) : (<>
        {test?.error && test.status === "failed" && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".35rem", color: "var(--danger)" }}>{test.error}</div>}
        {test?.status === "done" && !test.run?.qc_passed && test.run?.error_message && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".35rem" }}>Catatan QC: {test.run.error_message}</div>}
        {test?.video_url && (
          <video controls preload="metadata" src={test.video_url} style={{ marginTop: ".6rem", width: 168, aspectRatio: "9/16", borderRadius: 8, border: "1px solid var(--border)", background: "#000", display: "block" }} />
        )}
        {test?.status === "done" && !test.video_url && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".35rem" }}><Bi id="Video sudah dibersihkan dari penyimpanan (masa simpan uji ±3 hari)." en="Video already cleaned from storage (test retention ±3 days)." /></div>}
      </>)}

      <ConfirmDialog
        open={confirm}
        title={<Bi id="Test produksi niche?" en="Test-produce this niche?" />}
        message={confirmMessage}
        confirmLabel={<Bi id="Jalankan test" en="Run test" />}
        busy={busy}
        onConfirm={run}
        onCancel={() => setConfirm(false)}
      />
    </div>
  );
}
