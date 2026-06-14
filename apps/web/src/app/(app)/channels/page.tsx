"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Tv, Zap, ArrowRight, Pause, Play } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
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

function ChannelCard({ ch, busy, onToggle }: { ch: ChannelRow; busy: boolean; onToggle: (ch: ChannelRow) => void }) {
  const name = ch.channel_name || "Channel";
  const col = colorFor(ch.id);
  const niches = (ch.niche_pool?.length ? ch.niche_pool : ch.niche ? [ch.niche] : []).map(prettyNiche);
  const active = ch.is_active ?? false;
  return (
    <div className="ch-card">
      <div className="ch-card-top">
        <span className="ch-logo" style={{ background: col }}>{initials(name)}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="ch-name">{name}</div>
          <div className="ch-handle"><span className="yt" /> {ch.platform_channel_id ? `@${ch.platform_channel_id}` : <span className="muted"><Bi id="belum terhubung" en="not connected" /></span>}</div>
        </div>
        {active
          ? <span className="badge badge-success"><span className="dot" />Active</span>
          : <span className="badge badge-warning"><span className="dot" />Paused</span>}
      </div>
      <div className="niche-row">{niches.length ? niches.map((n) => <span key={n} className="badge badge-default">{n}</span>) : <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum ada niche" en="No niche set" /></span>}</div>
      <div className="ch-chart" style={{ display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "0.625rem" }}>
        <Bi id="Statistik 30 hari — segera" en="30-day stats — coming soon" />
      </div>
      <div className="ch-stats">
        <div className="ch-stat"><div className="v">—</div><div className="l">Video</div></div>
        <div className="ch-stat"><div className="v">—</div><div className="l">Views</div></div>
        <div className="ch-stat"><div className="v">—</div><div className="l">CTR</div></div>
        <div className="ch-stat"><div className="v">—</div><div className="l">Subs</div></div>
      </div>
      <div className="ch-foot">
        <Link href={`/channels/${ch.id}`} className="btn btn-secondary btn-sm" style={{ flex: 1 }}><Bi id="Kelola" en="Manage" /> <ArrowRight size={14} /></Link>
        <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onToggle(ch)} aria-label={active ? "Pause" : "Activate"}>
          {active ? <><Pause size={14} /> <Bi id="Jeda" en="Pause" /></> : <><Play size={14} /> <Bi id="Aktifkan" en="Activate" /></>}
        </button>
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

  const COLS = "id,channel_name,platform_channel_id,niche,niche_pool,is_active";

  const load = useCallback(async () => {
    const [{ data: chs, error: e1 }, { data: tc }] = await Promise.all([
      supabase.from("channels").select(COLS).order("created_at", { ascending: true }),
      supabase.from("tenant_configs").select("plan_type").maybeSingle(),
    ]);
    if (e1) { setErr(e1.message); setLoading(false); return; }
    setChannels((chs as ChannelRow[]) ?? []);
    const pt = (tc as { plan_type?: string } | null)?.plan_type ?? "";
    setPlan(pt);
    if (pt) {
      const { data: pl } = await supabase.from("plan_limits").select("max_channels").eq("plan_type", pt).maybeSingle();
      setMaxCh((pl as { max_channels?: number } | null)?.max_channels ?? null);
    }
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
    setBusyId(c.id);
    const next = !(c.is_active ?? false);
    setChannels((prev) => prev.map((x) => (x.id === c.id ? { ...x, is_active: next } : x))); // optimistic
    const { error } = await supabase.from("channels").update({ is_active: next }).eq("id", c.id);
    if (error) {
      setChannels((prev) => prev.map((x) => (x.id === c.id ? { ...x, is_active: !next } : x))); // revert
      setErr(error.message);
    }
    setBusyId(null);
  }

  const shown = channels.filter((c) => f === "all" || (f === "active" ? c.is_active : !c.is_active));
  const used = channels.length;

  return (
    <>
      <div className="ch-head">
        <h1>Channels</h1>
        <button className="btn btn-default"><Plus size={16} /> <Bi id="Tambah Channel" en="Add Channel" /></button>
      </div>

      {maxCh != null && (
        <div className="quota">
          <Tv size={16} style={{ color: "var(--text-muted)" }} />
          <span><b style={{ fontWeight: 600 }}>{used} dari {maxCh}</b> <Bi id="channel terpakai" en="channels used" /> <span className="muted">({PLAN_LABEL[plan] ?? plan})</span></span>
          <div className="progress bar"><span style={{ width: `${Math.min(100, maxCh ? (used / maxCh) * 100 : 0)}%`, background: used >= maxCh ? "var(--warning)" : "var(--brand)" }} /></div>
          {used >= maxCh && plan !== "business" && <a href="#" className="btn btn-secondary btn-sm up"><Zap size={14} /> <Bi id="Upgrade" en="Upgrade" /></a>}
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
              : shown.map((c) => <ChannelCard key={c.id} ch={c} busy={busyId === c.id} onToggle={toggleActive} />)}
      </div>
    </>
  );
}
