"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { createClient } from "@/lib/supabase/client";
import {
  HelpCircle, Moon, Sun, Play, Info, ShieldCheck, Sparkles, Check, CheckCircle,
  ExternalLink, ChevronDown, Plus, ArrowLeft, ArrowRight, Loader2, Video, X,
} from "lucide-react";
import "./onboarding.css";

// C1-C5 Onboarding (PoC) — port dari design-source/Onboarding.html. Wizard 5 langkah
// (Paket / YouTube / API Keys / Niche+Voice / Jadwal). Standalone pre-login (tanpa AppShell).
// Form mock — persist nyata = Supabase Phase 4+. Content language = config-driven (Phase: content_languages DB).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const STEPS = [
  { id: "Paket", en: "Plan", d_id: "Pilih trial", d_en: "Pick trial" },
  { id: "YouTube", en: "YouTube", d_id: "Hubungkan channel", d_en: "Connect channel" },
  { id: "API Keys", en: "API Keys", d_id: "BYOK setup", d_en: "BYOK setup" },
  { id: "Niche & Voice", en: "Niche & Voice", d_id: "Pilih style", d_en: "Pick style" },
  { id: "Jadwal", en: "Schedule", d_id: "Atur slot", d_en: "Set slots" },
];

const PLANS = [
  { name: "Starter", price: "Rp 149K", feats: ["1 channel", "5 video / hari", "Niche dasar", "Self-learning"] },
  { name: "Pro", price: "Rp 349K", popular: true, feats: ["3 channel", "10 video / hari", "Semua niche", "Quality Gate", "Compliance detail"] },
  { name: "Business", price: "Rp 699K", feats: ["10 channel", "24 video / hari", "Priority queue", "Custom voice", "Cross-channel insights"] },
];

const YT: [string, string, boolean][] = [
  ["Buka Google Cloud Console", "Open Google Cloud Console", true],
  ['Buat project "mesinviral-riko"', 'Create project "mesinviral-riko"', true],
  ["Enable YouTube Data API v3", "Enable YouTube Data API v3", false],
  ["Buat OAuth 2.0 credentials", "Create OAuth 2.0 credentials", false],
  ["Copy Client ID + Secret", "Copy Client ID + Secret", false],
];

const SVCS = [
  { key: "anthropic", name: "Anthropic Claude", meta: "LLM · Script & hook", req: true, c: "var(--anthropic)", glyph: "A", ph: "sk-ant-api03-…" },
  { key: "openai", name: "OpenAI", meta: "Visual AI · gpt-image", req: true, c: "var(--openai)", glyph: "O", ph: "sk-…" },
  { key: "elevenlabs", name: "ElevenLabs", meta: "TTS · Voice", req: false, c: "var(--elevenlabs)", glyph: "11", ph: "…" },
];

// key = niche key di DB (niches.niche/channels.niche). Display (id/en) ≠ key.
const NICHES = [
  { key: "universe_mysteries", id: "Misteri Alam Semesta", en: "Universe Mysteries", desc: "Luar angkasa, kosmos, fenomena", cols: ["#1e1b4b", "#312e81", "#4338ca"] },
  { key: "dark_history", id: "Sejarah Kelam", en: "Dark History", desc: "Peristiwa gelap masa lalu", cols: ["#450a0a", "#7f1d1d", "#991b1b"] },
  { key: "ocean_mysteries", id: "Misteri Samudra", en: "Ocean Mysteries", desc: "Laut dalam & makhluk misterius", cols: ["#082f49", "#0c4a6e", "#075985"] },
  { key: "fun_facts", id: "Fakta Menarik", en: "Fun Facts", desc: "Fakta sains & kehidupan", cols: ["#052e16", "#14532d", "#166534"] },
];

// Content language catalog (mock = content-languages.js → prod content_languages DB table)
const LANGS = [
  { code: "id-ID", flag: "🇮🇩", name: "Bahasa Indonesia", en: "Indonesian", tier: "official" },
  { code: "en-US", flag: "🇬🇧", name: "English", en: "English", tier: "official" },
  { code: "ms-MY", flag: "🇲🇾", name: "Bahasa Malaysia", en: "Malay", tier: "experimental" },
  { code: "fil-PH", flag: "🇵🇭", name: "Filipino", en: "Filipino", tier: "experimental" },
  { code: "th-TH", flag: "🇹🇭", name: "ภาษาไทย", en: "Thai", tier: "experimental" },
  { code: "vi-VN", flag: "🇻🇳", name: "Tiếng Việt", en: "Vietnamese", tier: "experimental" },
];
const VOICES: Record<string, [string, string, string][]> = {
  "id-ID": [["Arya", "Pria · dalam, misterius", "Male · deep"], ["Sari", "Wanita · hangat", "Female · warm"], ["Bima", "Pria · energik", "Male · energetic"], ["Dewi", "Wanita · tenang", "Female · calm"]],
  "en-US": [["Adam", "Male · narrative", "Male · narrative"], ["Bella", "Female · bright", "Female · bright"], ["Josh", "Male · deep", "Male · deep"]],
  "ms-MY": [["Aiman", "Lelaki · tenang", "Male · calm"], ["Nurul", "Wanita · mesra", "Female · warm"]],
  "fil-PH": [["Mateo", "Male · clear", "Male · clear"], ["Liza", "Female · friendly", "Female · friendly"]],
  "th-TH": [["Niran", "ชาย · นุ่มนวล", "Male · soft"], ["Mali", "หญิง · สดใส", "Female · bright"]],
  "vi-VN": [["Minh", "Nam · trầm", "Male · deep"], ["Linh", "Nữ · ấm áp", "Female · warm"]],
};

const COLS = ["#6366F1", "#8B5CF6", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#EC4899"];
const DAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];
const WEEK_SLOTS: [string, string][] = [["10:00", "Misteri Samudra"], ["14:00", "Fakta Menarik"], ["19:00", "Auto rotasi"]];

export default function OnboardingPage() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [lang, setLang] = useState<"id" | "en">("id");
  const [cur, setCur] = useState(0);

  const [plan, setPlan] = useState(0);
  const [ytChecks, setYtChecks] = useState<boolean[]>(YT.map(([, , d]) => d));
  const [ytState, setYtState] = useState<"idle" | "verifying" | "connected" | "deferred">("idle");
  const [ytClientId, setYtClientId] = useState("");
  const [ytClientSecret, setYtClientSecret] = useState("");
  const [ytErr, setYtErr] = useState<string | null>(null);
  const [openSvc, setOpenSvc] = useState<Record<string, boolean>>({ anthropic: true });
  const [svcState, setSvcState] = useState<Record<string, "idle" | "testing" | "ok" | "fail">>({});
  const [svcMsg, setSvcMsg] = useState<Record<string, string>>({});
  const [niches, setNiches] = useState<boolean[]>(NICHES.map((_, i) => i === 2));
  const [curLang, setCurLang] = useState("id-ID");
  const [voice, setVoice] = useState(0);
  const [color, setColor] = useState(0);
  const [svcKeys, setSvcKeys] = useState<Record<string, string>>({});
  const [supabase] = useState(() => createClient());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    const saved = (localStorage.getItem("mv-lang") as "id" | "en") || "id";
    setLang(saved); document.documentElement.lang = saved;
    // Kembali dari Google OAuth (ret=/onboarding). Tampilkan hasil + lompat ke langkah berikutnya bila sukses.
    const sp = new URLSearchParams(window.location.search);
    const yt = sp.get("youtube");
    if (yt === "connected") { setYtState("connected"); setCur(2); window.history.replaceState({}, "", "/onboarding"); }
    else if (yt === "error") { setYtState("idle"); setYtErr(`OAuth gagal: ${sp.get("reason") || "unknown"}`); setCur(1); window.history.replaceState({}, "", "/onboarding"); }
  }, []);

  function switchLang(l: "id" | "en") { setLang(l); document.documentElement.lang = l; localStorage.setItem("mv-lang", l); }

  function goto(i: number) {
    setCur(i);
    const c = document.querySelector(".ob-content"); if (c) c.scrollTop = 0;
  }
  function next() { if (cur < STEPS.length - 1) goto(cur + 1); else finish(); }

  // Persist onboarding. Urutan: (1) config via RPC whitelist (IDEMPOTEN, aman dari escalation),
  // lalu (2) INSERT channel (final, non-idempoten) → sukses → /dashboard. Retry aman bila gagal di (1).
  // tenant_credentials (OAuth C2, Fernet) = increment 2b (gate owner Google).
  async function finish() {
    setErr(null); setBusy(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setBusy(false); window.location.href = "/auth?view=login"; return; }

    // (1) Config NON-rahasia (voice + timezone) → SECURITY DEFINER RPC whitelist.
    const voiceName = (VOICES[curLang] || VOICES["id-ID"])[voice]?.[0] ?? null;
    const { error: eCfg } = await supabase.rpc("set_tenant_config", { p_timezone: "Asia/Jakarta", p_tts_voice: voiceName });
    if (eCfg) { setBusy(false); setErr(eCfg.message); return; }

    // (2) channel pertama = DRAFT NON-AKTIF (gerbang): provider terisi dari onboarding; tenant lengkapi
    //     model/voice/visual di Manage lalu aktifkan. Kunci = PER-CHANNEL (no tenant-level key).
    const ak = svcKeys.anthropic?.trim(), ok = svcKeys.openai?.trim(), ek = svcKeys.elevenlabs?.trim();
    const sel = NICHES.filter((_, i) => niches[i]);
    const keys = (sel.length ? sel : [NICHES[2]]).map((n) => n.key);
    const { data: chRow, error: eCh } = await supabase.from("channels").insert({
      tenant_id: user.id,
      channel_name: (sel[0] ?? NICHES[2]).en,
      channel_group: "default", // NOT NULL
      niche: keys[0],
      niche_pool: keys,
      niche_mode: keys.length > 1 ? "random" : "fixed", // chk_niche_mode ∈ {fixed,random}
      content_language: curLang,
      platform: "youtube",
      publish_privacy: "private", // trial-safe (decisions: default private)
      publish_slots: ["13:00"],   // C2: jadwal default (1 slot, ≤ semua tier) — atur di /schedule
      is_active: false,           // F2-01/gerbang: aktif setelah readiness lengkap di Manage
      llm_library: ak ? "anthropic" : null,
      tts_provider: ek ? "elevenlabs" : null,
    }).select("id").single();
    if (eCh) { setBusy(false); setErr(eCh.message); return; }

    // (3) Kunci AI (bila diisi) → POOL tenant per PENYEDIA (/api/credentials/ai). Endpoint per-channel lama DIBUANG.
    //     Non-fatal: tenant bisa lengkapi/ubah di Page Kredensial. (Model VENDOR: 1 kunci OpenAI utk GPT+TTS+image.)
    const keyJobs: [string, string][] = [];
    if (ak) keyJobs.push(["anthropic", ak]);
    if (ok) keyJobs.push(["openai", ok]);
    if (ek) keyJobs.push(["elevenlabs", ek]);
    for (const [provider_key, key] of keyJobs) {
      try { await fetch("/api/credentials/ai", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider_key, key, label: provider_key }) }); } catch { /* non-fatal */ }
    }
    setBusy(false);
    router.push("/dashboard"); // channel draft ada → lengkapi Kredensial + Channel (semua 🟢) = onboarded
  }

  // YouTube connect = BYO-CC Google OAuth NYATA. Tenant bawa OAuth app sendiri (client_id+secret).
  // POST ke /api/youtube/connect (authed) → vault Python simpan secret terenkripsi + balas consent URL
  // → redirect ke Google. Sekembalinya: /onboarding?youtube=connected|error (di-handle useEffect mount).
  // Channel ID dideteksi otomatis pasca-consent (channels.list mine=true) — tak perlu input manual.
  async function connectYt() {
    setYtErr(null);
    if (!ytClientId.trim() || !ytClientSecret.trim()) {
      setYtErr(lang === "id" ? "Isi Client ID & Client Secret dulu." : "Enter Client ID & Client Secret first.");
      return;
    }
    setYtState("verifying");
    try {
      const r = await fetch("/api/youtube/connect", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: ytClientId, client_secret: ytClientSecret, ret: "/onboarding" }),
      });
      const j = await r.json();
      if (r.ok && j.authorize_url) { window.location.href = j.authorize_url; return; }
      setYtState("idle");
      setYtErr(j.error || (lang === "id" ? "Gagal memulai koneksi." : "Failed to start connection."));
    } catch {
      setYtState("idle");
      setYtErr(lang === "id" ? "Server tak terjangkau." : "Server unreachable.");
    }
  }

  // Test koneksi API key — VALIDASI NYATA via /api/validate-key (panggil provider). Bukan simulasi.
  async function testSvc(provider: string) {
    const key = (svcKeys[provider] || "").trim();
    if (!key) { setSvcState((s) => ({ ...s, [provider]: "fail" })); setSvcMsg((m) => ({ ...m, [provider]: "Isi key dulu" })); return; }
    setSvcState((s) => ({ ...s, [provider]: "testing" }));
    try {
      const r = await fetch("/api/validate-key", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider, key }) });
      const j = await r.json();
      setSvcState((s) => ({ ...s, [provider]: j.ok ? "ok" : "fail" }));
      setSvcMsg((m) => ({ ...m, [provider]: j.msg || (j.ok ? "valid" : "gagal") }));
    } catch {
      setSvcState((s) => ({ ...s, [provider]: "fail" })); setSvcMsg((m) => ({ ...m, [provider]: "error jaringan" }));
    }
  }

  const last = cur === STEPS.length - 1;
  const voiceList = VOICES[curLang] || VOICES["id-ID"];

  return (
    <div className="ob-root">
      <div className="ob-top">
        <div className="brandmark"><img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 28, height: 28, objectFit: "contain", flex: "none" }} /> MesinViral</div>
        <div className="steps-bar">
          {STEPS.map((s, i) => {
            const cls = i < cur ? "done" : i === cur ? "current" : "";
            return (
              <div key={i} style={{ display: "contents" }}>
                <div className={`sdot ${cls}`}><span className="circle">{i < cur ? <Check size={14} /> : i + 1}</span><span className="lbl"><Bi id={s.id} en={s.en} /></span></div>
                {i < STEPS.length - 1 && <span className={`sconn ${i < cur ? "filled" : ""}`} />}
              </div>
            );
          })}
        </div>
        <div className="ob-tools">
          <button className="btn btn-ghost btn-icon"><HelpCircle size={18} /></button>
          <div className="segmented"><button aria-selected={lang === "id"} onClick={() => switchLang("id")}>ID</button><button aria-selected={lang === "en"} onClick={() => switchLang("en")}>EN</button></div>
          <button className="btn btn-secondary btn-icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{mounted && theme === "light" ? <Sun size={18} /> : <Moon size={18} />}</button>
        </div>
      </div>

      <div className="ob-main">
        <aside className="ob-rail">
          {STEPS.map((s, i) => {
            const cls = i < cur ? "done" : i === cur ? "current" : "";
            return (
              <div key={i} className={`rail-item ${cls}`} style={{ cursor: i <= cur ? "pointer" : "default" }} onClick={() => { if (i <= cur) goto(i); }}>
                <span className="n">{i < cur ? <Check size={12} /> : i + 1}</span>
                <div><div className="t"><Bi id={s.id} en={s.en} /></div><div className="d"><Bi id={s.d_id} en={s.d_en} /></div></div>
              </div>
            );
          })}
        </aside>

        <div className="ob-content">
          <div className="ob-inner">

            {/* C1 PAKET */}
            {cur === 0 && (
              <div>
                <h1 className="ob-h"><Bi id="Pilih paket untuk memulai trial" en="Pick a plan to start your trial" /></h1>
                <p className="ob-sub"><Bi id="Trial 7 hari semua paket gratis. Cancel kapan saja sebelum trial selesai." en="7-day free trial on all plans. Cancel anytime before it ends." /></p>
                <div className="plan-grid">
                  {PLANS.map((p, i) => (
                    <div key={i} className={`plan ${plan === i ? "sel" : ""} ${p.popular ? "popular" : ""}`} onClick={() => setPlan(i)}>
                      {p.popular && <span className="pop-badge">Most Popular</span>}
                      <span className="radio" />
                      <div className="pname">{p.name}</div>
                      <div className="price">{p.price}<small>/bln</small></div>
                      <ul>{p.feats.map((f) => <li key={f}><Check size={13} /> {f}</li>)}</ul>
                    </div>
                  ))}
                </div>
                <div className="note-box"><Info size={16} style={{ color: "var(--info)" }} /><Bi id="Kartu kredit tidak diperlukan untuk trial. Anda hanya membayar setelah 7 hari jika tidak cancel." en="No credit card needed for the trial. You're only charged after 7 days if you don't cancel." /></div>
              </div>
            )}

            {/* C2 YOUTUBE */}
            {cur === 1 && (
              <div>
                <h1 className="ob-h"><Bi id="Hubungkan channel YouTube" en="Connect your YouTube channel" /></h1>
                <p className="ob-sub"><Bi id="Anda akan membuat Google Cloud Project. Ikuti tutorial singkat ini." en="You'll create a Google Cloud Project. Follow this short tutorial." /></p>
                <div className="vembed"><div className="play"><Play size={22} /></div><div className="cap">▶ Tutorial: Setup Google Cloud + YouTube API (4 menit)</div></div>
                <div className="checklist">
                  {YT.map(([id, en], i) => (
                    <div key={i} className={`check-item ${ytChecks[i] ? "checked" : ""}`}>
                      <span className="box" onClick={() => setYtChecks((c) => c.map((v, k) => (k === i ? !v : v)))}>{ytChecks[i] && <Check size={12} />}</span>
                      <span><Bi id={id} en={en} /></span>
                      {i === 0 && <a href="#" className="open-ext muted" style={{ fontSize: "var(--text-xs)" }}><ExternalLink size={13} /></a>}
                    </div>
                  ))}
                </div>
                <div className="form-stack" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <div><label className="label">Google Client ID</label><input className="input input-mono" placeholder="xxxxx.apps.googleusercontent.com" value={ytClientId} onChange={(e) => setYtClientId(e.target.value)} disabled={ytState === "verifying" || ytState === "connected"} /></div>
                  <div><label className="label">Google Client Secret</label><input className="input input-mono" type="password" placeholder="GOCSPX-xxxxxxxx" value={ytClientSecret} onChange={(e) => setYtClientSecret(e.target.value)} disabled={ytState === "verifying" || ytState === "connected"} /></div>
                  <div className="note-box ai" style={{ fontSize: "var(--text-xs)" }}><ShieldCheck size={14} style={{ color: "var(--accent)" }} /><Bi id="Daftarkan Redirect URI ini di OAuth app Anda: " en="Register this Redirect URI in your OAuth app: " /><code style={{ marginLeft: 4 }}>{process.env.NEXT_PUBLIC_YT_REDIRECT_URI || "(lihat dokumentasi)"}</code></div>
                  {ytState !== "connected" && (
                    <button className="btn btn-default" style={{ width: "fit-content" }} onClick={connectYt} disabled={ytState === "verifying"}>
                      <Video size={16} /> {ytState === "verifying" ? <Bi id="Menghubungkan…" en="Connecting…" /> : <Bi id="Hubungkan via Google" en="Connect via Google" />}
                    </button>
                  )}
                </div>
                {ytErr && (
                  <div style={{ marginTop: "1rem", padding: "0.75rem 1rem", background: "color-mix(in srgb,var(--danger) 10%,transparent)", border: "1px solid color-mix(in srgb,var(--danger) 30%,transparent)", borderRadius: "var(--r-md)", fontSize: "var(--text-sm)", color: "var(--danger)" }}>{ytErr}</div>
                )}
                {ytState === "connected" && (
                  <div style={{ marginTop: "1rem", display: "flex", gap: "0.625rem", padding: "0.875rem 1.25rem", background: "color-mix(in srgb,var(--success,#16a34a) 12%,transparent)", border: "1px solid color-mix(in srgb,var(--success,#16a34a) 30%,transparent)", borderRadius: "var(--r-md)", fontSize: "var(--text-sm)" }}>
                    <Check size={16} style={{ color: "var(--success,#16a34a)", flex: "none" }} />
                    <span><Bi id="Channel YouTube tersambung. Anda bisa kelola/putus di Pengaturan." en="YouTube channel connected. Manage/disconnect in Settings." /></span>
                  </div>
                )}
                <div style={{ marginTop: "0.875rem", display: "flex", gap: "0.625rem", padding: "0.875rem 1.25rem", background: "var(--accent-soft)", border: "1px solid color-mix(in srgb,var(--accent) 25%,transparent)", borderRadius: "var(--r-md)", fontSize: "var(--text-sm)" }}>
                  <ShieldCheck size={16} style={{ color: "var(--accent)", flex: "none" }} />
                  <span><Bi id="Opsional sekarang — Anda juga bisa melewati langkah ini dan menghubungkan channel YouTube nanti di Pengaturan. Konfigurasi lain tetap berjalan." en="Optional now — you can skip this and connect your YouTube channel later in Settings. Other config still applies." /></span>
                </div>
              </div>
            )}

            {/* C3 API KEYS */}
            {cur === 2 && (
              <div>
                <h1 className="ob-h"><Bi id="Tambahkan API keys untuk power mesin" en="Add API keys to power the engine" /></h1>
                <p className="ob-sub"><Bi id="BYOK = Bring Your Own Keys. Anda yang kontrol biaya, sepenuhnya transparan." en="BYOK = Bring Your Own Keys. You control the cost, fully transparent." /></p>
                <div className="note-box ai"><ShieldCheck size={16} style={{ color: "var(--accent)" }} /><Bi id="Keys dienkripsi dengan Fernet AES-128 dan tidak pernah di-log." en="Keys are encrypted with Fernet AES-128 and never logged." /></div>
                <div style={{ marginTop: "1.5rem" }}>
                  {SVCS.map((s) => {
                    const open = !!openSvc[s.key]; const st = svcState[s.key] || "idle";
                    return (
                      <div key={s.key} className={`svc ${open ? "open" : ""}`}>
                        <div className="svc-head" onClick={() => setOpenSvc((o) => ({ ...o, [s.key]: !o[s.key] }))}>
                          <span className="svc-ic" style={{ background: s.c, fontWeight: 700, fontSize: "var(--text-sm)" }}>{s.glyph}</span>
                          <div><div className="svc-name">{s.name}</div><div className="svc-meta">{s.meta}</div></div>
                          <span className={`badge ${s.req ? "badge-warning" : "badge-outline"}`} style={{ marginLeft: "auto" }}>{s.req ? <Bi id="Wajib" en="Required" /> : <Bi id="Opsional" en="Optional" />}</span>
                          <span className="chev"><ChevronDown size={16} /></span>
                        </div>
                        {open && (
                          <div className="svc-body">
                            <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.875rem" }}><Bi id="Buat akun → tambah billing → generate API key. " en="Create account → add billing → generate API key. " /><a href="#" className="link" style={{ fontSize: "var(--text-xs)" }}>▶ Tutorial 2 menit</a></div>
                            <label className="label">API Key</label>
                            <div style={{ display: "flex", gap: "0.5rem" }}>
                              <input className="input input-mono" type="password" placeholder={s.ph} value={svcKeys[s.key] || ""} onChange={(e) => setSvcKeys((k) => ({ ...k, [s.key]: e.target.value }))} />
                              <button className="btn btn-secondary" disabled={st === "testing"} onClick={() => testSvc(s.key)}>{st === "testing" ? <Loader2 size={14} className="spin" /> : <Bi id="Test koneksi" en="Test connection" />}</button>
                            </div>
                            {(st === "ok" || st === "fail") && (
                              <div style={{ marginTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", color: st === "ok" ? "var(--success)" : "var(--danger)" }}>
                                {st === "ok" ? <CheckCircle size={16} /> : <X size={16} />} {svcMsg[s.key] || (st === "ok" ? "valid" : "gagal")}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="note-box"><Info size={16} style={{ color: "var(--info)" }} /><span data-id><b style={{ color: "var(--text-primary)" }}>Belum punya keys?</b> Lewati dulu — bisa dilengkapi nanti di halaman <b>Kredensial</b>. Kunci wajib lengkap sebelum channel bisa diaktifkan (tak ada kredensial pinjaman).</span><span data-en><b style={{ color: "var(--text-primary)" }}>No keys yet?</b> Skip for now — add them later in <b>Credentials</b>. Keys are required before a channel can be activated (no borrowed credentials).</span></div>
              </div>
            )}

            {/* C4 NICHE + VOICE */}
            {cur === 3 && (
              <div>
                <h1 className="ob-h"><Bi id="Pilih niche & suara channel" en="Choose your channel's niche & voice" /></h1>
                <p className="ob-sub"><Bi id="Pilih satu atau lebih niche. Mesin akan rotasi otomatis untuk diversity." en="Pick one or more niches. The engine rotates them automatically for diversity." /></p>
                <div className="niche-grid">
                  {NICHES.map((n, i) => (
                    <div key={i} className={`niche ${niches[i] ? "sel" : ""}`} onClick={() => setNiches((s) => s.map((v, k) => (k === i ? !v : v)))}>
                      <div className="ncheck"><Check size={13} /></div>
                      <div className="mood">{n.cols.map((c) => <span key={c} style={{ background: c }} />)}</div>
                      <div className="nbody"><div className="nname"><Bi id={n.id} en={n.en} /></div><div className="ndesc">{n.desc}</div></div>
                    </div>
                  ))}
                  <div className="niche" style={{ borderStyle: "dashed", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "0.375rem", color: "var(--text-muted)", minHeight: 120, cursor: "pointer" }}><Plus size={20} /><span style={{ fontSize: "var(--text-xs)" }}>Niche custom · Rp 299K</span></div>
                </div>

                <h3 style={{ fontSize: "var(--text-base)", fontWeight: 600, margin: "2rem 0 0.5rem" }}><Bi id="Bahasa Konten" en="Content Language" /></h3>
                <p className="muted" style={{ fontSize: "var(--text-xs)", margin: "0 0 0.625rem" }}><Bi id="Menentukan bahasa narasi, caption & script untuk semua video channel ini." en="Sets the language of narration, captions & script for every video on this channel." /></p>
                <div className="lang-select">
                  {LANGS.map((l) => (
                    <div key={l.code} className={`lang-opt ${l.code === curLang ? "sel" : ""}`} onClick={() => { setCurLang(l.code); setVoice(0); }}>
                      <span className="flag">{l.flag}</span>
                      <div><div className="ln"><Bi id={l.name} en={l.en} /></div></div>
                      {l.tier === "experimental" && <span className="badge badge-outline" style={{ fontSize: "0.5625rem", marginLeft: "auto" }}><Bi id="Eksperimental" en="Experimental" /></span>}
                      <span className="lradio" style={l.tier === "experimental" ? undefined : { marginLeft: "auto" }} />
                    </div>
                  ))}
                </div>
                <div className="note-box" style={{ marginTop: "0.625rem", padding: "0.625rem 0.875rem" }}><Info size={14} style={{ color: "var(--info)" }} /><span style={{ fontSize: "var(--text-xs)" }}><Bi id="Mengubah bahasa akan mengubah pilihan voice yang tersedia." en="Changing the language changes which voices are available." /></span></div>

                <h3 style={{ fontSize: "var(--text-base)", fontWeight: 600, margin: "2rem 0 0.875rem" }}><Bi id="Suara (Voice)" en="Voice" /></h3>
                <div>
                  {voiceList.map(([n, sId, sEn], i) => (
                    <div key={i} className={`voice ${voice === i ? "sel" : ""}`} onClick={() => setVoice(i)}>
                      <button className="vplay" onClick={(e) => e.stopPropagation()}><Play size={15} /></button>
                      <div><div className="vname">{n}</div><div className="vstyle"><Bi id={sId} en={sEn} /></div></div>
                      <span className="vradio" />
                    </div>
                  ))}
                </div>

                <h3 style={{ fontSize: "var(--text-base)", fontWeight: 600, margin: "2rem 0 0.5rem" }}><Bi id="Warna brand (untuk thumbnail)" en="Brand color (for thumbnails)" /></h3>
                <div className="color-row">{COLS.map((c, i) => <span key={c} className={`swatch-pick ${color === i ? "sel" : ""}`} style={{ background: c }} onClick={() => setColor(i)} />)}</div>
              </div>
            )}

            {/* C5 SCHEDULE */}
            {cur === 4 && (
              <div>
                <h1 className="ob-h"><Bi id="Tentukan jadwal publikasi" en="Set your publishing schedule" /></h1>
                <p className="ob-sub"><Bi id="Mesin akan memproduksi & publish otomatis sesuai slot ini." en="The engine will auto-produce & publish on these slots." /></p>
                <div className="note-box ai" style={{ marginTop: 0, marginBottom: "1.5rem" }}><Sparkles size={16} style={{ color: "var(--accent)" }} /><span data-id>Berdasarkan data, slot <b style={{ color: "var(--text-primary)" }}>10:00, 14:00, 19:00 WIB</b> punya engagement tertinggi. Kami sudah set sebagai default.</span><span data-en>Based on data, <b style={{ color: "var(--text-primary)" }}>10:00, 14:00, 19:00 WIB</b> have the highest engagement. We've set them as default.</span></div>
                <div className="week">
                  {DAYS.map((d) => (
                    <div className="day" key={d}>
                      <div className="dh">{d}</div>
                      {WEEK_SLOTS.map(([t, n]) => <div className="slot" key={t}><div className="st">{t}</div><div className="sn">{n}</div></div>)}
                      <button className="add-slot">+ Slot</button>
                    </div>
                  ))}
                </div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "1.5rem", padding: "1rem 1.25rem", border: "1px solid var(--border)", borderRadius: "var(--r-md)" }}>
                  <div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}><Bi id="Aktifkan scheduler sekarang" en="Activate scheduler now" /></div><div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Produksi pertama dimulai hari ini" en="First production starts today" /></div></div>
                  <label className="switch"><input type="checkbox" defaultChecked /><span className="track" /><span className="thumb" /></label>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>

      <div className="ob-foot">
        <a href="/dashboard" className="skip"><Bi id="Lewati semua, lakukan nanti" en="Skip all, do it later" /></a>
        <div className="nav">
          {err && <span style={{ color: "var(--danger, #ef4444)", fontSize: "var(--text-sm)", alignSelf: "center", marginRight: "0.75rem" }}>{err}</span>}
          {cur > 0 && <button className="btn btn-secondary" onClick={() => goto(cur - 1)} disabled={busy}><ArrowLeft size={15} /> <Bi id="Kembali" en="Back" /></button>}
          <button className={last ? "btn btn-ai" : "btn btn-default"} onClick={next} disabled={busy}>
            {busy ? <Loader2 size={15} className="spin" /> : <>{last ? <Bi id="Selesai Setup! Lihat Dashboard" en="Finish! Open dashboard" /> : <Bi id="Lanjut" en="Next" />} <ArrowRight size={15} /></>}
          </button>
        </div>
      </div>
    </div>
  );
}
