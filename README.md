# Code29

Personal brand landing page positioning the profile as **CTO as a Service / AI Project Manager**.

Visual identity: *"The Neon Architect"* — terminal aesthetic, neon accents, no border radius.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Astro 4.16 (`output: 'hybrid'`, `@astrojs/vercel` serverless adapter) |
| Interactivity | Vue 3.5 Islands — hydrated only where it adds value |
| Language | TypeScript 5.6 |
| Backend | FastAPI · Python 3.12 (`>=3.12,<3.13`), managed with [uv](https://docs.astral.sh/uv/) |
| Hosting | Vercel |
| Tests | Vitest (unit + build artifacts) · Playwright (e2e) · pytest (backend). No CI — every gate runs locally, see [testing strategy](docs/architecture/testing-strategy.md) |

---

## Repository structure

```
.
├── src/
│   ├── pages/            index · 404 · coming-soon · maintenance
│   │                     cookies · legal-notice · privacy-policy
│   │                     robots.txt.ts — generated, not a static file
│   ├── components/
│   │   ├── layout/       Nav · Footer
│   │   ├── sections/     Hero · Stats · EducationStack · Services
│   │   │                 Toolbelt · Testimonials · Contact
│   │   ├── contact/      ContactChat.vue — the guided contact flow island
│   │   ├── cookies/      CookieBanner.vue
│   │   ├── analytics/    Analytics.astro
│   │   └── LanguageSwitcher.astro
│   ├── layouts/          BaseLayout · LegalLayout · StatusLayout
│   ├── i18n/             translations.ts — single source of truth for all copy (ES/EN)
│   ├── utils/            analytics · cookie-consent · i18n
│   │                     contact-chat-flow.ts — the ten fixed steps, declarative
│   │                     contact-chat.ts — client state, sessionStorage persistence
│   │                     contact-api.ts — the only caller of the backend
│   │                     turnstile-client.ts — Turnstile widget wrapper
│   │                     seo.ts — single source of truth for the site origin
│   │                     (+ colocated *.test.ts)
│   └── styles/           tokens.css — design system tokens
├── public/               og-image.png · favicon.svg · favicon-32.png
│                         apple-touch-icon.png  (generated, committed)
├── scripts/
│   ├── generate-brand-assets.mjs   Rasterizes the OG card and icons
│   ├── assert-vercel-runtime.mjs   Fails on a build that emits nodejs18.x
│   └── assert-e2e-specs.mjs        Fails if the e2e suite shrinks
├── backend/
│   ├── app/
│   │   ├── main.py       create_app() factory + module-level app
│   │   ├── api/v1/       router.py · health.py
│   │   │                 contact.py — email verification (request/confirm)
│   │   │                 contact_report.py · site_analysis.py
│   │   ├── services/     tokens.py — stateless codes + signed access tokens
│   │   │                 tokens_port.py — the abstraction the endpoints depend on
│   │   │                 turnstile.py — anti-abuse gate, fails closed
│   │   │                 mailer.py · report.py — deterministic stub generator
│   │   │                 report_copy.py — ES/EN template copy
│   │   │                 report_gemini.py — Gemini over the REST API (ADR 0007)
│   │   │                 site_analysis.py · url_guard.py — SSRF boundary
│   │   └── core/         config.py · report_settings.py — env-driven Settings
│   ├── api/index.py      Vercel entrypoint — `from app.main import app`
│   ├── scripts/          gen-requirements.sh — regenerates requirements.txt
│   └── tests/            21 modules, 309 collected cases — see testing strategy
├── tests/
│   ├── artifacts/        Assertions on the real build output (13 cases)
│   └── e2e/              Playwright specs — 5 files, 32 cases
├── vitest.config.ts              Unit gate
├── vitest.artifacts.config.ts    Build-artifact gate (needs `npm run build`)
├── .env.example                  Frontend variable template — asserted by the unit gate
├── .nvmrc                        Node 20 — see Deployment
└── docs/                 PRD · architecture · ADRs · protocols
```

External services (analytics, the backend API, Turnstile) are reached **exclusively** through the
abstractions in `src/utils/` — see [SOLID](#conventions). Email is no longer sent from the
frontend at all.

---

## Getting started

### Frontend

```bash
npm install
npm run dev          # http://localhost:4321
```

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload    # interactive docs at /docs
```

---

## Scripts

### Frontend (`package.json`)

| Script | Purpose |
|--------|---------|
| `npm run dev` | Astro dev server |
| `npm run build` | Production build |
| `npm run preview` | Preview the build locally |
| `npm test` | Unit tests (`vitest run`) — 89 cases |
| `npm run test:watch` | Unit tests in watch mode |
| `npm run test:e2e` | End-to-end tests. Runs `scripts/assert-e2e-specs.mjs` first, then `playwright test` — **fails if `tests/e2e/` holds fewer than 4 spec files**, so a deleted spec breaks the gate instead of quietly shrinking coverage. The floor is still 4 while the suite holds 5 — raising it is a one-line change in the script. |
| `npm run verify:assets` | Build-artifact assertions (`vitest run --config vitest.artifacts.config.ts`) — 13 cases over the **real** output in `.vercel/output/static`. Requires `npm run build` first. |
| `npm run verify:runtime` | `scripts/assert-vercel-runtime.mjs` — fails if the build emitted a Node runtime Vercel no longer accepts. Requires a build first. |
| `npm run build:node20` | Build under Node 20 regardless of the local version (`npx --yes node@20 node_modules/astro/astro.js build`). |
| `npm run lint` | ESLint |
| `npm run format` | Prettier |

Full breakdown of the four test levels: [Testing strategy](docs/architecture/testing-strategy.md).

### Backend

| Command | Purpose |
|---------|---------|
| `uv run pytest` | Backend test suite |
| `uv run ruff check` | Lint (line length 100, rules `E,F,I,UP,B`) |

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/v1/health` | Backend liveness — returns `{"status": "ok"}`. Dependency-free: no DB, no external calls. |
| `POST` | `/api/v1/contact/verification/request` | Verifies the Turnstile challenge, then emails a 6-digit code. The code is never in the response. |
| `POST` | `/api/v1/contact/verification/confirm` | Exchanges a valid code for a signed access token (30 min) that authorises the expensive steps. |
| `POST` | `/api/v1/contact/site-analysis` | Token required. Fetches the lead's home page behind the SSRF guard and returns measured signals. |
| `POST` | `/api/v1/contact/report` | Token required. Generates the workflow report and emails it. The recipient comes from the token, never from the body. |

There is **no `/api/contact`** any more: the Astro serverless route, `ContactForm.vue` and
`src/utils/contact.ts` were deleted with the guided flow. The backend is the single email sender.

### Contact flow

One path, ten fixed steps, in this order:

```
name → company → email → code → delivery → bugs → deploys → security → website → consent
```

The order is an **authorisation rule, not a UX preference**: everything expensive — the
outbound fetch of the visitor's site, the AI draft, the email — sits after `code`, so nothing
runs for a visitor who has not proven control of the address. Verification is stateless (an
HMAC-derived code, a signed token; no datastore), Cloudflare Turnstile gates every outbound
email, and the AI only *drafts* the report from validated facts — it never sees free text.
Full rationale, privacy posture and the open risks: [ADR
0006](docs/architecture/decisions/0006-guided-ai-contact-flow.md).

### Route redirects

Legacy Spanish paths are preserved via `astro.config.ts`:

| From | To |
|------|-----|
| `/mantenimiento` | `/maintenance` |
| `/aviso-legal` | `/legal-notice` |
| `/privacidad` | `/privacy-policy` |

---

## Environment variables

Names only — never commit values. `.env` files are git-ignored.

### Frontend (Vercel project settings / local `.env`)

| Variable | Purpose |
|----------|---------|
| `PUBLIC_SITE_URL` | **Optional.** Absolute site origin, scheme included (e.g. `https://code29.dev`). When unset, `src/utils/seo.ts` falls back to `https://code29.dev`. |
| `PUBLIC_GA4_ID` | GA4 measurement ID. The script loads **only** after the visitor grants analytics consent. |
| `PUBLIC_API_BASE_URL` | Absolute base URL of the backend, scheme included. A value without a scheme is rejected at runtime. |
| `PUBLIC_TURNSTILE_SITE_KEY` | Cloudflare Turnstile site key. **Without it the chat stops before the verification step** rather than skipping the challenge. |

The frontend no longer holds any Resend credentials: `RESEND_API_KEY`, `CONTACT_TO_EMAIL` and
`CONTACT_FROM_EMAIL` moved to the **backend**, which is now the only sender of email.

`PUBLIC_SITE_URL` is the **only** place the domain is configured. The canonical URL,
`og:image`, `robots.txt` and the sitemap are all derived from it — change it here and
nothing else needs touching. A value without a scheme (`code29.dev`) **fails the build on
purpose**: it would otherwise emit relative `og:image` and sitemap URLs that crawlers and
social scrapers silently reject. See
[SEO and discoverability](docs/architecture/seo-and-discoverability.md).

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_ENV` | `development` | Environment name. |
| `CORS_ORIGINS` | `http://localhost:4321` | Comma-separated list of allowed origins. Never `*`. |
| `CONTACT_TOKEN_SECRET` | *(unset)* | HMAC key for verification codes and access tokens. In production it must be **≥ 32 characters** or the app refuses to boot. |
| `RESEND_API_KEY` | *(unset)* | Resend API key — the backend is the only email sender. |
| `CONTACT_FROM_EMAIL` | *(unset)* | Verified sender address. |
| `CONTACT_TO_EMAIL` | *(unset)* | Where the owner's copy of a report is delivered. |
| `TURNSTILE_SECRET_KEY` | *(unset)* | Cloudflare Turnstile secret. Without it no email path opens. |
| `REPORT_GENERATOR` | `stub` | Which generator writes the workflow report: `stub` or `gemini`. Never degrades silently — see below. |
| `GEMINI_API_KEY` | *(unset)* | Google AI Studio key. Required by `REPORT_GENERATOR=gemini`; unused by `stub`. |

#### The workflow report generator

`REPORT_GENERATOR` picks the implementation behind the one-method `ReportGenerator` port — the
contact endpoint, the mailer and the frontend never know which one ran:

| Value | Behaviour |
|-------|-----------|
| `stub` | **Default, and what runs today.** A deterministic template: same facts in, byte-identical report out. No key, no network. |
| `gemini` | Calls `gemini-2.5-flash` over the Generative Language REST API. Refuses to boot without `GEMINI_API_KEY`. |
| `genkit` | Refused on purpose: the Genkit Gemini plugin does not fit Vercel's Python bundle limit. Use `gemini` — [ADR 0007](docs/architecture/decisions/0007-gemini-over-rest.md). |

**Today the report is written by the deterministic stub, not by a model**, because no
`GEMINI_API_KEY` exists in any environment. The Gemini connector is implemented and covered by
a dedicated test module (`backend/tests/test_report_gemini.py`) against a mock transport, but
it has never been run against the real model — so
switching a lead-facing environment to `gemini` is an unverified change until a key exists and
someone reads what the model actually produces.

Both generators write in the visitor's language. The template's Spanish and English copy lives
in `backend/app/services/report_copy.py`, with `backend/tests/test_report_locale.py` asserting
key parity so a missing translation fails the suite; Gemini is instructed to write in the locale
it is given.

The model never receives the visitor's email address, and whatever it returns is validated
against the same Pydantic models the stub produces: an invented diagnosis axis, or a service
Code29 does not sell, is a hard failure rather than a delivered report. There is no silent
fallback to the stub.

The five contact-flow variables are **all-or-nothing**: when any of them is missing,
`contact_flow_enabled` is false and every contact endpoint answers `503` instead of
half-working. Local development therefore needs no configuration at all.

> **Note:** copy `backend/.env.example` to `backend/.env` to get started. The template ships
> every variable in the table above, contact-flow ones included, with placeholders and no real
> secrets. On the frontend side the root `.env.example` plays the same role, and
> `src/utils/env-example.test.ts` fails the unit gate if the code reads a variable the template
> does not document.

In production these are set in the **backend** Vercel project's environment settings:

| Variable | Production value |
|----------|------------------|
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | The frontend's real origin (e.g. `https://code29.vercel.app`) — comma-separated if more than one. Never `*`: the validator in `backend/app/core/config.py` raises on boot, so a wildcard fails the deploy instead of shipping an open policy. |

---

## Deployment

The repository deploys as **two independent Vercel projects**. They cannot be merged: the
`@astrojs/vercel` v7 adapter emits Build Output API into `.vercel/output`, which suppresses
Vercel's zero-config discovery of `api/` functions — a Python function in the frontend project
would never be routed. See [ADR 0004](docs/architecture/decisions/0004-backend-deploy-provider.md).

| Project | Root Directory | Builds |
|---------|----------------|--------|
| Frontend | `.` | `astro build` (Node 20) → `.vercel/output` |
| Backend | `backend/` | `@vercel/python` → `api/index.py` |

### Frontend

Deploy **from Git** (push to `main` / open a PR) — never with `vercel --prebuilt`.

> With a local Node version other than 20, the adapter bakes `"runtime": "nodejs18.x"` into
> `.vercel/output/functions/_render.func/.vc-config.json`, and Vercel has rejected Node 18 on
> new deployments since 2025-09-01. The build still **succeeds**, so nothing warns you until
> the deploy fails. Building on Vercel makes the local Node version irrelevant.
> `.nvmrc` and `package.json` → `engines` pin Node 20 for local work.

To check the runtime a local build actually emitted:

```bash
npm run build:node20      # build under Node 20 whatever the local version is
npm run verify:runtime    # fails unless .vc-config.json says nodejs20.x
```

### Brand and social assets

`public/og-image.png`, `favicon.svg`, `favicon-32.png` and `apple-touch-icon.png` are
generated from inline SVG with `sharp`, using the colors in `src/styles/tokens.css`:

```bash
node scripts/generate-brand-assets.mjs
```

The outputs are **committed on purpose** — the deploy must never depend on a rasterizer
being available in the build image. Regenerate and commit after any brand change, then run
`npm run build && npm run verify:assets` to confirm the emitted output carries them.

### Backend

Create a second Vercel project on the same repository with **Root Directory `backend/`**.
Two files drive it:

| File | Role |
|------|------|
| `backend/vercel.json` | Catch-all rewrite `"/(.*)" → "/api/index"`, so every path reaches the single function. |
| `backend/api/index.py` | Entrypoint. Logic-free: `from app.main import app`. Local uvicorn, pytest and the deployed function all serve the same object built by `create_app()`. |

Vercel's Python runtime does not read `pyproject.toml`/uv, so it installs from
`backend/requirements.txt`. That file is **generated — never edit it by hand**.
`pyproject.toml` stays the canonical manifest; regenerate after every dependency change:

```bash
cd backend
./scripts/gen-requirements.sh
```

`backend/tests/test_requirements_manifest.py` fails the suite if the two manifests drift.

---

## Project status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | **Landing v1** — 7 sections, GDPR cookie consent with granular categories persisted in `localStorage`, legal pages, centralized ES/EN i18n with a client-side switcher that does not change the URL. The Phase 1 contact form has since been **replaced** by the guided flow below. | ✅ Complete |
| 2 | **FastAPI backend** — health endpoint, env-driven config, CORS. No database, no auth. Deploys on Vercel as a second project ([ADR 0004](docs/architecture/decisions/0004-backend-deploy-provider.md)). | ✅ Complete |
| 3 | **AI services** — the guided contact flow: stateless email verification, Turnstile gate, SSRF-guarded site analysis, generated workflow report by email ([ADR 0006](docs/architecture/decisions/0006-guided-ai-contact-flow.md)). **The report generator is still a deterministic stub** until `GEMINI_API_KEY` is provisioned. The Gemini connector is written and tested but never run against the real model; it talks to the API over REST because the Genkit dependency set does not fit Vercel's function size limit ([ADR 0007](docs/architecture/decisions/0007-gemini-over-rest.md), [ADR 0004 → Measured bundle size](docs/architecture/decisions/0004-backend-deploy-provider.md)). | 🟡 Connector ready, unverified |

---

## Documentation

| Document | Contents |
|----------|----------|
| [PRD](docs/requirements/PRD.md) | Product requirements, v1 scope |
| [Tech stack decision](docs/architecture/tech-stack-decision.md) | Why Astro + Vue + FastAPI |
| [Design](docs/architecture/design.md) | Design system, tokens, source of truth |
| [i18n](docs/architecture/i18n.md) | Translation architecture and language detection |
| [SEO & discoverability](docs/architecture/seo-and-discoverability.md) | Site origin, canonical/OG tags, robots.txt, sitemap |
| [Testing strategy](docs/architecture/testing-strategy.md) | The four test levels and what each one catches |
| [Contact chat](docs/architecture/contact-chat-v1.md) | The phased design of the contact flow and what shipped |
| [Improvement canon](docs/architecture/improvement-canon.md) | The ten points that guide the project analysis and shape the deliverable PDF, their observable signals, and the single engagement they lead to (COD-42, not implemented) |
| [ADR index](docs/architecture/decisions/index.md) | Architecture decision records |
| [SDD workflow](docs/protocols/sdd-workflow.md) | Spec-driven development protocol |

---

## Conventions

- **Language** — user-facing communication in Spanish; code, comments and commit messages in English.
- **SOLID** — mandatory across the project. Business logic never depends on concrete implementations;
  external services are accessed only through abstractions in `src/utils/`.
- **SDD** — spec-driven development is required for structural changes: a new page or route, backend
  work, or any AI feature. Not required for CSS, content updates, bug fixes or dependency bumps.
- **Commits** — atomic, one logical change each, formatted `<type>: <short description>`.
- **Comments** — English, on non-obvious logic only. No speculative abstractions.

See [`CLAUDE.md`](CLAUDE.md) for the full working agreement.
