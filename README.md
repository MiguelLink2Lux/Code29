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
│   │   │                 cookies · legal-notice · privacy-policy
│   │   │                 robots.txt.ts — generated, not a static file
│   │   └── api/          contact.ts — serverless contact endpoint
│   ├── components/
│   │   ├── layout/       Nav · Footer
│   │   ├── sections/     Hero · Stats · EducationStack · Services
│   │   │                 Toolbelt · Testimonials · Contact
│   │   ├── contact/      ContactForm.vue
│   │   ├── cookies/      CookieBanner.vue
│   │   ├── analytics/    Analytics.astro
│   │   └── LanguageSwitcher.astro
│   ├── layouts/          BaseLayout · LegalLayout · StatusLayout
│   ├── i18n/             translations.ts — single source of truth for all copy (ES/EN)
│   ├── utils/            analytics · contact · cookie-consent · i18n
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
│   │   └── core/         config.py — env-driven Settings
│   ├── api/index.py      Vercel entrypoint — `from app.main import app`
│   ├── scripts/          gen-requirements.sh — regenerates requirements.txt
│   └── tests/            config · cors · health · requirements manifest
│                         vercel config · vercel entrypoint
├── tests/
│   ├── artifacts/        Assertions on the real build output (13 cases)
│   └── e2e/              Playwright specs — 4 files, 26 cases
├── vitest.config.ts              Unit gate
├── vitest.artifacts.config.ts    Build-artifact gate (needs `npm run build`)
├── .nvmrc                        Node 20 — see Deployment
└── docs/                 PRD · architecture · ADRs · protocols
```

External services (analytics, email, the future API) are reached **exclusively** through the
abstractions in `src/utils/` — see [SOLID](#conventions).

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
| `npm test` | Unit tests (`vitest run`) — 30 cases |
| `npm run test:watch` | Unit tests in watch mode |
| `npm run test:e2e` | End-to-end tests. Runs `scripts/assert-e2e-specs.mjs` first, then `playwright test` — **fails if `tests/e2e/` holds fewer than 4 spec files**, so a deleted spec breaks the gate instead of quietly shrinking coverage. |
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
| `POST` | `/api/contact` | Astro serverless route. Validates the payload, then sends the message via Resend. |

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
| `RESEND_API_KEY` | Resend API key. Required by `POST /api/contact`. |
| `CONTACT_TO_EMAIL` | Recipient of contact form submissions. Required. |
| `CONTACT_FROM_EMAIL` | Verified sender address. Required. |

If any of the three contact variables is missing, `POST /api/contact` responds `503` instead of failing silently.

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

> **Note:** copy `backend/.env.example` to `backend/.env` to get started — it ships the
> defaults above as placeholders.

In production both variables are set in the **backend** Vercel project's environment settings:

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
| 1 | **Landing v1** — 7 sections, GDPR cookie consent with granular categories persisted in `localStorage`, legal pages, contact form (Vercel serverless + Resend), centralized ES/EN i18n with a client-side switcher that does not change the URL | ✅ Complete |
| 2 | **FastAPI backend** — scaffolding: health endpoint, env-driven config, CORS. No database, no auth, no business logic. Deploys on Vercel as a second project ([ADR 0004](docs/architecture/decisions/0004-backend-deploy-provider.md)). | 🟡 Scaffolding |
| 3 | **AI services** | ⬜ Not started |

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
