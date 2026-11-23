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
    rolldownOptions: {
      output: {
        // Explicit, prioritised groups. (The old manualChunks function let the recharts group capture React and clsx -
        // dependencies of recharts that the app shell also uses - so every first visit downloaded and parsed the whole
        // 440 KB chart library.) Higher priority claims a module first; libraries the first page needs ('$initial')
        // are claimed before the chart groups, so the chart libraries load only on pages that draw charts.
        codeSplitting: {
          groups: [
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/, priority: 40 },
            { name: 'vendor', test: /node_modules/, tags: ['$initial'], priority: 35 },
            { name: 'charts', test: /node_modules[\\/](lightweight-charts|fancy-canvas)[\\/]/, priority: 30 },
            { name: 'recharts', test: /node_modules[\\/](recharts|d3-[a-z-]+|victory-vendor|es-toolkit|react-redux|@reduxjs|immer|reselect|redux|redux-thunk|decimal\.js-light|eventemitter3|tiny-invariant|internmap)[\\/]/, priority: 20 },
          ],
        },
      },
    },
  },
})
