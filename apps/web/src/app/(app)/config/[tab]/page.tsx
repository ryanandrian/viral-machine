"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { fetchPricing, idrK } from "@/lib/pricing";
import {
  Sparkles, Command, Mic, Image as ImageIcon, Music, FileText, Gauge, List, Target, Bell, Shield,
  ChevronDown, CheckCircle, Loader2, Play, Pause, Settings, X, Clock, Wand2, Plus, Tv,
  Info, Eye, EyeOff, Minus, BarChart3, XCircle, HelpCircle, RefreshCw, Check, Zap,
} from "lucide-react";
import "../config.css";

// Config (D8-D19) STAGE 1 — port dari design-source/Config.html + config/cfg-engines.js (Hybrid).
// Routing PATH-based /config/[tab] (sinkron dgn sidebar AppShell href /config/<id> + active-state pathname).
// Shell + grup ENGINE: AI Engines, API Keys, Voice, Visual, Music. Content+System = Stage 2 ("Segera hadir").
// Mock deterministik (no Math.random → SSR-safe). Nol wiring Supabase (guardrail v1/v2).

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
  const supabase = createClient();
  const [llmKey, setLlmKey] = useState(""); const [ttsKey, setTtsKey] = useState(""); const [visualKey, setVisualKey] = useState("");
  const [lib, setLib] = useState<"anthropic" | "openai">("openai");
  const [has, setHas] = useState<{ llm: boolean; tts: boolean; visual: boolean }>({ llm: false, tts: false, visual: false });
  const [saving, setSaving] = useState(false); const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => {
    // Presence-check via kolom TERENKRIPSI (*_enc, migr 0044) — plaintext sudah di-null-kan.
    supabase.from("tenant_configs").select("llm_library, llm_api_key_enc, tts_api_key_enc, visual_api_key_enc").maybeSingle().then(({ data }) => {
      if (data) { setLib((data.llm_library as "anthropic" | "openai") || "openai"); setHas({ llm: !!data.llm_api_key_enc, tts: !!data.tts_api_key_enc, visual: !!data.visual_api_key_enc }); }
    });
  }, [supabase]);
  async function save() {
    setSaving(true); setSaved(null);
    // API key (rahasia) → vault TERENKRIPSI Fernet (server pemegang-kunci). llm_library = passthrough.
    const payload: Record<string, string> = { llm_library: lib };
    if (llmKey.trim()) payload.llm_api_key = llmKey.trim();
    if (ttsKey.trim()) payload.tts_api_key = ttsKey.trim();
    if (visualKey.trim()) payload.visual_api_key = visualKey.trim();
    const r = await fetch("/api/keys/set", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const ok = r.ok;
    setSaving(false); setSaved(ok ? "Tersimpan (key terenkripsi Fernet, tak di-log)" : "Gagal menyimpan");
    if (ok) { setHas({ llm: has.llm || !!payload.llm_api_key, tts: has.tts || !!payload.tts_api_key, visual: has.visual || !!payload.visual_api_key }); setLlmKey(""); setTtsKey(""); setVisualKey(""); }
  }
  const ph = (set: boolean) => set ? "•••••••• (tersimpan — isi untuk ganti)" : "Tempel API key";
  return (
    <>
      <Svc mark="A" color="var(--anthropic)" name="Script LLM" meta="Anthropic / OpenAI · script & hook">
        <div className="fld"><label className="label"><Bi id="Library" en="Library" /></label><div className="radio-row">{(["anthropic", "openai"] as const).map((o) => <span key={o} className={`radio-pill${lib === o ? " sel" : ""}`} onClick={() => setLib(o)} style={{ textTransform: "capitalize" }}>{o}</span>)}</div></div>
        <div className="fld-row"><div className="k">API Key (LLM)</div><input className="input input-mono" type="password" placeholder={ph(has.llm)} value={llmKey} onChange={(e) => setLlmKey(e.target.value)} /></div>
      </Svc>
      <Svc mark="11" color="var(--elevenlabs)" name="Text-to-Speech" meta="ElevenLabs · voiceover">
        <div className="fld-row"><div className="k">API Key (TTS)</div><input className="input input-mono" type="password" placeholder={ph(has.tts)} value={ttsKey} onChange={(e) => setTtsKey(e.target.value)} /></div>
      </Svc>
      <Svc mark="AI" color="var(--openai)" name="Visual AI" meta="OpenAI · image generation">
        <div className="fld-row"><div className="k">API Key (Visual)</div><input className="input input-mono" type="password" placeholder={ph(has.visual)} value={visualKey} onChange={(e) => setVisualKey(e.target.value)} /></div>
      </Svc>
      <div className="save-bar"><span className="muted">{saved ?? <Bi id="BYOK — key milikmu, terenkripsi Fernet, tak pernah di-log" en="BYOK — your keys, Fernet-encrypted, never logged" />}</span><button className="btn btn-default" disabled={saving} onClick={save}>{saving ? "Menyimpan…" : <Bi id="Simpan" en="Save" />}</button></div>
    </>
  );
}

function ApiKeys() {
  const supabase = createClient();
  const [cfg, setCfg] = useState<Record<string, unknown> | null>(null);
  useEffect(() => { supabase.from("tenant_configs").select("llm_api_key_enc, visual_api_key_enc, tts_api_key_enc, youtube_api_key_enc, telegram_chat_id, llm_library, tts_provider").maybeSingle().then(({ data }) => setCfg(data ?? {})); }, [supabase]);
  const rows: [string, string, string, boolean][] = cfg ? [
    ["A", `LLM (${(cfg.llm_library as string) || "—"})`, "var(--anthropic)", !!cfg.llm_api_key_enc],
    ["AI", "Visual (OpenAI)", "var(--openai)", !!cfg.visual_api_key_enc],
    ["11", `TTS (${(cfg.tts_provider as string) || "—"})`, "var(--elevenlabs)", !!cfg.tts_api_key_enc],
    ["YT", "YouTube Data API", "var(--yt)", !!cfg.youtube_api_key_enc],
    ["TG", "Telegram", "var(--telegram)", !!cfg.telegram_chat_id],
  ] : [];
  const st = (ok: boolean) => ok
    ? <span className="badge badge-success"><span className="dot" />Tersimpan</span>
    : <span className="badge badge-default"><span className="dot" />Belum diisi</span>;
  return (
    <>
      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr><th>Service</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {!cfg && <tr><td colSpan={3} className="muted" style={{ padding: "1rem", textAlign: "center" }}>Memuat…</td></tr>}
          {rows.map(([m, n, c, ok]) => (
          <tr key={n}>
            <td><span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}><Mark label={m} color={c} size={24} /><b style={{ color: "var(--text-primary)", fontWeight: 500 }}>{n}</b></span></td>
            <td>{st(ok)}</td>
            <td style={{ textAlign: "right" }}><Link href="/config/ai-engines" className="btn btn-ghost btn-sm"><Settings size={13} /> <Bi id="Kelola" en="Manage" /></Link></td>
          </tr>
          ))}
        </tbody></table></div></div>
      <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".75rem" }}><Bi id="Key di-isi & dienkripsi (Fernet) di tab AI Engines / Notifikasi. Status di atas = ada/tidaknya key tersimpan (nilai tak pernah ditampilkan/di-log). Validasi koneksi nyata = saat run produksi." en="Keys are set & Fernet-encrypted in AI Engines / Notifications. Status above = whether a key is stored (values never shown/logged). Live connection validation happens at production run." /></div>
    </>
  );
}

function Voice() {
  const supabase = createClient();
  const [current, setCurrent] = useState<string>(""); const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => { supabase.from("tenant_configs").select("tts_voice").maybeSingle().then(({ data }) => setCurrent(data?.tts_voice ?? "")); }, [supabase]);
  async function useVoice(name: string) {
    const { error } = await supabase.rpc("set_tenant_config", { p_tts_voice: name });
    if (!error) { setCurrent(name); setSaved(name); }
  }
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
      {saved && <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: ".75rem" }}>Voice aktif: <b style={{ color: "var(--text-primary)" }}>{saved}</b> — tersimpan.</div>}
      <div className="grid-3">{voices.map(([n, s, c], idx) => { const sel = current === n; return (
        <div key={n} className="card card-pad" style={sel ? { borderColor: "var(--brand)" } : undefined}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}><PlayBtn />
            <div><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{n}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{s}</div></div></div>
          <div style={{ height: 24, display: "flex", alignItems: "center", gap: 2, marginBottom: "0.75rem" }}>{bars(idx + 1, 32).map((h, i) => (<span key={i} style={{ flex: 1, height: `${h}%`, background: c, opacity: 0.5, borderRadius: 1 }} />))}</div>
          <button className={`btn ${sel ? "btn-default" : "btn-outline"} btn-sm`} style={{ width: "100%" }} onClick={() => useVoice(n)} disabled={sel}>{sel ? <Bi id="Sedang dipakai" en="In use" /> : <Bi id="Pakai suara ini" en="Use this voice" />}</button>
        </div>
      ); })}</div>
      <div className="card card-pad" style={{ marginTop: "1.25rem" }}><h3 className="card-title" style={{ marginBottom: "1rem" }}><Target size={15} /> <Bi id="Voice default per niche" en="Default voice per niche" /></h3>
        {niches.map(([nc, v]) => (<div key={nc} className="fld-row"><div className="k">{nc}</div><div className="selbox"><Mic size={14} /> {v} <ChevronDown size={14} /></div></div>))}
      </div>
    </>
  );
}

function Visual() {
  const supabase = createClient();
  const [mode, setMode] = useState("video"); const [quality, setQuality] = useState("low");
  const [saving, setSaving] = useState(false); const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => { supabase.from("tenant_configs").select("visual_mode, image_quality").maybeSingle().then(({ data }) => { if (data) { setMode(data.visual_mode ?? "video"); setQuality(data.image_quality ?? "low"); } }); }, [supabase]);
  async function save() { setSaving(true); setSaved(null); const { error } = await supabase.rpc("set_tenant_content_config", { p: { visual_mode: mode, image_quality: quality } }); setSaving(false); setSaved(error ? "Gagal" : "Tersimpan"); }
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
      <div className="card card-pad" style={{ marginBottom: "1.25rem" }}>
        <h3 className="card-title" style={{ marginBottom: "0.875rem" }}><Bi id="Mode & kualitas visual" en="Visual mode & quality" /></h3>
        <div className="fld-row"><div className="k"><Bi id="Mode visual" en="Visual mode" /><div className="sub">video=stok · ai_image=generate</div></div><div className="radio-row">{["video", "ai_image"].map((m) => <span key={m} className={`radio-pill${mode === m ? " sel" : ""}`} onClick={() => setMode(m)}>{m}</span>)}</div></div>
        <div className="fld-row"><div className="k"><Bi id="Kualitas gambar" en="Image quality" /></div><div className="radio-row">{["low", "standard", "high"].map((q) => <span key={q} className={`radio-pill${quality === q ? " sel" : ""}`} onClick={() => setQuality(q)}>{q}</span>)}</div></div>
        <div style={{ display: "flex", alignItems: "center", gap: ".75rem", marginTop: ".5rem" }}><button className="btn btn-default btn-sm" disabled={saving} onClick={save}>{saving ? "…" : <Bi id="Simpan" en="Save" />}</button>{saved && <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{saved}</span>}</div>
      </div>
      <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: ".5rem" }}><Bi id="Preset gaya & palet di bawah dikelola per-niche (Admin Niches: visual_style)." en="Style presets & palettes below are managed per-niche (Admin Niches: visual_style)." /></div>
      <div className="grid-4" style={{ opacity: 0.7 }}>{presets.map(([n, cols, sel]) => (
        <div key={n} className="card" style={{ overflow: "hidden", ...(sel ? { borderColor: "var(--brand)" } : {}) }}>
          <div style={{ height: 90, display: "flex" }}>{cols.map((c) => (<span key={c} style={{ flex: 1, background: c }} />))}</div>
          <div style={{ padding: "0.75rem 1rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}><span style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>{n}</span>{sel ? <span style={{ color: "var(--brand)" }}><CheckCircle size={16} /></span> : null}</div>
        </div>
      ))}</div>
      <div className="card card-pad" style={{ marginTop: "1.25rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}><h3 className="card-title" style={{ margin: 0 }}><Wand2 size={15} /> <Bi id="Prompt prefix kustom" en="Custom prompt prefix" /></h3><span className="badge badge-default">Segera</span></div>
        <textarea className="textarea input-mono" rows={3} disabled placeholder="Prompt visual diatur per-niche (Admin Niches: image_quality_tags / negative_prompt). Override per-tenant = segera." />
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
  const supabase = createClient();
  const [enabled, setEnabled] = useState(false); const [vol, setVol] = useState(0.18); const [defMood, setDefMood] = useState("");
  const [saving, setSaving] = useState(false); const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => { supabase.from("tenant_configs").select("music_enabled, music_volume, music_default_mood").maybeSingle().then(({ data }) => { if (data) { setEnabled(data.music_enabled ?? false); setVol(data.music_volume ?? 0.18); setDefMood(data.music_default_mood ?? ""); } }); }, [supabase]);
  async function save() { setSaving(true); setSaved(null); const { error } = await supabase.rpc("set_tenant_content_config", { p: { music_enabled: enabled, music_volume: vol, music_default_mood: defMood || null } }); setSaving(false); setSaved(error ? "Gagal" : "Tersimpan"); }
  const moods = ["Semua", "Tegang", "Misterius", "Epik", "Tenang", "Ceria"];
  const [mood, setMood] = useState(0);
  const tracks: [string, string, string, string, boolean][] = [
    ["Deep Abyss", "Misterius", "1:42", "#0ea5e9", true], ["Ancient Echoes", "Epik", "2:10", "#f59e0b", true],
    ["Tension Rising", "Tegang", "1:58", "#ef4444", false], ["Quiet Discovery", "Tenang", "2:24", "#22c55e", true],
    ["Cosmic Drift", "Misterius", "2:02", "#8b5cf6", false], ["Bright Facts", "Ceria", "1:36", "#ec4899", false],
  ];
  return (
    <>
      <div className="card card-pad" style={{ marginBottom: "1.25rem" }}>
        <h3 className="card-title" style={{ marginBottom: "0.875rem" }}><Bi id="Pengaturan musik channel" en="Channel music settings" /></h3>
        <div className="fld-row"><div className="k"><Bi id="Aktifkan musik latar" en="Enable background music" /></div><label className="switch"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /><span className="track" /><span className="thumb" /></label></div>
        <div className="fld-row"><div className="k"><Bi id="Volume" en="Volume" /><div className="sub">{Math.round(vol * 100)}%</div></div><input type="range" className="slider" min={0} max={100} value={Math.round(vol * 100)} onChange={(e) => setVol(+e.target.value / 100)} /></div>
        <div className="fld-row"><div className="k"><Bi id="Mood default (opsional)" en="Default mood (optional)" /></div><div className="radio-row">{["", "tegang", "misterius", "epik", "tenang"].map((m) => <span key={m || "auto"} className={`radio-pill${defMood === m ? " sel" : ""}`} onClick={() => setDefMood(m)}>{m || "auto"}</span>)}</div></div>
        <div style={{ display: "flex", alignItems: "center", gap: ".75rem", marginTop: ".5rem" }}><button className="btn btn-default btn-sm" disabled={saving} onClick={save}>{saving ? "…" : <Bi id="Simpan" en="Save" />}</button>{saved && <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{saved}</span>}</div>
      </div>
      <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: ".5rem" }}><Bi id="Library track di bawah = katalog (dikelola admin); mesin pilih track sesuai mood & niche." en="Track library below = catalog (admin-managed); the engine picks tracks by mood & niche." /></div>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>{moods.map((m, i) => (<button key={m} className={`radio-pill${i === mood ? " sel" : ""}`} onClick={() => setMood(i)}>{m}</button>))}</div>
      <div className="card"><div style={{ padding: "0.5rem" }}>
        {tracks.map(([n, md, dur, c, on], idx) => (
          <div key={n} className="mrow" style={{ display: "grid", gridTemplateColumns: "36px 1fr auto auto auto", alignItems: "center", gap: "0.875rem", padding: "0.625rem 0.75rem", borderRadius: "var(--r-md)" }}>
            <PlayBtn small />
            <div><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>{n}</div><div style={{ height: 14, display: "flex", alignItems: "center", gap: 1, marginTop: 2 }}>{bars(idx + 3, 40).map((h, i) => (<span key={i} style={{ flex: 1, height: `${h}%`, background: c, opacity: 0.4, borderRadius: 1 }} />))}</div></div>
            <span className="badge badge-default">{md}</span>
            <span className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{dur}</span>
            <span className="badge badge-default" style={{ fontSize: "0.5625rem", opacity: on ? 1 : 0.5 }}>{on ? "library" : "off"}</span>
          </div>
        ))}
      </div></div>
    </>
  );
}

// ===== STAGE 2 panels (port cfg-content.js): Captions, Quality, Hashtags, Niches, Notifications =====

function Captions() {
  const supabase = createClient();
  const [sub, setSub] = useState<"style" | "position" | "animation">("style");
  const [size, setSize] = useState(119);
  const [textColor, setTextColor] = useState("#FFFFFF");
  const [activeColor, setActiveColor] = useState("#FFD700");
  const [pos, setPos] = useState("bottom");
  const [maxLine, setMaxLine] = useState(2);
  const [raw, setRaw] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false); const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => {
    supabase.from("tenant_configs").select("caption_style").maybeSingle().then(({ data }) => {
      const c = (data?.caption_style ?? {}) as Record<string, unknown>;
      setRaw(c);
      if (typeof c.font_size === "number") setSize(c.font_size as number);
      if (typeof c.color === "string") setTextColor(c.color as string);
      if (typeof c.active_color === "string") setActiveColor(c.active_color as string);
      if (typeof c.position === "string") setPos(c.position as string);
      if (typeof c.max_lines === "number") setMaxLine(c.max_lines as number);
    });
  }, [supabase]);
  async function save() {
    setSaving(true); setSaved(null);
    const merged = { ...raw, font_size: size, color: textColor, active_color: activeColor, position: pos, max_lines: maxLine };
    const { error } = await supabase.rpc("set_tenant_content_config", { p: { caption_style: merged } });
    setSaving(false); setSaved(error ? "Gagal" : "Tersimpan");
  }
  return (
    <>
      <div style={{ display: "flex", gap: ".5rem", alignItems: "center", padding: ".625rem .875rem", background: "var(--brand-soft)", border: "1px solid color-mix(in srgb,var(--brand) 25%,transparent)", borderRadius: "var(--r-md)", marginBottom: "1.25rem", fontSize: "var(--text-sm)" }}>
        <Info size={15} /> <span><Bi id="Caption mengikuti bahasa konten channel (🇮🇩 Bahasa Indonesia). Skrip non-Latin (Thai) pakai font pendukung — sistem otomatis fallback." en="Captions follow the channel's content language (🇮🇩 Indonesian). Non-Latin scripts (Thai) use a supporting font — system auto-falls back." /></span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1.5rem", alignItems: "start" }} className="cap-grid">
        <div style={{ position: "sticky", top: 72 }}>
          <div style={{ aspectRatio: "9/16", borderRadius: "var(--r-lg)", overflow: "hidden", position: "relative", background: "linear-gradient(170deg,#0c2233,#05101a)", border: "1px solid var(--border)" }}>
            <div style={{ position: "absolute", inset: 0, background: "radial-gradient(120% 70% at 50% 25%,transparent,rgba(0,0,0,.5))" }} />
            <div style={{ position: "absolute", left: 12, right: 12, bottom: 60, textAlign: "center", fontFamily: "Anton,Geist,sans-serif", fontWeight: 800, fontSize: size * 0.25, lineHeight: 1.1, textShadow: "0 2px 8px rgba(0,0,0,.8)", color: textColor }}>Suara aneh di kedalaman <span style={{ color: activeColor }}>Mariana Trench</span></div>
          </div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", textAlign: "center", marginTop: ".5rem" }}>Preview · 9:16 Shorts</div>
        </div>
        <div>
          <div className="segmented" style={{ marginBottom: "1.25rem" }}>
            <button aria-selected={sub === "style"} onClick={() => setSub("style")}>Style</button>
            <button aria-selected={sub === "position"} onClick={() => setSub("position")}>Position</button>
            <button aria-selected={sub === "animation"} onClick={() => setSub("animation")}>Animation</button>
          </div>
          {sub === "style" && <>
            <div className="fld-row"><div className="k"><Bi id="Font" en="Font" /></div><div className="selbox">Anton <ChevronDown size={14} /></div></div>
            <div className="fld-row"><div className="k"><Bi id="Ukuran font" en="Font size" /><div className="sub">{size}px</div></div><input type="range" className="slider" min={60} max={150} value={size} onChange={(e) => setSize(+e.target.value)} /></div>
            <div className="fld-row"><div className="k"><Bi id="Warna teks" en="Text color" /></div><div style={{ display: "flex", gap: ".5rem" }}>{["#FFFFFF", "#F8FAFC", "#FDE68A"].map((c) => <span key={c} onClick={() => setTextColor(c)} style={{ width: 28, height: 28, borderRadius: "var(--r-sm)", background: c, border: `2px solid ${textColor === c ? "var(--text-primary)" : "transparent"}`, cursor: "pointer" }} />)}</div></div>
            <div className="fld-row"><div className="k"><Bi id="Warna kata aktif" en="Active word" /></div><div style={{ display: "flex", gap: ".5rem" }}>{["#FFD700", "#22D3EE", "#F472B6", "#34D399"].map((c) => <span key={c} onClick={() => setActiveColor(c)} style={{ width: 28, height: 28, borderRadius: "var(--r-sm)", background: c, border: `2px solid ${activeColor === c ? "var(--text-primary)" : "transparent"}`, cursor: "pointer" }} />)}</div></div>
            <div className="fld-row"><div className="k"><Bi id="Opasitas background" en="Background opacity" /></div><input type="range" className="slider" min={0} max={100} defaultValue={0} /></div>
          </>}
          {sub === "position" && <>
            <div className="fld-row"><div className="k"><Bi id="Posisi" en="Position" /></div><div className="radio-row">{["top", "center", "bottom"].map((p) => <span key={p} className={`radio-pill${pos === p ? " sel" : ""}`} onClick={() => setPos(p)} style={{ textTransform: "capitalize" }}>{p}</span>)}</div></div>
            <div className="fld-row"><div className="k"><Bi id="Margin vertikal" en="Vertical margin" /><div className="sub">326px</div></div><input type="range" className="slider" min={0} max={400} defaultValue={326} /></div>
            <div className="fld-row"><div className="k">Max line</div><div className="radio-row">{[1, 2, 3].map((n) => <span key={n} className={`radio-pill${maxLine === n ? " sel" : ""}`} onClick={() => setMaxLine(n)}>{n}</span>)}</div></div>
          </>}
          {sub === "animation" && <>
            <div className="fld-row"><div className="k"><Bi id="Gaya karaoke" en="Karaoke style" /></div><div className="radio-row"><span className="radio-pill sel">Word highlight</span><span className="radio-pill">Line fade</span><span className="radio-pill">Pop</span></div></div>
            <div className="fld-row"><div className="k"><Bi id="Kecepatan" en="Speed" /></div><div className="radio-row"><span className="radio-pill">Slow</span><span className="radio-pill sel">Medium</span><span className="radio-pill">Fast</span></div></div>
            <div className="fld-row"><div className="k"><Bi id="Kata per baris" en="Words per line" /><div className="sub">3</div></div><input type="range" className="slider" min={2} max={6} defaultValue={3} /></div>
          </>}
          <h4 style={{ fontSize: "var(--text-sm)", fontWeight: 600, margin: "1.5rem 0 .75rem" }}><Bi id="Template preset" en="Preset templates" /></h4>
          <div className="grid-4">{([["🎬 Cinematic", true], ["✨ Subtle", false], ["🔥 Bold", false], ["🎨 Custom", false]] as [string, boolean][]).map(([n, s]) => <button key={n} className={`radio-pill${s ? " sel" : ""}`} style={{ justifyContent: "center" }}>{n}</button>)}</div>
        </div>
      </div>
      <div className="save-bar"><span className="muted">{saved ?? <Bi id="Disimpan ke caption_style channel" en="Saves to channel caption_style" />}</span><button className="btn btn-default" disabled={saving} onClick={save}>{saving ? "Menyimpan…" : <Bi id="Simpan & Terapkan" en="Save & Apply" />}</button></div>
    </>
  );
}

function QHist({ thr }: { thr: number }) {
  const binsArr = [4, 9, 16, 24, 30, 34, 28, 18, 9, 4]; const W = 320, H = 90, max = 34, bw = W / binsArr.length; const thrX = ((thr - 50) / 40) * W;
  return (
    <svg viewBox="0 0 320 90" style={{ width: "100%", height: "auto", margin: ".5rem 0" }}>
      {binsArr.map((v, i) => { const h = (v / max) * (H - 16); return <rect key={i} x={i * bw + 3} y={H - h - 4} width={bw - 6} height={h} rx={2} fill={(i * bw) >= thrX ? "#10B981" : "var(--surface-3)"} />; })}
      <line x1={thrX} y1={0} x2={thrX} y2={H - 4} stroke="var(--brand)" strokeWidth={2} strokeDasharray="3 3" />
    </svg>
  );
}

function Quality() {
  const supabase = createClient();
  const [score, setScore] = useState(75); const [retry, setRetry] = useState(3); const [fail, setFail] = useState(0); const [locked, setLocked] = useState(false);
  const [saving, setSaving] = useState(false); const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => {
    supabase.from("tenant_configs").select("script_min_viral_score, script_max_retry").maybeSingle()
      .then(({ data }) => { if (data) { if (data.script_min_viral_score != null) setScore(data.script_min_viral_score); if (data.script_max_retry != null) setRetry(data.script_max_retry); } });
  }, [supabase]);
  async function save() {
    setSaving(true); setSaved(null);
    const { error } = await supabase.rpc("set_tenant_content_config", { p: { script_min_viral_score: score, script_max_retry: retry } });
    setSaving(false); setSaved(error ? "Gagal menyimpan" : "Tersimpan");
  }
  const pass = Math.max(20, Math.round(100 - (score - 50) * 1.7));
  const dims: [string, number][] = [["Hook Power", 80], ["Curiosity Gap", 80], ["Retention Arc", 80], ["Emotional Peak", 80], ["Information Density", 75], ["CTA Strength", 70]];
  const fails: [string, number, string][] = [["Emotional Peak", 60, "var(--error)"], ["Hook Power", 25, "var(--warning)"], ["Lainnya", 15, "var(--text-muted)"]];
  const actions: [string, string][] = [["🛑", "Skip publish + notif Telegram"], ["⚠️", "Publish dengan tag warning"], ["⏸️", "Pause channel sampai review"]];
  return (
    <>
      <button className="btn btn-ghost btn-sm" style={{ marginBottom: "1rem" }} onClick={() => setLocked((l) => !l)}>{locked ? <><EyeOff size={14} /> <Bi id="Kembali ke Pro" en="Back to Pro" /></> : <><Eye size={14} /> <Bi id="Pratinjau sebagai Starter (terkunci)" en="Preview as Starter (locked)" /></>}</button>
      <div className="lock-overlay" style={{ position: "relative" }}>
        {locked && <div className="lock-shade"><span className="lic"><Shield size={26} /></span><div style={{ fontWeight: 600 }}><Bi id="Quality Gate hanya untuk paket Pro+" en="Quality Gate is for Pro+ plans only" /></div><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Upgrade untuk kustomisasi threshold" en="Upgrade to customize thresholds" /></div><button className="btn btn-default btn-sm"><Zap size={14} /> Upgrade ke Pro</button></div>}
        <div className="grid-2">
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: ".25rem" }}>Minimum Viral Score</h3>
            <div style={{ display: "flex", alignItems: "baseline", gap: ".5rem", margin: ".5rem 0" }}><span style={{ fontSize: "var(--text-3xl)", fontWeight: 700 }}>{score}</span><span className="muted">/ 100</span></div>
            <QHist thr={score} />
            <input type="range" className="slider" min={50} max={90} value={score} onChange={(e) => setScore(+e.target.value)} />
            <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".625rem" }}>Dengan threshold {score}, <b style={{ color: "var(--text-primary)" }}>{pass}% video lolos</b>.</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: ".75rem" }}>Max retry</h3>
              <div style={{ display: "flex", alignItems: "center", gap: ".75rem" }}><button className="btn btn-secondary btn-icon btn-sm" onClick={() => setRetry((r) => Math.max(1, r - 1))}><Minus size={14} /></button><span style={{ fontSize: "var(--text-2xl)", fontWeight: 700, width: "2ch", textAlign: "center" }}>{retry}</span><button className="btn btn-secondary btn-icon btn-sm" onClick={() => setRetry((r) => Math.min(5, r + 1))}><Plus size={14} /></button>
                <span className="muted" style={{ fontSize: "var(--text-xs)", marginLeft: ".5rem" }}>~$0.07 / retry · max <b style={{ color: "var(--text-primary)" }}>${(retry * 0.07).toFixed(2)}</b></span></div>
            </div>
            <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: ".75rem" }}><Bi id="Aksi saat gagal" en="Action on fail" /></h3>
              {actions.map(([e, t], i) => <label key={i} onClick={() => setFail(i)} style={{ display: "flex", alignItems: "center", gap: ".625rem", padding: ".5rem .625rem", border: `1px solid ${fail === i ? "var(--brand)" : "var(--border)"}`, borderRadius: "var(--r-md)", marginBottom: ".5rem", cursor: "pointer", background: fail === i ? "var(--brand-soft)" : "" }}><input type="radio" name="qfail" checked={fail === i} readOnly style={{ accentColor: "var(--brand)" }} /> <span>{e}</span> <span style={{ fontSize: "var(--text-sm)" }}>{t}</span></label>)}
            </div>
          </div>
        </div>
        <details className="card card-pad" style={{ marginTop: "1rem" }}><summary style={{ cursor: "pointer", fontWeight: 600, fontSize: "var(--text-sm)", listStyle: "none", display: "flex", alignItems: "center", gap: ".5rem" }}><ChevronDown size={16} /> <Bi id="Threshold per-dimensi (advanced)" en="Per-dimension thresholds (advanced)" /></summary>
          <div style={{ marginTop: "1rem" }}>{dims.map(([n, v]) => <div key={n} className="fld-row"><div className="k">{n}<div className="sub">{v}</div></div><input type="range" className="slider" min={50} max={95} defaultValue={v} /></div>)}</div>
        </details>
        <div className="grid-2" style={{ marginTop: "1rem" }}>
          <div className="card card-pad"><h3 className="card-title" style={{ marginBottom: ".75rem" }}><BarChart3 size={15} /> <Bi id="Riwayat kualitas (30 hari)" en="Quality history (30d)" /></h3>
            <div style={{ fontSize: "var(--text-2xl)", fontWeight: 700, marginBottom: ".5rem" }}>85% <span className="muted" style={{ fontSize: "var(--text-sm)", fontWeight: 400 }}>pass rate</span></div>
            {fails.map(([n, v, c]) => <div key={n} style={{ display: "flex", alignItems: "center", gap: ".75rem", fontSize: "var(--text-xs)", padding: ".25rem 0" }}><span style={{ width: 110, color: "var(--text-secondary)" }}>{n}</span><div style={{ flex: 1, height: 7, background: "var(--surface-2)", borderRadius: 99, overflow: "hidden" }}><span style={{ display: "block", height: "100%", width: `${v}%`, background: c }} /></div><span className="mono">{v}%</span></div>)}
          </div>
          <div className="card card-pad" style={{ borderColor: "color-mix(in srgb,var(--accent) 30%,transparent)", background: "var(--accent-soft)" }}>
            <div style={{ display: "flex", gap: ".625rem" }}><span style={{ color: "var(--accent)", flex: "none" }}><Sparkles size={18} /></span><div><div style={{ fontSize: "var(--text-sm)", lineHeight: 1.5 }}><b style={{ color: "var(--text-primary)" }}><Bi id="Rekomendasi AI: " en="AI suggestion: " /></b><Bi id="Hook Power channelmu avg 76 — naikkan threshold ke 80 untuk hasil lebih konsisten?" en="Your Hook Power averages 76 — raise the threshold to 80 for more consistent results?" /></div><button className="btn btn-default btn-sm" style={{ marginTop: ".75rem" }}><Bi id="Terapkan" en="Apply" /></button></div></div>
          </div>
        </div>
      </div>
      <div className="save-bar"><span className="muted">{saved ?? <Bi id="Threshold disimpan ke channel" en="Thresholds save to channel" />}</span><button className="btn btn-default" disabled={saving || locked} onClick={save}>{saving ? "Menyimpan…" : <Bi id="Simpan" en="Save" />}</button></div>
    </>
  );
}

function Hashtags() {
  const supabase = createClient();
  const [niches, setNiches] = useState<{ niche_id: string; name: string; default_hashtags: string[] }[]>([]);
  const [ni, setNi] = useState(0);
  const [map, setMap] = useState<Record<string, string[]>>({}); // niche_hashtags jsonb
  const [draft, setDraft] = useState(""); const [saving, setSaving] = useState(false); const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      supabase.from("niches").select("niche_id, name, default_hashtags").eq("is_active", true).order("niche_id"),
      supabase.from("tenant_configs").select("niche_hashtags").maybeSingle(),
    ]).then(([nq, tc]) => {
      setNiches((nq.data ?? []).map((n) => ({ niche_id: n.niche_id, name: n.name, default_hashtags: Array.isArray(n.default_hashtags) ? n.default_hashtags : [] })));
      setMap((tc.data?.niche_hashtags as Record<string, string[]>) ?? {});
    });
  }, [supabase]);

  const cur = niches[ni];
  const custom = (cur && map[cur.niche_id]) || [];
  const setCustom = (arr: string[]) => { if (cur) setMap({ ...map, [cur.niche_id]: arr }); };
  async function save() {
    setSaving(true); setSaved(null);
    const { error } = await supabase.rpc("set_tenant_content_config", { p: { niche_hashtags: map } });
    setSaving(false); setSaved(error ? "Gagal" : "Tersimpan");
  }
  function addTag() { const t = draft.trim().replace(/^#?/, "#"); if (t.length > 1 && !custom.includes(t)) { setCustom([...custom, t]); setDraft(""); } }

  if (niches.length === 0) return <div className="card card-pad muted">Memuat niche…</div>;
  return (
    <>
      <div className="segmented" style={{ marginBottom: "1.25rem" }}>{niches.map((n, i) => <button key={n.niche_id} aria-selected={ni === i} onClick={() => setNi(i)}>{n.name}</button>)}</div>
      <div className="grid-2">
        <div className="card card-pad"><div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: ".5rem" }}><h3 className="card-title" style={{ margin: 0 }}><Bi id="Pool default" en="Default pool" /></h3><span className="badge badge-default">Read-only</span></div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: ".75rem" }}><Bi id="Default niche (admin). Dipakai jika custom kosong." en="Niche default (admin). Used when custom is empty." /></div>
          <div className="chip-input" style={{ borderStyle: "dashed" }}>{cur.default_hashtags.length ? cur.default_hashtags.map((t) => <span key={t} className="chip ghost">{t}</span>) : <span className="muted" style={{ fontSize: "var(--text-xs)" }}>—</span>}</div>
        </div>
        <div className="card card-pad"><div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: ".5rem" }}><h3 className="card-title" style={{ margin: 0 }}><Bi id="Hashtag custom" en="Custom hashtags" /></h3><span className="muted" style={{ fontSize: "var(--text-xs)" }}>{custom.length} tag</span></div>
          <div className="chip-input">{custom.map((t) => <span key={t} className="chip">{t} <span className="x" onClick={() => setCustom(custom.filter((x) => x !== t))}><X size={11} /></span></span>)}<input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }} style={{ border: "none", background: "none", outline: "none", color: "var(--text-primary)", fontSize: "var(--text-xs)", flex: 1, minWidth: 80 }} placeholder="+ tambah (Enter)" /></div>
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem", marginTop: ".75rem" }}><button className="btn btn-default btn-sm" disabled={saving} onClick={save}>{saving ? "…" : <Bi id="Simpan" en="Save" />}</button>{saved && <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{saved}</span>}</div>
        </div>
      </div>
      <div className="card card-pad" style={{ marginTop: "1rem", background: "var(--bg-elevated)" }}><h3 className="card-title" style={{ marginBottom: ".5rem" }}><Eye size={15} /> <Bi id="Preview metadata" en="Metadata preview" /></h3>
        <div className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: 1.7 }}>{(custom.length ? custom : cur.default_hashtags).join(" ") || "—"}</div>
      </div>
    </>
  );
}

function Mood({ cols }: { cols: string[] }) {
  return <div style={{ height: 64, display: "flex" }}>{cols.map((c) => <span key={c} style={{ flex: 1, background: c }} />)}</div>;
}

function Niches() {
  const [seg, setSeg] = useState(0);
  const [modal, setModal] = useState(false);
  const [pricing, setPricing] = useState<Record<string, number>>({});
  useEffect(() => { fetchPricing().then(setPricing); }, []);
  const active: [string, string[], string[], string][] = [
    ["Misteri Samudra", ["#082f49", "#0c4a6e", "#0ea5e9"], ["#laut", "#misteri", "#samudra"], "47 video · avg 2.3K"],
    ["Fakta Menarik", ["#052e16", "#14532d", "#22c55e"], ["#fakta", "#sains", "#tahukah"], "63 video · avg 3.1K"],
    ["Sejarah Kelam", ["#450a0a", "#7f1d1d", "#dc2626"], ["#sejarah", "#kelam", "#sejarahdunia"], "31 video · avg 1.8K"],
  ];
  const catalog: [string, string, string[], string][] = [
    ["Misteri Alam Semesta", "Luar angkasa & kosmos", ["#1e1b4b", "#312e81", "#4338ca"], "activate"],
    ["Teknologi Masa Depan", "AI, robotik, inovasi", ["#0c4a6e", "#075985", "#0891b2"], "swap"],
    ["Kriminal Nyata", "True crime Indonesia", ["#1c1917", "#44403c", "#78716c"], "premium"],
    ["Mitologi Nusantara", "Legenda & folklor lokal", ["#422006", "#854d0e", "#ca8a04"], "activate"],
  ];
  const newThis: [string, string, string[], string, boolean][] = [
    ["Detektif Kripto", "Investigasi skandal crypto", ["#14532d", "#15803d", "#22c55e"], "2 hari lalu", true],
    ["Misteri Medis", "Kasus medis yang tak terpecahkan", ["#4a044e", "#86198f", "#c026d3"], "5 hari lalu", true],
    ["Arsitektur Hilang", "Bangunan kuno yang lenyap", ["#1e3a8a", "#1d4ed8", "#3b82f6"], "12 hari lalu", false],
  ];
  const tags = ["kapal-hantu", "palung-laut", "makhluk-abisal", "kota-tenggelam", "arus-misterius", "pulau-hilang", "bangkai-kapal", "fenomena-laut", "legenda-pelaut", "dasar-samudra", "cahaya-laut", "suara-laut"];
  const segs = ["All (12)", "Active", "Inactive", "Premium", "Custom"];
  const catBtn = (s: string) => s === "activate"
    ? <button className="btn btn-outline btn-sm" style={{ width: "100%" }}><Bi id="Aktifkan" en="Activate" /></button>
    : s === "swap"
      ? <button className="btn btn-secondary btn-sm" style={{ width: "100%" }}><Bi id="Tukar dengan…" en="Swap with…" /> <ChevronDown size={13} /></button>
      : <button className="btn btn-secondary btn-sm" style={{ width: "100%" }} disabled><Shield size={13} /> Premium</button>;
  return (
    <>
      <div className="muted" style={{ fontSize: "var(--text-xs)", padding: ".625rem .875rem", background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)", borderRadius: "var(--r-md)", marginBottom: "1rem" }}>
        <Bi id="Katalog niche & aktivasi dikelola tim (Admin Niches) + entitlement per-tier. Harga request custom di bawah = nyata dari pricing_config. Alur request custom-niche = fitur terjadwal." en="Niche catalog & activation are team-managed (Admin Niches) + per-tier entitlement. Custom-request prices below are live from pricing_config. The custom-niche request flow is a scheduled feature." />
      </div>
      <div className="grid-4">
        {active.map(([n, cols, chips, stat]) => (
          <div key={n} className="card" style={{ overflow: "hidden" }}><Mood cols={cols} /><div style={{ padding: ".875rem 1rem" }}><div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{n}</div><label className="switch" style={{ width: "1.75rem", height: "1rem" }}><input type="checkbox" defaultChecked /><span className="track" /><span className="thumb" style={{ width: ".75rem", height: ".75rem" }} /></label></div>
            <div style={{ display: "flex", gap: ".25rem", flexWrap: "wrap", margin: ".5rem 0" }}>{chips.map((c) => <span key={c} className="badge badge-default" style={{ fontSize: ".625rem" }}>{c}</span>)}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)" }}>{stat}</div></div></div>
        ))}
        <div className="card" style={{ borderStyle: "dashed", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: ".375rem", color: "var(--text-muted)", cursor: "pointer", minHeight: 150 }}><Plus size={20} /><span style={{ fontSize: "var(--text-xs)" }}><Bi id="Tambah dari catalog" en="Add from catalog" /></span></div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: ".5rem", margin: "2rem 0 1rem" }}><span style={{ color: "var(--accent)" }}><Sparkles size={18} /></span><h3 style={{ fontSize: "var(--text-lg)", fontWeight: 600, margin: 0 }}><Bi id="Baru Bulan Ini" en="New This Month" /></h3></div>
      <div style={{ display: "flex", gap: "1rem", overflowX: "auto", paddingBottom: ".5rem" }}>
        {newThis.map(([n, d, cols, rel, fresh]) => (
          <div key={n} className="card" style={{ flex: "0 0 260px", overflow: "hidden", ...(fresh ? { boxShadow: "var(--glow-accent)", borderColor: "color-mix(in srgb,var(--accent) 30%,transparent)" } : {}) }}><Mood cols={cols} /><div style={{ padding: "1rem" }}><div style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{n}</div>{fresh ? <span className="badge badge-brand" style={{ fontSize: ".625rem" }}>Baru</span> : null}</div><div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".25rem 0 .5rem" }}>{d}</div><div className="muted" style={{ fontSize: ".625rem", marginBottom: ".75rem", display: "flex", alignItems: "center", gap: ".3rem" }}><Clock size={11} /> Released {rel}</div><button className="btn btn-default btn-sm" style={{ width: "100%" }}><Bi id="Aktifkan" en="Activate" /></button></div></div>
        ))}
      </div>

      <h3 style={{ fontSize: "var(--text-lg)", fontWeight: 600, margin: "2rem 0 1rem" }}><Bi id="Katalog Niche" en="Niche Catalog" /></h3>
      <div className="segmented" style={{ marginBottom: "1rem" }}>{segs.map((s, i) => <button key={s} aria-selected={seg === i} onClick={() => setSeg(i)}>{s}</button>)}</div>
      <div className="grid-4">
        {catalog.map(([n, d, cols, s]) => (
          <div key={n} className="card" style={{ overflow: "hidden" }}><Mood cols={cols} /><div style={{ padding: ".875rem 1rem" }}><div style={{ fontWeight: 600, fontSize: "var(--text-sm)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>{n}{s === "premium" ? <span style={{ color: "var(--text-muted)" }}><Shield size={14} /></span> : null}</div><div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".25rem 0 .75rem" }}>{d}</div><button className="btn btn-ghost btn-sm" style={{ marginBottom: ".5rem", padding: 0 }}><Play size={12} /> Sample</button>{catBtn(s)}</div></div>
        ))}
      </div>

      {/* custom request DUAL — pricing PLACEHOLDER {{pricing.*}} (no-hardcode rule) */}
      <div className="card" style={{ marginTop: "2rem", padding: "1.75rem", background: "linear-gradient(120deg,var(--surface-1),color-mix(in srgb,var(--accent) 8%,var(--surface-1)))", borderColor: "color-mix(in srgb,var(--accent) 25%,transparent)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: ".625rem", marginBottom: "1.25rem" }}><span style={{ color: "var(--accent)" }}><Wand2 size={20} /></span><div><h3 style={{ margin: 0, fontSize: "var(--text-lg)", fontWeight: 600 }}><Bi id="Tidak menemukan niche yang cocok?" en="Can't find the right niche?" /></h3><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Request niche custom — dibuat sesuai brief Anda." en="Request a custom niche — built to your brief." /></div></div></div>
        <div className="grid-2">
          <div className="card card-pad">
            <div style={{ display: "flex", alignItems: "center", gap: ".5rem", fontWeight: 600, marginBottom: ".375rem" }}>🌍 <Bi id="Public Niche" en="Public Niche" /></div>
            <div className="price-dyn" style={{ fontSize: "var(--text-xl)", fontWeight: 700 }}>{pricing.custom_niche_public_90d ? `Rp ${idrK(pricing.custom_niche_public_90d)}` : "Rp 299K"}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".625rem 0 1rem" }}><Bi id="90 hari exclusive untuk channel-mu, lalu masuk public catalog. Affordable, cocok untuk solo creator." en="90 days exclusive to your channel, then enters the public catalog. Affordable, great for solo creators." /></div>
            <button className="btn btn-default btn-sm" style={{ width: "100%" }} onClick={() => setModal(true)}><Bi id="Request Public Niche" en="Request Public Niche" /></button>
          </div>
          <div className="card card-pad" style={{ borderColor: "color-mix(in srgb,var(--accent) 35%,transparent)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: ".5rem", fontWeight: 600, marginBottom: ".375rem" }}>🔒 <Bi id="Permanent Private" en="Permanent Private" /> <span className="badge badge-brand" style={{ fontSize: ".625rem" }}>Premium</span></div>
            <div className="price-dyn" style={{ fontSize: "var(--text-xl)", fontWeight: 700, color: "var(--accent)" }}>{pricing.custom_niche_private ? `Rp ${idrK(pricing.custom_niche_private)}` : "Rp 1.499K"}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".625rem 0 1rem" }}><Bi id="Tidak pernah public. Exclusive permanen untuk channel-mu. Positioning premium untuk agency." en="Never public. Permanently exclusive to your channel. Premium positioning for agencies." /></div>
            <button className="btn btn-ai btn-sm" style={{ width: "100%" }} onClick={() => setModal(true)}><Bi id="Request Private Niche" en="Request Private Niche" /></button>
          </div>
        </div>
        <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "1rem", display: "flex", alignItems: "center", gap: ".4rem" }}><Clock size={13} /> <Bi id="SLA: 3–5 hari delivery" en="SLA: 3–5 day delivery" /></div>
      </div>

      <details className="card card-pad" style={{ marginTop: "1rem" }} open><summary style={{ cursor: "pointer", fontWeight: 600, fontSize: "var(--text-sm)", listStyle: "none", display: "flex", alignItems: "center", gap: ".5rem" }}><ChevronDown size={16} /> <Bi id="Sub-tag pool · Misteri Samudra" en="Sub-tag pool · Ocean Mysteries" /> <span className="muted" title="Dipakai untuk variety tracking + hashtag granular" style={{ cursor: "help" }}><HelpCircle size={13} /></span></summary>
        <div style={{ display: "flex", gap: ".375rem", flexWrap: "wrap", marginTop: "1rem" }}>{tags.map((t, i) => <span key={t} className="chip" style={i < 3 ? { borderColor: "var(--brand)", color: "var(--brand)" } : undefined}>{i < 3 ? <Check size={11} /> : null} {t}</span>)}</div>
        <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".75rem" }}><Bi id="Tag dengan tanda ✓ jadi preferensi default-mu." en="Tags marked ✓ are your defaults." /></div>
      </details>

      <div className="card card-pad" style={{ marginTop: "1rem" }}><h3 className="card-title" style={{ marginBottom: "1rem" }}><Bi id="Override per channel" en="Per-channel override" /></h3>
        <div style={{ overflowX: "auto" }}><table className="tbl"><thead><tr><th>Channel</th><th><Bi id="Niche default" en="Default niche" /></th><th>Override</th><th></th></tr></thead>
          <tbody>{([["Misteri Samudra", "Misteri Samudra"], ["Fakta Yang Bikin Mikir", "Fakta Menarik"], ["Jejak Kelam Sejarah", "Sejarah Kelam"]] as [string, string][]).map(([ch, nc]) => <tr key={ch}><td style={{ color: "var(--text-primary)" }}>{ch}</td><td className="muted">{nc}</td><td><span className="selbox" style={{ height: "1.875rem", fontSize: "var(--text-xs)" }}>{nc} <ChevronDown size={12} /></span></td><td><button className="btn btn-ghost btn-sm"><Bi id="Terapkan" en="Apply" /></button></td></tr>)}</tbody></table></div>
      </div>

      {modal && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setModal(false); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card" style={{ maxWidth: 520, width: "100%", maxHeight: "90vh", overflow: "auto" }}>
            <div className="card-head"><h3 className="card-title"><Bi id="Request niche custom" en="Request custom niche" /></h3><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal(false)}><X size={16} /></button></div>
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div><label className="label"><Bi id="Ide niche" en="Niche idea" /></label><textarea className="textarea" rows={2} placeholder="mis. Misteri kapal selam Perang Dunia II" /></div>
              <div><label className="label"><Bi id="Target audiens" en="Target audience" /></label><div className="chip-input"><span className="chip">pria 18-34</span><span className="chip">pecinta sejarah</span><input style={{ border: "none", background: "none", outline: "none", color: "var(--text-primary)", fontSize: "var(--text-xs)", flex: 1, minWidth: 80 }} placeholder="+ tambah" /></div></div>
              <div><label className="label"><Bi id="Channel YouTube referensi" en="Reference YouTube channels" /></label><input className="input input-mono" placeholder="youtube.com/@..." /></div>
              <div><label className="label"><Bi id="Angle viral & use case" en="Viral angle & use case" /></label><textarea className="textarea" rows={2} /></div>
            </div>
            <div className="card-foot" style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end" }}><button className="btn btn-ghost" onClick={() => setModal(false)}><Bi id="Batal" en="Cancel" /></button><button className="btn btn-default" onClick={() => setModal(false)}><Bi id="Kirim request" en="Submit request" /></button></div>
          </div>
        </div>
      )}
    </>
  );
}

function NotifCard({ mark, color, name, meta, badge, children }: { mark: string; color: string; name: string; meta: string; badge: React.ReactNode; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`svc${open ? " open" : ""}`}>
      <div className="svc-head" onClick={(e) => { if ((e.target as HTMLElement).closest("input,button,a,label")) return; setOpen((o) => !o); }}>
        <Mark label={mark} color={color} />
        <div><div className="svc-name">{name}</div><div className="svc-meta">{meta}</div></div>
        {badge}<span className="chev"><ChevronDown size={16} /></span>
      </div>
      <div className="svc-body">{children}</div>
    </div>
  );
}

function Notifications() {
  const supabase = createClient();
  const [chatId, setChatId] = useState(""); const [tgOn, setTgOn] = useState(true); const [email, setEmail] = useState("");
  const [saving, setSaving] = useState(false); const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => {
    supabase.from("tenant_configs").select("telegram_chat_id, telegram_enabled").maybeSingle().then(({ data }) => {
      if (data) { setChatId(data.telegram_chat_id ?? ""); setTgOn(data.telegram_enabled ?? true); }
    });
    supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? ""));
  }, [supabase]);
  async function saveTg() {
    setSaving(true); setSaved(null);
    const { error } = await supabase.rpc("set_tenant_config", { p_telegram_chat_id: chatId || null, p_telegram_enabled: tgOn });
    setSaving(false); setSaved(error ? "Gagal" : "Tersimpan");
  }
  const events: [string, string, number[]][] = [
    ["✅", "Video Published", [1, 1, 0, 1]], ["❌", "Run Failed", [1, 1, 1, 1]], ["⚠️", "Quality Gate Failed", [1, 0, 0, 1]],
    ["🚫", "Channel Suspended", [1, 1, 0, 1]], ["🛡️", "Compliance Score Low", [1, 1, 0, 1]], ["⏰", "Trial Ending", [0, 1, 0, 1]],
    ["💳", "Payment Failed", [1, 1, 0, 1]], ["💡", "Self-Learning Insight", [0, 0, 0, 1]], ["📊", "Weekly Digest", [0, 1, 0, 0]],
  ];
  const cols = ["Telegram", "Email", "Webhook", "In-app"];
  const okBadge = (t: string) => <span className="badge badge-success" style={{ marginLeft: "auto" }}><span className="dot" />{t}</span>;
  return (
    <>
      <NotifCard mark="TG" color="var(--telegram)" name="Telegram" meta="@MesinViralBot" badge={okBadge(tgOn ? "Aktif" : "Off")}>
        <div className="fld-row"><div className="k">Chat ID</div><div style={{ display: "flex", gap: ".5rem" }}><input className="input input-mono" value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="-100..." /></div></div>
        <div className="fld-row"><div className="k"><Bi id="Aktifkan notif Telegram" en="Enable Telegram notif" /></div><label className="switch"><input type="checkbox" checked={tgOn} onChange={(e) => setTgOn(e.target.checked)} /><span className="track" /><span className="thumb" /></label></div>
        <div style={{ display: "flex", alignItems: "center", gap: ".75rem", marginTop: ".5rem" }}><button className="btn btn-default btn-sm" disabled={saving} onClick={saveTg}>{saving ? "…" : <Bi id="Simpan" en="Save" />}</button>{saved && <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{saved}</span>}</div>
      </NotifCard>
      <NotifCard mark="@" color="var(--info)" name="Email" meta={email || "—"} badge={okBadge("Akun")}>
        <div className="fld-row"><div className="k"><Bi id="Email akun (transaksional)" en="Account email (transactional)" /></div><input className="input" value={email} disabled /></div>
        <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Email sistem (receipt, trial, suspend) dikirim ke email akun. Ganti email akun di Pengaturan." en="System emails (receipt, trial, suspend) go to your account email. Change it in Settings." /></div>
      </NotifCard>
      <NotifCard mark="{}" color="var(--surface-3)" name="Webhook" meta="" badge={<span className="badge badge-brand" style={{ marginLeft: "auto" }}>Enterprise</span>}>
        <div className="fld-row"><div className="k">URL</div><input className="input input-mono" placeholder="https://..." /></div>
        <div className="fld-row"><div className="k">HMAC secret</div><input className="input input-mono" type="password" placeholder="whsec_..." /></div>
      </NotifCard>
      <div className="card" style={{ marginTop: "1.25rem" }}><div className="card-head"><h3 className="card-title"><Bell size={15} /> <Bi id="Matriks event (default sistem)" en="Event matrix (system defaults)" /></h3></div>
        <div style={{ overflowX: "auto" }}><table className="tbl"><thead><tr><th>Event</th>{cols.map((c) => <th key={c} style={{ textAlign: "center" }}>{c}</th>)}</tr></thead>
          <tbody>{events.map(([e, n, vals]) => <tr key={n}><td><span style={{ color: "var(--text-primary)" }}>{e} {n}</span></td>{vals.map((v, i) => <td key={i} style={{ textAlign: "center" }}>{v ? <Check size={14} style={{ color: "var(--success)" }} /> : <span className="muted">—</span>}</td>)}</tr>)}</tbody></table></div>
        <div className="muted" style={{ fontSize: "var(--text-xs)", padding: ".75rem 1rem 0" }}><Bi id="Routing per-event kustom = segera. Saat ini: notif Telegram (diatur di atas) + email sistem transaksional." en="Custom per-event routing = coming soon. Currently: Telegram notif (set above) + transactional system email." /></div>
      </div>
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
  "captions": { title: { id: "Teks", en: "Captions" }, desc: { id: "Atur gaya subtitle karaoke yang muncul di video. Preview real-time.", en: "Style the karaoke subtitles shown in your videos. Real-time preview." }, Body: Captions },
  "quality": { title: { id: "Gerbang Kualitas", en: "Quality Gate" }, badge: <span className="badge badge-brand" style={{ fontSize: ".625rem" }}>Pro+</span>, desc: { id: "Tentukan threshold skor viral, retry, dan aksi saat gagal.", en: "Set viral-score threshold, retries, and action on failure." }, Body: Quality },
  "hashtags": { title: { id: "Hashtags", en: "Hashtags" }, desc: { id: "Kelola pool hashtag per niche untuk metadata YouTube.", en: "Manage the hashtag pool per niche for YouTube metadata." }, Body: Hashtags },
  "niches": { title: { id: "Niches", en: "Niches" }, desc: { id: "3 dari 4 niche aktif (Pro plan). Aktifkan dari catalog atau request niche custom.", en: "3 of 4 niches active (Pro plan). Activate from catalog or request a custom niche." }, Body: Niches },
  "notifications": { title: { id: "Notifikasi", en: "Notifications" }, desc: { id: "Pilih event apa yang dikirim ke channel mana.", en: "Choose which events go to which channels." }, Body: Notifications },
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

export default function ConfigTabPage() {
  const params = useParams<{ tab: string }>();
  const active = (params?.tab as string) || "ai-engines";

  const panel = PANELS[active];
  const meta = NAV.find((n) => "id" in n && n.id === active) as Extract<NavItem, { id: string }> | undefined;
  const HeadIcon = meta?.Icon ?? Sparkles;

  return (
    <div className="cfg-layout">
      <nav className="cfg-nav">
        {NAV.map((n, i) => "grp" in n
          ? <div className="cfg-grp" key={`g${i}`}><Bi id={n.grp.id} en={n.grp.en} /></div>
          : <Link key={n.id} className={`cfg-item${n.id === active ? " active" : ""}`} href={`/config/${n.id}`}>
              <n.Icon size={18} /><Bi id={n.t.id} en={n.t.en} />{n.lock ? <span className="lock"><Shield size={13} /></span> : null}
            </Link>
        )}
      </nav>
      <main className="cfg-main">
        <div className="cfg-head">
          {panel ? <>
            <h1><HeadIcon size={22} /> <Bi id={panel.title.id} en={panel.title.en} />{panel.badge}</h1>
            <p><Bi id={panel.desc.id} en={panel.desc.en} /></p>
          </> : <h1><HeadIcon size={22} /> {meta ? <Bi id={meta.t.id} en={meta.t.en} /> : null}</h1>}
        </div>
        <div>{panel ? <panel.Body /> : <div className="card card-pad muted"><Bi id="Segera hadir — panel ini dibangun di Stage 2." en="Coming soon — this panel ships in Stage 2." /></div>}</div>
      </main>
    </div>
  );
}
