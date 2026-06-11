"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

// Tema dark default; light via toggle. Memetakan ke [data-theme] di <html> agar
// cocok dengan tokens.css desain ([data-theme="dark"|"light"]). enableSystem=false
// karena desain memutuskan dark sebagai default eksplisit.
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme="dark"
      enableSystem={false}
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
}
