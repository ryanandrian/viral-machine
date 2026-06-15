"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Plus, Target, ArrowRight, X } from "lucide-react";
import "./catalog.css";

// E2 Admin Catalog (Phase 10.4-10.7) — DATA NYATA via /api/admin/catalog (service_role).
// Tab: AI Models · Providers · Music · Voice · Languages · Niche(link). Toggle active + add (whitelisted). Prefix cat-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Cat = {
  ai_models: Record<string, unknown>[]; ai_providers: Record<string, unknown>[]; music_library: Record<string, unknown>[];
  content_languages: Record<string, unknown>[]; voice_catalog: Record<string, unknown>[]; tts_profiles: Record<string, unknown>[];
};

const TABS: [string, string][] = [["models", "AI Models"], ["providers", "Providers"], ["music", "Music"], ["voice", "Voice"], ["languages", "Languages"], ["niche", "Niche"]];

// field minimal untuk "Add" per tabel (PK + wajib)
const ADD_FIELDS: Record<string, { table: string; fields: [string, string][] }> = {
  models: { table: "ai_models", fields: [["model_key", "model_key (PK)"], ["provider_key", "provider_key"], ["component", "component (llm/image/tts/video)"], ["model_id", "model_id"], ["display_name", "display_name"]] },
  providers: { table: "ai_providers", fields: [["provider_key", "provider_key (PK)"], ["display_name", "display_name"], ["adapter", "adapter (mis. openai_chat)"], ["base_url", "base_url (opsional)"]] },
  voice: { table: "voice_catalog", fields: [["voice_key", "voice_key (PK)"], ["provider_key", "provider_key"], ["display_name", "display_name"], ["locale", "locale (mis. id-ID)"], ["niche_default", "niche_default (opsional)"]] },
  languages: { table: "content_languages", fields: [["locale", "locale (PK)"], ["display_name", "display_name"], ["quality_tier", "tier (official/experimental)"], ["caption_font", "caption_font"]] },
};

export default function AdminCatalogPage() {
  const [tab, setTab] = useState("models");
  const [data, setData] = useState<Cat | null>(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [add, setAdd] = useState<Record<string, string> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await fetch("/api/admin/catalog");
    if (r.ok) setData(await r.json());
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2200); return () => clearTimeout(t); }, [toast]);

  async function toggle(table: string, key: string, value: boolean) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table, key, patch: { is_active: value } }) });
    if (r.ok) { setToast("Tersimpan"); await load(); } else setToast("Gagal");
  }
  async function createRow() {
    if (!add) return;
    const def = ADD_FIELDS[tab];
    const r = await fetch("/api/admin/catalog", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: def.table, row: add }) });
    if (r.ok) { setToast("Ditambah"); setAdd(null); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? r.status}`); }
  }

  const Switch = ({ table, k, on }: { table: string; k: string; on: boolean }) => (
    <label className="switch"><input type="checkbox" checked={on} onChange={(e) => toggle(table, k, e.target.checked)} /><span className="track" /><span className="thumb" /></label>
  );

  return (
    <>
      <div style={{ marginBottom: "1.25rem" }}><h1 style={{ fontSize: "var(--text-3xl)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 0.25rem" }}>Catalog</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Kelola model/provider AI, musik, voice, bahasa" en="Manage AI models/providers, music, voice, languages" /></div></div>

      <div className="cat-tabs">{TABS.map(([k, l]) => <button key={k} className={`cat-tab${tab === k ? " active" : ""}`} onClick={() => setTab(k)}>{l}</button>)}</div>

      {loading && <div className="card card-pad muted">Memuat…</div>}
      {!loading && data && (<>
        {tab === "models" && (<>
          <div className="cat-toolbar"><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah model" en="Add model" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>model_key</th><th>provider</th><th>component</th><th>model_id</th><th>tier</th><th>active</th></tr></thead>
            <tbody>{data.ai_models.map((m) => (
              <tr key={m.model_key as string}>
                <td className="mono" style={{ color: "var(--text-primary)" }}>{m.model_key as string}</td>
                <td>{m.provider_key as string}</td><td><span className="badge badge-default">{m.component as string}</span></td>
                <td className="mono" style={{ fontSize: "var(--text-xs)" }}>{m.model_id as string}</td><td className="muted">{m.quality_tier as string}</td>
                <td><Switch table="ai_models" k={m.model_key as string} on={m.is_active as boolean} /></td>
              </tr>
            ))}</tbody>
          </table></div></div>
        </>)}

        {tab === "providers" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Provider AI (adapter protokol). Tambah vendor sejenis = 1 baris." en="AI providers (protocol adapters)." /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah provider" en="Add provider" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider_key</th><th>display</th><th>adapter</th><th>base_url</th><th>auth</th><th>active</th></tr></thead>
            <tbody>{data.ai_providers.map((p) => (
              <tr key={p.provider_key as string}>
                <td className="mono" style={{ color: "var(--text-primary)" }}>{p.provider_key as string}</td>
                <td>{p.display_name as string}</td><td className="mono" style={{ fontSize: "var(--text-xs)" }}>{p.adapter as string}</td>
                <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{(p.base_url as string) || "—"}</td><td className="muted">{p.auth_type as string}</td>
                <td><Switch table="ai_providers" k={p.provider_key as string} on={p.is_active as boolean} /></td>
              </tr>
            ))}</tbody>
          </table></div></div>
        </>)}

        {tab === "music" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}>{data.music_library.length} tracks</span><div className="right"><span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Bulk-upload via worker/seed (R2) — bukan dari browser" en="Bulk-upload via worker/seed (R2)" /></span></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>name</th><th>niche</th><th>mood</th><th>source</th><th className="num">durasi</th><th>active</th></tr></thead>
            <tbody>{data.music_library.map((t) => (
              <tr key={t.id as string}>
                <td style={{ color: "var(--text-primary)" }}>{t.name as string}</td><td className="muted">{t.niche as string}</td>
                <td><span className="badge badge-default">{t.mood as string}</span></td><td className="muted" style={{ fontSize: "var(--text-xs)" }}>{(t.source as string) || "—"}</td>
                <td className="num muted">{t.duration_s ? `${t.duration_s}s` : "—"}</td>
                <td><Switch table="music_library" k={t.id as string} on={t.is_active as boolean} /></td>
              </tr>
            ))}</tbody>
          </table></div></div>
        </>)}

        {tab === "voice" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Voice catalog + kelas TTS provider" en="Voice catalog + TTS provider classes" /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah voice" en="Add voice" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>voice_key</th><th>provider</th><th>display</th><th>locale</th><th>niche default</th><th>active</th></tr></thead>
            <tbody>
              {data.voice_catalog.length === 0 && <tr><td colSpan={6} className="muted" style={{ padding: "1rem", textAlign: "center" }}>Belum ada voice. Tambah untuk mulai.</td></tr>}
              {data.voice_catalog.map((v) => (
                <tr key={v.voice_key as string}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{v.voice_key as string}</td><td>{v.provider_key as string}</td>
                  <td>{v.display_name as string}</td><td className="muted">{(v.locale as string) || "—"}</td><td className="muted">{(v.niche_default as string) || "—"}</td>
                  <td><Switch table="voice_catalog" k={v.voice_key as string} on={v.is_active as boolean} /></td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
          <div className="cat-toolbar" style={{ marginTop: "1rem" }}><span className="muted" style={{ fontSize: "var(--text-sm)" }}>Kelas TTS provider (tts_profiles)</span></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider_key</th><th>class</th><th className="num">delivery_wps</th><th>active</th></tr></thead>
            <tbody>{data.tts_profiles.map((p) => (
              <tr key={p.provider_key as string}><td className="mono">{p.provider_key as string}</td><td>{p.tts_class as string}</td><td className="num">{String(p.delivery_wps)}</td><td><Switch table="tts_profiles" k={p.provider_key as string} on={p.is_active as boolean} /></td></tr>
            ))}</tbody>
          </table></div></div>
        </>)}

        {tab === "languages" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Bahasa konten — dikelola admin, dibaca per-channel" en="Content languages — admin-managed" /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah bahasa" en="Add language" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>locale</th><th><Bi id="Bahasa" en="Language" /></th><th>Tier</th><th>font</th><th>Active</th></tr></thead>
            <tbody>{data.content_languages.map((l) => (
              <tr key={l.locale as string}>
                <td className="mono" style={{ color: "var(--text-primary)" }}>{l.locale as string}</td><td>{l.display_name as string}</td>
                <td>{l.quality_tier === "official" ? <span className="badge badge-success"><span className="dot" />Official</span> : <span className="badge badge-warning"><span className="dot" />Experimental</span>}</td>
                <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{(l.caption_font as string) || "—"}</td>
                <td><Switch table="content_languages" k={l.locale as string} on={l.is_active as boolean} /></td>
              </tr>
            ))}</tbody>
          </table></div></div>
        </>)}

        {tab === "niche" && (
          <div className="card card-pad" style={{ textAlign: "center", padding: "3rem" }}>
            <div style={{ color: "var(--text-muted)", marginBottom: "0.75rem", display: "flex", justifyContent: "center" }}><Target size={32} /></div>
            <p className="muted" style={{ marginBottom: "1rem" }}><Bi id="Niche library punya halaman khusus (drawer, exclusivity, release)." en="Niche library has a dedicated page." /></p>
            <Link href="/admin/niches" className="btn btn-default btn-sm"><Bi id="Buka Niche Library" en="Open Niche Library" /> <ArrowRight size={14} /></Link>
          </div>
        )}
      </>)}

      {add && ADD_FIELDS[tab] && (
        <>
          <div className="cat-scrim open" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => setAdd(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(440px,92vw)", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong>Tambah {ADD_FIELDS[tab].table}</strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setAdd(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.5rem" }}>
              {ADD_FIELDS[tab].fields.map(([k, label]) => (
                <div key={k}><label className="label">{label}</label><input className="input" value={add[k] ?? ""} onChange={(e) => setAdd({ ...add, [k]: e.target.value })} /></div>
              ))}
              <button className="btn btn-primary btn-sm" style={{ justifySelf: "end", marginTop: "0.25rem" }} onClick={createRow}>Simpan</button>
            </div>
          </div>
        </>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "var(--surface-raised, #1f2937)", color: "var(--text-primary)", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid var(--border)" }}>{toast}</div>}
    </>
  );
}
