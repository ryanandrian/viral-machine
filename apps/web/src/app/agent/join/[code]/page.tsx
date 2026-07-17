"use client";

import { useState, useEffect } from "react";
import { use } from "react";
import "../../../auth/auth.css";

// [B21] F3 — form PUBLIK pendaftaran-mandiri reseller via tautan agen (SPEC 5f).
// Kirim → status 'pending' → agen menyetujui → email undangan portal. Dwibahasa.
function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

export default function ResellerJoinPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const [company, setCompany] = useState<string | null>(null);
  const [invalid, setInvalid] = useState(false);
  const [f, setF] = useState({ name: "", email: "", phone: "", bank_name: "", account_no: "", holder: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    fetch(`/api/partner/reseller-register?code=${encodeURIComponent(code.toUpperCase())}`)
      .then((r) => r.json()).then((j) => (j.valid ? setCompany(j.company) : setInvalid(true)))
      .catch(() => setInvalid(true));
  }, [code]);

  async function submit() {
    setErr(null); setBusy(true);
    const lang = (typeof document !== "undefined" && document.documentElement.lang === "en") ? "en" : "id";
    const res = await fetch("/api/partner/reseller-register", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code.toUpperCase(), lang, ...f }),
    }).catch(() => null);
    setBusy(false);
    if (!res || !res.ok) {
      const j = res ? await res.json().catch(() => ({})) : {};
      return setErr(j.msg || "Gagal — coba lagi. / Failed — try again.");
    }
    setDone(true);
  }

  return (
    <div style={{ minHeight: "100dvh", display: "grid", placeItems: "center", padding: "1.5rem", background: "var(--bg)" }}>
      <div className="auth-card" style={{ width: "min(460px, 100%)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "1rem" }}>
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 34, height: 34, objectFit: "contain", flex: "none" }} />
          <strong style={{ fontSize: "1.0625rem" }}>MesinViral</strong>
          <span className="badge" style={{ background: "var(--brand-soft)", color: "var(--brand)", fontSize: "0.5625rem", padding: "2px 6px" }}>PARTNER</span>
        </div>
        {invalid ? (
          <p className="lead"><Bi id="Tautan pendaftaran ini tidak berlaku. Minta tautan terbaru ke agen yang merekrut Anda." en="This registration link is not valid. Ask your recruiting agent for a fresh link." /></p>
        ) : done ? (<>
          <h1 style={{ fontSize: "1.25rem" }}><Bi id="Pendaftaran terkirim ✓" en="Registration submitted ✓" /></h1>
          <p className="lead"><Bi id={`Menunggu persetujuan ${company}. Setelah disetujui, undangan akses portal dikirim ke email Anda.`} en={`Awaiting approval from ${company}. Once approved, a portal invitation will be sent to your email.`} /></p>
        </>) : (<>
          <h1 style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}><Bi id="Daftar jadi reseller" en="Become a reseller" /></h1>
          <p className="lead" style={{ marginBottom: "1rem" }}>
            {company
              ? <Bi id={`Anda direkrut oleh ${company}. Isi data di bawah — komisi dibayar oleh agen Anda setiap bulan.`} en={`You're being recruited by ${company}. Fill in the form — commissions are paid monthly by your agent.`} />
              : "…"}
          </p>
          <div className="form-stack">
            <div><label className="label"><Bi id="Nama lengkap" en="Full name" /></label><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
            <div><label className="label">Email</label><input className="input" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
            <div><label className="label"><Bi id="No. WhatsApp (opsional)" en="WhatsApp number (optional)" /></label><input className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.625rem" }}>
              <div><label className="label">Bank</label><input className="input" placeholder="BCA / BRI / …" value={f.bank_name} onChange={(e) => setF({ ...f, bank_name: e.target.value })} /></div>
              <div><label className="label"><Bi id="No. rekening" en="Account number" /></label><input className="input" inputMode="numeric" value={f.account_no} onChange={(e) => setF({ ...f, account_no: e.target.value.replace(/\D/g, "") })} /></div>
            </div>
            <div><label className="label"><Bi id="Atas nama (sesuai rekening)" en="Account holder name" /></label><input className="input" value={f.holder} onChange={(e) => setF({ ...f, holder: e.target.value })} /></div>
            <p style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", margin: 0 }}><Bi id="Nomor rekening disimpan terenkripsi — dipakai agen Anda untuk transfer komisi bulanan." en="Your account number is stored encrypted — used by your agent for monthly commission transfers." /></p>
            <button className="btn btn-default btn-lg" style={{ width: "100%" }} onClick={submit} disabled={busy || !company}>{busy ? "…" : <Bi id="Kirim pendaftaran" en="Submit registration" />}</button>
            {err && <div style={{ color: "var(--error, #dc2626)", fontSize: "var(--text-sm)" }}>{err}</div>}
          </div>
        </>)}
      </div>
    </div>
  );
}
