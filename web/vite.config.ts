/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA is served under /next in the single production image, so every
// emitted asset URL must be prefixed. In dev the Vite server proxies /api to
// the local backend so the HttpOnly session cookie is same-origin.
export default defineConfig({
  base: "/next/",
  plugins: [react()],
  build: {
    outDir: "dist",
    // Content-hashed assets are immutable; index.html is served no-store by the
    // FastAPI /next mount (see reflex_app/preconsult/preconsult.py).
    assetsDir: "assets",
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
