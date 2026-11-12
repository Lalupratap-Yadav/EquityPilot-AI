import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev: the React app runs on :5173 and proxies API + WebSocket calls to FastAPI on :8000.
// Prod: `npm run build` emits web/dist, which FastAPI serves directly (single process).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, ws: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('lightweight-charts')) return 'charts'
          if (id.includes('recharts') || id.includes('d3-') || id.includes('victory-vendor')) return 'recharts'
          if (id.includes('node_modules')) return 'vendor'
        },
      },
    },
  },
})
