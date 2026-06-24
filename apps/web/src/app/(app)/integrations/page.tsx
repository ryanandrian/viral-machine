"use client";

import { useCallback, useEffect, useState } from "react";
import { Video, Send, Check, Loader2, ShieldCheck, Image as ImageIcon, KeyRound } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// F2-08 — Integrasi/Koneksi platform = TENANT-level (MAIN), §3.18/§10.F.
// Satu koneksi dipakai SEMUA channel (channel hanya pilih target id). Multi-platform:
// YouTube (semua) · Telegram (notif) · Instagram (Pro+) · TikTok (Business) — gated.
// YouTube OAuth tenant-level: /api/youtube/connect TANPA channel_id → tenant_credentials.
// NON-BREAKING: channel_credentials per-channel lama tetap di-resolve publisher (fallback).
// Hanya kelas GLOBAL (components.css) + inline — TANPA css scoped halaman lain.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
function Saved({ on }: { on: boolean }) { return on ? <span style={{ color: "var(--success)", fontSize: "var(--text-xs)", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}><Check size={13} /> <Bi id="Tersimpan" en="Saved" /></span> : null; }

const PLAN_RANK: Record<string, number> = { trial: 0, starter: 1, pro: 2, business: 3, scale: 3, enterprise: 4 };
const muted: React.CSSProperties = { fontSize: "var(--text-sm)", color: "var(--text-secondary)" };
const titleS: React.CSSProperties = { fontWeight: 600, color: "var(--text-primary)" };
const iconBox = (bg: string): React.CSSProperties => ({ width: 36, height: 36, borderRadius: "var(--r-md)", background: bg, display: "grid", placeItems: "center", color: "#fff", flex: "none" });

export default function IntegrationsPage() {
  const [supabase] = useState(() => createClient());
  const [plan, setPlan] = useState("starter");
  const [busy, setBusy] = useState("");
  const [saved, setSaved] = useState("");
  const [err, setErr] = useState<{ k: string; m: string } | null>(null);

  type YtStatus = { connected: boolean; has_client: boolean; channel_id: string | null; degraded?: boolean };
  const [yt, setYt] = useState<YtStatus | null>(null);
  const [ytCid, setYtCid] = useState(""); const [ytSecret, setYtSecret] = useState("");
  const [ytMsg, setYtMsg] = useState<string | null>(null);
  const YT_REDIRECT = process.env.NEXT_PUBLIC_YT_REDIRECT_URI || "(lihat dokumentasi)";

  const [tgChat, setTgChat] = useState(""); const [tgEnabled, setTgEnabled] = useState(false);

  // Kunci AI (POOL tenant_ai_accounts) per penyedia — validate-early
  const [aiProvs, setAiProvs] = useState<{ key: string; name: string; auth: string; uses: string[] }[]>([]);
  const [aiStatus, setAiStatus] = useState<Record<string, string>>({});  // provider_key → valid|invalid|unchecked
  const [aiKey, setAiKey] = useState<Record<string, string>>({});

  const loadYt = useCallback(async () => {
    try { const r = await fetch("/api/youtube/status"); if (r.ok) setYt(await r.json()); } catch { /* abaikan */ }
  }, []);
  const load = useCallback(async () => {
    const { data } = await supabase.from("tenant_configs").select("plan_type,telegram_chat_id,telegram_enabled").maybeSingle();
    const t = data as { plan_type?: string; telegram_chat_id?: string; telegram_enabled?: boolean } | null;
    setPlan(t?.plan_type ?? "starter"); setTgChat(t?.telegram_chat_id ?? ""); setTgEnabled(!!t?.telegram_enabled);
    // Penyedia AI dari katalog (yang punya model aktif) + status kunci tenant (pool)
    const { data: am } = await supabase.from("ai_models").select("provider_key,component").eq("is_active", true);
    const { data: ap } = await supabase.from("ai_providers").select("provider_key,display_name,auth_type").eq("is_active", true);
    const byProv: Record<string, Set<string>> = {};
    ((am ?? []) as { provider_key: string; component: string }[]).forEach((m) => { (byProv[m.provider_key] ??= new Set()).add(m.component); });
    const CL: Record<string, string> = { llm: "Penulis Naskah", tts: "Pengisi Suara", image: "Pembuat Visual", video: "Pembuat Visual" };
    setAiProvs(((ap ?? []) as { provider_key: string; display_name: string; auth_type: string }[])
      .filter((p) => byProv[p.provider_key])
      .map((p) => ({ key: p.provider_key, name: p.display_name, auth: p.auth_type, uses: [...new Set([...byProv[p.provider_key]].map((c) => CL[c] || c))] })));
    try {
      const r = await fetch("/api/credentials/ai");
      if (r.ok) { const j = await r.json(); const st: Record<string, string> = {}; (j.accounts ?? []).forEach((a: { provider_key: string; status: string }) => { st[a.provider_key] = a.status; }); setAiStatus(st); }
    } catch { /* non-fatal */ }
  }, [supabase]);

  async function saveAiKey(provider: string) {
    const key = (aiKey[provider] || "").trim();
    if (!key) { setErr({ k: "ai:" + provider, m: "Tempel kunci dulu" }); return; }
    setBusy("ai:" + provider); setErr(null);
    try {
      const r = await fetch("/api/credentials/ai", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider_key: provider, key }) });
      const j = await r.json();
      setBusy("");
      if (!r.ok) { setErr({ k: "ai:" + provider, m: j.error || "Gagal" }); return; }
      setAiStatus((s) => ({ ...s, [provider]: j.status }));
      setAiKey((s) => ({ ...s, [provider]: "" }));
      if (j.status === "invalid") setErr({ k: "ai:" + provider, m: "Kunci ditolak penyedia — cek lagi." });
    } catch { setBusy(""); setErr({ k: "ai:" + provider, m: "Server tak terjangkau" }); }
  }
  useEffect(() => {
    load(); loadYt();
    const sp = new URLSearchParams(window.location.search);
    const r = sp.get("youtube");
    if (r === "connected") { setYtMsg("connected"); window.history.replaceState({}, "", "/integrations"); loadYt(); }
    else if (r === "error") { setYtMsg(`error:${sp.get("reason") || "unknown"}`); window.history.replaceState({}, "", "/integrations"); }
  }, [load, loadYt]);

  const flash = (k: string) => { setSaved(k); setTimeout(() => setSaved(""), 2500); };
  const rank = PLAN_RANK[plan] ?? 1;

  async function connectYt() {
    setErr(null);
    if (!ytCid.trim() || !ytSecret.trim()) { setErr({ k: "yt", m: "Isi Client ID & Secret dulu." }); return; }
    setBusy("yt");
    try {
      const r = await fetch("/api/youtube/connect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: ytCid, client_secret: ytSecret, ret: "/integrations" }) });
      const j = await r.json();
      if (r.ok && j.authorize_url) { window.location.href = j.authorize_url; return; }
      setBusy(""); setErr({ k: "yt", m: j.error || "Gagal memulai koneksi." });
    } catch { setBusy(""); setErr({ k: "yt", m: "Server tak terjangkau." }); }
  }
  async function disconnectYt() {
    setBusy("ytd"); setErr(null);
    try { await fetch("/api/youtube/disconnect", { method: "POST" }); setYtCid(""); setYtSecret(""); await loadYt(); flash("ytd"); }
    catch { setErr({ k: "yt", m: "Gagal memutus." }); } finally { setBusy(""); }
  }
  async function saveTelegram() {
    setErr(null);
    if (!tgChat.trim()) { setErr({ k: "tg", m: "Isi Chat ID dulu" }); return; }
    setBusy("tg");
    // Validate-early: kirim pesan TES via bot → hanya tersimpan bila terkirim (bukti chat benar + bot di-Start).
    try {
      const r = await fetch("/api/credentials/telegram", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: tgChat.trim() }) });
      const j = await r.json();
      setBusy("");
      if (!j.ok) { setErr({ k: "tg", m: j.error || "Tes gagal — pastikan sudah tekan Start di bot." }); return; }
      setTgEnabled(true); flash("tg");
    } catch { setBusy(""); setErr({ k: "tg", m: "Server tak terjangkau" }); }
  }

  function GatedCard({ icon, name, desc, minRank, minLabel }: { icon: React.ReactNode; name: string; desc: { id: string; en: string }; minRank: number; minLabel: string }) {
    const ok = rank >= minRank;
    return (
      <div className="card card-pad" style={{ opacity: ok ? 1 : 0.65 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {icon}
          <div style={{ flex: 1 }}><div style={titleS}>{name} {!ok && <span className="badge badge-default" style={{ fontSize: "0.625rem" }}>{minLabel}</span>}</div><div style={muted}><Bi id={desc.id} en={desc.en} /></div></div>
          <span className="badge badge-default" style={{ fontSize: "0.625rem" }}><Bi id="Segera" en="Soon" /></span>
        </div>
        {!ok && <div style={{ ...muted, fontSize: "var(--text-xs)", marginTop: "0.5rem" }}><Bi id={`Tersedia di paket ${minLabel}. Upgrade untuk mengaktifkan.`} en={`Available on ${minLabel} plan. Upgrade to enable.`} /></div>}
      </div>
    );
  }

  return (
    <>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1><Bi id="Kredensial & Koneksi" en="Credentials & Connections" /></h1>
        <div style={muted}><Bi id="Isi kunci AI, hubungkan YouTube & Telegram sekali di sini — berlaku untuk semua channel Anda." en="Set AI keys, connect YouTube & Telegram once here — applies to all your channels." /></div>
      </div>

      <div style={{ display: "grid", gap: "1rem", maxWidth: 720 }}>
        {/* Kunci AI — POOL tenant per penyedia (validate-early) */}
        <div className="card card-pad">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
            <span style={iconBox("var(--accent,#7c3aed)")}><KeyRound size={18} /></span>
            <div style={{ flex: 1 }}><div style={titleS}><Bi id="Kunci AI" en="AI Keys" /></div><div style={muted}><Bi id="Kunci penyedia AI Anda (BYOK) — dipakai semua channel. Penulis naskah (LLM), pengisi suara (TTS), pembuat visual (gambar/video)." en="Your AI provider keys (BYOK) — shared across channels. Script writer (LLM), voice (TTS), visual generator (image/video)." /></div></div>
          </div>
          {aiProvs.length === 0 && <div style={{ ...muted, fontSize: "var(--text-xs)" }}><Bi id="Memuat penyedia…" en="Loading providers…" /></div>}
          {aiProvs.filter((p) => p.auth !== "none").map((p) => {
            const st = aiStatus[p.key];
            const badge = st === "valid" ? <span className="badge badge-success" style={{ fontSize: "0.625rem" }}><span className="dot" /> Valid</span>
              : st === "invalid" ? <span className="badge badge-danger" style={{ fontSize: "0.625rem" }}><span className="dot" /> Tidak valid</span>
              : st === "unchecked" ? <span className="badge badge-default" style={{ fontSize: "0.625rem" }}><span className="dot" /> Tersimpan</span>
              : <span className="badge badge-default" style={{ fontSize: "0.625rem" }}><span className="dot" /> Belum diisi</span>;
            return (
              <div key={p.key} style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.75rem", marginTop: "0.75rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
                  <b style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>{p.name}</b>
                  <span style={{ ...muted, fontSize: "var(--text-xs)" }}>· {p.uses.join(", ")}</span>
                  <span style={{ marginLeft: "auto" }}>{badge}</span>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input className="input input-mono" type="text" placeholder={st ? "Isi untuk ganti kunci" : "Tempel API key penyedia"} value={aiKey[p.key] || ""} onChange={(e) => setAiKey((s) => ({ ...s, [p.key]: e.target.value }))} />
                  <button className="btn btn-default btn-sm" disabled={busy === "ai:" + p.key} onClick={() => saveAiKey(p.key)}>{busy === "ai:" + p.key ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan & Uji" en="Save & Test" />}</button>
                </div>
                {err?.k === "ai:" + p.key && <span style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-xs)" }}>{err.m}</span>}
              </div>
            );
          })}
          <div style={{ ...muted, fontSize: "var(--text-xs)", marginTop: "0.75rem" }}><Bi id="Penyedia gratis (mis. Edge) tak butuh kunci. Biaya ditagih langsung ke akun penyedia Anda (BYOK)." en="Free providers (e.g. Edge) need no key. Cost is billed directly to your provider account (BYOK)." /></div>
        </div>

        {/* YouTube — tenant-level OAuth (BYO-CC) */}
        <div className="card card-pad">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <span style={iconBox("#ff0000")}><Video size={18} /></span>
            <div style={{ flex: 1 }}><div style={titleS}>YouTube</div><div style={muted}><Bi id="Auto-publish (BYO-CC, kredensial Anda sendiri). Satu koneksi → semua channel." en="Auto-publish (BYO-CC, your own credentials). One connection → all channels." /></div></div>
            <span style={{ fontSize: "var(--text-xs)", fontWeight: 600, color: yt?.connected ? "var(--success)" : "var(--text-muted,#888)" }}>
              {yt?.connected ? <><Check size={13} style={{ verticalAlign: "-2px" }} /> <Bi id="Tersambung" en="Connected" /></> : <Bi id="Belum tersambung" en="Not connected" />}
            </span>
          </div>
          {ytMsg === "connected" && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", color: "var(--success)" }}><Check size={13} style={{ verticalAlign: "-2px" }} /> <Bi id="YouTube berhasil tersambung." en="YouTube connected." /></div>}
          {ytMsg?.startsWith("error:") && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", color: "var(--danger,#ef4444)" }}>OAuth gagal: {ytMsg.slice(6)}</div>}
          {yt?.degraded && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-xs)", color: "var(--text-muted,#888)" }}><Bi id="Status koneksi tak tersedia saat ini." en="Connection status unavailable right now." /></div>}
          {yt?.connected ? (
            <div>
              {yt.channel_id && <div style={{ ...muted, marginBottom: "0.5rem" }}>Channel ID: <code>{yt.channel_id}</code></div>}
              <button className="btn btn-outline btn-sm" onClick={disconnectYt} disabled={busy === "ytd"}>{busy === "ytd" ? <Loader2 size={14} className="spin" /> : <Bi id="Putuskan" en="Disconnect" />}</button>
              <Saved on={saved === "ytd"} />
            </div>
          ) : (
            <div>
              <div style={{ fontSize: "var(--text-xs)", marginBottom: "0.75rem", padding: "0.5rem 0.625rem", borderRadius: "var(--r-md)", background: "var(--surface-2)", border: "1px solid var(--border-subtle)", display: "flex", gap: "0.4rem", alignItems: "center" }}><ShieldCheck size={14} style={{ color: "var(--accent)", flex: "none" }} /><span><Bi id="Daftarkan Redirect URI ini di OAuth app Google Anda: " en="Register this Redirect URI in your Google OAuth app: " /><code>{YT_REDIRECT}</code></span></div>
              <div className="fld"><label className="label">Google Client ID</label><input className="input input-mono" value={ytCid} onChange={(e) => setYtCid(e.target.value)} placeholder="xxxxx.apps.googleusercontent.com" /></div>
              <div className="fld"><label className="label">Google Client Secret</label><input className="input input-mono" type="password" value={ytSecret} onChange={(e) => setYtSecret(e.target.value)} placeholder="GOCSPX-xxxxxxxx" /></div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.75rem" }}>
                <button className="btn btn-default btn-sm" onClick={connectYt} disabled={busy === "yt"}>{busy === "yt" ? <Loader2 size={14} className="spin" /> : <><Video size={14} /> <Bi id="Hubungkan via Google" en="Connect via Google" /></>}</button>
                {err?.k === "yt" && <span style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-xs)" }}>{err.m}</span>}
              </div>
            </div>
          )}
        </div>

        {/* Telegram — notif */}
        <div className="card card-pad">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.875rem" }}>
            <span style={iconBox("var(--telegram,#229ED9)")}><Send size={18} /></span>
            <div style={{ flex: 1 }}><div style={titleS}>Telegram</div><div style={muted}><Bi id="Notif real-time per run ke chat Anda" en="Real-time per-run notifications to your chat" /></div></div>
            <label className="switch"><input type="checkbox" checked={tgEnabled} onChange={(e) => setTgEnabled(e.target.checked)} /><span className="track" /><span className="thumb" /></label>
          </div>
          <div className="fld"><label className="label">Telegram Chat ID</label><input className="input input-mono" value={tgChat} onChange={(e) => setTgChat(e.target.value)} placeholder="mis. 123456789" /></div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.75rem" }}>
            <button className="btn btn-default btn-sm" onClick={saveTelegram} disabled={busy === "tg"}>{busy === "tg" ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan Telegram" en="Save Telegram" />}</button>
            {err?.k === "tg" && <span style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-xs)" }}>{err.m}</span>}<Saved on={saved === "tg"} />
          </div>
        </div>

        <GatedCard icon={<span style={iconBox("linear-gradient(45deg,#f09433,#dc2743,#bc1888)")}><ImageIcon size={18} /></span>}
          name="Instagram" desc={{ id: "Auto-publish Reels", en: "Auto-publish Reels" }} minRank={2} minLabel="Pro" />
        <GatedCard icon={<span style={iconBox("#000")}><Video size={18} /></span>}
          name="TikTok" desc={{ id: "Auto-publish video pendek", en: "Auto-publish short videos" }} minRank={3} minLabel="Business" />
      </div>
    </>
  );
}
