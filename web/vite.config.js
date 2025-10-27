import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// Read version from VERSION file
const version = readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString())
  },
  build: {
    outDir: '../public',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Enhanced cache busting with version
        entryFileNames: `assets/[name]-${version}-[hash].js`,
        chunkFileNames: `assets/[name]-${version}-[hash].js`,
        assetFileNames: (assetInfo) => {
          const ext = assetInfo.name.split('.').pop()
          if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico'].includes(ext)) {
            return `assets/images/[name]-${version}-[hash].[ext]`
          }
          if (['css'].includes(ext)) {
            return `assets/[name]-${version}-[hash].css`
          }
          return `assets/[name]-${version}-[hash].[ext]`
        }
      }
    }
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
