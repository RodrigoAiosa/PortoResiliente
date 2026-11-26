import type { NextConfig } from "next";

// Em desenvolvimento local, use `vercel dev` para servir Next.js e a API Python juntos.
// Alternativa: defina API_PROXY=http://localhost:8000 e rode `uvicorn api.index:app`.
const proxy = process.env.API_PROXY;

const config: NextConfig = {
  async rewrites() {
    return proxy ? [{ source: "/api/:path*", destination: `${proxy}/api/:path*` }] : [];
  },
};

export default config;
