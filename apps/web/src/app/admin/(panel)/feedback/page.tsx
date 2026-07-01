"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageSquare } from "lucide-react";
import { PageHeader } from "@/components/page-header";

// Admin Masukan — daftar feedback_submissions (churn reason terstruktur + saran). Read-only, service_role.
function Bi({ id, en }: { id: string; en: string }) { return (<><span data-id>{id}</span><span data-en>{en}</span></>); }
const REASON: Record<string, { id: string; en: string }> = {
  price: { id: "Harga", en: "Price" },
  features: { id: "Fitur kurang", en: "Missing features" },
  results: { id: "Hasil kurang", en: "Results" },
  not_ready: { id: "Belum butuh", en: "Not ready" },
  other: { id: "Lainnya", en: "Other" },
};
type Fb = { id: string; tenant_id: string | null; reason: string | null; message: string | null; email: string | null; source: string | null; created_at: string };

export default function AdminFeedbackPage() {
  const [rows, setRows] = useState<Fb[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    const r = await fetch("/api/admin/feedback");
    const j = await r.json().catch(() => ({}));
    if (r.ok) setRows(j.feedback ?? []); else setErr(j.error || "Gagal memuat");
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <>
      <PageHeader icon={MessageSquare} title={<Bi id="Masukan" en="Feedback" />}
        subtitle={<Bi id="Masukan & alasan tenant belum melanjutkan (untuk perbaikan produk)." en="Tenant feedback & reasons for not continuing (product insight)." />} />
      {err && <div style={{ color: "var(--danger, #ef4444)", padding: "1rem" }}>{err}</div>}
      <div className="card"><div style={{ overflowX: "auto" }}><table className="tbl">
        <thead><tr>
          <th><Bi id="Tanggal" en="Date" /></th><th><Bi id="Alasan" en="Reason" /></th>
          <th><Bi id="Saran" en="Message" /></th><th>Email</th><th><Bi id="Sumber" en="Source" /></th>
        </tr></thead>
        <tbody>
          {loading && <tr><td colSpan={5} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}>Memuat…</td></tr>}
          {!loading && rows.length === 0 && <tr><td colSpan={5} className="muted" style={{ padding: "1.5rem", textAlign: "center" }}><Bi id="Belum ada masukan." en="No feedback yet." /></td></tr>}
          {rows.map((f) => (
            <tr key={f.id}>
              <td className="muted" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{new Date(f.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}</td>
              <td><span className="badge badge-default">{f.reason ? <><span data-id>{REASON[f.reason]?.id ?? f.reason}</span><span data-en>{REASON[f.reason]?.en ?? f.reason}</span></> : "—"}</span></td>
              <td style={{ maxWidth: 360, color: "var(--text-primary)" }}>{f.message || <span className="muted">—</span>}</td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{f.email || "—"}</td>
              <td className="muted" style={{ fontSize: "var(--text-xs)" }}>{f.source}</td>
            </tr>
          ))}
        </tbody>
      </table></div></div>
      {!loading && <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: ".625rem" }}>{rows.length} masukan</div>}
    </>
  );
}
