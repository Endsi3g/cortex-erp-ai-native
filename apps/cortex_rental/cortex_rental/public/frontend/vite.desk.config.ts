import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import tailwindcss from 'tailwindcss'
import autoprefixer from 'autoprefixer'
import path from 'node:path'
import { createRequire } from 'node:module'
import tailwindDeskConfig from './tailwind.desk.config'

const require = createRequire(import.meta.url)
const scopeCortexRoot = require('./postcss/scope-cortex-root.cjs')

// Builds the screens as one ES module loaded by Desk Pages (see public/js/cortex_host/cortex_host.js).
// Output: public/frontend/dist-desk -> /assets/cortex_rental/frontend/dist-desk/cortex-desk.js
export default defineConfig({
  plugins: [frappeui({ frappeProxy: false, jinjaBootData: false, buildConfig: false }), vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@locales': path.resolve(__dirname, './locales'),
      'tailwindcss/plugin': path.resolve(__dirname, './node_modules/tailwindcss/plugin.js')
    }
  },
  css: {
    postcss: { plugins: [tailwindcss(tailwindDeskConfig), autoprefixer(), scopeCortexRoot()] }
  },
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    outDir: 'dist-desk',
    emptyOutDir: true,
    sourcemap: false,
    cssCodeSplit: false,
    lib: { entry: path.resolve(__dirname, 'src/desk/entry.ts'), formats: ['es'], fileName: () => 'cortex-desk.js' },
    rollupOptions: {
      output: { chunkFileNames: 'chunks/[name]-[hash].js', assetFileNames: (asset) => (asset.name?.endsWith('.css') ? 'cortex-desk.css' : 'assets/[name]-[hash][extname]') }
    }
  }
})
