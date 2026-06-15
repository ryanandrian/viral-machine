"use client";

import { useState } from "react";
import { Shield, ArrowRight } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "../../auth/auth.css";

// Login ADMIN TERPISAH (keputusan owner 2026-06-15). Publik (di luar group (panel) yang ke-gate).
// HANYA email+password — admin di-provision manual (service_role); NOL signup/Google/reset.
// Gate sebenarnya = app_metadata.role='super_admin' (proxy/middleware + (panel)/layout). Di sini = UX +
// tolak dini akun non-admin (sign-out) supaya tak terjebak loop redirect /dashboard.
export default function AdminLoginPage() {
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function doLogin() {
    setErr(null);
    setBusy(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
    if (error) {
      setBusy(false);
      return setErr(error.message);
    }
    // Verifikasi role SEBELUM masuk. Bukan super-admin → sign-out + pesan (jangan biarkan tenant nyangkut).
    const { data: { user } } = await supabase.auth.getUser();
    if (user?.app_metadata?.role !== "super_admin") {
      await supabase.auth.signOut();
      setBusy(false);
      return setErr("Akun ini bukan admin.");
    }
    // Honor ?next HANYA bila menuju /admin (anti open-redirect). Full reload → cookie/middleware sinkron.
    const next = new URLSearchParams(window.location.search).get("next");
    window.location.href = next && next.startsWith("/admin") ? next : "/admin/tenants";
  }

  return (
    <div
      style={{
        minHeight: "100dvh",
        display: "grid",
        placeItems: "center",
        padding: "1.5rem",
        background: "var(--bg)",
      }}
    >
      <div className="auth-card" style={{ width: "min(400px, 100%)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "1rem" }}>
          <span
            className="sb-logo"
            style={{ background: "linear-gradient(135deg,#F59E0B,#D97757)", width: 34, height: 34, display: "inline-grid", placeItems: "center", borderRadius: 9 }}
          >
            <Shield size={18} />
          </span>
          <strong style={{ fontSize: "1.0625rem" }}>MesinViral</strong>
          <span
            className="badge"
            style={{ background: "var(--warning-soft)", color: "var(--warning)", fontSize: "0.5625rem", padding: "2px 6px" }}
          >
            ADMIN
          </span>
        </div>
        <h1 style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}>Masuk panel admin</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", marginBottom: "1rem" }}>
          Khusus staf MesinViral. Akun di-kelola internal.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) doLogin();
          }}
          style={{ display: "grid", gap: "0.75rem" }}
        >
          <div>
            <label className="label">Email</label>
            <input
              className="input"
              type="email"
              autoComplete="username"
              placeholder="admin@mesinviral.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
            />
          </div>
          {err ? (
            <div style={{ color: "var(--danger)", fontSize: "0.8125rem" }}>{err}</div>
          ) : null}
          <button className="btn btn-primary" type="submit" disabled={busy} style={{ marginTop: "0.25rem" }}>
            {busy ? "Memproses…" : (<>Masuk <ArrowRight size={15} style={{ verticalAlign: -2 }} /></>)}
          </button>
        </form>
      </div>
    </div>
  );
}
