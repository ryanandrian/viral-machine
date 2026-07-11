"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ExternalLink, Settings, ArrowRight, BarChart3, Calendar, Activity, Loader2, Check, Pause, Play, AlertTriangle, Mic, ShieldCheck, Sparkles, Clock, Trash2, Plus, PenLine, Image as ImageIcon, Info, Search, X, Shuffle, Upload, Lock, Video } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { effectiveStatus, TONE } from "@/lib/channel-status";
import PresetTables from "@/components/preset-tables";
import ConfirmDialog from "@/components/confirm-dialog";
import { ComplianceView, type Compliance } from "@/components/compliance-view";
import { InsightsView, type Insights, type LearnedWeights } from "@/components/insights-view";
import { LearningCurveCard } from "@/components/learning-curve-card";
import RunsTable from "@/components/runs-table";
import TestNichePanel, { type TestInfo } from "@/components/test-niche-panel";
import "./channel-detail.css";

// D3 Channel Detail — Phase 9.3 (wired Supabase v2, anon + RLS).
// Header + Settings = data NYATA (read channels by id, write via channels RLS UPDATE — tanpa kolom
// privilege jadi aman client-side, no RPC). KPI/Overview/Runs/Analytics/Schedule = placeholder JUJUR
// (timeseries di-wire 9.4 analytics; Runs nyata di D4/D5; slot-model saat D7). Niche dikelola di Config→Niches.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type ChannelRow = {
  id: string; channel_name: string | null; platform_channel_id: string | null; youtube_account_id: string | null; subscriber_count: number | null;
  niche: string | null; niche_pool: string[] | null; niche_mode: string | null; content_language: string | null;
  is_active: boolean | null; publish_privacy: string | null; duration_preset: number | null; publish_slots: string[] | null;
  production_paused: boolean | null; production_paused_reason: string | null;
  llm_model: string | null; llm_library: string | null; visual_mode: string | null;
  llm_account_id: string | null; tts_account_id: string | null; visual_account_id: string | null;
  tts_provider: string | null; tts_model: string | null; voice_key: string | null;
  image_quality: string | null; music_enabled: boolean | null; music_volume: number | null;
  music_default_mood: string | null; script_min_viral_score: number | null; script_max_retry: number | null;
  caption_style: Record<string, unknown> | null; niche_hashtags: Record<string, string[]> | null;
  cta_mode: string | null; brand_name: string | null; brand_cta_text: string | null; brand_logo: string | null;
  logo_position: string | null; logo_size: number | null; logo_opacity: number | null;
  landing_link: string | null; link_position: string | null;
};
// Default caption_style — match BE DEFAULT_CAPTION_STYLE (video_renderer). Partial-override OK.
const CAP_DEFAULT = { font_name: "Anton", font_size: 68, bold: true, active_word_color: "#FFD700", inactive_word_color: "#FFFFFF", outline_color: "#000000", outline: 4, position_y_pct: 83, max_words_per_line: 3 };
type ModelOpt = { model_key: string; provider_key: string; display_name: string; quality_tier?: string | null; pricing?: Record<string, unknown> | null; component?: string };
type VoiceOpt = { voice_key: string; provider_key: string; display_name: string; gender: string | null; preview_url: string | null; locale: string | null; language: string | null };

// F2-07/F1-09: status efektif terpadu = komponen bersama `lib/channel-status` (satu sumber, anti-drift).

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
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const wasHaltedRef = useRef(false);  // latch: channel pernah halted saat sesi ini → pesan hasil pakai "aktif kembali".
  // Siklus hidup kartu hasil uji (owner 2026-07-08: "sampai kapan muncul?") — hilang bila:
  // (1) tenant klik Tutup (localStorage per-test.id, persisten), (2) usang > test_result_ttl_hours
  // (app_config, admin-editable, fallback 24), (3) test baru menggantikan (test.id berubah).
  const [dismissedTestId, setDismissedTestId] = useState<string | null>(null);
  const [testTtlHours, setTestTtlHours] = useState(24);
  useEffect(() => { try { setDismissedTestId(localStorage.getItem(`mv:test-dismissed:${id}`)); } catch { /* non-fatal */ } }, [id]);
  const dismissTest = (testId: string) => { try { localStorage.setItem(`mv:test-dismissed:${id}`, testId); } catch { /* non-fatal */ } setDismissedTestId(testId); };
  const [confirmCfg, setConfirmCfg] = useState<null | { title: React.ReactNode; message: React.ReactNode; confirmLabel: React.ReactNode; confirmClass: string; onConfirm: () => void }>(null);
  // F2-07/F1-09: status efektif
  const [sub, setSub] = useState<string | null>(null);
  const [rd, setRd] = useState<{ ready: boolean; missing: string[] } | null>(null);
  // F2-13b: data per-channel utk tab (channel_insights + production_runs + publish_slots)
  const [chCmp, setChCmp] = useState<Compliance | null>(null);
  const [chIns, setChIns] = useState<Insights | null>(null);
  const [chLearned, setChLearned] = useState<LearnedWeights>(null);  // formula adaptif S3-A (tenant-wide)
  const [chRunStats, setChRunStats] = useState<{ total: number; success: number; failed: number; review: number } | null>(null);  // COUNT penuh utk KPI tab Analytics
  const [slots, setSlots] = useState<string[]>([]);
  const [newSlot, setNewSlot] = useState("");
  const [slotMsg, setSlotMsg] = useState<string | null>(null);
  const [savingSlot, setSavingSlot] = useState(false);
  const [totalVids, setTotalVids] = useState<number | null>(null);  // = Video terbit (videos.published) per channel (std 0098)
  const [chAnalytics, setChAnalytics] = useState<{ published_videos: number; total_views: number; avg_engagement: number | null } | null>(null);
  // F2-03: pemilih AI per-channel (model + voice). Katalog dari ai_models/tts_profiles/voice_catalog (RLS read).
  const [llmOpts, setLlmOpts] = useState<ModelOpt[]>([]);
  const [imgOpts, setImgOpts] = useState<(ModelOpt & { component: string })[]>([]);  // generator visual: image + video (BUKAN library/footage)
  const [ttsOpts, setTtsOpts] = useState<{ provider_key: string; display_name: string }[]>([]);
  const [ttsModelOpts, setTtsModelOpts] = useState<ModelOpt[]>([]);  // ai_models component='tts' (migr 0087)
  const [usdIdr, setUsdIdr] = useState<number>(0);  // kurs tampilan biaya model (0 = belum tersedia)
  const [voiceAll, setVoiceAll] = useState<VoiceOpt[]>([]);
  const [llmProv, setLlmProv] = useState("");     // penyedia LLM (= llm_library); pilih DULU, lalu model
  const [llmModel, setLlmModel] = useState("");
  const [visualProv, setVisualProv] = useState(""); // penyedia visual; pilih DULU, lalu model (image/video)
  const [imgModel, setImgModel] = useState("");  // Visual v2 = generator AI (gambar/video); footage/library Pexels dibuang
  const [ttsProv, setTtsProv] = useState("");
  const [ttsModel, setTtsModel] = useState("");  // model TTS dipilih tenant (eleven_turbo/multilingual/flash; tts-1/hd)
  const [voiceKey, setVoiceKey] = useState("");
  // Pemutar contoh suara — kelas SAMA dgn admin PlayBtn: ▶/⏹ toggle, satu audio, auto-stop (owner 2026-07-06)
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const toggleVoice = (k: string, url: string) => {
    if (playingVoice === k) { audioRef.current?.pause(); audioRef.current = null; setPlayingVoice(null); return; }
    audioRef.current?.pause();
    const a = new Audio(url); a.onended = () => setPlayingVoice(null);
    a.play().catch(() => setPlayingVoice(null));
    audioRef.current = a; setPlayingVoice(k);
  };
  useEffect(() => () => { audioRef.current?.pause(); }, []);
  const [savingAi, setSavingAi] = useState("");  // elemen yg sedang disimpan ("llm"/"tts"/"visual")
  const [aiMsg, setAiMsg] = useState<{ el: string; text: string; ok: boolean } | null>(null);
  // Kunci AI = tenant-wide POOL di Page Credential (/integrations). Channel pilih penyedia→model→voice→AKUN.
  // provMap: provider_key → {display_name, auth_type, key_group(vendor)}. Akun dari tenant_ai_accounts (status valid).
  const [provMap, setProvMap] = useState<Record<string, { name: string; auth: string; kg: string }>>({});
  const [aiAccts, setAiAccts] = useState<{ id: string; provider_key: string; key_group: string; label: string; status: string }[]>([]);
  const [llmAcct, setLlmAcct] = useState("");      // channels.llm_account_id (kosong = auto akun tunggal vendor)
  const [ttsAcct, setTtsAcct] = useState("");      // channels.tts_account_id
  const [visualAcct, setVisualAcct] = useState(""); // channels.visual_account_id
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
  const [savingHash, setSavingHash] = useState(false);
  const [hashMsg, setHashMsg] = useState<string | null>(null);
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
  const [logoUploading, setLogoUploading] = useState(false);

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
  async function uploadLogo(file: File) {
    setBr2Msg(null); setLogoUploading(true);
    try {
      const fd = new FormData(); fd.append("file", file); fd.append("channel_id", id);
      const res = await fetch("/api/channels/upload-logo", { method: "POST", body: fd });
      const j = await res.json().catch(() => ({}));
      if (res.ok) { setBrandLogo(j.public_url); setBr2Msg(`Logo terupload (${j.width}×${j.height}px) — klik “Simpan & Terapkan”.`); }
      else setBr2Msg(j.error || "Upload gagal");
    } catch (e) { setBr2Msg(`Error: ${(e as Error).message}`); }
    setLogoUploading(false);
  }
  const capNum = (k: string, d: number) => Number((cap[k] as number) ?? d);
  const capStr = (k: string, d: string) => String((cap[k] as string) ?? d);

  async function saveCaption() {
    setBrandMsg(null); setSavingBrand(true);
    const { error } = await supabase.from("channels").update({ caption_style: cap }).eq("id", id);
    setSavingBrand(false);
    setBrandMsg(error ? `Gagal: ${error.message}` : "Tersimpan");
    if (!error) load();
  }
  async function saveHashtags() {
    setHashMsg(null); setSavingHash(true);
    const nh: Record<string, string[]> = {};
    for (const [n, s] of Object.entries(tags)) {
      const arr = s.split(",").map((t) => t.trim()).filter(Boolean).map((t) => (t.startsWith("#") ? t : `#${t}`));
      if (arr.length) nh[n] = arr;
    }
    const { error } = await supabase.from("channels").update({ niche_hashtags: nh }).eq("id", id);
    setSavingHash(false);
    setHashMsg(error ? `Gagal: ${error.message}` : "Tersimpan");
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

  // F2-03 simpan AI per-ELEMEN (card terpisah §2.2). Hanya penyedia/model/voice → channels (RLS UPDATE).
  // Kunci TIDAK lagi di sini — di Page Credential (/integrations), worker resolusi dari tenant_ai_accounts.
  async function saveAiPart(el: string, patch: Record<string, unknown>) {
    setAiMsg(null); setSavingAi(el);
    const { error } = await supabase.from("channels").update(patch).eq("id", id);
    setSavingAi("");
    setAiMsg({ el, text: error ? `Gagal: ${error.message}` : "Tersimpan", ok: !error });
    if (!error) load();
  }
  const saveLlm = () => saveAiPart("llm", { llm_model: llmModel || null, llm_library: llmProv || null, llm_account_id: llmAcct || null });
  const saveTts = () => saveAiPart("tts", { tts_provider: ttsProv || null, tts_model: ttsModel || null, voice_key: voiceKey || null, tts_account_id: ttsAcct || null });
  const saveVisual = () => {
    // Prefix generator dari component model terpilih: image → ai_image:, video → ai_video: (no footage/library).
    const vModel = imgOpts.find((m) => m.model_key === imgModel);
    const visual_mode = imgModel && vModel ? `${vModel.component === "video" ? "ai_video" : "ai_image"}:${imgModel}` : null;
    return saveAiPart("visual", { visual_mode, image_quality: imgQuality, visual_account_id: visualAcct || null });
  };
  // Akun valid utk vendor penyedia terpilih (untuk pemilih akun; auto bila 1, pilih bila >1).
  const acctsFor = (provider: string) => {
    const kg = provMap[provider]?.kg || provider;
    return aiAccts.filter((a) => a.key_group === kg && a.status === "valid");
  };
  // Pemilih AKUN per-elemen: penyedia gratis → null; 0 akun → link Kredensial; 1 → auto; >1 → pilih.
  const acctPicker = (provider: string, sel: string, setSel: (v: string) => void) => {
    if (!provider || provMap[provider]?.auth === "none") return null;
    const as = acctsFor(provider);
    return (
      <div className="fld-row"><div className="k"><Bi id="Akun (kunci)" en="Account (key)" /></div>
        <div className="radio-row">
          {as.length === 0 && <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum ada kunci — " en="No key — " /><Link href="/integrations" className="link"><Bi id="lengkapi di Kredensial" en="add in Credentials" /></Link></span>}
          {as.length === 1 && <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{as[0].label} ✓ <Bi id="(otomatis)" en="(auto)" /></span>}
          {as.length > 1 && as.map((a) => <span key={a.id} className={`radio-pill${sel === a.id ? " sel" : ""}`} onClick={() => setSel(a.id)}>{a.label}</span>)}
        </div></div>
    );
  };

  // C3: editor niche per-channel — pilih dari ENTITLEMENT tenant (pool); mode disimpulkan dari jumlah; tulis via RPC.
  const [nicheOpts, setNicheOpts] = useState<{ id: string; name: string }[]>([]);
  const [nicheMsg, setNicheMsg] = useState<string | null>(null);
  const [savingNiche, setSavingNiche] = useState(false);
  const [pool, setPool] = useState<string[]>([]);                 // niche_pool channel (1=fixed, >1=random)
  const [nicheSearch, setNicheSearch] = useState("");             // kotak cari (skala ratusan)
  const [nicheDefaults, setNicheDefaults] = useState<Record<string, string[]>>({}); // niches.default_hashtags (placeholder hashtag)

  // Preset durasi per-channel (channels.duration_preset) — kolom "bersih", tulis via RLS UPDATE langsung.
  const [dpreset, setDpreset] = useState<number | null>(null);
  const [savingPreset, setSavingPreset] = useState(false);
  const [presetMsg, setPresetMsg] = useState<string | null>(null);

  // YouTube = bagian IDENTITAS channel (kartu 1): pilih KONEKSI (pool tenant_youtube_accounts, diatur di
  // /integrations) + channel TUJUAN (channels.platform_channel_id). Disimpan bareng identitas via save().
  const [targetYt, setTargetYt] = useState("");
  const [ytAccountId, setYtAccountId] = useState("");
  // [B11] Batch 1.7 — koneksi berwajah (nama+foto) + used_by (cegatan redundant di picker).
  const [ytAccounts, setYtAccounts] = useState<{ id: string; label: string; status: string | null; yt_channel_id: string | null; connected: boolean; yt_channel_title?: string | null; yt_channel_thumb?: string | null; used_by?: { id: string; channel_name: string }[] }[]>([]);
  const [ytFlash, setYtFlash] = useState<{ kind: "connected" | "already" | "error"; text: string } | null>(null);
  const [ytConnBusy, setYtConnBusy] = useState(false);

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
    // Mode disimpulkan dari jumlah: 1 niche = fixed, >1 = random (otomatis). Niche utama = pool[0].
    const mode = pool.length > 1 ? "random" : "fixed";
    const { error } = await supabase.rpc("set_channel_niche", { p_channel_id: id, p_niche: pool[0] ?? "", p_niche_mode: mode, p_niche_pool: pool });
    setSavingNiche(false);
    setNicheMsg(error ? (error.message.includes("entitlement") ? "Niche itu di luar paket Anda" : `Gagal: ${error.message}`) : "Niche tersimpan");
    if (!error) load();
  }

  // Hasil uji KHUSUS channel (renderResult TestNichePanel) — sopan (target tenant Indonesia), sebut model
  // bermasalah saat gagal, tautan YouTube Studio saat sukses. Status channel (recover) via banner yg disegarkan.
  // 1a/1c: petunjuk budget di pill model — badge tier + tag Gratis + tooltip harga (Rp via usdIdr).
  const TIER_LABEL: Record<string, { id: string; en: string }> = {
    basic: { id: "Basic", en: "Basic" }, standard: { id: "Standard", en: "Standard" },
    premium: { id: "Premium", en: "Premium" }, fast: { id: "Cepat", en: "Fast" },
  };
  const isFreeModel = (m: ModelOpt) => provMap[m.provider_key]?.auth === "none";
  function priceTitle(m: ModelOpt, comp: string): string {
    if (isFreeModel(m)) return "Gratis — tanpa biaya";
    const p = m.pricing as Record<string, number | null> | null;
    if (!p) return "Harga belum tersedia";
    const rp = (usd?: number | null) => usd != null && usdIdr ? `Rp${Math.round(usd * usdIdr).toLocaleString("id-ID")}` : (usd != null ? `$${usd}` : "—");
    if (comp === "llm") return `≈ ${rp(p.in_per_1m)}/1jt token masuk · ${rp(p.out_per_1m)}/1jt keluar`;
    if (comp === "tts") return `≈ ${rp(p.per_1m_chars)}/1jt karakter`;
    return `≈ ${rp(p.per_image)}/gambar`;
  }
  function ModelBadges({ m }: { m: ModelOpt }) {
    const t = m.quality_tier ? TIER_LABEL[m.quality_tier] : null;
    if (isFreeModel(m)) return <span className="badge badge-success" style={{ fontSize: ".55rem", marginLeft: 5 }}><Bi id="Gratis" en="Free" /></span>;
    return t ? <span className="badge badge-default" style={{ fontSize: ".55rem", marginLeft: 5 }}><Bi id={t.id} en={t.en} /></span> : null;
  }

  function failStageInfo(test: TestInfo): { stage: string; model: string | null } {
    const msg = ((test.run?.error_message as string) || test.error || "").toLowerCase();
    if (/tts|suara|voice|eleven|audio/.test(msg))
      return { stage: "Membuat suara (TTS)", model: `${provMap[ttsProv]?.name ?? ttsProv}${ttsModel ? ` — ${ttsModel}` : ""}` };
    if (/image|visual|gambar|render|clip/.test(msg))
      return { stage: "Membuat visual", model: imgModel ? `${provMap[visualProv]?.name ?? visualProv} — ${imgModel}` : null };
    if (/script|llm|naskah|hook|prompt/.test(msg))
      return { stage: "Membuat naskah (LLM)", model: `${provMap[llmProv]?.name ?? llmProv}${llmModel ? ` — ${llmModel}` : ""}` };
    return { stage: "produksi", model: null };
  }
  // Siklus hidup hasil uji (SATU predikat utk kartu + ringkasan badge/skor/tanggal — Tutup = SEMUA hilang):
  // ditutup tenant (per-test.id) ATAU usang > TTL → panel kembali tenang (hanya tombol uji).
  function isResultHidden(test: TestInfo): boolean {
    if (!["done", "published", "failed"].includes(test.status)) return false;
    if (dismissedTestId === test.id) return true;
    const endAt = new Date(test.completed_at || test.created_at).getTime();
    return Number.isFinite(endAt) && Date.now() - endAt > testTtlHours * 3_600_000;
  }
  function channelTestResult(test: TestInfo) {
    const s: React.CSSProperties = { fontSize: "var(--text-sm)", marginTop: ".5rem", lineHeight: 1.55 };
    if (isResultHidden(test)) return null;
    const closeBtn = (
      <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto", flexShrink: 0 }} onClick={() => dismissTest(test.id)} title="Tutup pesan ini"><X size={13} /> <Bi id="Tutup" en="Close" /></button>
    );
    if (["done", "published"].includes(test.status)) {
      const vid = test.run?.youtube_video_id as string | undefined;
      const studio = vid ? `https://studio.youtube.com/video/${vid}/edit` : (test.run?.youtube_url as string | undefined);
      return (
        <div style={{ ...s, padding: ".6rem .75rem", borderRadius: "var(--r-md)", background: "var(--success-soft, #e6f7ec)", color: "var(--text-primary)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><span style={{ fontWeight: 600 }}>✓ <Bi id="Uji berhasil." en="Test succeeded." />{wasHaltedRef.current && <> <Bi id="Channel Anda telah aktif kembali." en="Your channel is active again." /></>}</span>{closeBtn}</div>
          {!test.run?.qc_passed && test.run?.error_message && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".25rem" }}><Bi id="Catatan QC:" en="QC note:" /> {test.run.error_message as string}</div>}
          <div style={{ marginTop: ".4rem" }}><Bi id="Silakan evaluasi hasil uji ini di YouTube Studio Anda:" en="Please review this test in your YouTube Studio:" /></div>
          {studio && <a className="btn btn-secondary btn-sm" href={studio} target="_blank" rel="noopener noreferrer" style={{ marginTop: ".4rem", textDecoration: "none" }}><ExternalLink size={13} /> <Bi id="Buka di YouTube Studio" en="Open in YouTube Studio" /></a>}
          {/* Studio membuka link edit di bawah identitas channel yang AKTIF di sesi browser — akun Google
              ber-multi-channel yang sedang di channel lain akan melihat "Oops, something went wrong"
              (fenomena Google; URL edit tak bisa memaksa identitas). Pagar terbaik = edukasi di titik klik. */}
          {studio && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".35rem" }}><Bi id={`Bila Studio menampilkan "Oops, something went wrong": channel yang sedang aktif di YouTube Studio Anda bukan "${ch?.channel_name ?? "channel ini"}". Klik foto profil di Studio → Ganti akun → pilih "${ch?.channel_name ?? "channel ini"}", lalu buka tautan ini lagi.`} en={`If Studio shows "Oops, something went wrong": the channel currently active in your YouTube Studio is not "${ch?.channel_name ?? "this channel"}". Click your avatar in Studio → Switch account → pick "${ch?.channel_name ?? "this channel"}", then open this link again.`} /></div>}
        </div>
      );
    }
    if (test.status === "failed") {
      const f = failStageInfo(test);
      return (
        <div style={{ ...s, padding: ".6rem .75rem", borderRadius: "var(--r-md)", background: "var(--warning-soft, #fdf0e3)", color: "var(--text-primary)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: ".5rem" }}><span style={{ fontWeight: 600 }}>⚠ <Bi id={`Mohon maaf, uji belum berhasil pada tahap: ${f.stage}.`} en={`Sorry, the test did not succeed at stage: ${f.stage}.`} /></span>{closeBtn}</div>
          <div style={{ marginTop: ".35rem" }}>
            {f.model
              ? <Bi id={`Mohon periksa kembali kredensial atau kredit AI untuk ${f.model}, lalu silakan lakukan uji kembali.`} en={`Please re-check the AI credential or credit for ${f.model}, then kindly run the test again.`} />
              : <Bi id="Mohon periksa kembali kredensial atau kredit AI Anda, lalu silakan lakukan uji kembali." en="Please re-check your AI credential or credit, then kindly run the test again." />}
          </div>
          {wasHaltedRef.current && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".35rem" }}><Bi id="Channel akan aktif kembali setelah satu uji berhasil." en="The channel will be active again once one test succeeds." /></div>}
        </div>
      );
    }
    return null;
  }
  // Konfirmasi ringan — Pause menghentikan produksi baru channel ini.
  function askPause() {
    setConfirmCfg({
      title: <Bi id="Jeda produksi channel ini?" en="Pause this channel's production?" />,
      message: <Bi id="Produksi video baru akan berhenti sampai Anda aktifkan lagi. Tidak memakai kredit, dan bisa dilanjutkan kapan saja." en="New video production will stop until you resume. It uses no credit and can be resumed anytime." />,
      confirmLabel: <Bi id="Ya, jeda" en="Yes, pause" />,
      confirmClass: "btn-default",
      onConfirm: () => { setConfirmCfg(null); pausePlay(false); },
    });
  }


  // F2-07: pause/play (toggle is_active). Play hanya bila readiness lengkap (gerbang aktivasi).
  async function pausePlay(toActive: boolean) {
    setErr(null); setBusy(true);
    // Gerbang: aktivasi HANYA bila readiness terbaca DAN ready. rd null (cek gagal) → JANGAN izinkan (default aman).
    if (toActive && (!rd || !rd.ready)) { setBusy(false); setTab("settings"); return setTestMsg("Belum bisa diaktifkan — lengkapi konfigurasi dulu (lihat checklist)."); }
    const { error } = await supabase.from("channels").update({ is_active: toActive }).eq("id", id);
    setBusy(false);
    if (error) return setErr(error.message);
    load();
  }

  const load = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    const { data } = await supabase.from("channels")
      .select("id,channel_name,platform_channel_id,youtube_account_id,subscriber_count,niche,niche_pool,niche_mode,content_language,is_active,publish_privacy,duration_preset,publish_slots,production_paused,production_paused_reason,llm_model,llm_library,visual_mode,llm_account_id,tts_account_id,visual_account_id,tts_provider,tts_model,voice_key,image_quality,music_enabled,music_volume,music_default_mood,script_min_viral_score,script_max_retry,caption_style,niche_hashtags,cta_mode,brand_name,brand_cta_text,brand_logo,logo_position,logo_size,logo_opacity,landing_link,link_position")
      .eq("id", id).maybeSingle();
    const c = data as ChannelRow | null;
    setCh(c);
    if (c?.production_paused) wasHaltedRef.current = true;
    if (c) {
      setName(c.channel_name ?? ""); setClang(c.content_language ?? "id-ID");
      setPrivacy(c.publish_privacy ?? "private");
      setPool(Array.isArray(c.niche_pool) && c.niche_pool.length ? c.niche_pool : (c.niche ? [c.niche] : []));
      setDpreset(c.duration_preset ?? null); setSlots(c.publish_slots ?? []); setTargetYt(c.platform_channel_id ?? ""); setYtAccountId(c.youtube_account_id ?? "");
      setLlmProv(c.llm_library ?? ""); setLlmModel(c.llm_model ?? "");
      const vm = c.visual_mode ?? "";
      setImgModel(vm.startsWith("ai_image:") || vm.startsWith("ai_video:") ? vm.slice(9) : "");
      setTtsProv(c.tts_provider ?? ""); setTtsModel(c.tts_model ?? ""); setVoiceKey(c.voice_key ?? "");
      setLlmAcct(c.llm_account_id ?? ""); setTtsAcct(c.tts_account_id ?? ""); setVisualAcct(c.visual_account_id ?? "");
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
    // Penyedia AKTIF dimuat DULU: opsi model/TTS wajib disaring per vendor aktif (mesin get_providers() hanya
    // kenal penyedia aktif — model dari vendor yang admin matikan TIDAK BOLEH bisa dipilih; mandat butir-3 2026-07-06).
    const { data: aps } = await supabase.from("ai_providers").select("provider_key,display_name,auth_type,key_group").eq("is_active", true);
    const activeProv = new Set(((aps ?? []) as { provider_key: string }[]).map((p) => p.provider_key));
    // 1a/1b: sertakan tier + harga (petunjuk budget di pill) & urutkan sort_order (kurasi admin) lalu nama.
    const { data: amRaw } = await supabase.from("ai_models").select("model_key,provider_key,component,display_name,quality_tier,pricing,sort_order").eq("is_active", true).order("sort_order").order("display_name");
    const am = ((amRaw ?? []) as (ModelOpt & { component: string })[]).filter((m) => activeProv.has(m.provider_key));
    setLlmOpts(am.filter((m) => m.component === "llm"));
    const imgList = am.filter((m) => m.component === "image" || m.component === "video");
    setImgOpts(imgList);
    // visualProv = penyedia dari model visual tersimpan (visual_mode = ai_image:/ai_video:<model>)
    const curVm = c?.visual_mode ?? "";
    const curImgModel = curVm.startsWith("ai_image:") || curVm.startsWith("ai_video:") ? curVm.slice(9) : "";
    setVisualProv(imgList.find((m) => m.model_key === curImgModel)?.provider_key ?? "");
    setTtsModelOpts(am.filter((m) => m.component === "tts"));
    const { data: tp } = await supabase.from("tts_profiles").select("provider_key,display_name").eq("is_active", true);
    setTtsOpts(((tp ?? []) as { provider_key: string; display_name: string }[]).filter((p) => activeProv.has(p.provider_key)));
    const { data: vc } = await supabase.from("voice_catalog").select("voice_key,provider_key,display_name,gender,preview_url,locale,language").eq("is_active", true).order("sort_order");
    setVoiceAll((vc ?? []) as VoiceOpt[]);
    // penyedia: display_name (label pill) + auth_type (gratis 'none' → tak butuh kunci, mis. edge_tts).
    setProvMap(Object.fromEntries(((aps ?? []) as { provider_key: string; display_name: string; auth_type: string; key_group: string | null }[]).map((p) => [p.provider_key, { name: p.display_name, auth: p.auth_type, kg: p.key_group || p.provider_key }])));
    // Akun AI tenant (untuk pemilih akun per-elemen; baca-balik tak perlu di sini — cukup id/status/vendor).
    try { const ra = await fetch("/api/credentials/ai"); if (ra.ok) { const ja = await ra.json(); setAiAccts((ja.accounts || []).map((a: { id: string; provider_key: string; key_group: string; label: string; status: string }) => ({ id: a.id, provider_key: a.provider_key, key_group: a.key_group, label: a.label, status: a.status }))); } } catch { /* non-fatal */ }
    // Kunci AI = POOL tenant-wide (Page Credential /integrations). Tidak dibaca per-channel di sini.
    // Koneksi YouTube (pool) untuk pemilih di kartu identitas.
    try { const ry = await fetch("/api/youtube/status"); if (ry.ok) { const jy = await ry.json(); setYtAccounts(jy.accounts || []); } } catch { /* non-fatal */ }
    // F2-07: status efektif → subscription + readiness (RPC tenant-scoped F2-fondasi).
    const { data: cfg } = await supabase.from("tenant_configs").select("plan_type,subscription_status,viral_score_weights").maybeSingle();
    // Kurs USD→IDR utk tampilan harga model = app_config (BUKAN tenant_configs — kolomnya memang di sana).
    try {
      const { data: fx } = await supabase.from("app_config").select("value").eq("key", "usd_idr_rate").maybeSingle();
      setUsdIdr(Number((fx as { value?: number } | null)?.value) || 0);
    } catch { /* fail-soft: tooltip pakai USD */ }
    // Batas usang kartu hasil uji — app_config (admin-editable, fail-soft ke 24 jam).
    try {
      const { data: ttl } = await supabase.from("app_config").select("value").eq("key", "test_result_ttl_hours").maybeSingle();
      const h = Number((ttl as { value?: number } | null)?.value);
      if (Number.isFinite(h) && h > 0) setTestTtlHours(h);
    } catch { /* fail-soft */ }
    setSub((cfg as { subscription_status?: string } | null)?.subscription_status ?? null);
    { const w = (cfg as { viral_score_weights?: LearnedWeights } | null)?.viral_score_weights; setChLearned(w && w.weights ? w : null); }
    try { const { data: rdd } = await supabase.rpc("channel_readiness", { p_channel_id: id }); if (rdd) setRd(rdd as { ready: boolean; missing: string[] }); } catch { /* non-fatal */ }
    // F2-13b: insight per-channel (channel_insights by channel_id) + runs per-channel (production_runs).
    const { data: ci } = await supabase.from("channel_insights")
      .select("compliance,performance_grade,videos_analyzed,niche_weights,top_hooks,avoid_patterns,content_type_perf,top_topics,computed_at")
      .eq("channel_id", id).order("computed_at", { ascending: false }).limit(1).maybeSingle();
    if (ci) {
      setChCmp(((ci as { compliance?: Compliance }).compliance) ?? null);
      setChIns(ci as unknown as Insights);
    } else { setChCmp(null); setChIns(null); }
    // Analytics per-channel (all-time, std 0098): Video terbit=videos.published · Views/Engagement=video_analytics latest-per-video.
    try {
      const { data: ca } = await supabase.rpc("get_channel_analytics", { p_channel_id: id });
      const a = (Array.isArray(ca) ? ca[0] : ca) as { published_videos: number; total_views: number; avg_engagement: number | null } | null;
      setChAnalytics(a ?? null);
      setTotalVids(a?.published_videos ?? 0);
    } catch { setChAnalytics(null); setTotalVids(0); }
    // KPI tab Analytics = COUNT PENUH per status (chRuns ter-limit 60 → tak akurat utk total).
    const cntRun = async (st?: string[]) => {
      let qb = supabase.from("production_runs").select("id", { count: "exact", head: true }).eq("channel_id", id);
      if (st) qb = qb.in("status", st);
      const { count } = await qb; return count ?? 0;
    };
    const [rTot, rOk, rFail, rRev] = await Promise.all([cntRun(), cntRun(["success"]), cntRun(["failed"]), cntRun(["qc_failed", "ready_with_issues"])]);
    setChRunStats({ total: rTot, success: rOk, failed: rFail, review: rRev });
    const tier = (cfg as { plan_type?: string } | null)?.plan_type ?? "starter";
    // Entitlement katalog publik per-tier: CONFIG-DRIVEN dari plan_limits.full_niche_catalog (0124) — no-hardcode.
    const { data: plRow } = await supabase.from("plan_limits").select("full_niche_catalog").eq("plan_type", tier).maybeSingle();
    const fullCatalog = Boolean((plRow as { full_niche_catalog?: boolean } | null)?.full_niche_catalog);
    const { data: nrows } = await supabase.from("niches").select("niche_id,name,is_base,access_type,exclusive_to,default_hashtags").eq("is_active", true);
    const me = user?.id ?? "";
    const entitledN = (nrows ?? []).filter((n: { access_type: string; is_base: boolean; exclusive_to: string | null }) =>
      n.exclusive_to === me || (n.access_type === "public" && (fullCatalog || n.is_base)));
    setNicheOpts(entitledN.map((n: { niche_id: string; name: string }) => ({ id: n.niche_id, name: n.name })));
    setNicheDefaults(Object.fromEntries(entitledN.map((n: { niche_id: string; default_hashtags: string[] | null }) => [n.niche_id, Array.isArray(n.default_hashtags) ? n.default_hashtags : []])));
    setLoading(false);
  }, [supabase, id]);

  useEffect(() => { load(); }, [load]);

  // [B11] Batch 1.7 — kembali dari consent Google (ret=/channels/[id]): tampilkan hasil + tab settings.
  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const r = sp.get("youtube");
    if (!r) return;
    const chName = sp.get("channel") || "";
    window.history.replaceState({}, "", `/channels/${id}`);
    setTab("settings");
    if (r === "connected") setYtFlash({ kind: "connected", text: chName });
    else if (r === "already") setYtFlash({ kind: "already", text: chName });
    else setYtFlash({ kind: "error", text: sp.get("reason") || "unknown" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // [B11] Hubungkan channel YouTube LAIN langsung dari sini (tanpa pindah menu) — balik ke halaman ini.
  async function connectAnotherYt() {
    setYtConnBusy(true); setErr(null);
    try {
      const r = await fetch("/api/youtube/connect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ label: "", ret: `/channels/${id}` }) });
      const j = await r.json();
      if (r.ok && j.authorize_url) { window.location.href = j.authorize_url; return; }
      setYtConnBusy(false); setErr(j.error || "Gagal memulai koneksi.");
    } catch { setYtConnBusy(false); setErr("Server tak terjangkau."); }
  }

  async function save() {
    setErr(null); setSaved(false); setBusy(true);
    const { error } = await supabase.from("channels").update({
      channel_name: name.trim() || null, content_language: clang, publish_privacy: privacy,
      youtube_account_id: ytAccountId || null, platform_channel_id: targetYt.trim() || null,
    }).eq("id", id);
    setBusy(false);
    // [B11] pagar DB ux_channels_tenant_target: target sudah dipakai channel lain → pesan manusiawi.
    if (error) { setErr(error.message.includes("ux_channels_tenant_target") ? "__dup_target__" : error.message); return; }
    setSaved(true); load();
  }

  if (loading) return <div className="muted" style={{ padding: "3rem", textAlign: "center" }}><Bi id="Memuat channel…" en="Loading channel…" /></div>;
  if (!ch) return (
    <Placeholder icon={<BarChart3 size={32} />} idT="Channel tidak ditemukan atau bukan milik Anda." enT="Channel not found or not yours." href="/channels" ctaId="Kembali ke Channels" ctaEn="Back to Channels" />
  );

  const name0 = ch.channel_name || "Channel";
  const eff = effectiveStatus(ch, sub, rd);

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
            {/* Std 0098 (all-time): Video terbit=videos.published · Views/Engagement=video_analytics latest-per-video (video MesinViral). Subscribers=channels.subscriber_count. RPC get_channel_analytics. */}
            <div className="item"><div className="v">{totalVids != null ? totalVids.toLocaleString("id-ID") : "—"}</div><div className="l"><Bi id="Video terbit" en="Published" /></div></div>
            <div className="item"><div className="v">{ch.subscriber_count != null ? ch.subscriber_count.toLocaleString("id-ID") : "—"}</div><div className="l">Subscribers</div></div>
            <div className="item" title="Akumulasi views video yang diproduksi MesinViral (per sinkronisasi terakhir). Total channel penuh → YouTube Studio."><div className="v">{chAnalytics?.total_views != null ? chAnalytics.total_views.toLocaleString("id-ID") : "—"}</div><div className="l"><Bi id="Total Views" en="Total Views" /></div></div>
            <div className="item" title="(like+komentar)/views video MesinViral, per sinkronisasi terakhir."><div className="v">{chAnalytics?.avg_engagement != null ? `${chAnalytics.avg_engagement}%` : "—"}</div><div className="l"><Bi id="Avg engagement" en="Avg engagement" /></div></div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {/* Tombol YouTube Studio dipindah ke tab Analytics (F2-13b) — tak lagi di header (buang duplikat). */}
          {/* F2-07: pause/play (is_active). Play ter-gate readiness. Sembunyikan saat halted/sub (pakai aksi di banner). */}
          {!ch.production_paused && (sub === null || ["active","trialing","trial","grace"].includes(sub)) && (
            ch.is_active
              ? <button className="btn btn-secondary" disabled={busy} onClick={askPause}><Pause size={15} /> <Bi id="Jeda" en="Pause" /></button>
              : <button className="btn btn-secondary" disabled={busy} onClick={() => pausePlay(true)}><Play size={15} /> <Bi id="Aktifkan" en="Activate" /></button>
          )}
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
                {eff.key === "incomplete" && <button className="btn btn-default btn-sm" onClick={() => setTab("settings")}><Settings size={14} /> <Bi id="Lengkapi konfigurasi" en="Complete config" /></button>}
                {eff.key === "paused" && <button className="btn btn-default btn-sm" disabled={busy} onClick={() => pausePlay(true)}><Play size={14} /> <Bi id="Aktifkan" en="Activate" /></button>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Uji produksi channel (reuse TestNichePanel): konfirmasi + progres live + hasil sopan + tautan YT Studio.
          runLabel & pesan hasil adaptif konteks (halted=pulihkan / aktif=pratinjau). onComplete → segarkan banner. */}
      <div style={{ marginBottom: "1rem" }}>
        <TestNichePanel
          getUrl={`/api/channels/${id}/test`}
          postUrl={`/api/channels/${id}/test`}
          title={<Bi id="Uji produksi channel" en="Channel production test" />}
          runLabel={eff.key === "halted" ? <Bi id="Jalankan uji & pulihkan" en="Run & recover" /> : <Bi id="Uji sekarang (privat)" en="Test now (private)" />}
          confirmMessage={<Bi id="Tindakan ini memproduksi 1 video uji (privat di YouTube) untuk memeriksa konfigurasi channel Anda. Lanjutkan?" en="This produces 1 test video (private on YouTube) to check your channel configuration. Continue?" />}
          renderResult={channelTestResult}
          onComplete={() => load()}
          hideRefresh
          hideSummary={isResultHidden}
        />
      </div>

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
            ) : (() => {
              // Checklist PENUH 🟢/🔴 (§2.3): tiap syarat tampil — hijau=lengkap, merah=kurang + link ke lokasi perbaikan.
              const has = (s: string) => rd.missing.some((m) => m.toLowerCase().includes(s));
              const REQS = [
                { id: "Niche", en: "Niche", bad: rd.missing.includes("niche"), kred: false, tab: "settings" as const },
                { id: "Penulis Naskah (LLM)", en: "Script Writer (LLM)", bad: has("naskah"), kred: has("kunci naskah"), tab: "settings" as const },
                { id: "Pengisi Suara (TTS)", en: "Voice (TTS)", bad: has("suara"), kred: has("kunci suara"), tab: "settings" as const },
                { id: "Pembuat Visual", en: "Visual generator", bad: has("visual"), kred: has("kunci visual"), tab: "settings" as const },
                { id: "Jadwal tayang", en: "Publish schedule", bad: has("jadwal"), kred: false, tab: "schedule" as const },
                { id: "Koneksi YouTube + target", en: "YouTube connection + target", bad: has("youtube"), kred: false, tab: "settings" as const },
                { id: "Telegram", en: "Telegram", bad: rd.missing.includes("Telegram"), kred: true, tab: "settings" as const },
              ];
              return (
                <>
                  <ul style={{ listStyle: "none", margin: "0 0 0.75rem", padding: 0 }}>
                    {REQS.map((r) => (
                      <li key={r.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "var(--text-sm)", padding: "0.3rem 0" }}>
                        {r.bad ? <span style={{ width: 9, height: 9, borderRadius: "50%", background: "var(--danger,#ef4444)", flexShrink: 0 }} />
                               : <Check size={14} style={{ color: "var(--success)", flexShrink: 0 }} />}
                        <span style={{ flex: 1, color: r.bad ? "var(--text-primary)" : "var(--text-secondary)" }}><Bi id={r.id} en={r.en} /></span>
                        {r.bad && (r.kred
                          ? <Link href="/integrations" className="link" style={{ fontSize: "var(--text-xs)" }}><Bi id="Perbaiki →" en="Fix →" /></Link>
                          : <button className="link" style={{ fontSize: "var(--text-xs)", background: "none", border: "none", cursor: "pointer", padding: 0, color: "var(--brand)" }} onClick={() => setTab(r.tab)}><Bi id="Perbaiki →" en="Fix →" /></button>)}
                      </li>
                    ))}
                  </ul>
                  {/* Aktifkan DI DALAM kartu — ENABLED hanya saat semua 🟢 + langganan aktif + tak dihentikan */}
                  {(sub === null || ["active", "trialing", "trial", "grace"].includes(sub)) && !ch.production_paused && (
                    ch.is_active
                      ? <span style={{ fontSize: "var(--text-sm)", color: "var(--success)", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}><Check size={15} /> <Bi id="Channel aktif & berproduksi" en="Channel active & producing" /></span>
                      : <button className="btn btn-default btn-sm" disabled={busy || !rd.ready} onClick={() => pausePlay(true)} title={rd.ready ? "" : "Lengkapi semua syarat dulu"}><Play size={14} /> <Bi id="Aktifkan channel" en="Activate channel" /></button>
                  )}
                </>
              );
            })()}
          </div>
          {/* Ringkasan kinerja — KPI nyata di header; kinerja-mesin menyusul (F5-05/F2-13) */}
          <div className="card card-pad">
            <h3 className="card-title" style={{ marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}><Activity size={18} /> <Bi id="Ringkasan kinerja" en="Performance summary" /></h3>
            <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}><Bi id="Statistik muncul setelah channel berproduksi. Detail per-channel ada di tab Analytics · Compliance · Wawasan." en="Stats appear once the channel produces. Per-channel detail lives in the Analytics · Compliance · Insights tabs." /></p>
          </div>
        </div>
      )}
      {tab === "runs" && <RunsTable channelId={id} />}
      {tab === "analytics" && (
        <div className="card card-pad">
          <h3 className="card-title" style={{ marginBottom: "0.75rem" }}><Bi id="Kinerja mesin — channel ini" en="Engine performance — this channel" /></h3>
          {(() => { const tot = chRunStats?.total ?? 0, ok = chRunStats?.success ?? 0, qc = chRunStats?.review ?? 0, fail = chRunStats?.failed ?? 0;
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
        <>
          {/* [B17-F0] Kurva Belajar per-channel — kartu paling atas (spec §2b penempatan 1) */}
          <LearningCurveCard channelId={id} scopeLabel={{ id: "channel ini", en: "this channel" }} />
          <InsightsView insights={chIns} loading={loading} scopeLabel={{ id: "channel ini", en: "this channel" }} learnedWeights={chLearned} />
        </>
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
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <label className="label"><Bi id="Channel YouTube tujuan" en="Target YouTube channel" /></label>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.6rem" }}><Bi id="Pilih channel YouTube tempat video channel ini terbit. Tidak perlu menyalin ID apa pun — cukup klik." en="Pick the YouTube channel this channel publishes to. No ID copying needed — just click." /></div>
              {/* [B11] Batch 1.7 — pesan hasil consent (connected/already/error) */}
              {ytFlash?.kind === "connected" && <div style={{ marginBottom: "0.5rem", fontSize: "var(--text-sm)", color: "var(--success)" }}><Check size={13} style={{ verticalAlign: "-2px" }} /> <Bi id={`Channel "${ytFlash.text}" tersambung — pilih di daftar di bawah lalu Simpan.`} en={`Channel "${ytFlash.text}" connected — select it below, then Save.`} /></div>}
              {ytFlash?.kind === "already" && <div style={{ marginBottom: "0.5rem", fontSize: "var(--text-sm)", color: "var(--success)" }}><Check size={13} style={{ verticalAlign: "-2px" }} /> <Bi id={`Channel "${ytFlash.text}" sudah pernah terhubung — koneksinya disegarkan (tidak dibuat ganda).`} en={`Channel "${ytFlash.text}" was already connected — refreshed (no duplicate).`} /></div>}
              {ytFlash?.kind === "error" && <div style={{ marginBottom: "0.5rem", fontSize: "var(--text-sm)", color: "var(--danger,#ef4444)" }}>{ytFlash.text === "identity_failed" ? <Bi id="Gagal membaca identitas channel dari Google — coba lagi." en="Could not read channel identity from Google — try again." /> : <Bi id={`Koneksi Google gagal (kode: ${ytFlash.text}) — coba lagi.`} en={`Google sign-in failed (code: ${ytFlash.text}) — try again.`} />}</div>}
              {/* Galeri koneksi (berwajah): terpakai channel lain = terkunci (cegatan redundant) */}
              <div style={{ display: "grid", gap: "0.5rem", marginBottom: "0.6rem" }}>
                {ytAccounts.length === 0 && <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum ada koneksi YouTube — hubungkan dengan tombol di bawah." en="No YouTube connection yet — connect with the button below." /></span>}
                {ytAccounts.map((a) => {
                  const others = (a.used_by || []).filter((u) => u.id !== id);
                  const lockedByOther = others.length > 0;
                  const sel = ytAccountId === a.id;
                  // Koneksi tanpa identitas (legacy pra-B11) TAK BISA dipilih — memilihnya = target NULL
                  // (bisa meng-NULL-kan target yang sudah benar). Wajib re-connect dulu.
                  const selectable = a.connected && !!a.yt_channel_id && !lockedByOther;
                  return (
                    <div key={a.id} role="radio" aria-checked={sel} aria-disabled={!selectable}
                      onClick={() => {
                        if (!selectable) return;
                        // Channel draft boleh melepas pilihan (klik ulang); channel aktif wajib punya koneksi.
                        if (sel && !ch?.is_active) { setYtAccountId(""); setTargetYt(""); return; }
                        setYtAccountId(a.id); setTargetYt(a.yt_channel_id || "");
                      }}
                      style={{ display: "flex", alignItems: "center", gap: "0.625rem", padding: "0.5rem 0.625rem",
                        border: `1px solid ${sel ? "var(--accent)" : "var(--border-subtle)"}`, borderRadius: "var(--r-md)",
                        background: sel ? "var(--accent-soft)" : "transparent",
                        opacity: selectable || sel ? 1 : 0.55, cursor: selectable ? "pointer" : "not-allowed" }}>
                      {a.yt_channel_thumb
                        ? <img src={a.yt_channel_thumb} alt="" style={{ width: 32, height: 32, borderRadius: "50%", objectFit: "cover", flex: "none" }} referrerPolicy="no-referrer" />
                        : <span style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--surface-2)", display: "grid", placeItems: "center", color: "var(--text-muted)", flex: "none" }}><Video size={14} /></span>}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.yt_channel_title || a.label}</div>
                        <div className="muted" style={{ fontSize: "0.625rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}><code>{a.yt_channel_id || "—"}</code></div>
                      </div>
                      {sel ? <span className="badge badge-success" style={{ fontSize: "0.625rem", flex: "none" }}><Check size={11} /> <Bi id="Dipilih" en="Selected" /></span>
                        : lockedByOther ? <span className="badge badge-default" style={{ fontSize: "0.625rem", flex: "none" }} title={others.map((u) => u.channel_name).join(", ")}><Lock size={10} /> <Bi id={`Dipakai oleh ${others[0].channel_name}`} en={`Used by ${others[0].channel_name}`} /></span>
                        : !a.connected ? <span className="badge badge-default" style={{ fontSize: "0.625rem", flex: "none" }}><Bi id="Belum selesai connect" en="Connect unfinished" /></span>
                        : !a.yt_channel_id ? <span className="badge badge-default" style={{ fontSize: "0.625rem", flex: "none" }}><Bi id="Hubungkan ulang dulu (identitas belum terbaca)" en="Reconnect first (identity missing)" /></span>
                        : <span className="badge badge-default" style={{ fontSize: "0.625rem", flex: "none" }}><Bi id="Tersedia" en="Available" /></span>}
                    </div>
                  );
                })}
              </div>
              <button className="btn btn-secondary btn-sm" onClick={connectAnotherYt} disabled={ytConnBusy}>
                {ytConnBusy ? <Loader2 size={14} className="spin" /> : <><Plus size={13} /> <Bi id="Hubungkan channel YouTube lain" en="Connect another YouTube channel" /></>}
              </button>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.4rem" }}><Bi id="Anda akan diarahkan ke Google — pilih channel yang diinginkan di layar Google (satu izin per channel). ID tujuan terisi otomatis, tak bisa diubah manual." en="You'll be sent to Google — pick the channel on Google's screen (one consent per channel). The target ID is auto-filled and never manually edited." /></div>
            </div>
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
              <label className="label"><Bi id="Niche channel" en="Channel niche" /></label>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.6rem" }}>
                <Bi id="Pilih 1 niche → channel fokus 1 tema. Pilih lebih dari 1 → otomatis diacak antar tema terpilih." en="Pick 1 niche → single-theme channel. Pick more than 1 → auto-shuffled across selected themes." />
              </div>
              {/* Terpilih (chip, bisa dihapus) */}
              {pool.length > 0 && (
                <div className="chip-input" style={{ marginBottom: "0.5rem" }}>
                  {pool.map((pid) => (
                    <span key={pid} className="chip">{nicheOpts.find((o) => o.id === pid)?.name ?? pid}
                      <span className="x" onClick={() => setPool(pool.filter((x) => x !== pid))}><X size={12} /></span></span>
                  ))}
                </div>
              )}
              {/* Kotak cari (skala ratusan niche) */}
              <div style={{ position: "relative", marginBottom: "0.5rem" }}>
                <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
                <input className="input" style={{ paddingLeft: 30 }} placeholder="Cari niche…" value={nicheSearch} onChange={(e) => setNicheSearch(e.target.value)} />
              </div>
              {/* Hasil ter-filter — niche yang tersedia utk tenant & belum dipilih */}
              <div className="radio-row" style={{ maxHeight: 180, overflowY: "auto" }}>
                {nicheOpts.filter((o) => !pool.includes(o.id) && o.name.toLowerCase().includes(nicheSearch.toLowerCase())).map((n) => (
                  <span key={n.id} className="radio-pill" onClick={() => { setPool([...pool, n.id]); setNicheSearch(""); }}><Plus size={11} /> {n.name}</span>
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginTop: "0.6rem" }}>
                <span className="badge">{pool.length > 1 ? <><Shuffle size={12} /> <Bi id="Acak" en="Random" /></> : <Bi id="Tetap (1 niche)" en="Fixed (1 niche)" />}</span>
                <button className="btn btn-secondary btn-sm" onClick={saveNiche} disabled={savingNiche || pool.length === 0}>{savingNiche ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan niche" en="Save niche" />}</button>
              </div>
              <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "0.4rem" }}>
                <Bi id="Hanya niche yang tersedia untuk paket Anda + niche khusus milik Anda." en="Only niches available to your plan + your own custom niches." />
                {" "}<Link href="/niches" className="link"><Bi id="Ajukan niche khusus →" en="Request custom niche →" /></Link>
              </div>
              {nicheMsg && <div style={{ fontSize: "var(--text-sm)", marginTop: "0.4rem", color: nicheMsg.includes("tersimpan") ? "var(--success)" : "var(--danger,#ef4444)" }}>{nicheMsg}</div>}
            </div>
            {err && <div style={{ color: "var(--danger, #ef4444)", fontSize: "var(--text-sm)" }}>{err === "__dup_target__" ? <Bi id="Channel YouTube ini sudah dipakai channel lain — satu channel YouTube hanya untuk satu channel MesinViral." en="This YouTube channel is already used by another channel — one YouTube channel maps to one MesinViral channel." /> : err}</div>}
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

        {/* Catatan kunci → Kredensial (pindah dari sini ke Page Credential, tenant-wide) */}
        <div className="tip" style={{ maxWidth: 560, marginTop: "1rem", fontSize: "var(--text-xs)", display: "flex", gap: 6, alignItems: "flex-start" }}>
          <Info size={14} style={{ flexShrink: 0, marginTop: 1 }} />
          <span><Bi id="Pilih penyedia & model AI di tiap kartu di bawah. Kunci API diisi SEKALI di " en="Pick the AI provider & model in each card below. API keys are set ONCE in " /><Link href="/integrations" className="link"><Bi id="Kredensial & Koneksi" en="Credentials & Connections" /></Link><Bi id=" (berlaku untuk semua channel)." en=" (applies to all channels)." /></span>
        </div>

        {/* CARD: Penulis Naskah (LLM) */}
        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.2rem", display: "flex", alignItems: "center", gap: 6 }}><PenLine size={15} /> <Bi id="Penulis Naskah (LLM)" en="Script Writer (LLM)" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.6rem" }}><Bi id="AI yang menulis cerita & narasi video. Makin pintar = naskah makin bagus." en="AI that writes your video's story & narration. Smarter = better script." /></p>
          <div className="fld-row"><div className="k"><Bi id="Penyedia" en="Provider" /></div>
            <div className="radio-row">{[...new Set(llmOpts.map((m) => m.provider_key))].map((pk) => <span key={pk} className={`radio-pill${llmProv === pk ? " sel" : ""}`} onClick={() => { setLlmProv(pk); setLlmModel(""); }}>{provMap[pk]?.name ?? pk}</span>)}</div></div>
          {llmProv && (
            <div className="fld-row"><div className="k"><Bi id="Model" en="Model" /></div>
              <div className="radio-row">{llmOpts.filter((m) => m.provider_key === llmProv).map((m) => <span key={m.model_key} title={priceTitle(m, "llm")} className={`radio-pill${llmModel === m.model_key ? " sel" : ""}`} onClick={() => setLlmModel(m.model_key)}>{m.display_name}<ModelBadges m={m} /></span>)}</div></div>
          )}
          {acctPicker(llmProv, llmAcct, setLlmAcct)}
          <div className="save-bar">{aiMsg?.el === "llm" && <span style={{ color: aiMsg.ok ? "var(--success)" : "var(--danger,#ef4444)" }}>{aiMsg.text}</span>}<button className="btn btn-default btn-sm" disabled={savingAi === "llm"} onClick={saveLlm}>{savingAi === "llm" ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan" en="Save" />}</button></div>
        </div>

        {/* CARD: Pengisi Suara (TTS) */}
        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.2rem", display: "flex", alignItems: "center", gap: 6 }}><Mic size={15} /> <Bi id="Pengisi Suara (TTS)" en="Voice (TTS)" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.6rem" }}><Bi id="Suara narator: pilih penyedia → model → karakter suara (▶ dengar contoh)." en="Narrator voice: pick provider → model → character (▶ preview)." /></p>
          <div className="fld-row"><div className="k"><Bi id="Penyedia suara" en="Voice provider" /></div>
            <div className="radio-row">{ttsOpts.map((p) => <span key={p.provider_key} className={`radio-pill${ttsProv === p.provider_key ? " sel" : ""}`} onClick={() => { setTtsProv(p.provider_key); setTtsModel(""); setVoiceKey(""); }}>{p.display_name}</span>)}</div></div>
          {ttsProv && ttsModelOpts.filter((m) => m.provider_key === ttsProv).length > 0 && (
            <div className="fld-row"><div className="k"><Bi id="Model suara" en="Voice model" /><div className="sub"><Bi id="kualitas vs kecepatan" en="quality vs speed" /></div></div>
              <div className="radio-row">{ttsModelOpts.filter((m) => m.provider_key === ttsProv).map((m) => <span key={m.model_key} title={priceTitle(m, "tts")} className={`radio-pill${ttsModel === m.model_key ? " sel" : ""}`} onClick={() => setTtsModel(m.model_key)}>{m.display_name}<ModelBadges m={m} /></span>)}</div></div>
          )}
          {ttsProv && (() => {
            // Kecocokan bahasa konten channel (0131): cocok = locale voice se-bahasa ATAU voice Multilingual.
            // Voice tak cocok TETAP bisa dipilih (mis. ElevenLabs multilingual sudah tertanda cocok),
            // tapi diberi tanda jelas agar tenant awam tidak salah pilih suara beda bahasa.
            const langPrim = (clang || "en-US").split("-")[0].toLowerCase();
            const fits = (v: VoiceOpt) => (v.language || "") === "Multilingual" || (v.locale || "").toLowerCase().startsWith(langPrim);
            const list = voiceAll.filter((v) => v.provider_key === ttsProv).slice().sort((a, b) => Number(fits(b)) - Number(fits(a)));
            return (
              <div className="fld-row"><div className="k"><Bi id="Karakter suara" en="Voice character" /><div className="sub"><Bi id="urut: cocok bahasa konten dulu" en="sorted: content-language match first" /></div></div>
                <div className="radio-row">{list.map((v) => <span key={v.voice_key} className={`radio-pill${(voiceKey || "") === v.voice_key ? " sel" : ""}`} title={fits(v) ? undefined : `Bahasa voice: ${v.language || v.locale || "?"} — beda dari bahasa konten channel ini`} onClick={() => setVoiceKey(v.voice_key)}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Mic size={13} />{v.display_name}{v.gender ? ` · ${v.gender}` : ""}
                    {!fits(v) && <span className="muted" style={{ fontSize: ".625rem" }}>· {v.language || v.locale}</span>}</span>
                  {v.preview_url ? <span role="button" aria-label={playingVoice === v.voice_key ? "Stop" : "Dengar contoh"} title={playingVoice === v.voice_key ? "Stop" : "Dengar contoh"} style={{ cursor: "pointer", marginLeft: 5, fontWeight: 600 }} onClick={(e) => { e.stopPropagation(); toggleVoice(v.voice_key, v.preview_url as string); }}>{playingVoice === v.voice_key ? "⏹" : "▶"}</span> : null}
                </span>)}</div></div>
            );
          })()}
          {acctPicker(ttsProv, ttsAcct, setTtsAcct)}
          <div className="save-bar">{aiMsg?.el === "tts" && <span style={{ color: aiMsg.ok ? "var(--success)" : "var(--danger,#ef4444)" }}>{aiMsg.text}</span>}<button className="btn btn-default btn-sm" disabled={savingAi === "tts"} onClick={saveTts}>{savingAi === "tts" ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan" en="Save" />}</button></div>
        </div>

        {/* CARD: Pembuat Visual (Image/Video Generator) */}
        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.2rem", display: "flex", alignItems: "center", gap: 6 }}><ImageIcon size={15} /> <Bi id="Pembuat Visual (gambar/video)" en="Visual Generator (image/video)" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.6rem" }}><Bi id="Tiap adegan dibuat AI: pilih penyedia → model → kualitas." en="Each scene is AI-made: pick provider → model → quality." /></p>
          <div className="fld-row"><div className="k"><Bi id="Penyedia" en="Provider" /></div>
            <div className="radio-row">{[...new Set(imgOpts.map((m) => m.provider_key))].map((pk) => <span key={pk} className={`radio-pill${visualProv === pk ? " sel" : ""}`} onClick={() => { setVisualProv(pk); setImgModel(""); }}>{provMap[pk]?.name ?? pk}</span>)}</div></div>
          {visualProv && (
            <div className="fld-row"><div className="k"><Bi id="Model" en="Model" /><div className="sub"><Bi id="gambar atau video" en="image or video" /></div></div>
              <div className="radio-row">{imgOpts.filter((m) => m.provider_key === visualProv).map((m) => <span key={m.model_key} title={priceTitle(m, m.component || "image")} className={`radio-pill${imgModel === m.model_key ? " sel" : ""}`} onClick={() => setImgModel(m.model_key)}>{m.display_name}<ModelBadges m={m} /></span>)}</div></div>
          )}
          <div className="fld-row"><div className="k"><Bi id="Kualitas gambar" en="Image quality" /><div className="sub"><Bi id="makin tinggi makin bagus & makin mahal" en="higher = nicer & pricier" /></div></div>
            <div className="radio-row">{([["low", "Hemat", "Saver"], ["medium", "Seimbang", "Balanced"], ["high", "Terbaik", "Best"]] as [string, string, string][]).map(([q, idL, enL]) => <span key={q} className={`radio-pill${imgQuality === q ? " sel" : ""}`} onClick={() => setImgQuality(q)}><Bi id={idL} en={enL} /></span>)}</div></div>
          {acctPicker(visualProv, visualAcct, setVisualAcct)}
          <div className="save-bar">{aiMsg?.el === "visual" && <span style={{ color: aiMsg.ok ? "var(--success)" : "var(--danger,#ef4444)" }}>{aiMsg.text}</span>}<button className="btn btn-default btn-sm" disabled={savingAi === "visual"} onClick={saveVisual}>{savingAi === "visual" ? <Loader2 size={14} className="spin" /> : <Bi id="Simpan" en="Save" />}</button></div>
        </div>

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 760 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Caption (subtitle video)" en="Caption (video subtitles)" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Tampilan teks subtitle yang muncul di dalam video (brand channel ini)." en="On-screen subtitle styling shown inside the video (this channel's brand)." /></p>
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
          <div className="save-bar" style={{ marginTop: "1rem" }}><span className="muted">{brandMsg ?? <Bi id="Disimpan ke channel (caption)" en="Saves to channel (caption)" />}</span><button className="btn btn-default" disabled={savingBrand} onClick={saveCaption}>{savingBrand ? "Menyimpan…" : <Bi id="Simpan caption" en="Save caption" />}</button></div>
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
          <div className="fld-row"><div className="k"><Bi id="Logo brand" en="Brand logo" /><div className="sub"><Bi id="PNG transparan · maks 220×220px · overlay di video" en="transparent PNG · max 220×220px · video overlay" /></div></div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: 360 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <label className="btn btn-secondary btn-sm" style={{ cursor: logoUploading ? "default" : "pointer", opacity: logoUploading ? 0.7 : 1 }}>
                  {logoUploading ? <Loader2 size={14} className="spin" /> : <Upload size={14} />} <Bi id="Unggah PNG" en="Upload PNG" />
                  <input type="file" accept="image/png,.png" disabled={logoUploading} onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadLogo(f); e.target.value = ""; }} style={{ display: "none" }} />
                </label>
                {brandLogo && <img src={brandLogo} alt="logo" style={{ height: 36, maxWidth: 96, objectFit: "contain", borderRadius: "var(--r-sm)", border: "1px solid var(--border)", background: "var(--surface-2)", padding: 3 }} />}
              </div>
              <input className="input input-mono" value={brandLogo} onChange={(e) => setBrandLogo(e.target.value)} placeholder="atau tempel URL https://… .png" style={{ fontSize: "var(--text-xs)" }} />
            </div></div>
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

        <div className="card card-pad" style={{ marginTop: "1rem", maxWidth: 560 }}>
          <h3 className="card-title" style={{ marginBottom: "0.35rem" }}><Bi id="Hashtag" en="Hashtags" /></h3>
          <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1rem" }}><Bi id="Hashtag postingan per niche di pool channel ini. Dikosongkan = otomatis pakai default niche." en="Post hashtags per niche in this channel's pool. Left empty = uses the niche default automatically." /></p>
          <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: "0.75rem" }}><Bi id="Pisahkan dengan koma. Tanda # otomatis." en="Comma-separated. # added automatically." /></div>
          {pool.length === 0 && <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Pilih niche dulu di kartu Pengaturan di atas." en="Pick a niche in the Settings card above first." /></div>}
          {pool.map((pid) => {
            const nm = nicheOpts.find((o) => o.id === pid)?.name ?? pid;
            const def = (nicheDefaults[pid] ?? []).join(", ");
            return (
              <div key={pid} style={{ marginBottom: "0.625rem" }}>
                <label className="muted" style={{ fontSize: "var(--text-xs)", display: "block", marginBottom: "0.2rem" }}>{nm}</label>
                <input className="input" value={tags[pid] ?? ""} onChange={(e) => setTags({ ...tags, [pid]: e.target.value })} placeholder={def ? `Default niche: ${def}` : "space, science, viral"} />
              </div>
            );
          })}
          <div className="save-bar"><span className="muted">{hashMsg ?? <Bi id="Disimpan ke channel (hashtag)" en="Saves to channel (hashtags)" />}</span><button className="btn btn-default" disabled={savingHash} onClick={saveHashtags}>{savingHash ? "Menyimpan…" : <Bi id="Simpan hashtag" en="Save hashtags" />}</button></div>
        </div>

        </>
      )}

      <ConfirmDialog
        open={!!confirmCfg}
        title={confirmCfg?.title}
        message={confirmCfg?.message}
        confirmLabel={confirmCfg?.confirmLabel}
        confirmClass={confirmCfg?.confirmClass}
        busy={busy}
        onConfirm={() => confirmCfg?.onConfirm()}
        onCancel={() => setConfirmCfg(null)}
      />
    </>
  );
}
