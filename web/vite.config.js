import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../public',
    emptyOutDir: true
  },
  server: {
    host: true, // Listen on all network interfaces
    port: parseInt(process.env.PORT || '10051'),
    proxy: {
      '/api': {
        target: process.env.API_URL || 'http://localhost:10050',
        changeOrigin: true
      }
    }
  }
})
