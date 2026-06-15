"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import "./support.css";

// E4 Admin Support (Phase 10.9) — DATA NYATA via /api/admin/support (service_role). Inbox 3-kolom.
// Admin bukan tenant → RLS realtime tak berlaku; admin POLL detail tiap 5s untuk balasan tenant. Prefix sup-.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Ticket = { id: string; tenant_id: string; tenant_handle: string; subject: string; status: string; preview: string; messages: number; updated_at: string };
type Msg = { id: string; sender: string; body: string; created_at: string };
type Detail = { ticket: Ticket; messages: Msg[]; tenant: { display_handle: string; plan_type: string; subscription_status: string; created_at: string } | null; channels: number };

const QR = ["Terima kasih sudah menghubungi!", "Sedang kami cek, mohon tunggu.", "Sudah kami selesaikan ✅", "Bisa kirim screenshot?"];
const AVC = ["#1d4ed8", "#9f1239", "#047857", "#7c3aed", "#b45309"];
const ini = (s: string) => (s || "?").slice(0, 2).toUpperCase();

export default function AdminSupportPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [counts, setCounts] = useState<{ open: number; pending: number; resolved: number }>({ open: 0, pending: 0, resolved: 0 });
  const [filter, setFilter] = useState("open");
  const [sel, setSel] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  const loadList = useCallback(async () => {
    const r = await fetch("/api/admin/support");
    if (r.ok) { const j = await r.json(); setTickets(j.tickets); setCounts(j.counts); }
  }, []);
  useEffect(() => { loadList(); }, [loadList]);

  const loadDetail = useCallback(async (id: string) => {
    const r = await fetch(`/api/admin/support/${id}`);
    if (r.ok) setDetail(await r.json());
  }, []);
  useEffect(() => {
    if (!sel) { setDetail(null); return; }
    loadDetail(sel);
    const poll = setInterval(() => loadDetail(sel), 5000);  // admin poll (RLS realtime = tenant-only)
    return () => clearInterval(poll);
  }, [sel, loadDetail]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [detail?.messages.length]);

  const view = tickets.filter((t) => t.status === filter);

  async function sendReply() {
    if (!reply.trim() || !sel) return;
    setBusy(true);
    const r = await fetch(`/api/admin/support/${sel}/reply`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ body: reply.trim() }) });
    setBusy(false);
    if (r.ok) { setReply(""); await loadDetail(sel); await loadList(); }
  }
  async function setStatus(status: string) {
    if (!sel) return;
    setBusy(true);
    await fetch(`/api/admin/support/${sel}/status`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    setBusy(false); await loadDetail(sel); await loadList();
  }

  const idx = view.findIndex((t) => t.id === sel);

  return (
    <div className="sup-layout">
      <div className="sup-inbox">
        <div className="sup-inbox-head">
          <h1>Support</h1>
          <div className="segmented">
            <button aria-selected={filter === "open"} onClick={() => setFilter("open")}>Open <span style={{ opacity: 0.6 }}>{counts.open}</span></button>
            <button aria-selected={filter === "pending"} onClick={() => setFilter("pending")}>Pending <span style={{ opacity: 0.6 }}>{counts.pending}</span></button>
            <button aria-selected={filter === "resolved"} onClick={() => setFilter("resolved")}>Resolved <span style={{ opacity: 0.6 }}>{counts.resolved}</span></button>
          </div>
        </div>
        <div className="sup-inbox-list">
          {view.length === 0 && <div className="muted" style={{ padding: "1.25rem", textAlign: "center", fontSize: "var(--text-sm)" }}>Tidak ada tiket {filter}.</div>}
          {view.map((tk, i) => (
            <div className={`sup-ticket${sel === tk.id ? " active" : ""}`} key={tk.id} onClick={() => setSel(tk.id)}>
              <div className="t-top"><span className="sup-av" style={{ background: AVC[i % AVC.length] }}>{ini(tk.tenant_handle)}</span><span className="t-name">{tk.tenant_handle}</span><span className="t-time">{new Date(tk.updated_at).toLocaleDateString("id-ID", { day: "numeric", month: "short" })}</span></div>
              <div className="t-subj">{tk.subject}</div><div className="t-prev">{tk.preview}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="sup-convo">
        {!detail ? <div className="muted" style={{ padding: "2rem", textAlign: "center" }}>Pilih tiket.</div> : (<>
          <div className="sup-convo-head">
            <span className="sup-av" style={{ width: 34, height: 34, fontSize: "var(--text-xs)", background: AVC[Math.max(0, idx) % AVC.length] }}>{ini(detail.ticket.tenant_handle)}</span>
            <div style={{ flex: 1 }}><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{detail.ticket.subject}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{detail.ticket.tenant_handle} · {detail.tenant?.plan_type ?? "—"}</div></div>
            <span className={`badge ${detail.ticket.status === "open" ? "badge-info" : detail.ticket.status === "pending" ? "badge-warning" : "badge-success"}`}><span className="dot" />{detail.ticket.status}</span>
            {detail.ticket.status !== "resolved"
              ? <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setStatus("resolved")}><Bi id="Tandai selesai" en="Resolve" /></button>
              : <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setStatus("open")}><Bi id="Buka lagi" en="Reopen" /></button>}
          </div>
          <div className="sup-convo-body">
            {detail.messages.map((m) => (
              <div className={`sup-msg ${m.sender === "admin" ? "me" : "them"}`} key={m.id}><div className="bubble">{m.body}</div><div className="meta">{m.sender === "admin" ? "Admin" : detail.ticket.tenant_handle} · {new Date(m.created_at).toLocaleString("id-ID", { hour: "2-digit", minute: "2-digit" })}</div></div>
            ))}
            <div ref={endRef} />
          </div>
          {detail.ticket.status !== "resolved" && (
            <div className="sup-convo-foot">
              <div className="sup-qr-row">{QR.map((q) => <span key={q} className="sup-qr" onClick={() => setReply(q)}>{q}</span>)}</div>
              <form className="sup-reply-box" onSubmit={(e) => { e.preventDefault(); if (!busy) sendReply(); }}><input className="input" placeholder="Tulis balasan…" style={{ flex: 1 }} value={reply} onChange={(e) => setReply(e.target.value)} /><button className="btn btn-default" type="submit" disabled={busy || !reply.trim()}><ArrowRight size={15} /></button></form>
            </div>
          )}
        </>)}
      </div>

      <aside className="sup-ctx">
        <h3><Bi id="Konteks tenant" en="Tenant context" /></h3>
        {detail?.tenant ? (<>
          <div className="kv"><span className="k">Handle</span><span className="v">{detail.tenant.display_handle}</span></div>
          <div className="kv"><span className="k">Plan</span><span className="v"><span className="badge badge-brand">{detail.tenant.plan_type}</span></span></div>
          <div className="kv"><span className="k">Status</span><span className="v">{detail.tenant.subscription_status}</span></div>
          <div className="kv"><span className="k">Channels</span><span className="v">{detail.channels}</span></div>
          <div className="kv"><span className="k"><Bi id="Bergabung" en="Joined" /></span><span className="v">{new Date(detail.tenant.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" })}</span></div>
          <Link href="/admin/tenants" className="btn btn-secondary btn-sm" style={{ width: "100%", marginTop: "1.25rem" }}><Bi id="Buka profil tenant" en="Open tenant profile" /> <ArrowRight size={14} /></Link>
        </>) : <div className="muted" style={{ fontSize: "var(--text-xs)" }}>Pilih tiket untuk melihat konteks.</div>}
      </aside>
    </div>
  );
}
