import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Base path where the assets will be served from in Joomla
  base: '/sonobot/',
  build: {
    rollupOptions: {
      output: {
        // Fixed filenames — no hashes — so Joomla module doesn't break on rebuild
        entryFileNames: 'sonobot.js',
        chunkFileNames:  'sonobot-chunk.js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith('.css')) return 'sonobot.css';
          return assetInfo.name ?? 'asset';
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
