"use client";

import { useState, useEffect, useCallback } from "react";
import { Handshake, Plus, X, RefreshCw, Eye, CheckCircle2, Banknote } from "lucide-react";
import "./partners.css";

// [B21] Admin Program Agen F1 (SPEC AGENT_AND_AFILIATION_ARCITECTURE.md §1f/5c):
// resume lintas-agen + rinci per-agen + gerbang pencairan owner. Rate/pajak agen HANYA di sini.
// Uang via /api/admin/partners/ops → partner.py (satu otoritas). Dwibahasa Bi (data-id/data-en).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Agent = {
  id: string; company_name: string; pic_name: string | null; pic_email: string; status: string;
  commission_type: string; commission_value: number; tax_status: string; created_at: string;
  code: string | null; tenants: number; accrued_idr: number; paid_idr: number;
};
type Payout = {
  id: string; agent_id: string; period_month: string; gross_commission_idr: number; deduction_idr: number;
  tax_withheld_idr: number; net_paid_idr: number | null; status: string; transfer_ref: string | null;
};
type AgentRow = {
  id: string; company_name: string; pic_name: string | null; pic_email: string; pic_phone: string | null;
  status: string; commission_type: string; commission_value: number; tax_status: string;
  npwp: string | null; notes: string | null; bank_name: string | null; bank_holder: string | null;
  bank_account_set: boolean; user_id: string | null;
};
type Detail = {
  agent: AgentRow;
  codes: { code: string; owner_kind: string; active: boolean; used_count: number }[];
  tenants: { tenant_id: string; display_handle: string | null; plan_type: string; subscription_status: string }[];
  ledger: { id: number; order_id: string; entry_kind: string; status: string; agent_amount_idr: number; period_month: string; months_paid: number }[];
  payouts: Payout[];
};

const idr = (n: number | null | undefined) => `Rp ${Math.round(Number(n ?? 0)).toLocaleString("id-ID")}`;
const TAX: Record<string, string> = { badan_npwp: "Badan (NPWP)", badan_non_npwp: "Badan tanpa NPWP", perorangan: "Perorangan", pkp: "PKP" };
const PO_BADGE: Record<string, string> = { draft: "badge-warning", approved: "badge-info", paid: "badge-success" };
function prevMonth(): string {
  const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

const EMPTY_FORM = { company_name: "", pic_name: "", pic_email: "", pic_phone: "", code: "",
  commission_type: "percent", commission_value: "20", tax_status: "badan_npwp", npwp: "", notes: "" };

export default function PartnersAdmin() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [cfg, setCfg] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Record<string, string>>(EMPTY_FORM);
  const [editId, setEditId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [bank, setBank] = useState({ bank_name: "", account_no: "", holder: "" });
  const [period, setPeriod] = useState(prevMonth());
  const [refInput, setRefInput] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const j = await fetch("/api/admin/partners").then((r) => r.json()).catch(() => null);
    if (j) { setAgents(j.agents ?? []); setPayouts(j.payouts ?? []); setCfg(j.config ?? {}); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function openDetail(id: string) {
    const j = await fetch(`/api/admin/partners?id=${id}`).then((r) => r.json()).catch(() => null);
    if (j?.agent) { setDetail(j); setBank({ bank_name: j.agent.bank_name ?? "", account_no: "", holder: j.agent.bank_holder ?? "" }); }
  }
  function startEdit(d: Detail) {
    const a = d.agent;
    setEditId(a.id);
    setForm({ company_name: a.company_name ?? "", pic_name: a.pic_name ?? "",
      pic_email: a.pic_email ?? "", pic_phone: a.pic_phone ?? "",
      code: d.codes.find((c) => c.owner_kind === "agent")?.code ?? "",
      commission_type: a.commission_type, commission_value: String(a.commission_value),
      tax_status: a.tax_status, npwp: a.npwp ?? "", notes: a.notes ?? "" });
    setDetail(null); setShowForm(true);
  }
  async function saveAgent() {
    setBusy(true); setMsg(null);
    const payload = { ...form, commission_value: Number(form.commission_value) };
    const res = editId
      ? await fetch("/api/admin/partners", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: editId, patch: payload }) })
      : await fetch("/api/admin/partners", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const j = await res.json().catch(() => ({}));
    setBusy(false);
    if (!res.ok) return setMsg(j.error || "gagal");
    setShowForm(false); setEditId(null); setForm(EMPTY_FORM); void load();
  }
  async function ops(body: Record<string, unknown>): Promise<Record<string, unknown> | null> {
    setBusy(true); setMsg(null);
    const res = await fetch("/api/admin/partners/ops", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await res.json().catch(() => ({}));
    setBusy(false);
    if (!res.ok) { setMsg(j.error || "gagal"); return null; }
    return j;
  }
  async function toggleSuspend(a: Agent) {
    const to = a.status === "active" ? "suspended" : "active";
    if (!window.confirm(to === "suspended"
      ? `Suspend ${a.company_name}? Semua kodenya berhenti menerima pendaftaran BARU seketika.`
      : `Aktifkan kembali ${a.company_name}?`)) return;
    await fetch("/api/admin/partners", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: a.id, patch: { status: to } }) });
    void load();
  }
  async function saveBank(agentId: string) {
    const j = await ops({ op: "bank_set", agent_id: agentId, ...bank });
    if (j) { setMsg("rekening tersimpan (terenkripsi)"); void openDetail(agentId); }
  }
  async function revealBank(agentId: string) {
    const j = await ops({ op: "bank_reveal", agent_id: agentId }) as { bank_name?: string; account_no?: string; bank_holder?: string } | null;
    if (j) window.alert(`${j.bank_name ?? "?"} · ${j.account_no ?? "(belum diisi)"} · a.n. ${j.bank_holder ?? "?"}`);
  }
  async function invitePortal(agentId: string) {
    setBusy(true); setMsg(null);
    const res = await fetch("/api/admin/partners/invite", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ agent_id: agentId }) });
    const j = await res.json().catch(() => ({}));
    setBusy(false);
    if (!res.ok) return setMsg(j.error || "gagal mengundang");
    setMsg("undangan portal terkirim ke email PIC");
    void openDetail(agentId);
  }
  async function buildDrafts() {
    const j = await ops({ op: "payouts_build", period_month: `${period}-01` }) as { built?: unknown[]; skipped?: unknown[] } | null;
    if (j) { setMsg(`draft tersusun: ${j.built?.length ?? 0} agen · digulung/dilewati: ${j.skipped?.length ?? 0}`); void load(); }
  }
  async function approvePo(p: Payout) {
    if (!window.confirm(`Setujui tagihan ${idr(p.net_paid_idr)} utk periode ${p.period_month.slice(0, 7)}? Baris komisi ikut terkunci.`)) return;
    if (await ops({ op: "payout_approve", payout_id: p.id })) void load();
  }
  async function paidPo(p: Payout) {
    const ref = (refInput[p.id] ?? "").trim();
    if (!window.confirm(`Tandai DIBAYAR ${idr(p.net_paid_idr)}${ref ? ` (ref ${ref})` : ""}? Pastikan transfer sudah dilakukan.`)) return;
    if (await ops({ op: "payout_paid", payout_id: p.id, transfer_ref: ref })) void load();
  }

  const agentName = (id: string) => agents.find((a) => a.id === id)?.company_name ?? id.slice(0, 8);
  const kAccrued = agents.reduce((s, a) => s + a.accrued_idr, 0);
  const kPaid = agents.reduce((s, a) => s + a.paid_idr, 0);

  return (
    <div>
      <div className="pt-head">
        <div>
          <h1><Handshake size={26} style={{ verticalAlign: "-4px", marginRight: "0.5rem" }} /><Bi id="Program Agen" en="Partner Program" /></h1>
          <p style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)", margin: 0 }}>
            <Bi id={`Komisi cair tiap tanggal ${cfg.partner_payout_day ?? 5} · ambang minimum ${idr(cfg.partner_min_payout_idr)} · atribusi = kode saat daftar (permanen)`}
               en={`Payout on day ${cfg.partner_payout_day ?? 5} monthly · minimum ${idr(cfg.partner_min_payout_idr)} · attribution = code at signup (permanent)`} />
          </p>
        </div>
        <button className="btn btn-default" onClick={() => { setEditId(null); setForm(EMPTY_FORM); setShowForm(true); }}>
          <Plus size={15} /> <Bi id="Tambah agen" en="Add agent" /></button>
      </div>

      <div className="pt-kpis">
        <div className="pt-kpi"><div className="l"><Bi id="Agen aktif" en="Active agents" /></div><div className="v">{agents.filter((a) => a.status === "active").length}</div></div>
        <div className="pt-kpi"><div className="l"><Bi id="Tenant bawaan" en="Referred tenants" /></div><div className="v">{agents.reduce((s, a) => s + a.tenants, 0)}</div></div>
        <div className="pt-kpi"><div className="l"><Bi id="Komisi berjalan" en="Accrued commission" /></div><div className="v">{idr(kAccrued)}</div></div>
        <div className="pt-kpi"><div className="l"><Bi id="Sudah dibayar" en="Paid out" /></div><div className="v">{idr(kPaid)}</div></div>
      </div>

      {msg && <div className="pt-card" style={{ color: "var(--text-secondary)" }}>{msg} <button className="btn btn-outline btn-sm" style={{ marginLeft: "0.5rem" }} onClick={() => setMsg(null)}><X size={12} /></button></div>}

      {showForm && (
        <div className="pt-card">
          <p className="pt-sec">{editId ? <Bi id="Edit agen" en="Edit agent" /> : <Bi id="Agen baru (setelah kontrak ditandatangani)" en="New agent (after contract signed)" />}</p>
          <div className="pt-grid3">
            <div><label className="label"><Bi id="Nama perusahaan" en="Company name" /></label><input className="input" value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} /></div>
            <div><label className="label">PIC</label><input className="input" value={form.pic_name} onChange={(e) => setForm({ ...form, pic_name: e.target.value })} /></div>
            <div><label className="label">Email PIC</label><input className="input" value={form.pic_email} onChange={(e) => setForm({ ...form, pic_email: e.target.value })} /></div>
            <div><label className="label"><Bi id="Telepon" en="Phone" /></label><input className="input" value={form.pic_phone} onChange={(e) => setForm({ ...form, pic_phone: e.target.value })} /></div>
            <div><label className="label"><Bi id="Kode unik (4-12 huruf/angka; BEKU setelah dipakai)" en="Unique code (4-12 chars; frozen once used)" /></label>
              <input className="input" style={{ textTransform: "uppercase" }} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} /></div>
            <div><label className="label">NPWP</label><input className="input" value={form.npwp} onChange={(e) => setForm({ ...form, npwp: e.target.value })} /></div>
            <div><label className="label"><Bi id="Tipe komisi" en="Commission type" /></label>
              <select className="input" value={form.commission_type} onChange={(e) => setForm({ ...form, commission_type: e.target.value })}>
                <option value="percent">Persen dari pembayaran / Percent (%)</option>
                <option value="flat_idr">Rupiah tetap per bulan-langganan / Flat IDR</option>
              </select></div>
            <div><label className="label"><Bi id="Nilai (% atau Rp)" en="Value (% or IDR)" /></label><input className="input" type="number" min={0} value={form.commission_value} onChange={(e) => setForm({ ...form, commission_value: e.target.value })} /></div>
            <div><label className="label"><Bi id="Status pajak (prefill potongan PPh)" en="Tax status (withholding prefill)" /></label>
              <select className="input" value={form.tax_status} onChange={(e) => setForm({ ...form, tax_status: e.target.value })}>
                {Object.entries(TAX).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select></div>
          </div>
          <div style={{ marginTop: "0.75rem" }}><label className="label"><Bi id="Catatan" en="Notes" /></label><input className="input" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.875rem" }}>
            <button className="btn btn-default" onClick={saveAgent} disabled={busy}>{busy ? "…" : <Bi id="Simpan" en="Save" />}</button>
            <button className="btn btn-outline" onClick={() => { setShowForm(false); setEditId(null); }}><Bi id="Batal" en="Cancel" /></button>
          </div>
        </div>
      )}

      <div className="pt-card" style={{ padding: 0, overflowX: "auto" }}>
        <table className="tbl pt-tbl">
          <thead><tr>
            <th><Bi id="Agen" en="Agent" /></th><th><Bi id="Kode" en="Code" /></th><th><Bi id="Komisi" en="Commission" /></th>
            <th><Bi id="Pajak" en="Tax" /></th><th>Tenant</th><th><Bi id="Berjalan" en="Accrued" /></th><th><Bi id="Dibayar" en="Paid" /></th><th>Status</th><th></th>
          </tr></thead>
          <tbody>
            {agents.length === 0 && <tr><td colSpan={9} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}><Bi id="Belum ada agen — tambah setelah kontrak ditandatangani." en="No agents yet — add one after the contract is signed." /></td></tr>}
            {agents.map((a) => (
              <tr key={a.id} onClick={() => void openDetail(a.id)}>
                <td><strong>{a.company_name}</strong><div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{a.pic_name || a.pic_email}</div></td>
                <td><span className="badge badge-outline">{a.code ?? "—"}</span></td>
                <td>{a.commission_type === "percent" ? `${a.commission_value}%` : `${idr(a.commission_value)}/bln`}</td>
                <td style={{ fontSize: "var(--text-xs)" }}>{TAX[a.tax_status] ?? a.tax_status}</td>
                <td className="pt-num">{a.tenants}</td>
                <td className="pt-num">{idr(a.accrued_idr)}</td>
                <td className="pt-num">{idr(a.paid_idr)}</td>
                <td><span className={`badge ${a.status === "active" ? "badge-success" : "badge-error"}`}>{a.status}</span></td>
                <td onClick={(e) => e.stopPropagation()}>
                  <button className="btn btn-outline btn-sm" onClick={() => void toggleSuspend(a)}>{a.status === "active" ? "Suspend" : <Bi id="Aktifkan" en="Activate" />}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pt-card">
        <p className="pt-sec"><Banknote size={13} style={{ verticalAlign: "-2px" }} /> <Bi id="Pencairan bulanan (gerbang owner — tidak ada uang keluar otomatis)" en="Monthly payouts (owner gate — money never moves automatically)" /></p>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.875rem", flexWrap: "wrap" }}>
          <input className="input" type="month" style={{ width: "11rem" }} value={period} onChange={(e) => setPeriod(e.target.value)} />
          <button className="btn btn-default btn-sm" onClick={buildDrafts} disabled={busy}><RefreshCw size={13} /> <Bi id="Susun draft tagihan periode ini" en="Build drafts for this period" /></button>
          <a className="btn btn-outline btn-sm" href={`/api/admin/partners/tax-recap?year=${period.slice(0, 4)}`}><Bi id={`Rekap pajak ${period.slice(0, 4)} (Excel)`} en={`Tax recap ${period.slice(0, 4)} (Excel)`} /></a>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th><Bi id="Agen" en="Agent" /></th><th><Bi id="Periode" en="Period" /></th><th><Bi id="Kotor" en="Gross" /></th><th><Bi id="Pengurang" en="Deduction" /></th><th><Bi id="PPh" en="Tax" /></th><th><Bi id="Transfer bersih" en="Net transfer" /></th><th>Status</th><th></th></tr></thead>
            <tbody>
              {payouts.length === 0 && <tr><td colSpan={8} style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-muted)" }}><Bi id="Belum ada tagihan." en="No payouts yet." /></td></tr>}
              {payouts.map((p) => (
                <tr key={p.id}>
                  <td>{agentName(p.agent_id)}</td>
                  <td>{p.period_month.slice(0, 7)}</td>
                  <td className="pt-num">{idr(p.gross_commission_idr)}</td>
                  <td className="pt-num">{p.deduction_idr ? `− ${idr(p.deduction_idr)}` : "—"}</td>
                  <td className="pt-num">{idr(p.tax_withheld_idr)}</td>
                  <td className="pt-num"><strong>{idr(p.net_paid_idr)}</strong></td>
                  <td><span className={`badge ${PO_BADGE[p.status] ?? "badge-default"}`}>{p.status}</span>{p.transfer_ref && <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>ref {p.transfer_ref}</div>}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {p.status === "draft" && <button className="btn btn-default btn-sm" disabled={busy} onClick={() => void approvePo(p)}><CheckCircle2 size={13} /> <Bi id="Setujui" en="Approve" /></button>}
                    {p.status === "approved" && (<span style={{ display: "inline-flex", gap: "0.375rem" }}>
                      <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => void revealBank(p.agent_id)}><Eye size={13} /> <Bi id="Rekening" en="Bank" /></button>
                      <input className="input" style={{ width: "7.5rem", height: "1.875rem", fontSize: "var(--text-xs)" }} placeholder="ref transfer" value={refInput[p.id] ?? ""} onChange={(e) => setRefInput({ ...refInput, [p.id]: e.target.value })} />
                      <button className="btn btn-default btn-sm" disabled={busy} onClick={() => void paidPo(p)}><Bi id="Tandai dibayar" en="Mark paid" /></button>
                    </span>)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drawer rinci per-agen (SPEC §1f) */}
      <div className={`pt-scrim${detail ? " open" : ""}`} onClick={() => setDetail(null)} />
      <div className={`pt-drawer${detail ? " open" : ""}`}>
        {detail && (<>
          <div className="pt-drawer-head">
            <div><strong style={{ fontSize: "var(--text-lg)" }}>{detail.agent.company_name}</strong>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{detail.agent.pic_email}</div></div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-outline btn-sm" onClick={() => startEdit(detail)}><Bi id="Edit" en="Edit" /></button>
              <button className="btn btn-outline btn-sm" onClick={() => setDetail(null)}><X size={14} /></button>
            </div>
          </div>
          <div className="pt-drawer-body">
            <div>
              <p className="pt-sec"><Bi id="Ringkasan" en="Summary" /></p>
              <div className="pt-kv"><span className="k"><Bi id="Kode" en="Codes" /></span><span className="v">{detail.codes.map((c) => `${c.code}${c.used_count ? ` (dipakai ${c.used_count}×)` : ""}`).join(" · ") || "—"}</span></div>
              <div className="pt-kv"><span className="k"><Bi id="Komisi" en="Commission" /></span><span className="v">{detail.agent.commission_type === "percent" ? `${detail.agent.commission_value}%` : `${idr(detail.agent.commission_value)}/bln`}</span></div>
              <div className="pt-kv"><span className="k"><Bi id="Pajak" en="Tax" /></span><span className="v">{TAX[detail.agent.tax_status] ?? detail.agent.tax_status}{detail.agent.npwp ? ` · NPWP ${detail.agent.npwp}` : ""}</span></div>
              <div className="pt-kv"><span className="k"><Bi id="Portal agen" en="Agent portal" /></span>
                <span className="v" style={{ display: "inline-flex", gap: "0.5rem", alignItems: "center" }}>
                  <span className={`badge ${detail.agent.user_id ? "badge-success" : "badge-default"}`}>{detail.agent.user_id ? <Bi id="terhubung" en="linked" /> : <Bi id="belum ada login" en="no login yet" />}</span>
                  <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => void invitePortal(detail.agent.id)}>
                    {detail.agent.user_id ? <Bi id="Kirim ulang undangan" en="Resend invite" /> : <Bi id="Undang login portal" en="Invite portal login" />}
                  </button>
                </span></div>
            </div>
            <div>
              <p className="pt-sec"><Bi id="Rekening transfer (nomor terenkripsi)" en="Transfer bank (number encrypted)" /></p>
              <div className="pt-grid3">
                <input className="input" placeholder="Bank" value={bank.bank_name} onChange={(e) => setBank({ ...bank, bank_name: e.target.value })} />
                <input className="input" placeholder={detail.agent.bank_account_set ? "•••••• (terisi)" : "No. rekening"} value={bank.account_no} onChange={(e) => setBank({ ...bank, account_no: e.target.value })} />
                <input className="input" placeholder="Atas nama" value={bank.holder} onChange={(e) => setBank({ ...bank, holder: e.target.value })} />
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <button className="btn btn-outline btn-sm" disabled={busy || !bank.account_no} onClick={() => void saveBank(detail.agent.id)}><Bi id="Simpan rekening" en="Save bank" /></button>
                {detail.agent.bank_account_set && <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => void revealBank(detail.agent.id)}><Eye size={13} /> <Bi id="Lihat nomor" en="Reveal" /></button>}
              </div>
            </div>
            <div>
              <p className="pt-sec"><Bi id={`Tenant bawaan (${detail.tenants.length})`} en={`Referred tenants (${detail.tenants.length})`} /></p>
              <div className="pt-mini">
                {detail.tenants.length === 0 && <div className="row" style={{ color: "var(--text-muted)" }}><Bi id="Belum ada." en="None yet." /></div>}
                {detail.tenants.map((t) => (<div className="row" key={t.tenant_id}>
                  <span>{t.display_handle || t.tenant_id.slice(0, 8)}</span>
                  <span><span className="badge badge-outline">{t.plan_type}</span> <span className={`badge ${t.subscription_status === "active" ? "badge-success" : "badge-default"}`}>{t.subscription_status}</span></span>
                </div>))}
              </div>
            </div>
            <div>
              <p className="pt-sec"><Bi id="Buku besar komisi (terbaru)" en="Commission ledger (latest)" /></p>
              <div className="pt-mini">
                {detail.ledger.length === 0 && <div className="row" style={{ color: "var(--text-muted)" }}><Bi id="Belum ada komisi." en="No commissions yet." /></div>}
                {detail.ledger.slice(0, 30).map((l) => (<div className="row" key={l.id}>
                  <span style={{ fontSize: "var(--text-xs)" }}>{l.order_id}<span style={{ color: "var(--text-muted)" }}> · {l.period_month.slice(0, 7)}{l.months_paid > 1 ? ` · ${l.months_paid} bln` : ""}</span></span>
                  <span className="pt-num" style={{ color: l.entry_kind === "reversal" ? "var(--error)" : undefined }}>{idr(l.agent_amount_idr)} <span className="badge badge-outline">{l.status}</span></span>
                </div>))}
              </div>
            </div>
          </div>
        </>)}
      </div>
    </div>
  );
}
