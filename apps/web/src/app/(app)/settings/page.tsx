"use client";

import { useCallback, useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { User, Shield, Command, Bell, Globe, AlertTriangle, Send, Moon, Monitor, Check, Loader2, Video, ShieldCheck } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import "./settings.css";

// B5 Settings — Phase 9.3 (wired Supabase v2). Profil (email read + display_handle via RPC),
// Keamanan (ganti password via supabase.auth.updateUser — NYATA), Integrasi Telegram (RPC).
// Lang/theme = client toggle. 2FA/sesi/notif-email/danger = placeholder/gate. Config-write lewat
// RPC whitelist set_tenant_config (aman dari escalation).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Tab = "profile" | "security" | "integrations" | "notif" | "language" | "danger";
const NAV: [Tab, React.ReactNode, string, string][] = [
  ["profile", <User size={18} key="p" />, "Profil", "Profile"],
  ["security", <Shield size={18} key="s" />, "Keamanan", "Security"],
  ["integrations", <Command size={18} key="i" />, "Integrasi", "Integrations"],
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
  const [tgChat, setTgChat] = useState("");
  const [tgEnabled, setTgEnabled] = useState(false);
  const [pw, setPw] = useState(""); const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(""); // which action busy
  const [saved, setSaved] = useState(""); // which saved
  const [err, setErr] = useState<{ k: string; m: string } | null>(null);

  // YouTube BYO-CC (Integrasi). Status dibaca via /api/youtube/status (vault Python; RLS service_role).
  type YtStatus = { connected: boolean; has_client: boolean; channel_id: string | null; degraded?: boolean };
  const [yt, setYt] = useState<YtStatus | null>(null);
  const [ytCid, setYtCid] = useState(""); const [ytSecret, setYtSecret] = useState("");
  const [ytMsg, setYtMsg] = useState<string | null>(null);
  const YT_REDIRECT = process.env.NEXT_PUBLIC_YT_REDIRECT_URI || "(lihat dokumentasi)";

  const loadYt = useCallback(async () => {
    try { const r = await fetch("/api/youtube/status"); if (r.ok) setYt(await r.json()); } catch { /* abaikan */ }
  }, []);

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    setEmail(user?.email ?? "");
    const { data } = await supabase.from("tenant_configs").select("display_handle,telegram_chat_id,telegram_enabled").maybeSingle();
    const t = data as { display_handle?: string; telegram_chat_id?: string; telegram_enabled?: boolean } | null;
    setHandle(t?.display_handle ?? ""); setTgChat(t?.telegram_chat_id ?? ""); setTgEnabled(!!t?.telegram_enabled);
  }, [supabase]);
  useEffect(() => {
    load(); loadYt();
    const s = (localStorage.getItem("mv-lang") as "id" | "en") || "id"; setLang(s); document.documentElement.lang = s;
    // Kembali dari Google OAuth (ret=/settings).
    const sp = new URLSearchParams(window.location.search);
    const r = sp.get("youtube");
    if (r === "connected") { setTab("integrations"); setYtMsg("connected"); window.history.replaceState({}, "", "/settings"); }
    else if (r === "error") { setTab("integrations"); setYtMsg(`error:${sp.get("reason") || "unknown"}`); window.history.replaceState({}, "", "/settings"); }
  }, [load, loadYt]);

  function pickLang(l: "id" | "en") { setLang(l); document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }
  const flash = (k: string) => { setSaved(k); setTimeout(() => setSaved(""), 2500); };

  async function connectYt() {
    setErr(null);
    if (!ytCid.trim() || !ytSecret.trim()) { setErr({ k: "yt", m: lang === "id" ? "Isi Client ID & Secret" : "Enter Client ID & Secret" }); return; }
    setBusy("yt");
    try {
      const r = await fetch("/api/youtube/connect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: ytCid, client_secret: ytSecret, ret: "/settings" }) });
      const j = await r.json();
      if (r.ok && j.authorize_url) { window.location.href = j.authorize_url; return; }
      setBusy(""); setErr({ k: "yt", m: j.error || "Gagal memulai koneksi" });
    } catch { setBusy(""); setErr({ k: "yt", m: lang === "id" ? "Server tak terjangkau" : "Server unreachable" }); }
  }
  async function disconnectYt() {
    setBusy("ytd"); setErr(null);
    try { await fetch("/api/youtube/disconnect", { method: "POST" }); setYtCid(""); setYtSecret(""); await loadYt(); flash("ytd"); }
    catch { setErr({ k: "yt", m: lang === "id" ? "Gagal memutus" : "Disconnect failed" }); }
    finally { setBusy(""); }
  }

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
  async function saveTelegram() {
    setErr(null); setBusy("tg");
    const { error } = await supabase.rpc("set_tenant_config", { p_telegram_chat_id: tgChat.trim(), p_telegram_enabled: tgEnabled });
    setBusy(""); if (error) return setErr({ k: "tg", m: error.message }); flash("tg");
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

          {tab === "integrations" && (
            <div className="sec-card">
              <h2><Bi id="Integrasi" en="Integrations" /></h2>
              <p className="desc"><Bi id="Hubungkan layanan eksternal." en="Connect external services." /></p>

              {/* YouTube BYO-CC — sambung channel via OAuth app milik tenant (NYATA). */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
                <span style={{ width: 36, height: 36, borderRadius: "var(--r-md)", background: "#ff0000", display: "grid", placeItems: "center", color: "#fff" }}><Video size={18} /></span>
                <div><div className="t">YouTube</div><div className="s"><Bi id="Auto-publish ke channel Anda (BYO-CC, kredensial Anda sendiri)" en="Auto-publish to your channel (BYO-CC, your own credentials)" /></div></div>
                <span style={{ marginLeft: "auto", fontSize: "var(--text-xs)", fontWeight: 600, color: yt?.connected ? "var(--success)" : "var(--text-muted,#888)" }}>
                  {yt?.connected ? <><Check size={13} style={{ verticalAlign: "-2px" }} /> <Bi id="Tersambung" en="Connected" /></> : <Bi id="Belum tersambung" en="Not connected" />}
                </span>
              </div>
              {ytMsg === "connected" && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", color: "var(--success)" }}><Check size={13} style={{ verticalAlign: "-2px" }} /> <Bi id="Channel YouTube berhasil tersambung." en="YouTube channel connected." /></div>}
              {ytMsg?.startsWith("error:") && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", color: "var(--danger,#ef4444)" }}>OAuth gagal: {ytMsg.slice(6)}</div>}
              {yt?.degraded && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-xs)", color: "var(--text-muted,#888)" }}><Bi id="Status koneksi tak tersedia saat ini (layanan sambungan offline)." en="Connection status unavailable right now (connection service offline)." /></div>}

              {yt?.connected ? (
                <div style={{ marginBottom: "1rem" }}>
                  {yt.channel_id && <div className="s" style={{ marginBottom: "0.5rem" }}>Channel ID: <code>{yt.channel_id}</code></div>}
                  <button className="btn btn-outline btn-sm" onClick={disconnectYt} disabled={busy === "ytd"}>{busy === "ytd" ? <Loader2 size={14} className="spin" /> : <Bi id="Putuskan" en="Disconnect" />}</button>
                  <Saved on={saved === "ytd"} />
                </div>
              ) : (
                <div style={{ marginBottom: "1rem" }}>
                  <div className="note-box ai" style={{ fontSize: "var(--text-xs)", marginBottom: "0.75rem" }}><ShieldCheck size={14} style={{ color: "var(--accent)" }} /><Bi id="Daftarkan Redirect URI ini di OAuth app Google Anda: " en="Register this Redirect URI in your Google OAuth app: " /><code style={{ marginLeft: 4 }}>{YT_REDIRECT}</code></div>
                  <div className="fld"><label className="label">Google Client ID</label><input className="input input-mono" value={ytCid} onChange={(e) => setYtCid(e.target.value)} placeholder="xxxxx.apps.googleusercontent.com" /></div>
                  <div className="fld"><label className="label">Google Client Secret</label><input className="input input-mono" type="password" value={ytSecret} onChange={(e) => setYtSecret(e.target.value)} placeholder="GOCSPX-xxxxxxxx" /></div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.75rem" }}>
                    <button className="btn btn-default btn-sm" onClick={connectYt} disabled={busy === "yt"}>{busy === "yt" ? <Loader2 size={14} className="spin" /> : <><Video size={14} /> <Bi id="Hubungkan via Google" en="Connect via Google" /></>}</button>
                    <Err msg={err?.k === "yt" ? err.m : null} />
                  </div>
                </div>
              )}
              <div style={{ borderTop: "1px solid var(--border)", margin: "0.5rem 0 1rem" }} />

              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.875rem" }}>
                <span style={{ width: 36, height: 36, borderRadius: "var(--r-md)", background: "var(--telegram)", display: "grid", placeItems: "center", color: "#fff" }}><Send size={18} /></span>
                <div><div className="t">Telegram</div><div className="s"><Bi id="Notif real-time per run ke chat Anda" en="Real-time per-run notifications to your chat" /></div></div>
                <label className="switch" style={{ marginLeft: "auto" }}><input type="checkbox" checked={tgEnabled} onChange={(e) => setTgEnabled(e.target.checked)} /><span className="track" /><span className="thumb" /></label>
              </div>
              <div className="fld"><label className="label">Telegram Chat ID</label><input className="input input-mono" value={tgChat} onChange={(e) => setTgChat(e.target.value)} placeholder="mis. 123456789" /></div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.75rem" }}>
                <button className="btn btn-default btn-sm" onClick={saveTelegram} disabled={busy === "tg"}>{busy === "tg" ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan Telegram" en="Save Telegram" />}</button>
                <Err msg={err?.k === "tg" ? err.m : null} /><Saved on={saved === "tg"} />
              </div>
              <div className="row-between" style={{ marginTop: "1rem", opacity: 0.6 }}><div><div className="t">Webhook · Slack</div><div className="s"><span className="badge badge-brand" style={{ fontSize: "0.625rem" }}>Enterprise</span> <Bi id="(belum di rilis ini)" en="(not in this release)" /></div></div></div>
            </div>
          )}

          {tab === "notif" && (
            <div className="sec-card">
              <h2><Bi id="Preferensi notifikasi" en="Notification preferences" /></h2>
              <p className="desc"><Bi id="Toggle Telegram ada di tab Integrasi. Matriks lengkap di Config → Notifikasi." en="Telegram toggle is in Integrations. Full matrix in Config → Notifications." /></p>
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
