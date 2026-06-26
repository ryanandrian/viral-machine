"use client";

import { useState } from "react";
import { Eye, Sparkles, Mail, MessageCircle, Tv } from "lucide-react";
import "./about.css";

// A6 About/Contact/Status/Legal — port dari design-source/About.html (Hybrid). /about. 4 tab.

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

// Tab "Privacy" lama dihapus → kini halaman tersendiri /privacy & /terms (patuh Google/YouTube).
const TABS: [string, string, string][] = [["about", "Tentang", "About"], ["contact", "Kontak", "Contact"], ["status", "Status", "Status"]];
const SVC: [string, string, number][] = [["API Produksi", "Production API", 1], ["Pipeline Worker", "Pipeline Worker", 1], ["Dashboard", "Dashboard", 1], ["YouTube Upload", "YouTube Upload", 2], ["Database", "Database", 1], ["Notifikasi", "Notifications", 1]];

export default function AboutPage() {
  const [tab, setTab] = useState("about");
  const [cf, setCf] = useState({ name: "", email: "", msg: "" });
  function sendContact() {
    const subject = encodeURIComponent(`[Kontak] ${cf.name || "Pengunjung"}`);
    const body = encodeURIComponent(`Nama: ${cf.name}\nEmail: ${cf.email}\n\n${cf.msg}`);
    window.location.href = `mailto:mesinviral@lumite.biz.id?subject=${subject}&body=${body}`;
  }
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
            <div className="ab-contact-item"><span className="ic"><Mail size={18} /></span><div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}>Email</div><div className="muted" style={{ fontSize: "var(--text-sm)" }}>mesinviral@lumite.biz.id</div></div></div>
            <div className="ab-contact-item"><span className="ic"><MessageCircle size={18} /></span><div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}>WhatsApp Support</div><div className="muted" style={{ fontSize: "var(--text-sm)" }}>+62 811-2345-6789</div></div></div>
            <div className="ab-contact-item"><span className="ic"><Tv size={18} /></span><div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}><Bi id="Alamat" en="Address" /></div><div className="muted" style={{ fontSize: "var(--text-sm)" }}>Jakarta Selatan, Indonesia</div></div></div>
          </div>
          <div className="card card-pad">
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}><div><label className="label"><Bi id="Nama" en="Name" /></label><input className="input" value={cf.name} onChange={(e) => setCf({ ...cf, name: e.target.value })} /></div><div><label className="label">Email</label><input className="input" value={cf.email} onChange={(e) => setCf({ ...cf, email: e.target.value })} /></div></div>
              <div><label className="label"><Bi id="Pesan" en="Message" /></label><textarea className="textarea" rows={4} value={cf.msg} onChange={(e) => setCf({ ...cf, msg: e.target.value })} /></div>
              <button className="btn btn-default" disabled={!cf.msg.trim()} onClick={sendContact}><Bi id="Kirim pesan" en="Send message" /></button>
            </div>
          </div>
        </div>
      </>}

      {tab === "status" && <>
        <div className="ab-hero"><h1 style={{ fontSize: "var(--text-4xl)" }}><Bi id="Status Sistem" en="System Status" /></h1></div>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <div className="ab-status-banner"><span style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--success)" }} /><span style={{ fontWeight: 600, color: "var(--text-primary)" }}><Bi id="Semua sistem beroperasi normal" en="All systems operational" /></span><span className="muted" style={{ marginLeft: "auto", fontSize: "var(--text-sm)" }}>99.98% uptime · 90d</span></div>
          <div className="card card-pad">{SVC.map(([id, en, st]) => (
            <div className="ab-status-row" key={en}><div><div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}><Bi id={id} en={en} /></div></div>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}><div className="ab-uptime">{Array.from({ length: 30 }).map((_, i) => <span key={i} className={st === 2 && i > 26 ? "deg" : ""} />)}</div><span className={`badge ${st === 1 ? "badge-success" : "badge-warning"}`}><span className="dot" />{st === 1 ? "Normal" : "Degraded"}</span></div></div>
          ))}</div>
        </div>
      </>}

      <div style={{ height: "4rem" }} />
    </div>
  );
}
