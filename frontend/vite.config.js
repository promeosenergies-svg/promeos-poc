import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Cache isolé par worktree — sinon POC et refonte-sol2 (qui partagent
  // node_modules via symlink) écrivent dans le même .vite/deps ⇒ corruption
  // (Invalid hook call : 2 copies React optimisées concurrentes).
  cacheDir: 'node_modules/.vite-poc',
  server: {
    // Port 5173 — poc principal (la refonte audit-sol coexiste sur 5174).
    port: 5173,
    strictPort: true,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/openapi.json': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          maplibre: ['maplibre-gl'],
        },
      },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/__tests__/**/*.test.js'],
  },
});
