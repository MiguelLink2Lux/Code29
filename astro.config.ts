import { defineConfig } from 'astro/config'
import sitemap from '@astrojs/sitemap'
import vue from '@astrojs/vue'
import vercel from '@astrojs/vercel/serverless'

import { resolveSiteUrl } from './src/utils/seo'

// `site` is required by @astrojs/sitemap to emit absolute URLs. It comes from
// the same resolver the pages use, so origin lives in exactly one place.
// process.env is the config-time source: import.meta.env is not populated here.
const site = resolveSiteUrl(process.env)

// https://astro.build/config
export default defineConfig({
  site,
  // The dev toolbar injects its own h1/landmark elements, which collide with
  // strict-mode locators in the e2e suite. Disabled when Playwright starts the
  // server; on by default for normal development.
  devToolbar: { enabled: process.env.ASTRO_DEV_TOOLBAR !== 'false' },
  integrations: [
    vue(),
    sitemap({
      // Status pages must stay out of the index: they are either error states or
      // placeholders, and indexing them competes with the real landing page.
      filter: (page) =>
        !['/404', '/maintenance/', '/coming-soon/'].some((excluded) =>
          new URL(page).pathname.startsWith(excluded),
        ),
    }),
  ],
  output: 'hybrid',
  adapter: vercel(),
  redirects: {
    '/mantenimiento': '/maintenance',
    '/aviso-legal': '/legal-notice',
    '/privacidad': '/privacy-policy',
  },
})
