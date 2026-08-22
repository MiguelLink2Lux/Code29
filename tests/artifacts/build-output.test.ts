/**
 * Asserts on the files the build actually emits. These are the defects that
 * green unit tests cannot see: a sitemap that never got generated, a robots.txt
 * advertising a 404, a social-card image referenced but never shipped.
 *
 * Requires `npm run build` first — run via `npm run verify:assets`.
 */
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { PUBLIC_ROUTES, resolveSiteUrl, sitemapUrl } from '../../src/utils/seo'

// The Vercel adapter writes static output here, not to dist/.
const STATIC_DIR = join(process.cwd(), '.vercel', 'output', 'static')

const read = (file: string) => readFileSync(join(STATIC_DIR, file), 'utf8')

describe('build output', () => {
  it('exists at all', () => {
    expect(existsSync(STATIC_DIR)).toBe(true)
  })
})

describe('sitemap', () => {
  it('emits the index that robots.txt advertises', () => {
    expect(existsSync(join(STATIC_DIR, 'sitemap-index.xml'))).toBe(true)
  })

  it('lists every public route as an absolute URL', () => {
    const urls = read('sitemap-0.xml')
    const origin = resolveSiteUrl({})

    for (const route of PUBLIC_ROUTES) {
      // Astro emits directory-style URLs with a trailing slash; the root is "/".
      const expected = route === '/' ? `${origin}/` : `${origin}${route}/`
      expect(urls).toContain(`<loc>${expected}</loc>`)
    }
  })

  it('keeps status pages out of the index', () => {
    const urls = read('sitemap-0.xml')

    for (const excluded of ['404', 'maintenance', 'coming-soon']) {
      expect(urls).not.toContain(excluded)
    }
  })
})

describe('robots.txt', () => {
  it('is emitted as a static file', () => {
    expect(existsSync(join(STATIC_DIR, 'robots.txt'))).toBe(true)
  })

  it('advertises the sitemap that was actually generated', () => {
    // The historical bug: robots.txt pointed at /sitemap.xml, which never existed.
    expect(read('robots.txt')).toContain(`Sitemap: ${sitemapUrl({})}`)
  })
})
