"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "../../auth/auth.css";

// [B21] F3 — login PORTAL RESELLER (cermin login agen F2; email+password saja):
// TANPA Google — email+password saja, akun di-provision via undangan admin). Publik (di luar
// gate sebenarnya = app_metadata.role='reseller' (middleware + layout portal).
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export default function ResellerLoginPage() {
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function doLogin() {
    setErr(null); setBusy(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
    if (error) { setBusy(false); return setErr(error.message); }
    // Verifikasi peran SEBELUM masuk — akun non-agen di-sign-out (jangan nyangkut redirect loop).
    const { data: { user } } = await supabase.auth.getUser();
    if (user?.app_metadata?.role !== "reseller") {
      await supabase.auth.signOut();
      setBusy(false);
      return setErr("Akun ini bukan akun reseller. / This is not a reseller account.");
    }
    // Honor ?next HANYA menuju /reseller (anti open-redirect). Full reload → middleware sinkron.
    const next = new URLSearchParams(window.location.search).get("next");
    window.location.href = next && next.startsWith("/reseller") ? next : "/reseller";
  }

  return (
    <div style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: "1.5rem", background: "var(--bg)" }}>
      <div className="auth-card" style={{ width: "min(400px, 100%)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "1rem" }}>
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 34, height: 34, objectFit: "contain", flex: "none" }} />
          <strong style={{ fontSize: "1.0625rem" }}>MesinViral</strong>
          <span className="badge" style={{ background: "var(--brand-soft)", color: "var(--brand)", fontSize: "0.5625rem", padding: "2px 6px" }}>RESELLER</span>
        </div>
        <h1 style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}><Bi id="Masuk portal reseller" en="Reseller portal sign in" /></h1>
        <p className="lead" style={{ marginBottom: "1rem" }}><Bi id="Pantau pelanggan bawaan dan komisi bulanan Anda." en="Track your referrals and monthly commissions." /></p>
        <div className="form-stack">
          <div><label className="label">Email</label><input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <div><label className="label">Password</label><input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doLogin()} /></div>
          <button className="btn btn-default btn-lg" style={{ width: "100%" }} onClick={doLogin} disabled={busy}>
            {busy ? "…" : <><Bi id="Masuk" en="Sign in" /> <ArrowRight size={15} /></>}
          </button>
          {err && <div style={{ color: "var(--error, #dc2626)", fontSize: "var(--text-sm)" }}>{err}</div>}
        </div>
        <div className="auth-foot" style={{ marginTop: "1rem" }}>
          <Bi id="Lupa password?" en="Forgot password?" /> <a className="link" href="/auth?view=forgot"><Bi id="Reset di sini" en="Reset here" /></a>
        </div>
      </div>
    </div>
  );
}
