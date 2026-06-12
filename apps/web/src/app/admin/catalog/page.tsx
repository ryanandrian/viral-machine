"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, Upload, Settings, MoreVertical, Play, Pause, Target, ArrowRight } from "lucide-react";
import "./catalog.css";

// E2 Admin Catalog — port dari design-source/Admin Catalog.html (Hybrid). /admin/catalog.
// Tab: AI Models / Music / Niche (link) / Voice / Content Languages (E2.5). Mock deterministik (SSR-safe).
// Brand icon→kotak inisial; wave deterministik (ganti Math.random); nol wiring Supabase. Prefix cat-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}
function bars(seed: number, n: number): number[] {
  return Array.from({ length: n }, (_, i) => 20 + Math.round((Math.sin(seed * 1.7 + i * 0.6) * 0.5 + 0.5) * 70));
}
function PlayBtn() {
  const [p, setP] = useState(false);
  return <button className="btn btn-secondary btn-icon btn-sm" onClick={() => setP(!p)}>{p ? <Pause size={13} /> : <Play size={13} />}</button>;
}

const TABS: [string, string][] = [["models", "AI Models"], ["music", "Music Library"], ["niche", "Niche Library"], ["voice", "Voice Templates"], ["languages", "Content Languages"]];
const MARK: Record<string, [string, string]> = { anthropic: ["var(--anthropic)", "A"], openai: ["var(--openai)", "AI"], elevenlabs: ["var(--elevenlabs)", "11"] };
const MODELS: [string, string, string, string, boolean][] = [
  ["claude_sonnet", "anthropic", "claude-sonnet-4.6", "Script generate utama", true],
  ["claude_haiku", "anthropic", "claude-haiku-4.5", "Hook & utility cepat", true],
  ["gpt_image", "openai", "gpt-image-1-mini", "Visual per klip", true],
  ["gpt_4o", "openai", "gpt-4o", "LLM alternatif", true],
  ["eleven_v2", "elevenlabs", "multilingual-v2", "TTS voiceover", true],
  ["gpt_image_legacy", "openai", "dall-e-3", "Visual (legacy)", false],
];
const MOODS = ["Misterius", "Tegang", "Epik", "Tenang", "Ceria"]; const MCOL = ["#0ea5e9", "#ef4444", "#f59e0b", "#22c55e", "#ec4899"];
const TRACKS: [string, number, string][] = [["Deep Abyss", 0, "1:42"], ["Tension Rising", 1, "1:58"], ["Ancient Echoes", 2, "2:10"], ["Quiet Discovery", 3, "2:24"], ["Cosmic Drift", 0, "2:02"], ["Bright Facts", 4, "1:36"], ["Dark Ritual", 1, "2:14"], ["Ocean Depths", 0, "1:50"]];
const VOICES: [string, string, string][] = [["Arya", "Pria · dalam", "Misteri Samudra"], ["Sari", "Wanita · hangat", "—"], ["Bima", "Pria · energik", "Fakta Menarik"], ["Galih", "Pria · berwibawa", "Sejarah Kelam"], ["Dewi", "Wanita · tenang", "—"]];
const LANGS: { code: string; flag: string; name: string; en: string; tier: string; latin: boolean; voices: number; ch: number }[] = [
  { code: "id-ID", flag: "🇮🇩", name: "Bahasa Indonesia", en: "Indonesian", tier: "official", latin: true, voices: 4, ch: 198 },
  { code: "en-US", flag: "🇬🇧", name: "English", en: "English", tier: "official", latin: true, voices: 3, ch: 64 },
  { code: "ms-MY", flag: "🇲🇾", name: "Bahasa Malaysia", en: "Malay", tier: "experimental", latin: true, voices: 2, ch: 21 },
  { code: "fil-PH", flag: "🇵🇭", name: "Filipino", en: "Filipino", tier: "experimental", latin: true, voices: 2, ch: 9 },
  { code: "th-TH", flag: "🇹🇭", name: "ภาษาไทย", en: "Thai", tier: "experimental", latin: false, voices: 2, ch: 4 },
  { code: "vi-VN", flag: "🇻🇳", name: "Tiếng Việt", en: "Vietnamese", tier: "experimental", latin: true, voices: 2, ch: 6 },
];

export default function AdminCatalogPage() {
  const [tab, setTab] = useState("models");
  return (
    <>
      <div style={{ marginBottom: "1.25rem" }}><h1 style={{ fontSize: "var(--text-3xl)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 0.25rem" }}>Catalog</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Kelola model AI, musik, dan voice template" en="Manage AI models, music, and voice templates" /></div></div>

      <div className="cat-tabs">{TABS.map(([k, l]) => <button key={k} className={`cat-tab${tab === k ? " active" : ""}`} onClick={() => setTab(k)}>{l}</button>)}</div>

      {tab === "models" && (
        <>
          <div className="cat-toolbar"><div className="right"><button className="btn btn-default btn-sm"><Plus size={14} /> <Bi id="Tambah model" en="Add model" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>model_key</th><th>platform</th><th>model_id</th><th><Bi id="Deskripsi" en="Description" /></th><th>active</th><th></th></tr></thead>
            <tbody>{MODELS.map(([k, p, id, d, act]) => { const [c, ini] = MARK[p]; return (
              <tr key={k}>
                <td className="mono" style={{ color: "var(--text-primary)" }}>{k}</td>
                <td><span style={{ display: "inline-flex", alignItems: "center", gap: ".4rem" }}><span style={{ width: 20, height: 20, borderRadius: 5, background: c, display: "grid", placeItems: "center", color: "#fff", fontSize: 9, fontWeight: 700 }}>{ini}</span>{p}</span></td>
                <td className="mono">{id}</td><td className="muted" style={{ fontSize: "var(--text-xs)" }}>{d}</td>
                <td><label className="switch"><input type="checkbox" defaultChecked={act} /><span className="track" /><span className="thumb" /></label></td>
                <td><div style={{ display: "flex", gap: ".25rem", justifyContent: "flex-end" }}><button className="btn btn-ghost btn-icon btn-sm"><Settings size={14} /></button></div></td>
              </tr>
            ); })}</tbody>
          </table></div></div>
        </>
      )}

      {tab === "music" && (
        <>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}>68 tracks</span><div className="right"><button className="btn btn-secondary btn-sm"><Upload size={14} /> <Bi id="Bulk upload" en="Bulk upload" /></button></div></div>
          <div className="card"><div style={{ padding: "0.5rem" }}>
            {TRACKS.map(([n, m, dur], idx) => (
              <div className="cat-row" key={n} style={{ gridTemplateColumns: "32px 1fr auto auto auto" }}>
                <PlayBtn />
                <div><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>{n}</div><div className="cat-wave">{bars(idx + 1, 44).map((h, i) => <span key={i} style={{ height: `${h}%`, background: MCOL[m], opacity: 0.4 }} />)}</div></div>
                <span className="badge badge-default">{MOODS[m]}</span><span className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{dur}</span>
                <button className="btn btn-ghost btn-icon btn-sm"><MoreVertical size={14} /></button>
              </div>
            ))}
          </div></div>
        </>
      )}

      {tab === "niche" && (
        <div className="card card-pad" style={{ textAlign: "center", padding: "3rem" }}>
          <div style={{ color: "var(--text-muted)", marginBottom: "0.75rem", display: "flex", justifyContent: "center" }}><Target size={32} /></div>
          <p className="muted" style={{ marginBottom: "1rem" }}><Bi id="Niche library punya halaman khusus dengan drawer 6-tab, monthly release, dan exclusivity pipeline." en="The niche library has a dedicated page with a 6-tab drawer, monthly release, and exclusivity pipeline." /></p>
          <Link href="/admin/niches" className="btn btn-default btn-sm"><Bi id="Buka Niche Library" en="Open Niche Library" /> <ArrowRight size={14} /></Link>
        </div>
      )}

      {tab === "voice" && (
        <div className="card"><div style={{ padding: "0.5rem" }}>
          {VOICES.map(([n, s, niche]) => (
            <div className="cat-row" key={n} style={{ gridTemplateColumns: "32px 1fr auto auto" }}>
              <PlayBtn />
              <div><div style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>{n}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{s}</div></div>
              <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{niche !== "—" ? `default: ${niche}` : ""}</span>
              <button className="btn btn-ghost btn-icon btn-sm"><Settings size={14} /></button>
            </div>
          ))}
        </div></div>
      )}

      {tab === "languages" && (
        <>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Katalog bahasa konten — dikelola admin, dibaca per-channel" en="Content language catalog — admin-managed, read per-channel" /></span><div className="right"><button className="btn btn-default btn-sm"><Plus size={14} /> <Bi id="Tambah bahasa" en="Add language" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>code</th><th><Bi id="Bahasa" en="Language" /></th><th>Tier</th><th className="num"><Bi id="Voice" en="Voices" /></th><th className="num">Channel</th><th>Active</th></tr></thead>
            <tbody>{LANGS.map((l) => (
              <tr key={l.code}>
                <td className="mono" style={{ color: "var(--text-primary)" }}>{l.code}</td>
                <td><span style={{ fontSize: "var(--text-base)" }}>{l.flag}</span> <Bi id={l.name} en={l.en} /> {!l.latin ? <span className="badge badge-default" style={{ fontSize: "0.5625rem", marginLeft: ".25rem" }}>non-Latin</span> : null}</td>
                <td>{l.tier === "official" ? <span className="badge badge-success"><span className="dot" />Official</span> : <span className="badge badge-warning"><span className="dot" /><Bi id="Eksperimental" en="Experimental" /></span>}</td>
                <td className="num">{l.voices}</td><td className="num">{l.ch}</td>
                <td><label className="switch"><input type="checkbox" defaultChecked={l.tier === "official"} /><span className="track" /><span className="thumb" /></label></td>
              </tr>
            ))}</tbody>
          </table></div></div>
        </>
      )}
    </>
  );
}
