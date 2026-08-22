import { describe, expect, it } from 'vitest'
import { absoluteUrl, buildRobotsTxt, PUBLIC_ROUTES, resolveSiteUrl, sitemapUrl } from './seo'

describe('resolveSiteUrl', () => {
  it('falls back to the production origin when the env var is unset', () => {
    expect(resolveSiteUrl({})).toBe('https://code29.dev')
  })

  it('prefers PUBLIC_SITE_URL when provided', () => {
    expect(resolveSiteUrl({ PUBLIC_SITE_URL: 'https://code29.vercel.app' })).toBe(
      'https://code29.vercel.app',
    )
  })

  it('strips trailing slashes so joins never double up', () => {
    expect(resolveSiteUrl({ PUBLIC_SITE_URL: 'https://code29.dev/' })).toBe('https://code29.dev')
  })

  it('ignores an empty or whitespace-only value', () => {
    expect(resolveSiteUrl({ PUBLIC_SITE_URL: '   ' })).toBe('https://code29.dev')
  })

  it('rejects an origin without a scheme, which would break og:image and sitemap', () => {
    expect(() => resolveSiteUrl({ PUBLIC_SITE_URL: 'code29.dev' })).toThrow(/absolute/i)
  })
})

describe('absoluteUrl', () => {
  it('builds an absolute URL from a root-relative path', () => {
    expect(absoluteUrl('/og-image.png', {})).toBe('https://code29.dev/og-image.png')
  })

  it('tolerates a path without a leading slash', () => {
    expect(absoluteUrl('og-image.png', {})).toBe('https://code29.dev/og-image.png')
  })

  it('returns the bare origin for the site root', () => {
    expect(absoluteUrl('/', {})).toBe('https://code29.dev/')
  })
})

describe('sitemapUrl', () => {
  it('points at the index the sitemap integration emits', () => {
    // @astrojs/sitemap emits sitemap-index.xml as the entry document; robots.txt
    // must advertise that exact file or crawlers get a 404.
    expect(sitemapUrl({})).toBe('https://code29.dev/sitemap-index.xml')
  })
})

describe('PUBLIC_ROUTES', () => {
  it('lists every indexable page exactly once', () => {
    expect([...PUBLIC_ROUTES].sort()).toEqual(
      ['/', '/cookies', '/legal-notice', '/privacy-policy'].sort(),
    )
  })

  it('excludes the non-indexable status pages', () => {
    for (const route of ['/404', '/maintenance', '/coming-soon']) {
      expect(PUBLIC_ROUTES).not.toContain(route)
    }
  })
})

describe('buildRobotsTxt', () => {
  it('advertises the sitemap that the integration actually emits', () => {
    expect(buildRobotsTxt({})).toContain('Sitemap: https://code29.dev/sitemap-index.xml')
  })

  it('allows crawling of the whole site', () => {
    const robots = buildRobotsTxt({})
    expect(robots).toContain('User-agent: *')
    expect(robots).toContain('Allow: /')
  })

  it('follows PUBLIC_SITE_URL so a preview deploy never advertises production', () => {
    // The old static public/robots.txt hardcoded the origin and drifted the
    // moment the sitemap filename changed. Deriving it removes that failure mode.
    expect(buildRobotsTxt({ PUBLIC_SITE_URL: 'https://code29.vercel.app' })).toContain(
      'Sitemap: https://code29.vercel.app/sitemap-index.xml',
    )
  })

  it('ends with a trailing newline', () => {
    expect(buildRobotsTxt({}).endsWith('\n')).toBe(true)
  })
})
