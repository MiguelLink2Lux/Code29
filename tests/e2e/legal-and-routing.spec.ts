import { expect, test } from '@playwright/test'

// GDPR/LSSI pages are a legal requirement, and the Spanish legacy paths were
// public before the rename — a broken redirect is a broken obligation.

const LEGAL_ROUTES = ['/legal-notice', '/privacy-policy', '/cookies']

const LEGACY_REDIRECTS: Array<[string, string]> = [
  ['/mantenimiento', '/maintenance'],
  ['/aviso-legal', '/legal-notice'],
  ['/privacidad', '/privacy-policy'],
]

test.describe('legal pages', () => {
  for (const route of LEGAL_ROUTES) {
    test(`${route} responds with readable content`, async ({ page }) => {
      const response = await page.goto(route)

      expect(response?.status()).toBe(200)
      await expect(page.locator('h1')).toBeVisible()
      // Guard against an empty shell: a legal page with no text is not compliance.
      expect((await page.locator('main, body').first().innerText()).length).toBeGreaterThan(200)
    })
  }
})

test.describe('legacy redirects', () => {
  for (const [from, to] of LEGACY_REDIRECTS) {
    test(`${from} redirects to ${to}`, async ({ page }) => {
      await page.goto(from)

      expect(new URL(page.url()).pathname.replace(/\/$/, '')).toBe(to)
    })
  }
})

test.describe('error handling', () => {
  test('an unknown route renders the 404 page, not a blank screen', async ({ page }) => {
    const response = await page.goto('/this-route-does-not-exist')

    expect(response?.status()).toBe(404)
    await expect(page.locator('body')).toContainText(/404/)
  })
})
