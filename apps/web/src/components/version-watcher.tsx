"use client";

import { useEffect, useState } from "react";

// [Mitigasi muat-ulang otomatis, ketok owner 2026-07-20] Insiden: tab terbuka melintasi deploy FE
// → skrip halaman versi lama bicara ke server versi baru → tombol error sampai Ctrl-Shift-R
// (dialami owner 20-Jul; log "Failed to find Server Action ... older deployment").
// Dua lapis, dua gejala:
//  (1) PROAKTIF: cek /api/version saat tab kembali fokus + tiap 90 dtk → versi berubah →
//      toast kecil "Versi baru tersedia — Muat ulang" (tidak memaksa; kerja user tak terpotong).
//  (2) REAKTIF: chunk/Server-Action versi lama GAGAL dimuat → muat-ulang otomatis SEKALI
//      (pagar sessionStorage anti loop) — kasus di mana halaman memang sudah tak bisa dipakai.
// Fail-soft total: fetch gagal/offline → diam (tak pernah mengganggu).

const POLL_MS = 90_000;
const RELOAD_GUARD_KEY = "mv-ver-auto-reload";
const STALE_PATTERNS = [
  "chunkloaderror",
  "loading chunk",
  "failed to fetch dynamically imported module",
  "failed to find server action",
];

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export function VersionWatcher() {
  const [newVersion, setNewVersion] = useState(false);

  useEffect(() => {
    let initial: string | null = null;
    let stopped = false;

    async function check() {
      try {
        const r = await fetch("/api/version", { cache: "no-store" });
        if (!r.ok) return;
        const j = (await r.json()) as { build?: string };
        const b = (j.build || "").trim();
        if (!b || b === "dev" || stopped) return;
        if (initial === null) { initial = b; return; }
        if (b !== initial) setNewVersion(true);
      } catch { /* offline/transien — diam (fail-soft) */ }
    }

    // Lapis 2 — REAKTIF: aset versi lama gagal dimuat → halaman sudah lumpuh → reload SEKALI.
    function looksStale(msg: unknown): boolean {
      const m = String(msg ?? "").toLowerCase();
      return STALE_PATTERNS.some((p) => m.includes(p));
    }
    function autoReloadOnce() {
      try {
        if (sessionStorage.getItem(RELOAD_GUARD_KEY) === "1") return; // anti loop
        sessionStorage.setItem(RELOAD_GUARD_KEY, "1");
      } catch { /* storage diblok → tetap reload sekali (guard hilang, risiko kecil) */ }
      window.location.reload();
    }
    const onError = (e: ErrorEvent) => { if (looksStale(e.message)) autoReloadOnce(); };
    const onRejection = (e: PromiseRejectionEvent) => {
      const r = e.reason as { message?: string } | undefined;
      if (looksStale(r?.message ?? e.reason)) autoReloadOnce();
    };

    const onWake = () => { if (document.visibilityState === "visible") void check(); };
    void check();
    const timer = setInterval(check, POLL_MS);
    window.addEventListener("focus", onWake);
    document.addEventListener("visibilitychange", onWake);
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      stopped = true;
      clearInterval(timer);
      window.removeEventListener("focus", onWake);
      document.removeEventListener("visibilitychange", onWake);
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);

  if (!newVersion) return null;
  return (
    <div role="status" style={{
      position: "fixed", bottom: "1rem", left: "50%", transform: "translateX(-50%)",
      zIndex: 9999, display: "flex", alignItems: "center", gap: "0.75rem",
      background: "var(--surface-1, #1c1f28)", border: "1px solid var(--border, #2c303b)",
      borderRadius: 10, padding: "0.6rem 0.9rem", boxShadow: "0 6px 24px rgba(0,0,0,.25)",
      fontSize: "0.875rem", maxWidth: "92vw",
    }}>
      <span><Bi id="Versi baru aplikasi tersedia." en="A new app version is available." /></span>
      <button className="btn btn-default btn-sm" onClick={() => window.location.reload()}>
        <Bi id="Muat ulang" en="Reload" />
      </button>
    </div>
  );
}
