"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ExternalLink, Settings, Zap, ArrowRight, BarChart3, Calendar, Activity, Loader2, Check, Pause, Play, RotateCw, AlertTriangle } from "lucide-react";
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
  production_paused: boolean | null; production_paused_reason: string | null;
  llm_model: string | null; llm_library: string | null; visual_mode: string | null;
  tts_provider: string | null; voice_key: string | null;
  image_quality: string | null; music_enabled: boolean | null; music_volume: number | null;
  music_default_mood: string | null; script_min_viral_score: number | null; script_max_retry: number | null;
  caption_style: Record<string, unknown> | null; niche_hashtags: Record<string, string[]> | null;
  cta_mode: string | null; brand_name: string | null; brand_cta_text: string | null; brand_logo: string | null;
  logo_position: string | null; logo_size: number | null; logo_opacity: number | null;
  landing_link: string | null; link_position: string | null;
};
// Default caption_style — match BE DEFAULT_CAPTION_STYLE (video_renderer). Partial-override OK.
const CAP_DEFAULT = { font_name: "Anton", font_size: 68, bold: true, active_word_color: "#FFD700", inactive_word_color: "#FFFFFF", outline_color: "#000000", outline: 4, position_y_pct: 83, max_words_per_line: 3 };
type ModelOpt = { model_key: string; provider_key: string; display_name: string };
type VoiceOpt = { voice_key: string; provider_key: string; display_name: string; gender: string | null };

// F2-07/F1-09: status efektif terpadu — SATU sumber (bukan is_active saja yg menyesatkan).
type Eff = { key: string; label_id: string; label_en: string; tone: "ok" | "warn" | "stop" | "muted"; reason?: string; reco_id?: string; reco_en?: string };
function effectiveStatus(ch: ChannelRow, sub: string | null, rd: { ready: boolean; missing: string[] } | null): Eff {
  if (sub && !["active", "trialing", "trial", "grace"].includes(sub))
    return { key: "sub", label_id: "Langganan nonaktif", label_en: "Subscription inactive", tone: "stop", reco_id: "Aktifkan langganan untuk melanjutkan produksi.", reco_en: "Reactivate subscription to resume." };
  if (ch.production_paused)
    return { key: "halted", label_id: "Dihentikan sistem", label_en: "Halted by system", tone: "stop", reason: ch.production_paused_reason ?? undefined,
      reco_id: "Perbaiki penyebabnya (kredit/konfigurasi), lalu klik “Jalankan ulang & pulihkan” — produksi-test; bila sukses channel aktif lagi.",
      reco_en: "Fix the cause (credit/config), then “Run & recover” — a test production; success reactivates the channel." };
  if (rd && !rd.ready)
    return { key: "incomplete", label_id: "Belum lengkap", label_en: "Incomplete", tone: "warn", reason: rd.missing?.length ? `Kurang: ${rd.missing.join(", ")}` : undefined,
      reco_id: "Lengkapi konfigurasi & kredensial di bawah, lalu aktifkan.", reco_en: "Complete config & credentials below, then activate." };
  if (!ch.is_active)
    return { key: "paused", label_id: "Dijeda", label_en: "Paused", tone: "warn", reco_id: "Channel dijeda manual. Klik Play untuk melanjutkan.", reco_en: "Manually paused. Click Play to resume." };
  return { key: "active", label_id: "Aktif", label_en: "Active", tone: "ok" };
}

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
  // F2-07/F1-09: status efektif
  const [sub, setSub] = useState<string | null>(null);
  const [rd, setRd] = useState<{ ready: boolean; missing: string[] } | null>(null);
  // F2-03: pemilih AI per-channel (model + voice). Katalog dari ai_models/tts_profiles/voice_catalog (RLS read).
  const [llmOpts, setLlmOpts] = useState<ModelOpt[]>([]);
  const [imgOpts, setImgOpts] = useState<ModelOpt[]>([]);
  const [ttsOpts, setTtsOpts] = useState<{ provider_key: string; display_name: string }[]>([]);
  const [voiceAll, setVoiceAll] = useState<VoiceOpt[]>([]);
  const [llmModel, setLlmModel] = useState("");
  const [vmode, setVmode] = useState<"video" | "ai_image">("video");
  const [imgModel, setImgModel] = useState("");
  const [ttsProv, setTtsProv] = useState("");
  const [voiceKey, setVoiceKey] = useState("");
  const [nicheDefaults, setNicheDefaults] = useState<Record<string, string>>({});
  const [savingAi, setSavingAi] = useState(false);
  const [aiMsg, setAiMsg] = useState<string | null>(null);
  // F2-03: knob operasional per-channel (mutu & biaya — hak tenant)
  const [imgQuality, setImgQuality] = useState("low");
  const [musicOn, setMusicOn] = useState(false);
  const [musicVol, setMusicVol] = useState(0.1);
  const [musicMood, setMusicMood] = useState("");
  const [minScore, setMinScore] = useState(75);
  const [maxRetry, setMaxRetry] = useState(3);
  const [savingOps, setSavingOps] = useState(false);
  const [opsMsg, setOpsMsg] = useState<string | null>(null);
  // F2-02: caption styling (subtitle on-screen) + hashtag per-niche → channels (brand skin)
  const [cap, setCap] = useState<Record<string, unknown>>(CAP_DEFAULT);
  const [tags, setTags] = useState<Record<string, string>>({}); // niche → "#a, #b" (editing)
  const [savingBrand, setSavingBrand] = useState(false);
  const [brandMsg, setBrandMsg] = useState<string | null>(null);
  // F2-04: branded (CTA/logo/landing) per-channel → channels (DB+BE sudah ada, migr 0015)
  const [ctaMode, setCtaMode] = useState("implicit");
  const [brandName, setBrandName] = useState("");
  const [ctaText, setCtaText] = useState("");
  const [brandLogo, setBrandLogo] = useState("");
  const [logoPos, setLogoPos] = useState("top-right");
  const [logoSize, setLogoSize] = useState(0.12);
  const [logoOpacity, setLogoOpacity] = useState(0.85);
  const [landingLink, setLandingLink] = useState("");
  const [linkPos, setLinkPos] = useState("bottom");
  const [savingBr2, setSavingBr2] = useState(false);
  const [br2Msg, setBr2Msg] = useState<string | null>(null);

  async function saveBranded() {
    setBr2Msg(null); setSavingBr2(true);
    const { error } = await supabase.from("channels").update({
      cta_mode: ctaMode, brand_name: brandName.trim() || null, brand_cta_text: ctaText.trim() || null,
      brand_logo: brandLogo.trim() || null, logo_position: logoPos, logo_size: logoSize, logo_opacity: logoOpacity,
      landing_link: landingLink.trim() || null, link_position: linkPos,
    }).eq("id", id);
    setSavingBr2(false);
    setBr2Msg(error ? `Gagal: ${error.message}` : "Tersimpan");
    if (!error) load();
  }
  const capNum = (k: string, d: number) => Number((cap[k] as number) ?? d);
  const capStr = (k: string, d: string) => String((cap[k] as string) ?? d);

  async function saveBrand() {
    setBrandMsg(null); setSavingBrand(true);
    const nh: Record<string, string[]> = {};
    for (const [n, s] of Object.entries(tags)) {
      const arr = s.split(",").map((t) => t.trim()).filter(Boolean).map((t) => (t.startsWith("#") ? t : `#${t}`));
      if (arr.length) nh[n] = arr;
    }
    const { error } = await supabase.from("channels").update({ caption_style: cap, niche_hashtags: nh }).eq("id", id);
    setSavingBrand(false);
    setBrandMsg(error ? `Gagal: ${error.message}` : "Tersimpan");
    if (!error) load();
  }

  async function saveOps() {
    setOpsMsg(null); setSavingOps(true);
    const { error } = await supabase.from("channels").update({
      image_quality: imgQuality, music_enabled: musicOn, music_volume: musicVol,
      music_default_mood: musicMood.trim() || null,
      script_min_viral_score: minScore, script_max_retry: maxRetry,
    }).eq("id", id);
    setSavingOps(false);
    setOpsMsg(error ? `Gagal: ${error.message}` : "Tersimpan");
    if (!error) load();
  }

  // F2-03 simpan: model+voice → channels (RLS UPDATE). llm_library diturunkan dari provider model LLM.
  async function saveAi() {
    setAiMsg(null); setSavingAi(true);
    const lib = llmOpts.find((m) => m.model_key === llmModel)?.provider_key ?? null;
    const visual_mode = vmode === "ai_image" ? (imgModel ? `ai_image:${imgModel}` : null) : "video";
    const { error } = await supabase.from("channels").update({
      llm_model: llmModel || null, llm_library: lib,
      visual_mode, tts_provider: ttsProv || null, voice_key: voiceKey || null,
    }).eq("id", id);
    setSavingAi(false);
    setAiMsg(error ? `Gagal: ${error.message}` : "Tersimpan");
    if (!error) load();
  }

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

  // YouTube per-channel (migr 0060): connect/status/disconnect ber-scope channels.id ini.
  const [yt, setYt] = useState<{ connected: boolean; has_client: boolean; channel_id: string | null } | null>(null);
  const [ytCid, setYtCid] = useState("");
  const [ytSecret, setYtSecret] = useState("");
  const [ytBusy, setYtBusy] = useState(false);
  const [ytErr, setYtErr] = useState<string | null>(null);

  async function loadYtStatus() {
    try { const r = await fetch(`/api/youtube/status?channel_id=${id}`); setYt(await r.json()); }
    catch { setYt({ connected: false, has_client: false, channel_id: null }); }
  }
  async function connectYt() {
    setYtErr(null);
    if (!ytCid.trim() || !ytSecret.trim()) return setYtErr("Isi Client ID & Client Secret dulu.");
    setYtBusy(true);
    try {
      const r = await fetch("/api/youtube/connect", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: ytCid, client_secret: ytSecret, channel_id: id, ret: `/channels/${id}` }) });
      const j = await r.json();
      if (r.ok && j.authorize_url) { window.location.href = j.authorize_url; return; }
      setYtErr(j.error || "Gagal memulai koneksi."); setYtBusy(false);
    } catch { setYtErr("Server tak terjangkau."); setYtBusy(false); }
  }
  async function disconnectYt() {
    setYtBusy(true);
    try {
      await fetch("/api/youtube/disconnect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ channel_id: id }) });
      await loadYtStatus();
    } finally { setYtBusy(false); }
  }

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

  // F2-07: pause/play (toggle is_active). Play hanya bila readiness lengkap (gerbang aktivasi).
  async function pausePlay(toActive: boolean) {
    setErr(null); setBusy(true);
    if (toActive && rd && !rd.ready) { setBusy(false); setTab("settings"); return setTestMsg("Belum bisa diaktifkan — lengkapi konfigurasi dulu (lihat checklist)."); }
    const { error } = await supabase.from("channels").update({ is_active: toActive }).eq("id", id);
    setBusy(false);
    if (error) return setErr(error.message);
    setActive(toActive); load();
  }

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    const { data } = await supabase.from("channels")
      .select("id,channel_name,platform_channel_id,niche,niche_pool,niche_mode,content_language,is_active,publish_privacy,duration_preset,production_paused,production_paused_reason,llm_model,llm_library,visual_mode,tts_provider,voice_key,image_quality,music_enabled,music_volume,music_default_mood,script_min_viral_score,script_max_retry,caption_style,niche_hashtags,cta_mode,brand_name,brand_cta_text,brand_logo,logo_position,logo_size,logo_opacity,landing_link,link_position")
      .eq("id", id).maybeSingle();
    const c = data as ChannelRow | null;
    setCh(c);
    if (c) {
      setName(c.channel_name ?? ""); setClang(c.content_language ?? "id-ID");
      setPrivacy(c.publish_privacy ?? "private"); setActive(c.is_active ?? true);
      setNicheMode((c.niche_mode === "random" ? "random" : "fixed")); setNiche(c.niche ?? "");
      setDpreset(c.duration_preset ?? null);
      setLlmModel(c.llm_model ?? "");
      const vm = c.visual_mode ?? "";
      if (vm.startsWith("ai_image:")) { setVmode("ai_image"); setImgModel(vm.slice(9)); } else { setVmode("video"); setImgModel(""); }
      setTtsProv(c.tts_provider ?? ""); setVoiceKey(c.voice_key ?? "");
      setImgQuality(c.image_quality ?? "low"); setMusicOn(c.music_enabled ?? false);
      setMusicVol(c.music_volume ?? 0.1); setMusicMood(c.music_default_mood ?? "");
      setMinScore(c.script_min_viral_score ?? 75); setMaxRetry(c.script_max_retry ?? 3);
      setCap({ ...CAP_DEFAULT, ...(c.caption_style && typeof c.caption_style === "object" ? c.caption_style : {}) });
      const nh = (c.niche_hashtags && typeof c.niche_hashtags === "object") ? c.niche_hashtags : {};
      setTags(Object.fromEntries(Object.entries(nh).map(([k, v]) => [k, Array.isArray(v) ? v.join(", ") : ""])));
      setCtaMode(c.cta_mode ?? "implicit"); setBrandName(c.brand_name ?? ""); setCtaText(c.brand_cta_text ?? "");
      setBrandLogo(c.brand_logo ?? ""); setLogoPos(c.logo_position ?? "top-right");
      setLogoSize(c.logo_size ?? 0.12); setLogoOpacity(c.logo_opacity ?? 0.85);
      setLandingLink(c.landing_link ?? ""); setLinkPos(c.link_position ?? "bottom");
    }
    // F2-03: katalog (ai_models/tts_profiles/voice_catalog — RLS read) + voice_defaults niche (pre-fill).
    const { data: am } = await supabase.from("ai_models").select("model_key,provider_key,component,display_name").eq("is_active", true).order("display_name");
    setLlmOpts(((am ?? []) as (ModelOpt & {component:string})[]).filter((m) => m.component === "llm"));
    setImgOpts(((am ?? []) as (ModelOpt & {component:string})[]).filter((m) => m.component === "image"));
    const { data: tp } = await supabase.from("tts_profiles").select("provider_key,display_name").eq("is_active", true);
    setTtsOpts((tp ?? []) as { provider_key: string; display_name: string }[]);
    const { data: vc } = await supabase.from("voice_catalog").select("voice_key,provider_key,display_name,gender").eq("is_active", true).order("sort_order");
    setVoiceAll((vc ?? []) as VoiceOpt[]);
    if (c?.niche) { const { data: nd } = await supabase.from("niches").select("voice_defaults").eq("niche_id", c.niche).maybeSingle(); setNicheDefaults(((nd as { voice_defaults?: Record<string, string> } | null)?.voice_defaults) ?? {}); }
    // F2-07: status efektif → subscription + readiness (RPC tenant-scoped F2-fondasi).
    const { data: cfg } = await supabase.from("tenant_configs").select("plan_type,subscription_status").maybeSingle();
    setSub((cfg as { subscription_status?: string } | null)?.subscription_status ?? null);
    try { const { data: rdd } = await supabase.rpc("channel_readiness", { p_channel_id: id }); if (rdd) setRd(rdd as { ready: boolean; missing: string[] }); } catch { /* non-fatal */ }
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
  // Status YouTube per-channel + tangani kembalinya dari consent (?youtube=connected|error).
  useEffect(() => {
    loadYtStatus();
    const sp = new URLSearchParams(window.location.search);
    const y = sp.get("youtube");
    if (y === "connected") { setYtErr(null); window.history.replaceState({}, "", `/channels/${id}`); loadYtStatus(); }
    else if (y === "error") { setYtErr(`Koneksi gagal: ${sp.get("reason") || "unknown"}`); window.history.replaceState({}, "", `/channels/${id}`); }
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

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
  const eff = effectiveStatus(ch, sub, rd);
  const TONE: Record<string, string> = { ok: "badge-success", warn: "badge-warning", stop: "badge-danger", muted: "badge-default" };

  return (
    <>
      <div className="cd-header">
        <span className="cd-logo-lg" style={{ background: colorFor(ch.id) }}>{initials(name0)}</span>
        <div className="cd-h-meta">
          <h1>{name0} <span className={`badge ${TONE[eff.tone]}`} style={{ fontSize: "var(--text-xs)" }}><span className="dot" /><Bi id={eff.label_id} en={eff.label_en} /></span></h1>
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
          {ch.platform_channel_id && (
            <a className="btn btn-secondary" href={`https://studio.youtube.com/channel/${ch.platform_channel_id}`} target="_blank" rel="noopener noreferrer" title="Kelola di YouTube Studio (tab baru)" style={{ color: "var(--yt)" }}><ExternalLink size={15} /> YouTube Studio</a>
          )}
          {/* F2-07: pause/play (is_active). Play ter-gate readiness. Sembunyikan saat halted/sub (pakai aksi di banner). */}
          {!ch.production_paused && (sub === null || ["active","trialing","trial","grace"].includes(sub)) && (
            ch.is_active
              ? <button className="btn btn-secondary" disabled={busy} onClick={() => pausePlay(false)}><Pause size={15} /> <Bi id="Jeda" en="Pause" /></button>
              : <button className="btn btn-secondary" disabled={busy} onClick={() => pausePlay(true)}><Play size={15} /> <Bi id="Aktifkan" en="Activate" /></button>
          )}
          <button className="btn btn-secondary" onClick={() => setTab("settings")}><Settings size={15} /> <Bi id="Pengaturan" en="Settings" /></button>
          <button className="btn btn-ai" disabled={busy} onClick={testNow} title="Produksi 1 video private untuk preview config"><Zap size={15} /> <Bi id="Test sekarang (private)" en="Test now (private)" /></button>
        </div>
        {testMsg && <div style={{ flexBasis: "100%", fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginTop: ".5rem" }}>{testMsg}</div>}
      </div>

      {/* F2-07/F1-09: banner status efektif — tenant well-informed (alasan + rekomendasi + aksi pemulihan) */}
      {eff.key !== "active" && (
        <div className="card card-pad" style={{ marginBottom: "1rem", borderLeft: `3px solid var(--${eff.tone === "stop" ? "danger" : eff.tone === "warn" ? "warning" : "border"}, #f59e0b)` }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "0.625rem" }}>
            <AlertTriangle size={18} style={{ color: `var(--${eff.tone === "stop" ? "danger" : "warning"}, #f59e0b)`, flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <strong style={{ fontSize: "var(--text-sm)" }}><Bi id={`Status: ${eff.label_id}`} en={`Status: ${eff.label_en}`} /></strong>
              {eff.reason && <div style={{ fontSize: "var(--text-sm)", color: "var(--text-secondary)", marginTop: "0.25rem" }}>{eff.reason}</div>}
              {eff.reco_id && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.35rem" }}><Bi id={eff.reco_id} en={eff.reco_en!} /></div>}
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.625rem", flexWrap: "wrap" }}>
                {eff.key === "halted" && <button className="btn btn-ai btn-sm" disabled={busy} onClick={testNow}><RotateCw size={14} /> <Bi id="Jalankan ulang & pulihkan" en="Run & recover" /></button>}
                {eff.key === "incomplete" && <button className="btn btn-default btn-sm" onClick={() => setTab("settings")}><Settings size={14} /> <Bi id="Lengkapi konfigurasi" en="Complete config" /></button>}
                {eff.key === "paused" && <button className="btn btn-default btn-sm" disabled={busy} onClick={() => pausePlay(true)}><Play size={14} /> <Bi id="Aktifkan" en="Activate" /></button>}
              </div>
            </div>
          </div>
        </div>
      )}

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

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Produksi AI (model & suara)" en="AI production (models & voice)" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}>
            <Bi id="Pilih model AI tiap elemen + suara. Biaya = penyedia AI Anda (BYOK), bukan biaya kami." en="Pick the AI model per element + voice. Cost = your AI provider (BYOK), not our fee." />
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            <div><label className="label"><Bi id="Model LLM (skrip)" en="LLM model (script)" /></label>
              <select className="input" value={llmModel} onChange={(e) => setLlmModel(e.target.value)} style={{ width: "fit-content" }}>
                <option value="">— pilih —</option>
                {llmOpts.map((m) => <option key={m.model_key} value={m.model_key}>{m.display_name}</option>)}
              </select>
            </div>
            <div><label className="label"><Bi id="Visual" en="Visual" /></label>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <select className="input" value={vmode} onChange={(e) => setVmode(e.target.value as "video" | "ai_image")} style={{ width: "fit-content" }}>
                  <option value="video"><Bi id="Stock video" en="Stock video" /></option>
                  <option value="ai_image">AI Image</option>
                </select>
                {vmode === "ai_image" && (
                  <select className="input" value={imgModel} onChange={(e) => setImgModel(e.target.value)} style={{ width: "fit-content" }}>
                    <option value="">— model gambar —</option>
                    {imgOpts.map((m) => <option key={m.model_key} value={m.model_key}>{m.display_name}</option>)}
                  </select>
                )}
              </div>
            </div>
            <div><label className="label"><Bi id="Suara (TTS)" en="Voice (TTS)" /></label>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                <select className="input" value={ttsProv} onChange={(e) => { setTtsProv(e.target.value); setVoiceKey(""); }} style={{ width: "fit-content" }}>
                  <option value="">— provider —</option>
                  {ttsOpts.map((p) => <option key={p.provider_key} value={p.provider_key}>{p.display_name}</option>)}
                </select>
                {ttsProv && (
                  <select className="input" value={voiceKey || nicheDefaults[ttsProv] || ""} onChange={(e) => setVoiceKey(e.target.value)} style={{ width: "fit-content" }}>
                    <option value="">— suara —</option>
                    {voiceAll.filter((v) => v.provider_key === ttsProv).map((v) => <option key={v.voice_key} value={v.voice_key}>{v.display_name}{v.gender ? ` (${v.gender})` : ""}</option>)}
                  </select>
                )}
              </div>
              {ttsProv && !voiceKey && nicheDefaults[ttsProv] && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.35rem" }}><Bi id="Default niche dipakai bila tak diubah." en="Niche default used if unchanged." /></div>}
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.35rem" }}><Bi id="Test/preview suara — segera hadir." en="Voice test/preview — coming soon." /></div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <button className="btn btn-default" onClick={saveAi} disabled={savingAi}>{savingAi ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan produksi AI" en="Save AI production" />}</button>
              {aiMsg && <span style={{ fontSize: "var(--text-sm)", color: aiMsg.includes("Tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{aiMsg}</span>}
            </div>
          </div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Operasional & mutu" en="Operations & quality" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Kendali biaya & mutu output per-channel." en="Per-channel cost & output-quality controls." /></p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            {vmode === "ai_image" && (
              <div><label className="label"><Bi id="Kualitas gambar" en="Image quality" /></label>
                <select className="input" value={imgQuality} onChange={(e) => setImgQuality(e.target.value)} style={{ width: "fit-content" }}>
                  <option value="low"><Bi id="Hemat" en="Low" /></option><option value="medium">Medium</option><option value="high">High</option>
                </select>
                <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.3rem" }}><Bi id="Makin tinggi = makin bagus tapi lebih mahal (biaya provider AI Anda)." en="Higher = better but pricier (your AI provider cost)." /></div>
              </div>
            )}
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: "0.625rem", fontSize: "var(--text-sm)" }}>
                <span className="switch"><input type="checkbox" checked={musicOn} onChange={(e) => setMusicOn(e.target.checked)} /><span className="track" /><span className="thumb" /></span>
                <Bi id="Musik latar" en="Background music" />
              </label>
              {musicOn && (
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center", marginTop: "0.5rem" }}>
                  <label className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Volume" en="Volume" /> {Math.round(musicVol * 100)}%<br /><input type="range" min={0} max={0.5} step={0.01} value={musicVol} onChange={(e) => setMusicVol(parseFloat(e.target.value))} /></label>
                  <div><label className="label" style={{ fontSize: "var(--text-xs)" }}><Bi id="Mood (opsional)" en="Mood (optional)" /></label><input className="input" value={musicMood} onChange={(e) => setMusicMood(e.target.value)} placeholder="auto" style={{ width: 160 }} /></div>
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <div><label className="label"><Bi id="Skor viral min (QC)" en="Min viral score (QC)" /></label><input className="input" type="number" min={0} max={100} value={minScore} onChange={(e) => setMinScore(parseInt(e.target.value) || 0)} style={{ width: 110 }} /></div>
              <div><label className="label"><Bi id="Maks retry skrip" en="Max script retry" /></label><input className="input" type="number" min={0} max={10} value={maxRetry} onChange={(e) => setMaxRetry(parseInt(e.target.value) || 0)} style={{ width: 110 }} /></div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <button className="btn btn-default" onClick={saveOps} disabled={savingOps}>{savingOps ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan operasional" en="Save operations" />}</button>
              {opsMsg && <span style={{ fontSize: "var(--text-sm)", color: opsMsg.includes("Tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{opsMsg}</span>}
            </div>
          </div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Caption & Hashtag" en="Caption & Hashtags" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Tampilan teks subtitle di video + hashtag postingan (brand channel ini)." en="On-screen subtitle styling + post hashtags (this channel's brand)." /></p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <div><label className="label"><Bi id="Font" en="Font" /></label>
                <select className="input" value={capStr("font_name", "Anton")} onChange={(e) => setCap({ ...cap, font_name: e.target.value })} style={{ width: 150 }}>
                  {["Anton", "Montserrat", "Bebas Neue", "Oswald", "Roboto", "Poppins"].map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div><label className="label"><Bi id="Ukuran" en="Size" /></label><input className="input" type="number" min={24} max={120} value={capNum("font_size", 68)} onChange={(e) => setCap({ ...cap, font_size: parseInt(e.target.value) || 68 })} style={{ width: 90 }} /></div>
              <div><label className="label"><Bi id="Posisi Y (%)" en="Position Y (%)" /></label><input className="input" type="number" min={0} max={100} value={capNum("position_y_pct", 83)} onChange={(e) => setCap({ ...cap, position_y_pct: parseInt(e.target.value) || 83 })} style={{ width: 90 }} /></div>
              <div><label className="label"><Bi id="Kata/baris" en="Words/line" /></label><input className="input" type="number" min={1} max={8} value={capNum("max_words_per_line", 3)} onChange={(e) => setCap({ ...cap, max_words_per_line: parseInt(e.target.value) || 3 })} style={{ width: 80 }} /></div>
            </div>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div><label className="label"><Bi id="Warna kata aktif" en="Active word" /></label><input type="color" value={capStr("active_word_color", "#FFD700")} onChange={(e) => setCap({ ...cap, active_word_color: e.target.value })} style={{ width: 48, height: 34, padding: 2 }} /></div>
              <div><label className="label"><Bi id="Warna kata lain" en="Other words" /></label><input type="color" value={capStr("inactive_word_color", "#FFFFFF")} onChange={(e) => setCap({ ...cap, inactive_word_color: e.target.value })} style={{ width: 48, height: 34, padding: 2 }} /></div>
              <div><label className="label"><Bi id="Garis tepi" en="Outline" /></label><input type="color" value={capStr("outline_color", "#000000")} onChange={(e) => setCap({ ...cap, outline_color: e.target.value })} style={{ width: 48, height: 34, padding: 2 }} /></div>
              <div><label className="label"><Bi id="Tebal tepi" en="Outline px" /></label><input className="input" type="number" min={0} max={12} value={capNum("outline", 4)} onChange={(e) => setCap({ ...cap, outline: parseInt(e.target.value) || 0 })} style={{ width: 80 }} /></div>
              <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "var(--text-sm)" }}>
                <span className="switch"><input type="checkbox" checked={Boolean(cap.bold ?? true)} onChange={(e) => setCap({ ...cap, bold: e.target.checked })} /><span className="track" /><span className="thumb" /></span><Bi id="Tebal" en="Bold" />
              </label>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "0.875rem" }}>
              <label className="label"><Bi id="Hashtag per niche" en="Hashtags per niche" /></label>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.5rem" }}><Bi id="Pisahkan dengan koma. Tanda # otomatis." en="Comma-separated. # added automatically." /></div>
              {(nicheMode === "fixed" ? (niche ? [{ id: niche, name: nicheOpts.find((o) => o.id === niche)?.name ?? niche }] : []) : nicheOpts).map((n) => (
                <div key={n.id} style={{ marginBottom: "0.5rem" }}>
                  <label className="muted" style={{ fontSize: "var(--text-xs)" }}>{n.name}</label>
                  <input className="input" value={tags[n.id] ?? ""} onChange={(e) => setTags({ ...tags, [n.id]: e.target.value })} placeholder="space, science, viral" />
                </div>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <button className="btn btn-default" onClick={saveBrand} disabled={savingBrand}>{savingBrand ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan caption & hashtag" en="Save caption & hashtags" />}</button>
              {brandMsg && <span style={{ fontSize: "var(--text-sm)", color: brandMsg.includes("Tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{brandMsg}</span>}
            </div>
          </div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Branded (CTA · logo · link)" en="Branded (CTA · logo · link)" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Sentuhan brand opsional di video & deskripsi (semua boleh kosong = tanpa branding)." en="Optional brand touches in video & description (all blank = no branding)." /></p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
            <div><label className="label">CTA</label>
              <select className="input" value={ctaMode} onChange={(e) => setCtaMode(e.target.value)} style={{ width: "fit-content" }}>
                <option value="implicit"><Bi id="Implicit (tanpa sebut brand)" en="Implicit (no brand mention)" /></option>
                <option value="soft_sell"><Bi id="Soft-sell (sebut brand halus)" en="Soft-sell (subtle brand mention)" /></option>
              </select>
            </div>
            {ctaMode === "soft_sell" && (
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                <div><label className="label"><Bi id="Nama brand" en="Brand name" /></label><input className="input" value={brandName} onChange={(e) => setBrandName(e.target.value)} style={{ width: 200 }} /></div>
                <div><label className="label"><Bi id="Teks CTA" en="CTA text" /></label><input className="input" value={ctaText} onChange={(e) => setCtaText(e.target.value)} placeholder="Follow for more" style={{ width: 220 }} /></div>
              </div>
            )}
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "0.875rem" }}>
              <label className="label"><Bi id="Logo (URL gambar) — overlay di video" en="Logo (image URL) — video overlay" /></label>
              <input className="input input-mono" value={brandLogo} onChange={(e) => setBrandLogo(e.target.value)} placeholder="https://… .png" />
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.3rem" }}><Bi id="Tempel URL logo (PNG transparan disarankan). Upload file langsung — segera hadir." en="Paste logo URL (transparent PNG recommended). Direct file upload — coming soon." /></div>
              {brandLogo && (
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "flex-end", marginTop: "0.625rem" }}>
                  <div><label className="label" style={{ fontSize: "var(--text-xs)" }}><Bi id="Posisi" en="Position" /></label>
                    <select className="input" value={logoPos} onChange={(e) => setLogoPos(e.target.value)} style={{ width: 140 }}>
                      {[["top-left", "Kiri atas"], ["top-right", "Kanan atas"], ["bottom-left", "Kiri bawah"], ["bottom-right", "Kanan bawah"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select></div>
                  <label className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Ukuran" en="Size" /> {Math.round(logoSize * 100)}%<br /><input type="range" min={0.05} max={0.3} step={0.01} value={logoSize} onChange={(e) => setLogoSize(parseFloat(e.target.value))} /></label>
                  <label className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Opasitas" en="Opacity" /> {Math.round(logoOpacity * 100)}%<br /><input type="range" min={0.2} max={1} step={0.05} value={logoOpacity} onChange={(e) => setLogoOpacity(parseFloat(e.target.value))} /></label>
                </div>
              )}
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "0.875rem", display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ flex: 1, minWidth: 220 }}><label className="label"><Bi id="Link landing (deskripsi)" en="Landing link (description)" /></label><input className="input input-mono" value={landingLink} onChange={(e) => setLandingLink(e.target.value)} placeholder="https://…" /></div>
              <div><label className="label"><Bi id="Posisi link" en="Link position" /></label>
                <select className="input" value={linkPos} onChange={(e) => setLinkPos(e.target.value)} style={{ width: 110 }}><option value="top"><Bi id="Atas" en="Top" /></option><option value="bottom"><Bi id="Bawah" en="Bottom" /></option></select></div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <button className="btn btn-default" onClick={saveBranded} disabled={savingBr2}>{savingBr2 ? <Loader2 size={15} className="spin" /> : <Bi id="Simpan branded" en="Save branded" />}</button>
              {br2Msg && <span style={{ fontSize: "var(--text-sm)", color: br2Msg.includes("Tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{br2Msg}</span>}
            </div>
          </div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Koneksi YouTube" en="YouTube connection" /></h3>
          {yt?.connected ? (
            <>
              <p style={{ fontSize: "var(--text-sm)", marginBottom: "0.75rem" }}><Check size={14} style={{ color: "var(--success)", verticalAlign: -2 }} /> <Bi id="Tersambung" en="Connected" />{yt.channel_id ? ` · ${yt.channel_id}` : ""}</p>
              <button className="btn btn-secondary btn-sm" onClick={disconnectYt} disabled={ytBusy}>{ytBusy ? <Loader2 size={14} className="spin" /> : <Bi id="Putuskan" en="Disconnect" />}</button>
            </>
          ) : (
            <>
              <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "0.75rem" }}><Bi id="Hubungkan channel INI ke akun YouTube-nya (OAuth) agar bisa auto-publish. Tiap channel = koneksi sendiri." en="Connect THIS channel to its YouTube account (OAuth) for auto-publish. Each channel = its own connection." /></p>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: 460 }}>
                <input className="input input-mono" placeholder="Google Client ID" value={ytCid} onChange={(e) => setYtCid(e.target.value)} />
                <input className="input input-mono" type="password" placeholder="Google Client Secret" value={ytSecret} onChange={(e) => setYtSecret(e.target.value)} />
                <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Daftarkan Redirect URI ini di OAuth app Anda: " en="Register this Redirect URI in your OAuth app: " /><code>{process.env.NEXT_PUBLIC_YT_REDIRECT_URI || "(lihat dokumentasi)"}</code></div>
                <button className="btn btn-default btn-sm" style={{ width: "fit-content" }} onClick={connectYt} disabled={ytBusy}>{ytBusy ? <Loader2 size={14} className="spin" /> : <><ExternalLink size={14} /> <Bi id="Hubungkan via Google" en="Connect via Google" /></>}</button>
              </div>
            </>
          )}
          {ytErr && <div style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-sm)", marginTop: "0.5rem" }}>{ytErr}</div>}
        </div>
        </>
      )}
    </>
  );
}
