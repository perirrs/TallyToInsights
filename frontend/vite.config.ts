import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Browser (Azure SWA / dev): serve from root '/'
  // Electron build: relative paths './'
  base: command === 'build' && process.env.VITE_DEPLOY_TARGET === 'electron' ? './' : '/',
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
}))
