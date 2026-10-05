import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Trong Docker, API_PROXY_TARGET = http://api:8000; chạy tay ngoài Docker thì là localhost.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === 'true' },
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
