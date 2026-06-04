import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the built SPA works behind nginx at the domain root.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { host: true, port: 5173 },
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
