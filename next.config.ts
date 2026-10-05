import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: ["100.79.72.59"],
  reactCompiler: true,
  experimental: {
    // Uploads de vídeo passam pelo rewrite proxy (/api -> FastAPI).
    // Sem isto, o proxy do Next barra o corpo (~10MB) e estoura o timeout
    // (~30s), causando 500/socket hang up em vídeos. Elevamos ambos.
    proxyClientMaxBodySize: 500 * 1024 * 1024, // 500MB
    proxyTimeout: 900_000, // 15 min, alinhado ao AbortController do frontend
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
