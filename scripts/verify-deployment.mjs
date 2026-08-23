/**
 * Verifies a real deployment from the outside, the way a visitor and a crawler
 * see it. Local gates cannot catch a wrong environment variable, a missing
 * asset in the CDN or a CORS policy that forgot this origin.
 *
 * Usage:
 *   node scripts/verify-deployment.mjs --site https://code29.dev --api https://api.code29.dev
 *
 * Exits non-zero if any required check fails. Optional checks report but do not
 * fail the run: they depend on configuration only the owner can complete.
 */

const args = process.argv.slice(2)
const flag = (name) => {
  const index = args.indexOf(`--${name}`)
  return index === -1 ? '' : (args[index + 1] ?? '').replace(/\/+$/, '')
}

const SITE = flag('site')
const API = flag('api')

if (!SITE) {
  console.error('Usage: node scripts/verify-deployment.mjs --site <url> [--api <url>]')
  process.exit(2)
}

// Against a dev server three checks cannot pass by design: the sitemap is only
// emitted by a build, and og:image points at the production origin. They report
// as warnings there so a local run does not look broken.
const IS_LOCAL = /^https?:\/\/(localhost|127\.0\.0\.1)/.test(SITE)

const results = []
const record = (name, ok, detail, required = true) =>
  results.push({ name, ok, detail, required })

async function fetchSafe(url, init) {
  try {
    const response = await fetch(url, { redirect: 'follow', ...init })
    return { response, error: null }
  } catch (error) {
    return { response: null, error }
  }
}

async function checkFrontend() {
  const { response, error } = await fetchSafe(`${SITE}/`)
  if (error || !response.ok) {
    return record('landing responds', false, error?.message ?? `HTTP ${response.status}`)
  }

  const html = await response.text()
  record('landing responds', true, `HTTP ${response.status}`)

  // Sections the PRD requires, by id.
  const missingSections = ['hero', 'stats', 'stack', 'services', 'testimonials', 'contact'].filter(
    (id) => !html.includes(`id="${id}"`),
  )
  record('all landing sections render', missingSections.length === 0, missingSections.join(', '))

  // The chat replaced the form: neither may be missing nor duplicated.
  record('guided chat is mounted', html.includes('contact-chat'), 'looked for .contact-chat')
  record('classic form is gone', !html.includes('name="fullName"'), 'looked for the old input')

  const ogImage = html.match(/property="og:image" content="([^"]+)"/)?.[1] ?? ''
  record('og:image is absolute', /^https?:\/\//.test(ogImage), ogImage || 'not found')

  if (ogImage) {
    const { response: asset } = await fetchSafe(ogImage, { method: 'HEAD' })
    record(
      'og:image is actually served',
      asset?.ok === true,
      `HTTP ${asset?.status ?? 'no answer'}`,
      !IS_LOCAL,
    )
  }

  for (const path of ['/favicon.svg', '/apple-touch-icon.png']) {
    const { response: asset } = await fetchSafe(`${SITE}${path}`, { method: 'HEAD' })
    record(`${path} is served`, asset?.ok === true, `HTTP ${asset?.status ?? 'no answer'}`)
  }

  // robots.txt must advertise a sitemap that exists on this host.
  const { response: robots } = await fetchSafe(`${SITE}/robots.txt`)
  if (robots?.ok) {
    const body = await robots.text()
    const advertised = body.match(/Sitemap:\s*(\S+)/)?.[1] ?? ''
    record('robots.txt declares a sitemap', Boolean(advertised), advertised || 'no Sitemap line')

    if (advertised) {
      const sameHost = advertised.startsWith(SITE)
      record(
        'the sitemap URL matches this deployment',
        sameHost,
        sameHost ? advertised : `points elsewhere: ${advertised} — set PUBLIC_SITE_URL`,
        !IS_LOCAL,
      )
      const { response: sitemap } = await fetchSafe(`${SITE}/sitemap-index.xml`)
      record(
        'sitemap-index.xml is served',
        sitemap?.ok === true,
        IS_LOCAL && sitemap?.status === 404
          ? 'HTTP 404 — only emitted by a build, expected on a dev server'
          : `HTTP ${sitemap?.status}`,
        !IS_LOCAL,
      )
    }
  } else {
    record('robots.txt is served', false, `HTTP ${robots?.status ?? 'no answer'}`)
  }

  for (const [from, to] of [
    ['/mantenimiento', '/maintenance'],
    ['/aviso-legal', '/legal-notice'],
    ['/privacidad', '/privacy-policy'],
  ]) {
    const { response: redirected } = await fetchSafe(`${SITE}${from}`)
    const landed = redirected ? new URL(redirected.url).pathname.replace(/\/$/, '') : ''
    record(`${from} redirects to ${to}`, landed === to, landed || 'no answer')
  }

  const { response: notFound } = await fetchSafe(`${SITE}/this-does-not-exist`)
  record('unknown route returns 404', notFound?.status === 404, `HTTP ${notFound?.status}`)
}

async function checkBackend() {
  if (!API) {
    record('backend checks', true, 'skipped: no --api given', false)
    return
  }

  const { response, error } = await fetchSafe(`${API}/api/v1/health`)
  if (error || !response.ok) {
    return record('backend health', false, error?.message ?? `HTTP ${response.status}`)
  }

  const body = await response.json().catch(() => null)
  record('backend health', body?.status === 'ok', JSON.stringify(body))

  // CORS must name the frontend origin explicitly — never `*`.
  const { response: cors } = await fetchSafe(`${API}/api/v1/health`, {
    headers: { Origin: SITE },
  })
  const allowed = cors?.headers.get('access-control-allow-origin') ?? ''
  record('CORS allows the frontend origin', allowed === SITE, allowed || 'header absent')
  record('CORS is not a wildcard', allowed !== '*', allowed)

  // A verification request without a Turnstile token must be refused, not served.
  const { response: unauth } = await fetchSafe(`${API}/api/v1/contact/site-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: 'https://example.com' }),
  })
  record(
    'site analysis refuses an unauthenticated caller',
    unauth?.status === 401 || unauth?.status === 503,
    `HTTP ${unauth?.status}`,
  )

  // 503 here means the contact flow is not configured yet — expected before the
  // env vars land, a failure afterwards.
  const { response: verify } = await fetchSafe(`${API}/api/v1/contact/verification/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'probe@example.com', turnstileToken: 'probe' }),
  })
  const configured = verify?.status !== 503
  record(
    'contact flow is configured',
    configured,
    configured ? `HTTP ${verify?.status}` : 'HTTP 503 — env vars still missing',
    false,
  )
}

await checkFrontend()
await checkBackend()

const pad = Math.max(...results.map((r) => r.name.length))
let failed = 0

for (const { name, ok, detail, required } of results) {
  const mark = ok ? 'ok  ' : required ? 'FAIL' : 'warn'
  if (!ok && required) failed += 1
  console.log(`${mark}  ${name.padEnd(pad)}  ${detail ?? ''}`)
}

console.log(`\n${results.length - failed}/${results.length} checks passed`)
process.exit(failed > 0 ? 1 : 0)
