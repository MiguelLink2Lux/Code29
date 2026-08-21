// Single source of truth for the site origin and everything derived from it:
// canonical URLs, absolute asset URLs for social cards, and the sitemap URL.
// Callers pass an env bag (DIP) so this stays testable and framework-agnostic;
// production callers rely on the `import.meta.env` default.

export interface SeoEnv {
  PUBLIC_SITE_URL?: string
}

/** Production origin. Overridable via `PUBLIC_SITE_URL` (e.g. a preview deploy). */
const FALLBACK_SITE_URL = 'https://code29.dev'

/** Pages that belong in the sitemap. Status pages are excluded on purpose. */
export const PUBLIC_ROUTES = ['/', '/legal-notice', '/privacy-policy', '/cookies'] as const

export function resolveSiteUrl(env: SeoEnv = import.meta.env as SeoEnv): string {
  const configured = env.PUBLIC_SITE_URL?.trim()

  if (!configured) {
    return FALLBACK_SITE_URL
  }

  // A scheme-less value silently produces relative og:image and sitemap URLs,
  // which crawlers and social scrapers reject. Fail loudly at build time instead.
  if (!/^https?:\/\//i.test(configured)) {
    throw new Error(
      `PUBLIC_SITE_URL must be an absolute origin including the scheme, got: ${configured}`,
    )
  }

  return configured.replace(/\/+$/, '')
}

export function absoluteUrl(path: string, env?: SeoEnv): string {
  const origin = resolveSiteUrl(env)

  return new URL(path, `${origin}/`).href
}

export function sitemapUrl(env?: SeoEnv): string {
  // @astrojs/sitemap emits sitemap-index.xml as the entry document.
  return absoluteUrl('/sitemap-index.xml', env)
}
