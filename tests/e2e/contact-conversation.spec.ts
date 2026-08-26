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
      const factsHeld = turns >= completeAfter
      return route.fulfill({
        status: stub.turnStatus ?? 200,
        contentType: 'application/json',
        body: JSON.stringify({
          reply: factsHeld ? 'Solo me falta tu email.' : '¿En qué empresa trabajas?',
          envelope: `env-${turns}`,
          // Never complete here: the address is still unverified at this point,
          // which is exactly what the real endpoint reports.
          complete: false,
          exhausted: false,
          missing: factsHeld ? ['email'] : ['company', 'email'],
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

/**
 * Walks the verification exchange. Fails if it is not there: it is not optional.
 *
 * There is one composer for the whole conversation, and it changes what it asks
 * for — so the same submit button reads "enviar código" and then "confirmar".
 * The ids are what identify the mode; the button text is what the visitor sees.
 */
async function verifyEmail(page: Page, address = 'ada@example.com') {
  const email = page.locator('#conversation-email')
  await expect(email, 'the verification thread should appear once email is the last gap').toBeVisible()
  await email.fill(address)
  await page.locator('#contact button', { hasText: /send code|enviar código/i }).click()

  const code = page.locator('#conversation-code')
  await expect(code, 'the code field should appear once a code was requested').toBeVisible()
  await code.fill('123456')
  await page.locator('#contact button', { hasText: /confirm|confirmar/i }).click()
}

test.beforeEach(async ({ page }) => {
  await stubTurnstile(page)
})

test.describe('conversational contact', () => {
  test('the bot speaks first, and says what the questions are for', async ({ page }) => {
    await stubBackend(page)
    await page.goto('/')

    // An empty thread waiting for the visitor to start is what a form looks
    // like. The greeting must be a message, and it must name the report.
    const opening = page.locator('#contact .conversation__message--bot').first()

    await expect(opening).toBeVisible()
    await expect(opening).toContainText(/informe|report/i)
  })

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

  test('asks for the report once the email is verified', async ({ page }) => {
    const calls = await stubBackend(page, { completeAfter: 1 })
    await page.goto('/')

    await say(page, 'soy Ada de Analytical Engines, ae.example, somos tres')

    // Verifying the address is the last missing fact, and therefore what
    // unlocks the report. No conditional: if this thread does not appear, the
    // flow is broken and the test must say so.
    await verifyEmail(page)

    await expect
      .poll(() => calls.filter((url) => url.includes('/contact/report')).length, { timeout: 10000 })
      .toBeGreaterThan(0)
  })

  test('a failed delivery is never shown as success', async ({ page }) => {
    await stubBackend(page, { completeAfter: 1, reportStatus: 502 })
    await page.goto('/')

    await say(page, 'soy Ada de AE')
    await verifyEmail(page)

    // The request was made and refused: the visitor must not be told otherwise.
    await expect(page.locator('#contact [role="alert"]')).toBeVisible()
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
