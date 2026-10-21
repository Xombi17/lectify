// @ts-check

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",

  // Pin the workspace root to frontend/ so the standalone bundle is flat.
  // This keeps server.js at the top of the standalone bundle.
  outputFileTracingRoot: import.meta.dirname,

  turbopack: {
    root: import.meta.dirname,
  },

  // Allow the ngrok domain to access Next.js development resources.
  allowedDevOrigins: [
    "catchier-reynaldo-noneuphoniously.ngrok-free.dev",
  ],

  async rewrites() {
    if (process.env.NODE_ENV === "production") {
      return [];
    }

    const backendUrl =
      process.env.DEV_BACKEND_URL || "http://localhost:8001";

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