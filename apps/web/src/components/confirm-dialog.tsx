"use client";
import { ReactNode } from "react";

/**
 * ConfirmDialog — modal konfirmasi reusable (konsisten design system: token tema + kelas .btn).
 * Dipakai untuk aksi berdampak (mis. Test now = pakai kredit BYOK, Pause = hentikan produksi).
 * title/message terima ReactNode → bisa diisi <Bi> agar bilingual.
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Lanjut",
  cancelLabel = "Batal",
  confirmClass = "btn-default",
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: ReactNode;
  message: ReactNode;
  confirmLabel?: ReactNode;
  cancelLabel?: ReactNode;
  confirmClass?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={busy ? undefined : onCancel}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--bg-elevated)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-lg)",
          boxShadow: "var(--shadow-xl)",
          maxWidth: 440,
          width: "100%",
          padding: "1.25rem",
        }}
      >
        <h3 style={{ margin: "0 0 0.5rem", fontSize: "var(--text-lg)", fontWeight: 700, color: "var(--text-primary)" }}>
          {title}
        </h3>
        <div style={{ fontSize: "var(--text-sm)", lineHeight: 1.55, color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
          {message}
        </div>
        <div style={{ display: "flex", gap: "0.6rem", justifyContent: "flex-end" }}>
          <button className="btn btn-secondary" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button className={`btn ${confirmClass}`} disabled={busy} onClick={onConfirm}>
            {busy ? "Memproses…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
