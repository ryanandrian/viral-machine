"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { fetchPricing, idrK } from "@/lib/pricing";
import { PageHeader } from "@/components/page-header";
import { YT_CATEGORIES } from "@/lib/youtube-categories";
import { Target, Search, X, Wand2, Clock, ChevronRight, Tv, Check, Loader2, CreditCard } from "lucide-react";
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
};

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
  const [usage, setUsage] = useState<Record<string, string[]>>({});   // niche_id → [nama channel yang memakai]
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<"all" | "base" | "public" | "private">("all");
  const [cat, setCat] = useState("all");
  const [sel, setSel] = useState<string | null>(null);

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
    // Entitlement katalog publik per-tier: CONFIG-DRIVEN dari plan_limits.full_niche_catalog (0124) — no-hardcode.
    const { data: pl } = await supabase.from("plan_limits").select("full_niche_catalog").eq("plan_type", tier).maybeSingle();
    const fullCatalog = Boolean((pl as { full_niche_catalog?: boolean } | null)?.full_niche_catalog);
    const selCols = "niche_id,name,is_active,is_base,access_type,exclusive_to,keywords,default_hashtags,youtube_category_id,style,target_emotion,narration_persona,visual_style,mood_priority,section_timing";
    // Ambil niche aktif (publik) + niche MILIK tenant walau belum aktif (transparansi: "sedang disiapkan").
    const qN = supabase.from("niches").select(selCols);
    const { data: nrows } = await (uid ? qN.or(`is_active.eq.true,exclusive_to.eq.${uid}`) : qN.eq("is_active", true));
    // Entitlement: niche khusus MILIK tenant (aktif/belum) + niche publik AKTIF (katalog penuh ATAU base). Identik Channel Detail utk yang publik.
    const entitled = ((nrows ?? []) as NicheRow[]).filter((n) =>
      n.exclusive_to === uid || (n.is_active && n.access_type === "public" && (fullCatalog || n.is_base)));
    entitled.sort((a, b) => a.name.localeCompare(b.name));
    setNiches(entitled);
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
    const { data: ec } = await supabase.from("app_config").select("value").eq("key", "niche_eval_window_days").maybeSingle();
    if (ec && (ec as { value?: number }).value != null) setEvalDays(Number((ec as { value: number }).value));
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

  const view = useMemo(() => niches.filter((n) => {
    if (kind !== "all" && nicheKind(n, me).key !== kind) return false;
    if (cat !== "all" && n.youtube_category_id !== cat) return false;
    if (q.trim()) {
      const hay = `${n.name} ${n.niche_id} ${arr(n.keywords).join(" ")}`.toLowerCase();
      if (!hay.includes(q.trim().toLowerCase())) return false;
    }
    return true;
  }), [niches, kind, cat, q, me]);

  const cur = sel ? niches.find((n) => n.niche_id === sel) ?? null : null;

  return (
    <>
      <PageHeader icon={Target} title={<Bi id="Pustaka Niche" en="Niche Library" />}
        subtitle={<Bi id="Semua niche yang bisa kamu pakai. Pasang niche ke channel di halaman Channel." en="All niches you can use. Assign a niche to a channel on the Channels page." />}
        action={<button className="btn btn-default btn-sm" onClick={() => openReq("public_90d")}><Wand2 size={14} /> <Bi id="Pesan niche custom" en="Request custom niche" /></button>} />

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
          <th><Bi id="Niche" en="Niche" /></th>
          <th><Bi id="Kategori YouTube" en="YouTube category" /></th>
          <th><Bi id="Tipe" en="Type" /></th>
          <th><Bi id="Status" en="Status" /></th>
        </tr></thead>
        <tbody>
          {loading && <tr><td colSpan={4} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
          {!loading && view.length === 0 && <tr><td colSpan={4} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}><Bi id="Tidak ada niche yang cocok." en="No matching niche." /></td></tr>}
          {view.map((n) => {
            const k = nicheKind(n, me); const used = usage[n.niche_id] || [];
            return (
              <tr key={n.niche_id} onClick={() => setSel(n.niche_id)} style={{ cursor: "pointer" }}>
                <td><span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{n.name}</span></td>
                <td className="muted">{catLabel(n.youtube_category_id)}</td>
                <td><span className={`badge ${k.cls}`}>{k.label}</span></td>
                <td>{!n.is_active
                  ? <span className="badge badge-warning"><span className="dot" /><Bi id="Belum aktif" en="Not active" /></span>
                  : used.length > 0
                    ? <span className="badge badge-success"><span className="dot" />{`Dipakai (${used.length})`}</span>
                    : <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum dipakai" en="Not used" /></span>}</td>
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
          const desc = [cur.style, cur.target_emotion].filter(Boolean).join(" · ");
          const persona = joinVals(cur.narration_persona, ["tone", "style", "mood", "hook_style"]);
          const visual = joinVals(cur.visual_style, ["mood", "atmosphere", "lighting", "color_palette", "color_grading", "camera"]);
          const music = arr(cur.mood_priority).join(", ");
          const timing = timingText(cur.section_timing);
          const topics = arr(cur.keywords).slice(0, 8);
          const tags = arr(cur.default_hashtags);
          const Row = ({ k: kk, children }: { k: string; children: React.ReactNode }) =>
            <div className="nlib-def"><div className="k">{kk}</div><div className="v">{children}</div></div>;
          return (<>
            <div className="nlib-drawer-head">
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: "var(--text-base)" }}>{cur.name}</div>
                <div style={{ display: "flex", gap: ".375rem", marginTop: ".3rem" }}>
                  <span className={`badge ${k.cls}`}>{k.label}</span>
                  <span className="badge badge-outline">{catLabel(cur.youtube_category_id)}</span>
                </div>
              </div>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button>
            </div>
            <div className="nlib-dpanel">
              {!cur.is_active && <div style={{ background: "var(--warning-soft)", border: "1px solid color-mix(in srgb,var(--warning) 30%,transparent)", borderRadius: "var(--r-md)", padding: "0.625rem 0.75rem", marginBottom: "1rem", fontSize: "var(--text-xs)", color: "var(--warning)" }}><Bi id="Niche ini milikmu tapi BELUM AKTIF — sedang disiapkan, belum bisa dipakai di channel." en="This niche is yours but NOT ACTIVE yet — being prepared, not usable in a channel." /></div>}
              {desc && <Row k="Deskripsi">{desc}</Row>}
              {topics.length > 0 && <Row k="Contoh topik / tema">
                <div style={{ display: "flex", gap: ".375rem", flexWrap: "wrap" }}>{topics.map((t) => <span key={t} className="chip">{t}</span>)}</div>
              </Row>}
              {tags.length > 0 && <Row k="Hashtag default">{tags.map((t) => (t.startsWith("#") ? t : `#${t}`)).join(" ")}</Row>}
              {persona && <Row k="Gaya bahasa">{persona}</Row>}
              {music && <Row k="Musik">{music}</Row>}
              {visual && <Row k="Tampilan visual">{visual}</Row>}
              {timing && <Row k="Alur video">{timing}</Row>}
              <Row k="Kata kunci (SEO)">{arr(cur.keywords).length ? arr(cur.keywords).join(", ") : "—"}</Row>
              <Row k="Sedang dipakai di">{used.length ? used.join(", ") : <span className="muted"><Bi id="belum dipakai di channel mana pun" en="not used in any channel" /></span>}</Row>
            </div>
            <div className="nlib-drawer-foot">
              {cur.is_active
                ? <Link href="/channels" className="btn btn-default btn-sm"><Tv size={14} /> <Bi id="Pakai di channel" en="Use in a channel" /> <ChevronRight size={14} /></Link>
                : <span className="muted" style={{ fontSize: "var(--text-xs)" }}><Bi id="Belum bisa dipakai (niche belum aktif)." en="Not usable yet (niche not active)." /></span>}
            </div>
          </>);
        })()}
      </aside>

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
