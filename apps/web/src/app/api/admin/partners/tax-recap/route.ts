import { NextResponse } from "next/server";
import { requireSuperAdmin } from "@/lib/admin/guard";
import { createAdminClient } from "@/lib/supabase/admin";
import ExcelJS from "exceljs";

// [B21] F4 — REKAP PAJAK TAHUNAN per agen (SPEC §6b: dasar bukti potong PPh; dukungan sistem).
// Hanya pencairan status PAID (uang benar-benar keluar) tahun tsb, per agen per periode + total.
export const runtime = "nodejs";

export async function GET(req: Request) {
  const g = await requireSuperAdmin(); if (g.error) return g.error;
  const year = new URL(req.url).searchParams.get("year") || "";
  if (!/^\d{4}$/.test(year)) return NextResponse.json({ error: "year wajib YYYY" }, { status: 400 });
  const a = createAdminClient();
  const [{ data: agents }, { data: payouts }] = await Promise.all([
    a.from("agents").select("id,company_name,tax_status,npwp"),
    a.from("agent_payouts").select("agent_id,period_month,gross_commission_idr,deduction_idr,tax_withheld_idr,net_paid_idr,paid_at,transfer_ref")
      .eq("status", "paid").gte("period_month", `${year}-01-01`).lte("period_month", `${year}-12-01`)
      .order("period_month"),
  ]);
  const agOf = Object.fromEntries((agents ?? []).map((x) => [x.id, x]));
  const TAX: Record<string, string> = { badan_npwp: "Badan (NPWP)", badan_non_npwp: "Badan tanpa NPWP", perorangan: "Perorangan", pkp: "PKP" };

  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(`Rekap Pajak ${year}`);
  ws.columns = [
    { header: "Agen", key: "agent", width: 28 }, { header: "Status Pajak", key: "tax", width: 18 },
    { header: "NPWP", key: "npwp", width: 20 }, { header: "Periode", key: "period", width: 10 },
    { header: "Bruto Komisi (Rp)", key: "gross", width: 17 }, { header: "Pengurang Refund (Rp)", key: "ded", width: 19 },
    { header: "PPh Dipotong (Rp)", key: "pph", width: 17 }, { header: "Ditransfer Bersih (Rp)", key: "net", width: 19 },
    { header: "Tgl Bayar", key: "paid", width: 12 }, { header: "Ref", key: "ref", width: 14 },
  ];
  ws.getRow(1).font = { bold: true };
  ws.getColumn("npwp").numFmt = "@";
  for (const k of ["gross", "ded", "pph", "net"]) ws.getColumn(k).numFmt = "#,##0";
  let tGross = 0, tPph = 0, tNet = 0;
  for (const p of payouts ?? []) {
    const ag = agOf[p.agent_id];
    tGross += Number(p.gross_commission_idr); tPph += Number(p.tax_withheld_idr); tNet += Number(p.net_paid_idr ?? 0);
    ws.addRow({
      agent: ag?.company_name ?? p.agent_id, tax: TAX[ag?.tax_status] ?? ag?.tax_status ?? "", npwp: ag?.npwp ?? "",
      period: String(p.period_month).slice(0, 7), gross: Number(p.gross_commission_idr),
      ded: Number(p.deduction_idr), pph: Number(p.tax_withheld_idr), net: Number(p.net_paid_idr ?? 0),
      paid: p.paid_at ? String(p.paid_at).slice(0, 10) : "", ref: p.transfer_ref ?? "",
    });
  }
  const tr = ws.addRow({ period: "TOTAL", gross: tGross, pph: tPph, net: tNet });
  tr.font = { bold: true };
  const buf = await wb.xlsx.writeBuffer();
  return new NextResponse(Buffer.from(buf), {
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": `attachment; filename="rekap-pajak-agen-${year}.xlsx"`,
      "Cache-Control": "no-store",
    },
  });
}
