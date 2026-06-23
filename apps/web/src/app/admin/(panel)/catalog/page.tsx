"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Plus, Target, ArrowRight, X, Trash2 } from "lucide-react";
import PresetTables from "@/components/preset-tables";
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

const TABS: [string, string][] = [["models", "AI Models"], ["providers", "Providers"], ["music", "Music"], ["voice", "Voice"], ["languages", "Languages"], ["durations", "Durasi"], ["niche", "Niche"]];

// field minimal untuk "Add" per tabel (PK + wajib)
const ADD_FIELDS: Record<string, { table: string; fields: [string, string][] }> = {
  models: { table: "ai_models", fields: [["model_key", "model_key (PK)"], ["provider_key", "provider_key"], ["component", "component (llm/image/tts/video)"], ["model_id", "model_id"], ["display_name", "display_name"]] },
  providers: { table: "ai_providers", fields: [["provider_key", "provider_key (PK)"], ["display_name", "display_name"], ["adapter", "adapter (mis. openai_chat)"], ["base_url", "base_url (opsional)"]] },
  voice: { table: "voice_catalog", fields: [["voice_key", "voice_key (PK — voice_id provider)"], ["provider_key", "provider_key (mis. elevenlabs)"], ["display_name", "display_name"], ["locale", "locale (mis. id-ID)"], ["language", "language (mis. Indonesian)"], ["gender", "gender (male/female)"], ["age", "age (mis. young/middle-aged)"], ["accent", "accent (opsional)"], ["use_case", "use_case (mis. narration)"], ["description", "description (opsional)"], ["default_settings", "default_settings JSON {stability,style,speed}"], ["niche_default", "niche_default (opsional)"], ["preview_url", "preview_url (URL contoh suara .mp3, opsional)"], ["delivery_wps", "delivery_wps (pace voice 1.0–4.0; kosong = ikut engine)"]] },
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
  // F2-06: admin set contoh suara (preview_url) per voice — tenant ▶ memutarnya (nol biaya runtime).
  const [prevEdit, setPrevEdit] = useState<{ key: string; url: string } | null>(null);
  async function savePreview(key: string, url: string) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "voice_catalog", key, patch: { preview_url: url.trim() || null } }) });
    if (r.ok) { setToast("Contoh disimpan"); setPrevEdit(null); await load(); } else setToast("Gagal");
  }
  // F5-01: admin set pace PER-VOICE (voice_catalog.delivery_wps). Kosong → RESET ke NULL (ikut pace engine).
  // Server validasi rentang [1.0,4.0]. Beda level dari tts_profiles.delivery_wps (pace DASAR engine).
  const [paceEdit, setPaceEdit] = useState<{ key: string; val: string } | null>(null);
  async function savePace(key: string, val: string) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "voice_catalog", key, patch: { delivery_wps: val.trim() === "" ? null : val.trim() } }) });
    if (r.ok) { setToast(val.trim() === "" ? "Pace di-reset (ikut engine)" : "Pace voice disimpan"); setPaceEdit(null); await load(); }
    else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? r.status}`); }
  }
  // M2: CRUD musik di catalog (upload→S3, edit, delete, play). Aset = S3 (aturan owner). Durasi dibaca client-side.
  const [mUp, setMUp] = useState<{ name: string; niche: string; mood: string; bpm: string; duration_s: string; file: File | null } | null>(null);
  const [mEdit, setMEdit] = useState<{ id: string; name: string; niche: string; mood: string; bpm: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  function onMusicFile(f: File | null) {
    if (!f) { setMUp((m) => m ? { ...m, file: null } : m); return; }
    setMUp((m) => m ? { ...m, file: f } : m);
    const url = URL.createObjectURL(f);
    const au = new Audio(url);
    au.addEventListener("loadedmetadata", () => { setMUp((m) => m ? { ...m, duration_s: au.duration ? String(Math.round(au.duration)) : m.duration_s } : m); URL.revokeObjectURL(url); }, { once: true });
    au.addEventListener("error", () => URL.revokeObjectURL(url), { once: true });
  }
  async function uploadMusic() {
    if (!mUp?.file || !mUp.name.trim() || !mUp.niche.trim() || !mUp.mood.trim()) { setToast("Lengkapi file, nama, niche, mood"); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", mUp.file); fd.append("name", mUp.name.trim()); fd.append("niche", mUp.niche.trim()); fd.append("mood", mUp.mood.trim());
    if (mUp.bpm.trim()) fd.append("bpm", mUp.bpm.trim());
    if (mUp.duration_s.trim()) fd.append("duration_s", mUp.duration_s.trim());
    const r = await fetch("/api/admin/music/upload", { method: "POST", body: fd });
    setUploading(false);
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setToast("Musik diunggah ke S3"); setMUp(null); await load(); } else setToast(`Gagal: ${j.error ?? r.status}`);
  }
  async function saveMusicEdit() {
    if (!mEdit) return;
    const patch = { name: mEdit.name, niche: mEdit.niche, mood: mEdit.mood, bpm: mEdit.bpm.trim() === "" ? null : Number(mEdit.bpm) };
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "music_library", key: mEdit.id, patch }) });
    if (r.ok) { setToast("Tersimpan"); setMEdit(null); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
  }
  async function delAsset(table: string, key: string, label: string) {
    if (typeof window !== "undefined" && !window.confirm(`Hapus "${label}"? Berkas di S3 ikut dihapus.`)) return;
    const r = await fetch("/api/admin/catalog", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table, key }) });
    if (r.ok) { setToast("Dihapus"); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
  }
  function playUrl(url?: string | null) { if (url) new Audio(url).play().catch(() => setToast("Gagal memutar")); }

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

      {tab === "durations" && (
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Durasi & segmentasi konten" en="Duration & content segmentation" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Acuan segmentasi per preset (single-source: duration_presets + beat_glossary). Identik dengan yang dilihat tenant." en="Per-preset segmentation reference (single-source: duration_presets + beat_glossary). Identical to what tenants see." /></p>
          <PresetTables />
        </div>
      )}

      {loading && tab !== "durations" && <div className="card card-pad muted">Memuat…</div>}
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
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}>{data.music_library.length} tracks · S3</span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setMUp({ name: "", niche: "", mood: "", bpm: "", duration_s: "", file: null })}><Plus size={14} /> <Bi id="Tambah musik" en="Add music" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>name</th><th>niche</th><th>mood</th><th className="num">durasi</th><th className="num">bpm</th><th>putar</th><th>active</th><th></th></tr></thead>
            <tbody>
              {data.music_library.length === 0 && <tr><td colSpan={8} className="muted" style={{ padding: "1rem", textAlign: "center" }}>Belum ada musik. Unggah untuk mulai.</td></tr>}
              {data.music_library.map((t) => (mEdit && mEdit.id === t.id ? (
                <tr key={t.id as string}>
                  <td><input className="input" style={{ height: 28 }} value={mEdit.name} onChange={(e) => setMEdit({ ...mEdit, name: e.target.value })} /></td>
                  <td><input className="input" style={{ height: 28, width: 120 }} list="mus-niche-dl" value={mEdit.niche} onChange={(e) => setMEdit({ ...mEdit, niche: e.target.value })} /></td>
                  <td><input className="input" style={{ height: 28, width: 100 }} list="mus-mood-dl" value={mEdit.mood} onChange={(e) => setMEdit({ ...mEdit, mood: e.target.value })} /></td>
                  <td className="num muted">{t.duration_s ? `${t.duration_s}s` : "—"}</td>
                  <td><input className="input" style={{ height: 28, width: 56 }} value={mEdit.bpm} placeholder="bpm" onChange={(e) => setMEdit({ ...mEdit, bpm: e.target.value })} /></td>
                  <td colSpan={3}><button className="btn btn-default btn-sm" onClick={saveMusicEdit}>✓</button> <button className="btn btn-ghost btn-sm" onClick={() => setMEdit(null)}>✕</button></td>
                </tr>
              ) : (
                <tr key={t.id as string}>
                  <td style={{ color: "var(--text-primary)" }}>{t.name as string}</td><td className="muted">{t.niche as string}</td>
                  <td><span className="badge badge-default">{t.mood as string}</span></td>
                  <td className="num muted">{t.duration_s ? `${t.duration_s}s` : "—"}</td>
                  <td className="num muted">{(t.bpm as number) || "—"}</td>
                  <td>{t.public_url ? <button className="btn btn-ghost btn-sm" title="Putar" onClick={() => playUrl(t.public_url as string)}>▶</button> : <span className="muted" style={{ fontSize: "0.7rem" }}>—</span>}</td>
                  <td><Switch table="music_library" k={t.id as string} on={t.is_active as boolean} /></td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn btn-ghost btn-sm" title="Edit" onClick={() => setMEdit({ id: t.id as string, name: (t.name as string) || "", niche: (t.niche as string) || "", mood: (t.mood as string) || "", bpm: t.bpm != null ? String(t.bpm) : "" })}>✎</button>
                    <button className="btn btn-ghost btn-sm" title="Hapus" onClick={() => delAsset("music_library", t.id as string, (t.name as string) || "track")}><Trash2 size={13} /></button>
                  </td>
                </tr>
              )))}
            </tbody>
          </table></div></div>
          <datalist id="mus-niche-dl">{[...new Set(data.music_library.map((t) => t.niche as string).filter(Boolean))].map((n) => <option key={n} value={n} />)}</datalist>
          <datalist id="mus-mood-dl">{[...new Set(data.music_library.map((t) => t.mood as string).filter(Boolean))].map((m) => <option key={m} value={m} />)}</datalist>
        </>)}

        {tab === "voice" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Voice catalog + kelas TTS provider" en="Voice catalog + TTS provider classes" /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah voice" en="Add voice" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>voice_key</th><th>provider</th><th>display</th><th>locale</th><th>gender</th><th title="Pace voice (kata/detik @speed 1.0). Kosong = ikut pace DASAR engine di bawah. Override per-voice (mis. voice lebih cepat).">Pace voice</th><th>Contoh suara</th><th>active</th><th></th></tr></thead>
            <tbody>
              {data.voice_catalog.length === 0 && <tr><td colSpan={9} className="muted" style={{ padding: "1rem", textAlign: "center" }}>Belum ada voice. Tambah untuk mulai.</td></tr>}
              {data.voice_catalog.map((v) => (
                <tr key={v.voice_key as string}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{v.voice_key as string}</td><td>{v.provider_key as string}</td>
                  <td>{v.display_name as string}</td><td className="muted">{(v.locale as string) || "—"}</td><td className="muted">{(v.gender as string) || "—"}</td>
                  <td>
                    {paceEdit && paceEdit.key === v.voice_key
                      ? <span style={{ display: "inline-flex", gap: "0.25rem", alignItems: "center" }}>
                          <input className="input" style={{ height: 26, width: 58, fontSize: "0.72rem" }} value={paceEdit.val} placeholder="2.0" onChange={(e) => setPaceEdit({ key: v.voice_key as string, val: e.target.value })} />
                          <button className="btn btn-default btn-sm" title="Simpan (1.0–4.0)" onClick={() => savePace(v.voice_key as string, paceEdit.val)}>✓</button>
                          <button className="btn btn-ghost btn-sm" title="Reset ke pace engine (NULL)" onClick={() => savePace(v.voice_key as string, "")}>⟲</button>
                          <button className="btn btn-ghost btn-sm" title="Batal" onClick={() => setPaceEdit(null)}>✕</button>
                        </span>
                      : <span style={{ display: "inline-flex", gap: "0.3rem", alignItems: "center" }}>
                          {v.delivery_wps != null ? <span className="mono">{String(v.delivery_wps)}</span> : <span className="muted" style={{ fontSize: "0.7rem" }}>— ikut engine</span>}
                          <button className="btn btn-ghost btn-sm" title="Set pace voice (kosong=ikut engine)" onClick={() => setPaceEdit({ key: v.voice_key as string, val: v.delivery_wps != null ? String(v.delivery_wps) : "" })}>✎</button>
                        </span>}
                  </td>
                  <td>
                    <span style={{ display: "inline-flex", gap: "0.3rem", alignItems: "center" }}>
                      {v.preview_url ? <button className="btn btn-ghost btn-sm" title="Putar contoh" onClick={() => { new Audio(v.preview_url as string).play().catch(() => setToast("Gagal memutar")); }}>▶</button> : <span className="muted" style={{ fontSize: "0.7rem" }}>kosong</span>}
                      {prevEdit && prevEdit.key === v.voice_key
                        ? <><input className="input" style={{ height: 26, fontSize: "0.7rem", width: 150 }} value={prevEdit.url} onChange={(e) => setPrevEdit({ key: v.voice_key as string, url: e.target.value })} placeholder="https://… .mp3" /><button className="btn btn-default btn-sm" onClick={() => savePreview(v.voice_key as string, prevEdit.url)}>✓</button><button className="btn btn-ghost btn-sm" onClick={() => setPrevEdit(null)}>✕</button></>
                        : <button className="btn btn-ghost btn-sm" title="Set contoh" onClick={() => setPrevEdit({ key: v.voice_key as string, url: (v.preview_url as string) || "" })}>✎</button>}
                    </span>
                  </td>
                  <td><Switch table="voice_catalog" k={v.voice_key as string} on={v.is_active as boolean} /></td>
                  <td><button className="btn btn-ghost btn-sm" title="Hapus voice (+ contoh S3)" onClick={() => delAsset("voice_catalog", v.voice_key as string, (v.display_name as string) || (v.voice_key as string))}><Trash2 size={13} /></button></td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
          <div className="cat-toolbar" style={{ marginTop: "1.25rem" }}><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Pace DASAR & kelas per-ENGINE — fallback untuk SEMUA voice (tts_profiles). 'Pace voice' di atas menimpa ini khusus per-voice." en="Per-ENGINE base pace & class — fallback for ALL voices (tts_profiles). 'Pace voice' above overrides this per-voice." /></span></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider_key</th><th title="timed = punya timestamp per-kata (caption presisi); fast_fallback = tanpa timestamp (murah/gratis)">class</th><th className="num" title="Pace DASAR engine (kata/dtk) — fallback semua voice di engine ini">delivery_wps (engine)</th><th>active</th></tr></thead>
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
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(440px,92vw)", maxHeight: "85vh", overflowY: "auto", zIndex: 61, padding: "1.25rem" }}>
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

      {mUp && (
        <>
          <div className="cat-scrim open" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => { if (!uploading) setMUp(null); }} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(440px,92vw)", maxHeight: "85vh", overflowY: "auto", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong><Bi id="Unggah musik (→ S3)" en="Upload music (→ S3)" /></strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} disabled={uploading} onClick={() => setMUp(null)}><X size={16} /></button></div>
            <div style={{ display: "grid", gap: "0.6rem" }}>
              <div><label className="label">Berkas (.mp3, maks 25MB)</label><input className="input" type="file" accept="audio/mpeg,.mp3" onChange={(e) => onMusicFile(e.target.files?.[0] ?? null)} /></div>
              {mUp.file && <div className="muted" style={{ fontSize: "0.7rem" }}>{mUp.file.name} · {(mUp.file.size / (1024 * 1024)).toFixed(1)}MB{mUp.duration_s ? ` · ${mUp.duration_s}s` : ""}</div>}
              <div><label className="label">Nama</label><input className="input" value={mUp.name} onChange={(e) => setMUp({ ...mUp, name: e.target.value })} /></div>
              <div><label className="label">Niche</label><input className="input" list="mus-niche-dl" value={mUp.niche} onChange={(e) => setMUp({ ...mUp, niche: e.target.value })} placeholder="mis. dark_history" /></div>
              <div><label className="label">Mood</label><input className="input" list="mus-mood-dl" value={mUp.mood} onChange={(e) => setMUp({ ...mUp, mood: e.target.value })} placeholder="mis. dark" /></div>
              <div><label className="label">BPM (opsional)</label><input className="input" value={mUp.bpm} onChange={(e) => setMUp({ ...mUp, bpm: e.target.value })} /></div>
              <button className="btn btn-primary btn-sm" style={{ justifySelf: "end", marginTop: "0.25rem" }} disabled={uploading || !mUp.file} onClick={uploadMusic}>{uploading ? "Mengunggah…" : "Unggah ke S3"}</button>
            </div>
          </div>
        </>
      )}

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "var(--surface-raised, #1f2937)", color: "var(--text-primary)", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid var(--border)" }}>{toast}</div>}
    </>
  );
}
