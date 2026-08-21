import { expect, test } from '@playwright/test'

// The landing page is the product. These assertions are deliberately about
// structure rather than copy: copy lives in translations.ts and changes often.

test.describe('landing page', () => {
  test('renders every section of the MVP', async ({ page }) => {
    await page.goto('/')

    for (const id of ['hero', 'stats', 'stack', 'services', 'testimonials', 'contact']) {
      await expect(page.locator(`#${id}`)).toBeVisible()
    }
    // Toolbelt has no id; it is identified by its landmark role.
    await expect(page.locator('section.toolbelt')).toBeVisible()
  })

  test('exposes a single h1 and a document title', async ({ page }) => {
    await page.goto('/')

    await expect(page.locator('h1')).toHaveCount(1)
    await expect(page).toHaveTitle(/code29|miguel|cto/i)
  })

  test('ships the icons and an absolute og:image', async ({ page }) => {
    await page.goto('/')

    await expect(page.locator('link[rel="icon"][href="/favicon.svg"]')).toHaveCount(1)
    const ogImage = await page.locator('meta[property="og:image"]').getAttribute('content')
    expect(ogImage).toMatch(/^https?:\/\//)
  })

  test('serves the og-image and favicon without a 404', async ({ request }) => {
    for (const asset of ['/og-image.png', '/favicon.svg', '/apple-touch-icon.png']) {
      expect((await request.get(asset)).status(), asset).toBe(200)
    }
  })

  test('robots.txt declares an absolute sitemap URL', async ({ request }) => {
    const robots = await (await request.get('/robots.txt')).text()
    const match = robots.match(/Sitemap:\s*(\S+)/)

    expect(match, 'robots.txt must declare a sitemap').not.toBeNull()
    expect(match![1]).toMatch(/^https?:\/\/\S+\/sitemap-index\.xml$/)
    // That the file is actually emitted is asserted against the build output in
    // tests/artifacts: the sitemap integration only runs on build, not in dev.
  })
})
