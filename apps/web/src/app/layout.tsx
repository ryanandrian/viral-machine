import type { Metadata } from "next";
import "./globals.css";
// Hybrid: design system MesinViral (di-port dari Claude Design bundle). Urutan penting:
// tailwind (globals) -> tokens (CSS variables + base) -> components (.btn/.card/.kpi/dst).
// Font (Geist + JetBrains Mono) di-load via @import di tokens.css; tema dark default via [data-theme].
// TODO(optimasi): pindah font ke next/font, hapus @import google fonts di tokens.css (hindari double-load).
import "@/styles/tokens.css";
import "@/styles/components.css";

export const metadata: Metadata = {
  title: "MesinViral — Mesin produksi video YouTube otomatis",
  description:
    "SaaS produksi video YouTube Shorts otomatis berbasis AI — self-learning, BYOK, multi-channel.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // lang="id" = Bahasa Indonesia default (EN via toggle); data-theme="dark" = tema default desain.
  return (
    <html lang="id" data-theme="dark">
      <body>{children}</body>
    </html>
  );
}
