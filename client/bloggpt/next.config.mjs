/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { dev }) => {
    // Webpack's on-disk pack cache can leave index entries pointing to
    // half-renamed *.pack.gz_ files on Windows. Use a per-process cache in
    // development to avoid ENOENT warnings while retaining fast recompiles.
    if (dev) {
      config.cache = { type: "memory" };
    }

    return config;
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "oaidalleapiprodscus.blob.core.windows.net",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
