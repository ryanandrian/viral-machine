"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ExternalLink, Settings, Zap, ArrowRight, BarChart3, Calendar, Activity, Loader2, Check } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
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
  niche: string | null; niche_pool: string[] | null; content_language: string | null;
  is_active: boolean | null; publish_privacy: string | null;
};

const PALETTE = ["#6366F1", "#047857", "#9f1239", "#b45309", "#1d4ed8", "#7c3aed"];
function colorFor(id: string) { let h = 0; for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0; return PALETTE[h % PALETTE.length]; }
function initials(n: string) { const p = n.trim().split(/[\s—-]+/).filter(Boolean); return ((p[0]?.[0] ?? "C") + (p[1]?.[0] ?? "")).toUpperCase(); }
function prettyNiche(k: string) { return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }

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

  const load = useCallback(async () => {
    const { data } = await supabase.from("channels")
      .select("id,channel_name,platform_channel_id,niche,niche_pool,content_language,is_active,publish_privacy")
      .eq("id", id).maybeSingle();
    const c = data as ChannelRow | null;
    setCh(c);
    if (c) {
      setName(c.channel_name ?? ""); setClang(c.content_language ?? "id-ID");
      setPrivacy(c.publish_privacy ?? "private"); setActive(c.is_active ?? true);
    }
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
  const niches = (ch.niche_pool?.length ? ch.niche_pool : ch.niche ? [ch.niche] : []).map(prettyNiche);

  return (
    <>
      <div className="cd-header">
        <span className="cd-logo-lg" style={{ background: colorFor(ch.id) }}>{initials(name0)}</span>
        <div className="cd-h-meta">
          <h1>{name0} {ch.is_active
            ? <span className="badge badge-success" style={{ fontSize: "var(--text-xs)" }}><span className="dot" />Active</span>
            : <span className="badge badge-warning" style={{ fontSize: "var(--text-xs)" }}><span className="dot" />Paused</span>}</h1>
          {ch.platform_channel_id
            ? <a href="#" className="cd-yt-link"><span className="yt" /> youtube.com/@{ch.platform_channel_id} <ExternalLink size={13} /></a>
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
          <button className="btn btn-ai"><Zap size={15} /> <Bi id="Jalankan" en="Run" /></button>
        </div>
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
            <div><label className="label"><Bi id="Niche aktif" en="Active niches" /></label>
              <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap", alignItems: "center" }}>
                {niches.length ? niches.map((n) => <span key={n} className="badge badge-brand">{n}</span>) : <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum ada" en="None" /></span>}
                <Link href="/config/niches" className="btn btn-secondary btn-sm"><Bi id="Kelola di Config → Niches" en="Manage in Config → Niches" /></Link>
              </div>
            </div>
            {err && <div style={{ color: "var(--danger, #ef4444)", fontSize: "var(--text-sm)" }}>{err}</div>}
            {saved && <div style={{ color: "var(--success)", fontSize: "var(--text-sm)", display: "flex", alignItems: "center", gap: "0.375rem" }}><Check size={14} /> <Bi id="Tersimpan" en="Saved" /></div>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <Link href="/channels" className="btn btn-ghost"><Bi id="Batal" en="Cancel" /></Link>
              <button className="btn btn-default" onClick={save} disabled={busy}>{busy ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan" en="Save" />}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
