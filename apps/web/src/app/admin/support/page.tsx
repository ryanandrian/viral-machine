"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus } from "lucide-react";
import "./support.css";

// E4 Admin Support — port dari design-source/Admin Support.html (Hybrid). /admin/support.
// Inbox 3-kolom (tiket/percakapan/konteks). Mock deterministik; nol wiring Supabase. Prefix sup-.
// xendit→midtrans (keputusan final).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type Ticket = { av: string; c: string; name: string; plan: string; subj: string; prev: string; time: string; tags: string[] };
const TICKETS: Ticket[] = [
  { av: "RP", c: "#1d4ed8", name: "Riko Pratama", plan: "Pro", subj: "Pertanyaan tentang billing", prev: "Halo, saya mau tanya soal invoice bulan ini yang...", time: "12m", tags: ["billing", "midtrans"] },
  { av: "BP", c: "#9f1239", name: "Bagus Pratomo", plan: "Trial", subj: "Cara connect channel kedua", prev: "Saya sudah connect 1 channel, gimana cara...", time: "1j", tags: ["onboarding"] },
  { av: "MP", c: "#047857", name: "Maya Putri", plan: "Pro", subj: "API key OpenAI gagal test", prev: "Pas saya test koneksi muncul error 401...", time: "2j", tags: ["api-keys", "urgent"] },
  { av: "AS", c: "#7c3aed", name: "Andi Saputra", plan: "Scale", subj: "Request refund", prev: "Akun saya kena suspend tapi saya sudah bayar...", time: "3j", tags: ["billing", "refund"] },
];
const CONVO: ["them" | "me", string, string][] = [
  ["them", "Halo, saya mau tanya soal invoice bulan ini. Kenapa jumlahnya Rp 548K, bukan Rp 349K seperti biasa?", "12:02"],
  ["me", "Halo Riko! Selisih Rp 199K itu dari add-on Voice Pack yang aktif bulan ini. Mau saya kirim rincian invoice-nya?", "12:05"],
  ["them", "Oh begitu, iya boleh tolong dikirim. Terima kasih!", "12:06"],
];
const QR = ["Terima kasih sudah menghubungi!", "Sedang kami cek, mohon tunggu.", "Sudah kami selesaikan ✅", "Bisa kirim screenshot?"];

export default function AdminSupportPage() {
  const [sel, setSel] = useState(0);
  const [reply, setReply] = useState("");
  const [filter, setFilter] = useState("open");
  const t = TICKETS[sel];
  return (
    <div className="sup-layout">
      <div className="sup-inbox">
        <div className="sup-inbox-head">
          <h1>Support</h1>
          <div className="segmented">
            <button aria-selected={filter === "open"} onClick={() => setFilter("open")}>Open <span style={{ opacity: 0.6 }}>4</span></button>
            <button aria-selected={filter === "pending"} onClick={() => setFilter("pending")}>Pending</button>
            <button aria-selected={filter === "resolved"} onClick={() => setFilter("resolved")}>Resolved</button>
          </div>
        </div>
        <div className="sup-inbox-list">
          {TICKETS.map((tk, i) => (
            <div className={`sup-ticket${sel === i ? " active" : ""}`} key={tk.name} onClick={() => setSel(i)}>
              <div className="t-top"><span className="sup-av" style={{ background: tk.c }}>{tk.av}</span><span className="t-name">{tk.name}</span><span className="t-time">{tk.time}</span></div>
              <div className="t-subj">{tk.subj}</div><div className="t-prev">{tk.prev}</div>
              <div className="t-tags">{tk.tags.map((tag) => <span key={tag} className={`badge ${tag === "urgent" ? "badge-error" : "badge-default"}`} style={{ fontSize: "0.5625rem" }}>{tag}</span>)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="sup-convo">
        <div className="sup-convo-head">
          <span className="sup-av" style={{ width: 34, height: 34, fontSize: "var(--text-xs)", background: t.c }}>{t.av}</span>
          <div style={{ flex: 1 }}><div style={{ fontWeight: 600, fontSize: "var(--text-sm)" }}>{t.subj}</div><div className="muted" style={{ fontSize: "var(--text-xs)" }}>{t.name} · {t.plan}</div></div>
          <span className="badge badge-warning"><span className="dot" />Open</span>
          <button className="btn btn-secondary btn-sm"><Bi id="Tandai selesai" en="Resolve" /></button>
        </div>
        <div className="sup-convo-body">
          {CONVO.map(([who, txt, time], i) => (
            <div className={`sup-msg ${who}`} key={i}><div className="bubble">{txt}</div><div className="meta">{who === "me" ? "Admin" : t.name} · {time}</div></div>
          ))}
        </div>
        <div className="sup-convo-foot">
          <div className="sup-qr-row">{QR.map((q) => <span key={q} className="sup-qr" onClick={() => setReply(q)}>{q}</span>)}</div>
          <div className="sup-reply-box"><input className="input" placeholder="Tulis balasan…" style={{ flex: 1 }} value={reply} onChange={(e) => setReply(e.target.value)} /><button className="btn btn-default"><ArrowRight size={15} /></button></div>
        </div>
      </div>

      <aside className="sup-ctx">
        <h3><Bi id="Konteks tenant" en="Tenant context" /></h3>
        <div className="kv"><span className="k">Plan</span><span className="v"><span className="badge badge-brand">{t.plan}</span></span></div>
        <div className="kv"><span className="k">MRR</span><span className="v">Rp 548K</span></div>
        <div className="kv"><span className="k">Channels</span><span className="v">3</span></div>
        <div className="kv"><span className="k"><Bi id="Bergabung" en="Joined" /></span><span className="v">12 Jan 2026</span></div>
        <hr className="hr" style={{ margin: "1rem 0" }} />
        <h3><Bi id="Run terbaru" en="Recent runs" /></h3>
        <div style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: 1.9 }}>
          <div>✅ Kapal Hilang Bermuda · 2j</div>
          <div>✅ Suara Palung Mariana · 5j</div>
          <div style={{ color: "var(--error)" }}>❌ Pulau Hantu · 6j</div>
        </div>
        <hr className="hr" style={{ margin: "1rem 0" }} />
        <h3>Tags</h3>
        <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}><span className="badge badge-default">billing</span><span className="badge badge-default">midtrans</span><button className="btn btn-ghost btn-icon btn-sm"><Plus size={13} /></button></div>
        <Link href="/admin/tenants" className="btn btn-secondary btn-sm" style={{ width: "100%", marginTop: "1.25rem" }}><Bi id="Buka profil tenant" en="Open tenant profile" /> <ArrowRight size={14} /></Link>
      </aside>
    </div>
  );
}
