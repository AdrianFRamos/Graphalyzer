import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// O build sai direto no pacote Python, que é quem serve o dashboard.
const OUT_DIR = fileURLToPath(new URL('../src/graphalyzer/web', import.meta.url))

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'Graphalyzer',
        short_name: 'Graphalyzer',
        description: 'Grafo de dependências e fluxo de dados de projetos Python',
        lang: 'pt-BR',
        theme_color: '#1e293b',
        background_color: '#0f172a',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Cytoscape é grande; o shell inteiro precisa caber no precache para
        // o app abrir offline.
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        // A API é local e volátil: nunca serve resposta velha como se fosse
        // atual. Offline, o app usa o último grafo salvo no próprio dispositivo.
        navigateFallbackDenylist: [/^\/api/, /^\/docs/, /^\/health/, /^\/static/],
        runtimeCaching: [
          {
            urlPattern: /\/api\/.*/,
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: {
    outDir: OUT_DIR,
    emptyOutDir: true,
  },
  server: {
    // `npm run dev` fala com a API Python rodando em paralelo
    proxy: { '/api': 'http://127.0.0.1:5000' },
  },
})
