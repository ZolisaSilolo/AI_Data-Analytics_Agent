import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Plotly is dynamically imported by ChartViewer, so it is emitted as a
    // separate on-demand chunk (~4.6 MB) instead of blocking first paint.
    chunkSizeWarningLimit: 5000
  }
});
