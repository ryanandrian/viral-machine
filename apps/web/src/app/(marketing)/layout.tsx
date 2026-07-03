import { MarketingShell } from "@/components/marketing-shell";

// Route group (marketing) — halaman publik (Landing, Pricing, dst) dibungkus MarketingShell (nav+footer).
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <MarketingShell>{children}</MarketingShell>;
}
