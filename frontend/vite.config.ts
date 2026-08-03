/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the built SPA works behind nginx at the domain root.
// Data files under /data are served with a 24h max-age at stable URLs, so a
// deploy that adds a REQUIRED field (night_class did) would hand returning
// visitors a stale file and silently drop the sections that need it. Versioning
// the data URLs per build is what makes a deploy actually take effect.
const DATA_VERSION = Date.now().toString(36)

export default defineConfig({
  base: './',
  define: { __DATA_VERSION__: JSON.stringify(DATA_VERSION) },
  plugins: [react()],
  server: { host: true, port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // keep the heavy map stack out of the entry chunk (it's lazy-loaded with FlightMap)
        manualChunks: {
          maplibre: ['maplibre-gl'],
          deck: ['@deck.gl/core', '@deck.gl/layers', '@deck.gl/geo-layers', '@deck.gl/mapbox'],
        },
      },
    },
  },
})
