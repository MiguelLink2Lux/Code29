import { expect, test, type Page } from '@playwright/test'

/**
 * The guided contact chat, end to end in a real browser.
 *
 * The backend and Cloudflare are both stubbed at the network boundary: these
 * specs are about what the visitor experiences — the fixed order of the flow,
 * the verification gate, and honest failure states — not about third parties.
 */

/** Serves a fake Turnstile that immediately hands back a token. */
async function stubTurnstile(page: Page) {
  await page.route('**/turnstile/v0/api.js*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: `window.turnstile = {
        render: function (container, options) {
          setTimeout(function () { options.callback('e2e-turnstile-token') }, 0)
          return 'widget-1'
        }
      }`,
    }),
  )
}

interface BackendStub {
  requestStatus?: number
  confirmStatus?: number
  reportStatus?: number
}

async function stubBackend(page: Page, stub: BackendStub = {}) {
  const calls: string[] = []

  await page.route('**/api/v1/contact/**', async (route) => {
    const url = route.request().url()
    calls.push(url)

    if (url.includes('verification/request')) {
      return route.fulfill({
        status: stub.requestStatus ?? 202,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'sent' }),
      })
    }

    if (url.includes('verification/confirm')) {
      const status = stub.confirmStatus ?? 200
      return route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(
          status === 200 ? { accessToken: 'e2e-token' } : { detail: 'invalid code' },
        ),
      })
    }

    return route.fulfill({
      status: stub.reportStatus ?? 202,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'sent' }),
    })
  })

  return calls
}

async function answerText(page: Page, value: string) {
  await page.locator('#contact input[type="text"]').fill(value)
  await page.locator('#contact button[type="submit"]').click()
}

async function answerChoice(page: Page) {
  await page.locator('#contact input[type="radio"]').first().check()
  await page.locator('#contact button[type="submit"]').click()
}

test.beforeEach(async ({ page }) => {
  await stubTurnstile(page)
})

test.describe('guided contact chat', () => {
  test('replaces the classic form in the contact section', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    await expect(page.locator('#contact .contact-chat')).toBeVisible()
    // The old form is gone, not hidden.
    await expect(page.locator('#contact input[name="fullName"]')).toHaveCount(0)
  })

  test('asks the questions in the fixed order and shows progress', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    await expect(page.locator('#contact')).toContainText(/1.*11/)
    await answerText(page, 'Ada Lovelace')
    await expect(page.locator('#contact')).toContainText(/2.*11/)
  })

  test('keeps the visitor on a step until the answer is valid', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    await page.locator('#contact button[type="submit"]').click()

    await expect(page.locator('#contact [role="alert"]')).toBeVisible()
    await expect(page.locator('#contact')).toContainText(/1.*11/)
  })

  test('never asks the backend for a code before the email is valid', async ({ page }) => {
    const calls = await stubBackend(page)
    await page.goto('/')

    await answerText(page, 'Ada Lovelace')
    await answerText(page, 'Analytical Engines')
    await answerText(page, 'not-an-email')

    expect(calls).toEqual([])
    await expect(page.locator('#contact [role="alert"]')).toBeVisible()
  })

  test('solves the human challenge and requests a code once the email is valid', async ({
    page,
  }) => {
    const calls = await stubBackend(page)
    await page.goto('/')

    await answerText(page, 'Ada Lovelace')
    await answerText(page, 'Analytical Engines')
    await answerText(page, 'ada@example.com')

    await expect
      .poll(() => calls.filter((url) => url.includes('verification/request')).length)
      .toBe(1)
  })

  test('walks the whole flow and confirms the report was sent', async ({ page }) => {
    const calls = await stubBackend(page)
    await page.goto('/')

    await answerText(page, 'Ada Lovelace')
    await answerText(page, 'Analytical Engines')
    await answerText(page, 'ada@example.com')
    await expect.poll(() => calls.length).toBeGreaterThan(0)

    await answerText(page, '123456')
    await answerChoice(page)
    await answerChoice(page)
    await answerChoice(page)
    await answerChoice(page)
    await answerChoice(page)
    await answerText(page, 'example.com')

    await page.locator('#contact input[type="checkbox"]').check()
    await page.locator('#contact button[type="submit"]').click()

    await expect(page.locator('#contact [role="status"]')).toBeVisible()
    expect(calls.some((url) => url.includes('/contact/report'))).toBe(true)
  })

  test('a rejected code keeps the visitor on the code step', async ({ page }) => {
    await stubBackend(page, { confirmStatus: 400 })
    await page.goto('/')

    await answerText(page, 'Ada Lovelace')
    await answerText(page, 'Analytical Engines')
    await answerText(page, 'ada@example.com')
    await answerText(page, '123456')

    await expect(page.locator('#contact [role="alert"]')).toBeVisible()
    await expect(page.locator('#contact')).toContainText(/4.*11/)
  })

  test('an unconfigured backend reads as unavailable, not as the visitor’s fault', async ({
    page,
  }) => {
    await stubBackend(page, { requestStatus: 503 })
    await page.goto('/')

    await answerText(page, 'Ada Lovelace')
    await answerText(page, 'Analytical Engines')
    await answerText(page, 'ada@example.com')

    await expect(page.locator('#contact [role="alert"]')).toContainText(
      /no está disponible|unavailable/i,
    )
  })

  test('a failed delivery is never reported as success', async ({ page }) => {
    const calls = await stubBackend(page, { reportStatus: 502 })
    await page.goto('/')

    await answerText(page, 'Ada Lovelace')
    await answerText(page, 'Analytical Engines')
    await answerText(page, 'ada@example.com')
    await expect.poll(() => calls.length).toBeGreaterThan(0)
    await answerText(page, '123456')
    await answerChoice(page)
    await answerChoice(page)
    await answerChoice(page)
    await answerChoice(page)
    await answerChoice(page)
    await answerText(page, 'example.com')
    await page.locator('#contact input[type="checkbox"]').check()
    await page.locator('#contact button[type="submit"]').click()

    await expect(page.locator('#contact [role="alert"]')).toBeVisible()
    await expect(page.locator('#contact [role="status"]')).toHaveCount(0)
  })

  test('in-progress answers survive a reload within the tab', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    await answerText(page, 'Ada Lovelace')
    await page.reload()

    // sessionStorage keeps the flow; the visitor does not start over.
    await expect(page.locator('#contact')).toContainText(/2.*11/)
  })
})
