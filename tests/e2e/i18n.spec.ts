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
