"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

// [D1] Tombol Help kontekstual SOFTCODE (mandat owner 2026-07-11).
// SATU SUMBER registry LOKASI tombol (titik fisik hidup di halaman → tetap di kode) +
// pembaca pemetaan DB (help_links_effective, migr 0153; admin kelola via Content → Tombol Help).
// Rantai fallback (tombol TIDAK PERNAH mati/nyasar):
//   pemetaan DB (hanya artikel published — digugurkan view bila tidak) → defaultSlug registry → /docs.

export type HelpLocation = {
  key: string;
  defaultSlug: string;
  label: { id: string; en: string };   // dipakai layar admin
  group: { id: string; en: string };
};

const G_MENU = { id: "Menu utama", en: "Main menu" };
const G_CH = { id: "Channel", en: "Channels" };
const G_LAIN = { id: "Lainnya", en: "Others" };

export const HELP_LOCATIONS: HelpLocation[] = [
  { key: "integrations",   defaultSlug: "api-keys",           label: { id: "Integrasi (Kredensial & Koneksi)", en: "Integrations (Credentials)" }, group: G_MENU },
  { key: "niches",         defaultSlug: "niches",             label: { id: "Niche (Pustaka)", en: "Niches (Library)" }, group: G_MENU },
  { key: "runs",           defaultSlug: "runs-produksi",      label: { id: "Produksi (Runs)", en: "Runs" }, group: G_MENU },
  { key: "review",         defaultSlug: "review-video",       label: { id: "Perlu Ditinjau", en: "Needs Review" }, group: G_MENU },
  { key: "analytics",      defaultSlug: "analytics",          label: { id: "Analitik", en: "Analytics" }, group: G_MENU },
  { key: "schedule",       defaultSlug: "schedule",           label: { id: "Jadwal", en: "Schedule" }, group: G_MENU },
  { key: "compliance",     defaultSlug: "ai-slop-defense",    label: { id: "Kepatuhan", en: "Compliance" }, group: G_MENU },
  { key: "insights",       defaultSlug: "self-learning",      label: { id: "Wawasan (Insights)", en: "Insights" }, group: G_MENU },
  { key: "niche-studio",   defaultSlug: "niche-studio",       label: { id: "Niche Studio", en: "Niche Studio" }, group: G_MENU },
  { key: "billing",        defaultSlug: "billing",            label: { id: "Tagihan", en: "Billing" }, group: G_MENU },
  { key: "settings",       defaultSlug: "kelola-akun",        label: { id: "Pengaturan", en: "Settings" }, group: G_MENU },
  { key: "support",        defaultSlug: "bantuan",            label: { id: "Bantuan", en: "Support" }, group: G_MENU },
  { key: "channels",       defaultSlug: "membuat-channel",    label: { id: "Kanal (daftar)", en: "Channels (list)" }, group: G_CH },
  { key: "channel-new",    defaultSlug: "membuat-channel",    label: { id: "Tambah Channel", en: "Add Channel" }, group: G_CH },
  { key: "channel-detail", defaultSlug: "pengaturan-channel", label: { id: "Detail Channel (nama channel)", en: "Channel Detail" }, group: G_CH },
  { key: "onboarding",     defaultSlug: "onboarding",         label: { id: "Onboarding (Selamat datang)", en: "Onboarding (Welcome)" }, group: G_LAIN },
];

export const DEFAULT_HELP: Record<string, string> =
  Object.fromEntries(HELP_LOCATIONS.map((l) => [l.key, l.defaultSlug]));

// Cache pemetaan level-module: SEKALI ambil per sesi tab (semua tombol berbagi satu fetch).
let _cache: Record<string, string> | null = null;
let _inflight: Promise<Record<string, string>> | null = null;

async function fetchLinks(): Promise<Record<string, string>> {
  if (_cache) return _cache;
  if (!_inflight) {
    _inflight = (async () => {
      try {
        const { data } = await createClient()
          .from("help_links_effective")
          .select("location_key,article_slug");
        const m: Record<string, string> = {};
        for (const r of (data as { location_key: string; article_slug: string | null }[]) ?? []) {
          if (r.article_slug) m[r.location_key] = r.article_slug; // null (non-published) → pakai bawaan
        }
        _cache = m;
        return m;
      } catch {
        return {}; // fail-soft: gagal baca → bawaan
      }
    })();
  }
  return _inflight;
}

/** href tujuan tombol ? untuk sebuah lokasi — langsung usable, tak pernah kosong. */
export function useHelpHref(locationKey: string): string {
  const [slug, setSlug] = useState<string | null>(_cache?.[locationKey] ?? null);
  useEffect(() => {
    let alive = true;
    fetchLinks().then((m) => { if (alive && m[locationKey]) setSlug(m[locationKey]); });
    return () => { alive = false; };
  }, [locationKey]);
  const eff = slug ?? DEFAULT_HELP[locationKey];
  return eff ? `/docs?a=${eff}` : "/docs";
}
