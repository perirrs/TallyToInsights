import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // VITE_DEPLOY_TARGET=github-pages   → GitHub Pages  (base = /TallyToInsights/)
  // VITE_DEPLOY_TARGET=electron        → Electron build (base = ./)
  // (dev / unset)                      → local dev     (base = /)
  const deployTarget = env.VITE_DEPLOY_TARGET || (command === 'build' ? 'electron' : 'dev')
  const base =
    deployTarget === 'github-pages' ? '/TallyToInsights/' :
    deployTarget === 'electron'     ? './'                :
                                      '/'

  return {
    plugins: [react()],
    base,
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
