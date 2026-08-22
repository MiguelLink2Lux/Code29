> **Type:** Architecture — **Scope:** Testing strategy — **Status:** Active

# Testing Strategy

## Overview

Four independent gates, each answering a question the others cannot. **There is no CI:**
every gate runs locally, so the sequence below is the release checklist, not a pipeline
description.

| Level | Runner | Cases | Command | Answers |
|-------|--------|-------|---------|---------|
| Unit | Vitest (jsdom) | 30 | `npm test` | Does the logic in `src/utils/` behave? |
| Build artifacts | Vitest (separate config) | 13 | `npm run build && npm run verify:assets` | Did the build *emit* the files we claim to ship? |
| End-to-end | Playwright (Chromium) | 26 in 4 specs | `npm run test:e2e` | Does a real browser see the intended behaviour? |
| Backend | pytest | 25 | `cd backend && uv run pytest` | Does the API boot, respond and stay deploy-consistent? |

## Components

### Unit — `src/utils/*.test.ts`

Colocated with the code they cover: `contact` (4), `cookie-consent` (4), `i18n` (7),
`seo` (15). Fast, no build, no browser. This is the only gate cheap enough to run on
every save (`npm run test:watch`).

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
| `i18n-and-contact.spec.ts` | 8 | One click switches copy and `html[lang]`, two clicks return, choice survives reload, URL never changes; contact validation, success, backend-error surfacing, honeypot hidden |
| `legal-and-routing.spec.ts` | 7 | Legal routes readable, legacy Spanish redirects, unknown route renders 404 (parameterized over the route tables) |

Two non-obvious properties of the harness, both in `playwright.config.ts` → `webServer.env`:

1. **`PUBLIC_GA4_ID` is set to a dummy id** (`G-E2ETESTID`). Without a GA4 id the
   analytics snippet renders nothing at all, so every "no analytics before consent"
   assertion would pass **vacuously** — the strongest privacy guarantee in the suite would
   be testing an empty page.
2. **`ASTRO_DEV_TOOLBAR=false`.** The dev toolbar injects its own `<h1>` and landmark
   elements, which collide with strict-mode locators. `astro.config.ts` honours the var,
   so the toolbar stays on for normal development.

`npm run test:e2e` runs `scripts/assert-e2e-specs.mjs` **before** Playwright: it fails if
`tests/e2e/` holds fewer than 4 `*.spec.ts` files. The guard exists because the directory
once contained zero specs while `package.json` advertised the gate — a green run over
nothing. A deleted spec must break the command, not quietly shrink coverage.

### Backend — `backend/tests/`

`test_config` (4), `test_cors` (5), `test_health` (5), `test_requirements_manifest` (4),
`test_vercel_config` (4), `test_vercel_entrypoint` (3). The last three are **deploy
consistency** tests, not feature tests: they fail when `requirements.txt` drifts from
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
- [[../protocols/sdd-workflow]]
