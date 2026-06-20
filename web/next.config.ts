import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // pg usa APIs Node.js nativas — não deve ser empacotado pelo bundler
  serverExternalPackages: ['pg', 'pg-native'],
};

export default nextConfig;
