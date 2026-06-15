"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Plus, X, Send, ArrowLeft } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

// Support sisi TENANT (Phase 10.9) — buat/lihat/balas tiket SENDIRI (anon + RLS auth.uid()).
// Realtime support_messages (live chat dgn admin). Sumber tiket untuk admin E4.

type Ticket = { id: string; subject: string; status: string; updated_at: string };
type Msg = { id: string; sender: string; body: string; created_at: string };

export default function TenantSupportPage() {
  const supabase = createClient();
  const [uid, setUid] = useState<string>("");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [open, setOpen] = useState<Ticket | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [reply, setReply] = useState("");
  const [newT, setNewT] = useState<{ subject: string; body: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  const loadTickets = useCallback(async () => {
    const { data } = await supabase.from("support_tickets").select("id, subject, status, updated_at").order("updated_at", { ascending: false });
    setTickets(data ?? []);
  }, [supabase]);
  useEffect(() => { supabase.auth.getUser().then(({ data }) => setUid(data.user?.id ?? "")); loadTickets(); }, [supabase, loadTickets]);

  // open ticket → load messages + realtime subscribe
  useEffect(() => {
    if (!open) { setMsgs([]); return; }
    let active = true;
    supabase.from("support_messages").select("*").eq("ticket_id", open.id).order("created_at").then(({ data }) => { if (active) setMsgs(data ?? []); });
    const ch = supabase.channel(`ticket-${open.id}`).on("postgres_changes", { event: "INSERT", schema: "public", table: "support_messages", filter: `ticket_id=eq.${open.id}` }, (p) => {
      setMsgs((m) => m.some((x) => x.id === (p.new as Msg).id) ? m : [...m, p.new as Msg]);
    }).subscribe();
    return () => { active = false; supabase.removeChannel(ch); };
  }, [open, supabase]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function createTicket() {
    if (!newT?.subject.trim() || !newT.body.trim() || !uid) return;
    setBusy(true);
    const { data: t, error } = await supabase.from("support_tickets").insert({ tenant_id: uid, subject: newT.subject.trim() }).select("id, subject, status, updated_at").single();
    if (!error && t) {
      await supabase.from("support_messages").insert({ ticket_id: t.id, sender: "tenant", body: newT.body.trim() });
      setNewT(null); await loadTickets(); setOpen(t);
    }
    setBusy(false);
  }
  async function sendReply() {
    if (!reply.trim() || !open) return;
    setBusy(true);
    await supabase.from("support_messages").insert({ ticket_id: open.id, sender: "tenant", body: reply.trim() });
    setReply(""); setBusy(false);
  }

  const stColor = (s: string) => s === "open" ? "badge-info" : s === "pending" ? "badge-warning" : "badge-success";

  return (
    <div style={{ maxWidth: 760 }}>
      {!open ? (<>
        <div style={{ display: "flex", alignItems: "center", marginBottom: "1.25rem" }}>
          <div><h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 700 }}>Bantuan</h1><div className="muted" style={{ fontSize: "var(--text-sm)" }}>Tiket dukungan Anda</div></div>
          <button className="btn btn-primary btn-sm" style={{ marginLeft: "auto" }} onClick={() => setNewT({ subject: "", body: "" })}><Plus size={14} /> Tiket baru</button>
        </div>
        <div className="card"><div style={{ padding: "0.5rem" }}>
          {tickets.length === 0 && <div className="muted" style={{ padding: "1.25rem", textAlign: "center" }}>Belum ada tiket. Buat tiket baru untuk menghubungi tim.</div>}
          {tickets.map((t) => (
            <div key={t.id} onClick={() => setOpen(t)} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.75rem", borderRadius: 8, cursor: "pointer" }} className="hoverable">
              <div style={{ flex: 1 }}><div style={{ fontWeight: 500 }}>{t.subject}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{new Date(t.updated_at).toLocaleString("id-ID")}</div></div>
              <span className={`badge ${stColor(t.status)}`}>{t.status}</span>
            </div>
          ))}
        </div></div>
      </>) : (<>
        <button className="btn btn-ghost btn-sm" style={{ marginBottom: "0.75rem" }} onClick={() => setOpen(null)}><ArrowLeft size={14} /> Kembali</button>
        <div className="card" style={{ display: "flex", flexDirection: "column", height: "60vh" }}>
          <div style={{ padding: "1rem", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center" }}>
            <strong>{open.subject}</strong><span className={`badge ${stColor(open.status)}`} style={{ marginLeft: "auto" }}>{open.status}</span>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.625rem" }}>
            {msgs.map((m) => (
              <div key={m.id} style={{ alignSelf: m.sender === "tenant" ? "flex-end" : "flex-start", maxWidth: "75%", background: m.sender === "tenant" ? "var(--brand-soft, #1e3a8a)" : "var(--surface-2, #1f2937)", color: "var(--text-primary)", padding: "0.5rem 0.75rem", borderRadius: 10, fontSize: "var(--text-sm)" }}>
                <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", marginBottom: 2 }}>{m.sender === "tenant" ? "Anda" : "Admin"}</div>{m.body}
              </div>
            ))}
            <div ref={endRef} />
          </div>
          {open.status !== "resolved" && (
            <form onSubmit={(e) => { e.preventDefault(); if (!busy) sendReply(); }} style={{ padding: "0.75rem", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "0.5rem" }}>
              <input className="input" placeholder="Tulis balasan…" value={reply} onChange={(e) => setReply(e.target.value)} style={{ flex: 1 }} />
              <button className="btn btn-primary btn-icon" type="submit" disabled={busy || !reply.trim()}><Send size={16} /></button>
            </form>
          )}
        </div>
      </>)}

      {newT && (<>
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 60 }} onClick={() => setNewT(null)} />
        <div className="card" style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: "min(480px,92vw)", zIndex: 61, padding: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}><strong>Tiket baru</strong><button className="btn btn-ghost btn-icon btn-sm" style={{ marginLeft: "auto" }} onClick={() => setNewT(null)}><X size={16} /></button></div>
          <div style={{ display: "grid", gap: "0.625rem" }}>
            <input className="input" placeholder="Subjek" value={newT.subject} onChange={(e) => setNewT({ ...newT, subject: e.target.value })} />
            <textarea className="input" placeholder="Jelaskan masalah Anda" rows={5} value={newT.body} onChange={(e) => setNewT({ ...newT, body: e.target.value })} />
            <button className="btn btn-primary btn-sm" style={{ justifySelf: "end" }} disabled={busy || !newT.subject.trim() || !newT.body.trim()} onClick={createTicket}>Kirim tiket</button>
          </div>
        </div>
      </>)}
    </div>
  );
}
