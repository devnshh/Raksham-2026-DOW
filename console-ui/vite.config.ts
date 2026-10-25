import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Built into the FastAPI app (served at /console); `npm run dev` proxies the API to the local backend.
export default defineConfig({
  base: '/console/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: { outDir: '../api/static/console', emptyOutDir: true },
  server: { proxy: { '/v1': 'http://127.0.0.1:8000', '/console/inter.ttf': 'http://127.0.0.1:8000' } },
})
