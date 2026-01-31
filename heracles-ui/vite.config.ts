import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      host: true,
      // Allow heracles.local domains for development
      allowedHosts: [
        'localhost',
        'ui.heracles.local',
        '.heracles.local',
      ],
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://api.heracles.local:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
