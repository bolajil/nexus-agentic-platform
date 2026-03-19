/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8003',
  },
  experimental: {
    turbo: {
      root: __dirname,
    },
  },
};

module.exports = nextConfig;
