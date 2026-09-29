import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'node:path'

// Standalone Cortex app served by Frappe at /cortex (see www/cortex.py and website_route_rules in hooks.py).
// The frappe-ui plugin forwards /api, /assets, /login, /app... to the bench in development, injects the boot
// data (csrf_token, user) into the built index.html and copies it to www/cortex.html.
// Output: public/frontend/dist-spa -> /assets/cortex_rental/frontend/dist-spa/ (not versioned, see `npm run build:spa`).
export default defineConfig({
  plugins: [
    frappeui({
      frontendRoute: '/cortex',
      buildConfig: {
        outDir: 'dist-spa',
        baseUrl: '/assets/cortex_rental/frontend/dist-spa/',
        indexHtmlPath: path.resolve(__dirname, '../../www/cortex.html'),
        sourcemap: false
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
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['src/**/*.test.ts', 'src/**/*.spec.ts'],
    server: { deps: { inline: ['frappe-ui'] } },
    testTimeout: 60000
  }
})
