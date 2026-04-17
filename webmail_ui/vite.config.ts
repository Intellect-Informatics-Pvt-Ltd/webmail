// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, cloudflare (build-only),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    VitePWA({
      /**
       * We register the SW manually in __root.tsx via registerSW() so that:
       * - We control the update prompt lifecycle.
       * - No automatic HTML injection (TanStack Start generates HTML server-side).
       */
      injectRegister: null,
      registerType: "prompt",

      /**
       * injectManifest: we write src/sw.ts; Workbox injects the precache manifest.
       * This gives us full control over routing, background sync, and push handlers.
       */
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",

      /**
       * The compiled SW lands at dist/client/sw.js — served at /sw.js by
       * Cloudflare Pages which treats dist/client/ as the public root.
       */
      outDir: "dist/client",

      injectManifest: {
        // Match the hashed client assets emitted by TanStack Start / Vite.
        globDirectory: "dist/client",
        globPatterns: ["assets/**/*.{js,css,woff2,ico,png,svg,webp}"],
        // Exclude server chunks and chunked source maps to keep the manifest lean.
        globIgnores: ["**/node_modules/**", "sw.js", "**/*.map"],
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024, // 4 MB cap per file
      },

      // Web App Manifest — makes the app installable.
      manifest: {
        name: "PSense Mail",
        short_name: "PSense Mail",
        description: "PSense enterprise mail workspace",
        theme_color: "#4f46e5", // indigo-600 — aligns with --color-primary token
        background_color: "#ffffff",
        display: "standalone",
        scope: "/",
        start_url: "/",
        orientation: "portrait-primary",
        icons: [
          {
            src: "/icons/icon-192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any maskable",
          },
          {
            src: "/icons/icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any maskable",
          },
        ],
      },

      // Dev mode: serve a no-op SW in development so the plugin doesn't break HMR.
      devOptions: {
        enabled: false,
      },
    }),
  ],
});
