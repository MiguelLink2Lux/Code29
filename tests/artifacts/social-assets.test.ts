/**
 * Social-card and icon assets must exist AND have usable dimensions. The
 * historical defect: BaseLayout referenced /og-image.png while public/ held
 * nothing, so every shared link rendered a blank preview — invisible to the
 * build, the unit tests and the browser.
 *
 * Requires `npm run build` — run via `npm run verify:assets`.
 */
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const STATIC_DIR = join(process.cwd(), '.vercel', 'output', 'static')
const PUBLIC_DIR = join(process.cwd(), 'public')

/** Reads width/height from a PNG IHDR chunk (bytes 16-24). */
function pngSize(path: string): { width: number; height: number } {
  const buffer = readFileSync(path)
  expect(buffer.subarray(1, 4).toString()).toBe('PNG')

  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) }
}

describe('og-image', () => {
  it('is committed to public/', () => {
    expect(existsSync(join(PUBLIC_DIR, 'og-image.png'))).toBe(true)
  })

  it('meets the 1200x630 minimum every social scraper expects', () => {
    const { width, height } = pngSize(join(PUBLIC_DIR, 'og-image.png'))
    expect(width).toBeGreaterThanOrEqual(1200)
    expect(height).toBeGreaterThanOrEqual(630)
  })

  it('ships in the build output', () => {
    expect(existsSync(join(STATIC_DIR, 'og-image.png'))).toBe(true)
  })
})

describe('favicon', () => {
  it('ships an svg icon and a png fallback', () => {
    expect(existsSync(join(STATIC_DIR, 'favicon.svg'))).toBe(true)
    expect(existsSync(join(STATIC_DIR, 'favicon-32.png'))).toBe(true)
  })

  it('ships an apple-touch-icon at the size iOS expects', () => {
    const { width, height } = pngSize(join(STATIC_DIR, 'apple-touch-icon.png'))
    expect(width).toBe(180)
    expect(height).toBe(180)
  })
})

describe('rendered head', () => {
  const html = () => readFileSync(join(STATIC_DIR, 'index.html'), 'utf8')

  it('links the icons', () => {
    const head = html()
    expect(head).toContain('rel="icon"')
    expect(head).toContain('/favicon.svg')
    expect(head).toContain('rel="apple-touch-icon"')
  })

  it('uses an absolute og:image, which scrapers require', () => {
    // A root-relative og:image is silently ignored by most scrapers.
    expect(html()).toContain('property="og:image" content="https://code29.dev/og-image.png"')
  })
})
