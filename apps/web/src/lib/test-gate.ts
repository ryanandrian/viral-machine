import { createAdminClient } from "@/lib/supabase/admin";

// [B24 §10c] GERBANG UJI — sisi server Next.js.
// SATU OTAK: logikanya hidup di fungsi DB `tenant_test_gate` (migr 0191), yang juga dipanggil oleh
// aturan akses tabel `direct_jobs` (menjaga jalur browser-langsung) dan oleh worker Python. Modul ini
// HANYA memanggil — meniru logikanya di sini akan melahirkan kebenaran kedua yang suatu hari berbeda.
//
// Kenapa route API butuh pemeriksaan sendiri padahal aturan tabel sudah ada: route menyisipkan job
// dengan kunci layanan (service_role) yang justru MELEWATI aturan tabel. Tanpa modul ini, dua pintu
// (Uji produksi channel & Uji niche) tetap terbuka lebar.
//
// SSOT: PAYMENT_AND_TENANT_GATE_ARCHITECTURE.md §10.

export type GateReason =
  | "ok" | "gate_off" | "comp"
  | "subscription" | "trial_quota" | "tenant_unknown" | "forbidden" | "gate_unavailable";

export type TestGate = {
  allowed: boolean;
  reason: GateReason;
  status?: string;
  used?: number;
  max?: number;
};

/**
 * Tanya database: tenant ini boleh menjalankan uji atau tidak.
 *
 * GAGAL JUJUR: RPC tak terjawab → allowed=false + reason "gate_unavailable". Uji adalah aksi manual
 * yang bisa diulang tenant; menolak sesaat jauh lebih aman daripada membuka pintu justru saat kita
 * buta. Ini TIDAK menyentuh produksi terjadwal.
 */
export async function testGate(tenantId: string): Promise<TestGate> {
  if (!tenantId) return { allowed: false, reason: "tenant_unknown" };
  try {
    const admin = createAdminClient();
    const { data, error } = await admin.rpc("tenant_test_gate", { p_tenant_id: tenantId });
    if (error) {
      console.error("[test-gate] RPC tenant_test_gate gagal:", error.message);
      return { allowed: false, reason: "gate_unavailable" };
    }
    const g = (Array.isArray(data) ? data[0] : data) as TestGate | null;
    if (!g || typeof g.allowed !== "boolean") {
      console.error("[test-gate] bentuk hasil tak dikenal:", JSON.stringify(data));
      return { allowed: false, reason: "gate_unavailable" };
    }
    return g;
  } catch (e) {
    console.error("[test-gate] RPC tenant_test_gate melempar:", (e as Error).message);
    return { allowed: false, reason: "gate_unavailable" };
  }
}

/**
 * Kode penolakan yang dikirim ke layar. SENGAJA kode, bukan kalimat: aturan dwibahasa kita (§3.5)
 * mewajibkan API mengirim KODE dan layar yang menerjemahkan ke ID/EN. Bentuknya sama persis dengan
 * yang ditulis worker ke `direct_jobs.error`, sehingga layar cukup punya SATU penerjemah.
 *   GATE:subscription · GATE:trial_quota:8:3 · GATE:gate_unavailable · …
 */
export function gateCode(g: TestGate): string {
  if (g.reason === "trial_quota") return `GATE:trial_quota:${g.used ?? 0}:${g.max ?? 0}`;
  return `GATE:${g.reason}`;
}
