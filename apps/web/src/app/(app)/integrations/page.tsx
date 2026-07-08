"use client";

import { useCallback, useEffect, useState } from "react";
import { Video, Send, Check, Loader2, ShieldCheck, Image as ImageIcon, KeyRound, Globe } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { PageHeader } from "@/components/page-header";

// Page Kredensial (tenant-wide) — CHANNEL_LOCK_ACTIVATION_PLAN.md §2.1. Tiga bagian:
//  · Kunci AI PER-ELEMEN (LLM/TTS/Visual), model VENDOR/key-group, boleh >1 kunci, TAMPIL APA ADANYA.
//  · Koneksi YouTube = OAuth PLATFORM (kumpulan koneksi; tenant klik "Hubungkan dengan Google", tak pegang Client/URL).
//  · Telegram (notif, validate-early). Channel menugaskan penyedia+model+akun & koneksi+target di Channel Setting.
// Hanya kelas GLOBAL (components.css) + inline.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
function Saved({ on }: { on: boolean }) { return on ? <span style={{ color: "var(--success)", fontSize: "var(--text-xs)", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}><Check size={13} /> <Bi id="Tersimpan" en="Saved" /></span> : null; }

const PLAN_RANK: Record<string, number> = { trial: 0, starter: 1, pro: 2, business: 3, scale: 3, enterprise: 4 };
const muted: React.CSSProperties = { fontSize: "var(--text-sm)", color: "var(--text-secondary)" };
const titleS: React.CSSProperties = { fontWeight: 600, color: "var(--text-primary)" };
const iconBox = (bg: string): React.CSSProperties => ({ width: 36, height: 36, borderRadius: "var(--r-md)", background: bg, display: "grid", placeItems: "center", color: "#fff", flex: "none" });

// 3 ELEMEN AI (§0.4). Tiap elemen: penyedia disaring per komponen katalog; tenant boleh >1 kunci.
const AI_ELEMENTS: { key: string; comps: string[]; id: string; en: string; desc_id: string; desc_en: string }[] = [
  { key: "llm", comps: ["llm"], id: "Penulis Naskah (LLM)", en: "Script Writer (LLM)", desc_id: "AI penulis cerita, hook & narasi. Makin pintar = naskah makin bagus.", desc_en: "AI that writes story, hook & narration." },
  { key: "tts", comps: ["tts"], id: "Pengisi Suara (TTS)", en: "Voice (TTS)", desc_id: "Ubah naskah jadi suara narator.", desc_en: "Turns the script into narrator voice." },
  { key: "visual", comps: ["image", "video"], id: "Pembuat Visual", en: "Visual Generator", desc_id: "Buat gambar/video tiap adegan.", desc_en: "Makes the image/video for each scene." },
];

export default function IntegrationsPage() {
  const [supabase] = useState(() => createClient());
  const [plan, setPlan] = useState("starter");
  const [busy, setBusy] = useState("");
  const [saved, setSaved] = useState("");
  const [err, setErr] = useState<{ k: string; m: string } | null>(null);

  // [B11] Batch 1.6 — koneksi "berwajah": nama+foto channel YouTube + dipakai channel MesinViral mana.
  type YtAccount = { id: string; label: string; connected: boolean; has_client: boolean; status: string; yt_channel_id: string | null; yt_channel_title?: string | null; yt_channel_thumb?: string | null; used_by?: { id: string; channel_name: string }[] };
  const [ytAccounts, setYtAccounts] = useState<YtAccount[]>([]);
  const [ytDegraded, setYtDegraded] = useState(false);
  const [ytLabel, setYtLabel] = useState("");
  const [ytAdd, setYtAdd] = useState(false);
  const [ytMsg, setYtMsg] = useState<string | null>(null);

  const [tgChat, setTgChat] = useState(""); const [tgEnabled, setTgEnabled] = useState(false);

  // Kunci AI model VENDOR (§0.4): per-elemen, boleh >1 kunci/vendor, nilai TAMPIL APA ADANYA.
  type Prov = { key: string; name: string; auth: string; key_group: string; comps: string[]; activeComps: string[]; free_note: string | null };
  type AiAcct = { id: string; provider_key: string; key_group: string; label: string; status: string; key: string };
  const [provs, setProvs] = useState<Prov[]>([]);
  const [aiAccts, setAiAccts] = useState<AiAcct[]>([]);
  const [editKey, setEditKey] = useState<Record<string, string>>({});  // account id → nilai kunci (edit)
  const [addF, setAddF] = useState<Record<string, { provider: string; label: string; key: string }>>({});  // element key → form tambah
  const [openAdd, setOpenAdd] = useState<string>("");  // element key yg form-tambahnya terbuka

  const loadYt = useCallback(async () => {
    try { const r = await fetch("/api/youtube/status"); if (r.ok) { const j = await r.json(); setYtAccounts(j.accounts || []); setYtDegraded(!!j.degraded); } } catch { /* abaikan */ }
  }, []);
  const load = useCallback(async () => {
    const { data } = await supabase.from("tenant_configs").select("plan_type,telegram_chat_id,telegram_enabled").maybeSingle();
    const t = data as { plan_type?: string; telegram_chat_id?: string; telegram_enabled?: boolean } | null;
    setPlan(t?.plan_type ?? "starter"); setTgChat(t?.telegram_chat_id ?? ""); setTgEnabled(!!t?.telegram_enabled);
    // Penyedia AI dari katalog + VENDOR (key_group) utk pemetaan per-elemen. SEMUA model (aktif+nonaktif):
    // halaman kredensial = level VENDOR — tenant harus BISA memasukkan kunci walau modelnya belum
    // diaktifkan (temuan owner 2026-07-06: model nonaktif → provider tersembunyi → kunci tak pernah
    // bisa masuk → uji aktivasi tak pernah terjadi = lingkaran mati). Pemilih MODEL di channel tetap
    // menyaring is_active (di sana barulah "bisa dipakai").
    const { data: am } = await supabase.from("ai_models").select("provider_key,component,is_active");
    const { data: ap } = await supabase.from("ai_providers").select("provider_key,display_name,auth_type,key_group,free_tier_note").eq("is_active", true);
    const byProv: Record<string, Set<string>> = {};
    const byProvActive: Record<string, Set<string>> = {};
    ((am ?? []) as { provider_key: string; component: string; is_active: boolean }[]).forEach((m) => {
      (byProv[m.provider_key] ??= new Set()).add(m.component);
      if (m.is_active) (byProvActive[m.provider_key] ??= new Set()).add(m.component);
    });
    setProvs(((ap ?? []) as { provider_key: string; display_name: string; auth_type: string; key_group: string | null; free_tier_note: string | null }[])
      .filter((p) => byProv[p.provider_key])
      .map((p) => ({ key: p.provider_key, name: p.display_name, auth: p.auth_type, key_group: p.key_group || p.provider_key, comps: [...byProv[p.provider_key]], activeComps: [...(byProvActive[p.provider_key] ?? [])], free_note: p.free_tier_note || null })));
    try {
      const r = await fetch("/api/credentials/ai");
      if (r.ok) {
        const j = await r.json();
        const accts = (j.accounts ?? []) as AiAcct[];
        setAiAccts(accts);
        // TAMPIL APA ADANYA (§0.4): prefill nilai kunci ter-decrypt per akun (editable).
        setEditKey(Object.fromEntries(accts.map((a) => [a.id, a.key || ""])));
      }
    } catch { /* non-fatal */ }
  }, [supabase]);

  // Simpan/edit 1 kunci AI (vendor). accountId ada → edit; tidak ada → tambah baru. errKey = id akun / "add:"+elemen.
  async function saveAccount(provider: string, key: string, label: string, accountId: string | undefined, errKey: string) {
    if (!key.trim()) { setErr({ k: errKey, m: "Tempel kunci dulu" }); return; }
    if (!provider) { setErr({ k: errKey, m: "Pilih penyedia dulu" }); return; }
    setBusy("acct:" + errKey); setErr(null);
    try {
      const r = await fetch("/api/credentials/ai", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider_key: provider, key: key.trim(), label, account_id: accountId || null }) });
      const j = await r.json(); setBusy("");
      if (!r.ok) { setErr({ k: errKey, m: j.error || "Gagal" }); return; }
      if (j.status === "invalid") setErr({ k: errKey, m: "Kunci ditolak penyedia — cek lagi." });
      setOpenAdd(""); await load();  // muat ulang daftar (status + nilai)
    } catch { setBusy(""); setErr({ k: errKey, m: "Server tak terjangkau" }); }
  }
  async function deleteAccount(id: string) {
    setBusy("del:" + id); setErr(null);
    try { await fetch("/api/credentials/ai/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ account_id: id }) }); await load(); }
    catch { setErr({ k: id, m: "Gagal hapus" }); } finally { setBusy(""); }
  }
  // Helper pemetaan elemen → penyedia & akun (vendor key-group).
  const provsForEl = (comps: string[]) => provs.filter((p) => p.comps.some((c) => comps.includes(c)));
  const acctsForEl = (comps: string[]) => { const v = new Set(provsForEl(comps).map((p) => p.key_group)); return aiAccts.filter((a) => v.has(a.key_group)); };
  useEffect(() => {
    load(); loadYt();
    const sp = new URLSearchParams(window.location.search);
    const r = sp.get("youtube");
    const chName = sp.get("channel") || "";
    if (r === "connected") { setYtMsg(`connected:${chName}`); window.history.replaceState({}, "", "/integrations"); loadYt(); }
    else if (r === "already") { setYtMsg(`already:${chName}`); window.history.replaceState({}, "", "/integrations"); loadYt(); }  // [B11] dedup: token disegarkan, bukan baris baru
    else if (r === "error") { setYtMsg(`error:${sp.get("reason") || "unknown"}`); window.history.replaceState({}, "", "/integrations"); }
  }, [load, loadYt]);

  const flash = (k: string) => { setSaved(k); setTimeout(() => setSaved(""), 2500); };
  const rank = PLAN_RANK[plan] ?? 1;

  async function connectYt() {
    setErr(null); setBusy("yt");
    // OAuth PLATFORM: tenant cukup klik → consent Google. Tak ada client id/secret/URL.
    try {
      const r = await fetch("/api/youtube/connect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ label: ytLabel, ret: "/integrations" }) });
      const j = await r.json();
      if (r.ok && j.authorize_url) { window.location.href = j.authorize_url; return; }
      setBusy(""); setErr({ k: "yt", m: j.error || "Gagal memulai koneksi." });
    } catch { setBusy(""); setErr({ k: "yt", m: "Server tak terjangkau." }); }
  }
  async function disconnectYt(accountId: string) {
    setBusy("ytd:" + accountId); setErr(null);
    try { await fetch("/api/youtube/disconnect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ account_id: accountId }) }); await loadYt(); }
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
  // Toggle aktif/nonaktif notif Telegram — persist ke telegram_enabled (RPC whitelist). BE menghormati toggle ini.
  async function toggleTg(on: boolean) {
    setErr(null); setTgEnabled(on);  // optimistik
    const { error } = await supabase.rpc("set_tenant_config", { p_telegram_enabled: on });
    if (error) { setTgEnabled(!on); setErr({ k: "tg", m: error.message }); return; }
    flash("tg");
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
      <PageHeader icon={Globe} title={<Bi id="Kredensial & Koneksi" en="Credentials & Connections" />} subtitle={<Bi id="Isi kunci AI, hubungkan YouTube & Telegram sekali di sini — berlaku untuk semua channel Anda." en="Set AI keys, connect YouTube & Telegram once here — applies to all your channels." />} />

      <div style={{ display: "grid", gap: "1rem", maxWidth: 720 }}>
        {/* Kunci AI — per ELEMEN (LLM/TTS/Visual), boleh >1 kunci/vendor, nilai TAMPIL APA ADANYA (§0.4) */}
        {AI_ELEMENTS.map((el) => {
          const eProvs = provsForEl(el.comps).filter((p) => p.auth !== "none");   // berbayar → butuh kunci
          const freeProvs = provsForEl(el.comps).filter((p) => p.auth === "none"); // gratis (Edge) → tanpa kunci
          const accts = acctsForEl(el.comps);
          const badge = (s: string) => s === "valid" ? <span className="badge badge-success" title="Kunci terverifikasi bekerja di penyedia" style={{ fontSize: "0.625rem" }}><span className="dot" /> <Bi id="Valid" en="Valid" /></span>
            : s === "invalid" ? <span className="badge badge-danger" title="Kunci ditolak penyedia — periksa & simpan ulang" style={{ fontSize: "0.625rem" }}><span className="dot" /> <Bi id="Tidak valid" en="Invalid" /></span>
            : <span className="badge badge-default" title="Kunci tersimpan namun belum terverifikasi — klik Simpan & Uji untuk memastikan" style={{ fontSize: "0.625rem" }}><span className="dot" /> <Bi id="Tersimpan (belum diuji)" en="Saved (untested)" /></span>;
          const f = addF[el.key] || { provider: "", label: "", key: "" };
          const setF = (patch: Partial<{ provider: string; label: string; key: string }>) => setAddF((s) => ({ ...s, [el.key]: { ...f, ...patch } }));
          return (
            <div key={el.key} className="card card-pad">
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.25rem" }}>
                <span style={iconBox("var(--accent,#7c3aed)")}><KeyRound size={18} /></span>
                <div style={{ flex: 1 }}><div style={titleS}><Bi id={el.id} en={el.en} /></div><div style={muted}><Bi id={el.desc_id} en={el.desc_en} /></div></div>
              </div>
              <div style={{ ...muted, fontSize: "var(--text-xs)", marginBottom: "0.25rem" }}>
                <Bi id="Penyedia tersedia: " en="Available providers: " />
                {[...eProvs, ...freeProvs].map((p, i) => (
                  <span key={p.key}>{i > 0 && " · "}{p.name}
                    {p.free_note && <span className="badge badge-success" style={{ fontSize: ".575rem", marginLeft: 4, verticalAlign: "1px" }}><Bi id="Gratis harian" en="Free daily" /></span>}
                    {p.auth === "none" && <span className="badge badge-success" style={{ fontSize: ".575rem", marginLeft: 4, verticalAlign: "1px" }}><Bi id="Gratis tanpa kunci" en="Free, no key" /></span>}
                    {!p.activeComps.some((c) => el.comps.includes(c)) && <span className="badge badge-warning" style={{ fontSize: ".575rem", marginLeft: 4, verticalAlign: "1px" }} title="Kunci bisa disimpan sekarang (berlaku level vendor); model utk elemen ini sedang disiapkan/menunggu uji — belum tampil di Pengaturan Channel."><Bi id="model segera hadir" en="model coming soon" /></span>}
                  </span>))}
                {[...eProvs, ...freeProvs].length === 0 && "—"}
              </div>
              {accts.length === 0 && <div style={{ ...muted, fontSize: "var(--text-xs)", padding: "0.4rem 0" }}><Bi id="Belum ada kunci untuk elemen ini." en="No key for this element yet." /></div>}
              {accts.map((a) => (
                <div key={a.id} style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.6rem", marginTop: "0.6rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                    <b style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>{a.label || a.provider_key}</b>
                    <span style={{ ...muted, fontSize: "var(--text-xs)" }}>· {(provs.find((p) => p.key === a.provider_key)?.name) || a.provider_key}</span>
                    <span style={{ marginLeft: "auto" }}>{badge(a.status)}</span>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <input className="input input-mono" type="text" value={editKey[a.id] ?? ""} onChange={(e) => setEditKey((s) => ({ ...s, [a.id]: e.target.value }))} />
                    <button className="btn btn-default btn-sm" disabled={busy === "acct:" + a.id} onClick={() => saveAccount(a.provider_key, editKey[a.id] || "", a.label, a.id, a.id)}>{busy === "acct:" + a.id ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan & Uji" en="Save & Test" />}</button>
                    <button className="btn btn-outline btn-sm" disabled={busy === "del:" + a.id} onClick={() => deleteAccount(a.id)}>{busy === "del:" + a.id ? <Loader2 size={14} className="spin" /> : <Bi id="Hapus" en="Remove" />}</button>
                  </div>
                  {err?.k === a.id && <span style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-xs)" }}>{err.m}</span>}
                </div>
              ))}
              {eProvs.length > 0 && (openAdd === el.key ? (
                <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.6rem", marginTop: "0.6rem", display: "grid", gap: "0.4rem" }}>
                  <select className="input" value={f.provider} onChange={(e) => setF({ provider: e.target.value })}>
                    <option value="">— pilih penyedia —</option>
                    {eProvs.map((p) => <option key={p.key} value={p.key}>{p.name}{p.free_note ? " — GRATIS harian" : ""}{!p.activeComps.some((c) => el.comps.includes(c)) ? " (model segera hadir)" : ""}</option>)}
                  </select>
                  {(() => { const sp = eProvs.find((p) => p.key === f.provider); return sp?.free_note
                    ? <div style={{ fontSize: "var(--text-xs)", color: "var(--success)", lineHeight: 1.5 }}>✓ {sp.free_note}</div> : null; })()}
                  <input className="input" placeholder="Label (mis. Utama / Cadangan)" value={f.label} onChange={(e) => setF({ label: e.target.value })} />
                  <input className="input input-mono" type="text" placeholder="Tempel API key penyedia" value={f.key} onChange={(e) => setF({ key: e.target.value })} />
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <button className="btn btn-default btn-sm" disabled={busy === "acct:add:" + el.key} onClick={() => saveAccount(f.provider, f.key, f.label, undefined, "add:" + el.key)}>{busy === "acct:add:" + el.key ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan & Uji" en="Save & Test" />}</button>
                    <button className="btn btn-ghost btn-sm" onClick={() => setOpenAdd("")}><Bi id="Batal" en="Cancel" /></button>
                    {err?.k === "add:" + el.key && <span style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-xs)" }}>{err.m}</span>}
                  </div>
                </div>
              ) : (
                <button className="btn btn-secondary btn-sm" style={{ marginTop: "0.6rem" }} onClick={() => { setOpenAdd(el.key); setF({ provider: eProvs[0]?.key || "", label: "", key: "" }); setErr(null); }}><KeyRound size={13} /> <Bi id="Tambah kunci" en="Add key" /></button>
              ))}
            </div>
          );
        })}

        {/* YouTube — POOL koneksi (banyak akun Google; channel pilih + target di Channel Setting) */}
        <div className="card card-pad">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <span style={iconBox("#ff0000")}><Video size={18} /></span>
            <div style={{ flex: 1 }}><div style={titleS}>YouTube</div><div style={muted}><Bi id="Hubungkan akun Google Anda — bisa lebih dari satu. Tiap channel pilih akun + tujuan di Pengaturan Channel." en="Connect your Google accounts — more than one allowed. Each channel picks an account + target in Channel Settings." /></div></div>
          </div>
          {ytMsg?.startsWith("connected:") && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", color: "var(--success)" }}><Check size={13} style={{ verticalAlign: "-2px" }} /> {ytMsg.slice(10) ? <Bi id={`Channel "${ytMsg.slice(10)}" berhasil tersambung — pastikan nama & foto di bawah sesuai.`} en={`Channel "${ytMsg.slice(10)}" connected — confirm the name & photo below match.`} /> : <Bi id="YouTube berhasil tersambung." en="YouTube connected." />}</div>}
          {ytMsg?.startsWith("already:") && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", color: "var(--success)" }}><Check size={13} style={{ verticalAlign: "-2px" }} /> <Bi id={`Channel "${ytMsg.slice(8)}" sudah pernah terhubung — koneksinya disegarkan (tidak dibuat ganda).`} en={`Channel "${ytMsg.slice(8)}" was already connected — its connection was refreshed (no duplicate created).`} /></div>}
          {ytMsg?.startsWith("error:") && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-sm)", color: "var(--danger,#ef4444)" }}>{ytMsg.slice(6) === "identity_failed" ? <Bi id="Gagal membaca identitas channel dari Google — koneksi dibatalkan, coba lagi." en="Could not read the channel identity from Google — connection cancelled, try again." /> : <>OAuth gagal: {ytMsg.slice(6)}</>}</div>}
          {ytDegraded && <div style={{ marginBottom: "0.75rem", fontSize: "var(--text-xs)", color: "var(--text-muted,#888)" }}><Bi id="Status koneksi tak tersedia saat ini." en="Connection status unavailable right now." /></div>}

          {ytAccounts.map((a) => (
            <div key={a.id} style={{ display: "flex", alignItems: "center", gap: "0.625rem", borderTop: "1px solid var(--border-subtle)", paddingTop: "0.6rem", marginTop: "0.6rem" }}>
              {/* [B11] wajah channel: foto (fallback ikon) + NAMA channel YouTube — konfirmasi visual anti salah-pilih */}
              {a.yt_channel_thumb
                ? <img src={a.yt_channel_thumb} alt="" style={{ width: 36, height: 36, borderRadius: "50%", objectFit: "cover", flex: "none" }} referrerPolicy="no-referrer" />
                : <span style={{ ...iconBox("var(--surface-2)"), color: "var(--text-muted)" }}><Video size={16} /></span>}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.yt_channel_title || a.label}</div>
                <div style={{ ...muted, fontSize: "var(--text-xs)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {a.connected
                    ? <>{a.yt_channel_title && a.label !== a.yt_channel_title ? <>{a.label} · </> : null}<code style={{ fontSize: "0.625rem" }}>{a.yt_channel_id || "—"}</code></>
                    : <Bi id="belum selesai connect" en="connect not finished" />}
                </div>
                {(a.used_by?.length ?? 0) > 0
                  ? <div style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginTop: 2 }}><Bi id="Dipakai oleh: " en="Used by: " /><b>{a.used_by!.map((u) => u.channel_name).join(", ")}</b></div>
                  : (a.connected && <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: 2 }}><Bi id="Belum dipakai channel mana pun" en="Not used by any channel yet" /></div>)}
              </div>
              {a.connected ? <span className="badge badge-success" style={{ fontSize: "0.625rem" }}><span className="dot" /> <Bi id="Tersambung" en="Connected" /></span> : <span className="badge badge-default" style={{ fontSize: "0.625rem" }}><span className="dot" /> <Bi id="Belum" en="Pending" /></span>}
              <button className="btn btn-outline btn-sm" onClick={() => disconnectYt(a.id)} disabled={busy === "ytd:" + a.id}>{busy === "ytd:" + a.id ? <Loader2 size={14} className="spin" /> : <Bi id="Hapus" en="Remove" />}</button>
            </div>
          ))}

          {!ytAdd ? (
            <button className="btn btn-default btn-sm" style={{ marginTop: "0.875rem" }} onClick={() => { setYtAdd(true); setErr(null); }}><Video size={14} /> <Bi id="Tambah koneksi YouTube" en="Add YouTube connection" /></button>
          ) : (
            <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.875rem", marginTop: "0.875rem" }}>
              <div style={{ fontSize: "var(--text-xs)", marginBottom: "0.75rem", padding: "0.5rem 0.625rem", borderRadius: "var(--r-md)", background: "var(--surface-2)", border: "1px solid var(--border-subtle)", display: "flex", gap: "0.4rem", alignItems: "center" }}><ShieldCheck size={14} style={{ color: "var(--accent)", flex: "none" }} /><span><Bi id="Anda akan diarahkan ke Google untuk memberi izin. Tak perlu Client ID/Secret/URL." en="You'll be sent to Google to grant access. No Client ID/Secret/URL needed." /></span></div>
              <div className="fld"><label className="label"><Bi id="Nama koneksi (mis. Akun Brand A)" en="Connection name (e.g. Brand A account)" /></label><input className="input" value={ytLabel} onChange={(e) => setYtLabel(e.target.value)} placeholder="Akun YouTube saya" /></div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.75rem" }}>
                <button className="btn btn-default btn-sm" onClick={connectYt} disabled={busy === "yt"}>{busy === "yt" ? <Loader2 size={14} className="spin" /> : <><Video size={14} /> <Bi id="Hubungkan dengan Google" en="Connect with Google" /></>}</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setYtAdd(false)}><Bi id="Batal" en="Cancel" /></button>
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
            <label className="switch"><input type="checkbox" checked={tgEnabled} onChange={(e) => toggleTg(e.target.checked)} /><span className="track" /><span className="thumb" /></label>
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
