import Link from "next/link";
import { Zap, ArrowLeft } from "lucide-react";

// A8 Error 404 — port dari design-source/Error.html (view 404). Standalone (tanpa shell).
// not-found.tsx ditangkap Next saat route tak ada.

export default function NotFound() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Link href="/" style={{ display: "flex", alignItems: "center", gap: "0.625rem", fontWeight: 600, padding: "1.25rem 2rem", color: "var(--text-primary)", textDecoration: "none" }}>
        <span style={{ width: 28, height: 28, borderRadius: 7, background: "linear-gradient(135deg,var(--brand),var(--accent))", display: "grid", placeItems: "center", color: "#fff" }}><Zap size={16} /></span> MesinViral
      </Link>
      <div style={{ flex: 1, display: "grid", placeItems: "center", padding: "2rem", textAlign: "center" }}>
        <div style={{ maxWidth: 520 }}>
          <div style={{ fontSize: "6rem", fontWeight: 800, letterSpacing: "-0.05em", lineHeight: 1, background: "linear-gradient(135deg,var(--brand),var(--accent))", WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent", marginBottom: "0.5rem" }}>404</div>
          <h1 style={{ fontSize: "var(--text-3xl)", fontWeight: 700, letterSpacing: "-0.025em", margin: "0 0 0.75rem" }}>
            <span data-id>Halaman tidak ditemukan</span><span data-en>Page not found</span>
          </h1>
          <p style={{ fontSize: "var(--text-base)", color: "var(--text-secondary)", lineHeight: 1.6, margin: "0 0 2rem" }}>
            <span data-id>Sepertinya halaman yang Anda cari sudah dipindah atau tidak pernah ada. Mari kembali ke jalur yang benar.</span>
            <span data-en>Looks like the page you&apos;re after moved or never existed. Let&apos;s get you back on track.</span>
          </p>
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/" className="btn btn-default btn-lg"><ArrowLeft size={16} /> <span data-id>Kembali ke beranda</span><span data-en>Back to home</span></Link>
            <Link href="/docs" className="btn btn-outline btn-lg"><span data-id>Buka dokumentasi</span><span data-en>Open docs</span></Link>
          </div>
        </div>
      </div>
    </div>
  );
}
