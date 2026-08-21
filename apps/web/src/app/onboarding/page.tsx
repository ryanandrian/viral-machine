"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { KeyRound, Video, Send, Tv, Check, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { HelpDot } from "@/components/help-dot";
import "./onboarding.css";

// Onboarding = PENGARAH (keputusan owner 2026-06-25): arahkan tenant baru melengkapi
// (1) Page Kredensial lalu (2) Channel pertama. ONBOARDED = channel pertama semua indikator hijau.
// Pakai SINYAL NYATA (status kredensial pool + channel_readiness) — nol mock, nol endpoint mati.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

const muted: React.CSSProperties = { fontSize: "var(--text-sm)", color: "var(--text-secondary)" };
const iconBox = (bg: string): React.CSSProperties => ({ width: 40, height: 40, borderRadius: "var(--r-md)", background: bg, display: "grid", placeItems: "center", color: "#fff", flex: "none" });

export default function OnboardingPage() {
  const router = useRouter();
  const [supabase] = useState(() => createClient());
  const [loading, setLoading] = useState(true);
  // status kredensial (tenant-wide)
  const [aiOk, setAiOk] = useState(false);      // ≥1 kunci AI valid
  const [ytOk, setYtOk] = useState(false);      // ≥1 koneksi YouTube tersambung
  const [tgOk, setTgOk] = useState(false);      // Telegram terisi
  // channel pertama + kesiapan
  const [chId, setChId] = useState<string | null>(null);
  const [chName, setChName] = useState<string>("");
  const [chReady, setChReady] = useState<boolean | null>(null);
  const [chMissing, setChMissing] = useState<string[]>([]);
  // Alasan BERSTRUKTUR (migr 0204). Layar ini menampilkan LABEL MENTAH ke tenant BARU — tanpa
  // alasan, tenant baru membaca jargon mesin ("model naskah") dan tak tahu apa yang harus dikerjakan.
  const [chReasons, setChReasons] = useState<{ slot: string; code: string; model: string; provider: string; provider_name: string | null }[]>([]);

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { window.location.href = "/auth?view=login"; return; }
    // Kredensial: kunci AI (pool, validate-early) · YouTube (pool) · Telegram (tenant_configs)
    try { const r = await fetch("/api/credentials/ai"); if (r.ok) { const j = await r.json(); setAiOk((j.accounts || []).some((a: { status: string }) => a.status === "valid")); } } catch {}
    try { const r = await fetch("/api/youtube/status"); if (r.ok) { const j = await r.json(); setYtOk((j.accounts || []).some((a: { connected: boolean }) => a.connected)); } } catch {}
    const { data: tc } = await supabase.from("tenant_configs").select("telegram_chat_id").maybeSingle();
    setTgOk(!!(tc as { telegram_chat_id?: string } | null)?.telegram_chat_id);
    // Channel pertama
    const { data: chs } = await supabase.from("channels").select("id,channel_name").order("created_at", { ascending: true }).limit(1);
    const ch = (chs as { id: string; channel_name: string | null }[] | null)?.[0];
    if (ch) {
      setChId(ch.id); setChName(ch.channel_name || "Channel");
      try { const { data: rd } = await supabase.rpc("channel_readiness", { p_channel_id: ch.id }); if (rd) { setChReady((rd as { ready: boolean }).ready); setChMissing((rd as { missing: string[] }).missing || []); setChReasons((rd as { reasons?: { slot: string; code: string; model: string; provider: string; provider_name: string | null }[] }).reasons || []); } } catch {}
    }
    setLoading(false);
  }, [supabase]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="ob-root" style={{ display: "grid", placeItems: "center", minHeight: "60vh" }}><Loader2 className="spin" /></div>;

  const credAll = aiOk && ytOk && tgOk;
  const Dot = ({ ok }: { ok: boolean }) => ok
    ? <Check size={15} style={{ color: "var(--success)", flex: "none" }} />
    : <span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--danger,#ef4444)", flex: "none" }} />;

  return (
    <div className="ob-root" style={{ maxWidth: 640, margin: "0 auto", padding: "2rem 1.25rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.4rem" }}>
        <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 30, height: 30, objectFit: "contain" }} />
        <h1 style={{ fontSize: "1.4rem", margin: 0 }}><Bi id="Selamat datang 👋" en="Welcome 👋" /><HelpDot locationKey="onboarding" size={15} /></h1>
      </div>
      <p style={{ ...muted, marginBottom: "1.5rem" }}><Bi id="Dua langkah untuk mulai: lengkapi Kredensial, lalu siapkan channel pertama. Channel aktif otomatis saat semua indikator hijau." en="Two steps to start: complete Credentials, then set up your first channel. It activates once all indicators are green." /></p>

      {/* LANGKAH 1 — KREDENSIAL */}
      <div className="card card-pad" style={{ marginBottom: "1rem", borderLeft: `3px solid ${credAll ? "var(--success)" : "var(--brand)"}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
          <span style={iconBox("var(--accent,#7c3aed)")}><KeyRound size={20} /></span>
          <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}><Bi id="1. Lengkapi Kredensial" en="1. Complete Credentials" /></div><div style={muted}><Bi id="Kunci AI, YouTube, Telegram — berlaku semua channel." en="AI keys, YouTube, Telegram — shared across channels." /></div></div>
          {credAll && <Check size={18} style={{ color: "var(--success)" }} />}
        </div>
        <ul style={{ listStyle: "none", margin: "0 0 0.875rem", padding: 0, display: "grid", gap: "0.4rem" }}>
          <li style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)" }}><KeyRound size={14} style={{ color: "var(--text-muted)" }} /> <span style={{ flex: 1 }}><Bi id="Kunci AI (≥1 valid)" en="AI key (≥1 valid)" /></span> <Dot ok={aiOk} /></li>
          <li style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)" }}><Video size={14} style={{ color: "var(--text-muted)" }} /> <span style={{ flex: 1 }}><Bi id="Koneksi YouTube" en="YouTube connection" /></span> <Dot ok={ytOk} /></li>
          <li style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)" }}><Send size={14} style={{ color: "var(--text-muted)" }} /> <span style={{ flex: 1 }}>Telegram</span> <Dot ok={tgOk} /></li>
        </ul>
        <Link href="/integrations" className="btn btn-default btn-sm"><KeyRound size={14} /> <Bi id={credAll ? "Buka Kredensial" : "Lengkapi Kredensial"} en={credAll ? "Open Credentials" : "Complete Credentials"} /> <ArrowRight size={14} /></Link>
      </div>

      {/* LANGKAH 2 — CHANNEL */}
      <div className="card card-pad" style={{ marginBottom: "1.25rem", borderLeft: `3px solid ${chReady ? "var(--success)" : "var(--brand)"}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
          <span style={iconBox("var(--brand)")}><Tv size={20} /></span>
          <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}><Bi id="2. Siapkan channel pertama" en="2. Set up your first channel" /></div><div style={muted}><Bi id="Niche, AI (penyedia→model→akun), jadwal, YouTube tujuan." en="Niche, AI (provider→model→account), schedule, YouTube target." /></div></div>
          {chReady && <Check size={18} style={{ color: "var(--success)" }} />}
        </div>
        {!chId ? (
          <Link href="/channels/new" className="btn btn-default btn-sm"><Tv size={14} /> <Bi id="Buat channel" en="Create channel" /> <ArrowRight size={14} /></Link>
        ) : chReady ? (
          <p style={{ fontSize: "var(--text-sm)", color: "var(--success)", display: "flex", alignItems: "center", gap: "0.4rem", margin: "0 0 0.5rem" }}><Check size={15} /> <Bi id={`"${chName}" siap & bisa diaktifkan.`} en={`"${chName}" is ready to activate.`} /></p>
        ) : (
          <>
            <p style={{ ...muted, marginTop: 0, marginBottom: "0.5rem" }}><Bi id={`"${chName}" — lengkapi:`} en={`"${chName}" — complete:`} /></p>
            <ul style={{ listStyle: "none", margin: "0 0 0.875rem", padding: 0, display: "grid", gap: "0.3rem" }}>
              {chMissing.map((m) => <li key={m} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)" }}><span style={{ width: 9, height: 9, borderRadius: "50%", background: "var(--danger,#ef4444)", flex: "none" }} /> {m}</li>)}
            </ul>
            {chReasons.length > 0 && (
              <ul style={{ listStyle: "none", margin: "-0.5rem 0 0.875rem", padding: 0, display: "grid", gap: "0.25rem" }}>
                {chReasons.map((x) => (
                  <li key={`${x.slot}-${x.model}`} style={{ ...muted, fontSize: "var(--text-xs)" }}>
                    <Bi id={`Pilihan Anda "${x.model}" sudah tidak tersedia di ${x.provider_name || x.provider || "penyedianya"} — pilih penggantinya di halaman channel.`}
                        en={`Your choice "${x.model}" is no longer available at ${x.provider_name || x.provider || "its provider"} — pick a replacement on the channel page.`} />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
        {chId && <Link href={`/channels/${chId}`} className="btn btn-secondary btn-sm" style={{ marginTop: chReady ? 0 : "0.25rem" }}><Bi id="Buka channel" en="Open channel" /> <ArrowRight size={14} /></Link>}
      </div>

      {/* SELESAI */}
      {credAll && chReady ? (
        <div className="card card-pad" style={{ background: "var(--accent-soft)", textAlign: "center" }}>
          <Sparkles size={22} style={{ color: "var(--accent)", marginBottom: "0.4rem" }} />
          <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}><Bi id="Setup selesai! 🎉" en="Setup complete! 🎉" /></div>
          <p style={{ ...muted, marginBottom: "0.875rem" }}><Bi id="Channel siap berproduksi otomatis." en="Your channel is ready to auto-produce." /></p>
          <button className="btn btn-ai" onClick={() => router.push("/dashboard")}><Bi id="Masuk Dashboard" en="Go to Dashboard" /> <ArrowRight size={15} /></button>
        </div>
      ) : (
        <div style={{ textAlign: "center" }}><a href="/dashboard" className="link" style={{ fontSize: "var(--text-sm)" }}><Bi id="Lewati dulu, lanjutkan nanti →" en="Skip for now, finish later →" /></a></div>
      )}
    </div>
  );
}
