"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { fetchPricing, idrK } from "@/lib/pricing";
import { Sparkles, Music, Target, Bell, Shield, ChevronDown, Play, X, Clock, Wand2, Plus, Tv, HelpCircle, Check } from "lucide-react";
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

// ---------- panels ----------
// F2 (2026-06-24): kelola kunci AI = PER-CHANNEL (Channels → Manage). Tab "AI Engines" & "API Keys"
// (tenant-level key di tenant_configs) DIBUANG — fosil; jalur tulis (/api/keys/set) juga dihapus.

function Mood({ cols }: { cols: string[] }) {
  return <div style={{ height: 64, display: "flex" }}>{cols.map((c) => <span key={c} style={{ flex: 1, background: c }} />)}</div>;
}

function Niches() {
  const supabase = createClient();
  const [seg, setSeg] = useState(0);
  const [modal, setModal] = useState(false);
  const [pricing, setPricing] = useState<Record<string, number>>({});
  // C4: form ajukan custom niche → insert niche_requests (judul + clue/masukan tenant).
  const [reqType, setReqType] = useState<"public_90d" | "private">("public_90d");
  const [rTitle, setRTitle] = useState(""); const [rAudience, setRAudience] = useState("");
  const [rRefs, setRRefs] = useState(""); const [rAngle, setRAngle] = useState("");
  const [rBusy, setRBusy] = useState(false); const [rMsg, setRMsg] = useState<string | null>(null);
  function openReq(t: "public_90d" | "private") { setReqType(t); setRMsg(null); setModal(true); }
  async function submitReq() {
    if (!rTitle.trim()) { setRMsg("Isi ide niche dulu"); return; }
    setRBusy(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setRBusy(false); setRMsg("Sesi tak valid"); return; }
    const { error } = await supabase.from("niche_requests").insert({
      tenant_id: user.id, request_type: reqType, title: rTitle.trim(),
      clues: { audience: rAudience.trim(), references: rRefs.trim(), viral_angle: rAngle.trim() },
      price_key: reqType === "public_90d" ? "custom_niche_public_90d" : "custom_niche_private",
    });
    setRBusy(false);
    if (error) { setRMsg(`Gagal: ${error.message}`); return; }
    setRMsg("ok"); setRTitle(""); setRAudience(""); setRRefs(""); setRAngle("");
    setTimeout(() => { setModal(false); setRMsg(null); }, 1400);
  }
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
        <Bi id="Katalog & aktivasi niche dikelola tim (Admin Niches) + entitlement per-tier. Niche channel diatur di Channel Detail. Harga request custom = nyata dari pricing_config; pengajuan di bawah TERSIMPAN & diproses admin." en="Niche catalog & activation are team-managed (Admin Niches) + per-tier entitlement. Per-channel niche is set in Channel Detail. Custom-request prices are live from pricing_config; requests below are saved & processed by admin." />
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
            <button className="btn btn-default btn-sm" style={{ width: "100%" }} onClick={() => openReq("public_90d")}><Bi id="Request Public Niche" en="Request Public Niche" /></button>
          </div>
          <div className="card card-pad" style={{ borderColor: "color-mix(in srgb,var(--accent) 35%,transparent)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: ".5rem", fontWeight: 600, marginBottom: ".375rem" }}>🔒 <Bi id="Permanent Private" en="Permanent Private" /> <span className="badge badge-brand" style={{ fontSize: ".625rem" }}>Premium</span></div>
            <div className="price-dyn" style={{ fontSize: "var(--text-xl)", fontWeight: 700, color: "var(--accent)" }}>{pricing.custom_niche_private ? `Rp ${idrK(pricing.custom_niche_private)}` : "Rp 1.499K"}</div>
            <div className="muted" style={{ fontSize: "var(--text-xs)", margin: ".625rem 0 1rem" }}><Bi id="Tidak pernah public. Exclusive permanen untuk channel-mu. Positioning premium untuk agency." en="Never public. Permanently exclusive to your channel. Premium positioning for agencies." /></div>
            <button className="btn btn-ai btn-sm" style={{ width: "100%" }} onClick={() => openReq("private")}><Bi id="Request Private Niche" en="Request Private Niche" /></button>
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
            <div className="card-head"><h3 className="card-title"><Bi id="Request niche custom" en="Request custom niche" /> · {reqType === "private" ? "🔒 Private" : "🌍 Public-90d"}</h3><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal(false)}><X size={16} /></button></div>
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div><label className="label"><Bi id="Ide niche" en="Niche idea" /> *</label><textarea className="textarea" rows={2} value={rTitle} onChange={(e) => setRTitle(e.target.value)} placeholder="mis. Misteri kapal selam Perang Dunia II" /></div>
              <div><label className="label"><Bi id="Target audiens" en="Target audience" /></label><input className="input" value={rAudience} onChange={(e) => setRAudience(e.target.value)} placeholder="mis. pria 18-34, pecinta sejarah" /></div>
              <div><label className="label"><Bi id="Channel/referensi" en="Reference channels" /></label><input className="input input-mono" value={rRefs} onChange={(e) => setRRefs(e.target.value)} placeholder="youtube.com/@... , contoh gaya" /></div>
              <div><label className="label"><Bi id="Angle viral & use case" en="Viral angle & use case" /></label><textarea className="textarea" rows={2} value={rAngle} onChange={(e) => setRAngle(e.target.value)} placeholder="clue/masukan untuk tim saat membuat niche ini" /></div>
              {rMsg && <div style={{ fontSize: "var(--text-sm)", color: rMsg === "ok" ? "var(--success)" : "var(--danger,#ef4444)" }}>{rMsg === "ok" ? "✓ Request terkirim — tim akan memproses." : rMsg}</div>}
            </div>
            <div className="card-foot" style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end" }}><button className="btn btn-ghost" onClick={() => setModal(false)}><Bi id="Batal" en="Cancel" /></button><button className="btn btn-default" disabled={rBusy} onClick={submitReq}><Bi id="Kirim request" en="Submit request" /></button></div>
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

// F2-05: Voice/Visual/Music/Captions/Quality/Hashtags PINDAH ke per-channel (Channels → Manage).
// Pengaturan ini bukan lagi per-tenant. Notice + tautan (URL lama tetap informatif, nol duplikat membingungkan).
function MovedToChannel() {
  return (
    <div className="card card-pad" style={{ textAlign: "center", padding: "2.5rem", maxWidth: 560 }}>
      <div style={{ color: "var(--text-muted)", marginBottom: ".75rem", display: "flex", justifyContent: "center" }}><Tv size={30} /></div>
      <p style={{ marginBottom: ".35rem", fontWeight: 600 }}><Bi id="Pengaturan ini sekarang per-channel" en="This setting is now per-channel" /></p>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Voice, visual, musik, caption, hashtag, & quality-gate kini diatur di tiap channel (tiap channel punya brand & konfigurasi sendiri)." en="Voice, visual, music, captions, hashtags & quality gate are now set per channel (each channel has its own brand & config)." /></p>
      <a href="/channels" className="btn btn-default btn-sm"><Bi id="Buka Channels → Manage" en="Open Channels → Manage" /> <ChevronDown size={14} style={{ transform: "rotate(-90deg)" }} /></a>
    </div>
  );
}

type Panel = { title: { id: string; en: string }; desc: { id: string; en: string }; badge?: React.ReactNode; Body: () => React.ReactElement };
const PANELS: Record<string, Panel> = {
  "voice": { title: { id: "Suara", en: "Voice" }, desc: { id: "Voice difilter oleh bahasa konten channel aktif. Tetapkan voice default per niche.", en: "Voices are filtered by the active channel's content language. Set a default voice per niche." }, Body: MovedToChannel },
  "visual": { title: { id: "Visual", en: "Visual" }, desc: { id: "Pilih preset gaya visual & sesuaikan prompt per niche.", en: "Choose a visual style preset & customize prompts per niche." }, Body: MovedToChannel },
  "music": { title: { id: "Musik", en: "Music" }, desc: { id: "Library musik latar. Mesin memilih mood otomatis sesuai niche & performa.", en: "Background music library. The engine auto-selects mood by niche & performance." }, Body: MovedToChannel },
  "captions": { title: { id: "Teks", en: "Captions" }, desc: { id: "Atur gaya subtitle karaoke yang muncul di video. Preview real-time.", en: "Style the karaoke subtitles shown in your videos. Real-time preview." }, Body: MovedToChannel },
  "quality": { title: { id: "Gerbang Kualitas", en: "Quality Gate" }, badge: <span className="badge badge-brand" style={{ fontSize: ".625rem" }}>Pro+</span>, desc: { id: "Tentukan threshold skor viral, retry, dan aksi saat gagal.", en: "Set viral-score threshold, retries, and action on failure." }, Body: MovedToChannel },
  "hashtags": { title: { id: "Hashtags", en: "Hashtags" }, desc: { id: "Kelola pool hashtag per niche untuk metadata YouTube.", en: "Manage the hashtag pool per niche for YouTube metadata." }, Body: MovedToChannel },
  "niches": { title: { id: "Niches", en: "Niches" }, desc: { id: "3 dari 4 niche aktif (Pro plan). Aktifkan dari catalog atau request niche custom.", en: "3 of 4 niches active (Pro plan). Activate from catalog or request a custom niche." }, Body: Niches },
  "notifications": { title: { id: "Notifikasi", en: "Notifications" }, desc: { id: "Pilih event apa yang dikirim ke channel mana.", en: "Choose which events go to which channels." }, Body: Notifications },
};

type NavItem = { grp: { id: string; en: string } } | { id: string; Icon: typeof Sparkles; t: { id: string; en: string }; lock?: boolean };
// F2-05: Voice/Visual/Music/Captions/Quality/Hashtags DIBUANG dari nav tenant → kini per-channel
// (Channels → Manage). Sisa config tenant = item per-TENANT sejati: AI keys, Niches, Notifikasi.
const NAV: NavItem[] = [
  { grp: { id: "Konten", en: "Content" } },
  { id: "niches", Icon: Target, t: { id: "Niches", en: "Niches" } },
  { grp: { id: "Sistem", en: "System" } },
  { id: "notifications", Icon: Bell, t: { id: "Notifikasi", en: "Notifications" } },
];

export default function ConfigTabPage() {
  const params = useParams<{ tab: string }>();
  const active = (params?.tab as string) || "niches";

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
