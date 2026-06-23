"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ExternalLink, Settings, Zap, ArrowRight, BarChart3, Calendar, Activity, Loader2, Check, Pause, Play, RotateCw, AlertTriangle, Mic, ShieldCheck, Sparkles, Clock, Trash2, Plus } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import PresetTables from "@/components/preset-tables";
import { ComplianceView, type Compliance } from "@/components/compliance-view";
import { InsightsView, type Insights } from "@/components/insights-view";
import "./channel-detail.css";

// F2-13b: status produksi → label + varian badge design-system (tab Runs).
const RUN_ST: Record<string, [string, string, string]> = {
  success: ["Sukses", "Success", "badge-success"], failed: ["Gagal", "Failed", "badge-danger"],
  qc_failed: ["QC gagal", "QC failed", "badge-warning"], ready_with_issues: ["Perlu tinjau", "Needs review", "badge-warning"],
  running: ["Berjalan", "Running", "badge-brand"], queued: ["Antre", "Queued", "badge-default"],
};

// D3 Channel Detail — Phase 9.3 (wired Supabase v2, anon + RLS).
// Header + Settings = data NYATA (read channels by id, write via channels RLS UPDATE — tanpa kolom
// privilege jadi aman client-side, no RPC). KPI/Overview/Runs/Analytics/Schedule = placeholder JUJUR
// (timeseries di-wire 9.4 analytics; Runs nyata di D4/D5; slot-model saat D7). Niche dikelola di Config→Niches.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type ChannelRow = {
  id: string; channel_name: string | null; platform_channel_id: string | null; subscriber_count: number | null;
  niche: string | null; niche_pool: string[] | null; niche_mode: string | null; content_language: string | null;
  is_active: boolean | null; publish_privacy: string | null; duration_preset: number | null; publish_slots: string[] | null;
  production_paused: boolean | null; production_paused_reason: string | null;
  llm_model: string | null; llm_library: string | null; visual_mode: string | null;
  tts_provider: string | null; tts_model: string | null; voice_key: string | null;
  llm_account_id: string | null; tts_account_id: string | null; image_account_id: string | null;
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
type VoiceOpt = { voice_key: string; provider_key: string; display_name: string; gender: string | null; preview_url: string | null };

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
// Urutan tab = PROCESS FLOW (§10.F): siapkan → jadwalkan → produksi → pantau.
const TABS: [string, string, string][] = [["overview", "Overview", "Overview"], ["settings", "Pengaturan", "Settings"], ["schedule", "Jadwal", "Schedule"], ["runs", "Runs", "Runs"], ["analytics", "Analytics", "Analytics"], ["compliance", "Kepatuhan", "Compliance"], ["insights", "Wawasan", "Insights"]];

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
  // F2-13b: data per-channel utk tab (channel_insights + production_runs + publish_slots)
  const [chCmp, setChCmp] = useState<Compliance | null>(null);
  const [chIns, setChIns] = useState<Insights | null>(null);
  const [chRuns, setChRuns] = useState<{ id: string; status: string; niche: string | null; topic: string | null; created_at: string }[]>([]);
  const [slots, setSlots] = useState<string[]>([]);
  const [newSlot, setNewSlot] = useState("");
  const [slotMsg, setSlotMsg] = useState<string | null>(null);
  const [savingSlot, setSavingSlot] = useState(false);
  const [totalVids, setTotalVids] = useState<number | null>(null);  // video produksi sukses channel ini
  // F2-03: pemilih AI per-channel (model + voice). Katalog dari ai_models/tts_profiles/voice_catalog (RLS read).
  const [llmOpts, setLlmOpts] = useState<ModelOpt[]>([]);
  const [imgOpts, setImgOpts] = useState<ModelOpt[]>([]);
  const [ttsOpts, setTtsOpts] = useState<{ provider_key: string; display_name: string }[]>([]);
  const [ttsModelOpts, setTtsModelOpts] = useState<{ model_key: string; display_name: string; provider_key: string }[]>([]);  // ai_models component='tts' (migr 0087)
  const [voiceAll, setVoiceAll] = useState<VoiceOpt[]>([]);
  const [llmModel, setLlmModel] = useState("");
  const [vmode, setVmode] = useState<"video" | "ai_image">("video");
  const [imgModel, setImgModel] = useState("");
  const [ttsProv, setTtsProv] = useState("");
  const [ttsModel, setTtsModel] = useState("");  // model TTS dipilih tenant (eleven_turbo/multilingual/flash; tts-1/hd)
  const [voiceKey, setVoiceKey] = useState("");
  const [savingAi, setSavingAi] = useState(false);
  const [aiMsg, setAiMsg] = useState<string | null>(null);
  // F2-09: akun VAULT per-elemen (assign ke channel + tambah akun baru). account_id NULL → key default tenant (fallback BE).
  const [accounts, setAccounts] = useState<{ id: string; component: string; label: string }[]>([]);
  const [llmAcct, setLlmAcct] = useState(""); const [ttsAcct, setTtsAcct] = useState(""); const [imageAcct, setImageAcct] = useState("");
  const [addAcct, setAddAcct] = useState<{ component: string; label: string; key: string } | null>(null);
  const [addBusy, setAddBusy] = useState(false); const [addMsg, setAddMsg] = useState<string | null>(null);
  async function loadAccounts() {
    const { data } = await supabase.from("tenant_api_accounts").select("id,component,label").eq("status", "active").order("created_at");
    setAccounts((data ?? []) as { id: string; component: string; label: string }[]);
  }
  async function submitAddAcct() {
    if (!addAcct || !addAcct.key.trim()) return;
    setAddBusy(true); setAddMsg(null);
    try {
      const r = await fetch("/api/accounts/set", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ component: addAcct.component, label: addAcct.label, key: addAcct.key }) });
      const j = await r.json();
      if (!r.ok) { setAddMsg(j.error || "Gagal"); setAddBusy(false); return; }
      await loadAccounts();
      const c = addAcct.component;
      if (j.id) { if (c === "llm") setLlmAcct(j.id); else if (c === "tts") setTtsAcct(j.id); else if (c === "image") setImageAcct(j.id); }
      setAddAcct(null);
    } catch { setAddMsg("Server tak terjangkau"); }
    finally { setAddBusy(false); }
  }
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
      music_enabled: musicOn, music_volume: musicVol,
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
      visual_mode, image_quality: imgQuality, tts_provider: ttsProv || null, tts_model: ttsModel || null, voice_key: voiceKey || null,
      llm_account_id: llmAcct || null, tts_account_id: ttsAcct || null, image_account_id: imageAcct || null,
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

  // F2-08: koneksi YouTube/Google diatur TENANT-level di menu Integrasi (/integrations).
  // Channel HANYA pilih TARGET = youtube channel id yang dipublish (channels.platform_channel_id).
  const [targetYt, setTargetYt] = useState("");
  const [savingTarget, setSavingTarget] = useState(false);
  const [targetMsg, setTargetMsg] = useState<string | null>(null);
  async function saveTarget() {
    setTargetMsg(null); setSavingTarget(true);
    const { error } = await supabase.from("channels").update({ platform_channel_id: targetYt.trim() || null }).eq("id", id);
    setSavingTarget(false);
    setTargetMsg(error ? `Gagal: ${error.message}` : "Target tersimpan");
    if (!error) load();
  }

  async function savePreset() {
    setPresetMsg(null); setSavingPreset(true);
    const { error } = await supabase.from("channels").update({ duration_preset: dpreset }).eq("id", id);
    setSavingPreset(false);
    setPresetMsg(error ? `Gagal: ${error.message}` : "Durasi tersimpan");
    if (!error) load();
  }

  // F2-13b: jadwal publish per-channel (RPC set_channel_publish_slots — sama dgn MAIN /jadwal, scope channel ini).
  async function saveSlots(next: string[]) {
    setSavingSlot(true); setSlotMsg(null);
    const sorted = Array.from(new Set(next.map((t) => t.trim()).filter(Boolean))).sort();
    const { error } = await supabase.rpc("set_channel_publish_slots", { p_channel_id: id, p_slots: sorted });
    setSavingSlot(false);
    if (error) { setSlotMsg(`Gagal: ${error.message}`); return; }
    setSlots(sorted); setSlotMsg("Jadwal tersimpan");
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
      .select("id,channel_name,platform_channel_id,subscriber_count,niche,niche_pool,niche_mode,content_language,is_active,publish_privacy,duration_preset,publish_slots,production_paused,production_paused_reason,llm_model,llm_library,visual_mode,tts_provider,tts_model,voice_key,image_quality,music_enabled,music_volume,music_default_mood,script_min_viral_score,script_max_retry,llm_account_id,tts_account_id,image_account_id,caption_style,niche_hashtags,cta_mode,brand_name,brand_cta_text,brand_logo,logo_position,logo_size,logo_opacity,landing_link,link_position")
      .eq("id", id).maybeSingle();
    const c = data as ChannelRow | null;
    setCh(c);
    if (c) {
      setName(c.channel_name ?? ""); setClang(c.content_language ?? "id-ID");
      setPrivacy(c.publish_privacy ?? "private"); setActive(c.is_active ?? true);
      setNicheMode((c.niche_mode === "random" ? "random" : "fixed")); setNiche(c.niche ?? "");
      setDpreset(c.duration_preset ?? null); setSlots(c.publish_slots ?? []); setTargetYt(c.platform_channel_id ?? "");
      setLlmModel(c.llm_model ?? "");
      const vm = c.visual_mode ?? "";
      if (vm.startsWith("ai_image:")) { setVmode("ai_image"); setImgModel(vm.slice(9)); } else { setVmode("video"); setImgModel(""); }
      setTtsProv(c.tts_provider ?? ""); setTtsModel(c.tts_model ?? ""); setVoiceKey(c.voice_key ?? "");
      setLlmAcct(c.llm_account_id ?? ""); setTtsAcct(c.tts_account_id ?? ""); setImageAcct(c.image_account_id ?? "");
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
    // F2-03: katalog (ai_models/tts_profiles/voice_catalog — RLS read). Voice = CHANNEL (§10.B FINAL); tanpa pre-fill niche.
    const { data: am } = await supabase.from("ai_models").select("model_key,provider_key,component,display_name").eq("is_active", true).order("display_name");
    setLlmOpts(((am ?? []) as (ModelOpt & {component:string})[]).filter((m) => m.component === "llm"));
    setImgOpts(((am ?? []) as (ModelOpt & {component:string})[]).filter((m) => m.component === "image"));
    setTtsModelOpts(((am ?? []) as { model_key: string; display_name: string; provider_key: string; component: string }[]).filter((m) => m.component === "tts"));
    const { data: tp } = await supabase.from("tts_profiles").select("provider_key,display_name").eq("is_active", true);
    setTtsOpts((tp ?? []) as { provider_key: string; display_name: string }[]);
    const { data: vc } = await supabase.from("voice_catalog").select("voice_key,provider_key,display_name,gender,preview_url").eq("is_active", true).order("sort_order");
    setVoiceAll((vc ?? []) as VoiceOpt[]);
    const { data: accs } = await supabase.from("tenant_api_accounts").select("id,component,label").eq("status", "active").order("created_at");
    setAccounts((accs ?? []) as { id: string; component: string; label: string }[]);
    // F2-07: status efektif → subscription + readiness (RPC tenant-scoped F2-fondasi).
    const { data: cfg } = await supabase.from("tenant_configs").select("plan_type,subscription_status").maybeSingle();
    setSub((cfg as { subscription_status?: string } | null)?.subscription_status ?? null);
    try { const { data: rdd } = await supabase.rpc("channel_readiness", { p_channel_id: id }); if (rdd) setRd(rdd as { ready: boolean; missing: string[] }); } catch { /* non-fatal */ }
    // F2-13b: insight per-channel (channel_insights by channel_id) + runs per-channel (production_runs).
    const { data: ci } = await supabase.from("channel_insights")
      .select("compliance,performance_grade,videos_analyzed,niche_weights,top_hooks,avoid_patterns,computed_at")
      .eq("channel_id", id).order("computed_at", { ascending: false }).limit(1).maybeSingle();
    if (ci) {
      setChCmp(((ci as { compliance?: Compliance }).compliance) ?? null);
      setChIns(ci as unknown as Insights);
    } else { setChCmp(null); setChIns(null); }
    const { data: pr } = await supabase.from("production_runs")
      .select("id,status,niche,topic,created_at").eq("channel_id", id).order("created_at", { ascending: false }).limit(60);
    setChRuns((pr ?? []) as { id: string; status: string; niche: string | null; topic: string | null; created_at: string }[]);
    // Total video per-channel = produksi SUKSES (production_runs.channel_id terisi 100%; akurat).
    const { count: vCount } = await supabase.from("production_runs").select("id", { count: "exact", head: true }).eq("channel_id", id).eq("status", "success");
    setTotalVids(vCount ?? 0);
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
            {/* Total video + Subscribers = NYATA per-channel. Views/Engagement = metrik YouTube → tab Analytics/Studio; per-channel menunggu backfill video_analytics.channel_id (F1-06). */}
            <div className="item"><div className="v">{totalVids != null ? totalVids.toLocaleString("id-ID") : "—"}</div><div className="l"><Bi id="Total video" en="Total videos" /></div></div>
            <div className="item"><div className="v">{ch.subscriber_count != null ? ch.subscriber_count.toLocaleString("id-ID") : "—"}</div><div className="l">Subscribers</div></div>
            <div className="item" title="Metrik YouTube — buka YouTube Studio (tab Analytics). Per-channel menunggu F1-06."><div className="v">—</div><div className="l"><Bi id="Views bulan ini" en="Views this month" /></div></div>
            <div className="item" title="Metrik YouTube — buka YouTube Studio (tab Analytics). Per-channel menunggu F1-06."><div className="v">—</div><div className="l"><Bi id="Avg engagement" en="Avg engagement" /></div></div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {/* Tombol YouTube Studio dipindah ke tab Analytics (F2-13b) — tak lagi di header (buang duplikat). */}
          {/* F2-07: pause/play (is_active). Play ter-gate readiness. Sembunyikan saat halted/sub (pakai aksi di banner). */}
          {!ch.production_paused && (sub === null || ["active","trialing","trial","grace"].includes(sub)) && (
            ch.is_active
              ? <button className="btn btn-secondary" disabled={busy} onClick={() => pausePlay(false)}><Pause size={15} /> <Bi id="Jeda" en="Pause" /></button>
              : <button className="btn btn-secondary" disabled={busy} onClick={() => pausePlay(true)}><Play size={15} /> <Bi id="Aktifkan" en="Activate" /></button>
          )}
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
        <div style={{ display: "grid", gap: "1rem" }}>
          {/* Kesiapan channel — data NYATA dari RPC channel_readiness (rd) */}
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <ShieldCheck size={18} style={{ color: "var(--brand)" }} /> <Bi id="Kesiapan channel" en="Channel readiness" />
            </h3>
            {rd == null ? (
              <p className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Memeriksa kesiapan…" en="Checking readiness…" /></p>
            ) : rd.ready ? (
              <p style={{ fontSize: "var(--text-sm)", color: "var(--success)", display: "flex", alignItems: "center", gap: "0.4rem", margin: 0 }}>
                <Check size={15} /> <Bi id="Semua syarat lengkap — channel siap diaktifkan." en="All requirements met — channel is ready to activate." />
              </p>
            ) : (
              <>
                <p className="muted" style={{ fontSize: "var(--text-sm)", marginTop: 0, marginBottom: "0.625rem" }}><Bi id="Lengkapi item berikut agar channel bisa aktif:" en="Complete these to activate the channel:" /></p>
                <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                  {rd.missing.map((m) => (
                    <li key={m} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", padding: "0.3rem 0" }}>
                      <AlertTriangle size={14} style={{ color: "var(--warning)", flexShrink: 0 }} /> <span>{m}</span>
                    </li>
                  ))}
                </ul>
                <button className="btn btn-default btn-sm" style={{ marginTop: "0.75rem" }} onClick={() => setTab("settings")}><Settings size={14} /> <Bi id="Lengkapi di Pengaturan" en="Complete in Settings" /></button>
              </>
            )}
          </div>
          {/* Ringkasan kinerja — KPI nyata di header; kinerja-mesin menyusul (F5-05/F2-13) */}
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}><Activity size={18} /> <Bi id="Ringkasan kinerja" en="Performance summary" /></h3>
            <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}><Bi id="Statistik muncul setelah channel berproduksi. Detail per-channel ada di tab Analytics · Compliance · Wawasan." en="Stats appear once the channel produces. Per-channel detail lives in the Analytics · Compliance · Insights tabs." /></p>
          </div>
        </div>
      )}
      {tab === "runs" && (
        chRuns.length === 0
          ? <Placeholder icon={<BarChart3 size={32} />} idT="Belum ada run untuk channel ini." enT="No runs for this channel yet." />
          : <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
              <thead><tr><th>Status</th><th>Niche</th><th>Topik</th><th>Waktu</th></tr></thead>
              <tbody>{chRuns.map((r) => { const st = RUN_ST[r.status] ?? [r.status, r.status, "badge-default"]; return (
                <tr key={r.id}>
                  <td><span className={`badge ${st[2]}`}><span className="dot" /><Bi id={st[0]} en={st[1]} /></span></td>
                  <td className="muted">{r.niche ?? "—"}</td>
                  <td style={{ color: "var(--text-primary)", maxWidth: 360 }}>{r.topic ?? "—"}</td>
                  <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{new Date(r.created_at).toLocaleString("id-ID")}</td>
                </tr>); })}</tbody>
            </table></div></div>
      )}
      {tab === "analytics" && (
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Bi id="Kinerja mesin — channel ini" en="Engine performance — this channel" /></h3>
          {(() => { const tot = chRuns.length, ok = chRuns.filter((r) => r.status === "success").length, qc = chRuns.filter((r) => r.status === "qc_failed" || r.status === "ready_with_issues").length, fail = chRuns.filter((r) => r.status === "failed").length;
            return (<div className="cd-kpi-strip">
              <div className="item"><div className="v">{tot}</div><div className="l"><Bi id="Total run" en="Total runs" /></div></div>
              <div className="item"><div className="v">{tot ? Math.round((ok / tot) * 100) : 0}%</div><div className="l"><Bi id="Success rate" en="Success rate" /></div></div>
              <div className="item"><div className="v">{qc}</div><div className="l"><Bi id="Perlu tinjau / QC" en="Review / QC" /></div></div>
              <div className="item"><div className="v">{fail}</div><div className="l"><Bi id="Gagal" en="Failed" /></div></div>
            </div>); })()}
          <p className="muted" style={{ fontSize: "var(--text-sm)", margin: "0.875rem 0 0.625rem" }}><Bi id="Metrik YouTube mentah (views/retensi/subscriber) ada di YouTube Studio — kami tak menduplikasinya (kpt 12)." en="Raw YouTube metrics (views/retention/subscribers) live in YouTube Studio — we don't duplicate them." /></p>
          {ch.platform_channel_id && <a className="btn btn-secondary btn-sm" style={{ color: "var(--yt)" }} href={`https://studio.youtube.com/channel/${ch.platform_channel_id}`} target="_blank" rel="noopener noreferrer"><ExternalLink size={14} /> YouTube Studio</a>}
        </div>
      )}
      {tab === "compliance" && (
        <ComplianceView compliance={chCmp} loading={loading} hasRow={!!chCmp} showEdu={false} />
      )}
      {tab === "insights" && (
        <InsightsView insights={chIns} loading={loading} scopeLabel={{ id: "channel ini", en: "this channel" }} />
      )}
      {tab === "schedule" && (
        <div className="card card-pad" style={{ maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Jadwal publish — channel ini" en="Publish schedule — this channel" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Jam publish harian (zona tenant). Bisa juga diatur di menu Jadwal (semua channel)." en="Daily publish times (tenant timezone). Also editable in the Schedule menu (all channels)." /></p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
            {slots.length === 0 && <span className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Belum ada slot." en="No slots yet." /></span>}
            {slots.map((t) => (<span key={t} className="chip"><Clock size={12} /> {t} <span className="x" onClick={() => saveSlots(slots.filter((s) => s !== t))}><Trash2 size={12} /></span></span>))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input type="time" className="input" style={{ width: "fit-content" }} value={newSlot} onChange={(e) => setNewSlot(e.target.value)} />
            <button className="btn btn-secondary btn-sm" disabled={savingSlot || !newSlot} onClick={() => { if (newSlot) { saveSlots([...slots, newSlot]); setNewSlot(""); } }}><Plus size={14} /> <Bi id="Tambah slot" en="Add slot" /></button>
            {savingSlot && <Loader2 size={14} className="spin" />}
            {slotMsg && <span style={{ fontSize: "var(--text-xs)", color: slotMsg.includes("tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{slotMsg}</span>}
          </div>
        </div>
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
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Produksi AI — siapa yang membuat video Anda" en="AI production — who makes your video" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "0.5rem" }}>
            <Bi id="Tiap bagian video dikerjakan oleh AI. Pilih AI-nya, lalu tempel kunci akun AI Anda di tiap bagian." en="Each part of your video is made by AI. Pick the AI, then paste your AI account key in each part." />
          </p>
          <div className="tip" style={{ fontSize: "var(--text-xs)", marginBottom: "1rem" }}>
            <Bi id="💡 Biaya AI ditagih langsung ke akun penyedia Anda (BYOK) — bukan ke kami. Kosongkan kunci untuk memakai kunci default akun Anda." en="💡 AI cost is billed directly to your provider account (BYOK) — not to us. Leave a key empty to use your account default key." />
          </div>

          {/* ✍️ PENULIS NASKAH (LLM) */}
          <div style={{ fontWeight: 700, fontSize: "var(--text-sm)" }}>✍️ <Bi id="Penulis naskah" en="Script writer" /></div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", margin: "0.15rem 0 0.6rem" }}><Bi id="AI yang menulis cerita & narasi video. Makin pintar = naskah makin bagus (biaya sedikit lebih tinggi)." en="The AI that writes your video's story & narration. Smarter = better script (slightly pricier)." /></div>
          <div className="fld-row"><div className="k"><Bi id="Pilihan AI" en="Choose AI" /></div>
            <div className="radio-row">{llmOpts.map((m) => <span key={m.model_key} className={`radio-pill${llmModel === m.model_key ? " sel" : ""}`} onClick={() => setLlmModel(m.model_key)}>{m.display_name}</span>)}</div></div>
          <div className="fld-row"><div className="k"><Bi id="Kunci akun" en="Account key" /><div className="sub"><Bi id="akun AI Anda untuk penulis naskah" en="your AI account for the writer" /></div></div>
            <div className="radio-row">
              {accounts.filter((a) => a.component === "llm").map((a) => <span key={a.id} className={`radio-pill${llmAcct === a.id ? " sel" : ""}`} onClick={() => setLlmAcct(a.id)}>{a.label}</span>)}
              {llmAcct && <span className="radio-pill" onClick={() => setLlmAcct("")} title="pakai kunci default akun Anda"><Bi id="kunci default" en="default key" /></span>}
              <span className="radio-pill" onClick={() => setAddAcct({ component: "llm", label: "", key: "" })}><Plus size={12} /> <Bi id="Tambah kunci" en="Add key" /></span>
            </div></div>

          {/* 🖼️ VISUAL */}
          <div style={{ borderTop: "1px solid var(--border-subtle)", fontWeight: 700, fontSize: "var(--text-sm)", marginTop: "1rem", paddingTop: "1rem" }}>🖼️ <Bi id="Visual (gambar adegan)" en="Visuals (scene images)" /></div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", margin: "0.15rem 0 0.6rem" }}><Bi id="Sumber gambar tiap adegan: pakai video stok, atau biarkan AI menggambar." en="Source for each scene: use stock video, or let AI draw the images." /></div>
          <div className="fld-row"><div className="k"><Bi id="Jenis visual" en="Visual type" /></div>
            <div className="radio-row">{(["video", "ai_image"] as const).map((m) => <span key={m} className={`radio-pill${vmode === m ? " sel" : ""}`} onClick={() => setVmode(m)}><Bi id={m === "video" ? "Video stok" : "Gambar AI"} en={m === "video" ? "Stock video" : "AI image"} /></span>)}</div></div>
          {vmode === "ai_image" && <>
            <div className="fld-row"><div className="k"><Bi id="Pilihan AI gambar" en="Choose image AI" /></div>
              <div className="radio-row">{imgOpts.map((m) => <span key={m.model_key} className={`radio-pill${imgModel === m.model_key ? " sel" : ""}`} onClick={() => setImgModel(m.model_key)}>{m.display_name}</span>)}</div></div>
            <div className="fld-row"><div className="k"><Bi id="Kualitas gambar" en="Image quality" /><div className="sub"><Bi id="makin tinggi makin bagus & makin mahal" en="higher = nicer & pricier" /></div></div>
              <div className="radio-row">{([["low", "Hemat", "Saver"], ["medium", "Seimbang", "Balanced"], ["high", "Terbaik", "Best"]] as [string, string, string][]).map(([q, idL, enL]) => <span key={q} className={`radio-pill${imgQuality === q ? " sel" : ""}`} onClick={() => setImgQuality(q)}><Bi id={idL} en={enL} /></span>)}</div></div>
            <div className="fld-row"><div className="k"><Bi id="Kunci akun" en="Account key" /><div className="sub"><Bi id="akun AI Anda untuk gambar" en="your AI account for images" /></div></div>
              <div className="radio-row">
                {accounts.filter((a) => a.component === "image").map((a) => <span key={a.id} className={`radio-pill${imageAcct === a.id ? " sel" : ""}`} onClick={() => setImageAcct(a.id)}>{a.label}</span>)}
                {imageAcct && <span className="radio-pill" onClick={() => setImageAcct("")} title="pakai kunci default akun Anda"><Bi id="kunci default" en="default key" /></span>}
                <span className="radio-pill" onClick={() => setAddAcct({ component: "image", label: "", key: "" })}><Plus size={12} /> <Bi id="Tambah kunci" en="Add key" /></span>
              </div></div>
          </>}

          {/* 🎙️ SUARA NARATOR (TTS) */}
          <div style={{ borderTop: "1px solid var(--border-subtle)", fontWeight: 700, fontSize: "var(--text-sm)", marginTop: "1rem", paddingTop: "1rem" }}>🎙️ <Bi id="Suara narator" en="Narrator voice" /></div>
          <div className="muted" style={{ fontSize: "var(--text-xs)", margin: "0.15rem 0 0.6rem" }}><Bi id="Suara yang membacakan narasi: pilih penyedia → model → karakter suara (▶ untuk dengar contoh)." en="The voice that reads your narration: pick provider → model → character (▶ to preview)." /></div>
          <div className="fld-row"><div className="k"><Bi id="Penyedia suara" en="Voice provider" /></div>
            <div className="radio-row">{ttsOpts.map((p) => <span key={p.provider_key} className={`radio-pill${ttsProv === p.provider_key ? " sel" : ""}`} onClick={() => { setTtsProv(p.provider_key); setTtsModel(""); setVoiceKey(""); }}>{p.display_name}</span>)}</div></div>
          {ttsProv && ttsModelOpts.filter((m) => m.provider_key === ttsProv).length > 0 && (
            <div className="fld-row"><div className="k"><Bi id="Model suara" en="Voice model" /><div className="sub"><Bi id="kualitas vs kecepatan" en="quality vs speed" /></div></div>
              <div className="radio-row">{ttsModelOpts.filter((m) => m.provider_key === ttsProv).map((m) => <span key={m.model_key} className={`radio-pill${ttsModel === m.model_key ? " sel" : ""}`} onClick={() => setTtsModel(m.model_key)}>{m.display_name}</span>)}</div></div>
          )}
          {ttsProv && (
            <div className="fld-row"><div className="k"><Bi id="Karakter suara" en="Voice character" /></div>
              <div className="radio-row">{voiceAll.filter((v) => v.provider_key === ttsProv).map((v) => <span key={v.voice_key} className={`radio-pill${(voiceKey || "") === v.voice_key ? " sel" : ""}`} onClick={() => setVoiceKey(v.voice_key)}><Mic size={13} />{v.display_name}{v.gender ? ` · ${v.gender}` : ""}{v.preview_url ? <span title="Dengar contoh" style={{ cursor: "pointer", marginLeft: 4 }} onClick={(e) => { e.stopPropagation(); new Audio(v.preview_url as string).play().catch(() => {}); }}>▶</span> : null}</span>)}</div></div>
          )}
          {ttsProv && (
            <div className="fld-row"><div className="k"><Bi id="Kunci akun" en="Account key" /><div className="sub"><Bi id="akun AI Anda untuk suara" en="your AI account for voice" /></div></div>
              <div className="radio-row">
                {accounts.filter((a) => a.component === "tts").map((a) => <span key={a.id} className={`radio-pill${ttsAcct === a.id ? " sel" : ""}`} onClick={() => setTtsAcct(a.id)}>{a.label}</span>)}
                {ttsAcct && <span className="radio-pill" onClick={() => setTtsAcct("")} title="pakai kunci default akun Anda"><Bi id="kunci default" en="default key" /></span>}
                <span className="radio-pill" onClick={() => setAddAcct({ component: "tts", label: "", key: "" })}><Plus size={12} /> <Bi id="Tambah kunci" en="Add key" /></span>
              </div></div>
          )}

          {/* form tambah kunci (muncul kontekstual) */}
          {addAcct && (
            <div className="fld-row" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.75rem" }}><div className="k"><Bi id="Kunci akun baru" en="New account key" /></div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                <input className="input" placeholder="Nama akun (mis. Akun OpenAI saya)" value={addAcct.label} onChange={(e) => setAddAcct({ ...addAcct, label: e.target.value })} />
                <input className="input input-mono" type="password" placeholder="Tempel API key dari penyedia" value={addAcct.key} onChange={(e) => setAddAcct({ ...addAcct, key: e.target.value })} />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <button className="btn btn-default btn-sm" disabled={addBusy || !addAcct.key.trim()} onClick={submitAddAcct}>{addBusy ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan kunci" en="Save key" />}</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setAddAcct(null)}><Bi id="Batal" en="Cancel" /></button>
                  {addMsg && <span style={{ fontSize: "var(--text-xs)", color: "var(--danger,#ef4444)" }}>{addMsg}</span>}
                </div>
              </div>
            </div>
          )}
          <div className="save-bar"><span className="muted">{aiMsg ?? <Bi id="Disimpan ke channel" en="Saves to channel" />}</span><button className="btn btn-default" disabled={savingAi} onClick={saveAi}>{savingAi ? "Menyimpan…" : <Bi id="Simpan & Terapkan" en="Save & Apply" />}</button></div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Operasional & mutu" en="Operations & quality" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1.25rem" }}><Bi id="Musik latar & ambang mutu (QC) per-channel." en="Background music & quality gate (QC) per-channel." /></p>
          <div className="fld-row"><div className="k"><Bi id="Aktifkan musik latar" en="Enable background music" /></div>
            <label className="switch"><input type="checkbox" checked={musicOn} onChange={(e) => setMusicOn(e.target.checked)} /><span className="track" /><span className="thumb" /></label></div>
          {musicOn && <>
            <div className="fld-row"><div className="k"><Bi id="Volume" en="Volume" /><div className="sub">{Math.round(musicVol * 100)}%</div></div>
              <input type="range" className="slider" min={0} max={50} value={Math.round(musicVol * 100)} onChange={(e) => setMusicVol(+e.target.value / 100)} /></div>
            <div className="fld-row"><div className="k"><Bi id="Mood default (opsional)" en="Default mood (optional)" /></div>
              <div className="radio-row">{["", "tegang", "misterius", "epik", "tenang", "ceria"].map((m) => <span key={m || "auto"} className={`radio-pill${musicMood === m ? " sel" : ""}`} onClick={() => setMusicMood(m)}>{m || "auto"}</span>)}</div></div>
          </>}
          <div className="fld-row"><div className="k"><Bi id="Skor viral min (QC)" en="Min viral score (QC)" /><div className="sub">{minScore}/100</div></div>
            <input type="range" className="slider" min={0} max={100} value={minScore} onChange={(e) => setMinScore(+e.target.value)} /></div>
          <div className="fld-row"><div className="k"><Bi id="Maks retry skrip" en="Max script retry" /></div>
            <div className="radio-row">{[1, 2, 3, 4, 5].map((n) => <span key={n} className={`radio-pill${maxRetry === n ? " sel" : ""}`} onClick={() => setMaxRetry(n)}>{n}</span>)}</div></div>
          <div className="save-bar"><span className="muted">{opsMsg ?? <Bi id="Disimpan ke channel (operasional)" en="Saves to channel (operations)" />}</span><button className="btn btn-default" disabled={savingOps} onClick={saveOps}>{savingOps ? "Menyimpan…" : <Bi id="Simpan & Terapkan" en="Save & Apply" />}</button></div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 760 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Caption & Hashtag" en="Caption & Hashtags" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Tampilan teks subtitle di video + hashtag postingan (brand channel ini)." en="On-screen subtitle styling + post hashtags (this channel's brand)." /></p>
          <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "1.5rem", alignItems: "start" }}>
            {/* Preview 9:16 LIVE — pakai nilai caption_style sebenarnya */}
            <div style={{ position: "sticky", top: 72 }}>
              <div style={{ aspectRatio: "9/16", borderRadius: "var(--r-lg)", overflow: "hidden", position: "relative", background: "linear-gradient(170deg,#0c2233,#05101a)", border: "1px solid var(--border)" }}>
                <div style={{ position: "absolute", inset: 0, background: "radial-gradient(120% 70% at 50% 25%,transparent,rgba(0,0,0,.55))" }} />
                <div style={{ position: "absolute", left: 10, right: 10, top: `${capNum("position_y_pct", 83)}%`, transform: "translateY(-50%)", textAlign: "center", lineHeight: 1.12,
                  fontFamily: `${capStr("font_name", "Anton")},Geist,sans-serif`, fontWeight: (cap.bold ?? true) ? 800 : 500,
                  fontSize: capNum("font_size", 68) * 0.18, color: capStr("inactive_word_color", "#FFFFFF"),
                  textShadow: `0 0 ${capNum("outline", 4)}px ${capStr("outline_color", "#000000")}, 0 1px 4px rgba(0,0,0,.8)` }}>
                  Suara aneh di <span style={{ color: capStr("active_word_color", "#FFD700") }}>kedalaman</span>
                </div>
              </div>
              <div className="muted" style={{ fontSize: "var(--text-xs)", textAlign: "center", marginTop: ".5rem" }}>Preview · 9:16</div>
            </div>
            {/* Kontrol — fld-row/slider/radio-pill/swatch */}
            <div>
              <div className="fld-row"><div className="k"><Bi id="Font" en="Font" /></div>
                <div className="radio-row">{["Anton", "Montserrat", "Bebas Neue", "Oswald", "Poppins"].map((f) => <span key={f} className={`radio-pill${capStr("font_name", "Anton") === f ? " sel" : ""}`} onClick={() => setCap({ ...cap, font_name: f })}>{f}</span>)}</div></div>
              <div className="fld-row"><div className="k"><Bi id="Ukuran font" en="Font size" /><div className="sub">{capNum("font_size", 68)}px</div></div>
                <input type="range" className="slider" min={36} max={120} value={capNum("font_size", 68)} onChange={(e) => setCap({ ...cap, font_size: +e.target.value })} /></div>
              <div className="fld-row"><div className="k"><Bi id="Posisi vertikal" en="Vertical position" /><div className="sub">{capNum("position_y_pct", 83)}% dari atas</div></div>
                <input type="range" className="slider" min={10} max={95} value={capNum("position_y_pct", 83)} onChange={(e) => setCap({ ...cap, position_y_pct: +e.target.value })} /></div>
              <div className="fld-row"><div className="k"><Bi id="Kata per baris" en="Words per line" /></div>
                <div className="radio-row">{[1, 2, 3, 4, 5].map((n) => <span key={n} className={`radio-pill${capNum("max_words_per_line", 3) === n ? " sel" : ""}`} onClick={() => setCap({ ...cap, max_words_per_line: n })}>{n}</span>)}</div></div>
              <div className="fld-row"><div className="k"><Bi id="Warna kata aktif" en="Active word color" /></div>
                <input type="color" value={capStr("active_word_color", "#FFD700")} onChange={(e) => setCap({ ...cap, active_word_color: e.target.value })} style={{ width: 44, height: 30, padding: 2, borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }} /></div>
              <div className="fld-row"><div className="k"><Bi id="Warna kata lain" en="Other words color" /></div>
                <input type="color" value={capStr("inactive_word_color", "#FFFFFF")} onChange={(e) => setCap({ ...cap, inactive_word_color: e.target.value })} style={{ width: 44, height: 30, padding: 2, borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }} /></div>
              <div className="fld-row"><div className="k"><Bi id="Garis tepi" en="Outline" /><div className="sub">{capNum("outline", 4)}px</div></div>
                <div style={{ display: "flex", gap: ".625rem", alignItems: "center" }}>
                  <input type="color" value={capStr("outline_color", "#000000")} onChange={(e) => setCap({ ...cap, outline_color: e.target.value })} style={{ width: 44, height: 30, padding: 2, borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }} />
                  <input type="range" className="slider" style={{ flex: 1 }} min={0} max={10} value={capNum("outline", 4)} onChange={(e) => setCap({ ...cap, outline: +e.target.value })} /></div></div>
              <div className="fld-row"><div className="k"><Bi id="Tebal (bold)" en="Bold" /></div>
                <label className="switch"><input type="checkbox" checked={Boolean(cap.bold ?? true)} onChange={(e) => setCap({ ...cap, bold: e.target.checked })} /><span className="track" /><span className="thumb" /></label></div>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem", marginTop: "1rem" }}>
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
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1.25rem" }}><Bi id="Sentuhan brand opsional di video & deskripsi (semua boleh kosong = tanpa branding)." en="Optional brand touches in video & description (all blank = no branding)." /></p>
          <div className="fld-row"><div className="k">CTA<div className="sub"><Bi id="implicit=tanpa brand · soft-sell=sebut halus" en="implicit=no brand · soft-sell=subtle" /></div></div>
            <div className="radio-row">{[["implicit", "Implicit"], ["soft_sell", "Soft-sell"]].map(([v, l]) => <span key={v} className={`radio-pill${ctaMode === v ? " sel" : ""}`} onClick={() => setCtaMode(v)}>{l}</span>)}</div></div>
          {ctaMode === "soft_sell" && <>
            <div className="fld-row"><div className="k"><Bi id="Nama brand" en="Brand name" /></div><input className="input" value={brandName} onChange={(e) => setBrandName(e.target.value)} style={{ maxWidth: 280 }} /></div>
            <div className="fld-row"><div className="k"><Bi id="Teks CTA" en="CTA text" /></div><input className="input" value={ctaText} onChange={(e) => setCtaText(e.target.value)} placeholder="Follow for more" style={{ maxWidth: 280 }} /></div>
          </>}
          <div className="fld-row"><div className="k"><Bi id="Logo (URL)" en="Logo (URL)" /><div className="sub"><Bi id="PNG transparan · overlay di video · upload file: segera" en="transparent PNG · video overlay · file upload: soon" /></div></div>
            <input className="input input-mono" value={brandLogo} onChange={(e) => setBrandLogo(e.target.value)} placeholder="https://… .png" style={{ maxWidth: 320 }} /></div>
          {brandLogo && <>
            <div className="fld-row"><div className="k"><Bi id="Posisi logo" en="Logo position" /></div>
              <div className="radio-row">{[["top-left", "↖"], ["top-right", "↗"], ["bottom-left", "↙"], ["bottom-right", "↘"]].map(([v, l]) => <span key={v} className={`radio-pill${logoPos === v ? " sel" : ""}`} onClick={() => setLogoPos(v)} style={{ fontSize: "1rem" }}>{l}</span>)}</div></div>
            <div className="fld-row"><div className="k"><Bi id="Ukuran logo" en="Logo size" /><div className="sub">{Math.round(logoSize * 100)}%</div></div>
              <input type="range" className="slider" min={5} max={30} value={Math.round(logoSize * 100)} onChange={(e) => setLogoSize(+e.target.value / 100)} /></div>
            <div className="fld-row"><div className="k"><Bi id="Opasitas logo" en="Logo opacity" /><div className="sub">{Math.round(logoOpacity * 100)}%</div></div>
              <input type="range" className="slider" min={20} max={100} value={Math.round(logoOpacity * 100)} onChange={(e) => setLogoOpacity(+e.target.value / 100)} /></div>
          </>}
          <div className="fld-row"><div className="k"><Bi id="Link landing (deskripsi)" en="Landing link (description)" /></div><input className="input input-mono" value={landingLink} onChange={(e) => setLandingLink(e.target.value)} placeholder="https://…" style={{ maxWidth: 320 }} /></div>
          {landingLink && <div className="fld-row"><div className="k"><Bi id="Posisi link" en="Link position" /></div>
            <div className="radio-row">{[["top", "Atas"], ["bottom", "Bawah"]].map(([v, l]) => <span key={v} className={`radio-pill${linkPos === v ? " sel" : ""}`} onClick={() => setLinkPos(v)}>{l}</span>)}</div></div>}
          <div className="save-bar"><span className="muted">{br2Msg ?? <Bi id="Disimpan ke channel (branded)" en="Saves to channel (branded)" />}</span><button className="btn btn-default" disabled={savingBr2} onClick={saveBranded}>{savingBr2 ? "Menyimpan…" : <Bi id="Simpan & Terapkan" en="Save & Apply" />}</button></div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Target YouTube channel" en="YouTube target channel" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}>
            <Bi id="Koneksi Google/YouTube diatur sekali di menu Integrasi (berlaku semua channel). Di sini pilih channel YouTube TUJUAN publish untuk channel ini." en="Google/YouTube connection is set once in the Integrations menu (all channels). Here, choose the destination YouTube channel for this channel." />
            {" "}<Link href="/integrations" className="link" style={{ color: "var(--brand)" }}><Bi id="Buka Integrasi →" en="Open Integrations →" /></Link>
          </p>
          <div className="fld"><label className="label"><Bi id="YouTube Channel ID (target)" en="YouTube Channel ID (target)" /></label>
            <input className="input input-mono" value={targetYt} onChange={(e) => setTargetYt(e.target.value)} placeholder="UCxxxxxxxxxxxxxxxxxxxxxx" /></div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginTop: "0.5rem" }}>
            <button className="btn btn-default btn-sm" onClick={saveTarget} disabled={savingTarget}>{savingTarget ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan target" en="Save target" />}</button>
            {targetMsg && <span style={{ fontSize: "var(--text-xs)", color: targetMsg.includes("tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{targetMsg}</span>}
          </div>
        </div>
        </>
      )}
    </>
  );
}
