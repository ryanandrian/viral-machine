import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    // /demo → /showcase (2026-07-03): halaman demo lama dihapus (iframe internal = layar login utk calon tenant).
    return [{ source: "/demo", destination: "/showcase", permanent: true }];
  },
};

export default nextConfig;
