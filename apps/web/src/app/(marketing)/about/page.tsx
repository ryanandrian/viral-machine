"use client";

import { useState, useEffect } from "react";
import { Eye, Sparkles, Mail, Globe, CheckCircle } from "lucide-react";
import "./about.css";

// A6 About/Contact/Status — /about, 3 tab. Keputusan owner 2026-07-04:
// - Kontak: WhatsApp placeholder DIBUANG; email+website dari company_profile (via /api/public/company,
//   admin-editable — nol hardcode); form kirim dari SERVER (/api/contact → company_profile.email).
// - Status: kondisi NYATA dari worker_heartbeats (/api/public/status) — angka uptime & bar 30-hari
//   palsu DIBUANG (belum ada data historis; jujur > dekorasi).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

const TABS: [string, string, string][] = [["about", "Tentang", "About"], ["contact", "Kontak", "Contact"], ["status", "Status", "Status"]];

// Nama layanan ramah-awam (dwibahasa) utk worker_heartbeats — key tak dikenal → tampil apa adanya.
const SVC_LABEL: Record<string, [string, string]> = {
  producer: ["Produksi video", "Video production"],
  publisher: ["Publikasi YouTube", "YouTube publishing"],
  self_learning: ["Self-learning engine", "Self-learning engine"],
  trend_refresher: ["Trend radar", "Trend radar"],
  billing_renewal: ["Billing & langganan", "Billing & subscriptions"],
  email_outbox: ["Notifikasi email", "Email notifications"],
  janitor: ["Pemeliharaan sistem", "System maintenance"],
  niche_sweeper: ["Layanan niche", "Niche services"],
  payment_reconciler: ["Rekonsiliasi pembayaran", "Payment reconciliation"],
};

type Svc = { key: string; up: boolean };

export default function AboutPage() {
  const [tab, setTab] = useState("about");
  const [cf, setCf] = useState({ name: "", email: "", msg: "" });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [sendErr, setSendErr] = useState<string | null>(null);
  const [company, setCompany] = useState<{ website: string | null; email: string | null }>({ website: null, email: null });
  const [status, setStatus] = useState<{ services: Svc[]; all_ok: boolean } | null>(null);
  const [statusErr, setStatusErr] = useState(false);

  useEffect(() => {
    fetch("/api/public/company").then((r) => r.json()).then(setCompany).catch(() => {});
  }, []);
  useEffect(() => {
    if (tab !== "status") return;
    setStatusErr(false);
    fetch("/api/public/status").then((r) => { if (!r.ok) throw new Error(); return r.json(); }).then(setStatus).catch(() => setStatusErr(true));
  }, [tab]);

  async function sendContact() {
    setSending(true); setSendErr(null);
    const r = await fetch("/api/contact", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cf) }).catch(() => null);
    setSending(false);
    if (r?.ok) { setSent(true); }
    else setSendErr("fail");
  }

  const website = company.website?.replace(/^https?:\/\//, "") ?? null;

  return (
    <div className="mk-container">
      <div className="ab-tabs">{TABS.map(([v, id, en]) => <button key={v} className={`ab-tab${tab === v ? " sel" : ""}`} onClick={() => { setTab(v); window.scrollTo(0, 0); }}><Bi id={id} en={en} /></button>)}</div>

      {tab === "about" && <>
        <div className="ab-hero">
          <span className="mk-kicker"><Bi id="Tentang kami" en="About us" /></span>
          <h1><Bi id="Memberdayakan creator Indonesia untuk scale." en="Empowering Indonesian creators to scale." /></h1>
          <p className="mk-lead mk-center"><Bi id="MesinViral lahir dari satu keyakinan: produksi konten berkualitas tidak harus memakan seluruh waktumu. Kami membangun mesin yang belajar, agar kamu bisa fokus pada strategi." en="MesinViral was born from one belief: quality content production shouldn't consume all your time. We build a machine that learns, so you can focus on strategy." /></p>
        </div>
        <div className="ab-values">
          <div className="ab-value"><span className="ic"><Eye size={22} /></span><h3><Bi id="Transparan" en="Transparent" /></h3><p><Bi id="BYOK & biaya real-time. Tidak ada markup tersembunyi." en="BYOK & real-time cost. No hidden markup." /></p></div>
          <div className="ab-value"><span className="ic"><Sparkles size={22} /></span><h3><Bi id="Selalu belajar" en="Always learning" /></h3><p><Bi id="Mesin yang beradaptasi dari data channelmu sendiri." en="A machine that adapts from your own channel data." /></p></div>
          <div className="ab-value"><span className="ic">🇮🇩</span><h3><Bi id="Lokal" en="Local-first" /></h3><p><Bi id="Dibangun untuk creator Indonesia, dengan dukungan lokal." en="Built for Indonesian creators, with local support." /></p></div>
        </div>
      </>}

      {tab === "contact" && <>
        <div className="ab-hero"><h1 style={{ fontSize: "var(--text-4xl)" }}><Bi id="Hubungi kami" en="Contact us" /></h1></div>
        <div className="ab-contact-grid">
          <div>
            <div className="ab-contact-item"><span className="ic"><Mail size={18} /></span><div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}>Email</div><div className="muted" style={{ fontSize: "var(--text-sm)" }}>{company.email ?? "—"}</div></div></div>
            <div className="ab-contact-item"><span className="ic"><Globe size={18} /></span><div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}>Website</div><div className="muted" style={{ fontSize: "var(--text-sm)" }}>{website ? <a href={`https://${website}`} target="_blank" rel="noopener" style={{ color: "inherit" }}>{website}</a> : "—"}</div></div></div>
          </div>
          <div className="card card-pad">
            {sent ? (
              <div style={{ textAlign: "center", padding: "1.5rem 0.5rem", display: "grid", gap: "0.5rem", justifyItems: "center" }}>
                <CheckCircle size={28} style={{ color: "var(--success)" }} />
                <div style={{ fontWeight: 600 }}><Bi id="Pesan terkirim!" en="Message sent!" /></div>
                <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}><Bi id="Terima kasih — kami akan membalas ke email Anda." en="Thank you — we'll reply to your email." /></p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}><div><label className="label"><Bi id="Nama" en="Name" /></label><input className="input" value={cf.name} onChange={(e) => setCf({ ...cf, name: e.target.value })} /></div><div><label className="label">Email</label><input className="input" value={cf.email} onChange={(e) => setCf({ ...cf, email: e.target.value })} /></div></div>
                <div><label className="label"><Bi id="Pesan" en="Message" /></label><textarea className="textarea" rows={4} value={cf.msg} onChange={(e) => setCf({ ...cf, msg: e.target.value })} /></div>
                <button className="btn btn-default" disabled={!cf.msg.trim() || sending} onClick={sendContact}>{sending ? <Bi id="Mengirim…" en="Sending…" /> : <Bi id="Kirim pesan" en="Send message" />}</button>
                {sendErr && <div className="muted" style={{ fontSize: "var(--text-xs)", color: "var(--danger)" }}><Bi id="Gagal mengirim — coba lagi, atau email kami langsung." en="Failed to send — try again, or email us directly." /></div>}
              </div>
            )}
          </div>
        </div>
      </>}

      {tab === "status" && <>
        <div className="ab-hero"><h1 style={{ fontSize: "var(--text-4xl)" }}><Bi id="Status Sistem" en="System Status" /></h1></div>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          {statusErr ? (
            <div className="ab-status-banner"><span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--warning)" }} /><span style={{ fontWeight: 600, color: "var(--text-primary)" }}><Bi id="Status tidak dapat dimuat saat ini" en="Status is unavailable right now" /></span></div>
          ) : !status ? (
            <div className="mk-center muted" style={{ padding: "2rem" }}><Bi id="Memuat status…" en="Loading status…" /></div>
          ) : (<>
            <div className="ab-status-banner"><span style={{ width: 10, height: 10, borderRadius: "50%", background: status.all_ok ? "var(--success)" : "var(--warning)" }} /><span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{status.all_ok ? <Bi id="Semua sistem beroperasi normal" en="All systems operational" /> : <Bi id="Sebagian layanan sedang terganggu" en="Some services are degraded" />}</span><span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-sm)" }}><Bi id="kondisi langsung" en="live status" /></span></div>
            <div className="card card-pad">{status.services.map((s) => {
              const [idL, enL] = SVC_LABEL[s.key] ?? [s.key, s.key];
              return (
                <div className="ab-status-row" key={s.key}><div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}><Bi id={idL} en={enL} /></div></div>
                  <span className={`badge ${s.up ? "badge-success" : "badge-warning"}`}><span className="dot" />{s.up ? "Normal" : <Bi id="Gangguan" en="Degraded" />}</span></div>
              );
            })}</div>
          </>)}
        </div>
      </>}

      <div style={{ height: "4rem" }} />
    </div>
  );
}
