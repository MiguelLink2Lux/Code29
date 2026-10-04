---
title: 'COD-36 — Astro 5 + @astrojs/vercel 9 on Node 24'
type: 'bugfix'
ticket: ''
created: '2026-10-04'
status: 'built'
baseline_revision: '1ba5d5f6d8b54d4e1fac24a97e82c6012fd94752'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Vercel discontinued Node 20 on 2026-10-01, so every deploy of both projects (`code29` frontend, `code29-api` FastAPI backend) fails before building: `Node.js Version "20.x" is discontinued ... set "engines": { "node": "24.x" }`. Production keeps serving the last good build, but nothing merged to `main` can ship (Linear COD-36, Urgent).

**Approach:** Move the Node pin to 24 and upgrade the frontend to the smallest stack that supports it: astro ^5.18.2, @astrojs/vercel ^9.0.5, @astrojs/vue ^5.1.4, @astrojs/sitemap ~3.7. With no on-demand routes left, the site builds as fully static output and Vercel no longer receives a function at all.

## Boundaries & Constraints

**Always:** `.nvmrc` stays the single source of the Node major (CI and the runtime check read it). The three redirects stay 301s. Sitemap still excludes `/404`, `/maintenance/`, `/coming-soon/`. GA4 still loads only after consent and only when `PUBLIC_GA4_ID` is set. Full suite green on Node 24: lint, unit, build, verify:runtime, verify:assets, e2e and e2e:ci-sim.

**Never:** Astro 6/7 or adapter 10+ (two more majors of breaking changes, vite 8 / vitest majors — out of scope). No `backend/package.json` and no backend code change. No `vercel --prebuilt`. No edits under `docs/` (routed to doc-guardian after merge). No cleanup of unrelated stale code (e.g. `RESEND_API_KEY` / `CONTACT_*` declarations in `src/env.d.ts`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Static build | `npm run build` on Node 24 | `.vercel/output/` with static files + 301 routes in `config.json`, no `functions/` dir | No error expected |
| Runtime check, static | no `.vercel/output/functions` | `verify:runtime` exits 0, logs "static output, no function runtime" | — |
| Runtime check, good function | a `*.func/.vc-config.json` with `nodejs24.x` | exits 0 | — |
| Runtime check, stale function | a `*.func/.vc-config.json` with `nodejs18.x` / `nodejs20.x` | exits 1 naming the file, emitted and expected runtime | message keeps the "never `vercel --prebuilt`" advice |
| No build at all | no `.vercel/output` | exits 1 "Run `npm run build` first" | — |

</frozen-after-approval>

## Code Map

- `package.json:6-8` -- `engines.node` `20.x` → `24.x`. This root file is also what fails `code29-api` (project root `backend`, no own package.json; Vercel walks up). Project settings of both Vercel projects already say 24.x.
- `package.json:21` -- `build:node20` → `build:node24` (`npx --yes node@24 ...`).
- `package.json` deps -- astro `^5.18.2`, `@astrojs/vercel` `^9.0.5`, `@astrojs/vue` `^5.1.4`, `@astrojs/sitemap` `~3.7.4`. `@vitejs/plugin-vue` 5.2.4 and vitest 3.2.7 stay (compatible with vite 6). Regenerate `package-lock.json` with `npm install`.
- `.nvmrc` -- `20` → `24`.
- `astro.config.ts:4` -- `@astrojs/vercel/serverless` → `@astrojs/vercel` (subpath deprecated in 9).
- `astro.config.ts:34` -- delete `output: 'hybrid'` (removed in Astro 5; static is default). Keep `adapter: vercel()` so redirects become Vercel 301 routes (adapter 9 `getRedirects`).
- `scripts/assert-vercel-runtime.mjs` -- hard-codes `functions/_render.func/.vc-config.json` (:18-25) and exits 1 when absent; after the upgrade that file never exists. Rewrite per the I/O matrix: scan every `functions/**/.vc-config.json`; none → pass. Keep the header comment's intent, updated for adapter 9.
- `.github/workflows/ci.yml:27-29` -- comment "Node 20 on purpose…" → explain that `.nvmrc` pins the runtime major (`node-version-file` at :32 follows automatically). CI runs `verify:runtime` at :48.
- Script hoisting removed in Astro 5 -- scripts now render in place; check behaviour, do not rewrite preemptively: `src/components/LanguageSwitcher.astro:16`, `src/components/layout/Footer.astro:45`, `src/components/layout/Nav.astro:56`, `src/components/analytics/Analytics.astro:13` (inside `{GA_ID && (...)}`; e2e sets `PUBLIC_GA4_ID=G-E2ETESTID` in `playwright.config.ts`). `BaseLayout.astro:67` is `is:inline`, unaffected.
- `tests/artifacts/build-output.test.ts` -- asserts `sitemap-0.xml` / `sitemap-index.xml`; must still pass after the sitemap bump.
- Not used, no impact: content collections, `Astro.glob`, `astro:env`, `astro:assets`, view transitions, Astro i18n routing (i18n is `src/utils/i18n.ts`), middleware.
- Full scope report: `~/.claude/reports/Code29/2026-10-04-cod-36-astro-migration-scope.md`.

## Tasks & Acceptance

**Execution:**
- [x] `.nvmrc`, `package.json` -- Node 24 pin, `build:node24`, dependency bumps, `npm install` to refresh the lockfile -- unblocks both Vercel projects and moves to an adapter that knows Node 24
- [x] `astro.config.ts` -- drop `output: 'hybrid'`, import adapter from `@astrojs/vercel` -- Astro 5 API
- [x] `scripts/assert-vercel-runtime.mjs` -- rewrite to scan all functions, pass on static output -- the current check fails on every correct build
- [x] `tests/scripts/assert-vercel-runtime.test.mjs` (or the location the existing vitest configs can reach) -- spawn the script against temp fixture dirs for each I/O matrix row -- regression test for the check itself
- [x] `.github/workflows/ci.yml` -- update the Node comment -- it states an obsolete reason
- [x] Astro components with `<script>` -- fix only what lint/e2e show broken after the upgrade -- hoisting change

**Acceptance Criteria:**
- Given a clean checkout on Node 24, when `npm ci && npm run build` runs, then it succeeds with no deprecation warning about the adapter subpath or `hybrid`.
- Given that build, when `npm run verify:runtime` and `npm run verify:assets` run, then both exit 0.
- Given the dev server, when `npm run test:e2e` and `npm run test:e2e:ci-sim` run, then all specs pass, including cookie consent / GA4 and language switching.
- Given this branch pushed, when Vercel builds the previews, then both `code29` and `code29-api` deployments reach Ready.
- Given the `code29` preview, when `/aviso-legal` is requested, then it answers 301 to `/legal-notice`.

## Implementation Notes

- Regression test lives at `tests/scripts/assert-vercel-runtime.test.ts`; `vitest.config.ts` include extended to `tests/scripts/**` (file runs in the node environment). Verified it fails 3/5 against the baseline script.
- Script hoisting: no component change needed — consent/GA4 and i18n e2e pass on Astro 5.
- e2e `legacy redirects` broke: in static output the dev server answers redirects with a meta refresh, not a 301, and the spec read `page.url()` once. Spec now waits with `toHaveURL`; the 301s are pinned instead in `tests/artifacts/build-output.test.ts` against `.vercel/output/config.json`.
- Lint broke after a build: Astro 5 stages static output in `dist/` and ESLint 8 ignores `.gitignore`. Added `ignorePatterns: ['dist/']` to `.eslintrc.cjs` (CI lints before building, so CI was unaffected).
- `README.md` still documents Node 20 / hybrid / `build:node20` — left for doc-guardian.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — high 0 · medium 0 · low 4 · false 1 · maybe-false 1 · deferred 1

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | `ci.yml:27-28` comment says .nvmrc pins Vercel | low | patch | Vercel reads `engines.node` (the failing log asks for it); .nvmrc only feeds `setup-node` and `verify:runtime`. Direct rewording. |
| 1b | `assert-vercel-runtime.mjs` message "honours .nvmrc and engines.node" | low | patch | Same root cause; carried from the old script, but the rewrite re-emits it. Direct rewording. |
| 1c | .nvmrc and engines.node can drift unchecked | medium (unverified harm) | defer | Pre-existing: both pins existed at baseline; not caused by this change. |
| 2 | Edge runtime / malformed `.vc-config.json` misreported | low | reject | Unreachable: no `edgeMiddleware`, adapter writes the file itself; fix adds branches. |
| 3 | `functions/` present but empty branch untested | low | patch | `configs.length === 0` branch has no test; adding one case is direct. |
| 4 | e2e redirect assertion is an unanchored suffix match | low | patch | `new RegExp(`${to}/?$`)` accepts `/x/legal-notice`; old check compared the exact pathname. |
| 5 | ACs without evidence (Vercel previews, e2e) | false | reject | e2e 40/40 and ci-sim 40/40 reported by the implementer on Node 24; Vercel ACs can only be checked after push, which step 3 forbids — verified at presentation. |
| 6 | Plan lacks Critical Section / SOLID Check required by `CLAUDE.md` | medium | defer | Real conflict between project CLAUDE.md and the BMad plan template; fix edits agent-context files. |
| 7 | Empty `.vercel/output/server/` after build | maybe-false (low) | reject | Harmless static staging dir; would need adapter source to confirm, and at most low. |

## Verification

**Commands:**
- `node -v` -- expected: v24.x (use `npx --yes node@24` if the local Node is 23)
- `npm run lint && npm test` -- expected: green
- `npm run build && npm run verify:runtime && npm run verify:assets` -- expected: green; `ls .vercel/output/functions` empty or absent
- `grep -A3 aviso-legal .vercel/output/config.json` -- expected: 301 route to `/legal-notice`
- `npm run test:e2e && npm run test:e2e:ci-sim` -- expected: green
- `cd backend && uv run ruff check && uv run pytest` -- expected: green (untouched, sanity)
- `gh pr checks <pr>` -- expected: `Vercel – code29` and `Vercel – code29-api` pass
