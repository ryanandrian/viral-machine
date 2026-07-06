"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
  duration_presets: Record<string, unknown>[];
  moods: Record<string, unknown>[];
};

// Urutan hierarki (owner 2026-07-04): PROVIDER dulu → AI Models (model = DETAIL dari provider).
const TABS: [string, string][] = [["providers", "Providers"], ["models", "AI Models"], ["music", "Music"], ["moods", "Moods"], ["voice", "Voice"], ["languages", "Languages"], ["durations", "Durasi"], ["niche", "Niche"]];

// field minimal untuk "Add" per tabel (PK + wajib)
const ADD_FIELDS: Record<string, { table: string; fields: [string, string][] }> = {
  models: { table: "ai_models", fields: [["provider_key", "Provider (induk model ini)"], ["component", "component"], ["model_key", "model_key (PK)"], ["model_id", "model_id (ID resmi di provider)"], ["display_name", "display_name"]] },
  providers: { table: "ai_providers", fields: [["provider_key", "provider_key (PK)"], ["display_name", "display_name"], ["adapter", "adapter (mis. openai_chat)"], ["auth_type", "auth_type (api_key/none)"], ["key_group", "key_group (vendor kunci — mis. openai_tts→openai)"], ["base_url", "base_url (opsional)"]] },
  voice: { table: "voice_catalog", fields: [["voice_key", "voice_key (PK — voice_id provider)"], ["provider_key", "provider_key (mis. elevenlabs)"], ["display_name", "display_name"], ["locale", "locale (mis. id-ID)"], ["language", "language (mis. Indonesian)"], ["gender", "gender (male/female)"], ["age", "age (mis. young/middle-aged)"], ["accent", "accent (opsional)"], ["use_case", "use_case (mis. narration)"], ["description", "description (opsional)"], ["default_settings", "default_settings JSON {stability,style,speed}"], ["niche_default", "niche_default (opsional)"], ["preview_url", "preview_url (URL contoh suara .mp3, opsional)"], ["delivery_wps", "delivery_wps (pace voice 1.0–4.0; kosong = ikut engine)"]] },
  languages: { table: "content_languages", fields: [["locale", "locale (PK)"], ["display_name", "display_name"], ["quality_tier", "tier (official/experimental)"], ["caption_font", "caption_font"]] },
  moods: { table: "moods", fields: [["mood_id", "mood_id (PK, huruf kecil)"], ["keywords", 'keywords JSON — kata pemicu deteksi dari NASKAH, campur ID+EN, mis. ["misterius","mysterious"]']] },
};

export default function AdminCatalogPage() {
  const [tab, setTab] = useState("providers");
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
  // PEMUTAR TUNGGAL (owner 2026-07-04, world-class): satu audio aktif; play record lain otomatis
  // stop yang sedang bunyi; klik ulang = stop; pindah tab/keluar halaman = stop.
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingKey, setPlayingKey] = useState<string | null>(null);
  const stopAudio = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    setPlayingKey(null);
  }, []);
  useEffect(() => { stopAudio(); }, [tab, stopAudio]);
  useEffect(() => () => { audioRef.current?.pause(); }, []);
  function togglePlay(key: string, url?: string | null) {
    if (!url) return;
    if (playingKey === key) { stopAudio(); return; }
    audioRef.current?.pause();
    const audio = new Audio(url);
    audio.addEventListener("ended", () => { if (audioRef.current === audio) { audioRef.current = null; setPlayingKey(null); } });
    audio.play().catch(() => { setToast("Gagal memutar"); if (audioRef.current === audio) { audioRef.current = null; setPlayingKey(null); } });
    audioRef.current = audio;
    setPlayingKey(key);
  }
  const PlayBtn = ({ k, url, emptyLabel = "—" }: { k: string; url?: string | null; emptyLabel?: string }) => (
    url
      ? <button className="btn btn-ghost btn-sm" title={playingKey === k ? "Stop" : "Putar"} onClick={() => togglePlay(k, url)}>{playingKey === k ? "⏹" : "▶"}</button>
      : <span className="muted" style={{ fontSize: "0.7rem" }}>{emptyLabel}</span>
  );

  // B2 cost-tracking: edit manual harga model (USD per satuan). Simpan manual → pricing_locked=true
  // (sinkron feed harian TIDAK menimpa). Utk model di luar feed (ElevenLabs = tergantung paket langganan).
  const [priceEdit, setPriceEdit] = useState<{ key: string; in1m: string; out1m: string; img: string; chars1m: string } | null>(null);
  async function savePricing() {
    if (!priceEdit) return;
    const num = (s: string) => (s.trim() === "" ? null : Number(s));
    const pricing = { in_per_1m: num(priceEdit.in1m), out_per_1m: num(priceEdit.out1m), per_image: num(priceEdit.img), per_1m_chars: num(priceEdit.chars1m), source: "manual", synced_at: new Date().toISOString() };
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "ai_models", key: priceEdit.key, patch: { pricing, pricing_locked: true } }) });
    if (r.ok) { setToast("Harga disimpan (terkunci dari sinkron otomatis)"); setPriceEdit(null); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
  }
  // Sanity-guard: usulan harga DITAHAN (berubah drastis dari sinkron) → admin Terapkan / Abaikan.
  async function resolvePending(key: string, pending: Record<string, unknown>, apply: boolean) {
    const patch = apply
      ? { pricing: Object.fromEntries(Object.entries(pending).filter(([k]) => k !== "reason")), pricing_pending: null }
      : { pricing_pending: null };
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "ai_models", key, patch }) });
    if (r.ok) { setToast(apply ? "Usulan harga diterapkan" : "Usulan diabaikan (harga lama dipertahankan)"); await load(); } else setToast("Gagal");
  }
  async function toggleLock(key: string, locked: boolean) {
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "ai_models", key, patch: { pricing_locked: locked } }) });
    if (r.ok) { setToast(locked ? "Harga dikunci (sinkron tak menimpa)" : "Harga dibuka (ikut sinkron harian)"); await load(); } else setToast("Gagal");
  }
  const fmtPricing = (p: Record<string, unknown> | null | undefined): string => {
    if (!p) return "";
    const parts: string[] = [];
    if (p.in_per_1m != null) parts.push(`in $${p.in_per_1m}/1M`);
    if (p.out_per_1m != null) parts.push(`out $${p.out_per_1m}/1M`);
    if (p.per_image != null) parts.push(`$${p.per_image}/img`);
    if (p.per_1m_chars != null) parts.push(`$${p.per_1m_chars}/1M chr`);
    return parts.join(" · ");
  };

  // NICHE_DNA F4: edit keyword deteksi mood (dipakai music_selector mendeteksi mood dari NASKAH —
  // wajib campur ID+EN agar naskah Indonesia terdeteksi; audit 2026-07-04: dulu EN-only = deteksi mati).
  const [kwEdit, setKwEdit] = useState<{ mood_id: string; text: string } | null>(null);
  async function saveKeywords() {
    if (!kwEdit) return;
    const keywords = kwEdit.text.split(",").map((s) => s.trim()).filter(Boolean);
    const r = await fetch("/api/admin/catalog", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ table: "moods", key: kwEdit.mood_id, patch: { keywords } }) });
    if (r.ok) { setToast("Keywords disimpan"); setKwEdit(null); await load(); } else { const j = await r.json().catch(() => ({})); setToast(`Gagal: ${j.error ?? ""}`); }
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

      {tab === "durations" && (
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Durasi & segmentasi konten" en="Duration & content segmentation" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Kendali preset (semua, termasuk nonaktif): matikan/hidupkan durasi yang ditawarkan ke tenant. Di bawahnya = acuan segmentasi persis seperti yang dilihat tenant (hanya yang aktif)." en="Preset control (all, incl. inactive): toggle which durations are offered to tenants. Below it = the segmentation reference exactly as tenants see it (active only)." /></p>
          {data && <div className="card" style={{ marginBottom: "1.25rem" }}><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th><Bi id="Detik" en="Seconds" /></th><th>Beats</th><th>render_mode</th><th><Bi id="Kegunaan" en="Use case" /></th><th>default</th><th>active</th></tr></thead>
            <tbody>{data.duration_presets.map((d) => (
              <tr key={String(d.seconds)} style={{ opacity: d.is_active ? 1 : .55 }}>
                <td className="num" style={{ fontWeight: 600 }}>{String(d.seconds)}s</td>
                <td className="num">{String(d.visual_beats)}</td>
                <td className="mono" style={{ fontSize: "var(--text-xs)" }}>{String(d.render_mode)}{d.render_mode === "ai_video" && <span className="muted" style={{ marginLeft: 6 }}><Bi id="(video-gen belum tersedia)" en="(video-gen not available yet)" /></span>}</td>
                <td className="muted" style={{ fontSize: "var(--text-xs)", maxWidth: 260 }}>{String(d.use_case ?? "")}</td>
                <td>{d.is_default ? <span className="badge badge-default">default</span> : "—"}</td>
                <td><Switch table="duration_presets" k={String(d.seconds)} on={d.is_active as boolean} /></td>
              </tr>))}</tbody>
          </table></div></div>}
          <PresetTables />
        </div>
      )}

      {loading && tab !== "durations" && <div className="card card-pad muted">Memuat…</div>}
      {!loading && data && (<>
        {tab === "providers" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Provider AI = INDUK. Model adalah detailnya — tambah model langsung dari baris provider (＋ Model)." en="AI providers = PARENT. Models are their details — add a model straight from the provider row." /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah provider" en="Add provider" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider_key</th><th>display</th><th>adapter</th><th>auth</th><th>key_group</th><th><Bi id="model" en="models" /></th><th>active</th><th></th></tr></thead>
            <tbody>{data.ai_providers.map((p) => {
              const pk = p.provider_key as string;
              const nModels = data.ai_models.filter((m) => m.provider_key === pk).length;
              return (
                <tr key={pk}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{pk}</td>
                  <td>{p.display_name as string}</td><td className="mono" style={{ fontSize: "var(--text-xs)" }}>{p.adapter as string}</td>
                  <td className="muted">{p.auth_type as string}</td>
                  <td className="mono" style={{ fontSize: "var(--text-xs)" }}>{(p.key_group as string) || pk}</td>
                  <td><span className={`badge ${nModels > 0 ? "badge-default" : "badge-warning"}`}>{nModels}</span></td>
                  <td><Switch table="ai_providers" k={pk} on={p.is_active as boolean} /></td>
                  <td><button className="btn btn-secondary btn-sm" title="Tambah model utk provider ini" onClick={() => { setTab("models"); setAdd({ provider_key: pk }); }}><Plus size={12} /> Model</button></td>
                </tr>
              );
            })}</tbody>
          </table></div></div>
        </>)}

        {tab === "models" && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Model = DETAIL dari provider (dikelompokkan per provider)." en="Models = details of a provider (grouped by provider)." /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah model" en="Add model" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>provider</th><th>model_key</th><th>component</th><th><Bi id="harga (USD, auto-sync harian)" en="pricing (USD, auto-synced daily)" /></th><th>tier</th><th>active</th></tr></thead>
            <tbody>{[...data.ai_models].sort((a, b) => String(a.provider_key).localeCompare(String(b.provider_key)) || String(a.component).localeCompare(String(b.component))).map((m, i, arr) => {
              const mk = m.model_key as string;
              const pr = m.pricing as Record<string, unknown> | null;
              return (
                <tr key={mk}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{i === 0 || arr[i - 1].provider_key !== m.provider_key ? (m.provider_key as string) : <span className="muted" style={{ opacity: .35 }}>·</span>}</td>
                  <td className="mono">{mk}</td><td><span className="badge badge-default">{m.component as string}</span></td>
                  <td style={{ maxWidth: 300 }}>
                    {priceEdit?.key === mk ? (
                      <span style={{ display: "inline-flex", gap: ".3rem", alignItems: "center", flexWrap: "wrap" }}>
                        <input className="input" style={{ height: 26, width: 70 }} placeholder="in/1M" value={priceEdit.in1m} onChange={(e) => setPriceEdit({ ...priceEdit, in1m: e.target.value })} />
                        <input className="input" style={{ height: 26, width: 70 }} placeholder="out/1M" value={priceEdit.out1m} onChange={(e) => setPriceEdit({ ...priceEdit, out1m: e.target.value })} />
                        <input className="input" style={{ height: 26, width: 70 }} placeholder="/img" value={priceEdit.img} onChange={(e) => setPriceEdit({ ...priceEdit, img: e.target.value })} />
                        <input className="input" style={{ height: 26, width: 76 }} placeholder="/1M chr" value={priceEdit.chars1m} onChange={(e) => setPriceEdit({ ...priceEdit, chars1m: e.target.value })} />
                        <button className="btn btn-default btn-sm" onClick={savePricing}>✓</button>
                        <button className="btn btn-ghost btn-sm" onClick={() => setPriceEdit(null)}>✕</button>
                      </span>
                    ) : (
                      <span style={{ display: "inline-flex", gap: ".4rem", alignItems: "center", flexWrap: "wrap" }}>
                        {pr ? <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{fmtPricing(pr)}</span>
                          : (m.is_active ? <span className="badge badge-warning" title="Model aktif tanpa harga → biaya video tampil 'belum lengkap'">⚠️ kosong</span> : <span className="muted" style={{ fontSize: "0.7rem" }}>—</span>)}
                        {m.pricing_locked ? <span title="Terkunci — sinkron otomatis tak menimpa (klik utk buka)" style={{ cursor: "pointer" }} onClick={() => toggleLock(mk, false)}>🔒</span>
                          : pr ? <span title="Ikut sinkron harian (klik utk kunci)" style={{ cursor: "pointer", opacity: .45 }} onClick={() => toggleLock(mk, true)}>🔓</span> : null}
                        <button className="btn btn-ghost btn-sm" title="Edit harga manual" onClick={() => setPriceEdit({ key: mk, in1m: String(pr?.in_per_1m ?? ""), out1m: String(pr?.out_per_1m ?? ""), img: String(pr?.per_image ?? ""), chars1m: String(pr?.per_1m_chars ?? "") })}>✎</button>
                        {(m.pricing_pending as Record<string, unknown> | null) && (
                          <span style={{ display: "inline-flex", gap: ".3rem", alignItems: "center", padding: ".15rem .4rem", borderRadius: 6, background: "var(--warning-soft)", fontSize: "0.6875rem" }} title={String((m.pricing_pending as Record<string, unknown>).reason ?? "")}>
                            ⚠️ <Bi id="usulan baru:" en="new proposal:" /> {fmtPricing(m.pricing_pending as Record<string, unknown>)}
                            <button className="btn btn-default btn-sm" style={{ height: 20, padding: "0 .4rem", fontSize: "0.625rem" }} onClick={() => resolvePending(mk, m.pricing_pending as Record<string, unknown>, true)}><Bi id="Terapkan" en="Apply" /></button>
                            <button className="btn btn-ghost btn-sm" style={{ height: 20, padding: "0 .4rem", fontSize: "0.625rem" }} onClick={() => resolvePending(mk, m.pricing_pending as Record<string, unknown>, false)}><Bi id="Abaikan" en="Dismiss" /></button>
                          </span>
                        )}
                      </span>
                    )}
                  </td>
                  <td className="muted">{m.quality_tier as string}</td>
                  <td><Switch table="ai_models" k={mk} on={m.is_active as boolean} /></td>
                </tr>
              );
            })}</tbody>
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
                  <td><button className="btn btn-ghost btn-sm" title={playingKey === `music:${t.id}` ? "Stop" : "Putar"} onClick={async () => {
                    if (playingKey === `music:${t.id}`) { stopAudio(); return; }
                    // bucket aset PRIVAT → URL publik 403; putar via presigned URL (route auth)
                    const j = await fetch(`/api/music/preview?id=${t.id}`).then((r) => r.json()).catch(() => ({}));
                    if (j.url) togglePlay(`music:${t.id}`, j.url); else setToast("Gagal memutar");
                  }}>{playingKey === `music:${t.id}` ? "⏹" : "▶"}</button></td>
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
                      <PlayBtn k={`voice:${v.voice_key}`} url={v.preview_url as string | null} emptyLabel="kosong" />
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

        {tab === "moods" && data && (<>
          <div className="cat-toolbar"><span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Mood musik + kata pemicu deteksi dari naskah (campur ID+EN). Dipakai pemilih musik & paket mood niche." en="Music moods + script detection trigger words (mix ID+EN)." /></span><div className="right"><button className="btn btn-default btn-sm" onClick={() => setAdd({})}><Plus size={14} /> <Bi id="Tambah mood" en="Add mood" /></button></div></div>
          <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl cat-tbl">
            <thead><tr><th>mood</th><th><Bi id="Track di library" en="Library tracks" /></th><th><Bi id="Kata pemicu (deteksi dari naskah)" en="Trigger words" /></th><th>Active</th><th></th></tr></thead>
            <tbody>{data.moods.map((m) => {
              const mid = m.mood_id as string;
              const kws = Array.isArray(m.keywords) ? (m.keywords as string[]) : [];
              const nTracks = data.music_library.filter((t) => t.mood === mid && t.is_active).length;
              return (
                <tr key={mid}>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{mid}</td>
                  <td>{nTracks > 0 ? <span className="badge badge-success">{nTracks}</span> : <span className="badge badge-warning">0</span>}</td>
                  <td style={{ maxWidth: 480 }}>
                    {kwEdit?.mood_id === mid ? (
                      <div style={{ display: "flex", gap: ".4rem" }}>
                        <textarea className="textarea" rows={2} style={{ flex: 1 }} value={kwEdit.text} onChange={(e) => setKwEdit({ mood_id: mid, text: e.target.value })} />
                        <button className="btn btn-default btn-sm" onClick={saveKeywords}>OK</button>
                        <button className="btn btn-ghost btn-sm" onClick={() => setKwEdit(null)}>Batal</button>
                      </div>
                    ) : (
                      <span className="muted" style={{ fontSize: "var(--text-xs)", cursor: "pointer" }} title="Klik untuk edit" onClick={() => setKwEdit({ mood_id: mid, text: kws.join(", ") })}>{kws.join(", ") || "(kosong — klik utk isi)"}</span>
                    )}
                  </td>
                  <td><Switch table="moods" k={mid} on={m.is_active as boolean} /></td>
                  <td></td>
                </tr>
              );
            })}</tbody>
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
                <div key={k}><label className="label">{label}</label>
                  {tab === "models" && k === "provider_key" ? (
                    <select className="input" value={add[k] ?? ""} onChange={(e) => setAdd({ ...add, [k]: e.target.value })}>
                      <option value="">— pilih provider —</option>
                      {(data?.ai_providers ?? []).map((p) => <option key={p.provider_key as string} value={p.provider_key as string}>{(p.display_name as string) || (p.provider_key as string)}</option>)}
                    </select>
                  ) : tab === "models" && k === "component" ? (
                    <select className="input" value={add[k] ?? ""} onChange={(e) => setAdd({ ...add, [k]: e.target.value })}>
                      <option value="">— pilih —</option>
                      {["llm", "image", "video", "tts"].map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  ) : (
                    <input className="input" value={add[k] ?? ""} onChange={(e) => setAdd({ ...add, [k]: e.target.value })} />
                  )}
                </div>
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

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "#1f2937", color: "#fff", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)", boxShadow: "0 6px 20px rgba(0,0,0,0.35)", fontSize: "var(--text-sm)" }}>{toast}</div>}
    </>
  );
}
