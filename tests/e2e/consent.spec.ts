import { expect, test } from '@playwright/test'

/**
 * GDPR: no non-essential storage or tracking before an explicit opt-in. This is
 * the one behaviour on the site with legal consequences, so it is asserted on
 * the wire (was a request to GA made?) rather than on the UI alone.
 *
 * The dev server runs with PUBLIC_GA4_ID set (see playwright.config.ts), so the
 * GA snippet is actually present; without it these tests would pass vacuously.
 */

const CONSENT_KEY = 'cookie-consent'
const BANNER = '.cookie-banner'
const PRIMARY_BTN = '.cookie-banner__btn--primary'
const SECONDARY_BTN = '.cookie-banner__btn--secondary'

test.describe('cookie consent', () => {
  test('the banner appears on a first visit', async ({ page }) => {
    await page.goto('/')

    await expect(page.locator(BANNER)).toBeVisible()
  })

  test('no analytics request is made before consent', async ({ page }) => {
    const analyticsRequests: string[] = []
    page.on('request', (request) => {
      if (/googletagmanager|google-analytics/.test(request.url())) {
        analyticsRequests.push(request.url())
      }
    })

    await page.goto('/')
    await expect(page.locator(BANNER)).toBeVisible()

    // Consent Mode v2 defaults everything to denied, so the tag may load but
    // must not send a collect hit.
    expect(analyticsRequests.filter((url) => url.includes('/collect'))).toEqual([])
  })

  test('accepting persists granular consent and dismisses the banner', async ({ page }) => {
    await page.goto('/')
    await page.locator(PRIMARY_BTN).click()

    await expect(page.locator(BANNER)).toBeHidden()

    const stored = await page.evaluate((key) => localStorage.getItem(key), CONSENT_KEY)
    expect(stored).not.toBeNull()
    expect(JSON.parse(stored!)).toMatchObject({
      necessary: true,
      analytics: true,
      marketing: true,
    })
  })

  test('rejecting stores necessary-only consent', async ({ page }) => {
    await page.goto('/')
    await page.locator(SECONDARY_BTN).first().click()

    const stored = await page.evaluate((key) => localStorage.getItem(key), CONSENT_KEY)
    expect(JSON.parse(stored!)).toMatchObject({
      necessary: true,
      analytics: false,
      marketing: false,
    })
  })

  test('the decision survives a reload', async ({ page }) => {
    await page.goto('/')
    await page.locator(PRIMARY_BTN).click()
    await page.reload()

    await expect(page.locator(BANNER)).toBeHidden()
  })

  test('the footer button reopens preferences after a decision', async ({ page }) => {
    await page.goto('/')
    await page.locator(PRIMARY_BTN).click()
    await expect(page.locator(BANNER)).toBeHidden()

    await page.locator('#cookie-preferences-btn').click()

    await expect(page.locator(BANNER)).toBeVisible()
  })
})
