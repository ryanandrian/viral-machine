"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { Plus, Tv, Zap, ArrowRight, Pause, Play, Shuffle, AlertTriangle } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { effectiveStatus, ChannelStatusBadge, type Eff } from "@/lib/channel-status";
import ConfirmDialog from "@/components/confirm-dialog";
import { PageHeader } from "@/components/page-header";
import "./channels.css";

// D2 Channels List — Phase 9.2 VERTICAL SLICE (wired ke Supabase v2, anon + RLS).
// Membuktikan pola stack untuk fan-out 28 layar: READ (RLS) + WRITE (toggle is_active,
// optimistic) + REALTIME (subscribe perubahan `channels`, tenant-scoped via RLS).
// Stats per-channel (views/CTR/subs/spark) BELUM ada sumber real → placeholder "—"
// (video historis ryan channel_id=null; analytics timeseries di-wire fase 9.4). Jujur, bukan mock.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

// ── row DB (RLS: tenant_id = auth.uid()) → bentuk kartu
type ChannelRow = {
  id: string;
  channel_name: string | null;
  platform_channel_id: string | null;
  niche: string | null;
  niche_pool: string[] | null;
  is_active: boolean | null;
  production_paused: boolean | null;
  production_paused_reason: string | null;
  subscriber_count: number | null;
};

const PALETTE = ["#6366F1", "#047857", "#9f1239", "#b45309", "#1d4ed8", "#7c3aed"];
function colorFor(id: string) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}
function initials(name: string) {
  const parts = name.trim().split(/[\s—-]+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "C") + (parts[1]?.[0] ?? "")).toUpperCase();
}
function prettyNiche(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const PLAN_LABEL: Record<string, string> = { trial: "Trial", starter: "Starter", pro: "Pro", business: "Business" };

// Card daftar — status-first (badge bersama), sinyal NYATA (Video terbit), aksi sesuai status, handle benar.
const fmtK = (n: number) => n >= 1_000_000 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

function ChannelCard({ ch, eff, vid, ana, busy, onToggle }: { ch: ChannelRow; eff: Eff; vid: number; ana?: { total_views: number; avg_engagement: number | null }; busy: boolean; onToggle: (ch: ChannelRow) => void }) {
  const name = ch.channel_name || "Channel";
  const col = colorFor(ch.id);
  const niches = (ch.niche_pool?.length ? ch.niche_pool : ch.niche ? [ch.niche] : []).map(prettyNiche);
  return (
    <div className="ch-card">
      <div className="ch-card-top">
        <span className="ch-logo" style={{ background: col }}>{initials(name)}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="ch-name">{name}</div>
          <div className="ch-handle"><span className="yt" /> {ch.platform_channel_id
            ? <a href={`https://youtube.com/channel/${ch.platform_channel_id}`} target="_blank" rel="noopener noreferrer" style={{ color: "inherit" }}>youtube.com/channel/{ch.platform_channel_id.slice(0, 12)}…</a>
            : <span className="muted"><Bi id="belum terhubung" en="not connected" /></span>}</div>
        </div>
        <ChannelStatusBadge eff={eff} />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", padding: "0 1.25rem 0.4rem" }}>
        <span className="muted" style={{ fontSize: "var(--text-xs)", fontWeight: 500 }}><Bi id="Menggunakan Niche" en="Used Niche" /></span>
        {niches.length > 1 && <span className="badge" style={{ gap: "0.25rem" }}><Shuffle size={11} /> <Bi id="acak" en="random" /></span>}
      </div>
      <div className="niche-row">{niches.length
        ? (niches.length > 4 ? [...niches.slice(0, 4), `+${niches.length - 4}`] : niches).map((n) => <span key={n} className="badge badge-default">{n}</span>)
        : <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum ada niche" en="No niche set" /></span>}</div>
      {eff.reason && <div style={{ display: "flex", gap: 8, alignItems: "flex-start", background: "var(--warning-soft)",
        border: "1px solid color-mix(in srgb,var(--warning) 35%,transparent)", borderRadius: "var(--r-md)",
        padding: "0.5rem 0.625rem", margin: "0.125rem 1.25rem 0.625rem", fontSize: "var(--text-xs)",
        color: "var(--text-primary)", lineHeight: 1.55, fontWeight: 500 }}>
        <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1, color: "var(--warning)" }} /><span>{eff.reason}</span></div>}
      <div className="ch-stats">
        <div className="ch-stat"><div className="v">{vid.toLocaleString("id-ID")}</div><div className="l"><Bi id="Video terbit" en="Published" /></div></div>
        <div className="ch-stat"><div className="v">{ch.subscriber_count != null ? fmtK(ch.subscriber_count) : "—"}</div><div className="l">Subscribers</div></div>
        <div className="ch-stat"><div className="v">{ana?.total_views != null ? fmtK(ana.total_views) : "—"}</div><div className="l"><Bi id="Total Views" en="Total Views" /></div></div>
        <div className="ch-stat"><div className="v">{ana?.avg_engagement != null ? `${ana.avg_engagement}%` : "—"}</div><div className="l"><Bi id="Engagement" en="Engagement" /></div></div>
      </div>
      <div className="ch-foot">
        <Link href={`/channels/${ch.id}`} className="btn btn-secondary btn-sm" style={{ flex: 1 }}><Bi id="Kelola" en="Manage" /> <ArrowRight size={14} /></Link>
        {eff.key === "active" && <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onToggle(ch)} aria-label="Pause"><Pause size={14} /> <Bi id="Jeda" en="Pause" /></button>}
        {eff.key === "paused" && <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onToggle(ch)} aria-label="Activate"><Play size={14} /> <Bi id="Aktifkan" en="Activate" /></button>}
        {eff.key === "incomplete" && <Link href={`/channels/${ch.id}`} className="btn btn-ghost btn-sm"><Bi id="Lengkapi" en="Complete" /></Link>}
        {eff.key === "halted" && <Link href={`/channels/${ch.id}`} className="btn btn-ghost btn-sm"><Bi id="Pulihkan" en="Recover" /></Link>}
      </div>
    </div>
  );
}

function IncompleteCard() {
  return (
    <div className="ch-card incomplete">
      <div className="ch-card-top">
        <span className="ch-logo" style={{ background: "#52525b" }}><Plus size={22} /></span>
        <div style={{ flex: 1 }}><div className="ch-name" style={{ color: "var(--text-secondary)" }}><Bi id="Channel Baru" en="New Channel" /></div><div className="ch-handle"><Bi id="Belum terhubung" en="Not connected" /></div></div>
        <span className="badge badge-warning"><span className="dot" />Setup</span>
      </div>
      <div className="setup-body">
        <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Selesaikan setup channel pertama Anda." en="Finish setting up your first channel." /></div>
        <Link href="/onboarding" className="btn btn-default btn-sm" style={{ width: "100%" }}><Bi id="Lanjutkan setup" en="Continue setup" /> <ArrowRight size={14} /></Link>
      </div>
    </div>
  );
}

const FILTERS: [string, string, string][] = [["all", "Semua", "All"], ["active", "Active", "Active"], ["paused", "Paused", "Paused"]];

export default function ChannelsPage() {
  const [supabase] = useState(() => createClient());
  const [channels, setChannels] = useState<ChannelRow[]>([]);
  const [plan, setPlan] = useState<string>("");
  const [maxCh, setMaxCh] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [f, setF] = useState("all");
  const [sub, setSub] = useState<string | null>(null);
  const [rdMap, setRdMap] = useState<Record<string, { ready: boolean; missing: string[] }>>({});
  const [vidCount, setVidCount] = useState<Record<string, number>>({});
  const [anaMap, setAnaMap] = useState<Record<string, { total_views: number; avg_engagement: number | null }>>({});  // resume per-channel (RPC get_channel_analytics)
  const [confirmCfg, setConfirmCfg] = useState<null | { title: ReactNode; message: ReactNode; confirmLabel: ReactNode; onConfirm: () => void }>(null);

  const COLS = "id,channel_name,platform_channel_id,niche,niche_pool,is_active,production_paused,production_paused_reason,subscriber_count";

  const load = useCallback(async () => {
    const [{ data: chs, error: e1 }, { data: tc }] = await Promise.all([
      supabase.from("channels").select(COLS).order("created_at", { ascending: true }),
      supabase.from("tenant_configs").select("plan_type,subscription_status").maybeSingle(),
    ]);
    if (e1) { setErr(e1.message); setLoading(false); return; }
    const rows = (chs as ChannelRow[]) ?? [];
    setChannels(rows);
    setSub((tc as { subscription_status?: string } | null)?.subscription_status ?? null);
    const pt = (tc as { plan_type?: string } | null)?.plan_type ?? "";
    setPlan(pt);
    if (pt) {
      const { data: pl } = await supabase.from("plan_limits").select("max_channels").eq("plan_type", pt).maybeSingle();
      setMaxCh((pl as { max_channels?: number } | null)?.max_channels ?? null);
    }
    // Kesiapan + resume analytics per channel (RPC) — Video NYATA (videos published) di bawah.
    const rd: Record<string, { ready: boolean; missing: string[] }> = {};
    const am: Record<string, { total_views: number; avg_engagement: number | null }> = {};
    await Promise.all(rows.map(async (c) => {
      try { const { data } = await supabase.rpc("channel_readiness", { p_channel_id: c.id }); if (data) rd[c.id] = data as { ready: boolean; missing: string[] }; } catch { /* non-fatal */ }
      try {
        const { data: ca } = await supabase.rpc("get_channel_analytics", { p_channel_id: c.id });
        const a = (Array.isArray(ca) ? ca[0] : ca) as { total_views: number; avg_engagement: number | null } | null;
        if (a) am[c.id] = { total_views: a.total_views, avg_engagement: a.avg_engagement };
      } catch { /* non-fatal */ }
    }));
    setRdMap(rd);
    setAnaMap(am);
    // Hitung-pasti server-side per channel (count=exact head) — kebal cap 1000 baris berapa pun jumlah video (audit 2026-07-11).
    const vc: Record<string, number> = {};
    await Promise.all(rows.map(async (c) => {
      const { count: nv } = await supabase.from("videos").select("id", { count: "exact", head: true }).eq("channel_id", c.id).eq("status", "published");
      vc[c.id] = nv ?? 0;
    }));
    setVidCount(vc);
    setLoading(false);
  }, [supabase]);

  useEffect(() => {
    load();
    // REALTIME: perubahan row channels (RLS men-scope ke tenant ini) → re-sync.
    const ch = supabase
      .channel("rt-channels")
      .on("postgres_changes", { event: "*", schema: "public", table: "channels" }, () => { load(); })
      .subscribe();
    return () => { supabase.removeChannel(ch); };
  }, [supabase, load]);

  async function toggleActive(c: ChannelRow) {
    const next = !(c.is_active ?? false);
    // Gerbang: aktivasi HANYA bila kesiapan terbaca DAN ready → pesan RAMAH (bukan error DB mentah).
    if (next) {
      const rd = rdMap[c.id];
      if (!rd || !rd.ready) { setErr(`"${c.channel_name || "Channel"}" belum bisa diaktifkan — lengkapi: ${rd?.missing?.join(", ") || "konfigurasi & kredensial"} (buka Kelola).`); return; }
    }
    setBusyId(c.id); setErr(null);
    setChannels((prev) => prev.map((x) => (x.id === c.id ? { ...x, is_active: next } : x))); // optimistic
    const { error } = await supabase.from("channels").update({ is_active: next }).eq("id", c.id);
    if (error) {
      setChannels((prev) => prev.map((x) => (x.id === c.id ? { ...x, is_active: !next } : x))); // revert
      setErr(/channel|gate|missing|aktif/i.test(error.message) ? "Belum bisa diaktifkan — lengkapi konfigurasi & kredensial dulu (buka Kelola)." : error.message);
    }
    setBusyId(null);
  }

  // Pause = konfirmasi (cegah hentikan produksi tak sengaja). Resume = langsung (sudah ada gerbang readiness).
  function askToggle(c: ChannelRow) {
    if (!c.is_active) { toggleActive(c); return; }
    setConfirmCfg({
      title: <Bi id="Jeda produksi channel ini?" en="Pause this channel's production?" />,
      message: <Bi id="Produksi video baru akan berhenti sampai Anda aktifkan lagi. Tidak memakai kredit, bisa dilanjutkan kapan saja." en="New video production will stop until you resume. It uses no credit and can be resumed anytime." />,
      confirmLabel: <Bi id="Ya, jeda" en="Yes, pause" />,
      onConfirm: () => { setConfirmCfg(null); toggleActive(c); },
    });
  }

  const shown = channels.filter((c) => f === "all" || (f === "active" ? c.is_active : !c.is_active));
  const used = channels.length;

  return (
    <>
      <PageHeader helpSlug="membuat-channel" icon={Tv} title="Channels" action={<a href="/channels/new" className="btn btn-default"><Plus size={16} /> <Bi id="Tambah Channel" en="Add Channel" /></a>} />

      {maxCh != null && (
        <div className="quota">
          <Tv size={16} style={{ color: "var(--text-muted)" }} />
          <span><b style={{ fontWeight: 600 }}>{used} dari {maxCh}</b> <Bi id="channel terpakai" en="channels used" /> <span className="muted">({PLAN_LABEL[plan] ?? plan})</span></span>
          <div className="progress bar"><span style={{ width: `${Math.min(100, maxCh ? (used / maxCh) * 100 : 0)}%`, background: used >= maxCh ? "var(--warning)" : "var(--brand)" }} /></div>
          {used >= maxCh && plan !== "business" && <a href="/billing" className="btn btn-secondary btn-sm up"><Zap size={14} /> <Bi id="Upgrade" en="Upgrade" /></a>}
        </div>
      )}

      {err && <div style={{ color: "var(--danger, #ef4444)", fontSize: "var(--text-sm)", marginBottom: "1rem" }}>{err}</div>}

      <div className="ch-filters">
        <div className="segmented">{FILTERS.map(([k, id, en]) => <button key={k} aria-selected={f === k} onClick={() => setF(k)}><Bi id={id} en={en} /></button>)}</div>
      </div>

      <div className="ch-grid">
        {loading
          ? <div className="muted" style={{ padding: "2rem", gridColumn: "1/-1", textAlign: "center" }}><Bi id="Memuat channel…" en="Loading channels…" /></div>
          : channels.length === 0
            ? <IncompleteCard />
            : shown.length === 0
              ? <div className="muted" style={{ padding: "2rem", gridColumn: "1/-1", textAlign: "center" }}><Bi id="Tidak ada channel pada filter ini." en="No channels in this filter." /></div>
              : shown.map((c) => <ChannelCard key={c.id} ch={c} eff={effectiveStatus(c, sub, rdMap[c.id] ?? null)} vid={vidCount[c.id] ?? 0} ana={anaMap[c.id]} busy={busyId === c.id} onToggle={askToggle} />)}
      </div>

      <ConfirmDialog
        open={!!confirmCfg}
        title={confirmCfg?.title}
        message={confirmCfg?.message}
        confirmLabel={confirmCfg?.confirmLabel}
        confirmClass="btn-default"
        busy={!!busyId}
        onConfirm={() => confirmCfg?.onConfirm()}
        onCancel={() => setConfirmCfg(null)}
      />
    </>
  );
}
