import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // [2026-07-11] Upload showcase video 12MB gagal "form-data tidak valid": Next canary membatasi body
  // request yang melewati middleware (proxy) dgn `proxyClientMaxBodySize` DEFAULT 10MB (config-shared.js:260;
  // ambang direproduksi empiris: 8MB lolos, 10MB gagal). Naikkan ke 100MB = selaras nginx client_max_body_size
  // 100m; batas per-jenis file tetap ditegakkan route upload (video 80MB / screen 5MB / poster 3MB).
  experimental: {
    proxyClientMaxBodySize: 100 * 1024 * 1024,
  },
  async redirects() {
    // /demo → /showcase (2026-07-03): halaman demo lama dihapus (iframe internal = layar login utk calon tenant).
    return [{ source: "/demo", destination: "/showcase", permanent: true }];
  },
};

export default nextConfig;
