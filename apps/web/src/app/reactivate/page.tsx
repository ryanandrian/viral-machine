"use client";

import { useEffect, useState } from "react";

// Reaktivasi 1-klik dari link email (LIFECYCLE B9). PUBLIK (token = auth). Bilingual ID/EN. Standalone,
// reuse kelas global (card/btn). trial_expired+tuas → trial diperpanjang gratis → arahkan masuk;
// status lain → arahkan ke /billing (bayar). Token invalid/kedaluwarsa → pesan + tautan masuk.

type State = "loading" | "extended" | "checkout" | "error";

export default function ReactivatePage() {
  const [lang, setLang] = useState<"id" | "en">("id");
  const [state, setState] = useState<State>("loading");
  const [days, setDays] = useState<number>(0);
  // [B24] 'upgrade' = belum pernah berlangganan → ajak PILIH PAKET.
  // 'renew' = pernah membayar → ajak PERPANJANG. Dulu keduanya dilempar diam-diam ke /billing:
  // tenant yang mengira dapat perpanjangan gratis mendarat di halaman tagihan tanpa satu kalimat
  // pun penjelasan — cara tercepat kehilangan orang yang sebenarnya sudah hampir membayar.
  const [arah, setArah] = useState<"upgrade" | "renew">("upgrade");

  useEffect(() => {
    if ((navigator.language || "id").toLowerCase().startsWith("en")) setLang("en");
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) { setState("error"); return; }
    fetch("/api/lifecycle/reactivate", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }),
    })
      .then((r) => r.ok ? r.json() : r.json().then((j) => Promise.reject(j)))
      .then((j) => {
        if (j?.action === "extended") { setDays(j.days || 0); setState("extended"); }
        else if (j?.action === "checkout") { setArah(j.arah === "renew" ? "renew" : "upgrade"); setState("checkout"); }
        else setState("error");
      })
      .catch(() => setState("error"));
  }, []);

  const t = (id: string, en: string) => (lang === "id" ? id : en);

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem 1rem", background: "var(--surface-0, #0b0d12)" }}>
      <div className="card card-pad" style={{ width: "100%", maxWidth: 460, textAlign: "center" }}>
        <a href="/" style={{ display: "inline-flex", alignItems: "center", gap: 8, textDecoration: "none", color: "var(--text-primary)", marginBottom: "1.25rem" }}>
          <img src="/mesinviral_logo512.png" alt="MesinViral" style={{ width: 30, height: 30, borderRadius: 6 }} />
          <b>MesinViral</b>
        </a>
        {state === "loading" && <p className="muted">{t("Memproses…", "Processing…")}</p>}
        {state === "extended" && (
          <>
            <h2 style={{ marginBottom: ".5rem" }}>{t("Trial diperpanjang! 🎉", "Trial extended! 🎉")}</h2>
            <p className="muted" style={{ marginBottom: "1.25rem" }}>
              {t(`Kami tambahkan ${days} hari trial untuk Anda. Masuk untuk melanjutkan produksi.`,
                 `We added ${days} more trial days for you. Sign in to keep producing.`)}
            </p>
            <a href="/auth?view=login" className="btn btn-default btn-lg" style={{ width: "100%" }}>{t("Masuk sekarang", "Sign in now")}</a>
          </>
        )}
        {state === "checkout" && (
          <>
            <h2 style={{ marginBottom: ".5rem" }}>
              {arah === "renew"
                ? t("Perpanjang langganan Anda", "Renew your subscription")
                : t("Lanjutkan dengan paket berbayar", "Continue on a paid plan")}
            </h2>
            <p className="muted" style={{ marginBottom: "1.25rem" }}>
              {arah === "renew"
                ? t("Produksi otomatis Anda berhenti karena langganan belum diperpanjang. Perpanjang sekarang dan channel Anda langsung jalan lagi — pengaturan, niche, dan riwayatnya tetap utuh.",
                    "Your automated production stopped because the subscription hasn't been renewed. Renew now and your channels resume immediately — settings, niches, and history are all still there.")
                : t("Masa coba Anda sudah kami perpanjang sebelumnya, jadi kali ini pilih paket untuk melanjutkan. Semua pengaturan channel Anda tersimpan dan langsung dipakai begitu paket aktif.",
                    "We already extended your trial once before, so this time please pick a plan to continue. All your channel settings are saved and will be used the moment a plan is active.")}
            </p>
            <a href="/billing" className="btn btn-default btn-lg" style={{ width: "100%" }}>
              {arah === "renew" ? t("Perpanjang sekarang", "Renew now") : t("Lihat paket", "View plans")}
            </a>
            <a href="/auth?view=login" className="btn btn-ghost btn-sm" style={{ width: "100%", marginTop: ".5rem" }}>
              {t("Masuk dulu", "Sign in first")}
            </a>
          </>
        )}
        {state === "error" && (
          <>
            <h2 style={{ marginBottom: ".5rem" }}>{t("Link tidak berlaku", "Link not valid")}</h2>
            <p className="muted" style={{ marginBottom: "1.25rem" }}>
              {t("Link reaktivasi tidak valid atau sudah kedaluwarsa. Silakan masuk untuk mengelola langganan Anda.",
                 "This reactivation link is invalid or expired. Please sign in to manage your subscription.")}
            </p>
            <a href="/auth?view=login" className="btn btn-secondary btn-lg" style={{ width: "100%" }}>{t("Masuk", "Sign in")}</a>
          </>
        )}
      </div>
    </div>
  );
}
