import { createClient } from "@/lib/supabase/client";

// Ambil harga aktif dari pricing_config (public-read, anon — tanpa auth). SUMBER HARGA sistem
// (landing A1 + pricing A2 + billing D13 + admin E5). value_idr = Rupiah penuh. Phase: no-hardcode.
export async function fetchPricing(): Promise<Record<string, number>> {
  const supabase = createClient();
  const { data } = await supabase.from("pricing_config").select("key, value_idr").eq("active", true);
  const m: Record<string, number> = {};
  (data ?? []).forEach((r) => { m[r.key] = r.value_idr as number; });
  return m;
}

// "149K" / "1.5JT" ringkas (untuk kartu harga marketing).
export function idrK(n: number | undefined): string {
  if (!n) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}JT`;
  return `${Math.round(n / 1_000)}K`;
}
