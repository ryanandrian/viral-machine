"use client";

import { useState, useEffect } from "react";
import { Copy, Check } from "lucide-react";
import "./agent.css";

// [B21] F2 — dasbor agen: angka dari SATU pintu /api/agent/overview (sumber tabel yang sama dgn
// admin rinci-per-agen — SPEC §1f nol selisih). Hanya milik agen ini (filter server, §6).
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Overview = {
  agent: { company_name: string; status: string; commission_type: string; commission_value: number;
    bank_name: string | null; bank_holder: string | null; bank_account_set: boolean };
  codes: { code: string; owner_kind: string; active: boolean; used_count: number }[];
  tenants: { label: string; plan: string; status: string; locked_at: string | null; code: string | null }[];
  ledger: { id: number; order_id: string; entry_kind: string; status: string; agent_amount_idr: number; period_month: string; months_paid: number }[];
  payouts: { id: string; period_month: string; gross_commission_idr: number; deduction_idr: number; tax_withheld_idr: number; net_paid_idr: number | null; status: string; transfer_ref: string | null }[];
  config: Record<string, number>;
};

const idr = (n: number | null | undefined) => `Rp ${Math.round(Number(n ?? 0)).toLocaleString("id-ID")}`;
const PO_BADGE: Record<string, string> = { draft: "badge-warning", approved: "badge-info", paid: "badge-success" };

export default function AgentDashboard() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/agent/overview").then(async (r) => {
      if (!r.ok) throw new Error((await r.json().catch(() => ({})) as { error?: string }).error || `HTTP ${r.status}`);
      setOv(await r.json());
    }).catch((e) => setErr(String(e.message || e)));
  }, []);

  async function copy(text: string, key: string) {
    try { await navigator.clipboard.writeText(text); setCopied(key); setTimeout(() => setCopied(null), 1500); } catch { /* clipboard ditolak browser — abaikan */ }
  }

  if (err) return <div className="ag-card" style={{ color: "var(--error)" }}>{err}</div>;
  if (!ov) return <div className="ag-card" style={{ color: "var(--text-muted)" }}>…</div>;

  const accrued = ov.ledger.filter((l) => l.status === "accrued" || l.status === "approved")
    .reduce((s, l) => s + Number(l.agent_amount_idr), 0);
  const paid = ov.payouts.filter((p) => p.status === "paid").reduce((s, p) => s + Number(p.net_paid_idr ?? 0), 0);
  const mainCode = ov.codes.find((c) => c.owner_kind === "agent" && c.active)?.code;
  const refLink = mainCode ? `https://mesinviral.com/?ref=${mainCode}` : null;

  return (
    <div>
      {ov.agent.status !== "active" && (
        <div className="ag-card" style={{ borderColor: "var(--error)", color: "var(--text-secondary)" }}>
          <Bi id="Akun agen Anda sedang ditangguhkan — kode berhenti menerima pendaftaran baru. Hubungi MesinViral untuk klarifikasi."
             en="Your agent account is suspended — codes no longer accept new signups. Contact MesinViral for clarification." />
        </div>
      )}

      <div className="ag-kpis">
        <div className="ag-kpi"><div className="l"><Bi id="Pelanggan bawaan" en="Referred customers" /></div><div className="v">{ov.tenants.length}</div></div>
        <div className="ag-kpi"><div className="l"><Bi id="Komisi berjalan" en="Accrued commission" /></div><div className="v">{idr(accrued)}</div></div>
        <div className="ag-kpi"><div className="l"><Bi id="Sudah dibayar (bersih)" en="Paid out (net)" /></div><div className="v">{idr(paid)}</div></div>
        <div className="ag-kpi"><div className="l"><Bi id="Skema komisi Anda" en="Your commission" /></div>
          <div className="v" style={{ fontSize: "var(--text-lg)" }}>{ov.agent.commission_type === "percent" ? `${ov.agent.commission_value}%` : `${idr(ov.agent.commission_value)}/bln`}</div></div>
      </div>

      <div className="ag-card">
        <p className="ag-sec"><Bi id="Kode & tautan Anda — calon pelanggan yang mendaftar membawa kode ini tercatat sebagai bawaan Anda (permanen)" en="Your code & link — signups carrying this code are permanently credited to you" /></p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          {mainCode ? (<>
            <span className="ag-code">{mainCode}
              <button className="btn btn-outline btn-sm" onClick={() => void copy(mainCode, "code")}>{copied === "code" ? <Check size={13} /> : <Copy size={13} />}</button>
            </span>
            {refLink && <span className="ag-code" style={{ letterSpacing: 0, fontWeight: 500, fontSize: "var(--text-sm)" }}>{refLink}
              <button className="btn btn-outline btn-sm" onClick={() => void copy(refLink, "link")}>{copied === "link" ? <Check size={13} /> : <Copy size={13} />}</button>
            </span>}
          </>) : <span style={{ color: "var(--text-muted)" }}><Bi id="Belum ada kode aktif — hubungi MesinViral." en="No active code — contact MesinViral." /></span>}
        </div>
      </div>

      <div className="ag-card">
        <p className="ag-sec"><Bi id={`Pelanggan bawaan Anda (${ov.tenants.length})`} en={`Your referred customers (${ov.tenants.length})`} /></p>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th><Bi id="Pelanggan" en="Customer" /></th><th><Bi id="Paket" en="Plan" /></th><th>Status</th><th><Bi id="Via kode" en="Via code" /></th><th><Bi id="Sejak" en="Since" /></th></tr></thead>
            <tbody>
              {ov.tenants.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-muted)" }}><Bi id="Belum ada — sebarkan kode/tautan Anda." en="None yet — share your code/link." /></td></tr>}
              {ov.tenants.map((t, i) => (<tr key={i}>
                <td><strong>{t.label}</strong></td>
                <td><span className="badge badge-outline">{t.plan}</span></td>
                <td><span className={`badge ${t.status === "active" ? "badge-success" : "badge-default"}`}>{t.status}</span></td>
                <td>{t.code ?? "—"}</td>
                <td style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{t.locked_at ? new Date(t.locked_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "—"}</td>
              </tr>))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="ag-card">
        <p className="ag-sec"><Bi id={`Pencairan komisi (cair tiap tanggal ${ov.config.partner_payout_day ?? 5}; minimum ${idr(ov.config.partner_min_payout_idr)})`} en={`Commission payouts (paid on day ${ov.config.partner_payout_day ?? 5}; minimum ${idr(ov.config.partner_min_payout_idr)})`} /></p>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th><Bi id="Periode" en="Period" /></th><th><Bi id="Kotor" en="Gross" /></th><th><Bi id="Pengurang" en="Deduction" /></th><th>PPh</th><th><Bi id="Diterima bersih" en="Net received" /></th><th>Status</th></tr></thead>
            <tbody>
              {ov.payouts.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-muted)" }}><Bi id="Belum ada pencairan." en="No payouts yet." /></td></tr>}
              {ov.payouts.map((p) => (<tr key={p.id}>
                <td>{p.period_month.slice(0, 7)}</td>
                <td className="ag-num">{idr(p.gross_commission_idr)}</td>
                <td className="ag-num">{p.deduction_idr ? `− ${idr(p.deduction_idr)}` : "—"}</td>
                <td className="ag-num">{idr(p.tax_withheld_idr)}</td>
                <td className="ag-num"><strong>{idr(p.net_paid_idr)}</strong></td>
                <td><span className={`badge ${PO_BADGE[p.status] ?? "badge-default"}`}>{p.status}</span>{p.transfer_ref && <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>ref {p.transfer_ref}</div>}</td>
              </tr>))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="ag-card">
        <p className="ag-sec"><Bi id="Riwayat komisi per pembayaran (terbaru)" en="Commission history per payment (latest)" /></p>
        <div className="ag-mini">
          {ov.ledger.length === 0 && <div className="row" style={{ color: "var(--text-muted)" }}><Bi id="Belum ada komisi — komisi lahir otomatis tiap pelanggan bawaan Anda membayar." en="No commissions yet — they appear automatically whenever your referred customer pays." /></div>}
          {ov.ledger.slice(0, 40).map((l) => (<div className="row" key={l.id}>
            <span style={{ fontSize: "var(--text-xs)" }}>{l.period_month.slice(0, 7)}{l.months_paid > 1 ? ` · ${l.months_paid} bln` : ""}{l.entry_kind === "reversal" ? " · refund" : ""}</span>
            <span className="ag-num" style={{ color: l.entry_kind === "reversal" ? "var(--error)" : undefined }}>{idr(l.agent_amount_idr)} <span className="badge badge-outline">{l.status}</span></span>
          </div>))}
        </div>
      </div>

      <div className="ag-card" style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
        <Bi id={`Rekening pencairan: ${ov.agent.bank_name ?? "—"} a.n. ${ov.agent.bank_holder ?? "—"} (${ov.agent.bank_account_set ? "nomor tersimpan aman" : "belum diisi — hubungi MesinViral"}). Perubahan rekening & skema komisi dilakukan oleh MesinViral sesuai kontrak.`}
           en={`Payout bank: ${ov.agent.bank_name ?? "—"} — ${ov.agent.bank_holder ?? "—"} (${ov.agent.bank_account_set ? "number stored securely" : "not set — contact MesinViral"}). Bank & commission changes are handled by MesinViral per contract.`} />
      </div>
    </div>
  );
}
