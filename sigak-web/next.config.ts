import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "sigak-production.up.railway.app",
      },
    ],
  },
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "sigak-web.vercel.app" }],
        destination: "https://www.sigak.asia/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
