import { expect, test, type Page } from '@playwright/test'

/**
 * The conversational contact flow, end to end in a real browser.
 *
 * The backend and Cloudflare are stubbed at the network boundary: what is under
 * test is what the visitor experiences — a conversation that gathers facts,
 * verifies an address, and ends with a report actually being requested. That
 * last part is the one that matters: a chat that gathers everything and delivers
 * nothing would be worse than the questionnaire it replaced.
 */

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
  completeAfter?: number
  reportStatus?: number
  turnStatus?: number
}

async function stubBackend(page: Page, stub: BackendStub = {}) {
  const calls: string[] = []
  let turns = 0
  const completeAfter = stub.completeAfter ?? 2

  await page.route('**/api/v1/contact/**', async (route) => {
    const url = route.request().url()
    calls.push(url)

    if (url.includes('/conversation/turn')) {
      turns += 1
      const complete = turns >= completeAfter
      return route.fulfill({
        status: stub.turnStatus ?? 200,
        contentType: 'application/json',
        body: JSON.stringify({
          reply: complete ? 'Con esto tengo suficiente.' : '¿En qué empresa trabajas?',
          envelope: `env-${turns}`,
          complete,
          exhausted: false,
          missing: complete ? [] : ['company', 'email'],
        }),
      })
    }

    if (url.includes('verification/request')) {
      return route.fulfill({ status: 202, contentType: 'application/json', body: '{}' })
    }

    if (url.includes('verification/confirm')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ accessToken: 'e2e-token' }),
      })
    }

    return route.fulfill({
      status: stub.reportStatus ?? 200,
      contentType: 'application/json',
      body: JSON.stringify({ delivered: true, title: 'Diagnóstico', summary: 'ok' }),
    })
  })

  return calls
}

const composer = (page: Page) => page.locator('#contact textarea, #contact input[type="text"]').first()

async function say(page: Page, text: string) {
  await composer(page).fill(text)
  await page.locator('#contact button[type="submit"]').first().click()
}

test.beforeEach(async ({ page }) => {
  await stubTurnstile(page)
})

test.describe('conversational contact', () => {
  test('replaces the questionnaire in the contact section', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    await expect(page.locator('#contact .conversation')).toBeVisible()
    // The eleven-step questionnaire is gone, not hidden.
    await expect(page.locator('#contact input[type="radio"]')).toHaveCount(0)
  })

  test('answers with the bot reply and keeps the thread', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    await say(page, 'hola, soy Ada')

    await expect(page.locator('#contact')).toContainText('¿En qué empresa trabajas?')
    await expect(page.locator('#contact')).toContainText('hola, soy Ada')
  })

  test('never sends an empty message to the backend', async ({ page }) => {
    const calls = await stubBackend(page)
    await page.goto('/')

    await page.locator('#contact button[type="submit"]').first().click()

    expect(calls.filter((url) => url.includes('/conversation/turn'))).toHaveLength(0)
  })

  test('asks for the report once the conversation completes and the email is verified', async ({
    page,
  }) => {
    const calls = await stubBackend(page, { completeAfter: 1 })
    await page.goto('/')

    await say(page, 'soy Ada de Analytical Engines, ae.example, somos tres')

    // The email thread appears; verifying it is what unlocks the report.
    const emailField = page.locator('#contact input[type="email"]')
    if (await emailField.count()) {
      await emailField.fill('ada@example.com')
      await page.locator('#contact button', { hasText: /enviar|send|código|code/i }).first().click()
      const codeField = page.locator('#contact input[inputmode="numeric"], #contact input[autocomplete="one-time-code"]')
      await codeField.first().fill('123456')
      await page.locator('#contact button', { hasText: /confirmar|confirm|verificar|verify/i }).first().click()
    }

    await expect
      .poll(() => calls.filter((url) => url.includes('/contact/report')).length, { timeout: 10000 })
      .toBeGreaterThan(0)
  })

  test('a failed delivery is never shown as success', async ({ page }) => {
    await stubBackend(page, { completeAfter: 1, reportStatus: 502 })
    await page.goto('/')

    await say(page, 'soy Ada de AE')

    // Whatever the UI does, it must not claim the report is on its way.
    await expect(page.locator('#contact')).not.toContainText(/informe en camino|report on its way/i)
  })

  test('an expired conversation lets the visitor start again', async ({ page }) => {
    await stubBackend(page, { turnStatus: 401 })
    await page.goto('/')

    await say(page, 'hola')

    await expect(page.locator('#contact [role="alert"]')).toBeVisible()
  })

  test('the thread survives a reload within the tab', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    await say(page, 'hola, soy Ada')
    await page.reload()

    await expect(page.locator('#contact')).toContainText('hola, soy Ada')
  })
})
