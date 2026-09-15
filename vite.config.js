import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// The farmer may be on a slow connection, an old Android phone, or none at all.
// The service worker caches the app shell and the last recommendation so the
// screen still shows something useful with no network.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Smart Irrigation',
        short_name: 'Paani',
        start_url: '/',
        display: 'standalone',
        background_color: '#0f1115',
        theme_color: '#3b82f6',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' }
        ]
      },
      workbox: {
        runtimeCaching: [
          {
            // The day's decision. Network first, but a cached copy is shown
            // rather than an error when the network is gone.
            urlPattern: /\/api\/today/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'today',
              expiration: { maxEntries: 8, maxAgeSeconds: 60 * 60 * 24 * 3 }
            }
          },
          {
            // Spoken audio, cached hard: the same script recurs for days and a
            // farmer tapping to listen again must not wait for a download.
            urlPattern: /\.mp3$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'speech',
              expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 24 * 30 }
            }
          }
        ]
      }
    })
  ]
})
