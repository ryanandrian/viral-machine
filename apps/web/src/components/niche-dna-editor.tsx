"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Sparkles, Music, Image as ImageIcon, Clock3, Gauge, User, Plus, X, AlertTriangle, Video } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { validateDnaPatch, PERSONA_KEYS, VISUAL_CORE_KEYS, SECTION_KEYS, SECTION_LABELS, type DnaErrors } from "@/lib/niche-dna";
import { YT_CATEGORIES } from "@/lib/youtube-categories";

// NICHE DNA EDITOR — SATU komponen utk ADMIN & TENANT (kesepakatan owner 2026-07-04: fungsi & alur
// identik; beda hanya kepemilikan — di-enforce server). Prinsip:
// - NOL JSON mentah: tiap properti dipecah per-kotak ber-label awam + panduan + contoh.
// - PRESET dua tingkat: per-SECTION ("mulai cepat", replace) + saran per-FIELD (chip klik);
//   properti daftar (larangan/quality/mood) = MERGE (gabung, dedup). Semua kotak tetap teks bebas.
// - Validasi jujur (lib/niche-dna, sama dgn server): salah → pesan per-field + Simpan disabled.
// - DB TIDAK berubah: load = pecah JSON kolom niches; save = rakit kembali bentuk PERSIS yang
//   dibaca pipeline (audit NICHE_DNA_AUDIT_REMEDIATION.md).

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }

type Preset = { id: string; property: string; preset_key: string; label: string; label_en: string | null; description: string | null; description_en: string | null; value: unknown; apply_mode: string; sort_order: number };
type Mood = { mood_id: string };
type Track = { id: string; name: string; mood: string; niche: string | null; is_active: boolean };
export type NicheRow = Record<string, unknown> & { niche_id: string };

// ---- util bentuk ----
const asDict = (v: unknown): Record<string, string> => (v && typeof v === "object" && !Array.isArray(v)) ? Object.fromEntries(Object.entries(v as object).map(([k, x]) => [k, String(x ?? "")])) : {};
const asArr = (v: unknown): string[] => Array.isArray(v) ? (v as unknown[]).map(String) : [];
const asStr = (v: unknown): string => (v == null ? "" : String(v));
const mergeCsv = (cur: string, add: string) => {
  const items = [...cur.split(","), ...add.split(",")].map((s) => s.trim()).filter(Boolean);
  return [...new Set(items)].join(", ");
};

// ---- input chip kecil (keywords/hashtags/mood) ----
function ChipInput({ value, onChange, placeholder, suggestions }: { value: string[]; onChange: (v: string[]) => void; placeholder?: string; suggestions?: string[] }) {
  const [txt, setTxt] = useState("");
  const add = (s: string) => { const t = s.trim(); if (t && !value.includes(t)) onChange([...value, t]); setTxt(""); };
  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: ".35rem", marginBottom: value.length ? ".4rem" : 0 }}>
        {value.map((v, i) => (
          <span key={v} className="badge badge-default" style={{ display: "inline-flex", alignItems: "center", gap: ".25rem" }}>
            {i + 1 <= 99 ? "" : ""}{v}
            <X size={11} style={{ cursor: "pointer" }} onClick={() => onChange(value.filter((x) => x !== v))} />
          </span>
        ))}
      </div>
      <input className="input" value={txt} placeholder={placeholder ?? "ketik lalu Enter"}
        onChange={(e) => setTxt(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(txt); } }}
        onBlur={() => txt.trim() && add(txt)} />
      {suggestions && suggestions.filter((s) => !value.includes(s)).length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: ".3rem", marginTop: ".4rem" }}>
          {suggestions.filter((s) => !value.includes(s)).map((s) => (
            <button key={s} type="button" className="btn btn-ghost btn-sm" style={{ padding: "0 .5rem", height: 22, fontSize: "0.6875rem" }} onClick={() => add(s)}>+ {s}</button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---- pemilih preset section ----
function PresetPicker({ presets, onApply, mergeHint }: { presets: Preset[]; onApply: (p: Preset) => void; mergeHint?: boolean }) {
  if (!presets.length) return null;
  return (
    <div style={{ marginBottom: ".75rem" }}>
      <div className="muted" style={{ fontSize: "var(--text-xs)", marginBottom: ".35rem", display: "flex", alignItems: "center", gap: ".35rem" }}>
        <Sparkles size={12} style={{ color: "var(--accent)" }} />
        {mergeHint ? <Bi id="Mulai cepat — boleh pilih beberapa (digabung):" en="Quick start — pick multiple (merged):" /> : <Bi id="Mulai cepat — pilih satu (mengisi semua kotak di bawah):" en="Quick start — pick one (fills all boxes below):" />}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: ".4rem" }}>
        {presets.map((p) => (
          <button key={p.id} type="button" className="btn btn-secondary btn-sm" title={p.description ?? undefined} onClick={() => onApply(p)}>
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Sec({ icon, titleId, titleEn, subId, subEn, children }: { icon: React.ReactNode; titleId: string; titleEn: string; subId: string; subEn: string; children: React.ReactNode }) {
  return (
    <div className="card card-pad" style={{ marginBottom: "1rem" }}>
      <div style={{ marginBottom: ".75rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: ".5rem", fontWeight: 600 }}>{icon} <Bi id={titleId} en={titleEn} /></div>
        <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".15rem" }}><Bi id={subId} en={subEn} /></div>
      </div>
      <div style={{ display: "grid", gap: ".75rem" }}>{children}</div>
    </div>
  );
}

function Fld({ label, hint, error, children }: { label: React.ReactNode; hint?: React.ReactNode; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {hint && !error && <div className="muted" style={{ fontSize: "0.6875rem", marginTop: ".25rem" }}>{hint}</div>}
      {error && <div style={{ fontSize: "0.6875rem", marginTop: ".25rem", color: "var(--danger)", display: "flex", gap: ".3rem", alignItems: "center" }}><AlertTriangle size={11} /> {error}</div>}
    </div>
  );
}

const STYLE_SUGGESTIONS = ["mysterious and awe-inspiring", "fun and energetic", "dark and gripping", "warm and reassuring", "smart and curious"];
const EMOTION_SUGGESTIONS = ["wonder and curiosity", "chills and dread", "surprise and delight", "calm and motivation", "excitement"];
const HOOK_FORMULAS = ["question", "impossible_claim", "you_dont_know", "number_shock", "story_open"];

export default function NicheDnaEditor({ niche, onSave, busy, onCancel }: { niche: NicheRow; onSave: (patch: Record<string, unknown>) => Promise<{ ok: boolean; fields?: DnaErrors }>; busy: boolean; onCancel?: () => void }) {
  // draft terstruktur (bukan JSON string)
  const [name, setName] = useState(asStr(niche.name));
  const [descId, setDescId] = useState(asStr(niche.description));       // 0135: deskripsi etalase (ID)
  const [descEn, setDescEn] = useState(asStr(niche.description_en));    // 0135: deskripsi etalase (EN)
  const [keywords, setKeywords] = useState(asArr(niche.keywords));
  const [hashtags, setHashtags] = useState(asArr(niche.default_hashtags));
  const [ytCat, setYtCat] = useState(asStr(niche.youtube_category_id));
  const [style, setStyle] = useState(asStr(niche.style));
  const [emotion, setEmotion] = useState(asStr(niche.target_emotion));
  const [persona, setPersona] = useState<Record<string, string>>({ ...Object.fromEntries(PERSONA_KEYS.map((k) => [k, ""])), ...asDict(niche.narration_persona) });
  // [EKSPRESI VOKAL 2026-07-16] {style, stability} 0..1 · null = ikut bawaan suara (voice_catalog).
  const _ve0 = (niche as { voice_expression?: { style?: number; stability?: number } | null }).voice_expression ?? null;
  const [veOn, setVeOn] = useState<boolean>(!!_ve0);
  const [veStyle, setVeStyle] = useState<number>(typeof _ve0?.style === "number" ? _ve0.style : 0.5);
  const [veStab, setVeStab] = useState<number>(typeof _ve0?.stability === "number" ? _ve0.stability : 0.4);
  // camera_motion = objek bersarang (Ken Burns), DIKELUARKAN dari dict visual datar → dikelola state terpisah.
  const _vs0 = asDict(niche.visual_style);
  const { camera_motion: _cm0, ..._vsFlat } = _vs0 as Record<string, unknown>;
  const [visual, setVisual] = useState<Record<string, string>>({ ...Object.fromEntries(VISUAL_CORE_KEYS.map((k) => [k, ""])), ...(_vsFlat as Record<string, string>) });
  const _cmIntensity0 = (asDict(_cm0).intensity as string) || "normal";
  const [cameraMotion, setCameraMotion] = useState<string>(["halus", "normal", "dinamis", "cepat"].includes(_cmIntensity0) ? _cmIntensity0 : "normal");
  const [newVisKey, setNewVisKey] = useState("");
  const [qualityTags, setQualityTags] = useState(asStr(niche.image_quality_tags));
  const [negPrompt, setNegPrompt] = useState(asStr(niche.image_negative_prompt));
  const [fallbacks, setFallbacks] = useState(asArr(niche.visual_fallbacks).join("\n"));
  const mc0 = asDict(niche.music_config);
  const [musicMode, setMusicMode] = useState(mc0.mode || "auto");
  const [musicMood, setMusicMood] = useState(mc0.mood || "");
  const [musicTrack, setMusicTrack] = useState(mc0.track_id || "");
  const [moodPriority, setMoodPriority] = useState(asArr(niche.mood_priority));
  const st0 = asDict(niche.section_timing);
  const [timing, setTiming] = useState<Record<string, string>>(Object.fromEntries(SECTION_KEYS.map((k) => [k, st0[k] ?? ""])));
  const [scoring, setScoring] = useState(asStr(niche.emotion_scoring_criteria));

  // katalog + preset (baca langsung — RLS: presets public-read; moods/music_library terbuka baca)
  const [presets, setPresets] = useState<Preset[]>([]);
  const [moods, setMoods] = useState<Mood[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  useEffect(() => {
    const sb = createClient();
    sb.from("niche_property_presets").select("*").eq("is_active", true).order("sort_order").then(({ data }) => setPresets((data as Preset[]) ?? []));
    sb.from("moods").select("mood_id").eq("is_active", true).order("mood_id").then(({ data }) => setMoods((data as Mood[]) ?? []));
    sb.from("music_library").select("id,name,mood,niche,is_active").eq("is_active", true).order("name").then(({ data }) => setTracks((data as Track[]) ?? []));
  }, []);
  const presetsFor = useCallback((prop: string) => presets.filter((p) => p.property === prop), [presets]);

  // Preview musik play/stop (owner 2026-07-04): PEMUTAR TUNGGAL; URL via presign (bucket aset privat).
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);
  useEffect(() => () => { audioRef.current?.pause(); }, []);
  async function toggleTrack(id: string) {
    if (playingId === id) { audioRef.current?.pause(); audioRef.current = null; setPlayingId(null); return; }
    audioRef.current?.pause();
    const r = await fetch(`/api/music/preview?id=${id}`).catch(() => null);
    const j = await r?.json().catch(() => ({}));
    if (!j?.url) { setPlayingId(null); return; }
    const audio = new Audio(j.url);
    audio.addEventListener("ended", () => { if (audioRef.current === audio) { audioRef.current = null; setPlayingId(null); } });
    audio.play().catch(() => { if (audioRef.current === audio) { audioRef.current = null; setPlayingId(null); } });
    audioRef.current = audio;
    setPlayingId(id);
  }
  const trackCountByMood = useMemo(() => {
    const m = new Map<string, number>();
    tracks.forEach((t) => m.set(t.mood, (m.get(t.mood) ?? 0) + 1));
    return m;
  }, [tracks]);
  const nicheTrackCount = useMemo(() => tracks.filter((t) => t.niche === niche.niche_id || moodPriority.includes(t.mood)).length, [tracks, niche.niche_id, moodPriority]);

  // rakit patch (bentuk PERSIS konsumen pipeline)
  const patch = useMemo(() => {
    const personaClean = Object.fromEntries(Object.entries(persona).filter(([, v]) => v.trim() !== ""));
    // visual_style datar + suntikkan kembali camera_motion (Ken Burns, per-karakter niche).
    const visualClean: Record<string, unknown> = Object.fromEntries(Object.entries(visual).filter(([, v]) => v.trim() !== ""));
    visualClean.camera_motion = { intensity: cameraMotion };
    const music: Record<string, string> = { mode: musicMode };
    if (musicMode === "random" && musicMood) music.mood = musicMood;
    if (musicMode === "fixed" && musicTrack) music.track_id = musicTrack;
    const timingVals = Object.values(timing).some((v) => String(v).trim() !== "")
      ? Object.fromEntries(SECTION_KEYS.map((k) => [k, Number(timing[k])]))
      : {};
    return {
      name: name.trim(), description: descId.trim() || null, description_en: descEn.trim() || null,
      keywords, default_hashtags: hashtags, youtube_category_id: ytCat || null,
      style, target_emotion: emotion,
      narration_persona: personaClean, visual_style: visualClean,
      voice_expression: veOn ? { style: veStyle, stability: veStab } : null,
      image_quality_tags: qualityTags, image_negative_prompt: negPrompt,
      visual_fallbacks: fallbacks.split("\n").map((s) => s.trim()).filter(Boolean),
      music_config: music, mood_priority: moodPriority,
      section_timing: timingVals, emotion_scoring_criteria: scoring,
    };
  }, [name, descId, descEn, keywords, hashtags, ytCat, style, emotion, persona, visual, cameraMotion, qualityTags, negPrompt, fallbacks, musicMode, musicMood, musicTrack, moodPriority, timing, scoring, veOn, veStyle, veStab]);

  const errors = useMemo(() => {
    const e = validateDnaPatch(patch);
    if (musicMode === "fixed" && !musicTrack) e.music_config = "Pilih track untuk mode 'satu lagu tetap'.";
    return e;
  }, [patch, musicMode, musicTrack]);
  const valid = Object.keys(errors).length === 0;

  const totalTiming = SECTION_KEYS.reduce((a, k) => a + (Number(timing[k]) || 0), 0);
  const timingEmpty = Object.values(timing).every((v) => String(v).trim() === "");

  // penerapan preset
  const applyPersona = (p: Preset) => setPersona({ ...Object.fromEntries(PERSONA_KEYS.map((k) => [k, ""])), ...asDict(p.value) });
  const applyVisual = (p: Preset) => setVisual({ ...Object.fromEntries(VISUAL_CORE_KEYS.map((k) => [k, ""])), ...asDict(p.value) });
  const applyTiming = (p: Preset) => { const v = asDict(p.value); setTiming(Object.fromEntries(SECTION_KEYS.map((k) => [k, v[k] ?? ""]))); };
  const applyScoring = (p: Preset) => setScoring(asStr(p.value));
  const applyQuality = (p: Preset) => setQualityTags((c) => mergeCsv(c, asStr(p.value)));
  const applyNeg = (p: Preset) => setNegPrompt((c) => mergeCsv(c, asStr(p.value)));
  const applyMoods = (p: Preset) => setMoodPriority((c) => [...new Set([...c, ...asArr(p.value)])]);

  return (
    <div>
      <Sec icon={<User size={16} />} titleId="Identitas" titleEn="Identity"
        subId="Siapa niche ini & topik apa yang dicari mesin tren." subEn="What this niche is & what topics the engine hunts.">
        <Fld label={<Bi id="Nama tampilan" en="Display name" />} error={errors.name}>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </Fld>
        <Fld label={<Bi id="Deskripsi etalase (Indonesia)" en="Showcase description (Indonesian)" />}
          hint={<Bi id="1-2 kalimat menjual utk tenant: channel berisi video apa & rasanya seperti apa. Tampil di tabel & drawer Pustaka Niche. Tidak dipakai mesin produksi." en="1-2 selling sentences for tenants: what the channel contains & how it feels. Shown in the Niche Library table & drawer. Not used by the production engine." />}>
          <textarea className="textarea" rows={2} value={descId} onChange={(e) => setDescId(e.target.value)} placeholder="mis. Kisah kasus kriminal nyata dan misteri yang belum terpecahkan — dibawakan seperti detektif membaca berkas tengah malam." />
        </Fld>
        <Fld label={<Bi id="Deskripsi etalase (English)" en="Showcase description (English)" />}>
          <textarea className="textarea" rows={2} value={descEn} onChange={(e) => setDescEn(e.target.value)} placeholder="e.g. Real crime cases and unsolved mysteries — told like a detective reading the file at midnight." />
        </Fld>
        <Fld label={<Bi id="Kata kunci topik" en="Topic keywords" />} error={errors.keywords}
          hint={<Bi id="Dipakai mesin mencari tren & tag video. Isi kata khas topik niche ini (mis. imunitas, vitamin, kesehatan)." en="Used for trend hunting & video tags. Use words specific to this niche's topic." />}>
          <ChipInput value={keywords} onChange={setKeywords} placeholder="ketik kata kunci lalu Enter" />
        </Fld>
        <Fld label={<Bi id="Hashtag bawaan" en="Default hashtags" />} error={errors.default_hashtags}
          hint={<Bi id="Fallback hashtag deskripsi YouTube bila channel tidak menyetel sendiri (tanpa #)." en="YouTube description hashtag fallback when the channel sets none (no #)." />}>
          <ChipInput value={hashtags} onChange={setHashtags} placeholder="mis. KesehatanAlami" />
        </Fld>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".75rem" }}>
          <Fld label={<Bi id="Gaya konten (style)" en="Content style" />} error={errors.style}
            hint={<Bi id="Frasa singkat pengarah pemilihan topik." en="Short phrase steering topic selection." />}>
            <input className="input" value={style} onChange={(e) => setStyle(e.target.value)} placeholder="mis. mysterious and awe-inspiring" list="dna-style-dl" />
            <datalist id="dna-style-dl">{STYLE_SUGGESTIONS.map((s) => <option key={s} value={s} />)}</datalist>
          </Fld>
          <Fld label={<Bi id="Emosi target" en="Target emotion" />} error={errors.target_emotion}
            hint={<Bi id="Perasaan yang harus ditinggalkan video ke penonton." en="The feeling the video must leave behind." />}>
            <input className="input" value={emotion} onChange={(e) => setEmotion(e.target.value)} placeholder="mis. wonder and curiosity" list="dna-emo-dl" />
            <datalist id="dna-emo-dl">{EMOTION_SUGGESTIONS.map((s) => <option key={s} value={s} />)}</datalist>
          </Fld>
        </div>
        <Fld label={<Bi id="Kategori YouTube" en="YouTube category" />}>
          <select className="input" value={ytCat} onChange={(e) => setYtCat(e.target.value)}>
            <option value="">— default (Education) —</option>
            {YT_CATEGORIES.map(([id, nm]) => <option key={id} value={id}>{nm}</option>)}
          </select>
        </Fld>
      </Sec>

      <Sec icon={<Sparkles size={16} />} titleId="Kepribadian Narasi" titleEn="Narration Persona"
        subId="Karakter penulisan naskah (bukan pemilih suara — suara diatur di Channel)." subEn="Script-writing character (not the voice — voice is set on the Channel).">
        <PresetPicker presets={presetsFor("narration_persona")} onApply={applyPersona} />
        <Fld label={<Bi id="Nada bicara (tone)" en="Tone" />} hint={<Bi id="Bagaimana narasi terdengar di telinga penonton." en="How the narration feels to the viewer." />}>
          <input className="input" value={persona.tone ?? ""} onChange={(e) => setPersona({ ...persona, tone: e.target.value })} placeholder="mis. berwibawa namun memukau, seperti narator dokumenter" />
        </Fld>
        <Fld label={<Bi id="Gaya penyampaian (style)" en="Delivery style" />}>
          <input className="input" value={persona.style ?? ""} onChange={(e) => setPersona({ ...persona, style: e.target.value })} placeholder="mis. jeda dramatis, membangun ketegangan" />
        </Fld>
        <Fld label={<Bi id="Pantangan (avoid) — teks bebas, dipatuhi mesin apa adanya" en="Never say (avoid) — free text, obeyed verbatim" />}
          hint={<Bi id="Tuliskan hal yang TIDAK BOLEH dikatakan narasi — termasuk kepentingan bisnis Anda (mis. 'jangan menyatakan suplemen tidak diperlukan; jangan sebut merek kompetitor')." en="Write what the narration must NEVER say — including your business red lines (e.g. 'never claim supplements are unnecessary; never mention competitor brands')." />}>
          <textarea className="textarea" rows={3} value={persona.avoid ?? ""} onChange={(e) => setPersona({ ...persona, avoid: e.target.value })} />
        </Fld>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".75rem" }}>
          <Fld label={<Bi id="Formula hook" en="Hook formula" />} hint={<Bi id="Pola pembuka; boleh sebut beberapa." en="Opening pattern; may list several." />}>
            <input className="input" value={persona.hook_style ?? ""} onChange={(e) => setPersona({ ...persona, hook_style: e.target.value })} placeholder="mis. impossible_claim or number_shock" list="dna-hook-dl" />
            <datalist id="dna-hook-dl">{HOOK_FORMULAS.map((s) => <option key={s} value={s} />)}</datalist>
          </Fld>
          <Fld label={<Bi id="Kurva emosi" en="Emotion arc" />} hint={<Bi id="Perjalanan perasaan penonton dari awal ke akhir." en="The viewer's feeling journey start to end." />}>
            <input className="input" value={persona.emotion_arc ?? ""} onChange={(e) => setPersona({ ...persona, emotion_arc: e.target.value })} placeholder="mis. penasaran → kaget → takjub" />
          </Fld>
        </div>
        {errors.narration_persona && <div style={{ fontSize: "0.6875rem", color: "var(--danger)" }}>{errors.narration_persona}</div>}
      </Sec>

      {/* [EKSPRESI VOKAL 2026-07-16] gaya-baca narator per-niche — resmi menggantikan kenop warisan buta-layar */}
      <Sec icon={<Sparkles size={16} />} titleId="Ekspresi Vokal" titleEn="Vocal Expression"
        subId="Mengatur GAYA BACA narator untuk niche ini — lebih dramatis ↔ lebih tenang, lebih stabil ↔ lebih hidup. Berlaku untuk suara premium (ElevenLabs). Kosong = mengikuti karakter bawaan suara yang dipilih channel. Tempo bicara TIDAK diatur di sini — dijaga otomatis oleh mesin durasi."
        subEn="Sets the narrator's READING STYLE for this niche — more dramatic ↔ calmer, steadier ↔ livelier. Applies to premium voices (ElevenLabs). Empty = follows the chosen voice's own character. Speaking tempo is NOT set here — it is managed automatically by the duration engine.">
        <label style={{ display: "flex", alignItems: "center", gap: ".5rem", fontSize: "var(--text-sm)" }}>
          <input type="checkbox" checked={veOn} onChange={(e) => setVeOn(e.target.checked)} />
          <Bi id="Atur khusus untuk niche ini" en="Customize for this niche" />
        </label>
        {veOn && (<>
          <Fld label={<span><Bi id="Kedramatisan" en="Dramatic intensity" /> <span className="mono muted" style={{ fontSize: "0.6875rem" }}>({veStyle.toFixed(2)})</span></span>}
            hint={<Bi id="0 = datar/netral · 1 = sangat ekspresif/teatrikal." en="0 = flat/neutral · 1 = highly expressive/theatrical." />}>
            <input type="range" min={0} max={1} step={0.05} value={veStyle} onChange={(e) => setVeStyle(parseFloat(e.target.value))} style={{ width: "100%" }} />
          </Fld>
          <Fld label={<span><Bi id="Kestabilan" en="Stability" /> <span className="mono muted" style={{ fontSize: "0.6875rem" }}>({veStab.toFixed(2)})</span></span>}
            hint={<Bi id="0 = sangat hidup/bervariasi (bisa liar) · 1 = sangat stabil/konsisten (bisa monoton)." en="0 = very lively/varied (can get wild) · 1 = very steady/consistent (can be monotone)." />}>
            <input type="range" min={0} max={1} step={0.05} value={veStab} onChange={(e) => setVeStab(parseFloat(e.target.value))} style={{ width: "100%" }} />
          </Fld>
        </>)}
        {errors.voice_expression && <div style={{ fontSize: "0.6875rem", color: "var(--danger)" }}>{errors.voice_expression}</div>}
      </Sec>

      <Sec icon={<Music size={16} />} titleId="Musik" titleEn="Music"
        subId="Musik latar dipilih dari library sesuai kebijakan ini." subEn="Background music picked from the library by this policy.">
        <Fld label={<Bi id="Cara memilih musik" en="Music selection mode" />} error={errors.music_config}>
          <div className="radio-row">
            {[["auto", "Otomatis ikut isi naskah", "Auto by script"], ["random", "Acak dalam satu mood", "Random within a mood"], ["fixed", "Satu lagu tetap", "One fixed track"]].map(([v, idL, enL]) => (
              <span key={v} className={`radio-pill${musicMode === v ? " sel" : ""}`} onClick={() => setMusicMode(v)}><Bi id={idL} en={enL} /></span>
            ))}
          </div>
        </Fld>
        {musicMode === "random" && (
          <Fld label={<Bi id="Mood" en="Mood" />}>
            <select className="input" value={musicMood} onChange={(e) => setMusicMood(e.target.value)}>
              <option value="">— pilih mood —</option>
              {moods.map((m) => <option key={m.mood_id} value={m.mood_id}>{m.mood_id} ({trackCountByMood.get(m.mood_id) ?? 0} track)</option>)}
            </select>
          </Fld>
        )}
        {musicMode === "fixed" && (
          <Fld label={<Bi id="Track" en="Track" />}>
            <select className="input" value={musicTrack} onChange={(e) => setMusicTrack(e.target.value)}>
              <option value="">— pilih track —</option>
              {tracks.map((t) => <option key={t.id} value={t.id}>{t.name} · {t.mood}</option>)}
            </select>
          </Fld>
        )}
        <Fld label={<Bi id="Urutan mood prioritas" en="Mood priority order" />} error={errors.mood_priority}
          hint={<Bi id="Cadangan & rotasi: mesin memakai urutan ini bila deteksi otomatis tak yakin. Minimal 2." en="Fallback & rotation: the engine uses this order when auto-detection is unsure. Min 2." />}>
          <PresetPicker presets={presetsFor("mood_priority")} onApply={applyMoods} mergeHint />
          <ChipInput value={moodPriority} onChange={setMoodPriority} placeholder="pilih dari saran di bawah" suggestions={moods.map((m) => m.mood_id)} />
        </Fld>
        <div className="muted" style={{ fontSize: "0.6875rem", display: "flex", alignItems: "center", gap: ".35rem" }}>
          {nicheTrackCount > 0
            ? <><Music size={11} /> <Bi id={`${nicheTrackCount} track cocok tersedia di library untuk pilihan ini.`} en={`${nicheTrackCount} matching tracks available in the library.`} /></>
            : <><AlertTriangle size={11} style={{ color: "var(--warning)" }} /> <Bi id="Belum ada track yang cocok — mesin akan memakai track acak (kualitas musik tak terjaga)." en="No matching tracks yet — the engine will fall back to random tracks." /></>}
        </div>
        {(() => {
          // Dengarkan library (owner 2026-07-04): daftar track relevan dgn pilihan — ▶/⏹ pemutar tunggal.
          const relevant = tracks.filter((t) =>
            musicMode === "fixed" ? true
            : musicMode === "random" && musicMood ? t.mood === musicMood
            : (t.niche === niche.niche_id || moodPriority.includes(t.mood))).slice(0, 10);
          if (!relevant.length) return null;
          return (
            <div style={{ border: "1px solid var(--border-subtle)", borderRadius: "var(--r-md)", padding: ".4rem .6rem" }}>
              <div className="muted" style={{ fontSize: "0.6875rem", marginBottom: ".25rem" }}><Bi id="Dengarkan dulu dari library:" en="Preview from the library:" /></div>
              {relevant.map((t) => (
                <div key={t.id} style={{ display: "flex", alignItems: "center", gap: ".5rem", padding: ".15rem 0", fontSize: "var(--text-xs)" }}>
                  <button type="button" className="btn btn-ghost btn-sm" style={{ padding: "0 .4rem", height: 22 }} title={playingId === t.id ? "Stop" : "Putar"} onClick={() => toggleTrack(t.id)}>{playingId === t.id ? "⏹" : "▶"}</button>
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.name}</span>
                  <span className="badge badge-default" style={{ fontSize: "0.5625rem" }}>{t.mood}</span>
                  {musicMode === "fixed" && <button type="button" className="btn btn-secondary btn-sm" style={{ padding: "0 .5rem", height: 22, fontSize: "0.625rem" }} onClick={() => setMusicTrack(t.id)}>{musicTrack === t.id ? "✓ dipakai" : "pakai"}</button>}
                </div>
              ))}
            </div>
          );
        })()}
        {moodPriority.length > 0 && moodPriority.length < 2 && <div style={{ fontSize: "0.6875rem", color: "var(--warning)" }}><Bi id="Disarankan minimal 2 mood agar cadangan hidup." en="At least 2 moods recommended so fallback works." /></div>}
      </Sec>

      <Sec icon={<ImageIcon size={16} />} titleId="Gaya Visual" titleEn="Visual Style"
        subId="DNA gambar tiap adegan — di-inject ke prompt pembuat visual." subEn="Per-scene image DNA — injected into the visual generator prompts.">
        <PresetPicker presets={presetsFor("visual_style")} onApply={applyVisual} />
        <Fld label={<Bi id="Gaya dasar (base_style)" en="Base style" />} hint={<Bi id="Fondasi tampilan semua gambar." en="Foundation look of every image." />}>
          <input className="input" value={visual.base_style ?? ""} onChange={(e) => setVisual({ ...visual, base_style: e.target.value })} placeholder="mis. hyper-photorealistic cinematic photography" />
        </Fld>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".75rem" }}>
          <Fld label={<Bi id="Palet warna" en="Color palette" />}>
            <input className="input" value={visual.color_palette ?? ""} onChange={(e) => setVisual({ ...visual, color_palette: e.target.value })} placeholder="mis. deep contrast, rich natural tones" />
          </Fld>
          <Fld label={<Bi id="Atmosfer" en="Atmosphere" />}>
            <input className="input" value={visual.atmosphere ?? ""} onChange={(e) => setVisual({ ...visual, atmosphere: e.target.value })} placeholder="mis. dramatic, larger than life" />
          </Fld>
        </div>
        {Object.entries(visual).filter(([k]) => !(VISUAL_CORE_KEYS as readonly string[]).includes(k)).map(([k, v]) => (
          <div key={k} style={{ display: "flex", gap: ".5rem", alignItems: "end" }}>
            <Fld label={<span className="mono" style={{ fontSize: "0.6875rem" }}>{k}</span>}>
              <input className="input" value={v} onChange={(e) => setVisual({ ...visual, [k]: e.target.value })} />
            </Fld>
            <button type="button" className="btn btn-ghost btn-icon btn-sm" style={{ color: "var(--danger)", flex: "none", marginBottom: 2 }} onClick={() => { const nv = { ...visual }; delete nv[k]; setVisual(nv); }}><X size={13} /></button>
          </div>
        ))}
        <div style={{ display: "flex", gap: ".5rem", alignItems: "center" }}>
          <input className="input" style={{ maxWidth: 220 }} value={newVisKey} placeholder="properti tambahan (mis. lighting)" onChange={(e) => setNewVisKey(e.target.value.replace(/[^a-z0-9_]/g, ""))} />
          <button type="button" className="btn btn-secondary btn-sm" disabled={!newVisKey || newVisKey in visual} onClick={() => { setVisual({ ...visual, [newVisKey]: "" }); setNewVisKey(""); }}><Plus size={13} /> <Bi id="Tambah" en="Add" /></button>
        </div>
        {errors.visual_style && <div style={{ fontSize: "0.6875rem", color: "var(--danger)" }}>{errors.visual_style}</div>}
        <Fld label={<Bi id="Tag kualitas gambar" en="Image quality tags" />} error={errors.image_quality_tags}
          hint={<Bi id="Rangkaian kata kualitas yang ditempel ke setiap prompt gambar (pisah koma)." en="Quality words appended to every image prompt (comma separated)." />}>
          <PresetPicker presets={presetsFor("image_quality_tags")} onApply={applyQuality} mergeHint />
          <textarea className="textarea" rows={2} value={qualityTags} onChange={(e) => setQualityTags(e.target.value)} />
        </Fld>
        <Fld label={<Bi id="Larangan gambar (negative prompt)" en="Image bans (negative prompt)" />} error={errors.image_negative_prompt}
          hint={<Bi id="Hal yang dilarang muncul di gambar (pisah koma)." en="Things banned from images (comma separated)." />}>
          <PresetPicker presets={presetsFor("image_negative_prompt")} onApply={applyNeg} mergeHint />
          <textarea className="textarea" rows={2} value={negPrompt} onChange={(e) => setNegPrompt(e.target.value)} />
        </Fld>
        <Fld label={<Bi id="Contoh shot khas niche (1 baris = 1 shot)" en="Signature example shots (1 line = 1 shot)" />} error={errors.visual_fallbacks}
          hint={<Bi id="Contoh adegan visual khas niche ini — jadi acuan kualitas mesin (mis. 'teleskop berputar di bawah langit berbintang')." en="Signature scenes of this niche — used as the engine's quality reference." />}>
          <textarea className="textarea input-mono" rows={4} value={fallbacks} onChange={(e) => setFallbacks(e.target.value)} placeholder={"A single star sharpening into focus against black void\nRadio telescope rotating under star-dense night sky"} />
        </Fld>
      </Sec>

      <Sec icon={<Video size={16} />} titleId="Gerakan Kamera" titleEn="Camera Motion"
        subId="Seberapa 'hidup' gerakan zoom/geser pada video niche ini. Durasi & struktur video tidak berubah." subEn="How 'alive' the zoom/pan movement feels for this niche. Video duration & structure are unchanged.">
        <Fld label={<Bi id="Intensitas gerak" en="Motion intensity" />}
          hint={<Bi id="Berlaku untuk video 15–90 detik. Video 8 detik memakai video-AI (gerakan terpisah)." en="Applies to 15–90s videos. 8s videos use AI-video (separate motion)." />}>
          <div className="radio-row" style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
            {([["halus", "Halus", "Subtle", "pelan & tenang — niche kalem", "slow & calm — calm niches"],
               ["normal", "Normal", "Normal", "gerakan sedang — kebanyakan niche", "medium — most niches"],
               ["dinamis", "Dinamis", "Dynamic", "energik & terasa — niche seru", "energetic — lively niches"],
               ["cepat", "Cepat", "Fast", "paling enerjik — niche hype/cepat", "most energetic — hype/fast niches"]] as [string, string, string, string, string][])
              .map(([v, idL, enL, idH, enH]) => (
                <button type="button" key={v} className={`radio-pill${cameraMotion === v ? " sel" : ""}`}
                  style={{ flexDirection: "column", alignItems: "flex-start", gap: 2, padding: ".5rem .75rem", textAlign: "left" }}
                  onClick={() => setCameraMotion(v)}>
                  <span style={{ fontWeight: 600 }}><Bi id={idL} en={enL} /></span>
                  <span className="muted" style={{ fontSize: "0.625rem" }}><Bi id={idH} en={enH} /></span>
                </button>
              ))}
          </div>
        </Fld>
      </Sec>

      <Sec icon={<Clock3 size={16} />} titleId="Struktur Naskah" titleEn="Script Structure"
        subId="Pembagian detik per bagian naskah (basis 51 detik utk preset 60s — otomatis diskalakan ke durasi lain). Kosongkan semua = struktur standar mesin." subEn="Seconds per script section (51s basis for the 60s preset — auto-scaled to other durations). Leave all empty = engine default.">
        <PresetPicker presets={presetsFor("section_timing")} onApply={applyTiming} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: ".6rem" }}>
          {SECTION_KEYS.map((k) => {
            const [idL, enL, idH, enH] = SECTION_LABELS[k];
            return (
              <div key={k}>
                <label className="label" style={{ fontSize: "0.6875rem" }} title={idH}><Bi id={idL} en={enL} /></label>
                <input className="input" type="number" min={0} value={timing[k]} onChange={(e) => setTiming({ ...timing, [k]: e.target.value })} placeholder="dtk" title={`${idH} / ${enH}`} />
              </div>
            );
          })}
        </div>
        <div className="muted" style={{ fontSize: "0.6875rem" }}>
          {timingEmpty ? <Bi id="Kosong — memakai struktur standar mesin." en="Empty — using the engine's default structure." /> : <Bi id={`Total: ${totalTiming} detik.`} en={`Total: ${totalTiming} seconds.`} />}
        </div>
        {errors.section_timing && <div style={{ fontSize: "0.6875rem", color: "var(--danger)", display: "flex", gap: ".3rem", alignItems: "center" }}><AlertTriangle size={11} /> {errors.section_timing}</div>}
      </Sec>

      <Sec icon={<Gauge size={16} />} titleId="Kriteria Penilaian" titleEn="Scoring Criteria"
        subId="Standar emosi yang dipakai mesin menilai & menulis ulang naskah — makin spesifik makin tajam." subEn="The emotional bar the engine scores & rewrites against — the more specific the sharper.">
        <PresetPicker presets={presetsFor("emotion_scoring_criteria")} onApply={applyScoring} />
        <Fld label={<Bi id="Kriteria (bahasa bebas)" en="Criteria (free text)" />} error={errors.emotion_scoring_criteria}
          hint={<Bi id="Format ampuh: 'Skor 80+ bila …' + teknik yang sah + 'Skor RENDAH untuk …'." en="Strong format: 'Score 80+ if …' + valid techniques + 'Score LOW for …'." />}>
          <textarea className="textarea" rows={4} value={scoring} onChange={(e) => setScoring(e.target.value)} />
        </Fld>
      </Sec>

      <div style={{ display: "flex", alignItems: "center", gap: ".75rem", position: "sticky", bottom: 0, background: "var(--surface-1)", padding: ".75rem 0", borderTop: "1px solid var(--border-subtle)" }}>
        {onCancel && <button className="btn btn-ghost" disabled={busy} onClick={onCancel}><Bi id="Batal" en="Cancel" /></button>}
        <button className="btn btn-default" disabled={busy || !valid} onClick={() => onSave(patch)}>
          {busy ? <Bi id="Menyimpan…" en="Saving…" /> : <Bi id="Simpan DNA" en="Save DNA" />}
        </button>
        {!valid && <span style={{ fontSize: "var(--text-xs)", color: "var(--danger)" }}><Bi id={`Perbaiki ${Object.keys(errors).length} isian bertanda merah dulu.`} en={`Fix the ${Object.keys(errors).length} flagged fields first.`} /></span>}
      </div>
    </div>
  );
}
