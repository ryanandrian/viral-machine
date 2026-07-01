"use client";

import { useState, useEffect, useCallback } from "react";
import { SlidersHorizontal } from "lucide-react";

// Application Config (admin) — parameter GLOBAL mesin & trial (app_config). Halaman khusus.
// Auto-save (PATCH /api/admin/app-config/[key]). Label ramah + keterangan bahasa admin (description DB).

function Bi({ id, en }: { id: string; en: string }) {
  return (<><span data-id>{id}</span><span data-en>{en}</span></>);
}

type AppCfg = { key: string; value: number; description: string | null };

// Metadata tampilan (label ramah + unit + grup). Keterangan detail = description (DB, bahasa admin).
const G_BILLING = "Langganan, Trial & Penagihan";
const G_TREND = "Bobot Sumber Tren";
const G_ENGINE = "Performa Mesin Tren";
const G_OTHER = "Lainnya";
const CFG_GROUPS: [string, string][] = [
  [G_BILLING, "Subscription, Trial & Billing"],
  [G_TREND, "Trend Source Weights"],
  [G_ENGINE, "Trend Engine Performance"],
  [G_OTHER, "Others"],   // ← catch-all: SETIAP key app_config tanpa metadata TETAP tampil (anti-hilang selamanya)
];
const CFG_META: Record<string, { label: string; group: string; unit: string; hint?: string }> = {
  trial_duration_days:          { label: "Masa Trial Gratis", group: G_BILLING, unit: "hari" },
  trial_reminder_days_before:   { label: "Pengingat Sebelum Trial Habis", group: G_BILLING, unit: "hari", hint: "H-x; 0 = matikan" },
  renewal_reminder_days_before: { label: "Pengingat Sebelum Langganan Habis", group: G_BILLING, unit: "hari", hint: "H-x; 0 = matikan" },
  subscription_period_days:     { label: "Durasi Periode Langganan", group: G_BILLING, unit: "hari", hint: "default 30 (bulanan)" },
  billing_grace_days:           { label: "Masa Tenggang Sebelum Dihentikan", group: G_BILLING, unit: "hari" },
  checkout_expiry_hours:        { label: "Masa Berlaku Link Bayar", group: G_BILLING, unit: "jam" },
  ppn_percent:                  { label: "PPN Invoice", group: G_BILLING, unit: "%", hint: "0 = harga final; 11 = PKP" },
  niche_eval_window_days:       { label: "Masa Evaluasi Niche Custom", group: G_OTHER, unit: "hari" },
  trend_weight_youtube:    { label: "YouTube (utama)", group: G_TREND, unit: "%" },
  trend_weight_trends:     { label: "Google Trends", group: G_TREND, unit: "%" },
  trend_weight_news:       { label: "Google News", group: G_TREND, unit: "%" },
  trend_weight_wikipedia:  { label: "Wikipedia", group: G_TREND, unit: "%" },
  trend_weight_hackernews: { label: "HackerNews", group: G_TREND, unit: "%" },
  trend_cache_ttl_sec:     { label: "Penyegaran Data Tren", group: G_ENGINE, unit: "detik", hint: "43200 = 12 jam" },
  trend_refresh_pacing_ms: { label: "Jeda Ambil Data", group: G_ENGINE, unit: "ms", hint: "3000 = 3 detik" },
};

export default function AppConfigPage() {
  const [cfg, setCfg] = useState<AppCfg[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await fetch("/api/admin/app-config");
    const j = await r.json().catch(() => ({ app_config: [] }));
    setCfg(j.app_config ?? []);
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  async function patch(key: string, value: number) {
    const r = await fetch(`/api/admin/app-config/${key}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ value }),
    });
    setToast(r.ok ? "✓ Tersimpan" : "Gagal menyimpan");
    if (r.ok) await load();
    setTimeout(() => setToast(null), 2200);
  }

  return (
    <>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 0.375rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <SlidersHorizontal size={20} /> <Bi id="Konfigurasi Sistem" en="System Configuration" />
        </h1>
        <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0, maxWidth: "65ch" }}>
          <Bi id="Parameter global mesin produksi & trial. Berlaku ke seluruh tenant. Tersimpan otomatis — tanpa tombol Save." en="Global production-engine & trial parameters. Applies to all tenants. Auto-saved — no Save button." />
        </p>
      </div>

      {loading ? (
        <div className="muted" style={{ padding: "3rem", textAlign: "center" }}>Memuat…</div>
      ) : (
        <div className="card" style={{ maxWidth: 720 }}>
          <div className="card-head">
            <h3 className="card-title"><SlidersHorizontal size={15} /> <Bi id="Parameter mesin & trial" en="Engine & trial parameters" /></h3>
            <span className="card-sub" style={{ color: "var(--success)", fontWeight: 500 }}><Bi id="✓ Tersimpan otomatis" en="✓ Auto-saved" /></span>
          </div>
          <div className="card-body" style={{ display: "grid", gap: "1.5rem" }}>
            {CFG_GROUPS.map(([grp, grpEn]) => {
              const items = cfg.filter((a) => (CFG_META[a.key]?.group ?? G_OTHER) === grp);
              if (items.length === 0) return null;
              const total = grp === G_TREND ? items.reduce((n, a) => n + (a.value || 0), 0) : null;
              return (
                <div key={grp}>
                  <div className="label" style={{ textTransform: "uppercase", letterSpacing: ".04em", marginBottom: ".5rem", display: "flex", alignItems: "center", gap: ".5rem" }}>
                    <span><Bi id={grp} en={grpEn} /></span>
                    {total != null && <span style={{ color: total === 100 ? "var(--success)" : "var(--warning)", fontWeight: 600 }}>total {total}%{total !== 100 && " ⚠"}</span>}
                  </div>
                  {items.map((a) => {
                    const m = CFG_META[a.key];
                    return (
                      <div key={a.key} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "1rem", alignItems: "center", padding: ".7rem 0", borderBottom: "1px solid var(--border-subtle)" }}>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 500, fontSize: "var(--text-sm)" }}>{m?.label ?? a.key}</div>
                          <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: "3px", lineHeight: 1.45 }}>{a.description}{m?.hint && <span style={{ marginLeft: ".375rem", opacity: .75 }}>({m.hint})</span>}</div>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: ".4rem", flex: "none" }}>
                          <input className="input" type="number" min={0} style={{ width: "5.5rem", height: "2rem", textAlign: "right" }} defaultValue={a.value} onBlur={(e) => { const n = parseInt(e.target.value, 10); if (Number.isInteger(n) && n !== a.value) patch(a.key, n); }} />
                          <span className="muted" style={{ fontSize: "var(--text-xs)", width: "2.75rem" }}>{m?.unit ?? ""}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
            {cfg.length === 0 && <div className="muted" style={{ fontSize: "var(--text-xs)" }}>—</div>}
          </div>
        </div>
      )}

      {toast && (
        <div style={{ position: "fixed", bottom: "1.5rem", right: "1.5rem", background: "var(--surface-3)", border: "1px solid var(--border-strong)", borderRadius: "var(--r-md)", padding: ".625rem 1rem", fontSize: "var(--text-sm)", boxShadow: "var(--shadow-md)", zIndex: 50 }}>{toast}</div>
      )}
    </>
  );
}
