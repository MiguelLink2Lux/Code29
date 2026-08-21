import { expect, test, type Page } from '@playwright/test'

// The initial language depends on the browser locale (the test browser is en-US),
// so these assertions are written relative to whatever is on screen rather than
// assuming Spanish. That asymmetry is exactly what hid the first-click bug.

const otherLang = (lang: string) => (lang === 'en' ? 'es' : 'en')

const currentLang = (page: Page) => page.locator('html').getAttribute('lang')

test.describe('language switcher', () => {
  test('one click switches the copy and the html lang attribute', async ({ page }) => {
    await page.goto('/')

    const before = (await currentLang(page)) ?? 'es'
    const heroBefore = await page.locator('#hero').innerText()

    await page.locator('#lang-switcher').click()

    // Regression: the handler used to read an empty localStorage and re-apply
    // the language already on screen, so the first click was a no-op for every
    // visitor arriving with a non-Spanish browser.
    await expect(page.locator('html')).toHaveAttribute('lang', otherLang(before))
    await expect(page.locator('#hero')).not.toHaveText(heroBefore)
  })

  test('two clicks return to the original language', async ({ page }) => {
    await page.goto('/')
    const before = (await currentLang(page)) ?? 'es'

    await page.locator('#lang-switcher').click()
    await page.locator('#lang-switcher').click()

    await expect(page.locator('html')).toHaveAttribute('lang', before)
  })

  test('the choice is remembered across a reload', async ({ page }) => {
    await page.goto('/')
    const before = (await currentLang(page)) ?? 'es'

    await page.locator('#lang-switcher').click()
    const switched = otherLang(before)
    await expect(page.locator('html')).toHaveAttribute('lang', switched)

    await page.reload()

    await expect(page.locator('html')).toHaveAttribute('lang', switched)
  })

  test('switching does not change the URL', async ({ page }) => {
    // Deliberate design decision (docs/architecture/i18n.md): one URL per page.
    await page.goto('/')
    const before = page.url()

    await page.locator('#lang-switcher').click()

    expect(page.url()).toBe(before)
  })
})

test.describe('contact form', () => {
  /** Fills the form, asserting each value landed in Vue's model before moving on. */
  async function fill(page: Page, email: string) {
    const values: Array<[string, string]> = [
      ['input[name="fullName"]', 'Ada Lovelace'],
      ['input[name="company"]', 'Analytical Engines'],
      ['input[name="email"]', email],
      ['textarea[name="message"]', 'I need a CTO as a service for a six-month engagement.'],
    ]

    for (const [selector, value] of values) {
      const field = page.locator(`#contact ${selector}`)
      await field.fill(value)
      await expect(field).toHaveValue(value)
    }
  }

  test('an invalid email never reaches the API', async ({ page }) => {
    let posted = false
    await page.route('**/api/contact', async (route) => {
      posted = true
      await route.fulfill({ status: 200, body: '{"ok":true}' })
    })

    await page.goto('/')
    await fill(page, 'not-an-email')
    await page.locator('#contact button[type="submit"]').click()

    expect(posted, 'client-side validation must block the request').toBe(false)
    await expect(page.locator('#contact-email-error')).toBeVisible()
  })

  test('a valid submission is confirmed to the visitor', async ({ page }) => {
    await page.route('**/api/contact', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{"ok":true}',
      }),
    )

    await page.goto('/')
    await fill(page, 'ada@example.com')
    await page.locator('#contact button[type="submit"]').click()

    await expect(page.locator('.contact-form__feedback--success')).toBeVisible()
  })

  test('a misconfigured backend surfaces an error instead of failing silently', async ({
    page,
  }) => {
    // 503 is what POST /api/contact returns when the Resend env vars are absent
    // — exactly the state of a fresh deploy before they are set.
    await page.route('**/api/contact', (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: '{"error":"Missing required environment variable: RESEND_API_KEY"}',
      }),
    )

    await page.goto('/')
    await fill(page, 'ada@example.com')
    await page.locator('#contact button[type="submit"]').click()

    const error = page.locator('.contact-form__feedback--error')
    await expect(error).toBeVisible()
    await expect(error).toHaveAttribute('role', 'alert')
  })

  test('the honeypot is hidden from real visitors and from autofill', async ({ page }) => {
    await page.goto('/')

    // Regression: it used to be a 1x1 clipped field — focusable and autofillable,
    // so a password manager could silently flag a real message as spam.
    await expect(page.locator('#contact input[name="website"]')).toBeHidden()
  })
})
