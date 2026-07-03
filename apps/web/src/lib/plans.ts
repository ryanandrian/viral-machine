import { createClient } from "@/lib/supabase/client";

// SUMBER TUNGGAL konfigurasi tier (public-read, anon — tanpa auth). No-hardcode (owner 2026-06-21):
// Landing/Billing/sidebar render nama + harga + batas + Niche Studio + masa trial DARI SINI, bukan literal.
// Gabung: plan_limits (nama/batas/niche-studio/urutan) + pricing_config (harga) + app_config (trial hari).
export type Plan = {
  plan_type: string;          // KEY stabil (trial/starter/pro/business) — jangan ditampilkan mentah
  display_name: string;       // nama yang dilihat pelanggan (admin-editable)
  price_idr: number | null;   // dari pricing_config plan_<type>; null = gratis (trial)
  max_channels: number;
  max_videos_per_day: number;
  niche_studio: boolean;      // fasilitas Niche Studio (admin-editable per-tier)
  sort_order: number;
};

export async function fetchPlans(): Promise<{ plans: Plan[]; trialDays: number }> {
  const supabase = createClient();
  const [{ data: pl }, { data: pc }, { data: ac }] = await Promise.all([
    supabase.from("plan_limits")
      .select("plan_type, display_name, max_channels, max_videos_per_day, niche_studio, sort_order")
      .order("sort_order"),
    supabase.from("pricing_config").select("key, value_idr").eq("active", true),
    supabase.from("app_config").select("value").eq("key", "trial_duration_days").maybeSingle(),
  ]);
  const price: Record<string, number> = {};
  (pc ?? []).forEach((r) => { price[r.key as string] = r.value_idr as number; });
  const plans: Plan[] = (pl ?? []).map((r) => ({
    plan_type: r.plan_type as string,
    display_name: (r.display_name as string) || (r.plan_type as string),
    price_idr: price[`plan_${r.plan_type}`] ?? null,
    max_channels: r.max_channels as number,
    max_videos_per_day: r.max_videos_per_day as number,
    niche_studio: Boolean(r.niche_studio),
    sort_order: (r.sort_order as number) ?? 0,
  }));
  const trialDays = Number((ac as { value?: number } | null)?.value ?? 7);
  return { plans, trialDays };
}

// Masa trial SAJA (ringan, 1 query) — utk halaman yang cuma butuh angka hari (showcase/auth CTA).
// Sumber = app_config.trial_duration_days (admin-editable "Masa Trial Gratis" di System Config). No-hardcode.
export async function fetchTrialDays(): Promise<number> {
  const { data } = await createClient().from("app_config").select("value").eq("key", "trial_duration_days").maybeSingle();
  return Number((data as { value?: number } | null)?.value ?? 7);
}

// Tier berbayar (punya harga) urut — untuk kartu Landing/Pricing (trial gratis dikecualikan).
export function paidPlans(plans: Plan[]): Plan[] {
  return plans.filter((p) => p.price_idr != null).sort((a, b) => a.sort_order - b.sort_order);
}
