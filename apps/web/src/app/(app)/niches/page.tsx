"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { fetchPricing, idrK } from "@/lib/pricing";
import { PageHeader } from "@/components/page-header";
import { YT_CATEGORIES } from "@/lib/youtube-categories";
import { Target, Search, X, Wand2, Clock, ChevronRight, Tv, Check, Loader2, CreditCard, Lock, ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import "./niches.css";

// Pustaka Niche (tenant) — daftar SEMUA niche yang jadi hak tenant (dasar/umum/khusus miliknya),
// dengan cari + filter + tabel + drawer detail (baca-saja) agar tenant well-informed sebelum memakai
// niche di channel. Pemasangan niche ke channel tetap di Channel Detail (tak diduplikasi di sini).
// Data 100% NYATA dari `niches` (entitlement = query identik Channel Detail) + `channels` (status dipakai)
// + `pricing_config` (harga custom) + insert `niche_requests` (pesan custom). Kelas global (components.css).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type NicheRow = {
  niche_id: string; name: string; is_active: boolean; is_base: boolean; access_type: string; exclusive_to: string | null;
  keywords: unknown; default_hashtags: unknown; youtube_category_id: string | null;
  style: string | null; target_emotion: string | null;
  narration_persona: unknown; visual_style: unknown; mood_priority: unknown; section_timing: unknown;
  created_at: string | null; description: string | null; description_en: string | null;
  visual_fallbacks: unknown;
};

// ── Config UI Pustaka Niche — SUMBER: app_config (migr 0134, admin-editable, no-hardcode).
// Nilai di bawah = FALLBACK fail-soft bila app_config tak terbaca (pola sama niche_eval_window_days).
type ToneCfg = { dark: string[]; bright: string[] };
const FALLBACK_TONE: ToneCfg = { dark: ["dark", "eerie", "ominous", "suspense", "tense", "mysterious"],
                                 bright: ["upbeat", "happy", "energetic", "inspirational", "calm", "playful"] };
const FALLBACK_NEW_DAYS = 14;
function toneOf(mood: unknown, cfg: ToneCfg): { key: "dark" | "bright" | "neutral"; id: string; en: string; color: string } {
  const top = (Array.isArray(mood) ? (mood as string[]) : []).slice(0, 3);
  const d = top.filter((m) => cfg.dark.includes(m)).length, b = top.filter((m) => cfg.bright.includes(m)).length;
  if (d > b) return { key: "dark", id: "Gelap", en: "Dark", color: "var(--accent)" };
  if (b > d) return { key: "bright", id: "Cerah", en: "Bright", color: "var(--warning)" };
  return { key: "neutral", id: "Netral", en: "Neutral", color: "var(--text-muted)" };
}
function expandQuery(q: string, syn: Record<string, string>): string {
  const base = q.toLowerCase().trim();
  let extra = "";
  for (const [id, en] of Object.entries(syn)) if (base.includes(id)) extra += " " + en;
  return (base + extra).trim();
}

const CAT_LABEL: Record<string, string> = Object.fromEntries(YT_CATEGORIES as [string, string][]);
const catLabel = (id: string | null) => (id && CAT_LABEL[id]) || (id ? `Kategori ${id}` : "—");
const arr = (v: unknown): string[] => Array.isArray(v) ? (v as unknown[]).map(String) : [];
function joinVals(v: unknown, keys?: string[]): string {
  if (!v) return "";
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return v.map(String).join(", ");
  if (typeof v === "object") {
    const o = v as Record<string, unknown>;
    const picked = (keys ? keys.map((k) => o[k]) : Object.values(o)).filter((x) => typeof x === "string" || typeof x === "number");
    return picked.map(String).join(" · ");
  }
  return "";
}
function timingText(v: unknown): string {
  if (!v || typeof v !== "object" || Array.isArray(v)) return "";
  return Object.entries(v as Record<string, unknown>)
    .filter(([, s]) => typeof s === "number")
    .map(([k, s]) => `${k.replace(/_/g, " ")} ${s}d`)
    .join(" → ");
}

// Tipe niche untuk tenant (dasar/umum/khusus milik sendiri)
function nicheKind(n: NicheRow, me: string): { key: "base" | "public" | "private"; label: string; cls: string } {
  if (n.exclusive_to && n.exclusive_to === me) return { key: "private", label: "Khusus", cls: "badge-brand" };
  if (n.is_base) return { key: "base", label: "Dasar", cls: "badge-default" };
  return { key: "public", label: "Umum", cls: "badge-info" };
}

// ── Riwayat pengajuan custom niche ──
type NReq = {
  request_id: string; request_type: string; title: string; status: string;
  created_at: string; delivered_at: string | null; delivery_note: string | null;
  revision_note: string | null; niche_id: string | null;
};
const REQ_STATUS: Record<string, { label: string; cls: string }> = {
  pending: { label: "Diajukan", cls: "badge-info" },
  awaiting_payment: { label: "Menunggu pembayaran", cls: "badge-warning" },
  in_progress: { label: "Diproses", cls: "badge-info" },
  delivered: { label: "Evaluasi", cls: "badge-brand" },
  closed: { label: "Selesai", cls: "badge-success" },
  rejected: { label: "Ditolak", cls: "badge-error" },
  cancelled: { label: "Dibatalkan", cls: "badge-default" },
};
const reqStatus = (s: string) => REQ_STATUS[s] ?? { label: s, cls: "badge-default" };
function daysLeft(deliveredAt: string | null, windowDays: number): number | null {
  if (!deliveredAt) return null;
  const end = new Date(deliveredAt).getTime() + windowDays * 864e5;
  return Math.max(0, Math.ceil((end - Date.now()) / 864e5));
}

export default function NichesPage() {
  const supabase = createClient();
  const [me, setMe] = useState("");
  const [niches, setNiches] = useState<NicheRow[]>([]);
  const [fullCatalog, setFullCatalog] = useState(true);   // hak pakai niche publik non-dasar (plan_limits.full_niche_catalog)
  const [canReq, setCanReq] = useState(true);             // hak pesan niche custom (plan_limits.can_request_custom_niche, 0130)
  const [upModal, setUpModal] = useState(false);          // ajakan upgrade saat fitur pesan terkunci
  const [usage, setUsage] = useState<Record<string, string[]>>({});   // niche_id → [nama channel yang memakai]
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<"all" | "base" | "public" | "private">("all");
  const [cat, setCat] = useState("all");
  const [sel, setSel] = useState<string | null>(null);
  // Sorting kolom (world-class table): klik header = asc → desc → reset. Default = Baru dulu, lalu nama.
  const [sort, setSort] = useState<{ key: "name" | "cat" | "tone" | "status"; dir: 1 | -1 } | null>(null);
  const cycleSort = (key: "name" | "cat" | "tone" | "status") =>
    setSort((s) => (!s || s.key !== key) ? { key, dir: 1 } : s.dir === 1 ? { key, dir: -1 } : null);
  // Config UI dari app_config (0134) — fail-soft ke fallback kode.
  const [toneCfg, setToneCfg] = useState<ToneCfg>(FALLBACK_TONE);
  const [syn, setSyn] = useState<Record<string, string>>({});
  const [newDays, setNewDays] = useState(FALLBACK_NEW_DAYS);
  const isNewNiche = useCallback((iso: string | null) =>
    !!iso && (Date.now() - new Date(iso).getTime()) < newDays * 864e5, [newDays]);

  // ── Riwayat pengajuan + masa evaluasi ──
  const [requests, setRequests] = useState<NReq[]>([]);
  const [evalDays, setEvalDays] = useState(3);
  const [reqBusy, setReqBusy] = useState<string | null>(null);
  const [reqMsg, setReqMsg] = useState<string | null>(null);
  const [reviseFor, setReviseFor] = useState<NReq | null>(null);
  const [revNote, setRevNote] = useState("");

  // ── Pesan niche custom (NYATA: insert niche_requests; harga live pricing_config) ──
  const [pricing, setPricing] = useState<Record<string, number>>({});
  const [modal, setModal] = useState(false);
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
    load();   // segarkan riwayat → pengajuan baru langsung tampil (tenant tahu sudah ter-submit)
    setTimeout(() => { setModal(false); setRMsg(null); }, 1400);
  }

  const load = useCallback(async () => {
    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    const uid = user?.id ?? ""; setMe(uid);
    const { data: cfg } = await supabase.from("tenant_configs").select("plan_type").maybeSingle();
    const tier = (cfg as { plan_type?: string } | null)?.plan_type ?? "starter";
    // Entitlement per-tier: CONFIG-DRIVEN dari plan_limits (0124 katalog + 0130 pesan custom) — no-hardcode.
    const { data: pl } = await supabase.from("plan_limits").select("full_niche_catalog,can_request_custom_niche").eq("plan_type", tier).maybeSingle();
    const plr = pl as { full_niche_catalog?: boolean; can_request_custom_niche?: boolean } | null;
    setFullCatalog(Boolean(plr?.full_niche_catalog));
    setCanReq(Boolean(plr?.can_request_custom_niche));
    const selCols = "niche_id,name,is_active,is_base,access_type,exclusive_to,keywords,default_hashtags,youtube_category_id,style,target_emotion,narration_persona,visual_style,mood_priority,section_timing,created_at,description,description_en,visual_fallbacks";
    // Ambil niche aktif (publik) + niche MILIK tenant walau belum aktif (transparansi: "sedang disiapkan").
    const qN = supabase.from("niches").select(selCols);
    const { data: nrows } = await (uid ? qN.or(`is_active.eq.true,exclusive_to.eq.${uid}`) : qN.eq("is_active", true));
    // ETALASE TERBUKA (keputusan owner 2026-07-05): SEMUA niche publik aktif TAMPIL utk semua tier
    // (yang di luar hak diberi tanda 🔒 Upgrade — gerbang pakai tetap di server: RPC set_channel_niche).
    // Niche khusus milik tenant lain TIDAK ikut tampil.
    const visible = ((nrows ?? []) as NicheRow[]).filter((n) =>
      n.exclusive_to === uid || (!n.exclusive_to && n.is_active && n.access_type === "public"));
    visible.sort((a, b) => a.name.localeCompare(b.name));
    setNiches(visible);
    // Status "dipakai": kumpulkan dari channels (niche fixed + niche_pool).
    const { data: chs } = await supabase.from("channels").select("channel_name,niche,niche_pool");
    const map: Record<string, string[]> = {};
    ((chs ?? []) as { channel_name: string | null; niche: string | null; niche_pool: string[] | null }[]).forEach((c) => {
      const used = new Set<string>([...(c.niche ? [c.niche] : []), ...((c.niche_pool ?? []) as string[])]);
      used.forEach((nid) => { (map[nid] ??= []).push(c.channel_name || "channel"); });
    });
    setUsage(map);
    // Riwayat pengajuan custom niche (RLS: milik sendiri) + lebar masa evaluasi (app_config, public-read).
    const { data: rq } = await supabase.from("niche_requests")
      .select("request_id,request_type,title,status,created_at,delivered_at,delivery_note,revision_note,niche_id")
      .order("created_at", { ascending: false });
    setRequests((rq ?? []) as NReq[]);
    // Config UI (satu query): masa evaluasi + badge Baru + nuansa mood + sinonim pencarian (0134).
    const { data: cfgs } = await supabase.from("app_config").select("key,value,value_text")
      .in("key", ["niche_eval_window_days", "niche_new_badge_days", "niche_tone_moods", "niche_search_synonyms"]);
    for (const c of (cfgs ?? []) as { key: string; value: number | null; value_text: string | null }[]) {
      try {
        if (c.key === "niche_eval_window_days" && c.value != null) setEvalDays(Number(c.value));
        if (c.key === "niche_new_badge_days" && c.value != null) setNewDays(Number(c.value));
        if (c.key === "niche_tone_moods" && c.value_text) setToneCfg(JSON.parse(c.value_text));
        if (c.key === "niche_search_synonyms" && c.value_text) setSyn(JSON.parse(c.value_text));
      } catch { /* fail-soft: fallback kode tetap berlaku */ }
    }
    setLoading(false);
  }, [supabase]);

  // Aksi tenant pada pesanan (gerbang RPC server).
  async function cancelReq(id: string) {
    setReqBusy(id); setReqMsg(null);
    const { error } = await supabase.rpc("cancel_niche_request", { p_request_id: id });
    setReqBusy(null);
    if (error) { setReqMsg(error.message); return; }
    load();
  }
  async function actReq(id: string, act: "accept" | "revision", note?: string) {
    setReqBusy(id); setReqMsg(null);
    const { error } = await supabase.rpc("tenant_niche_request_action", { p_request_id: id, p_action: act, p_note: note ?? null });
    setReqBusy(null);
    if (error) { setReqMsg(error.message); return; }
    setReviseFor(null); setRevNote(""); load();
  }
  // Bayar add-on via Midtrans (status awaiting_payment) → redirect ke halaman bayar. Aktivasi via webhook.
  async function payReq(id: string) {
    setReqBusy(id); setReqMsg(null);
    try {
      const res = await fetch(`/api/niche-requests/${id}/pay`, { method: "POST" });
      const j = await res.json().catch(() => ({}));
      if (res.ok && j.redirect_url) { window.location.href = j.redirect_url; return; }
      setReqMsg(j.error || "Gagal memulai pembayaran."); setReqBusy(null);
    } catch { setReqMsg("Gagal terhubung. Coba lagi."); setReqBusy(null); }
  }

  useEffect(() => { load(); fetchPricing().then(setPricing); }, [load]);
  useEffect(() => { const k = (e: KeyboardEvent) => { if (e.key === "Escape") setSel(null); }; document.addEventListener("keydown", k); return () => document.removeEventListener("keydown", k); }, []);

  // Kategori YouTube yang benar-benar muncul di niche tenant (untuk dropdown filter).
  const catsPresent = useMemo(() => {
    const s = new Set(niches.map((n) => n.youtube_category_id).filter(Boolean) as string[]);
    return [...s].sort((a, b) => catLabel(a).localeCompare(catLabel(b)));
  }, [niches]);

  // Hak PAKAI per niche (cermin gerbang server RPC set_channel_niche): milik sendiri ATAU publik (katalog penuh / dasar).
  // (Dideklarasikan SEBELUM `view` — dipakai bobot status sorting.)
  const isEntitled = useCallback((n: NicheRow) =>
    n.exclusive_to === me || (n.access_type === "public" && (fullCatalog || n.is_base)), [me, fullCatalog]);

  const view = useMemo(() => {
    const qx = expandQuery(q, syn);
    const tokens = qx ? qx.split(/\s+/) : [];
    const out = niches.filter((n) => {
      if (kind !== "all" && nicheKind(n, me).key !== kind) return false;
      if (cat !== "all" && n.youtube_category_id !== cat) return false;
      if (tokens.length) {
        // Cakupan diperluas: nama + id + keywords + style + emosi + deskripsi ID/EN (lintas bahasa natural).
        const hay = `${n.name} ${n.niche_id} ${arr(n.keywords).join(" ")} ${n.style ?? ""} ${n.target_emotion ?? ""} ${n.description ?? ""} ${n.description_en ?? ""}`.toLowerCase();
        if (!tokens.some((t) => hay.includes(t))) return false;
      }
      return true;
    });
    // Bobot status utk sorting: dipakai > siap dipakai > perlu upgrade > belum aktif.
    const statusW = (n: NicheRow) => !n.is_active ? 0 : !isEntitled(n) ? 1 : (usage[n.niche_id]?.length ? 3 : 2);
    if (sort) {
      const dir = sort.dir;
      out.sort((a, b) => {
        if (sort.key === "name") return dir * a.name.localeCompare(b.name);
        if (sort.key === "cat") return dir * catLabel(a.youtube_category_id).localeCompare(catLabel(b.youtube_category_id));
        if (sort.key === "tone") return dir * toneOf(a.mood_priority, toneCfg).id.localeCompare(toneOf(b.mood_priority, toneCfg).id);
        return dir * (statusW(b) - statusW(a));
      });
    } else {
      // Default: yang BARU dulu (etalase menonjolkan kedatangan), lalu abjad.
      out.sort((a, b) => (Number(isNewNiche(b.created_at)) - Number(isNewNiche(a.created_at))) || a.name.localeCompare(b.name));
    }
    return out;
  }, [niches, kind, cat, q, me, sort, usage, isEntitled, syn, toneCfg, isNewNiche]);

  const cur = sel ? niches.find((n) => n.niche_id === sel) ?? null : null;

  return (
    <>
      <PageHeader icon={Target} title={<Bi id="Pustaka Niche" en="Niche Library" />}
        subtitle={<Bi id="Semua niche yang bisa kamu pakai. Pasang niche ke channel di halaman Channel." en="All niches you can use. Assign a niche to a channel on the Channels page." />}
        action={<button className="btn btn-default btn-sm" onClick={() => (canReq ? openReq("public_90d") : setUpModal(true))}>{canReq ? <Wand2 size={14} /> : <Lock size={14} />} <Bi id="Pesan niche custom" en="Request custom niche" /></button>} />

      {/* Toolbar: cari + filter tipe + filter kategori */}
      <div className="nlib-toolbar">
        <div className="nlib-search">
          <Search size={15} />
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari niche atau kata kunci…" />
        </div>
        <div className="segmented">
          {([["all", "Semua"], ["base", "Dasar"], ["public", "Umum"], ["private", "Khusus"]] as [typeof kind, string][]).map(([k, l]) =>
            <button key={k} aria-selected={kind === k} onClick={() => setKind(k)}>{l}</button>)}
        </div>
        {catsPresent.length > 0 && (
          <select className="input nlib-cat" value={cat} onChange={(e) => setCat(e.target.value)}>
            <option value="all">Semua kategori YouTube</option>
            {catsPresent.map((c) => <option key={c} value={c}>{catLabel(c)}</option>)}
          </select>
        )}
      </div>

      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl nlib-tbl">
        <thead><tr>
          {([["name", <Bi key="h" id="Niche" en="Niche" />], ["cat", <Bi key="h" id="Kategori YouTube" en="YouTube category" />],
             ["tone", <Bi key="h" id="Nuansa" en="Tone" />], ["status", <Bi key="h" id="Status" en="Status" />]] as ["name" | "cat" | "tone" | "status", React.ReactNode][]).map(([k, label]) => (
            <th key={k} onClick={() => cycleSort(k)} aria-sort={sort?.key === k ? (sort.dir === 1 ? "ascending" : "descending") : "none"}
                style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }}
                title="Klik untuk mengurutkan">
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>{label}
                {sort?.key === k ? (sort.dir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} style={{ opacity: .35 }} />}
              </span>
            </th>))}
          <th><Bi id="Tipe" en="Type" /></th>
        </tr></thead>
        <tbody>
          {loading && <tr><td colSpan={5} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
          {!loading && view.length === 0 && <tr><td colSpan={5} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}><Bi id="Tidak ada niche yang cocok." en="No matching niche." /></td></tr>}
          {view.map((n) => {
            const k = nicheKind(n, me); const used = usage[n.niche_id] || [];
            const tone = toneOf(n.mood_priority, toneCfg);
            // Teaser = deskripsi manusiawi (0135); fallback DNA teknis bila deskripsi kosong (niche custom lama).
            const teaser = n.description || [n.style, n.target_emotion].filter(Boolean).join(" · ");
            return (
              <tr key={n.niche_id} onClick={() => setSel(n.niche_id)} style={{ cursor: "pointer" }}>
                <td>
                  <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{n.name}</span>
                  {isNewNiche(n.created_at) && <span className="badge badge-brand" style={{ marginLeft: 6, fontSize: ".625rem", verticalAlign: "1px" }}><Bi id="Baru" en="New" /></span>}
                  {teaser && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 2, maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {n.description ? <Bi id={n.description} en={n.description_en || n.description} /> : teaser}</div>}
                </td>
                <td className="muted">{catLabel(n.youtube_category_id)}</td>
                <td><span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
                  <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: tone.color, display: "inline-block" }} />
                  <Bi id={tone.id} en={tone.en} /></span></td>
                <td>{!n.is_active
                  ? <span className="badge badge-warning"><span className="dot" /><Bi id="Belum aktif" en="Not active" /></span>
                  : !isEntitled(n)
                    ? <span className="badge badge-brand"><Lock size={11} /> <Bi id="Perlu upgrade" en="Upgrade needed" /></span>
                    : used.length > 0
                      ? <span className="badge badge-success"><span className="dot" />{`Dipakai (${used.length})`}</span>
                      : <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum dipakai" en="Not used" /></span>}</td>
                <td><span className={`badge ${k.cls}`}>{k.label}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table></div></div>
      {!loading && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".625rem" }}>{view.length} niche</div>}

      {/* Riwayat pengajuan custom niche + aksi (batal saat pending · evaluasi saat delivered) */}
      {requests.length > 0 && (
        <div className="card" style={{ marginTop: "1.75rem" }}>
          <div className="card-head"><h3 className="card-title"><Wand2 size={15} /> <Bi id="Riwayat pengajuan niche custom" en="Custom niche requests" /></h3></div>
          <div style={{ overflowX: "auto" }}><table className="tbl">
            <thead><tr><th><Bi id="Jenis" en="Type" /></th><th><Bi id="Judul" en="Title" /></th><th><Bi id="Diajukan" en="Submitted" /></th><th>Status</th><th></th></tr></thead>
            <tbody>{requests.map((rq) => {
              const st = reqStatus(rq.status);
              const dl = rq.status === "delivered" ? daysLeft(rq.delivered_at, evalDays) : null;
              return (
                <tr key={rq.request_id}>
                  <td><span className="badge badge-default">{rq.request_type === "private" ? "🔒 Privat" : "🌍 Publik 90h"}</span></td>
                  <td style={{ color: "var(--text-primary)" }}>{rq.title}{rq.revision_note && rq.status === "in_progress" ? <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Revisi diminta" en="Revision requested" /></div> : null}</td>
                  <td className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{new Date(rq.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}</td>
                  <td><span className={`badge ${st.cls}`}>{st.label}</span>{rq.status === "delivered" && dl != null && <div style={{ fontSize: "var(--text-xs)", marginTop: 3, color: dl <= 1 ? "var(--warning)" : "var(--text-muted)" }}>{dl > 0 ? `Sisa evaluasi: ${dl} hari` : "Evaluasi berakhir hari ini"}</div>}</td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    {rq.status === "pending" && <button className="btn btn-ghost btn-sm" disabled={reqBusy === rq.request_id} onClick={() => cancelReq(rq.request_id)}>{reqBusy === rq.request_id ? <Loader2 size={13} className="spin" /> : <Bi id="Batalkan" en="Cancel" />}</button>}
                    {rq.status === "awaiting_payment" && <button className="btn btn-default btn-sm" disabled={reqBusy === rq.request_id} onClick={() => payReq(rq.request_id)}>{reqBusy === rq.request_id ? <Loader2 size={13} className="spin" /> : <><CreditCard size={13} /> <Bi id="Bayar" en="Pay" /></>}</button>}
                    {rq.status === "delivered" && <>
                      <button className="btn btn-default btn-sm" disabled={reqBusy === rq.request_id} onClick={() => actReq(rq.request_id, "accept")} style={{ marginRight: ".375rem" }}><Check size={13} /> <Bi id="Terima & Selesaikan" en="Accept & close" /></button>
                      <button className="btn btn-ghost btn-sm" disabled={reqBusy === rq.request_id} onClick={() => { setReviseFor(rq); setRevNote(""); }}><Bi id="Minta perbaikan" en="Request revision" /></button>
                    </>}
                  </td>
                </tr>
              );
            })}</tbody>
          </table></div>
          {reqMsg && <div style={{ color: "var(--danger,#ef4444)", fontSize: "var(--text-xs)", padding: "0 1rem .75rem" }}>{reqMsg}</div>}
          {requests.some((r) => r.status === "delivered") && <div className="muted" style={{ fontSize: "var(--text-xs)", padding: "0 1rem 1rem" }}><Bi id="Niche yang sudah jadi: cek detailnya di tabel atas, lalu tekan Terima & Selesaikan bila puas. Lewat masa evaluasi tanpa respons = otomatis dianggap selesai." en="Delivered niches: review them in the table above, then Accept & close if satisfied. No response past the window = auto-closed." /></div>}
        </div>
      )}

      {/* Modal minta perbaikan */}
      {reviseFor && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setReviseFor(null); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card" style={{ maxWidth: 480, width: "100%" }}>
            <div className="card-head"><h3 className="card-title"><Bi id="Minta perbaikan" en="Request revision" /> · {reviseFor.title}</h3><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setReviseFor(null)}><X size={16} /></button></div>
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: ".75rem" }}>
              <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Jelaskan apa yang perlu diperbaiki — tim akan menyesuaikan niche, lalu menyerahkannya kembali untuk Anda evaluasi." en="Describe what needs fixing — the team will adjust the niche and re-deliver it for your evaluation." /></div>
              <textarea className="textarea" rows={3} value={revNote} onChange={(e) => setRevNote(e.target.value)} placeholder="mis. gaya visual terlalu gelap, tolong lebih cerah & dinamis" />
            </div>
            <div className="card-foot" style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end" }}>
              <button className="btn btn-ghost" onClick={() => setReviseFor(null)}><Bi id="Batal" en="Cancel" /></button>
              <button className="btn btn-default" disabled={!revNote.trim() || reqBusy === reviseFor.request_id} onClick={() => actReq(reviseFor.request_id, "revision", revNote.trim())}><Bi id="Kirim permintaan" en="Send request" /></button>
            </div>
          </div>
        </div>
      )}

      {/* Drawer detail (baca-saja) */}
      <div className={`nlib-scrim${cur ? " open" : ""}`} onClick={() => setSel(null)} />
      <aside className={`nlib-drawer${cur ? " open" : ""}`}>
        {cur && (() => {
          const k = nicheKind(cur, me); const used = usage[cur.niche_id] || [];
          const tone = toneOf(cur.mood_priority, toneCfg);
          const pers = (cur.narration_persona && typeof cur.narration_persona === "object") ? cur.narration_persona as Record<string, string> : {};
          const vs0 = (cur.visual_style && typeof cur.visual_style === "object") ? cur.visual_style as Record<string, unknown> : {};
          const vs = { atmosphere: typeof vs0.atmosphere === "string" ? vs0.atmosphere : "",
                       color_palette: typeof vs0.color_palette === "string" ? vs0.color_palette : "" };
          const arc = (pers.emotion_arc || "").split("→").map((s) => s.trim()).filter(Boolean);
          const scenes = arr(cur.visual_fallbacks).slice(0, 3);
          const moods = arr(cur.mood_priority);
          const timing = timingText(cur.section_timing);
          const topics = arr(cur.keywords).slice(0, 8);
          const tags = arr(cur.default_hashtags);
          const Sec = ({ icon, id, en, children }: { icon: React.ReactNode; id: string; en: string; children: React.ReactNode }) =>
            <div className="nlib-sec"><div className="nlib-sec-title">{icon}<Bi id={id} en={en} /></div>{children}</div>;
          return (<>
            <div className="nlib-drawer-head">
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: "var(--text-base)" }}>{cur.name}</div>
                <div style={{ display: "flex", gap: ".375rem", marginTop: ".3rem", alignItems: "center" }}>
                  <span className={`badge ${k.cls}`}>{k.label}</span>
                  <span className="badge badge-outline">{catLabel(cur.youtube_category_id)}</span>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
                    <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: tone.color, display: "inline-block" }} />
                    <Bi id={tone.id} en={tone.en} /></span>
                  {isNewNiche(cur.created_at) && <span className="badge badge-brand" style={{ fontSize: ".625rem" }}><Bi id="Baru" en="New" /></span>}
                </div>
              </div>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button>
            </div>
            <div className="nlib-dpanel">
              {!cur.is_active && <div style={{ background: "var(--warning-soft)", border: "1px solid color-mix(in srgb,var(--warning) 30%,transparent)", borderRadius: "var(--r-md)", padding: "0.625rem 0.75rem", marginBottom: "1rem", fontSize: "var(--text-xs)", color: "var(--text-primary)" }}><Bi id="Niche ini milikmu tapi BELUM AKTIF — sedang disiapkan, belum bisa dipakai di channel." en="This niche is yours but NOT ACTIVE yet — being prepared, not usable in a channel." /></div>}

              {(cur.description || cur.style) && <div className="nlib-hero">
                {cur.description ? <Bi id={cur.description} en={cur.description_en || cur.description} /> : [cur.style, cur.target_emotion].filter(Boolean).join(" · ")}
              </div>}

              {(arc.length > 0 || cur.target_emotion) && <Sec icon={<Wand2 size={13} />} id="Perjalanan emosi penonton" en="Viewer's emotional journey">
                {arc.length > 1
                  ? <div className="nlib-arc">{arc.map((a, i) => (<span key={i} style={{ display: "contents" }}><span className="step">{a}</span>{i < arc.length - 1 && <span className="sep">→</span>}</span>))}</div>
                  : <div className="nlib-kv">{cur.target_emotion}</div>}
              </Sec>}

              {(pers.tone || pers.style) && <Sec icon={<Tv size={13} />} id="Suara narator" en="Narrator's voice">
                {pers.tone && <div className="nlib-kv">{pers.tone}</div>}
                {pers.style && <div className="nlib-kv muted" style={{ fontSize: "var(--text-xs)" }}>{pers.style}</div>}
              </Sec>}

              {(scenes.length > 0 || vs.atmosphere) && <Sec icon={<Search size={13} />} id="Seperti apa videonya terlihat" en="How the videos look">
                {vs.atmosphere !== "" && <div className="nlib-kv" style={{ marginBottom: ".55rem" }}>{vs.atmosphere}</div>}
                {scenes.map((s, i) => <div key={i} className="nlib-scene">“{s}”</div>)}
                {vs.color_palette !== "" && <div className="nlib-kv muted" style={{ fontSize: "var(--text-xs)" }}><b><Bi id="Palet warna" en="Palette" />:</b> {vs.color_palette}</div>}
              </Sec>}

              {moods.length > 0 && <Sec icon={<Clock size={13} />} id="Musik & alur" en="Music & flow">
                <div className="nlib-chiprow" style={{ marginBottom: timing ? ".5rem" : 0 }}>{moods.map((m) => <span key={m} className="chip">{m}</span>)}</div>
                {timing && <div className="nlib-kv muted" style={{ fontSize: "var(--text-xs)" }}>{timing}</div>}
              </Sec>}

              {(topics.length > 0 || tags.length > 0) && <Sec icon={<Target size={13} />} id="Topik & jangkauan" en="Topics & reach">
                {topics.length > 0 && <div className="nlib-chiprow" style={{ marginBottom: tags.length ? ".5rem" : 0 }}>{topics.map((t) => <span key={t} className="chip">{t}</span>)}</div>}
                {tags.length > 0 && <div className="nlib-kv muted" style={{ fontSize: "var(--text-xs)" }}>{tags.map((t) => (t.startsWith("#") ? t : `#${t}`)).join(" ")}</div>}
              </Sec>}

              <Sec icon={<Tv size={13} />} id="Sedang dipakai di" en="Currently used in">
                <div className="nlib-kv">{used.length ? used.join(", ") : <span className="muted"><Bi id="belum dipakai di channel mana pun — jadilah yang pertama" en="not used in any channel yet — be the first" /></span>}</div>
              </Sec>
            </div>
            <div className="nlib-drawer-foot">
              {!isEntitled(cur)
                ? <Link href="/billing" className="btn btn-default btn-sm"><Lock size={14} /> <Bi id="Upgrade paket untuk memakai niche ini" en="Upgrade your plan to use this niche" /> <ChevronRight size={14} /></Link>
                : cur.is_active
                  ? <Link href="/channels" className="btn btn-default btn-sm"><Tv size={14} /> <Bi id="Pakai di channel" en="Use in a channel" /> <ChevronRight size={14} /></Link>
                  : <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum bisa dipakai (niche belum aktif)." en="Not usable yet (niche not active)." /></span>}
            </div>
          </>);
        })()}
      </aside>

      {/* Modal: ajakan upgrade — fitur pesan niche custom untuk paket berbayar (gerbang server: RLS 0130) */}
      {upModal && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setUpModal(false); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card" style={{ maxWidth: 440, width: "100%" }}>
            <div className="card-head"><h3 className="card-title"><Lock size={15} /> <Bi id="Fitur paket berbayar" en="Paid plan feature" /></h3><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setUpModal(false)}><X size={16} /></button></div>
            <div className="card-body">
              <div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Pesan niche custom (dibuat khusus untuk channelmu oleh tim kami) tersedia untuk paket berbayar. Upgrade untuk mulai memesan." en="Custom niche requests (built for your channel by our team) are available on paid plans. Upgrade to start ordering." /></div>
            </div>
            <div className="card-foot" style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end" }}>
              <button className="btn btn-ghost" onClick={() => setUpModal(false)}><Bi id="Nanti dulu" en="Not now" /></button>
              <Link href="/billing" className="btn btn-default"><Bi id="Lihat paket & upgrade" en="See plans & upgrade" /> <ChevronRight size={14} /></Link>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Pesan niche custom — DUAL (public-90d / private), harga live pricing_config */}
      {modal && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setModal(false); }} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "1.5rem" }}>
          <div className="card" style={{ maxWidth: 560, width: "100%", maxHeight: "92vh", overflow: "auto" }}>
            <div className="card-head"><h3 className="card-title"><Wand2 size={16} /> <Bi id="Pesan niche custom" en="Request custom niche" /></h3><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal(false)}><X size={16} /></button></div>
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div className="grid-2">
                <div className={`nlib-pick${reqType === "public_90d" ? " sel" : ""}`} onClick={() => setReqType("public_90d")}>
                  <div style={{ fontWeight: 600 }}>🌍 <Bi id="Publik (90 hari eksklusif)" en="Public (90-day exclusive)" /></div>
                  <div className="price-dyn" style={{ fontSize: "var(--text-lg)", fontWeight: 700 }}>{pricing.custom_niche_public_90d ? `Rp ${idrK(pricing.custom_niche_public_90d)}` : "—"}</div>
                  <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Eksklusif untukmu 90 hari, lalu masuk katalog umum." en="Exclusive to you for 90 days, then enters the public catalog." /></div>
                </div>
                <div className={`nlib-pick${reqType === "private" ? " sel" : ""}`} onClick={() => setReqType("private")}>
                  <div style={{ fontWeight: 600 }}>🔒 <Bi id="Privat permanen" en="Permanent private" /> <span className="badge badge-brand" style={{ fontSize: ".625rem" }}>Premium</span></div>
                  <div className="price-dyn" style={{ fontSize: "var(--text-lg)", fontWeight: 700, color: "var(--accent)" }}>{pricing.custom_niche_private ? `Rp ${idrK(pricing.custom_niche_private)}` : "—"}</div>
                  <div className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Tidak pernah publik. Milikmu selamanya." en="Never public. Permanently yours." /></div>
                </div>
              </div>
              <div><label className="label"><Bi id="Ide niche" en="Niche idea" /> *</label><textarea className="textarea" rows={2} value={rTitle} onChange={(e) => setRTitle(e.target.value)} placeholder="mis. Misteri kapal selam Perang Dunia II" /></div>
              <div><label className="label"><Bi id="Target audiens" en="Target audience" /></label><input className="input" value={rAudience} onChange={(e) => setRAudience(e.target.value)} placeholder="mis. pria 18-34, pecinta sejarah" /></div>
              <div><label className="label"><Bi id="Channel/referensi" en="Reference channels" /></label><input className="input input-mono" value={rRefs} onChange={(e) => setRRefs(e.target.value)} placeholder="youtube.com/@... , contoh gaya" /></div>
              <div><label className="label"><Bi id="Angle viral & use case" en="Viral angle & use case" /></label><textarea className="textarea" rows={2} value={rAngle} onChange={(e) => setRAngle(e.target.value)} placeholder="clue/masukan untuk tim saat membuat niche ini" /></div>
              {rMsg && <div style={{ fontSize: "var(--text-sm)", color: rMsg === "ok" ? "var(--success)" : "var(--danger,#ef4444)" }}>{rMsg === "ok" ? "✓ Request terkirim — tim akan memproses." : rMsg}</div>}
              <div className="muted" style={{ fontSize: "var(--text-xs)", display: "flex", alignItems: "center", gap: ".4rem" }}><Clock size={13} /> <Bi id="SLA: 3–5 hari delivery" en="SLA: 3–5 day delivery" /></div>
            </div>
            <div className="card-foot" style={{ display: "flex", gap: ".5rem", justifyContent: "flex-end" }}><button className="btn btn-ghost" onClick={() => setModal(false)}><Bi id="Batal" en="Cancel" /></button><button className="btn btn-default" disabled={rBusy} onClick={submitReq}><Bi id="Kirim request" en="Submit request" /></button></div>
          </div>
        </div>
      )}
    </>
  );
}
