/** @type {import('next').NextConfig} */
const nextConfig = {
  // The retrieval engine is a separate Python backend; the Next.js app is just the
  // Aletheia UI + a thin /api/ask proxy. No native server packages, no bundled index.
};
export default nextConfig;
