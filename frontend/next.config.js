/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    return [
      { source: "/api/:path*", destination: api + "/api/:path*" },
      { source: "/share/:path*", destination: api + "/share/:path*" },
    ];
  },
};
module.exports = nextConfig;
