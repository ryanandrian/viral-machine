import { AdminShell } from "@/components/admin-shell";

// Segment /admin/* → dibungkus AdminShell (admin.mesinviral.com). Internal/staff-only.
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
