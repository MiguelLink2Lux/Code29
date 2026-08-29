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

test.describe('the closing block', () => {
  test('contact and footer share one container, with no seam between them', async ({ page }) => {
    await page.goto('/')

    const closing = page.locator('.closing')
    await expect(closing).toHaveCount(1)

    // Both inside the same container: that is what removes the seam. The
    // decoration used to be duplicated in each, with divergent opacities and
    // two unsynchronised animations, and the join showed.
    await expect(closing.locator('#contact')).toHaveCount(1)
    await expect(closing.locator('footer')).toHaveCount(1)
  })

  test('the chat stays out of the footer landmark', async ({ page }) => {
    await page.goto('/')

    // Visually one block, semantically not: a chat inside contentinfo is a chat
    // that landmark navigation hides, and #contact is where three CTAs point.
    await expect(page.locator('footer .conversation')).toHaveCount(0)
    await expect(page.getByRole('contentinfo')).toHaveCount(1)
    await expect(page.locator('#contact .conversation')).toBeVisible()
  })

  test('the nav CTA still reaches the contact section', async ({ page }) => {
    await page.goto('/')

    await page.locator('.nav__cta').click()

    await expect(page.locator('#contact')).toBeInViewport()
  })

  test('legal pages get the footer without the closing decoration', async ({ page }) => {
    await page.goto('/legal-notice')

    // Animated grid behind a legal text is noise. The closing container is a
    // home-page thing.
    await expect(page.locator('.closing')).toHaveCount(0)
    await expect(page.getByRole('contentinfo')).toHaveCount(1)
  })
})
