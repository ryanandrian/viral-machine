"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, Tv, Zap, ArrowRight, MoreVertical, Check, Clock } from "lucide-react";
import "./channels.css";

// D2 Channels List — port dari design-source/Channels.html (Hybrid). Sidebar "Kanal".
// Spark = SVG area+line hand-drawn (gradient id deterministik per index). Mock deterministik (SSR-safe).
// Nol wiring Supabase. "Kelola" → /channels/[id] (D3).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Channel = { id: number; name: string; handle: string; c: string; i: string; niches: string[]; videos: number; views: string; ctr: string; subs: string; spark: number[] };
const CHANNELS: Channel[] = [
  { id: 1, name: "Misteri Samudra", handle: "@misterisamudra", c: "#1d4ed8", i: "MS", niches: ["Misteri Samudra", "Fakta Menarik"], videos: 284, views: "1.4M", ctr: "6.8%", subs: "12.4K", spark: [8, 10, 9, 14, 12, 18, 16, 22, 20, 26, 24, 30] },
  { id: 2, name: "Fakta Yang Bikin Mikir", handle: "@faktabikinmikir", c: "#047857", i: "FB", niches: ["Fakta Menarik", "Sains"], videos: 512, views: "4.2M", ctr: "9.1%", subs: "32.7K", spark: [20, 24, 22, 30, 28, 34, 40, 38, 46, 52, 49, 58] },
  { id: 3, name: "Jejak Kelam Sejarah", handle: "@jejakkelam", c: "#9f1239", i: "JS", niches: ["Sejarah Kelam", "Misteri Alam Semesta"], videos: 176, views: "820K", ctr: "5.4%", subs: "8.2K", spark: [6, 7, 6, 9, 8, 11, 10, 9, 12, 14, 13, 16] },
];

function SparkArea({ d, col, gid }: { d: number[]; col: string; gid: string }) {
  const W = 120, H = 34, max = Math.max(...d), min = Math.min(...d);
  const x = (i: number) => i * (W / (d.length - 1));
  const y = (v: number) => H - 3 - ((v - min) / ((max - min) || 1)) * (H - 8);
  const line = d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${W} ${H} L0 ${H} Z`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={34} preserveAspectRatio="none">
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={col} stopOpacity={0.3} /><stop offset="1" stopColor={col} stopOpacity={0} /></linearGradient></defs>
      <path d={area} fill={`url(#${gid})`} /><path d={line} fill="none" stroke={col} strokeWidth={1.8} />
    </svg>
  );
}

function ChannelCard({ ch }: { ch: Channel }) {
  return (
    <div className="ch-card">
      <div className="ch-card-top">
        <span className="ch-logo" style={{ background: ch.c }}>{ch.i}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="ch-name">{ch.name}</div>
          <div className="ch-handle"><span className="yt" /> {ch.handle}</div>
        </div>
        <span className="badge badge-success"><span className="dot" />Active</span>
      </div>
      <div className="niche-row">{ch.niches.map((n) => <span key={n} className="badge badge-default">{n}</span>)}</div>
      <div className="ch-chart"><SparkArea d={ch.spark} col={ch.c === "#1d4ed8" ? "#6366F1" : ch.c} gid={`chspark${ch.id}`} /><div className="muted" style={{ fontSize: "0.625rem", marginTop: 2 }}><Bi id="Views 30 hari terakhir" en="Views last 30 days" /></div></div>
      <div className="ch-stats">
        <div className="ch-stat"><div className="v">{ch.videos}</div><div className="l">Video</div></div>
        <div className="ch-stat"><div className="v">{ch.views}</div><div className="l">Views</div></div>
        <div className="ch-stat"><div className="v">{ch.ctr}</div><div className="l">CTR</div></div>
        <div className="ch-stat"><div className="v">{ch.subs}</div><div className="l">Subs</div></div>
      </div>
      <div className="ch-foot">
        <Link href={`/channels/${ch.id}`} className="btn btn-secondary btn-sm" style={{ flex: 1 }}><Bi id="Kelola" en="Manage" /> <ArrowRight size={14} /></Link>
        <button className="btn btn-ghost btn-icon btn-sm"><MoreVertical size={14} /></button>
      </div>
    </div>
  );
}

function IncompleteCard() {
  return (
    <div className="ch-card incomplete">
      <div className="ch-card-top">
        <span className="ch-logo" style={{ background: "#52525b" }}><Plus size={22} /></span>
        <div style={{ flex: 1 }}><div className="ch-name" style={{ color: "var(--text-secondary)" }}>Channel Baru</div><div className="ch-handle"><Bi id="Belum terhubung" en="Not connected" /></div></div>
        <span className="badge badge-warning"><span className="dot" />Setup</span>
      </div>
      <div className="setup-body">
        <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Selesaikan langkah untuk mengaktifkan:" en="Steps left to activate:" /></div>
        <div className="setup-steps">
          <div className="setup-step"><span className="c" style={{ background: "var(--success-soft)", color: "var(--success)" }}><Check size={11} /></span><Bi id="YouTube terhubung" en="YouTube connected" /></div>
          <div className="setup-step"><span className="c" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}><Clock size={11} /></span><Bi id="API keys belum lengkap" en="API keys incomplete" /></div>
          <div className="setup-step"><span className="c" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}><Clock size={11} /></span><Bi id="Niche & voice belum dipilih" en="Niche & voice not set" /></div>
        </div>
        <Link href="/onboarding" className="btn btn-default btn-sm" style={{ width: "100%" }}><Bi id="Lanjutkan setup" en="Continue setup" /> <ArrowRight size={14} /></Link>
      </div>
    </div>
  );
}

const FILTERS: [string, string, string][] = [["all", "Semua", "All"], ["active", "Active", "Active"], ["incomplete", "Setup belum selesai", "Setup incomplete"], ["suspended", "Suspended", "Suspended"]];

export default function ChannelsPage() {
  const [f, setF] = useState("all");
  return (
    <>
      <div className="ch-head">
        <h1>Channels</h1>
        <button className="btn btn-default"><Plus size={16} /> <Bi id="Tambah Channel" en="Add Channel" /></button>
      </div>

      <div className="quota">
        <Tv size={16} style={{ color: "var(--text-muted)" }} />
        <span><b style={{ fontWeight: 600 }}>3 dari 3</b> channel terpakai <span className="muted">(Pro plan)</span></span>
        <div className="progress bar"><span style={{ width: "100%", background: "var(--warning)" }} /></div>
        <a href="#" className="btn btn-secondary btn-sm up"><Zap size={14} /> <Bi id="Upgrade ke Scale" en="Upgrade to Scale" /></a>
      </div>

      <div className="ch-filters">
        <div className="segmented">{FILTERS.map(([k, id, en]) => <button key={k} aria-selected={f === k} onClick={() => setF(k)}><Bi id={id} en={en} /></button>)}</div>
      </div>

      <div className="ch-grid">
        {f === "suspended"
          ? <div className="muted" style={{ padding: "2rem", gridColumn: "1/-1", textAlign: "center" }}><Bi id="Tidak ada channel suspended." en="No suspended channels." /></div>
          : <>
              {(f === "all" || f === "active") && CHANNELS.map((ch) => <ChannelCard key={ch.id} ch={ch} />)}
              {(f === "all" || f === "incomplete") && <IncompleteCard />}
            </>}
      </div>
    </>
  );
}
