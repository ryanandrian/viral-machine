"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ExternalLink, Settings, Zap, ArrowRight, BarChart3, Calendar, Activity, Loader2, Check } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import PresetTables from "@/components/preset-tables";
import "./channel-detail.css";

// D3 Channel Detail — Phase 9.3 (wired Supabase v2, anon + RLS).
// Header + Settings = data NYATA (read channels by id, write via channels RLS UPDATE — tanpa kolom
// privilege jadi aman client-side, no RPC). KPI/Overview/Runs/Analytics/Schedule = placeholder JUJUR
// (timeseries di-wire 9.4 analytics; Runs nyata di D4/D5; slot-model saat D7). Niche dikelola di Config→Niches.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type ChannelRow = {
  id: string; channel_name: string | null; platform_channel_id: string | null;
  niche: string | null; niche_pool: string[] | null; niche_mode: string | null; content_language: string | null;
  is_active: boolean | null; publish_privacy: string | null; duration_preset: number | null;
};

const PALETTE = ["#6366F1", "#047857", "#9f1239", "#b45309", "#1d4ed8", "#7c3aed"];
function colorFor(id: string) { let h = 0; for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0; return PALETTE[h % PALETTE.length]; }
function initials(n: string) { const p = n.trim().split(/[\s—-]+/).filter(Boolean); return ((p[0]?.[0] ?? "C") + (p[1]?.[0] ?? "")).toUpperCase(); }

const LANGS: [string, string][] = [["id-ID", "🇮🇩 Bahasa Indonesia"], ["en-US", "🇬🇧 English"], ["ms-MY", "🇲🇾 Bahasa Malaysia"], ["fil-PH", "🇵🇭 Filipino"], ["th-TH", "🇹🇭 ภาษาไทย"], ["vi-VN", "🇻🇳 Tiếng Việt"]];
const PRIVACY: [string, string, string][] = [["private", "Privat", "Private"], ["unlisted", "Tak terdaftar", "Unlisted"], ["public", "Publik", "Public"]];
const TABS: [string, string, string][] = [["overview", "Overview", "Overview"], ["runs", "Runs", "Runs"], ["analytics", "Analytics", "Analytics"], ["schedule", "Jadwal", "Schedule"], ["settings", "Pengaturan", "Settings"]];

function Placeholder({ icon, idT, enT, href, ctaId, ctaEn }: { icon: React.ReactNode; idT: string; enT: string; href?: string; ctaId?: string; ctaEn?: string }) {
  return (
    <div className="card card-pad" style={{ textAlign: "center", padding: "3rem" }}>
      <div style={{ color: "var(--text-muted)", marginBottom: "0.75rem", display: "flex", justifyContent: "center" }}>{icon}</div>
      <p className="muted"><Bi id={idT} en={enT} /></p>
      {href && <Link href={href} className="btn btn-secondary btn-sm" style={{ marginTop: "0.75rem" }}><Bi id={ctaId!} en={ctaEn!} /> <ArrowRight size={14} /></Link>}
    </div>
  );
}

export default function ChannelDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id as string;
  const [supabase] = useState(() => createClient());
  const [ch, setCh] = useState<ChannelRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("overview");

  // form (settings)
  const [name, setName] = useState("");
  const [clang, setClang] = useState("id-ID");
  const [privacy, setPrivacy] = useState("private");
  const [active, setActive] = useState(true);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [testMsg, setTestMsg] = useState<string | null>(null);

  // C3: editor niche per-channel (fixed/random) — opsi dari ENTITLEMENT tenant; tulis via RPC.
  const [nicheMode, setNicheMode] = useState<"fixed" | "random">("fixed");
  const [niche, setNiche] = useState("");
  const [nicheOpts, setNicheOpts] = useState<{ id: string; name: string }[]>([]);
  const [nicheMsg, setNicheMsg] = useState<string | null>(null);
  const [savingNiche, setSavingNiche] = useState(false);

  // Preset durasi per-channel (channels.duration_preset) — kolom "bersih", tulis via RLS UPDATE langsung.
  const [dpreset, setDpreset] = useState<number | null>(null);
  const [savingPreset, setSavingPreset] = useState(false);
  const [presetMsg, setPresetMsg] = useState<string | null>(null);

  async function savePreset() {
    setPresetMsg(null); setSavingPreset(true);
    const { error } = await supabase.from("channels").update({ duration_preset: dpreset }).eq("id", id);
    setSavingPreset(false);
    setPresetMsg(error ? `Gagal: ${error.message}` : "Durasi tersimpan");
    if (!error) load();
  }

  async function saveNiche() {
    setNicheMsg(null); setSavingNiche(true);
    const { error } = await supabase.rpc("set_channel_niche", { p_channel_id: id, p_niche: niche, p_niche_mode: nicheMode });
    setSavingNiche(false);
    setNicheMsg(error ? (error.message.includes("entitlement") ? "Niche itu di luar paket Anda" : `Gagal: ${error.message}`) : "Niche tersimpan");
    if (!error) load();
  }

  // Test sekarang (private) — direct_job: produksi 1 dgn config channel ini, publish private (preview).
  async function testNow() {
    setTestMsg(null); setBusy(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setBusy(false); return setTestMsg("Sesi tak valid"); }
    const { error } = await supabase.from("direct_jobs").insert({
      tenant_id: user.id, channel_id: id, job_type: "test", publish_privacy: "private", requested_by: user.id,
    });
    setBusy(false);
    setTestMsg(error ? `Gagal: ${error.message}` : "Diantre — produksi 1 video (private). Pantau di Runs (Antre→Berjalan).");
  }

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    const { data } = await supabase.from("channels")
      .select("id,channel_name,platform_channel_id,niche,niche_pool,niche_mode,content_language,is_active,publish_privacy,duration_preset")
      .eq("id", id).maybeSingle();
    const c = data as ChannelRow | null;
    setCh(c);
    if (c) {
      setName(c.channel_name ?? ""); setClang(c.content_language ?? "id-ID");
      setPrivacy(c.publish_privacy ?? "private"); setActive(c.is_active ?? true);
      setNicheMode((c.niche_mode === "random" ? "random" : "fixed")); setNiche(c.niche ?? "");
      setDpreset(c.duration_preset ?? null);
    }
    // Opsi niche = ENTITLEMENT tenant (katalog per-tier + niche custom/private milik tenant).
    const { data: cfg } = await supabase.from("tenant_configs").select("plan_type").maybeSingle();
    const tier = (cfg as { plan_type?: string } | null)?.plan_type ?? "starter";
    const { data: nrows } = await supabase.from("niches").select("niche_id,name,is_base,access_type,exclusive_to").eq("is_active", true);
    const me = user?.id ?? "";
    const opts = (nrows ?? []).filter((n: { access_type: string; is_base: boolean; exclusive_to: string | null }) =>
      n.exclusive_to === me || (n.access_type === "public" && (["pro", "business"].includes(tier) || n.is_base))
    ).map((n: { niche_id: string; name: string }) => ({ id: n.niche_id, name: n.name }));
    setNicheOpts(opts);
    setLoading(false);
  }, [supabase, id]);

  useEffect(() => { load(); }, [load]);

  async function save() {
    setErr(null); setSaved(false); setBusy(true);
    const { error } = await supabase.from("channels").update({
      channel_name: name.trim() || null, content_language: clang, publish_privacy: privacy, is_active: active,
    }).eq("id", id);
    setBusy(false);
    if (error) { setErr(error.message); return; }
    setSaved(true); load();
  }

  if (loading) return <div className="muted" style={{ padding: "3rem", textAlign: "center" }}><Bi id="Memuat channel…" en="Loading channel…" /></div>;
  if (!ch) return (
    <Placeholder icon={<BarChart3 size={32} />} idT="Channel tidak ditemukan atau bukan milik Anda." enT="Channel not found or not yours." href="/channels" ctaId="Kembali ke Channels" ctaEn="Back to Channels" />
  );

  const name0 = ch.channel_name || "Channel";

  return (
    <>
      <div className="cd-header">
        <span className="cd-logo-lg" style={{ background: colorFor(ch.id) }}>{initials(name0)}</span>
        <div className="cd-h-meta">
          <h1>{name0} {ch.is_active
            ? <span className="badge badge-success" style={{ fontSize: "var(--text-xs)" }}><span className="dot" />Active</span>
            : <span className="badge badge-warning" style={{ fontSize: "var(--text-xs)" }}><span className="dot" />Paused</span>}</h1>
          {ch.platform_channel_id
            ? <a href={`https://youtube.com/channel/${ch.platform_channel_id}`} target="_blank" rel="noopener noreferrer" className="cd-yt-link"><span className="yt" /> youtube.com/channel/{ch.platform_channel_id} <ExternalLink size={13} /></a>
            : <span className="cd-yt-link muted"><span className="yt" /> <Bi id="YouTube belum terhubung" en="YouTube not connected" /></span>}
          <div className="cd-kpi-strip">
            <div className="item"><div className="v">—</div><div className="l"><Bi id="Total video" en="Total videos" /></div></div>
            <div className="item"><div className="v">—</div><div className="l">Subscribers</div></div>
            <div className="item"><div className="v">—</div><div className="l"><Bi id="Views bulan ini" en="Views this month" /></div></div>
            <div className="item"><div className="v">—</div><div className="l"><Bi id="Avg engagement" en="Avg engagement" /></div></div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-secondary" onClick={() => setTab("settings")}><Settings size={15} /> <Bi id="Pengaturan" en="Settings" /></button>
          <button className="btn btn-ai" disabled={busy} onClick={testNow} title="Produksi 1 video private untuk preview config"><Zap size={15} /> <Bi id="Test sekarang (private)" en="Test now (private)" /></button>
        </div>
        {testMsg && <div style={{ flexBasis: "100%", fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginTop: ".5rem" }}>{testMsg}</div>}
      </div>

      <div className="cd-tabs">
        {TABS.map(([k, idT, en]) => <button key={k} className={`cd-tab${tab === k ? " active" : ""}`} onClick={() => setTab(k)}><Bi id={idT} en={en} /></button>)}
      </div>

      {tab === "overview" && (
        <Placeholder icon={<Activity size={32} />} idT="Statistik performa muncul setelah channel berproduksi (views, watch-time, niche, hook)." enT="Performance stats appear once the channel starts producing (views, watch-time, niche, hooks)." href="/analytics" ctaId="Buka Analytics" ctaEn="Open Analytics" />
      )}
      {tab === "runs" && (
        <Placeholder icon={<BarChart3 size={32} />} idT="Belum ada run untuk channel ini." enT="No runs for this channel yet." href="/runs" ctaId="Lihat semua Runs" ctaEn="View all Runs" />
      )}
      {tab === "analytics" && (
        <Placeholder icon={<BarChart3 size={32} />} idT="Analytics per-channel — chart mendalam." enT="Per-channel analytics — deep charts." href="/analytics" ctaId="Buka Analytics lengkap" ctaEn="Open full Analytics" />
      )}
      {tab === "schedule" && (
        <Placeholder icon={<Calendar size={32} />} idT="Jadwal slot per-channel diatur di layar Jadwal." enT="Per-channel slots are managed in the Schedule screen." href="/schedule" ctaId="Buka Jadwal" ctaEn="Open Schedule" />
      )}

      {tab === "settings" && (
        <>
        <div className="card card-pad" style={{ maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "1rem" }}><Bi id="Pengaturan channel" en="Channel settings" /></h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div><label className="label"><Bi id="Nama channel" en="Channel name" /></label><input className="input" value={name} onChange={(e) => setName(e.target.value)} /></div>
            <div><label className="label"><Bi id="Bahasa konten" en="Content language" /></label>
              <select className="input" value={clang} onChange={(e) => setClang(e.target.value)} style={{ width: "fit-content" }}>
                {LANGS.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
              </select>
              <div style={{ marginTop: "0.625rem", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}><Bi id="Berlaku untuk video baru — video lama tidak diproduksi ulang." en="Applies to new videos only — existing videos aren't re-produced." /></div>
            </div>
            <div><label className="label"><Bi id="Privasi publish" en="Publish privacy" /></label>
              <select className="input" value={privacy} onChange={(e) => setPrivacy(e.target.value)} style={{ width: "fit-content" }}>
                {PRIVACY.map(([v, idT]) => <option key={v} value={v}>{idT}</option>)}
              </select>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "0.625rem", fontSize: "var(--text-sm)" }}>
              <span className="switch"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /><span className="track" /><span className="thumb" /></span>
              <Bi id="Channel aktif (produksi berjalan)" en="Channel active (production runs)" />
            </label>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <label className="label"><Bi id="Niche channel" en="Channel niche" /></label>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center", marginBottom: "0.5rem" }}>
                <select className="input" value={nicheMode} onChange={(e) => setNicheMode(e.target.value as "fixed" | "random")} style={{ width: "fit-content" }}>
                  <option value="fixed">Fixed — 1 niche</option>
                  <option value="random">Random — putar semua niche paket</option>
                </select>
                {nicheMode === "fixed" && (
                  <select className="input" value={niche} onChange={(e) => setNiche(e.target.value)} style={{ width: "fit-content" }}>
                    <option value="">— pilih niche —</option>
                    {nicheOpts.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
                  </select>
                )}
                <button className="btn btn-secondary btn-sm" onClick={saveNiche} disabled={savingNiche || (nicheMode === "fixed" && !niche)}>{savingNiche ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan niche" en="Save niche" />}</button>
              </div>
              <div className="muted" style={{ fontSize: "var(--text-xs)" }}>
                <Bi id="Random = putar otomatis SELURUH niche yang jadi hak paket Anda. Pilihan terbatas pada entitlement Anda." en="Random = auto-rotate ALL niches your plan entitles. Options are limited to your entitlement." />
                {" "}<Link href="/config/niches" className="link"><Bi id="Ajukan niche khusus →" en="Request custom niche →" /></Link>
              </div>
              {nicheMsg && <div style={{ fontSize: "var(--text-sm)", marginTop: "0.4rem", color: nicheMsg.includes("tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{nicheMsg}</div>}
            </div>
            {err && <div style={{ color: "var(--danger, #ef4444)", fontSize: "var(--text-sm)" }}>{err}</div>}
            {saved && <div style={{ color: "var(--success)", fontSize: "var(--text-sm)", display: "flex", alignItems: "center", gap: "0.375rem" }}><Check size={14} /> <Bi id="Tersimpan" en="Saved" /></div>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <Link href="/channels" className="btn btn-ghost"><Bi id="Batal" en="Cancel" /></Link>
              <button className="btn btn-default" onClick={save} disabled={busy}>{busy ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan" en="Save" />}</button>
            </div>
          </div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem" }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Durasi & segmentasi konten" en="Duration & content segmentation" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}>
            <Bi id="Pilih durasi video untuk channel ini. Makin panjang, makin banyak bagian cerita. Tabel di bawah menjelaskan tiap pilihan." en="Pick this channel's video duration. Longer durations add more story parts. The table below explains each option." />
          </p>
          <PresetTables selectable selectedSeconds={dpreset} onSelect={setDpreset} />
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "1rem" }}>
            <button className="btn btn-default" onClick={savePreset} disabled={savingPreset || dpreset == null}>{savingPreset ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan durasi" en="Save duration" />}</button>
            {presetMsg && <span style={{ fontSize: "var(--text-sm)", color: presetMsg.includes("tersimpan") ? "var(--success)" : "var(--danger, #ef4444)" }}>{presetMsg}</span>}
          </div>
        </div>
        </>
      )}
    </>
  );
}
