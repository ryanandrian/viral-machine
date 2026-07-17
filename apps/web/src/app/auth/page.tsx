"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun, Eye, EyeOff, Command, CheckCircle, Bell, ArrowLeft, ArrowRight, Star } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { fetchTrialDays, fetchPlans } from "@/lib/plans";
import { TestimonialAvatar, type Testimonial } from "@/components/testimonial-avatar";
import "./auth.css";

// B1-B4 Auth (PoC) — port dari design-source/Auth.html. Multi-view (signup/login/forgot/verify),
// deep-link ?view=. Standalone (tanpa AppShell/MarketingShell). Auth nyata = Supabase Auth (Phase 4+).

type View = "signup" | "login" | "forgot" | "forgot-sent" | "verify" | "verified" | "reset";

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
      <path fill="#4285F4" d="M22.5 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.9a5 5 0 0 1-2.2 3.3v2.7h3.6c2.1-2 3.3-4.9 3.3-7.8z" />
      <path fill="#34A853" d="M12 23c3 0 5.5-1 7.3-2.7l-3.6-2.7c-1 .7-2.3 1.1-3.7 1.1-2.8 0-5.2-1.9-6.1-4.5H2.2v2.8A11 11 0 0 0 12 23z" />
      <path fill="#FBBC05" d="M5.9 14.2a6.6 6.6 0 0 1 0-4.2V7.2H2.2a11 11 0 0 0 0 9.8z" />
      <path fill="#EA4335" d="M12 5.4c1.6 0 3 .5 4.1 1.6l3.1-3.1A11 11 0 0 0 2.2 7.2L5.9 10c.9-2.6 3.3-4.5 6.1-4.5z" />
    </svg>
  );
}

function PwInput({ id, ...rest }: { id: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  const [show, setShow] = useState(false);
  return (
    <div className="pw-wrap">
      <input className="input" id={id} type={show ? "text" : "password"} {...rest} />
      <button type="button" className="toggle" onClick={() => setShow((s) => !s)} aria-label="Toggle password">
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

export default function AuthPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [lang, setLang] = useState<"id" | "en">("id");
  const [view, setView] = useState<View>("signup");

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved); document.documentElement.lang = saved;
    const qs = new URLSearchParams(window.location.search);
    const v = qs.get("view") as View | null;
    if (v && ["signup", "login", "forgot", "forgot-sent", "verify", "verified", "reset"].includes(v)) setView(v);
    const e = qs.get("error");
    if (e) setErr(e); // error dari /auth/callback (link kedaluwarsa, dll)
    const rf = qs.get("ref"); // [B21] tautan agen/reseller ?ref=KODE → isi otomatis + validasi
    if (rf) { const c = rf.trim().toUpperCase(); setRefCode(c); void checkRef(c); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function switchLang(l: "id" | "en") { setLang(l); document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }
  const go = (v: View) => { setView(v); setErr(null); window.scrollTo(0, 0); };

  // ── Supabase Auth (Phase 9.1) — email flows. signUp → provisioning otomatis via trigger 0028.
  const [email, setEmail] = useState("");
  // [B21] kode agen/reseller (opsional) — atribusi PERMANEN saat daftar (SPEC §1b); ?ref= mengisi otomatis.
  const [refCode, setRefCode] = useState("");
  const [refStatus, setRefStatus] = useState<"idle" | "checking" | "ok" | "bad">("idle");
  async function checkRef(code: string) {
    const c = code.trim().toUpperCase();
    if (!c) { setRefStatus("idle"); return; }
    setRefStatus("checking");
    const r = await fetch(`/api/partner/check?code=${encodeURIComponent(c)}`).then((x) => x.json()).catch(() => null);
    setRefStatus(r?.valid ? "ok" : "bad");
  }
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [trialDays, setTrialDays] = useState(7);
  // T2 (owner 2026-07-13): kapasitas maks per AKUN = video/hari × channel tier tertinggi (Business
  // 5×10=50) — dihitung LIVE dari plan_limits (admin naikkan kuota → klaim ikut). null = belum termuat.
  const [maxDaily, setMaxDaily] = useState<number | null>(null);
  // © dari company_profile.legal_name (SUMBER RESMI admin-editable — no-hardcode, owner 2026-07-13);
  // T3: testimoni panel kanan = urutan-PERTAMA tabel testimonials (satu sumber dgn landing; ubah
  // urutan/isi di admin → halaman ini ikut). null/gagal → kartu disembunyikan (bukan data palsu).
  const [legalName, setLegalName] = useState<string | null>(null);
  const [tst, setTst] = useState<Testimonial | null>(null);
  const supabase = createClient();
  useEffect(() => {
    fetchTrialDays().then(setTrialDays);
    fetchPlans().then(({ plans }) => {
      const caps = plans.filter((p) => p.price_idr != null).map((p) => p.max_videos_per_day * p.max_channels);
      if (caps.length) setMaxDaily(Math.max(...caps));
    });
    // via PINTU RESMI whitelist (bukan tabel langsung — akses anon ke company_profile ditutup migr 0159)
    fetch("/api/public/company").then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((j) => setLegalName(j.legal_name ?? null)).catch(() => setLegalName(null));
    supabase.from("testimonials").select("*").eq("is_active", true).eq("show_on_landing", true)
      .order("sort_order").limit(1).maybeSingle()
      .then(({ data }) => setTst((data as Testimonial | null) ?? null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const origin = () => (typeof window !== "undefined" ? window.location.origin : "");

  async function doSignup() {
    setErr(null);
    if (pw.length < 8) return setErr(lang === "id" ? "Password minimal 8 karakter." : "Password must be at least 8 characters.");
    if (pw !== pw2) return setErr(lang === "id" ? "Konfirmasi password tidak cocok." : "Passwords do not match.");
    // [B21] anti-salah-di-titik-input (§3.1): kode terisi tapi tak dikenal → tolak SEBELUM kirim
    // (server tetap memvalidasi ulang — satu semantik).
    if (refCode.trim() && refStatus === "bad") {
      return setErr(lang === "id" ? "Kode agen/reseller tidak dikenal. Kosongkan bila tidak punya." : "Partner code not recognized. Leave empty if you don't have one.");
    }
    setBusy(true);
    // Email konfirmasi DIKIRIM SENDIRI oleh mv-web (ber-brand, dwibahasa, link token_hash lintas-alat)
    // via /api/auth/signup → BUKAN supabase.auth.signUp (email default Supabase + PKCE rapuh lintas-alat).
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password: pw, lang, refCode: refCode.trim().toUpperCase() || undefined }),
    }).catch(() => null);
    setBusy(false);
    if (!res || !res.ok) {
      const j = res ? await res.json().catch(() => ({})) : {};
      return setErr(j?.msg || (lang === "id" ? "Gagal mendaftar. Coba lagi." : "Signup failed. Try again."));
    }
    go("verify");
  }
  async function doLogin() {
    setErr(null); setBusy(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
    if (error) { setBusy(false); return setErr(error.message); }
    // Honor ?next (dari middleware redirect) bila path valid; else onboarded-check.
    const nextParam = new URLSearchParams(window.location.search).get("next");
    if (nextParam && nextParam.startsWith("/")) { window.location.href = nextParam; return; }
    // Non-produksi (trial habis/suspend) → /billing (pintu upgrade), JANGAN terjebak di onboarding.
    const { data: tc } = await supabase.from("tenant_configs").select("subscription_status").maybeSingle();
    const st = (tc as { subscription_status?: string } | null)?.subscription_status;
    if (st === "trial_expired" || st === "suspended") { window.location.href = "/billing"; return; }
    // Onboarded? punya channel → dashboard; belum → onboarding. (RLS: query ter-scope auth.uid())
    const { count } = await supabase.from("channels").select("id", { count: "exact", head: true });
    window.location.href = (count ?? 0) > 0 ? "/dashboard" : "/onboarding"; // full reload → middleware sinkron
  }
  async function doForgot() {
    setErr(null);
    if (!email.trim()) return setErr(lang === "id" ? "Masukkan email dulu." : "Enter your email first.");
    setBusy(true);
    // Dikirim via endpoint kita sendiri: email ber-brand + link token_hash (JALAN DI SEMUA ALAT),
    // BUKAN resetPasswordForEmail (PKCE ?code yang gagal lintas-alat). Server anti-enumeration.
    const res = await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), lang }),
    }).catch(() => null);
    setBusy(false);
    if (!res || !res.ok) {
      const j = res ? await res.json().catch(() => ({})) : {};
      return setErr(j?.msg || (lang === "id" ? "Gagal mengirim. Coba lagi." : "Failed to send. Try again."));
    }
    go("forgot-sent");
  }
  async function doReset() {
    setErr(null);
    if (pw.length < 8) return setErr(lang === "id" ? "Password minimal 8 karakter." : "Password must be at least 8 characters.");
    if (pw !== pw2) return setErr(lang === "id" ? "Konfirmasi password tidak cocok." : "Passwords do not match.");
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password: pw });
    setBusy(false);
    if (error) return setErr(error.message);
    window.location.href = "/dashboard"; // recovery session aktif → langsung masuk
  }
  async function doResend() {
    setErr(null);
    if (!email.trim()) return setErr(lang === "id" ? "Masukkan email dulu." : "Enter your email first.");
    // Kirim-ulang lewat route yang sama (idempoten utk user belum-konfirmasi). Butuh password (route
    // pakai generateLink type=signup); state pw masih terisi tepat setelah daftar. Bila kosong (mis. reload) → minta isi.
    if (pw.length < 8) return setErr(lang === "id" ? "Masukkan password (min. 8 karakter) lalu kirim ulang." : "Enter your password (min. 8) then resend.");
    setBusy(true);
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password: pw, lang }),
    }).catch(() => null);
    setBusy(false);
    if (!res || !res.ok) {
      const j = res ? await res.json().catch(() => ({})) : {};
      return setErr(j?.msg || (lang === "id" ? "Gagal mengirim ulang. Coba lagi." : "Failed to resend. Try again."));
    }
  }
  async function doGoogle() {
    setErr(null);
    const after = `${origin()}/auth/callback?next=${encodeURIComponent("/dashboard")}`;
    // prompt=select_account → Google SELALU tampilkan pemilih akun (tak silent-SSO ke akun terakhir).
    const { error } = await supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo: after, queryParams: { prompt: "select_account" } } });
    if (error) setErr(error.message);  // aktif setelah provider Google dikonfigurasi di Supabase
  }
  const ErrBox = () => err ? <div style={{ color: "var(--danger, #ef4444)", fontSize: "var(--text-sm)", marginTop: "0.5rem" }}>{err}</div> : null;

  const Stars = ({ n = 5 }: { n?: number }) => <div className="stars">{Array.from({ length: Math.max(1, Math.min(5, n)) }).map((_, i) => <Star key={i} size={15} fill="#FBBF24" color="#FBBF24" />)}</div>;

  return (
    <div className="auth">
      <div className="auth-left">
        <div className="auth-top">
          <a href="/" className="brandmark"><img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 30, height: 30, objectFit: "contain", flex: "none" }} /> MesinViral</a>
          <div className="auth-tools">
            <div className="segmented">
              <button aria-selected={lang === "id"} onClick={() => switchLang("id")}>ID</button>
              <button aria-selected={lang === "en"} onClick={() => switchLang("en")}>EN</button>
            </div>
            <button className="btn btn-secondary btn-icon" aria-label="Theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {mounted && theme === "light" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </div>

        <div className="auth-center">
          {/* SIGN UP */}
          {view === "signup" && (
            <div className="auth-card">
              <h1><Bi id={`Mulai gratis ${trialDays} hari`} en={`Start your ${trialDays}-day trial`} /></h1>
              {/* T1 (owner 2026-07-13): angka "5 video" = fosil rencana lama & basi vs setelan admin — klaim kini config-driven (trialDays). */}
              <p className="lead"><Bi id={`Coba gratis ${trialDays} hari, tanpa kartu kredit.`} en={`Try free for ${trialDays} days, no credit card.`} /></p>
              <button className="oauth-btn" onClick={doGoogle}><GoogleLogo /><Bi id="Daftar dengan Google" en="Sign up with Google" /></button>
              <div className="divider"><Bi id="atau pakai email" en="or use email" /></div>
              <div className="form-stack">
                <div><label className="label">Email</label><input className="input" type="email" placeholder="riko@channel.id" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
                <div><label className="label">Password</label>
                  <PwInput id="pw1" placeholder="Min. 8 karakter" value={pw} onChange={(e) => setPw(e.target.value)} />
                </div>
                <div><label className="label"><Bi id="Konfirmasi password" en="Confirm password" /></label><PwInput id="pw2" value={pw2} onChange={(e) => setPw2(e.target.value)} /></div>
                <div>{/* [B21] atribusi agen — opsional, validasi langsung di titik input */}
                  <label className="label"><Bi id="Kode agen/reseller (opsional)" en="Partner code (optional)" /></label>
                  <input className="input" value={refCode} placeholder="MIS. MAJU2026" style={{ textTransform: "uppercase" }}
                    onChange={(e) => { setRefCode(e.target.value.toUpperCase()); setRefStatus("idle"); }}
                    onBlur={(e) => void checkRef(e.target.value)} />
                  {refStatus === "ok" && <div style={{ fontSize: "var(--text-xs)", color: "var(--ok, #059669)", marginTop: "0.25rem" }}><Bi id="✓ Kode valid — pendaftaran Anda tercatat lewat mitra kami." en="✓ Valid code — your signup is credited to our partner." /></div>}
                  {refStatus === "bad" && <div style={{ fontSize: "var(--text-xs)", color: "var(--danger, #dc2626)", marginTop: "0.25rem" }}><Bi id="✗ Kode tidak dikenal. Kosongkan bila tidak punya." en="✗ Code not recognized. Leave empty if you don't have one." /></div>}
                </div>
                <label className="terms"><input type="checkbox" defaultChecked /><Bi id="Saya setuju dengan Ketentuan Layanan dan Kebijakan Privasi MesinViral." en="I agree to MesinViral's Terms of Service and Privacy Policy." /></label>
                <button className="btn btn-default btn-lg" style={{ width: "100%" }} onClick={doSignup} disabled={busy}>{busy ? "…" : <Bi id="Buat Akun" en="Create account" />}</button>
                <ErrBox />
              </div>
              <div className="auth-foot"><Bi id="Sudah punya akun?" en="Already have an account?" /> <a className="link" onClick={() => go("login")}><Bi id="Masuk" en="Sign in" /></a></div>
            </div>
          )}

          {/* SIGN IN */}
          {view === "login" && (
            <div className="auth-card">
              <h1><Bi id="Selamat datang kembali" en="Welcome back" /></h1>
              <p className="lead"><Bi id="Masuk untuk lanjut ke dashboard Anda." en="Sign in to continue to your dashboard." /></p>
              <button className="oauth-btn" onClick={doGoogle}><GoogleLogo /><Bi id="Masuk dengan Google" en="Sign in with Google" /></button>
              <div className="divider"><Bi id="atau pakai email" en="or use email" /></div>
              <div className="form-stack">
                <div><label className="label">Email</label><input className="input" type="email" placeholder="riko@channel.id" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
                <div>
                  <div className="row-between" style={{ marginBottom: "0.4375rem" }}><label className="label" style={{ margin: 0 }}>Password</label><a className="link" style={{ fontSize: "var(--text-xs)" }} onClick={() => go("forgot")}><Bi id="Lupa password?" en="Forgot password?" /></a></div>
                  <PwInput id="pw3" value={pw} onChange={(e) => setPw(e.target.value)} />
                </div>
                <button className="btn btn-default btn-lg" style={{ width: "100%" }} onClick={doLogin} disabled={busy}>{busy ? "…" : <Bi id="Masuk" en="Sign in" />}</button>
                <ErrBox />
              </div>
              <div className="auth-foot"><Bi id="Belum punya akun?" en="No account yet?" /> <a className="link" onClick={() => go("signup")}><Bi id="Daftar gratis" en="Sign up free" /></a></div>
            </div>
          )}

          {/* FORGOT */}
          {view === "forgot" && (
            <div className="auth-card">
              <div className="state-ico" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><Command size={26} /></div>
              <h1><Bi id="Reset password" en="Reset password" /></h1>
              <p className="lead"><Bi id="Masukkan email Anda, kami kirim link untuk reset password." en="Enter your email and we'll send a reset link." /></p>
              <div className="form-stack">
                <div><label className="label">Email</label><input className="input" type="email" placeholder="riko@channel.id" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
                <button className="btn btn-default btn-lg" style={{ width: "100%" }} onClick={doForgot} disabled={busy}>{busy ? "…" : <Bi id="Kirim link reset" en="Send reset link" />}</button>
                <ErrBox />
              </div>
              <div className="auth-foot"><a className="link" onClick={() => go("login")}><ArrowLeft size={14} style={{ verticalAlign: -2 }} /> <Bi id="Kembali ke masuk" en="Back to sign in" /></a></div>
            </div>
          )}

          {/* FORGOT SENT */}
          {view === "forgot-sent" && (
            <div className="auth-card">
              <div className="state-ico" style={{ background: "var(--success-soft)", color: "var(--success)" }}><CheckCircle size={28} /></div>
              <h1><Bi id="Cek email Anda" en="Check your email" /></h1>
              <p className="lead"><span data-id>Kami sudah mengirim link reset ke <b style={{ color: "var(--text-primary)" }}>{email || "email Anda"}</b>. Cek folder spam jika tidak ada.</span><span data-en>We sent a reset link to <b style={{ color: "var(--text-primary)" }}>{email || "your email"}</b>. Check spam if you don&apos;t see it.</span></p>
              <button className="btn btn-secondary btn-lg" style={{ width: "100%" }} onClick={doForgot} disabled={busy}><Bi id="Kirim ulang link" en="Resend link" /></button>
              <ErrBox />
              <div className="auth-foot"><a className="link" onClick={() => go("login")}><ArrowLeft size={14} style={{ verticalAlign: -2 }} /> <Bi id="Kembali ke masuk" en="Back to sign in" /></a></div>
            </div>
          )}

          {/* VERIFY */}
          {view === "verify" && (
            <div className="auth-card">
              <div className="state-ico" style={{ background: "var(--info-soft)", color: "var(--info)" }}><Bell size={26} /></div>
              <h1><Bi id="Verifikasi email Anda" en="Verify your email" /></h1>
              <p className="lead"><Bi id="Kami kirim link verifikasi ke email Anda. Klik untuk mengaktifkan akun." en="We sent a verification link to your email. Click it to activate your account." /></p>
              <button className="btn btn-secondary btn-lg" style={{ width: "100%", marginBottom: "0.75rem" }} onClick={doResend} disabled={busy}><Bi id="Kirim ulang email" en="Resend email" /></button>
              <ErrBox />
              <div className="auth-foot"><a className="link" onClick={() => go("login")}><ArrowLeft size={14} style={{ verticalAlign: -2 }} /> <Bi id="Kembali ke masuk" en="Back to sign in" /></a></div>
            </div>
          )}

          {/* VERIFIED */}
          {view === "verified" && (
            <div className="auth-card">
              <div className="state-ico" style={{ background: "var(--success-soft)", color: "var(--success)" }}><CheckCircle size={28} /></div>
              <h1><Bi id="Email berhasil diverifikasi!" en="Email verified!" /></h1>
              <p className="lead"><Bi id="Akun Anda aktif. Mari mulai setup channel pertama." en="Your account is active. Let's set up your first channel." /></p>
              <a href="/onboarding" className="btn btn-default btn-lg" style={{ width: "100%" }}><Bi id="Lanjut ke setup" en="Continue to setup" /> <ArrowRight size={16} /></a>
            </div>
          )}

          {/* RESET — set password baru (landing dari link reset, recovery session aktif) */}
          {view === "reset" && (
            <div className="auth-card">
              <div className="state-ico" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}><Command size={26} /></div>
              <h1><Bi id="Buat password baru" en="Set a new password" /></h1>
              <p className="lead"><Bi id="Masukkan password baru untuk akun Anda." en="Enter a new password for your account." /></p>
              <div className="form-stack">
                <div><label className="label"><Bi id="Password baru" en="New password" /></label>
                  <PwInput id="pwr1" placeholder="Min. 8 karakter" value={pw} onChange={(e) => setPw(e.target.value)} />
                </div>
                <div><label className="label"><Bi id="Konfirmasi password" en="Confirm password" /></label>
                  <PwInput id="pwr2" value={pw2} onChange={(e) => setPw2(e.target.value)} />
                </div>
                <button className="btn btn-default btn-lg" style={{ width: "100%" }} onClick={doReset} disabled={busy}>{busy ? "…" : <Bi id="Simpan password" en="Save password" />}</button>
                <ErrBox />
              </div>
              <div className="auth-foot"><a className="link" onClick={() => go("login")}><ArrowLeft size={14} style={{ verticalAlign: -2 }} /> <Bi id="Kembali ke masuk" en="Back to sign in" /></a></div>
            </div>
          )}
        </div>
        <div />
      </div>

      <div className="auth-right">
        <div className="mesh" />
        {/* T2 (owner 2026-07-13): "24/hari per channel" = klaim basi rencana lama; kini = kapasitas
            NYATA akun tertinggi (video/hari × channel, live dari plan_limits). */}
        <div className="stat-ticker"><span style={{ width: 7, height: 7, borderRadius: "50%", background: "#34D399", display: "inline-block" }} /> {maxDaily
          ? <Bi id={`Produksi 24/7 · hingga ${maxDaily} video/hari`} en={`Runs 24/7 · up to ${maxDaily} videos/day`} />
          : <Bi id="Produksi 24/7" en="Runs 24/7" />}</div>
        {/* T3 (owner 2026-07-13): testimoni dari TABEL (urutan-pertama; satu sumber dgn landing) —
            "Riko Pratama" lama = fiksi hardcode yang tak ada di tabel. Gagal muat → kartu disembunyikan. */}
        {tst && (
          <div className="quote-card">
            <Stars n={tst.rating} />
            <blockquote>&quot;<Bi id={tst.quote} en={tst.quote_en || tst.quote} />&quot;</blockquote>
            <div className="quote-author">
              <TestimonialAvatar t={tst} size={40} />
              <div><div className="nm">{tst.person_name}</div><div className="ch">{tst.channel_label ?? ""}</div></div>
              {tst.metric_value && <div className="delta"><div className="big">{tst.metric_value}</div><div className="lbl"><Bi id={tst.metric_label ?? ""} en={tst.metric_label_en || (tst.metric_label ?? "")} /></div></div>}
            </div>
          </div>
        )}
        {/* © = tahun BERJALAN otomatis + legal_name dari company_profile (no-hardcode; identik footer marketing) */}
        <div className="muted" style={{ fontSize: "var(--text-xs)", textAlign: "center", marginBottom: ".5rem" }}>
          © {new Date().getFullYear()} MesinViral.{legalName ? ` Provided By ${legalName}.` : ""}
        </div>
        <div className="trust-row">
          <Bi id="Didukung oleh" en="Powered by" />
          <div className="logos">
            <span style={{ color: "var(--anthropic)" }}>Claude</span>
            <span>ElevenLabs</span>
            <span>OpenAI</span>
            <span style={{ color: "var(--yt)" }}>YouTube</span>
          </div>
        </div>
      </div>
    </div>
  );
}
