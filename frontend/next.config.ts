import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Required for Docker/Cloud Run deployment
  output: "standalone",
};

export default nextConfig;
