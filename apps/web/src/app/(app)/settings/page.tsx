"use client";

import { useCallback, useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { User, Shield, Bell, Globe, AlertTriangle, Moon, Monitor, Check, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./settings.css";

// B5 Settings — Phase 9.3 (wired Supabase v2). Profil (email read + display_handle via RPC),
// Keamanan (ganti password via supabase.auth.updateUser — NYATA), Integrasi Telegram (RPC).
// Lang/theme = client toggle. 2FA/sesi/notif-email/danger = placeholder/gate. Config-write lewat
// RPC whitelist set_tenant_config (aman dari escalation).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Tab = "profile" | "security" | "notif" | "language" | "danger";
const NAV: [Tab, React.ReactNode, string, string][] = [
  ["profile", <User size={18} key="p" />, "Profil", "Profile"],
  ["security", <Shield size={18} key="s" />, "Keamanan", "Security"],
  ["notif", <Bell size={18} key="n" />, "Notifikasi", "Notifications"],
  ["language", <Globe size={18} key="l" />, "Bahasa", "Language"],
  ["danger", <AlertTriangle size={18} key="d" />, "Zona berbahaya", "Danger zone"],
];

function Saved({ on }: { on: boolean }) { return on ? <span style={{ color: "var(--success)", fontSize: "var(--text-xs)", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}><Check size={13} /> <Bi id="Tersimpan" en="Saved" /></span> : null; }
function Err({ msg }: { msg: string | null }) { return msg ? <span style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-xs)" }}>{msg}</span> : null; }

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [supabase] = useState(() => createClient());
  const [tab, setTab] = useState<Tab>("profile");
  const [lang, setLang] = useState<"id" | "en">("id");

  const [email, setEmail] = useState("");
  const [handle, setHandle] = useState("");
  const [pw, setPw] = useState(""); const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(""); // which action busy
  const [saved, setSaved] = useState(""); // which saved
  const [err, setErr] = useState<{ k: string; m: string } | null>(null);

  // Integrasi (YouTube/Telegram/IG/TikTok) DIPINDAH ke halaman MAIN /integrations (F2-08, §10.F).

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    setEmail(user?.email ?? "");
    const { data } = await supabase.from("tenant_configs").select("display_handle").maybeSingle();
    const t = data as { display_handle?: string } | null;
    setHandle(t?.display_handle ?? "");
  }, [supabase]);
  useEffect(() => {
    load();
    const s = (localStorage.getItem("mv-lang") as "id" | "en") || "id"; setLang(s); document.documentElement.lang = s;
  }, [load]);

  function pickLang(l: "id" | "en") { setLang(l); document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }
  const flash = (k: string) => { setSaved(k); setTimeout(() => setSaved(""), 2500); };

  async function saveProfile() {
    setErr(null); setBusy("profile");
    const { error } = await supabase.rpc("set_tenant_config", { p_display_handle: handle.trim() });
    setBusy(""); if (error) return setErr({ k: "profile", m: error.message }); flash("profile");
  }
  async function updatePassword() {
    setErr(null);
    if (pw.length < 8) return setErr({ k: "security", m: "Password minimal 8 karakter." });
    if (pw !== pw2) return setErr({ k: "security", m: "Konfirmasi tidak cocok." });
    setBusy("security");
    const { error } = await supabase.auth.updateUser({ password: pw });
    setBusy(""); if (error) return setErr({ k: "security", m: error.message });
    setPw(""); setPw2(""); flash("security");
  }
  return (
    <>
      <div className="page-head"><h1><Bi id="Pengaturan" en="Settings" /></h1></div>
      <div className="set-layout">
        <nav className="set-nav">
          {NAV.map(([id, ic, t, en]) => (
            <div key={id} className={`set-item${id === "danger" ? " danger" : ""}${tab === id ? " active" : ""}`} onClick={() => { setTab(id); window.scrollTo(0, 0); }}>{ic}<span><Bi id={t} en={en} /></span></div>
          ))}
        </nav>

        <main className="set-main">
          {tab === "profile" && (
            <>
              <div className="sec-card">
                <h2><Bi id="Profil" en="Profile" /></h2>
                <p className="desc"><Bi id="Informasi akun Anda." en="Your account information." /></p>
                <div className="fld-2">
                  <div className="fld"><label className="label"><Bi id="Nama tampilan" en="Display name" /></label><input className="input" value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="display_handle" /></div>
                  <div className="fld"><label className="label">Email</label><input className="input" value={email} readOnly style={{ opacity: 0.7 }} /><div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.375rem" }}><Bi id="Email tak bisa diubah di sini." en="Email can't be changed here." /></div></div>
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", alignItems: "center" }}>
                <Err msg={err?.k === "profile" ? err.m : null} /><Saved on={saved === "profile"} />
                <button className="btn btn-default" onClick={saveProfile} disabled={busy === "profile"}>{busy === "profile" ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan perubahan" en="Save changes" />}</button>
              </div>
            </>
          )}

          {tab === "security" && (
            <>
              <div className="sec-card">
                <h2><Bi id="Password" en="Password" /></h2>
                <p className="desc"><Bi id="Ubah password akun Anda." en="Change your account password." /></p>
                <div className="fld-2"><div className="fld"><label className="label"><Bi id="Password baru" en="New password" /></label><input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Min. 8 karakter" /></div><div className="fld"><label className="label"><Bi id="Konfirmasi" en="Confirm" /></label><input className="input" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} /></div></div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.5rem" }}>
                  <button className="btn btn-default btn-sm" onClick={updatePassword} disabled={busy === "security"}>{busy === "security" ? <Loader2 size={14} className="spin" /> : <Bi id="Perbarui password" en="Update password" />}</button>
                  <Err msg={err?.k === "security" ? err.m : null} /><Saved on={saved === "security"} />
                </div>
              </div>
              <div className="sec-card">
                <h2>2FA · <Bi id="Sesi aktif" en="Active sessions" /></h2>
                <p className="desc"><Bi id="Segera — 2FA & manajemen sesi belum aktif di rilis ini." en="Coming soon — 2FA & session management not in this release." /></p>
                <div className="session"><span className="ic"><Monitor size={16} /></span><div style={{ flex: 1 }}><div className="t"><Bi id="Sesi ini" en="This session" /> <span className="badge badge-success" style={{ marginLeft: "0.375rem" }}><span className="dot" /><Bi id="Aktif" en="Current" /></span></div></div></div>
              </div>
            </>
          )}

          {tab === "notif" && (
            <div className="sec-card">
              <h2><Bi id="Preferensi notifikasi" en="Notification preferences" /></h2>
              <p className="desc"><Bi id="Hubungkan Telegram di menu Integrasi. Matriks lengkap di Config → Notifikasi." en="Connect Telegram in the Integrations menu. Full matrix in Config → Notifications." /></p>
              <a href="/config/notifications" className="link" style={{ color: "var(--brand)", textDecoration: "none", fontSize: "var(--text-sm)", display: "inline-block", marginTop: "0.5rem" }}><Bi id="Buka matriks notifikasi" en="Open notification matrix" /> →</a>
            </div>
          )}

          {tab === "language" && (
            <div className="sec-card">
              <h2><Bi id="Bahasa & tema" en="Language & theme" /></h2>
              <p className="desc"><Bi id="Bahasa antarmuka (UI) — terpisah dari bahasa konten channel." en="Interface (UI) language — separate from channel content language." /></p>
              <div className={`lang-opt${lang === "id" ? " sel" : ""}`} onClick={() => pickLang("id")}><span className="flag">🇮🇩</span><div><div className="t">Bahasa Indonesia</div><div className="s">Default</div></div><span className="radio" /></div>
              <div className={`lang-opt${lang === "en" ? " sel" : ""}`} onClick={() => pickLang("en")}><span className="flag">🇬🇧</span><div><div className="t">English</div><div className="s">English (US)</div></div><span className="radio" /></div>
              <div className="row-between" style={{ marginTop: "0.5rem" }}><div><div className="t"><Bi id="Tema" en="Theme" /></div><div className="s"><Bi id="Dark / Light mode" en="Dark / Light mode" /></div></div><button className="btn btn-secondary btn-sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}><Moon size={14} /> <Bi id="Ganti tema" en="Toggle theme" /></button></div>
            </div>
          )}

          {tab === "danger" && (
            <div className="sec-card danger-zone">
              <h2 style={{ color: "var(--error)" }}><Bi id="Zona berbahaya" en="Danger zone" /></h2>
              <p className="desc"><Bi id="Ekspor & hapus akun belum aktif di rilis ini (butuh alur konfirmasi aman)." en="Export & account deletion not in this release (needs a safe confirmation flow)." /></p>
              <div className="danger-row" style={{ opacity: 0.6 }}><div><div className="t"><Bi id="Ekspor data" en="Export data" /></div><div className="s"><Bi id="Segera" en="Coming soon" /></div></div><button className="btn btn-outline btn-sm" disabled><Bi id="Ekspor" en="Export" /></button></div>
              <div className="danger-row" style={{ opacity: 0.6 }}><div><div className="t" style={{ color: "var(--error)" }}><Bi id="Hapus akun" en="Delete account" /></div><div className="s"><Bi id="Segera" en="Coming soon" /></div></div><button className="btn btn-destructive btn-sm" disabled><Bi id="Hapus akun" en="Delete account" /></button></div>
            </div>
          )}
        </main>
      </div>
    </>
  );
}
