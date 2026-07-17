import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { compression } from 'vite-plugin-compression2'
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VueI18nPlugin({
      include: [
        path.resolve(path.dirname(fileURLToPath(import.meta.url)), './src/locales/**'),
      ],
      runtimeOnly: true,
    }),
    compression({ algorithms: ['gzip', 'brotliCompress'] }),
  ],
  server: {
    port: 3000,
    host: true,
    open: false,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false
      }
    }
  },
  // `vite preview` mode (production static serve) — bind 0.0.0.0:3000,
  // permettre tous les hosts (Cloudflare tunnel domain) et proxy /api vers
  // le backend Flask local. Utilisé par le CMD docker `npm run start`.
  preview: {
    port: 3000,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'd3': ['d3'],
          'vue-vendor': ['vue', 'vue-router'],
          'data-vendor': ['@supabase/supabase-js', 'axios'],
          'i18n-vendor': ['pinia', 'vue-i18n'],
          'i18n-locales': [
            './src/locales/ar.json',
            './src/locales/en.json',
            './src/locales/fr.json',
          ],
          'codemirror-editor': [
            '@codemirror/commands',
            '@codemirror/lang-markdown',
            '@codemirror/state',
            '@codemirror/view',
          ],
          'tiptap-editor': [
            '@tiptap/extension-placeholder',
            '@tiptap/starter-kit',
            '@tiptap/vue-3',
          ],
          'markdown-vendor': ['dompurify', 'marked'],
        }
      }
    }
  }
})
