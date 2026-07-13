"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CreditCard, DollarSign, Receipt } from "lucide-react";
import { PageHeader } from "@/components/page-header";

// Admin Pembayaran — ledger transaksi `payments` (lintas-tenant, service_role, read-only).
// Reuse komponen/kelas standar (PageHeader, card, tbl, badge). Refund/aksi = dashboard Midtrans.
// Status langganan per-tenant tetap di halaman Tenant (anti-redundan) — halaman ini fokus TRANSAKSI.

function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
function fmtIDR(n: number | null | undefined) { return n == null ? "—" : `Rp ${Number(n).toLocaleString("id-ID")}`; }
const SETTLED = (s: string | null) => ["settlement", "capture", "paid"].includes((s || "").toLowerCase());
const CAT_LABEL: Record<string, { id: string; en: string }> = {
  subscription: { id: "Langganan", en: "Subscription" },
  addon: { id: "Add-on", en: "Add-on" },
};

type Pay = {
  order_id: string; tenant_id: string; tenant_email: string | null; category: string;
  plan_type: string | null; ref_id: string | null; gross_amount: number | null;
  currency: string | null; status: string | null; payment_type: string | null; created_at: string;
};

type Stats = { revenue_idr: number; settled_count: number; pending_count: number; total_count: number };

export default function AdminBillingPage() {
  const [rows, setRows] = useState<Pay[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [fStatus, setFStatus] = useState("all");

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    const r = await fetch("/api/admin/payments");
    const j = await r.json().catch(() => ({}));
    if (r.ok) { setRows(j.payments ?? []); setStats(j.stats ?? null); } else setErr(j.error || "Gagal memuat");
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  // Angka uang = agregat SQL SELURUH tabel dari server (Tahap 3 — kebal batas 500 baris daftar).
  const revenue = stats?.revenue_idr ?? 0;
  const settledCount = stats?.settled_count ?? 0;
  const pendingCount = stats?.pending_count ?? 0;
  const view = useMemo(() => rows.filter((p) => fStatus === "all"
    ? true : fStatus === "settled" ? SETTLED(p.status) : (p.status || "") === fStatus), [rows, fStatus]);

  return (
    <>
      <PageHeader icon={CreditCard} title={<Bi id="Pembayaran" en="Payments" />}
        subtitle={<Bi id="Transaksi langganan & add-on (Midtrans). Refund via dashboard Midtrans." en="Subscription & add-on transactions (Midtrans). Refund via the Midtrans dashboard." />} />

      {err && <div style={{ color: "var(--danger, #ef4444)", padding: "1rem" }}>{err}</div>}

      {/* Ringkasan */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "1.25rem" }}>
        <div className="card card-pad"><div className="card-title" style={{ marginBottom: ".5rem" }}><DollarSign size={16} /> <Bi id="Pendapatan (lunas)" en="Revenue (settled)" /></div><div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>{fmtIDR(revenue)}</div></div>
        <div className="card card-pad"><div className="card-title" style={{ marginBottom: ".5rem" }}><Receipt size={16} /> <Bi id="Transaksi lunas" en="Settled transactions" /></div><div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>{settledCount}</div></div>
        <div className="card card-pad"><div className="card-title" style={{ marginBottom: ".5rem" }}><Receipt size={16} /> <Bi id="Menunggu bayar" en="Pending" /></div><div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>{pendingCount}</div></div>
      </div>

      {/* Filter status */}
      <div className="segmented" style={{ marginBottom: "1rem" }}>
        {([["all", "Semua", "All"], ["settled", "Lunas", "Settled"], ["pending", "Menunggu", "Pending"]] as [string, string, string][]).map(([k, l, e]) =>
          <button key={k} aria-selected={fStatus === k} onClick={() => setFStatus(k)}><span data-id>{l}</span><span data-en>{e}</span></button>)}
      </div>

      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr>
          <th>Order</th><th>Tenant</th><th><Bi id="Jenis" en="Type" /></th>
          <th className="num"><Bi id="Jumlah" en="Amount" /></th><th><Bi id="Metode" en="Method" /></th>
          <th>Status</th><th><Bi id="Tanggal" en="Date" /></th>
        </tr></thead>
        <tbody>
          {loading && <tr><td colSpan={7} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
          {!loading && view.length === 0 && <tr><td colSpan={7} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}><Bi id="Belum ada transaksi." en="No transactions yet." /></td></tr>}
          {view.map((p) => (
            <tr key={p.order_id}>
              <td className="mono" style={{ fontSize: "0.6875rem" }}><a href={`/billing/invoice/${p.order_id}`} target="_blank" rel="noopener" style={{ color: "var(--brand)", textDecoration: "none" }} title="Lihat / cetak invoice">{p.order_id}</a></td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{p.tenant_email ?? p.tenant_id.slice(0, 8)}</td>
              <td><span className="badge badge-default">{(CAT_LABEL[p.category] ?? { id: p.category, en: p.category }) && <><span data-id>{CAT_LABEL[p.category]?.id ?? p.category}</span><span data-en>{CAT_LABEL[p.category]?.en ?? p.category}</span></>}{p.plan_type ? ` · ${p.plan_type}` : ""}</span></td>
              <td className="num"><b style={{ color: "var(--text-primary)", fontWeight: 600 }}>{fmtIDR(p.gross_amount)}</b></td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{p.payment_type ?? "—"}</td>
              <td><span className={`badge ${SETTLED(p.status) ? "badge-success" : (p.status || "") === "pending" ? "badge-warning" : "badge-default"}`}><span className="dot" />{p.status}</span></td>
              <td className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{new Date(p.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}</td>
            </tr>
          ))}
        </tbody>
      </table></div></div>
      {!loading && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".625rem" }}>
        <Bi id={`menampilkan ${view.length} dari ${stats?.total_count ?? rows.length} transaksi`} en={`showing ${view.length} of ${stats?.total_count ?? rows.length} transactions`} /> · <Bi id="Status langganan tenant di menu Tenant." en="Tenant subscription status in the Tenants menu." /></div>}
    </>
  );
}
