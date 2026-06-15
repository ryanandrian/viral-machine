"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, KeyRound } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// Akun admin (PHASE10 §1) — menutup gap "belum ada fasilitas ganti password".
// Ganti password = sesi admin SENDIRI via auth.updateUser (client-RLS, TANPA service_role — pola B5).
export default function AdminAccountPage() {
  const supabase = createClient();
  const [email, setEmail] = useState<string>("");
  const [role, setRole] = useState<string>("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setEmail(user?.email ?? "");
      setRole((user?.app_metadata?.role as string) ?? "");
    });
  }, [supabase]);

  async function changePassword() {
    setMsg(null);
    if (pw.length < 8) return setMsg({ kind: "err", text: "Password minimal 8 karakter." });
    if (pw !== pw2) return setMsg({ kind: "err", text: "Konfirmasi password tidak cocok." });
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password: pw });
    setBusy(false);
    if (error) return setMsg({ kind: "err", text: error.message });
    setPw(""); setPw2("");
    setMsg({ kind: "ok", text: "Password berhasil diganti." });
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <h1 style={{ fontSize: "1.375rem", marginBottom: "0.25rem" }}>Akun Admin</h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Kelola kredensial akun super-admin Anda.
      </p>

      <div className="card" style={{ padding: "1.25rem", marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.75rem" }}>
          <ShieldCheck size={18} style={{ color: "var(--success, #16a34a)" }} />
          <strong>Identitas</strong>
        </div>
        <div style={{ display: "grid", gap: "0.5rem", fontSize: "0.875rem" }}>
          <div><span style={{ color: "var(--text-muted)" }}>Email: </span>{email || "—"}</div>
          <div><span style={{ color: "var(--text-muted)" }}>Peran: </span><span className="badge" style={{ background: "var(--warning-soft)", color: "var(--warning)", padding: "2px 6px", fontSize: "0.6875rem" }}>{role || "—"}</span></div>
        </div>
      </div>

      <div className="card" style={{ padding: "1.25rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.75rem" }}>
          <KeyRound size={18} />
          <strong>Ganti Password</strong>
        </div>
        <form
          onSubmit={(e) => { e.preventDefault(); if (!busy) changePassword(); }}
          style={{ display: "grid", gap: "0.75rem" }}
        >
          <div>
            <label className="label">Password baru</label>
            <input className="input" type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} />
          </div>
          <div>
            <label className="label">Konfirmasi password baru</label>
            <input className="input" type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
          </div>
          {msg ? (
            <div style={{ color: msg.kind === "ok" ? "var(--success, #16a34a)" : "var(--danger)", fontSize: "0.8125rem" }}>{msg.text}</div>
          ) : null}
          <button className="btn btn-primary" type="submit" disabled={busy} style={{ justifySelf: "start" }}>
            {busy ? "Menyimpan…" : "Simpan password"}
          </button>
        </form>
      </div>
    </div>
  );
}
