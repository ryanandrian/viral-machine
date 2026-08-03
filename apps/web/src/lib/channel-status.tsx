// Status efektif channel — SATU SUMBER (dipakai daftar /channels + detail /channels/[id]), anti-drift.
// Prioritas: langganan → dihentikan sistem → belum lengkap (readiness) → dijeda → aktif.

export type Eff = {
  key: "sub" | "halted" | "incomplete" | "paused" | "active";
  label_id: string; label_en: string;
  tone: "ok" | "warn" | "stop" | "muted";
  reason?: string; reco_id?: string; reco_en?: string;
};

type ChLite = { is_active: boolean | null; production_paused: boolean | null; production_paused_reason?: string | null };
type Readiness = { ready: boolean; missing: string[] } | null;

/**
 * Status langganan yang membolehkan PRODUKSI — cerminan `PRODUCING_STATUSES` di
 * src/billing/limits.py dan `tenant_produce_allowed()` di database.
 *
 * [B24 2026-08-02] Daftar ini sebelumnya ditulis ulang di TIGA tempat dan salah satu isinya berbeda:
 * ketiganya memuat `"trialing"` — nilai yang TIDAK ADA di mesin maupun di database (diperiksa
 * langsung ke keduanya). Artinya layar bersiap menerima status yang tak pernah lahir, sementara
 * mesin akan memperlakukannya sebagai mati. Fosil dibuang; daftarnya kini satu tempat.
 *
 * CATATAN: ini gerbang PRODUKSI. Gerbang UJI berbeda — masa tenggang (grace) boleh berproduksi
 * tapi TIDAK boleh menjalankan uji. Aturannya ada di database (`tenant_test_gate`), bukan di sini.
 */
export const SUB_PRODUCING = ["active", "trial", "grace"] as const;

export function subIsProducing(sub: string | null | undefined): boolean {
  return !sub || (SUB_PRODUCING as readonly string[]).includes(sub);
}

export function effectiveStatus(ch: ChLite, sub: string | null, rd: Readiness): Eff {
  if (sub && !subIsProducing(sub))
    return { key: "sub", label_id: "Langganan nonaktif", label_en: "Subscription inactive", tone: "stop",
      reco_id: "Aktifkan langganan untuk melanjutkan produksi.", reco_en: "Reactivate subscription to resume." };
  if (ch.production_paused)
    // [B25] TANPA `reco` — sengaja. Anjuran lama ("perbaiki kredit/konfigurasi") adalah TEBAKAN yang
    // dibuat sebelum sistem menyimpan kelas errornya. Kini penjelasan + langkah konkret per-KELAS ada
    // di `PemulihanChannel` (halaman channel), dan permukaan lain (dashboard, daftar channel) cukup
    // menampilkan `reason` lalu mengantar ke sana. Menyisakan tebakan di sini = mengundang permukaan
    // berikutnya memakainya lagi dan menyebarkan anjuran yang salah.
    return { key: "halted", label_id: "Dihentikan sistem", label_en: "Halted by system", tone: "stop",
      reason: ch.production_paused_reason ?? undefined };
  if (rd && !rd.ready)
    return { key: "incomplete", label_id: "Belum lengkap", label_en: "Incomplete", tone: "warn", reason: rd.missing?.length ? `Kurang: ${rd.missing.join(", ")}` : undefined,
      reco_id: "Lengkapi konfigurasi & kredensial, lalu aktifkan.", reco_en: "Complete config & credentials, then activate." };
  if (!ch.is_active)
    return { key: "paused", label_id: "Dijeda", label_en: "Paused", tone: "warn", reco_id: "Channel dijeda manual. Klik Play untuk melanjutkan.", reco_en: "Manually paused. Click Play to resume." };
  return { key: "active", label_id: "Aktif", label_en: "Active", tone: "ok" };
}

export const TONE: Record<string, string> = { ok: "badge-success", warn: "badge-warning", stop: "badge-danger", muted: "badge-default" };

// Badge ringkas (bilingual via data-id/data-en — sama pola Bi). Dipakai daftar + header detail.
export function ChannelStatusBadge({ eff, style }: { eff: Eff; style?: React.CSSProperties }) {
  return (
    <span className={`badge ${TONE[eff.tone]}`} style={{ fontSize: "var(--text-xs)", ...style }}>
      <span className="dot" />
      <span data-id>{eff.label_id}</span><span data-en>{eff.label_en}</span>
    </span>
  );
}
