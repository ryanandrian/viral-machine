// D1 Dashboard (placeholder fondasi) — dalam AppShell. Mock data; akan diperkaya
// saat implementasi D1 penuh. Memverifikasi shell + design components dalam konteks app.
export default function DashboardPage() {
  return (
    <>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 700, letterSpacing: "-0.02em", margin: "0 0 0.25rem" }}>
          <span data-id>Beranda</span><span data-en>Dashboard</span>
        </h1>
        <p className="muted" style={{ margin: 0, fontSize: "var(--text-sm)" }}>
          <span data-id>Ringkasan produksi hari ini — channel Misteri Samudra.</span>
          <span data-en>Today&apos;s production overview — channel Misteri Samudra.</span>
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.875rem", marginBottom: "1.5rem" }}>
        <div className="kpi">
          <div className="kpi-label"><span data-id>Total Views</span><span data-en>Total Views</span></div>
          <div className="kpi-value">58.2K</div>
          <div className="kpi-delta up">▲ 2.3x</div>
        </div>
        <div className="kpi">
          <div className="kpi-label"><span data-id>Video Hari Ini</span><span data-en>Videos Today</span></div>
          <div className="kpi-value">5</div>
          <div className="kpi-delta up">▲ 12%</div>
        </div>
        <div className="kpi">
          <div className="kpi-label"><span data-id>Compliance</span><span data-en>Compliance</span></div>
          <div className="kpi-value">94</div>
          <div className="kpi-delta down">▼ 3</div>
        </div>
        <div className="kpi">
          <div className="kpi-label"><span data-id>Biaya AI (BYOK)</span><span data-en>AI Cost (BYOK)</span></div>
          <div className="kpi-value">$1.7</div>
          <div className="kpi-delta up">5 video</div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h2 className="card-title">
            <span data-id>Produksi terbaru</span><span data-en>Recent runs</span>
          </h2>
          <span className="badge badge-success"><span className="dot" />
            <span data-id>Scheduler aktif</span><span data-en>Scheduler active</span>
          </span>
        </div>
        <div className="card-body">
          <table className="tbl">
            <thead>
              <tr>
                <th>Topic</th><th>Niche</th><th>Status</th><th className="num">Views</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Kapal Hilang di Segitiga Bermuda</td>
                <td><span className="badge badge-brand">ocean_mysteries</span></td>
                <td><span className="badge badge-success"><span className="dot" />published</span></td>
                <td className="num">12.4K</td>
              </tr>
              <tr>
                <td>Misteri Suara di Palung Mariana</td>
                <td><span className="badge badge-brand">ocean_mysteries</span></td>
                <td><span className="badge badge-running"><span className="dot" />running</span></td>
                <td className="num">—</td>
              </tr>
              <tr>
                <td>Fakta Mengejutkan Tentang Galaksi</td>
                <td><span className="badge badge-brand">universe_mysteries</span></td>
                <td><span className="badge badge-warning"><span className="dot" />queued</span></td>
                <td className="num">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
