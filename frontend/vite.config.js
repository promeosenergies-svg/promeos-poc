import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Cache isolé par worktree — sinon le POC (worktree poc-main) et sol2
  // partagent node_modules/.vite/deps via symlink et corrompent le cache
  // (erreur "Invalid hook call" causée par 2 copies React optimisées).
  cacheDir: 'node_modules/.vite-sol2',
  server: {
    // Port 5175 — refonte-sol2 (branche claude/refonte-sol2, fork POC + skin Sol).
    // Règle figée 3 ports : POC=5173 (main), refonte audit-sol=5174, refonte-sol2=5175.
    // Backend partagé sur 8001. Ne jamais inverser — comparaison live des 3 UIs.
    port: 5175,
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
