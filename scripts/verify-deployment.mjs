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

//: Cloudflare's always-passing site key. Fine on a preview, never in production.
const TURNSTILE_TEST_SITE_KEY = '1x00000000000000000000AA'

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

  // The chat replaced the form: neither may be missing nor duplicated. The class
  // is `conversation`, not `contact-chat` — the questionnaire's name went away
  // with it, and this check kept looking for it long after the cutover.
  record(
    'conversational chat is mounted',
    html.includes('class="conversation"'),
    'looked for .conversation',
  )
  record('classic form is gone', !html.includes('name="fullName"'), 'looked for the old input')

  await checkContactIslandEnv(html)

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

/**
 * The contact island is compiled with its environment inlined, so a missing
 * PUBLIC_* variable is invisible in the HTML and only shows up as a broken chat.
 * These two checks read the shipped bundle instead of trusting the dashboard.
 *
 * Both failures were live on 2026-08-26: the chat called http://localhost:8000
 * and reported "service unavailable" because no Turnstile key was compiled in.
 */
async function checkContactIslandEnv(html) {
  const scripts = [...html.matchAll(/\/_astro\/[A-Za-z0-9._-]+\.js/g)].map((m) => m[0])
  const bundles = []

  for (const path of new Set(scripts)) {
    const { response } = await fetchSafe(`${SITE}${path}`)
    if (response?.ok) bundles.push(await response.text())
  }

  const island = bundles.find((code) => code.includes('conversation__thread'))

  if (!island) {
    return record('contact island bundle found', false, 'no shipped chunk renders the chat')
  }

  // Assert the compiled VALUE, not the absence of a default. `localhost:8000`
  // is the fallback in resolveApiBaseUrl and is therefore always in the bundle,
  // used or not — searching for it reported a correctly configured deployment
  // as broken.
  const configuredApi = island.match(/PUBLIC_API_BASE_URL:"(https?:\/\/[^"]+)"/)?.[1] ?? ''
  const pointsAtLocalhost = /localhost|127\.0\.0\.1/.test(configuredApi)

  record(
    'PUBLIC_API_BASE_URL reached the build',
    Boolean(configuredApi) && !pointsAtLocalhost,
    configuredApi
      ? pointsAtLocalhost
        ? `the chat ships pointing at ${configuredApi}`
        : configuredApi
      : 'not compiled in — set it on the frontend project and redeploy without the build cache',
    !IS_LOCAL,
  )

  const siteKey = island.match(/PUBLIC_TURNSTILE_SITE_KEY:"([^"]*)"/)?.[1] ?? ''

  record(
    'PUBLIC_TURNSTILE_SITE_KEY reached the build',
    Boolean(siteKey),
    siteKey || 'without it every code request answers "service unavailable"',
    !IS_LOCAL,
  )

  // Cloudflare's test pair approves every token by design. It is the right
  // thing on a preview — those live on *.vercel.app, a hostname no widget can
  // claim — and an open door in production, where this challenge is the only
  // limit on an endpoint that mails a code to any address it is given.
  if (siteKey && !IS_LOCAL) {
    record(
      'Turnstile runs on a real key, not the test one',
      siteKey !== TURNSTILE_TEST_SITE_KEY,
      siteKey === TURNSTILE_TEST_SITE_KEY
        ? 'the test key is live: any token passes the human check'
        : 'a real widget key is compiled in',
    )
  }
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

  // Whether a model or the deterministic stub conducts the chat. The stub cannot
  // read a name out of a sentence, so it still reports contact_name as missing —
  // which is exactly what a deployment with no working GEMINI_API_KEY looks like.
  const { response: turn } = await fetchSafe(`${API}/api/v1/contact/conversation/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Origin: SITE },
    body: JSON.stringify({ message: 'Hola, me llamo Miguel y trabajo en Link2Lux' }),
  })
  const turnBody = await turn?.json().catch(() => null)
  const extracted = Array.isArray(turnBody?.missing) && !turnBody.missing.includes('contact_name')
  record(
    'the conversation is model-driven',
    extracted,
    extracted
      ? 'the name was extracted from a sentence'
      : 'the stub is answering — GEMINI_API_KEY is missing or rejected',
    false,
  )

  // 503 here means the contact flow is not configured yet — expected before the
  // env vars land, a failure afterwards. `probe` is deliberately not a real
  // challenge token: a closed gate rejects it before any mail is attempted.
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

  // The site-key check reads the frontend bundle; the backend secret is invisible
  // from outside, and only this answer reveals it. An invented token that gets
  // past the challenge means the gate is open: 202 mailed a code to an address
  // the caller simply named, and 502 got as far as the mail provider — both are
  // the amplifier COD-49 describes. Only a refusal (403, or 503 naming the
  // variable) proves the door is shut.
  const gateHeld = verify?.status === 403 || verify?.status === 503
  record(
    'an invented Turnstile token is refused',
    gateHeld,
    gateHeld
      ? `HTTP ${verify?.status} — the challenge rejected it`
      : `HTTP ${verify?.status} — the token passed: the backend runs on the test secret`,
    !IS_LOCAL,
  )

  // 403 and 503 both mean the door is shut, and they were reported as the same
  // success — so a flow that was switched off entirely looked identical to one
  // defending itself. Only 403 means the flow is configured AND the gate held.
  //
  // This is what makes a bad sender visible from outside: COD-58 turns a public
  // mailbox domain into "not configured", and without this line that change
  // would read as green.
  const flowLive = verify?.status === 403
  record(
    'the contact flow is switched on',
    flowLive,
    flowLive
      ? 'HTTP 403 — configured, and the challenge did its job'
      : `HTTP ${verify?.status} — the flow is off; the backend log names the variable`,
    !IS_LOCAL,
  )

  // 502 means the opposite: the flow IS configured and the mail provider
  // refused the send. Unreachable while the gate holds — it takes a real token
  // to get this far — so it stays as the diagnosis for when the gate is open.
  if (verify?.status === 502) {
    record('the mail provider accepts our sends', false, 'HTTP 502 — check the backend logs')
  }
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
