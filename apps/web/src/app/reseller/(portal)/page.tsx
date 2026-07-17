"use client";

import { useState, useEffect } from "react";
import { Copy, Check } from "lucide-react";
import "./reseller.css";

// [B21] F3 — dasbor reseller: pencapaian per periode/bulan (SPEC §1e), HANYA miliknya.
// Angka = buku besar yang sama dgn agen/admin (satu sumber); pembayaran = kewajiban AGEN.
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Overview = {
  reseller: { name: string; status: string; commission_type: string; commission_value: number;
    bank_name: string | null; bank_holder: string | null; bank_account_set: boolean; agent_company: string };
  code: string | null;
  tenants: { label: string; status: string; locked_at: string | null }[];
  monthly: { period: string; total_idr: number; n_payment: number }[];
};

const idr = (n: number | null | undefined) => `Rp ${Math.round(Number(n ?? 0)).toLocaleString("id-ID")}`;

export default function ResellerDashboard() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/reseller/overview").then(async (r) => {
      if (!r.ok) throw new Error((await r.json().catch(() => ({})) as { error?: string }).error || `HTTP ${r.status}`);
      setOv(await r.json());
    }).catch((e) => setErr(String(e.message || e)));
  }, []);

  async function copy(text: string, key: string) {
    try { await navigator.clipboard.writeText(text); setCopied(key); setTimeout(() => setCopied(null), 1500); } catch { /* clipboard ditolak — abaikan */ }
  }

  if (err) return <div className="rs-card" style={{ color: "var(--error)" }}>{err}</div>;
  if (!ov) return <div className="rs-card" style={{ color: "var(--text-muted)" }}>…</div>;

  const thisPeriod = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}-01`;
  const cur = ov.monthly.find((m) => m.period === thisPeriod);
  const totalAll = ov.monthly.reduce((s, m) => s + m.total_idr, 0);
  const refLink = ov.code ? `https://mesinviral.com/?ref=${ov.code}` : null;

  return (
    <div>
      {ov.reseller.status !== "active" && (
        <div className="rs-card" style={{ borderColor: "var(--error)", color: "var(--text-secondary)" }}>
          <Bi id="Status Anda sedang ditangguhkan — kode berhenti menerima pendaftaran baru. Hubungi agen Anda."
             en="Your status is suspended — your code no longer accepts new signups. Contact your agent." />
        </div>
      )}

      <div className="rs-kpis">
        <div className="rs-kpi"><div className="l"><Bi id="Pelanggan bawaan" en="Referred customers" /></div><div className="v">{ov.tenants.length}</div></div>
        <div className="rs-kpi"><div className="l"><Bi id="Komisi bulan ini" en="This month" /></div><div className="v">{idr(cur?.total_idr)}</div></div>
        <div className="rs-kpi"><div className="l"><Bi id="Total sepanjang waktu" en="All-time total" /></div><div className="v">{idr(totalAll)}</div></div>
        <div className="rs-kpi"><div className="l"><Bi id="Jatah Anda" en="Your cut" /></div>
          <div className="v" style={{ fontSize: "var(--text-lg)" }}>{ov.reseller.commission_type === "percent" ? `${ov.reseller.commission_value}%` : `${idr(ov.reseller.commission_value)}/bln`}</div></div>
      </div>

      <div className="rs-card">
        <p className="rs-sec"><Bi id="Kode & tautan Anda — pendaftar yang membawa kode ini tercatat sebagai bawaan Anda (permanen)" en="Your code & link — signups carrying it are permanently credited to you" /></p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          {ov.code ? (<>
            <span className="rs-code">{ov.code}
              <button className="btn btn-outline btn-sm" onClick={() => void copy(ov.code!, "code")}>{copied === "code" ? <Check size={13} /> : <Copy size={13} />}</button>
            </span>
            {refLink && <span className="rs-code" style={{ letterSpacing: 0, fontWeight: 500, fontSize: "var(--text-sm)" }}>{refLink}
              <button className="btn btn-outline btn-sm" onClick={() => void copy(refLink, "link")}>{copied === "link" ? <Check size={13} /> : <Copy size={13} />}</button>
            </span>}
          </>) : <span style={{ color: "var(--text-muted)" }}><Bi id="Kode belum aktif — hubungi agen Anda." en="Code not active — contact your agent." /></span>}
        </div>
      </div>

      <div className="rs-card">
        <p className="rs-sec"><Bi id="Pencapaian per bulan" en="Monthly performance" /></p>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th><Bi id="Periode" en="Period" /></th><th><Bi id="Pembayaran masuk" en="Payments" /></th><th><Bi id="Komisi Anda" en="Your commission" /></th></tr></thead>
            <tbody>
              {ov.monthly.length === 0 && <tr><td colSpan={3} style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-muted)" }}><Bi id="Belum ada — sebarkan kode/tautan Anda." en="None yet — share your code/link." /></td></tr>}
              {ov.monthly.map((m) => (<tr key={m.period}>
                <td>{m.period.slice(0, 7)}</td>
                <td className="rs-num">{m.n_payment}×</td>
                <td className="rs-num"><strong>{idr(m.total_idr)}</strong></td>
              </tr>))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rs-card">
        <p className="rs-sec"><Bi id={`Pelanggan bawaan Anda (${ov.tenants.length})`} en={`Your referred customers (${ov.tenants.length})`} /></p>
        <div className="rs-mini">
          {ov.tenants.length === 0 && <div className="row" style={{ color: "var(--text-muted)" }}><Bi id="Belum ada." en="None yet." /></div>}
          {ov.tenants.map((t, i) => (<div className="row" key={i}>
            <span>{t.label}</span>
            <span><span className={`badge ${t.status === "active" ? "badge-success" : "badge-default"}`}>{t.status}</span></span>
          </div>))}
        </div>
      </div>

      <div className="rs-card" style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
        <Bi id={`Komisi Anda dibayarkan oleh ${ov.reseller.agent_company} setiap bulan ke rekening ${ov.reseller.bank_name ?? "—"} a.n. ${ov.reseller.bank_holder ?? "—"} (${ov.reseller.bank_account_set ? "nomor tersimpan aman" : "belum diisi — hubungi agen Anda"}). Angka di halaman ini = perhitungan resmi sistem; jadwal transfer mengikuti agen Anda.`}
           en={`Your commission is paid by ${ov.reseller.agent_company} monthly to ${ov.reseller.bank_name ?? "—"} — ${ov.reseller.bank_holder ?? "—"} (${ov.reseller.bank_account_set ? "number stored securely" : "not set — contact your agent"}). Figures here are the official system calculation; transfer timing follows your agent.`} />
      </div>
    </div>
  );
}
