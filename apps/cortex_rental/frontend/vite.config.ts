import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'node:path'

export default defineConfig({
  plugins: [
    frappeui({
      frontendRoute: '/cortex',
      frappeProxy: false,
      jinjaBootData: true,
      buildConfig: {
        outDir: path.resolve(__dirname, '../cortex_rental/public/frontend'),
        indexHtmlPath: path.resolve(__dirname, '../cortex_rental/www/cortex.html'),
        baseUrl: '/assets/cortex_rental/frontend/'
      }
    }),
    vue()
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@locales': path.resolve(__dirname, './locales'),
      'tailwindcss/plugin': path.resolve(__dirname, './node_modules/tailwindcss/plugin.js')
    }
  },
  optimizeDeps: {
    // frappe-ui imports Feather Icons as CommonJS from its source .vue files;
    // the dev toolchain also imports debug's CommonJS browser entry directly.
    // Prebundle both so Vite supplies the default interop exports they expect.
    include: ['feather-icons', 'debug', 'debug/src/browser.js'],
    exclude: ['frappe-ui']
  },
  server: {
    port: 5173,
    host: true,
    strictPort: true,
    proxy: {
      '/api': { target: process.env.FRAPPE_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true },
      '/assets': { target: process.env.FRAPPE_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true }
    }
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['src/**/*.test.ts', 'src/**/*.spec.ts'],
    server: { deps: { inline: ['frappe-ui'] } },
    testTimeout: 60000
  }
})
