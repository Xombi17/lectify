// @ts-check

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Pin the workspace root to frontend/ so the standalone bundle is flat (server.js at the top).
  outputFileTracingRoot: import.meta.dirname,
  turbopack: { root: import.meta.dirname },
  async rewrites() {
    if (process.env.NODE_ENV === "production") {
      return [];
    }
    const backendUrl = process.env.DEV_BACKEND_URL || "http://localhost:8001";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  images: {
    unoptimized: false,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.pexels.com",
      },
    ],
  },
};

export default nextConfig;