import nodemailer from "nodemailer";

// Pengirim SMTP untuk email transaksional yang dikirim LANGSUNG dari mv-web (sinkron, instan —
// mis. reset password, konfirmasi signup). Kredensial 100% dari env (no-hardcode), SATU sumber sama
// dengan worker (mail.lumite.biz.id). SERVER-ONLY: jangan pernah diimpor dari komponen "use client".
//
// Catatan: pipeline email admin→tenant (broadcast) tetap lewat `email_outbox` (worker, cadence 60s).
// Yang lewat sini HANYA email yang harus instan & terpicu aksi pengguna.

let cached: nodemailer.Transporter | null = null;

function transport(): nodemailer.Transporter {
  if (cached) return cached;
  const host = process.env.SMTP_HOST;
  const port = Number(process.env.SMTP_PORT || "465");
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;
  if (!host || !user || !pass) {
    throw new Error("SMTP env belum lengkap (SMTP_HOST/SMTP_USER/SMTP_PASS)");
  }
  cached = nodemailer.createTransport({
    host,
    port,
    secure: port === 465, // 465 = SMTPS implicit TLS
    auth: { user, pass },
  });
  return cached;
}

export async function sendMail(to: string, subject: string, html: string, text: string): Promise<void> {
  const from = process.env.SMTP_FROM || `MesinViral <${process.env.SMTP_USER}>`;
  await transport().sendMail({ from, to, subject, html, text });
}
