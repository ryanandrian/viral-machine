import { AppShell } from "@/components/app-shell";

// Route group (app) — semua screen tenant dibungkus AppShell (sidebar + topbar).
// URL tidak terpengaruh nama group: /dashboard, /channels, dst.
export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
