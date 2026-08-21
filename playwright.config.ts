import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4321',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Start the dev server before running tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:4321',
    reuseExistingServer: !process.env.CI,
    env: {
      // Without a GA4 id the analytics snippet renders nothing, and the consent
      // assertions would pass vacuously. A dummy id makes them real.
      PUBLIC_GA4_ID: process.env.PUBLIC_GA4_ID ?? 'G-E2ETESTID',
      // The dev toolbar adds its own h1/landmarks and breaks strict locators.
      ASTRO_DEV_TOOLBAR: 'false',
    },
  },
})
