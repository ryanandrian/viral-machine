"use client";

import { useState, useEffect } from "react";
import {
  Sparkles, Command, Mic, Image as ImageIcon, Music, FileText, Gauge, List, Target, Bell, Shield,
  ChevronDown, CheckCircle, Loader2, Play, Pause, RefreshCw, Settings, X, Clock, Wand2, Plus, Tv,
} from "lucide-react";
import "./config.css";

// Config (D8-D19) STAGE 1 — port dari design-source/Config.html + config/cfg-engines.js (Hybrid).
// Shell + grup ENGINE: AI Engines, API Keys, Voice, Visual, Music. Grup Content+System = Stage 2 ("Coming soon").
// Mock deterministik (no Math.random → SSR-safe). Nol wiring Supabase (guardrail v1/v2). Routing ?tab= pola auth.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

// brand icon disubstitusi kotak warna + inisial (lucide tak punya brand marks — gotcha D5)
function Mark({ label, color, size = 38 }: { label: string; color: string; size?: number }) {
  return <span className="svc-ic" style={{ background: color, width: size, height: size, fontSize: size <= 24 ? 10 : 13, fontWeight: 700 }}>{label}</span>;
}

// waveform deterministik (ganti Math.random)
function bars(seed: number, n: number): number[] {
  return Array.from({ length: n }, (_, i) => 20 + Math.round((Math.sin(seed * 1.7 + i * 0.6) * 0.5 + 0.5) * 60));
}

function TestBtn({ small, label }: { small?: boolean; label?: { id: string; en: string } }) {
  const [s, setS] = useState<"idle" | "loading" | "done">("idle");
  if (s === "done") {
    return (
      <span className="test-out" style={{ color: "var(--success)", display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "var(--text-sm)" }}>
        <CheckCircle size={15} /> <Bi id="Terhubung · $0.00" en="Connected · $0.00" />
      </span>
    );
  }
  return (
    <button className={`btn ${small ? "btn-ghost btn-sm" : "btn-secondary"}`} disabled={s === "loading"} onClick={() => { setS("loading"); setTimeout(() => setS("done"), 1100); }}>
      {s === "loading" ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : (label ? <Bi id={label.id} en={label.en} /> : <Bi id="Test" en="Test" />)}
    </button>
  );
}

function PlayBtn({ small }: { small?: boolean }) {
  const [p, setP] = useState(false);
  const sz = small ? 13 : 15;
  return (
    <button className={`btn btn-secondary btn-icon ${small ? "btn-sm" : ""}`} style={{ borderRadius: "50%" }} onClick={() => setP(!p)}>
      {p ? <Pause size={sz} /> : <Play size={sz} />}
    </button>
  );
}

function RadioRow({ options }: { options: string[] }) {
  const [sel, setSel] = useState(0);
  return (
    <div className="radio-row">
      {options.map((o, i) => (
        <span key={o} className={`radio-pill${i === sel ? " sel" : ""}`} onClick={() => setSel(i)}>{o}</span>
      ))}
    </div>
  );
}

function Svc({ mark, color, name, meta, defaultOpen = true, children }: { mark: string; color: string; name: string; meta: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`svc${open ? " open" : ""}`}>
      <div className="svc-head" onClick={(e) => { if ((e.target as HTMLElement).closest("input,button,select,a,label,.selbox,.radio-pill")) return; setOpen((o) => !o); }}>
        <Mark label={mark} color={color} />
        <div><div className="svc-name">{name}</div><div className="svc-meta">{meta}</div></div>
        <span className="badge badge-success" style={{ marginLeft: "auto" }}><span className="dot" />Connected</span>
        <span className="chev"><ChevronDown size={16} /></span>
      </div>
      <div className="svc-body">{children}</div>
    </div>
  );
}

function TaskRow({ k, sub, model }: { k: string; sub: string; model: string }) {
  return (
    <div className="fld-row">
      <div className="k">{k}<div className="sub">{sub}</div></div>
      <div className="selbox">{model} <ChevronDown size={14} /></div>
    </div>
  );
}

// ---------- panels ----------
function AiEngines() {
  return (
    <>
      <Svc mark="A" color="var(--anthropic)" name="Script LLM" meta="Anthropic Claude · script & hook">
        <div className="fld"><label className="label"><Bi id="Provider" en="Provider" /></label><RadioRow options={["Anthropic", "OpenAI"]} /></div>
        <TaskRow k="Script generate" sub="Tugas utama" model="Claude Sonnet 4.6" />
        <TaskRow k="Hook & utility" sub="Cepat & murah" model="Claude Haiku 4.5" />
        <div className="fld-row"><div className="k">API Key</div><div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}><input className="input input-mono" type="password" defaultValue="sk-ant-api03-xxxxxxxx" /><TestBtn /></div></div>
        <div className="fld-row"><div className="k"><Bi id="Pemakaian bulan ini" en="Usage this month" /></div><div><b style={{ fontWeight: 600 }}>$24</b> <span className="muted">· 612 requests</span></div></div>
      </Svc>
      <Svc mark="11" color="var(--elevenlabs)" name="Text-to-Speech" meta="ElevenLabs · voiceover">
        <div className="fld"><label className="label"><Bi id="Provider" en="Provider" /></label><RadioRow options={["ElevenLabs", "OpenAI TTS"]} /></div>
        <TaskRow k="Voiceover" sub="Model TTS" model="Multilingual v2" />
        <div className="fld-row"><div className="k">API Key</div><div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}><input className="input input-mono" type="password" defaultValue="xxxxxxxx" /><TestBtn /></div></div>
        <div className="fld-row"><div className="k"><Bi id="Pemakaian bulan ini" en="Usage this month" /></div><div><b style={{ fontWeight: 600 }}>$18</b> <span className="muted">· 430 requests</span></div></div>
      </Svc>
      <Svc mark="AI" color="var(--openai)" name="Visual AI" meta="OpenAI · image generation">
        <div className="fld"><label className="label"><Bi id="Provider" en="Provider" /></label><RadioRow options={["OpenAI"]} /></div>
        <TaskRow k="Image generate" sub="Visual per klip" model="gpt-image-1-mini" />
        <div className="fld-row"><div className="k">API Key</div><div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}><input className="input input-mono" type="password" defaultValue="sk-xxxxxxxx" /><TestBtn /></div></div>
        <div className="fld-row"><div className="k"><Bi id="Pemakaian bulan ini" en="Usage this month" /></div><div><b style={{ fontWeight: 600 }}>$31</b> <span className="muted">· 720 requests</span></div></div>
      </Svc>
      <div className="save-bar"><span className="muted"><Bi id="Perubahan belum disimpan" en="Unsaved changes" /></span><button className="btn btn-ghost"><Bi id="Reset" en="Reset" /></button><button className="btn btn-default"><Bi id="Simpan" en="Save" /></button></div>
    </>
  );
}

function ApiKeys() {
  const rows: [string, string, string, "connected" | "failed", string, string][] = [
    ["A", "Anthropic", "var(--anthropic)", "connected", "2 jam lalu", "5 menit lalu"],
    ["AI", "OpenAI", "var(--openai)", "connected", "2 jam lalu", "12 menit lalu"],
    ["11", "ElevenLabs", "var(--elevenlabs)", "connected", "1 hari lalu", "5 menit lalu"],
    ["YT", "YouTube Data API", "var(--yt)", "connected", "3 hari lalu", "baru saja"],
    ["TG", "Telegram Bot", "var(--telegram)", "failed", "1 hari lalu", "—"],
  ];
  const st = (s: "connected" | "failed") => s === "connected"
    ? <span className="badge badge-success"><span className="dot" />Connected</span>
    : <span className="badge badge-error"><span className="dot" />Failed</span>;
  return (
    <>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "1rem" }}><TestBtn label={{ id: "Test semua", en: "Test all" }} /></div>
      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr><th>Service</th><th>Status</th><th>Last test</th><th>Last used</th><th></th></tr></thead>
        <tbody>{rows.map(([m, n, c, s, lt, lu]) => (
          <tr key={n}>
            <td><span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}><Mark label={m} color={c} size={24} /><b style={{ color: "var(--text-primary)", fontWeight: 500 }}>{n}</b></span></td>
            <td>{st(s)}</td><td className="muted">{lt}</td><td className="muted">{lu}</td>
            <td><div style={{ display: "flex", gap: "0.25rem", justifyContent: "flex-end" }}><TestBtn small /><button className="btn btn-ghost btn-icon btn-sm"><Settings size={14} /></button><button className="btn btn-ghost btn-icon btn-sm" style={{ color: "var(--error)" }}><X size={14} /></button></div></td>
          </tr>
        ))}</tbody></table></div></div>
      <div className="card card-pad" style={{ marginTop: "1rem" }}><h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Clock size={15} /> <Bi id="Audit log" en="Audit log" /></h3>
        {["API key Anthropic diperbarui · 2 hari lalu", "Telegram bot token gagal validasi · 1 hari lalu", "API key OpenAI ditambahkan · 5 hari lalu"].map((t) => (
          <div key={t} style={{ fontSize: "var(--text-sm)", color: "var(--text-secondary)", padding: "0.4rem 0", borderBottom: "1px solid var(--border-subtle)" }}>{t}</div>
        ))}
      </div>
    </>
  );
}

function Voice() {
  const filters = ["Style: Semua", "Gender: Semua", "Usia: Semua"];
  const voices: [string, string, string, boolean][] = [
    ["Arya", "Pria · dalam, misterius", "#1d4ed8", true], ["Sari", "Wanita · hangat, naratif", "#9f1239", false],
    ["Bima", "Pria · energik, muda", "#047857", false], ["Dewi", "Wanita · tenang, jernih", "#7c3aed", false],
    ["Galih", "Pria · berwibawa", "#b45309", false], ["Nadia", "Wanita · ekspresif", "#be185d", false],
  ];
  const niches: [string, string][] = [["Misteri Samudra", "Arya"], ["Fakta Menarik", "Bima"], ["Sejarah Kelam", "Galih"]];
  return (
    <>
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", padding: "0.625rem 0.875rem", background: "var(--brand-soft)", border: "1px solid color-mix(in srgb,var(--brand) 25%,transparent)", borderRadius: "var(--r-md)", marginBottom: "1rem", fontSize: "var(--text-sm)" }}>
        <Tv size={15} /> <span><Bi id={"Channel: Misteri Samudra · bahasa konten"} en={"Channel: Misteri Samudra · content language"} /></span>
        <span className="badge badge-default" style={{ marginLeft: "auto" }}>🇮🇩 Bahasa Indonesia</span>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>{filters.map((f) => (<span key={f} className="selbox" style={{ height: "2rem" }}>{f} <ChevronDown size={13} /></span>))}</div>
      <div className="grid-3">{voices.map(([n, s, c, sel], idx) => (
        <div key={n} className="card card-pad" style={sel ? { borderColor: "var(--brand)" } : undefined}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}><PlayBtn />
            <div><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{n}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{s}</div></div></div>
          <div style={{ height: 24, display: "flex", alignItems: "center", gap: 2, marginBottom: "0.75rem" }}>{bars(idx + 1, 32).map((h, i) => (<span key={i} style={{ flex: 1, height: `${h}%`, background: c, opacity: 0.5, borderRadius: 1 }} />))}</div>
          <button className={`btn ${sel ? "btn-default" : "btn-outline"} btn-sm`} style={{ width: "100%" }}>{sel ? <Bi id="Sedang dipakai" en="In use" /> : <Bi id="Pakai suara ini" en="Use this voice" />}</button>
        </div>
      ))}</div>
      <div className="card card-pad" style={{ marginTop: "1.25rem" }}><h3 className="card-title" style={{ marginBottom: "1rem" }}><Target size={15} /> <Bi id="Voice default per niche" en="Default voice per niche" /></h3>
        {niches.map(([nc, v]) => (<div key={nc} className="fld-row"><div className="k">{nc}</div><div className="selbox"><Mic size={14} /> {v} <ChevronDown size={14} /></div></div>))}
      </div>
    </>
  );
}

function Visual() {
  const presets: [string, string[], boolean][] = [
    ["Cinematic Dark", ["#0c1222", "#1e293b", "#334155"], true],
    ["Vibrant", ["#7c3aed", "#db2777", "#f59e0b"], false],
    ["Minimalist", ["#f8fafc", "#cbd5e1", "#64748b"], false],
    ["Mysterious", ["#0f172a", "#1e1b4b", "#4c1d95"], false],
  ];
  const palettes: [string, string[]][] = [
    ["Misteri Samudra", ["#082f49", "#0c4a6e", "#0ea5e9"]],
    ["Sejarah Kelam", ["#450a0a", "#7f1d1d", "#dc2626"]],
    ["Fakta Menarik", ["#052e16", "#14532d", "#22c55e"]],
  ];
  return (
    <>
      <div className="grid-4">{presets.map(([n, cols, sel]) => (
        <div key={n} className="card" style={{ cursor: "pointer", overflow: "hidden", ...(sel ? { borderColor: "var(--brand)" } : {}) }}>
          <div style={{ height: 90, display: "flex" }}>{cols.map((c) => (<span key={c} style={{ flex: 1, background: c }} />))}</div>
          <div style={{ padding: "0.75rem 1rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>{n}</span>{sel ? <span style={{ color: "var(--brand)" }}><CheckCircle size={16} /></span> : null}</div>
        </div>
      ))}</div>
      <div className="card card-pad" style={{ marginTop: "1.25rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}><h3 className="card-title" style={{ margin: 0 }}><Wand2 size={15} /> <Bi id="Prompt prefix kustom" en="Custom prompt prefix" /></h3><span className="badge badge-brand">Pro+</span></div>
        <textarea className="textarea input-mono" rows={3} defaultValue="cinematic, dark moody lighting, deep ocean atmosphere, volumetric fog, 9:16 vertical, highly detailed" />
      </div>
      <div className="card card-pad" style={{ marginTop: "1rem" }}><h3 className="card-title" style={{ marginBottom: "1rem" }}><Bi id="Palet warna per niche" en="Color palette per niche" /></h3>
        {palettes.map(([n, cols]) => (
          <div key={n} className="fld-row"><div className="k">{n}</div><div style={{ display: "flex", gap: "0.5rem" }}>{cols.map((c) => (<span key={c} style={{ width: 28, height: 28, borderRadius: "var(--r-sm)", background: c, border: "1px solid var(--border)" }} />))}<button className="btn btn-ghost btn-icon btn-sm"><Plus size={14} /></button></div></div>
        ))}
      </div>
    </>
  );
}

function MusicPanel() {
  const moods = ["Semua", "Tegang", "Misterius", "Epik", "Tenang", "Ceria"];
  const [mood, setMood] = useState(0);
  const tracks: [string, string, string, string, boolean][] = [
    ["Deep Abyss", "Misterius", "1:42", "#0ea5e9", true], ["Ancient Echoes", "Epik", "2:10", "#f59e0b", true],
    ["Tension Rising", "Tegang", "1:58", "#ef4444", false], ["Quiet Discovery", "Tenang", "2:24", "#22c55e", true],
    ["Cosmic Drift", "Misterius", "2:02", "#8b5cf6", false], ["Bright Facts", "Ceria", "1:36", "#ec4899", false],
  ];
  return (
    <>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>{moods.map((m, i) => (<button key={m} className={`radio-pill${i === mood ? " sel" : ""}`} onClick={() => setMood(i)}>{m}</button>))}</div>
      <div className="card"><div style={{ padding: "0.5rem" }}>
        {tracks.map(([n, md, dur, c, on], idx) => (
          <div key={n} className="mrow" style={{ display: "grid", gridTemplateColumns: "36px 1fr auto auto auto", alignItems: "center", gap: "0.875rem", padding: "0.625rem 0.75rem", borderRadius: "var(--r-md)" }}>
            <PlayBtn small />
            <div><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>{n}</div><div style={{ height: 14, display: "flex", alignItems: "center", gap: 1, marginTop: 2 }}>{bars(idx + 3, 40).map((h, i) => (<span key={i} style={{ flex: 1, height: `${h}%`, background: c, opacity: 0.4, borderRadius: 1 }} />))}</div></div>
            <span className="badge badge-default">{md}</span>
            <span className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{dur}</span>
            <label className="switch"><input type="checkbox" defaultChecked={on} /><span className="track" /><span className="thumb" /></label>
          </div>
        ))}
      </div></div>
    </>
  );
}

type Panel = { title: { id: string; en: string }; desc: { id: string; en: string }; badge?: React.ReactNode; Body: () => React.ReactElement };
const PANELS: Record<string, Panel> = {
  "ai-engines": { title: { id: "Mesin AI", en: "AI Engines" }, desc: { id: "Pilih provider & model per tugas produksi. Hubungkan API key milikmu (BYOK).", en: "Choose provider & model per production task. Connect your own API keys (BYOK)." }, Body: AiEngines },
  "api-keys": { title: { id: "API Keys", en: "API Keys" }, desc: { id: "Kelola semua API key. Dienkripsi Fernet AES-128, tidak pernah di-log.", en: "Manage all API keys. Encrypted with Fernet AES-128, never logged." }, Body: ApiKeys },
  "voice": { title: { id: "Suara", en: "Voice" }, desc: { id: "Voice difilter oleh bahasa konten channel aktif. Tetapkan voice default per niche.", en: "Voices are filtered by the active channel's content language. Set a default voice per niche." }, Body: Voice },
  "visual": { title: { id: "Visual", en: "Visual" }, desc: { id: "Pilih preset gaya visual & sesuaikan prompt per niche.", en: "Choose a visual style preset & customize prompts per niche." }, Body: Visual },
  "music": { title: { id: "Musik", en: "Music" }, desc: { id: "Library musik latar. Mesin memilih mood otomatis sesuai niche & performa.", en: "Background music library. The engine auto-selects mood by niche & performance." }, Body: MusicPanel },
};

type NavItem = { grp: { id: string; en: string } } | { id: string; Icon: typeof Sparkles; t: { id: string; en: string }; lock?: boolean };
const NAV: NavItem[] = [
  { grp: { id: "Mesin", en: "Engine" } },
  { id: "ai-engines", Icon: Sparkles, t: { id: "Mesin AI", en: "AI Engines" } },
  { id: "api-keys", Icon: Command, t: { id: "API Keys", en: "API Keys" } },
  { id: "voice", Icon: Mic, t: { id: "Suara", en: "Voice" } },
  { id: "visual", Icon: ImageIcon, t: { id: "Visual", en: "Visual" } },
  { id: "music", Icon: Music, t: { id: "Musik", en: "Music" } },
  { grp: { id: "Konten", en: "Content" } },
  { id: "captions", Icon: FileText, t: { id: "Teks", en: "Captions" } },
  { id: "quality", Icon: Gauge, t: { id: "Gerbang Kualitas", en: "Quality Gate" }, lock: true },
  { id: "hashtags", Icon: List, t: { id: "Hashtags", en: "Hashtags" } },
  { id: "niches", Icon: Target, t: { id: "Niches", en: "Niches" } },
  { grp: { id: "Sistem", en: "System" } },
  { id: "notifications", Icon: Bell, t: { id: "Notifikasi", en: "Notifications" } },
];

export default function ConfigPage() {
  const [active, setActive] = useState("ai-engines");

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("tab");
    if (t && PANELS[t]) setActive(t);
  }, []);

  function select(id: string) {
    setActive(id);
    history.replaceState(null, "", `?tab=${id}`);
    window.scrollTo(0, 0);
  }

  const panel = PANELS[active];
  const meta = NAV.find((n) => "id" in n && n.id === active) as Extract<NavItem, { id: string }> | undefined;
  const HeadIcon = meta?.Icon ?? Sparkles;

  return (
    <div className="cfg-layout">
      <nav className="cfg-nav">
        {NAV.map((n, i) => "grp" in n
          ? <div className="cfg-grp" key={`g${i}`}><Bi id={n.grp.id} en={n.grp.en} /></div>
          : <div key={n.id} className={`cfg-item${n.id === active ? " active" : ""}`} onClick={() => select(n.id)}>
              <n.Icon size={18} /><Bi id={n.t.id} en={n.t.en} />{n.lock ? <span className="lock"><Shield size={13} /></span> : null}
            </div>
        )}
      </nav>
      <main className="cfg-main">
        <div className="cfg-head">
          {panel ? <>
            <h1><HeadIcon size={22} /> <Bi id={panel.title.id} en={panel.title.en} />{panel.badge}</h1>
            <p><Bi id={panel.desc.id} en={panel.desc.en} /></p>
          </> : <h1>{meta ? <Bi id={meta.t.id} en={meta.t.en} /> : null}</h1>}
        </div>
        <div>{panel ? <panel.Body /> : <div className="muted"><Bi id="Segera hadir." en="Coming soon." /></div>}</div>
      </main>
    </div>
  );
}
