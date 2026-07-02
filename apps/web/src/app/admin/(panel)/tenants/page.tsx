"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, X, Bell, Pause, Send, CalendarPlus, CalendarClock, RotateCcw, Trash2 } from "lucide-react";
import ConfirmDialog from "@/components/confirm-dialog";
import "./tenants.css";

// E1 Admin Tenants (Phase 10.1) — DATA NYATA via /api/admin/* (service_role, bypass-RLS, gated super-admin).
// Aksi: Suspend/Unsuspend (subscription_status) + Kirim email (antre email_outbox→worker).
// Add-credit & Impersonate DIBUANG (owner: BYOK tanpa kredit; admin tak masuk panel tenant). Prefix adm-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const COLORS = ["#1d4ed8", "#9f1239", "#047857", "#7c3aed", "#b45309", "#0891b2", "#be185d"];

type Row = {
  tenant_id: string; handle: string; email: string; plan: string; status: string; comp: boolean;
  mrr_idr: number; channels: number; joined: string; last_activity: string | null; current_period_end: string | null;
  lead_temp?: string | null; suspended_at?: string | null; blocked_at?: string | null; deletion_scheduled_at?: string | null;
};
type Kpi = { total: number; mrr_idr: number; trials: number; trial_expired: number; suspended: number; blocked?: number };

// LIFECYCLE: suhu lead (nurture) — badge ringkas utk concierge (owner outreach lead panas).
const LEAD_TEMP: Record<string, { emoji: string; id: string; en: string }> = {
  hot:  { emoji: "🔥", id: "Panas", en: "Hot" },
  warm: { emoji: "🌤️", id: "Hangat", en: "Warm" },
  cold: { emoji: "❄️", id: "Dingin", en: "Cold" },
};
type Detail = {
  tenant: Row & { timezone?: string; is_developer?: boolean; discount_pct?: number };
  channels: { id: string; channel_name: string; niche: string; platform: string; is_active: boolean; publish_privacy: string }[];
  runs: { id: number; topic: string; niche: string; status: string; created_at: string; youtube_url: string | null }[];
  payments: { order_id: string; plan_type: string; gross_amount: number; status: string; created_at: string }[];
};

function idr(n: number): string {
  if (!n) return "Rp 0";
  if (n >= 1_000_000) return `Rp ${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}JT`;
  if (n >= 1_000) return `Rp ${Math.round(n / 1_000)}K`;
  return `Rp ${n}`;
}
function dateID(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}
function rel(iso: string | null): string {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "baru saja";
  if (s < 3600) return `${Math.floor(s / 60)} menit lalu`;
  if (s < 86400) return `${Math.floor(s / 3600)} jam lalu`;
  return `${Math.floor(s / 86400)} hari lalu`;
}
function initials(s: string): string {
  const p = (s || "?").replace(/[@.].*$/, "").trim().split(/[\s_-]+/);
  return ((p[0]?.[0] ?? "") + (p[1]?.[0] ?? "")).toUpperCase() || "?";
}

function StBadge({ s }: { s: string }) {
  if (s === "active") return <span className="badge badge-success"><span className="dot" />Active</span>;
  if (s === "trial") return <span className="badge badge-info"><span className="dot" />Trial</span>;
  if (s === "trial_expired") return <span className="badge badge-warning"><span className="dot" />Trial lapse</span>;
  if (s === "grace") return <span className="badge badge-warning"><span className="dot" />Grace</span>;
  if (s === "suspended") return <span className="badge badge-error"><span className="dot" />Suspended</span>;
  return <span className="badge badge-default">{s}</span>;
}

const FILTERS: [string, string, string][] = [
  ["all", "Semua", "All"], ["active", "Active", "Active"], ["trial", "Trial", "Trial"],
  ["trial_expired", "Leads", "Leads"], ["suspended", "Suspended", "Suspended"],
];

export default function AdminTenantsPage() {
  const [filter, setFilter] = useState("all");
  const [rows, setRows] = useState<Row[]>([]);
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [busy, setBusy] = useState(false);
  const [compose, setCompose] = useState<{ subject: string; body: string } | null>(null);
  const [compModal, setCompModal] = useState<{ is_developer: boolean; discount_pct: number } | null>(null);
  // LIFECYCLE (B9): aksi manual — modal isi hari (extend/undur-hapus) + konfirmasi (aktifkan-bersih/hapus).
  const [lifeModal, setLifeModal] = useState<{ action: "extend" | "postpone_deletion"; days: string } | null>(null);
  const [confirm, setConfirm] = useState<null | "reactivate" | "delete">(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    const r = await fetch("/api/admin/tenants");
    if (!r.ok) { setErr(`Gagal memuat (${r.status})`); setLoading(false); return; }
    const j = await r.json();
    setRows(j.rows); setKpi(j.kpi); setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setSel(null); setCompose(null); setCompModal(null); } };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 2800);
    return () => clearTimeout(id);
  }, [toast]);

  useEffect(() => {
    if (!sel) { setDetail(null); return; }
    setDetail(null);
    fetch(`/api/admin/tenants/${sel}`).then((r) => r.ok ? r.json() : null).then(setDetail);
  }, [sel]);

  const view = rows.filter((t) => filter === "all" || t.status === filter);
  const cur = rows.find((t) => t.tenant_id === sel) ?? null;

  async function toggleSuspend() {
    if (!cur) return;
    setBusy(true);
    const action = cur.status === "suspended" ? "unsuspend" : "suspend";
    const r = await fetch(`/api/admin/tenants/${cur.tenant_id}/suspend`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }),
    });
    setBusy(false);
    if (r.ok) { setToast(action === "suspend" ? "Tenant disuspend" : "Suspend dicabut"); await load(); }
    else setToast("Gagal mengubah status");
  }

  async function sendEmail() {
    if (!cur || !compose) return;
    setBusy(true);
    const r = await fetch(`/api/admin/tenants/${cur.tenant_id}/email`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(compose),
    });
    setBusy(false);
    if (r.ok) { setToast("Email diantre (dikirim worker)"); setCompose(null); }
    else setToast("Gagal mengantre email");
  }

  async function saveComp() {
    if (!cur || !compModal) return;
    setBusy(true);
    const r = await fetch(`/api/admin/tenants/${cur.tenant_id}/comp`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(compModal),
    });
    setBusy(false);
    if (r.ok) { setToast("Comp/diskon disimpan"); setCompModal(null); await load(); }
    else setToast("Gagal simpan comp/diskon");
  }

  // LIFECYCLE (B9): perpanjang trial / undur jadwal hapus / aktifkan-bersih (reset penanda). days kosong = default sistem.
  async function doLifecycle(action: "extend" | "postpone_deletion" | "reactivate_clean", days?: string) {
    if (!cur) return;
    setBusy(true);
    const r = await fetch(`/api/admin/tenants/${cur.tenant_id}/lifecycle`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, days: days && days.trim() ? days.trim() : undefined }),
    });
    setBusy(false);
    if (r.ok) {
      setToast(action === "extend" ? "Trial diperpanjang" : action === "postpone_deletion" ? "Jadwal hapus diundur" : "Akun diaktifkan kembali");
      setLifeModal(null); setConfirm(null); await load();
    } else setToast("Gagal memproses");
  }

  // LIFECYCLE (B9): HAPUS PERMANEN (revoke YouTube + purge S3 + purge data). Irreversible → lewat ConfirmDialog.
  async function doHardDelete() {
    if (!cur) return;
    setBusy(true);
    const r = await fetch(`/api/admin/tenants/${cur.tenant_id}/hard-delete`, { method: "POST" });
    setBusy(false);
    if (r.ok) { setToast("Tenant dihapus permanen"); setConfirm(null); setSel(null); await load(); }
    else setToast("Gagal menghapus tenant");
  }

  return (
    <>
      <div className="adm-head">
        <div><h1>Tenants</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}><Bi id="Kelola semua akun pelanggan" en="Manage all customer accounts" /></div></div>
      </div>

      <div className="adm-kpi-strip">
        <div className="adm-kpic"><div className="l"><Bi id="Total tenant" en="Total tenants" /></div><div className="v">{kpi?.total ?? "—"}</div></div>
        <div className="adm-kpic"><div className="l">MRR</div><div className="v">{kpi ? idr(kpi.mrr_idr) : "—"}</div></div>
        <div className="adm-kpic"><div className="l"><Bi id="Trial aktif" en="Active trials" /></div><div className="v">{kpi?.trials ?? "—"}</div></div>
        <div className="adm-kpic"><div className="l"><Bi id="Leads (trial lapse)" en="Leads (trial lapse)" /></div><div className="v">{kpi?.trial_expired ?? "—"}</div></div>
      </div>

      <div className="adm-filters">
        <div className="segmented">{FILTERS.map(([k, id, en]) => <button key={k} aria-selected={filter === k} onClick={() => setFilter(k)}><Bi id={id} en={en} /></button>)}</div>
        <div className="adm-selbox"><Search size={14} /> {view.length} <Bi id="tenant" en="tenants" /></div>
      </div>

      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl adm-tbl">
        <thead><tr><th>Tenant</th><th>Plan</th><th>Status</th><th className="num">MRR</th><th><Bi id="Bergabung" en="Joined" /></th><th><Bi id="Aktivitas" en="Last activity" /></th></tr></thead>
        <tbody>
          {loading && <tr><td colSpan={6} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
          {err && <tr><td colSpan={6} style={{ padding: "1.5rem", textAlign: "center", color: "var(--danger)" }}>{err}</td></tr>}
          {!loading && !err && view.length === 0 && <tr><td colSpan={6} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Tidak ada tenant pada filter ini.</td></tr>}
          {view.map((t, i) => (
            <tr key={t.tenant_id} onClick={() => setSel(t.tenant_id)} style={{ cursor: "pointer" }}>
              <td><span className="adm-tn-cell"><span className="adm-tn-av" style={{ background: COLORS[i % COLORS.length] }}>{initials(t.handle || t.email)}</span><div><div style={{ color: "var(--text-primary)", fontWeight: 500 }}>{t.handle || "—"}{t.comp && <span className="badge badge-default" style={{ marginLeft: 6, fontSize: "var(--text-xs)" }}>Comp</span>}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{t.email || t.tenant_id.slice(0, 8)}</div></div></span></td>
              <td><span className={`badge ${t.plan === "pro" || t.plan === "business" ? "badge-brand" : "badge-default"}`}>{t.plan}</span></td>
              <td><StBadge s={t.status} /></td>
              <td className="num adm-mrr">{t.comp ? "—" : idr(t.mrr_idr)}</td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{dateID(t.joined)}</td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{rel(t.last_activity)}</td>
            </tr>
          ))}
        </tbody>
      </table></div></div>

      <div className={`adm-scrim${cur ? " open" : ""}`} onClick={() => setSel(null)} />
      <aside className={`adm-drawer${cur ? " open" : ""}`}>
        {cur && (<>
          <div className="adm-drawer-head">
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <span className="adm-tn-av" style={{ width: 40, height: 40, fontSize: "var(--text-sm)", background: COLORS[view.findIndex(v => v.tenant_id === cur.tenant_id) % COLORS.length] || COLORS[0] }}>{initials(cur.handle || cur.email)}</span>
              <div style={{ flex: 1 }}><div style={{ fontWeight: 600, fontSize: "var(--text-base)" }}>{cur.handle || "—"}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{detail?.tenant.email || cur.email || "…"}</div></div>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSel(null)}><X size={16} /></button>
            </div>
            <div style={{ marginTop: "0.75rem" }}><StBadge s={cur.status} /> <span className={`badge ${cur.plan === "pro" || cur.plan === "business" ? "badge-brand" : "badge-default"}`} style={{ marginLeft: "0.375rem" }}>{cur.plan}</span>{cur.comp && <span className="badge badge-default" style={{ marginLeft: "0.375rem" }}>Comp · gratis</span>}{cur.lead_temp && LEAD_TEMP[cur.lead_temp] && <span className="badge badge-default" style={{ marginLeft: "0.375rem" }} title="Suhu lead">{LEAD_TEMP[cur.lead_temp].emoji} <Bi id={LEAD_TEMP[cur.lead_temp].id} en={LEAD_TEMP[cur.lead_temp].en} /></span>}</div>
          </div>
          <div className="adm-drawer-body">
            <div>
              <div className="adm-sec-label"><Bi id="Ringkasan" en="Summary" /></div>
              <div className="adm-kv"><span className="k">Plan</span><span className="v">{cur.plan}</span></div>
              <div className="adm-kv"><span className="k">MRR</span><span className="v">{cur.comp ? "— (comp)" : idr(cur.mrr_idr)}</span></div>
              <div className="adm-kv"><span className="k">Channels</span><span className="v">{cur.channels}</span></div>
              <div className="adm-kv"><span className="k"><Bi id="Bergabung" en="Joined" /></span><span className="v">{dateID(cur.joined)}</span></div>
              <div className="adm-kv"><span className="k"><Bi id="Periode s/d" en="Period end" /></span><span className="v">{dateID(cur.current_period_end)}</span></div>
              {cur.suspended_at && <div className="adm-kv"><span className="k">Suspended</span><span className="v">{dateID(cur.suspended_at)}</span></div>}
              {cur.deletion_scheduled_at && <div className="adm-kv"><span className="k"><Bi id="Hapus data" en="Data deletion" /></span><span className="v" style={{ color: "var(--danger)" }}>{dateID(cur.deletion_scheduled_at)}</span></div>}
            </div>
            <div>
              <div className="adm-sec-label"><Bi id="Run terbaru" en="Recent runs" /></div>
              <div className="adm-mini-list">
                {!detail && <div className="row muted">Memuat…</div>}
                {detail && detail.runs.length === 0 && <div className="row muted">Belum ada run.</div>}
                {detail?.runs.map((r) => (
                  <div className="row" key={r.id}>
                    <span className={`badge ${r.status === "completed" ? "badge-success" : r.status === "failed" ? "badge-error" : "badge-default"}`}><span className="dot" />{r.status === "completed" ? "OK" : r.status === "failed" ? "Fail" : r.status}</span>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.topic || r.niche || "—"}</span>
                    <span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-xs)" }}>{rel(r.created_at)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="adm-sec-label"><Bi id="Riwayat billing" en="Billing history" /></div>
              <div className="adm-mini-list">
                {detail && detail.payments.length === 0 && <div className="row muted">{cur.comp ? "Comp — tanpa tagihan." : "Belum ada pembayaran."}</div>}
                {detail?.payments.map((p) => (
                  <div className="row" key={p.order_id}><span>{p.order_id}</span><span className="muted" style={{ marginLeft: "auto" }}>{idr(p.gross_amount)} · <span style={{ color: p.status === "settlement" || p.status === "capture" ? "var(--success)" : "var(--text-muted)" }}>{p.status}</span></span></div>
                ))}
              </div>
            </div>
          </div>
          <div className="adm-drawer-foot">
            <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setCompose({ subject: "", body: "" })}><Bell size={14} /> <Bi id="Kirim email" en="Send email" /></button>
            {/* Suspend hanya utk status hidup (active/trial/grace/trial_expired). Utk suspended/blocked → pakai Aktifkan-bersih (footgun fix). */}
            {(cur.status === "active" || cur.status === "trial" || cur.status === "grace" || cur.status === "trial_expired") && (
              <button className="btn btn-secondary btn-sm" disabled={busy} style={{ color: "var(--warning)" }} onClick={toggleSuspend}><Pause size={14} /> Suspend</button>
            )}
            {/* LIFECYCLE (B9) — aksi manual per-kondisi */}
            {(cur.status === "trial" || cur.status === "trial_expired") && (
              <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setLifeModal({ action: "extend", days: "" })}><CalendarPlus size={14} /> <Bi id="Perpanjang trial" en="Extend trial" /></button>
            )}
            {cur.status === "blocked" && (
              <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setLifeModal({ action: "postpone_deletion", days: "" })}><CalendarClock size={14} /> <Bi id="Undur hapus" en="Postpone deletion" /></button>
            )}
            {(cur.status === "suspended" || cur.status === "blocked") && (
              <button className="btn btn-secondary btn-sm" disabled={busy} style={{ color: "var(--success)" }} onClick={() => setConfirm("reactivate")}><RotateCcw size={14} /> <Bi id="Aktifkan bersih" en="Reactivate" /></button>
            )}
            <button className="btn btn-secondary btn-sm" disabled={busy || !detail} onClick={() => setCompModal({ is_developer: !!detail?.tenant?.is_developer, discount_pct: detail?.tenant?.discount_pct ?? 0 })}>{cur.comp ? "Comp ✓" : "Comp/Diskon"}</button>
            {(cur.status === "suspended" || cur.status === "blocked") && (
              <button className="btn btn-secondary btn-sm" disabled={busy} style={{ color: "var(--danger)" }} onClick={() => setConfirm("delete")}><Trash2 size={14} /> <Bi id="Hapus sekarang" en="Delete now" /></button>
            )}
          </div>
        </>)}
      </aside>

      {compose && cur && (
        <>
          <div className="adm-scrim open" style={{ zIndex: 60 }} onClick={() => setCompose(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(480px,92vw)", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}>
              <strong>Email ke {cur.handle || cur.email}</strong>
              <button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setCompose(null)}><X size={16} /></button>
            </div>
            <div style={{ display: "grid", gap: "0.625rem" }}>
              <input className="input" placeholder="Subjek" value={compose.subject} onChange={(e) => setCompose({ ...compose, subject: e.target.value })} />
              <textarea className="input" placeholder="Isi pesan" rows={6} value={compose.body} onChange={(e) => setCompose({ ...compose, body: e.target.value })} />
              <div className="muted" style={{ fontSize: "var(--text-xs)" }}>Email diantre & dikirim oleh worker (bukan instan).</div>
              <button className="btn btn-primary btn-sm" disabled={busy || !compose.subject.trim() || !compose.body.trim()} style={{ justifySelf: "end" }} onClick={sendEmail}><Send size={14} /> Antre kirim</button>
            </div>
          </div>
        </>
      )}

      {compModal && cur && (
        <>
          <div className="adm-scrim open" style={{ zIndex: 60 }} onClick={() => setCompModal(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(420px,92vw)", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}>
              <strong>Comp / Diskon — {cur.handle || cur.email}</strong>
              <button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setCompModal(null)}><X size={16} /></button>
            </div>
            <div style={{ display: "grid", gap: "0.75rem" }}>
              <label style={{ display: "flex", alignItems: "center", gap: ".5rem", fontSize: "var(--text-sm)" }}>
                <input type="checkbox" checked={compModal.is_developer} onChange={(e) => setCompModal({ ...compModal, is_developer: e.target.checked })} />
                Comp / Developer — gratis selamanya (exempt sweep tagihan)
              </label>
              <div>
                <label className="label">Diskon (%)</label>
                <input className="input" type="number" min={0} max={100} value={compModal.discount_pct} onChange={(e) => setCompModal({ ...compModal, discount_pct: Math.max(0, Math.min(100, parseInt(e.target.value, 10) || 0)) })} />
                <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 3 }}>≥100% = gratis (setara comp). 0 = tanpa diskon.</div>
              </div>
              <button className="btn btn-primary btn-sm" disabled={busy} style={{ justifySelf: "end" }} onClick={saveComp}>Simpan</button>
            </div>
          </div>
        </>
      )}

      {lifeModal && cur && (
        <>
          <div className="adm-scrim open" style={{ zIndex: 60 }} onClick={() => setLifeModal(null)} />
          <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(420px,92vw)", zIndex: 61, padding: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}>
              <strong>{lifeModal.action === "extend" ? "Perpanjang trial" : "Undur jadwal hapus"} — {cur.handle || cur.email}</strong>
              <button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setLifeModal(null)}><X size={16} /></button>
            </div>
            <div style={{ display: "grid", gap: "0.625rem" }}>
              <label className="label"><Bi id="Jumlah hari" en="Number of days" /></label>
              <input className="input" type="number" min={1} placeholder="Kosongkan = pakai default sistem" value={lifeModal.days} onChange={(e) => setLifeModal({ ...lifeModal, days: e.target.value })} />
              <div className="muted" style={{ fontSize: "var(--text-xs)" }}>
                {lifeModal.action === "extend"
                  ? <Bi id="Trial diberikan/diperpanjang sekian hari dari sekarang. Kosongkan untuk memakai default sistem." en="Grants/extends the trial by this many days from now. Leave blank to use the system default." />
                  : <Bi id="Tanggal penghapusan dimundurkan sekian hari. Kosongkan untuk memakai default sistem." en="Pushes the deletion date back by this many days. Leave blank to use the system default." />}
              </div>
              <button className="btn btn-primary btn-sm" disabled={busy} style={{ justifySelf: "end" }} onClick={() => doLifecycle(lifeModal.action, lifeModal.days)}><Bi id="Terapkan" en="Apply" /></button>
            </div>
          </div>
        </>
      )}

      <ConfirmDialog
        open={confirm === "reactivate"}
        title={<Bi id="Aktifkan kembali (bersih)?" en="Reactivate (clean)?" />}
        message={<Bi id="Akun dihidupkan sebagai trial baru; semua penanda suspend/hapus dibersihkan. Untuk melanjutkan, tenant harus berlangganan." en="The account is restored to a fresh trial; all suspend/deletion markers are cleared. To continue, the tenant must subscribe." />}
        confirmLabel={<Bi id="Aktifkan" en="Reactivate" />}
        busy={busy}
        onConfirm={() => doLifecycle("reactivate_clean")}
        onCancel={() => setConfirm(null)}
      />
      <ConfirmDialog
        open={confirm === "delete"}
        title={<Bi id="Hapus tenant permanen?" en="Delete tenant permanently?" />}
        message={<Bi id="Semua data tenant dihapus, koneksi YouTube dicabut, file dibersihkan. Bukti pembayaran tetap disimpan (legal). Tindakan ini TIDAK bisa dibatalkan." en="All tenant data is deleted, YouTube is disconnected, and files are purged. Payment records are kept (legal). This action CANNOT be undone." />}
        confirmLabel={<Bi id="Ya, hapus permanen" en="Yes, delete permanently" />}
        confirmClass="btn-destructive"
        busy={busy}
        onConfirm={doHardDelete}
        onCancel={() => setConfirm(null)}
      />

      {toast && <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 70, background: "var(--surface-raised, #1f2937)", color: "var(--text-primary)", padding: "0.625rem 1rem", borderRadius: 8, border: "1px solid var(--border)" }}>{toast}</div>}
    </>
  );
}
