import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the built SPA works behind nginx at the domain root.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { host: true, port: 5173 },
})
