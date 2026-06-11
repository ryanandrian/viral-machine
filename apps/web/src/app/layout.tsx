import type { Metadata } from "next";
import "./globals.css";
// Hybrid design system MesinViral (port dari Claude Design bundle). Urutan import penting:
// tailwind (globals) -> tokens -> components -> app-shell.
// TODO(optimasi): font ke next/font, hapus @import google fonts di tokens.css.
import "@/styles/tokens.css";
import "@/styles/components.css";
import "@/styles/app-shell.css";
import { ThemeProvider } from "@/components/theme-provider";

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
  // lang="id" default (EN via toggle). data-theme dikelola next-themes (default dark);
  // suppressHydrationWarning karena next-themes inject atribut sebelum hydrate.
  return (
    <html lang="id" suppressHydrationWarning>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
