import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://mathgraph.org',
  output: 'static',
  build: {
    assets: '_assets',
  },
  vite: {
    build: {
      assetsInlineLimit: 0,
    },
  },
});
