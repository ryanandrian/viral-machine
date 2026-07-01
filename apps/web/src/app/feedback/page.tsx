"use client";

import { useEffect, useState } from "react";

// Halaman masukan PUBLIK (tujuan link email trial-lapse/reminder). Bilingual (ID/EN). Alasan churn
// terstruktur + saran bebas → /api/feedback (service_role). Standalone, reuse kelas global (card/input/btn).

const REASONS: { key: string; id: string; en: string }[] = [
  { key: "price", id: "Harga terlalu mahal", en: "Too expensive" },
  { key: "features", id: "Fitur belum lengkap", en: "Missing features" },
  { key: "results", id: "Hasil belum sesuai harapan", en: "Results not good enough" },
  { key: "not_ready", id: "Belum membutuhkan sekarang", en: "Not needed right now" },
  { key: "other", id: "Lainnya", en: "Other" },
];

export default function FeedbackPage() {
  const [lang, setLang] = useState<"id" | "en">("id");
  const [reason, setReason] = useState<string>("");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [ref, setRef] = useState<string | null>(null);
  const [source, setSource] = useState("feedback_page");

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setRef(q.get("ref"));
    if (q.get("source")) setSource(q.get("source")!);
    const nav = (navigator.language || "id").toLowerCase();
    if (nav.startsWith("en")) setLang("en");
  }, []);

  const t = (id: string, en: string) => (lang === "id" ? id : en);

  async function submit() {
    setBusy(true);
    await fetch("/api/feedback", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason, message: message.trim(), email: email.trim(), ref, source }),
    }).catch(() => {});
    setBusy(false); setSent(true);
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", padding: "2rem 1rem", background: "var(--surface-0, #0b0d12)" }}>
      <div style={{ width: "100%", maxWidth: 520 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <a href="/" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "var(--text-primary)" }}>
            <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 28, height: 28, borderRadius: 6 }} />
            <b>MesinViral</b>
          </a>
          <div className="segmented">
            <button aria-selected={lang === "id"} onClick={() => setLang("id")}>ID</button>
            <button aria-selected={lang === "en"} onClick={() => setLang("en")}>EN</button>
          </div>
        </div>

        <div className="card card-pad">
          {sent ? (
            <div style={{ textAlign: "center", padding: "1.5rem 0" }}>
              <h2 style={{ marginBottom: ".5rem" }}>{t("Terima kasih! 🙏", "Thank you! 🙏")}</h2>
              <p className="muted">{t("Masukan Anda sangat berarti untuk membuat MesinViral lebih baik.", "Your feedback helps us make MesinViral better.")}</p>
              <a href="/" className="btn btn-secondary" style={{ marginTop: "1rem" }}>{t("Kembali ke beranda", "Back to home")}</a>
            </div>
          ) : (
            <>
              <h2 style={{ marginBottom: ".35rem" }}>{t("Bantu kami jadi lebih baik", "Help us improve")}</h2>
              <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "1.25rem" }}>
                {t("Butuh 1 menit. Apa alasan utama Anda belum melanjutkan?", "Takes 1 minute. What's the main reason you didn't continue?")}
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: ".5rem", marginBottom: "1rem" }}>
                {REASONS.map((r) => (
                  <button key={r.key} onClick={() => setReason(r.key)}
                    className={`btn ${reason === r.key ? "btn-default" : "btn-secondary"}`}
                    style={{ justifyContent: "flex-start", textAlign: "left" }}>
                    {t(r.id, r.en)}
                  </button>
                ))}
              </div>
              <label className="label">{t("Saran / masukan (opsional)", "Suggestions (optional)")}</label>
              <textarea className="textarea" rows={4} value={message} onChange={(e) => setMessage(e.target.value)}
                placeholder={t("Ceritakan apa yang bisa kami perbaiki…", "Tell us what we could do better…")} />
              <label className="label" style={{ marginTop: ".75rem" }}>{t("Email (opsional, bila ingin kami hubungi)", "Email (optional, if you'd like a reply)")}</label>
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@email.com" />
              <button className="btn btn-default btn-lg" style={{ width: "100%", marginTop: "1.25rem" }}
                disabled={busy || (!reason && !message.trim())} onClick={submit}>
                {busy ? "…" : t("Kirim masukan", "Send feedback")}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
