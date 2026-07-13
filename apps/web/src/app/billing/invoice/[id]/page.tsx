"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

// Invoice / bukti bayar SIAP-CETAK (pemilik + admin, via /api/invoice/[id]). Standalone (tanpa AppShell → bersih
// saat print). Dwibahasa ID/EN. PPN dari config (0 = harga final). Print-to-PDF via window.print().

type Data = {
  payment: { order_id: string; category: string; plan_type: string | null; gross_amount: number; currency: string | null;
             status: string; payment_type: string | null; period_start: string | null; period_end: string | null;
             period_months?: number | null; created_at: string };
  plan_display_name?: string | null;
  buyer: { name: string | null; email: string | null };
  company: { legal_name: string; brand: string; tagline: string; website: string; email: string; phone: string;
             address: string; npwp: string; nib: string; sk_menkum: string } | null;
  ppn_percent: number;
};

const idr = (n: number) => `Rp ${Number(n || 0).toLocaleString("id-ID")}`;
const SETTLED = (s: string) => ["settlement", "capture", "paid"].includes((s || "").toLowerCase());

export default function InvoicePage() {
  const params = useParams();
  const orderId = String(params?.id || "");
  const [lang, setLang] = useState<"id" | "en">("id");
  const [d, setD] = useState<Data | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if ((navigator.language || "id").toLowerCase().startsWith("en")) setLang("en");
    fetch(`/api/invoice/${orderId}`).then((r) => r.ok ? r.json() : r.json().then((j) => Promise.reject(j.error || r.status)))
      .then(setD).catch((e) => setErr(String(e)));
  }, [orderId]);

  const t = (id: string, en: string) => (lang === "id" ? id : en);
  if (err) return <div style={{ padding: "3rem", textAlign: "center" }}>{t("Invoice tidak ditemukan / tidak diizinkan.", "Invoice not found / not allowed.")} ({err})</div>;
  if (!d) return <div style={{ padding: "3rem", textAlign: "center" }} className="muted">{t("Memuat…", "Loading…")}</div>;

  const p = d.payment, co = d.company;
  const settled = SETTLED(p.status);
  const total = p.gross_amount || 0;
  const ppn = d.ppn_percent > 0 ? Math.round(total - total / (1 + d.ppn_percent / 100)) : 0;
  const dpp = total - ppn;
  // Nama paket = display_name (admin-editable, Pilar 4); fallback kapitalisasi key. + label periode tahunan.
  const planLabel = d.plan_display_name || (p.plan_type ? p.plan_type.charAt(0).toUpperCase() + p.plan_type.slice(1) : "");
  const periodTag = (p.period_months ?? 1) === 12 ? ` (${t("Tahunan", "Annual")})` : "";
  const itemName = p.category === "addon" ? t("Niche custom (add-on)", "Custom niche (add-on)")
    : `${t("Langganan", "Subscription")} ${planLabel}${periodTag}`;
  const periode = p.period_start && p.period_end
    ? `${new Date(p.period_start).toLocaleDateString("id-ID")} – ${new Date(p.period_end).toLocaleDateString("id-ID")}` : "—";

  return (
    <div style={{ background: "#fff", color: "#1f2430", minHeight: "100vh", padding: "2rem 1rem" }}>
      <style>{`@media print { .noprint { display: none !important; } body { background:#fff; } } .inv-tbl th,.inv-tbl td{padding:.55rem .5rem;border-bottom:1px solid #e6e8f0;text-align:left;font-size:14px} .inv-tbl th{color:#6b7280;font-weight:600}`}</style>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div className="noprint" style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
          <div style={{ display: "flex", gap: 6, border: "1px solid #ddd", borderRadius: 8, overflow: "hidden" }}>
            <button onClick={() => setLang("id")} style={{ padding: "4px 10px", background: lang === "id" ? "#6366F1" : "#fff", color: lang === "id" ? "#fff" : "#333", border: 0, cursor: "pointer" }}>ID</button>
            <button onClick={() => setLang("en")} style={{ padding: "4px 10px", background: lang === "en" ? "#6366F1" : "#fff", color: lang === "en" ? "#fff" : "#333", border: 0, cursor: "pointer" }}>EN</button>
          </div>
          <button onClick={() => window.print()} style={{ padding: "8px 18px", background: "#6366F1", color: "#fff", border: 0, borderRadius: 8, fontWeight: 600, cursor: "pointer" }}>🖨 {t("Cetak / Unduh PDF", "Print / Download PDF")}</button>
        </div>

        <div style={{ border: "1px solid #e6e8f0", borderRadius: 12, padding: "2rem" }}>
          {/* header */}
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
            <div>
              <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-.01em" }}>INVOICE</div>
              <div style={{ color: "#6b7280", fontSize: 13, marginTop: 4 }}>No: <b style={{ color: "#1f2430" }}>{p.order_id}</b></div>
              <div style={{ color: "#6b7280", fontSize: 13 }}>{t("Tanggal", "Date")}: {new Date(p.created_at).toLocaleDateString(lang === "id" ? "id-ID" : "en-US", { day: "numeric", month: "long", year: "numeric" })}</div>
              <div style={{ marginTop: 6, display: "inline-block", padding: "2px 10px", borderRadius: 20, fontSize: 12, fontWeight: 700, background: settled ? "#dcfce7" : "#fef3c7", color: settled ? "#166534" : "#92400e" }}>{settled ? t("LUNAS", "PAID") : (p.status || "").toUpperCase()}</div>
            </div>
            <div style={{ textAlign: "right", fontSize: 13, lineHeight: 1.5 }}>
              <div style={{ fontWeight: 700, fontSize: 15 }}>{co?.legal_name}</div>
              {co?.brand && <div style={{ color: "#6366F1", fontWeight: 600 }}>{co.brand} — {co.tagline}</div>}
              <div style={{ color: "#6b7280", maxWidth: 280 }}>{co?.address}</div>
              <div style={{ color: "#6b7280" }}>{co?.phone} · {co?.email}</div>
              {co?.npwp && <div style={{ color: "#6b7280" }}>NPWP: {co.npwp}</div>}
              {co?.nib && <div style={{ color: "#6b7280" }}>NIB: {co.nib}</div>}
            </div>
          </div>

          {/* buyer */}
          <div style={{ background: "#fafbff", border: "1px solid #eef", borderRadius: 8, padding: "0.75rem 1rem", marginBottom: "1.25rem" }}>
            <div style={{ color: "#6b7280", fontSize: 12 }}>{t("Ditagihkan kepada", "Billed to")}</div>
            <div style={{ fontWeight: 600 }}>{d.buyer.name || d.buyer.email || "—"}</div>
            {d.buyer.email && <div style={{ color: "#6b7280", fontSize: 13 }}>{d.buyer.email}</div>}
          </div>

          {/* items */}
          <table className="inv-tbl" style={{ width: "100%", borderCollapse: "collapse", marginBottom: "1rem" }}>
            <thead><tr><th>{t("Deskripsi", "Description")}</th><th>{t("Periode", "Period")}</th><th style={{ textAlign: "right" }}>{t("Jumlah", "Amount")}</th></tr></thead>
            <tbody>
              <tr><td style={{ fontWeight: 500 }}>{itemName}</td><td style={{ color: "#6b7280" }}>{p.category === "addon" ? "—" : periode}</td><td style={{ textAlign: "right" }}>{idr(dpp)}</td></tr>
            </tbody>
          </table>

          {/* totals */}
          <div style={{ marginLeft: "auto", maxWidth: 260 }}>
            {d.ppn_percent > 0 && (<>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, padding: "2px 0", color: "#6b7280" }}><span>{t("DPP", "Subtotal")}</span><span>{idr(dpp)}</span></div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, padding: "2px 0", color: "#6b7280" }}><span>PPN {d.ppn_percent}%</span><span>{idr(ppn)}</span></div>
            </>)}
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 17, fontWeight: 800, borderTop: "2px solid #1f2430", paddingTop: 8, marginTop: 6 }}><span>Total</span><span>{idr(total)}</span></div>
            <div style={{ color: "#6b7280", fontSize: 12, marginTop: 4, textAlign: "right" }}>{t("Metode", "Method")}: {p.payment_type || "—"}</div>
          </div>

          <div style={{ marginTop: "2rem", paddingTop: "1rem", borderTop: "1px solid #e6e8f0", color: "#9aa1b1", fontSize: 12, textAlign: "center" }}>
            {t("Terima kasih atas kepercayaan Anda.", "Thank you for your business.")} · {co?.website} · MesinViral
          </div>
        </div>
      </div>
    </div>
  );
}
