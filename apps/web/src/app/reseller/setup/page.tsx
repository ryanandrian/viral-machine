"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import "../../auth/auth.css";

// [B21] F2 — set password pasca-klik undangan (sesi recovery sudah aktif via /auth/callback).
// Di bawah gate /reseller/* middleware (role agent) — tanpa sesi/peran benar tak pernah sampai sini.
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export default function ResellerSetupPage() {
  const supabase = createClient();
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setErr(null);
    if (pw.length < 8) return setErr("Password minimal 8 karakter. / Min. 8 characters.");
    if (pw !== pw2) return setErr("Konfirmasi tidak cocok. / Passwords do not match.");
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password: pw });
    if (error) { setBusy(false); return setErr(error.message); }
    window.location.href = "/reseller";
  }

  return (
    <div style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: "1.5rem", background: "var(--bg)" }}>
      <div className="auth-card" style={{ width: "min(400px, 100%)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "1rem" }}>
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 34, height: 34, objectFit: "contain", flex: "none" }} />
          <strong style={{ fontSize: "1.0625rem" }}>MesinViral</strong>
          <span className="badge" style={{ background: "var(--brand-soft)", color: "var(--brand)", fontSize: "0.5625rem", padding: "2px 6px" }}>RESELLER</span>
        </div>
        <h1 style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}><Bi id="Buat kata sandi portal" en="Set your portal password" /></h1>
        <p className="lead" style={{ marginBottom: "1rem" }}><Bi id="Sekali ini saja — setelah ini masuk lewat /reseller/login." en="One time only — afterwards sign in at /reseller/login." /></p>
        <div className="form-stack">
          <div><label className="label">Password</label><input className="input" type="password" placeholder="Min. 8 karakter" value={pw} onChange={(e) => setPw(e.target.value)} /></div>
          <div><label className="label"><Bi id="Konfirmasi password" en="Confirm password" /></label><input className="input" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()} /></div>
          <button className="btn btn-default btn-lg" style={{ width: "100%" }} onClick={save} disabled={busy}>{busy ? "…" : <Bi id="Simpan & masuk dasbor" en="Save & open dashboard" />}</button>
          {err && <div style={{ color: "var(--error, #dc2626)", fontSize: "var(--text-sm)" }}>{err}</div>}
        </div>
      </div>
    </div>
  );
}
