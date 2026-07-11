"use client";

import { useCallback, useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { User, Shield, Globe, Moon, Check, Loader2, Settings as SettingsIcon } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/page-header";
import "./settings.css";

// B5 Settings — Phase 9.3 (wired Supabase v2). 3 tab: Profil (email read + display_handle via RPC),
// Keamanan (ganti password via supabase.auth.updateUser — NYATA), Bahasa & tema (client toggle).
// 2FA/sesi + Danger zone (ekspor/hapus akun) DIHAPUS 2026-06-30 (placeholder belum dibutuhkan; 2FA
// menyusul opt-in pasca-launch). Config-write lewat RPC whitelist set_tenant_config (aman dari escalation).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Tab = "profile" | "security" | "language";
const NAV: [Tab, React.ReactNode, string, string][] = [
  ["profile", <User size={18} key="p" />, "Profil", "Profile"],
  ["security", <Shield size={18} key="s" />, "Keamanan", "Security"],
  ["language", <Globe size={18} key="l" />, "Bahasa", "Language"],
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
  const [tz, setTz] = useState("");            // zona waktu tenant (dipakai publisher utk jam slot publish)
  const [tzSaved, setTzSaved] = useState("");  // nilai tersimpan — deteksi perubahan
  const [pw, setPw] = useState(""); const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(""); // which action busy
  const [saved, setSaved] = useState(""); // which saved
  const [err, setErr] = useState<{ k: string; m: string } | null>(null);

  // Integrasi (YouTube/Telegram/IG/TikTok) DIPINDAH ke halaman MAIN /integrations (F2-08, §10.F).

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    setEmail(user?.email ?? "");
    const { data } = await supabase.from("tenant_configs").select("display_handle,timezone").maybeSingle();
    const t = data as { display_handle?: string; timezone?: string } | null;
    setHandle(t?.display_handle ?? "");
    setTz(t?.timezone || "UTC"); setTzSaved(t?.timezone || "UTC");
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
    if (!error && tz && tz !== tzSaved) {
      // Zona waktu diubah MANUAL → set_tenant_timezone p_manual=true (mengunci; auto-detect login tak menimpa lagi)
      const { error: e2 } = await supabase.rpc("set_tenant_timezone", { p_timezone: tz, p_manual: true });
      if (e2) { setBusy(""); return setErr({ k: "profile", m: e2.message }); }
      setTzSaved(tz);
    }
    setBusy(""); if (error) return setErr({ k: "profile", m: error.message }); flash("profile");
  }
  // Daftar zona waktu resmi dari browser + pratinjau jam lokal (tenant awam langsung tahu zonanya benar)
  const tzList = (() => { try { return Intl.supportedValuesOf("timeZone"); } catch { return [tz || "UTC"]; } })();
  const tzNow = (() => { try { return new Intl.DateTimeFormat(lang === "id" ? "id-ID" : "en-US", { timeZone: tz || "UTC", hour: "2-digit", minute: "2-digit", timeZoneName: "short" }).format(new Date()); } catch { return ""; } })();
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
      <PageHeader helpKey="settings" icon={SettingsIcon} title={<Bi id="Pengaturan" en="Settings" />} />
      <div className="set-layout">
        <nav className="set-nav">
          {NAV.map(([id, ic, t, en]) => (
            <div key={id} className={`set-item${tab === id ? " active" : ""}`} onClick={() => { setTab(id); window.scrollTo(0, 0); }}>{ic}<span><Bi id={t} en={en} /></span></div>
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
                <div className="fld" style={{ marginTop: "0.75rem" }}>
                  <label className="label"><Bi id="Zona waktu" en="Timezone" /></label>
                  <select className="input" value={tz} onChange={(e) => setTz(e.target.value)}>
                    {tzList.map((z) => <option key={z} value={z}>{z}</option>)}
                  </select>
                  <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.375rem" }}>
                    <Bi id={`Jam publish di halaman Jadwal mengikuti zona ini.${tzNow ? ` Waktu sekarang di zona ini: ${tzNow}.` : ""} Terdeteksi otomatis dari perangkat Anda — ubah bila perlu.`}
                        en={`Publish times on the Schedule page follow this zone.${tzNow ? ` Current time in this zone: ${tzNow}.` : ""} Auto-detected from your device — change if needed.`} />
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", alignItems: "center" }}>
                <Err msg={err?.k === "profile" ? err.m : null} /><Saved on={saved === "profile"} />
                <button className="btn btn-default" onClick={saveProfile} disabled={busy === "profile"}>{busy === "profile" ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan perubahan" en="Save changes" />}</button>
              </div>
            </>
          )}

          {tab === "security" && (
            <div className="sec-card">
              <h2><Bi id="Password" en="Password" /></h2>
              <p className="desc"><Bi id="Ubah password akun Anda." en="Change your account password." /></p>
              <div className="fld-2"><div className="fld"><label className="label"><Bi id="Password baru" en="New password" /></label><input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Min. 8 karakter" /></div><div className="fld"><label className="label"><Bi id="Konfirmasi" en="Confirm" /></label><input className="input" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} /></div></div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.5rem" }}>
                <button className="btn btn-default btn-sm" onClick={updatePassword} disabled={busy === "security"}>{busy === "security" ? <Loader2 size={14} className="spin" /> : <Bi id="Perbarui password" en="Update password" />}</button>
                <Err msg={err?.k === "security" ? err.m : null} /><Saved on={saved === "security"} />
              </div>
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
        </main>
      </div>
    </>
  );
}
