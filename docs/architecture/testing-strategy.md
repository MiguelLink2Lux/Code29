> **Type:** Architecture — **Scope:** Testing strategy — **Status:** Active

# Testing Strategy

## Overview

Four independent gates, each answering a question the others cannot. **There is no CI:**
every gate runs locally, so the sequence below is the release checklist, not a pipeline
description.

| Level | Runner | Cases | Command | Answers |
|-------|--------|-------|---------|---------|
| Unit | Vitest (jsdom) | 79 | `npm test` | Does the logic in `src/utils/` and the chat island behave? |
| Build artifacts | Vitest (separate config) | 13 | `npm run build && npm run verify:assets` | Did the build *emit* the files we claim to ship? |
| End-to-end | Playwright (Chromium) | 32 in 5 specs | `npm run test:e2e` | Does a real browser see the intended behaviour? |
| Backend | pytest | 261 | `cd backend && uv run pytest` | Does the API boot, respond, refuse correctly and stay deploy-consistent? |

## Components

### Unit — `src/utils/*.test.ts`

Colocated with the code they cover: `contact-api` (12), `contact-chat-flow` (12),
`contact-chat` (18), `cookie-consent` (4), `i18n` (7), `seo` (15), plus the chat island
itself in `src/components/contact/ContactChat.test.ts` (11). Fast, no build, no browser.
This is the only gate cheap enough to run on every save (`npm run test:watch`).

The contact-chat trio is where the flow's *rules* are asserted rather than its looks: that
the ten steps keep their fixed order, that a step's validation rejects what it should, that
answers round-trip through `sessionStorage`, and that the API client attaches the bearer
token only where a token is required.

### Build artifacts — `tests/artifacts/`

Runs under `vitest.artifacts.config.ts`, a **separate config on purpose** so it stays out
of the fast unit gate: it asserts over `.vercel/output/static`, which only exists after
`npm run build`.

- `build-output.test.ts` (6) — the sitemap index and `sitemap-0.xml` exist, list exactly
  `PUBLIC_ROUTES` as absolute URLs, and keep the status pages out. Coherence between
  `robots.txt` and the sitemap filename is checked by **string comparison against the same
  function that generates both**: the emitted body must contain `Sitemap: ${sitemapUrl({})}`.
  Nothing issues an HTTP request; that the sitemap file *exists* is a separate assertion
  over the build output.
- `social-assets.test.ts` (7) — the icons and `og-image.png` exist in both `public/` and
  the emitted output, with usable dimensions (read straight from the PNG IHDR chunk).

This level exists because of a class of defect the other three are blind to: markup that
references `/og-image.png` while `public/` holds nothing. Unit tests pass, the build
succeeds, the browser renders fine — and every shared link previews blank.

### End-to-end — `tests/e2e/`

| Spec | Cases | Covers |
|------|-------|--------|
| `landing.spec.ts` | 5 | All MVP sections render, single `h1`, absolute `og:image`, assets serve without a 404, `robots.txt` declares a line matching `^https?://\S+/sitemap-index\.xml$` — the URL is deliberately **not** followed, since it carries the production origin and the dev server does not answer there |
| `consent.spec.ts` | 6 | Banner on first visit, **no analytics request before consent**, granular persistence, reject path, survives reload, footer reopens preferences |
| `contact-chat.spec.ts` | 10 | The guided flow end to end: step order, per-step validation, the verification-code exchange, an in-progress chat surviving a reload, error surfacing, and report delivery |
| `i18n.spec.ts` | 4 | One click switches copy and `html[lang]`, two clicks return, choice survives reload, URL never changes |
| `legal-and-routing.spec.ts` | 7 | Legal routes readable, legacy Spanish redirects, unknown route renders 404 (parameterized over the route tables) |

Case counts are as **collected** (`npx playwright test --list`), so parameterized specs
report more cases than they declare `test()` calls.

Four non-obvious properties of the harness — the first two in `playwright.config.ts` →
`webServer.env`, the last two in `contact-chat.spec.ts` itself:

1. **`PUBLIC_GA4_ID` is set to a dummy id** (`G-E2ETESTID`). Without a GA4 id the
   analytics snippet renders nothing at all, so every "no analytics before consent"
   assertion would pass **vacuously** — the strongest privacy guarantee in the suite would
   be testing an empty page.
2. **`ASTRO_DEV_TOOLBAR=false`.** The dev toolbar injects its own `<h1>` and landmark
   elements, which collide with strict-mode locators. `astro.config.ts` honours the var,
   so the toolbar stays on for normal development.

3. **`PUBLIC_TURNSTILE_SITE_KEY` is set to Cloudflare's always-passing test key**
   (`1x00000000000000000000AA`). Without a site key the chat **short-circuits before it ever
   asks for a challenge** — `TurnstileNotConfigured` is raised and the flow stops — so every
   verification assertion would be testing a dead path instead of the real one.
4. **Cloudflare's script is stubbed with `page.route`.** The spec intercepts
   `**/turnstile/v0/api.js*` and fulfils it with a tiny `window.turnstile` shim that invokes
   the callback with a fixed token. The suite must not depend on a third-party CDN, and a real
   widget cannot be solved headlessly. The backend calls are stubbed the same way, on
   `**/api/v1/contact/**`.

`npm run test:e2e` runs `scripts/assert-e2e-specs.mjs` **before** Playwright: it fails if
`tests/e2e/` holds fewer than 4 `*.spec.ts` files. The guard exists because the directory
once contained zero specs while `package.json` advertised the gate — a green run over
nothing. A deleted spec must break the command, not quietly shrink coverage.

> **Known gap:** `MINIMUM_SPECS` is still `4` while `tests/e2e/` now holds **5** specs, so one
> spec can be deleted without the gate noticing. Raising the floor to 5 is a one-line change in
> `scripts/assert-e2e-specs.mjs` and is not a documentation fix.

### Backend — `backend/tests/`

261 collected cases across 17 modules — many are `pytest.mark.parametrize` expansions, so
the collected total is well above the number of `def test_` lines.

| Area | Modules |
|---|---|
| Contact flow | `test_contact_verification_api` (11), `test_verification_tokens` (17), `test_turnstile` (8), `test_contact_settings` (8) |
| Report | `test_report` (22), `test_contact_report_endpoint` (18), `test_mailer` (12) |
| Site analysis | `test_url_guard` (20), `test_site_fetch` (15), `test_site_signals` (19), `test_site_analysis_endpoint` (12) |
| Platform | `test_config` (4), `test_cors` (5), `test_health` (5) |
| Deploy consistency | `test_requirements_manifest` (4), `test_vercel_config` (4), `test_vercel_entrypoint` (3) |

(Counts above are declared test functions; parameterization is what lifts the collected total
to 261.)

The security-shaped modules carry most of the weight, and deliberately: `test_url_guard`
asserts the SSRF policy refusal by refusal, and `test_turnstile` asserts that every failure
mode **fails closed**. The deploy-consistency group are not feature tests: they fail when `requirements.txt` drifts from
`pyproject.toml`, when the catch-all rewrite in `vercel.json` is wrong, or when the
entrypoint stops serving the same app object as local uvicorn and pytest.

## Decisions & Rationale

- **No CI.** Accepted consequence: nothing enforces the gates but the developer running
  them. The mitigations are the two assertion scripts (`assert-e2e-specs.mjs`,
  `assert-vercel-runtime.mjs`), which convert "someone should have checked" into a
  non-zero exit code.
- **Separate artifact config over a unit-test tag.** Tagging would still load the suite in
  the watch loop and fail confusingly with no build present. A second config makes the
  prerequisite explicit in the command name.
- **Chromium only.** One engine for the behaviours under test (consent, `localStorage`,
  redirects); cross-browser breadth is not worth the runtime at this scale.

## Release checklist

```bash
npm test                                    # unit
npm run build && npm run verify:assets      # build artifacts
npm run verify:runtime                      # emitted Vercel runtime — see README → Deployment
npm run test:e2e                            # browser
cd backend && uv run pytest                 # backend
```

## References

- [[seo-and-discoverability]]
- [[i18n]]
- [[decisions/0004-backend-deploy-provider]]
- [[decisions/0006-guided-ai-contact-flow]]
- [[contact-chat-v1]]
- [[../protocols/sdd-workflow]]
