// Halaman cek fondasi (sementara) — memverifikasi design system MesinViral ter-port:
// tokens (warna/tema), components (.btn/.card/.kpi/.badge), tipografi Geist, pola i18n data-id/data-en.
// Akan diganti screen asli (D5/D1) pada langkah implementasi berikutnya.
export default function FoundationCheck() {
  return (
    <main style={{ maxWidth: 980, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <span className="badge badge-brand" style={{ marginBottom: "1rem" }}>
        <span className="dot" />
        <span data-id>Fondasi terpasang</span>
        <span data-en>Foundation ready</span>
      </span>

      <h1 style={{ fontSize: "var(--text-4xl)", fontWeight: 800, letterSpacing: "-0.03em", margin: "0 0 0.5rem" }}>
        MesinViral — Design System
      </h1>
      <p className="secondary" style={{ margin: "0 0 2rem", fontSize: "var(--text-lg)" }}>
        <span data-id>Port Hybrid dari Claude Design: tokens + components, tema dark, tipografi Geist.</span>
        <span data-en>Hybrid port from Claude Design: tokens + components, dark theme, Geist type.</span>
      </p>

      {/* Buttons — dari components.css */}
      <div style={{ display: "flex", gap: "0.625rem", flexWrap: "wrap", marginBottom: "2rem" }}>
        <button className="btn btn-default">Primary</button>
        <button className="btn btn-secondary">Secondary</button>
        <button className="btn btn-outline">Outline</button>
        <button className="btn btn-ghost">Ghost</button>
        <button className="btn btn-ai glow-ai">AI Action</button>
      </div>

      {/* KPI cards — grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.875rem", marginBottom: "2rem" }}>
        <div className="kpi">
          <div className="kpi-label">Total Views</div>
          <div className="kpi-value">58.2K</div>
          <div className="kpi-delta up">▲ 2.3x</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Video Hari Ini</div>
          <div className="kpi-value">5</div>
          <div className="kpi-delta up">▲ 12%</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Compliance</div>
          <div className="kpi-value">94</div>
          <div className="kpi-delta down">▼ 3</div>
        </div>
      </div>

      {/* Card + badges */}
      <div className="card">
        <div className="card-head">
          <h2 className="card-title">Channel: Misteri Samudra</h2>
          <span className="badge badge-success"><span className="dot" />Aktif</span>
        </div>
        <div className="card-body">
          <p className="secondary" style={{ margin: 0 }}>
            <span data-id>Kartu, badge, dan tipografi memakai class design system asli — nol redesign.</span>
            <span data-en>Cards, badges, and type use the original design-system classes — zero redesign.</span>
          </p>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", flexWrap: "wrap" }}>
            <span className="badge badge-brand">universe_mysteries</span>
            <span className="badge badge-warning">pending</span>
            <span className="badge badge-running"><span className="dot" />running</span>
            <span className="badge badge-outline">id-ID</span>
          </div>
        </div>
      </div>
    </main>
  );
}
