import { NextResponse, type NextRequest } from "next/server";
import { requireAgent } from "@/lib/agent/guard";
import { vault } from "@/lib/youtube";
import ExcelJS from "exceljs";

// [B21] F3 — Export Excel transfer-massal komisi reseller per periode (SPEC 5d; ketok owner:
// .xlsx ASLI via exceljs — CSV ditolak krn no-rek berawalan 0 bisa terpotong). Angka & nomor
// rekening dibuka dari SATU otoritas (partner.py, include_bank) hanya utk sesi agen ybs.
export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const g = await requireAgent(); if (g.error) return g.error;
  const period = new URL(req.url).searchParams.get("period") || "";
  if (!/^\d{4}-\d{2}$/.test(period)) return NextResponse.json({ error: "period wajib YYYY-MM" }, { status: 400 });
  const r = await vault("/api/partner/op", {
    op: "reseller_breakdown", agent_id: g.agent.id, period_month: `${period}-01`, include_bank: true,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) return NextResponse.json({ error: j.error || "gagal mengambil rincian" }, { status: 502 });
  type Row = { name: string; email: string | null; bank_name: string | null; account_no?: string;
    bank_holder: string | null; total_idr: number; n_payment: number; n_refund: number;
    commission_type: string; commission_value: number };
  const rows: Row[] = (j.rows ?? []).filter((x: Row) => x.total_idr > 0);

  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(`Komisi ${period}`);
  ws.columns = [
    { header: "Nama Reseller", key: "name", width: 28 },
    { header: "Email", key: "email", width: 28 },
    { header: "Bank", key: "bank", width: 12 },
    { header: "No. Rekening", key: "acc", width: 20 },
    { header: "Atas Nama", key: "holder", width: 24 },
    { header: "Total Komisi (Rp)", key: "total", width: 18 },
    { header: "Jml Pembayaran", key: "n", width: 14 },
    { header: "Jml Refund", key: "nr", width: 11 },
    { header: "Skema", key: "rate", width: 16 },
  ];
  ws.getRow(1).font = { bold: true };
  for (const x of rows) {
    ws.addRow({
      name: x.name, email: x.email ?? "", bank: x.bank_name ?? "",
      acc: x.account_no ?? "(BELUM DIISI)", // teks (bukan angka) → nol di depan AMAN
      holder: x.bank_holder ?? "", total: x.total_idr, n: x.n_payment, nr: x.n_refund,
      rate: x.commission_type === "percent" ? `${x.commission_value}%` : `Rp ${x.commission_value}/bln`,
    });
  }
  ws.getColumn("acc").numFmt = "@";
  ws.getColumn("total").numFmt = "#,##0";
  const totalAll = rows.reduce((s, x) => s + x.total_idr, 0);
  const tr = ws.addRow({ holder: "TOTAL", total: totalAll });
  tr.font = { bold: true };
  const buf = await wb.xlsx.writeBuffer();
  return new NextResponse(Buffer.from(buf), {
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": `attachment; filename="komisi-reseller-${period}.xlsx"`,
      "Cache-Control": "no-store",
    },
  });
}
