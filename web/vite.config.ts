import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "DeliveryGram",
        short_name: "DeliveryGram",
        description: "Order from shops in your village",
        lang: "hi",
        start_url: "/",
        display: "standalone",
        background_color: "#f7faf7",
        theme_color: "#15803d",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/images\//],
        runtimeCaching: [
          // Shop lists and items: show the last good copy when the network is slow or gone.
          { urlPattern: ({ url }) => url.pathname.startsWith("/api/") && !url.pathname.includes("/auth/"), method: "GET",
            handler: "NetworkFirst", options: { cacheName: "api", networkTimeoutSeconds: 6, expiration: { maxEntries: 150, maxAgeSeconds: 7 * 86400 } } },
          { urlPattern: ({ url }) => url.pathname.startsWith("/images/"), handler: "CacheFirst",
            options: { cacheName: "item-images", expiration: { maxEntries: 400, maxAgeSeconds: 30 * 86400 } } },
        ],
      },
    }),
  ],
  server: {
    proxy: { "/api": "http://localhost:8000", "/images": "http://localhost:8000" },
  },
  test: { environment: "node" },
});
