import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'fs'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    https: fs.existsSync('/certs/key.pem')
      ? {
          key: fs.readFileSync('/certs/key.pem'),
          cert: fs.readFileSync('/certs/cert.pem'),
        }
      : undefined,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
