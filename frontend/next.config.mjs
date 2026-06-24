const isDev = process.env.NODE_ENV === 'development';

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for production — FastAPI serves the `out/` directory as
  // static files on the same origin. No server-only features (no API routes,
  // no server actions). `output: export` is incompatible with rewrites, so it
  // is only applied for production builds.
  ...(isDev ? {} : { output: 'export' }),
  reactStrictMode: true,
  // next/image optimization requires a server; disable for static export.
  images: { unoptimized: true },
  // Trailing slashes keep static hosting path resolution predictable.
  trailingSlash: true,
  // Local-dev only: proxy `/api/*` to the FastAPI backend so the frontend can
  // run on :3000 while the backend runs on :8000. In production the static
  // export is served by FastAPI itself (same origin) and these rewrites are
  // unused. Set BACKEND_ORIGIN to override the target.
  ...(isDev
    ? {
        async rewrites() {
          const target = process.env.BACKEND_ORIGIN || 'http://localhost:8000';
          return [{ source: '/api/:path*', destination: `${target}/api/:path*` }];
        },
      }
    : {}),
};

export default nextConfig;
