import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

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
