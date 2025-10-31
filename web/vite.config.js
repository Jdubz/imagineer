import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { visualizer } from 'rollup-plugin-visualizer'
import { compression } from 'vite-plugin-compression2'

const __dirname = dirname(fileURLToPath(import.meta.url))

// Read version from VERSION file
const version = readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()

export default defineConfig(({ mode }) => ({
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  plugins: [
    react(),
    // Bundle analyzer - generates stats.html after build
    mode === 'production' && visualizer({
      filename: '../public/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
    // Compression - generates .gz and .br files for production
    mode === 'production' && compression({
      algorithm: 'gzip',
      exclude: [/\.(br|gz)$/, /\.map$/],
    }),
    mode === 'production' && compression({
      algorithm: 'brotliCompress',
      exclude: [/\.(br|gz)$/, /\.map$/],
    }),
  ].filter(Boolean),
  define: {
    __APP_VERSION__: JSON.stringify(version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString())
  },
  build: {
    outDir: '../public',
    emptyOutDir: true,
    // Enable source maps for production debugging (optional)
    sourcemap: mode === 'production' ? 'hidden' : true,
    // Set chunk size warning limit to 1000kb
    chunkSizeWarningLimit: 1000,
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
        },
        // Use Vite's default chunking strategy to avoid circular vendor splits
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
}))
