"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { User, Shield, Command, Bell, Globe, AlertTriangle, Upload, Download, ExternalLink, Send, Moon, Monitor } from "lucide-react";
import "./settings.css";

// B5 Settings (PoC) — port dari design-source/Settings.html. Tab nav (profile/security/integrations/
// notif/language/danger). Form mock — persist nyata = Supabase Phase 4+. Lang/theme = client toggle.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Tab = "profile" | "security" | "integrations" | "notif" | "language" | "danger";
const NAV: [Tab, React.ReactNode, string, string][] = [
  ["profile", <User size={18} key="p" />, "Profil", "Profile"],
  ["security", <Shield size={18} key="s" />, "Keamanan", "Security"],
  ["integrations", <Command size={18} key="i" />, "Integrasi", "Integrations"],
  ["notif", <Bell size={18} key="n" />, "Notifikasi", "Notifications"],
  ["language", <Globe size={18} key="l" />, "Bahasa", "Language"],
  ["danger", <AlertTriangle size={18} key="d" />, "Zona berbahaya", "Danger zone"],
];

function Switch({ checked }: { checked?: boolean }) {
  return (<label className="switch"><input type="checkbox" defaultChecked={checked} /><span className="track" /><span className="thumb" /></label>);
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [tab, setTab] = useState<Tab>("profile");
  const [lang, setLang] = useState<"id" | "en">("id");

  useEffect(() => {
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved); document.documentElement.lang = saved;
  }, []);

  function pickLang(l: "id" | "en") {
    setLang(l); document.documentElement.lang = l; localStorage.setItem("mv-lang", l);
  }

  return (
    <>
      <div className="page-head"><h1><Bi id="Pengaturan" en="Settings" /></h1></div>

      <div className="set-layout">
        <nav className="set-nav">
          {NAV.map(([id, ic, t, en]) => (
            <div key={id} className={`set-item${id === "danger" ? " danger" : ""}${tab === id ? " active" : ""}`} onClick={() => { setTab(id); window.scrollTo(0, 0); }}>
              {ic}<span><Bi id={t} en={en} /></span>
            </div>
          ))}
        </nav>

        <main className="set-main">
          {/* PROFILE */}
          {tab === "profile" && (
            <>
              <div className="sec-card">
                <h2><Bi id="Profil" en="Profile" /></h2>
                <p className="desc"><Bi id="Informasi akun Anda." en="Your account information." /></p>
                <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", marginBottom: "1.5rem" }}>
                  <span className="avatar-lg">RP</span>
                  <div><button className="btn btn-secondary btn-sm"><Upload size={14} /> <Bi id="Ganti foto" en="Change photo" /></button><div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.5rem" }}>JPG/PNG · max 2MB</div></div>
                </div>
                <div className="fld-2">
                  <div className="fld"><label className="label"><Bi id="Nama lengkap" en="Full name" /></label><input className="input" defaultValue="Riko Pratama" /></div>
                  <div className="fld"><label className="label">Email</label><input className="input" defaultValue="riko@misterisamudra.id" /></div>
                </div>
                <div className="fld"><label className="label"><Bi id="Nomor telepon" en="Phone number" /></label><input className="input" defaultValue="+62 812-3456-7890" /></div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}><button className="btn btn-ghost"><Bi id="Batal" en="Cancel" /></button><button className="btn btn-default"><Bi id="Simpan perubahan" en="Save changes" /></button></div>
            </>
          )}

          {/* SECURITY */}
          {tab === "security" && (
            <>
              <div className="sec-card">
                <h2><Bi id="Password" en="Password" /></h2>
                <p className="desc"><Bi id="Ubah password akun Anda." en="Change your account password." /></p>
                <div className="fld"><label className="label"><Bi id="Password saat ini" en="Current password" /></label><input className="input" type="password" defaultValue="password" /></div>
                <div className="fld-2"><div className="fld"><label className="label"><Bi id="Password baru" en="New password" /></label><input className="input" type="password" /></div><div className="fld"><label className="label"><Bi id="Konfirmasi" en="Confirm" /></label><input className="input" type="password" /></div></div>
                <button className="btn btn-default btn-sm" style={{ marginTop: "0.5rem" }}><Bi id="Perbarui password" en="Update password" /></button>
              </div>
              <div className="sec-card">
                <h2>2FA</h2>
                <p className="desc"><Bi id="Tambah lapisan keamanan ekstra." en="Add an extra layer of security." /></p>
                <div className="row-between"><div><div className="t"><Bi id="Autentikasi dua faktor" en="Two-factor authentication" /></div><div className="s"><Bi id="Via aplikasi authenticator" en="Via authenticator app" /></div></div><Switch /></div>
              </div>
              <div className="sec-card">
                <h2><Bi id="Sesi aktif" en="Active sessions" /></h2>
                <p className="desc"><Bi id="Perangkat yang sedang login." en="Devices currently logged in." /></p>
                <div className="session"><span className="ic"><Monitor size={16} /></span><div style={{ flex: 1 }}><div className="t">Chrome · macOS <span className="badge badge-success" style={{ marginLeft: "0.375rem" }}><span className="dot" /><Bi id="Sekarang" en="Current" /></span></div><div className="s">Jakarta, ID · 11 Jun 2026</div></div></div>
                <div className="session"><span className="ic"><Monitor size={16} /></span><div style={{ flex: 1 }}><div className="t">Safari · iPhone</div><div className="s">Jakarta, ID · 10 Jun 2026</div></div><button className="btn btn-ghost btn-sm" style={{ color: "var(--error)" }}><Bi id="Keluar" en="Revoke" /></button></div>
              </div>
            </>
          )}

          {/* INTEGRATIONS */}
          {tab === "integrations" && (
            <div className="sec-card">
              <h2><Bi id="Integrasi" en="Integrations" /></h2>
              <p className="desc"><Bi id="Hubungkan layanan eksternal." en="Connect external services." /></p>
              <div className="row-between"><div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}><span style={{ width: 36, height: 36, borderRadius: "var(--r-md)", background: "var(--telegram)", display: "grid", placeItems: "center", color: "#fff" }}><Send size={18} /></span><div><div className="t">Telegram</div><div className="s">@MesinViralBot · <Bi id="terhubung" en="connected" /></div></div></div><button className="btn btn-secondary btn-sm"><Bi id="Kelola" en="Manage" /></button></div>
              <div className="row-between"><div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}><span style={{ width: 36, height: 36, borderRadius: "var(--r-md)", background: "var(--surface-2)", display: "grid", placeItems: "center", color: "var(--text-secondary)" }}><ExternalLink size={16} /></span><div><div className="t">Webhook URL</div><div className="s"><span className="badge badge-brand" style={{ fontSize: "0.625rem" }}>Enterprise</span></div></div></div><button className="btn btn-secondary btn-sm" disabled><Bi id="Atur" en="Setup" /></button></div>
              <div className="row-between"><div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}><span style={{ width: 36, height: 36, borderRadius: "var(--r-md)", background: "#4A154B", display: "grid", placeItems: "center", color: "#fff", fontWeight: 700 }}>S</span><div><div className="t">Slack</div><div className="s"><span className="badge badge-brand" style={{ fontSize: "0.625rem" }}>Enterprise</span></div></div></div><button className="btn btn-secondary btn-sm" disabled><Bi id="Hubungkan" en="Connect" /></button></div>
            </div>
          )}

          {/* NOTIFICATIONS */}
          {tab === "notif" && (
            <div className="sec-card">
              <h2><Bi id="Preferensi notifikasi" en="Notification preferences" /></h2>
              <p className="desc"><Bi id="Pengaturan cepat. Detail lengkap di Config → Notifikasi." en="Quick settings. Full matrix in Config → Notifications." /></p>
              <div className="row-between"><div><div className="t">Email</div><div className="s"><Bi id="Ringkasan & peringatan penting" en="Digests & important alerts" /></div></div><Switch checked /></div>
              <div className="row-between"><div><div className="t">Telegram</div><div className="s"><Bi id="Notif real-time per run" en="Real-time per-run notifications" /></div></div><Switch checked /></div>
              <div className="row-between"><div><div className="t">In-app</div><div className="s"><Bi id="Lonceng notifikasi" en="Notification bell" /></div></div><Switch checked /></div>
              <a href="/config?tab=notifications" className="link" style={{ color: "var(--brand)", textDecoration: "none", fontSize: "var(--text-sm)", display: "inline-block", marginTop: "1rem" }}><Bi id="Buka matriks notifikasi lengkap" en="Open full notification matrix" /> →</a>
            </div>
          )}

          {/* LANGUAGE */}
          {tab === "language" && (
            <div className="sec-card">
              <h2><Bi id="Bahasa & tema" en="Language & theme" /></h2>
              <p className="desc"><Bi id="Pilih bahasa antarmuka." en="Choose your interface language." /></p>
              <div className={`lang-opt${lang === "id" ? " sel" : ""}`} onClick={() => pickLang("id")}><span className="flag">🇮🇩</span><div><div className="t">Bahasa Indonesia</div><div className="s">Default</div></div><span className="radio" /></div>
              <div className={`lang-opt${lang === "en" ? " sel" : ""}`} onClick={() => pickLang("en")}><span className="flag">🇬🇧</span><div><div className="t">English</div><div className="s">English (US)</div></div><span className="radio" /></div>
              <div className="row-between" style={{ marginTop: "0.5rem" }}><div><div className="t"><Bi id="Tema" en="Theme" /></div><div className="s"><Bi id="Dark / Light mode" en="Dark / Light mode" /></div></div><button className="btn btn-secondary btn-sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}><Moon size={14} /> <Bi id="Ganti tema" en="Toggle theme" /></button></div>
            </div>
          )}

          {/* DANGER */}
          {tab === "danger" && (
            <div className="sec-card danger-zone">
              <h2 style={{ color: "var(--error)" }}><Bi id="Zona berbahaya" en="Danger zone" /></h2>
              <p className="desc"><Bi id="Aksi permanen. Hati-hati." en="Permanent actions. Proceed carefully." /></p>
              <div className="danger-row"><div><div className="t"><Bi id="Ekspor data" en="Export data" /></div><div className="s"><Bi id="Unduh semua data channel & run (CSV/JSON)" en="Download all channel & run data (CSV/JSON)" /></div></div><button className="btn btn-outline btn-sm"><Download size={14} /> <Bi id="Ekspor" en="Export" /></button></div>
              <div className="danger-row"><div><div className="t" style={{ color: "var(--error)" }}><Bi id="Hapus akun" en="Delete account" /></div><div className="s"><Bi id="Hapus akun & semua data secara permanen" en="Permanently delete account & all data" /></div></div><button className="btn btn-destructive btn-sm"><Bi id="Hapus akun" en="Delete account" /></button></div>
            </div>
          )}
        </main>
      </div>
    </>
  );
}
