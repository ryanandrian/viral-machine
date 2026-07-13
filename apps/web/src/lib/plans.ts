import { createClient } from "@/lib/supabase/client";

// SUMBER TUNGGAL konfigurasi tier (public-read, anon — tanpa auth). No-hardcode (owner 2026-06-21):
// Landing/Billing/sidebar render nama + harga + batas + Niche Studio + masa trial DARI SINI, bukan literal.
// Gabung: plan_limits (nama/batas/niche-studio/urutan) + pricing_config (harga) + app_config (trial hari).
export type PlanFeature = { id: string; en: string };
export type Plan = {
  plan_type: string;          // KEY stabil (trial/starter/pro/business) — jangan ditampilkan mentah
  display_name: string;       // nama yang dilihat pelanggan (admin-editable)
  price_idr: number | null;   // dari pricing_config plan_<type>; null = gratis (trial)
  max_channels: number;
  max_videos_per_day: number;
  niche_studio: boolean;      // fasilitas Niche Studio (admin-editable per-tier)
  sort_order: number;
  // Narasi marketing per-paket (Tahap 3/4 — admin-editable dari /admin/pricing, keputusan owner 2026-07-13)
  tagline_id: string;
  tagline_en: string;
  is_popular: boolean;
  marketing_features: PlanFeature[];
};

export async function fetchPlans(): Promise<{ plans: Plan[]; trialDays: number; annualDiscountPct: number }> {
  const supabase = createClient();
  const [{ data: pl }, { data: pc }, { data: ac }] = await Promise.all([
    supabase.from("plan_limits")
      .select("plan_type, display_name, max_channels, max_videos_per_day, niche_studio, sort_order, tagline_id, tagline_en, is_popular, marketing_features")
      .order("sort_order"),
    supabase.from("pricing_config").select("key, value_idr").eq("active", true),
    supabase.from("app_config").select("key, value").in("key", ["trial_duration_days", "annual_discount_pct"]),
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
    tagline_id: (r.tagline_id as string) ?? "",
    tagline_en: (r.tagline_en as string) ?? "",
    is_popular: Boolean(r.is_popular),
    marketing_features: (r.marketing_features as PlanFeature[]) ?? [],
  }));
  const cfg: Record<string, number> = {};
  (ac ?? []).forEach((r) => { cfg[r.key as string] = Number(r.value); });
  // Diskon tahunan (Tahap 2): 0/absen = pilihan tahunan DISEMBUNYIKAN (knob admin, no-hardcode).
  return { plans, trialDays: cfg.trial_duration_days ?? 7, annualDiscountPct: cfg.annual_discount_pct ?? 0 };
}

// Harga TAHUNAN total (IDR) untuk satu paket — rumus resmi = bulanan × 12 × (100−diskon)% (Pilar 3).
export function annualPriceIdr(monthly: number, discountPct: number): number {
  return Math.round(monthly * 12 * (100 - Math.max(0, Math.min(99, discountPct))) / 100);
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
