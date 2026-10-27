/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA is the canonical document served at the site root (/), so asset URLs
// are emitted root-relative. In dev the Vite server proxies /api to the local
// backend so the HttpOnly session cookie is same-origin.
export default defineConfig({
  base: "/",
  plugins: [react()],
  build: {
    outDir: "dist",
    // Content-hashed assets are immutable; index.html is served no-store by the
    // Reflex-free Python host that mounts this bundle at / (see
    // src/preconsult/host.py).
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
