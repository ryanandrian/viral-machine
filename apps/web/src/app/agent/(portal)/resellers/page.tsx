"use client";

import { useState, useEffect, useCallback } from "react";
import { Copy, Check, Link2, Download, UserCheck, UserX, Pause, Play } from "lucide-react";
import "../agent.css";

// [B21] F3 — kelola reseller oleh agen (SPEC §1c/5d/5f): tautan rekrut · antrean setujui/tolak ·
// rate Rp/% per reseller (auto-save saat blur/ganti, §3.6) · kinerja per periode · Export Excel.
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Rs = {
  id: string; name: string; email: string | null; phone: string | null; status: string;
  commission_type: string; commission_value: number; bank_name: string | null; bank_holder: string | null;
  bank_account_set: boolean; code: string | null; code_used: number; tenants: number;
  period_total_idr: number; period_n_payment: number;
};

const idr = (n: number | null | undefined) => `Rp ${Math.round(Number(n ?? 0)).toLocaleString("id-ID")}`;
function thisMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function AgentResellers() {
  const [rows, setRows] = useState<Rs[]>([]);
  const [bdOk, setBdOk] = useState(true);
  const [joinCode, setJoinCode] = useState<string | null>(null);
  const [period, setPeriod] = useState(thisMonth());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [rate, setRate] = useState<Record<string, { t: string; v: string }>>({});

  const load = useCallback(async (p: string) => {
    const j = await fetch(`/api/agent/resellers?period=${p}`).then((r) => r.json()).catch(() => null);
    if (j) {
      setRows(j.resellers ?? []); setJoinCode(j.join_code); setBdOk(j.breakdown_ok !== false);
      setRate(Object.fromEntries((j.resellers ?? []).map((r: Rs) => [r.id, { t: r.commission_type, v: String(r.commission_value) }])));
    }
  }, []);
  useEffect(() => { void load(period); }, [load, period]);

  async function act(body: Record<string, unknown>, okMsg?: string) {
    setBusy(true); setMsg(null);
    const res = await fetch("/api/agent/resellers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await res.json().catch(() => ({}));
    setBusy(false);
    if (!res.ok) { setMsg(j.error || "gagal"); return null; }
    if (j.warning) setMsg(j.warning); else if (okMsg) setMsg(okMsg);
    void load(period);
    return j;
  }
  async function saveRate(r: Rs) {
    const cur = rate[r.id]; if (!cur) return;
    if (cur.t === r.commission_type && Number(cur.v) === Number(r.commission_value)) return; // tak berubah
    await act({ action: "rate", reseller_id: r.id, commission_type: cur.t, commission_value: Number(cur.v) },
      "jatah reseller tersimpan (berlaku utk pembayaran berikutnya)");
  }
  const joinUrl = joinCode ? `https://mesinviral.com/agent/join/${joinCode}` : null;
  const pending = rows.filter((r) => r.status === "pending");
  const team = rows.filter((r) => r.status === "active" || r.status === "suspended");

  return (
    <div>
      <div className="ag-card">
        <p className="ag-sec"><Link2 size={13} style={{ verticalAlign: "-2px" }} /> <Bi id="Tautan rekrut reseller — bagikan ke calon penjual Anda; mereka mendaftar sendiri, Anda tinggal menyetujui" en="Reseller recruitment link — share it; candidates self-register, you approve" /></p>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          {joinUrl ? (<>
            <span className="ag-code" style={{ letterSpacing: 0, fontWeight: 500, fontSize: "var(--text-sm)" }}>{joinUrl}
              <button className="btn btn-outline btn-sm" onClick={async () => { await navigator.clipboard.writeText(joinUrl).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? <Check size={13} /> : <Copy size={13} />}</button>
            </span>
            <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => void act({ action: "join_code" }, "tautan BARU dibuat — tautan lama otomatis mati")}><Bi id="Ganti tautan" en="New link" /></button>
          </>) : (
            <button className="btn btn-default btn-sm" disabled={busy} onClick={() => void act({ action: "join_code" }, "tautan rekrut siap")}><Bi id="Buat tautan rekrut" en="Create recruitment link" /></button>
          )}
        </div>
      </div>

      {msg && <div className="ag-card" style={{ color: "var(--text-secondary)" }}>{msg}</div>}

      {pending.length > 0 && (
        <div className="ag-card" style={{ borderColor: "var(--warning)" }}>
          <p className="ag-sec"><Bi id={`Menunggu persetujuan Anda (${pending.length})`} en={`Awaiting your approval (${pending.length})`} /></p>
          <div className="ag-mini">
            {pending.map((r) => (<div className="row" key={r.id}>
              <span><strong>{r.name}</strong> <span style={{ color: "var(--text-muted)", fontSize: "var(--text-xs)" }}>{r.email}{r.phone ? ` · ${r.phone}` : ""} · {r.bank_name} a.n. {r.bank_holder}</span></span>
              <span style={{ display: "inline-flex", gap: "0.375rem" }}>
                <button className="btn btn-default btn-sm" disabled={busy} onClick={() => void act({ action: "approve", reseller_id: r.id }, "disetujui — kode dibuat & undangan portal terkirim")}><UserCheck size={13} /> <Bi id="Setujui" en="Approve" /></button>
                <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => window.confirm(`Tolak ${r.name}?`) && void act({ action: "reject", reseller_id: r.id }, "ditolak")}><UserX size={13} /> <Bi id="Tolak" en="Reject" /></button>
              </span>
            </div>))}
          </div>
        </div>
      )}

      <div className="ag-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.625rem" }}>
          <p className="ag-sec" style={{ margin: 0 }}><Bi id={`Tim reseller (${team.length}) — kinerja periode`} en={`Reseller team (${team.length}) — period performance`} /></p>
          <span style={{ display: "inline-flex", gap: "0.5rem", alignItems: "center" }}>
            <input className="input" type="month" style={{ width: "10.5rem", height: "2rem" }} value={period} onChange={(e) => setPeriod(e.target.value)} />
            <a className="btn btn-outline btn-sm" href={`/api/agent/resellers/export?period=${period}`}><Download size={13} /> <Bi id="Unduh Excel transfer" en="Download transfer Excel" /></a>
          </span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead><tr><th>Reseller</th><th><Bi id="Kode" en="Code" /></th><th><Bi id="Jatah komisi (Anda yang atur)" en="Their cut (you set it)" /></th><th>Tenant</th><th><Bi id="Komisi periode" en="Period commission" /></th><th>Status</th><th></th></tr></thead>
            <tbody>
              {team.length === 0 && <tr><td colSpan={7} style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-muted)" }}><Bi id="Belum ada reseller — bagikan tautan rekrut di atas." en="No resellers yet — share the recruitment link above." /></td></tr>}
              {team.map((r) => (<tr key={r.id}>
                <td><strong>{r.name}</strong><div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{r.email}{r.bank_account_set ? "" : " · ⚠ rekening belum ada"}</div></td>
                <td><span className="badge badge-outline">{r.code ?? "—"}</span>{r.code_used > 0 && <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>dipakai {r.code_used}×</div>}</td>
                <td>
                  <span style={{ display: "inline-flex", gap: "0.25rem" }}>
                    <select className="input" style={{ height: "1.875rem", fontSize: "var(--text-xs)", width: "6.5rem" }} value={rate[r.id]?.t ?? r.commission_type}
                      onChange={(e) => { setRate({ ...rate, [r.id]: { t: e.target.value, v: rate[r.id]?.v ?? String(r.commission_value) } }); }}>
                      <option value="flat_idr">Rp/bln</option>
                      <option value="percent">%</option>
                    </select>
                    <input className="input" type="number" min={0} style={{ height: "1.875rem", width: "6rem", fontSize: "var(--text-xs)" }}
                      value={rate[r.id]?.v ?? String(r.commission_value)}
                      onChange={(e) => setRate({ ...rate, [r.id]: { t: rate[r.id]?.t ?? r.commission_type, v: e.target.value } })}
                      onBlur={() => void saveRate(r)} />
                  </span>
                </td>
                <td className="ag-num">{r.tenants}</td>
                <td className="ag-num">{bdOk ? idr(r.period_total_idr) : "—"}<div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{bdOk ? `${r.period_n_payment}× bayar` : <Bi id="hitungan tak tersedia — muat ulang" en="totals unavailable — reload" />}</div></td>
                <td><span className={`badge ${r.status === "active" ? "badge-success" : "badge-error"}`}>{r.status}</span></td>
                <td style={{ whiteSpace: "nowrap" }}>
                  <button className="btn btn-outline btn-sm" disabled={busy} onClick={() => void act({ action: "toggle", reseller_id: r.id })} title={r.status === "active" ? "Suspend (kode berhenti terima pendaftaran baru)" : "Aktifkan kembali"}>
                    {r.status === "active" ? <Pause size={13} /> : <Play size={13} />}
                  </button>
                  {r.status === "active" && <button className="btn btn-outline btn-sm" style={{ marginLeft: "0.25rem" }} disabled={busy} onClick={() => void act({ action: "approve", reseller_id: r.id }, "undangan portal dikirim ulang")}><Bi id="Kirim ulang undangan" en="Resend invite" /></button>}
                </td>
              </tr>))}
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginTop: "0.625rem" }}>
          <Bi id="Excel berisi rekening tiap reseller + total komisi periode — siap untuk transfer massal bulanan Anda. Pembayaran ke reseller adalah kewajiban Anda sebagai agen (sesuai kontrak)."
             en="The Excel contains each reseller's bank details + period totals — ready for your monthly bulk transfer. Paying resellers is your obligation as the agent (per contract)." />
        </p>
      </div>
    </div>
  );
}
