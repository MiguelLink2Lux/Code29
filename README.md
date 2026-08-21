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
| Tests | Vitest (unit) · Playwright (e2e) · pytest (backend) |

---

## Repository structure

```
.
├── src/
│   ├── pages/            index · 404 · coming-soon · maintenance
│   │   │                 cookies · legal-notice · privacy-policy
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
│   │                     (+ colocated *.test.ts)
│   └── styles/           tokens.css — design system tokens
├── backend/
│   ├── app/
│   │   ├── main.py       create_app() factory + module-level app
│   │   ├── api/v1/       router.py · health.py
│   │   └── core/         config.py — env-driven Settings
│   └── tests/            conftest · test_config · test_cors · test_health
├── tests/e2e/            Playwright specs
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
| `npm test` | Unit tests (`vitest run`) |
| `npm run test:watch` | Unit tests in watch mode |
| `npm run test:e2e` | End-to-end tests (`playwright test`) |
| `npm run lint` | ESLint |
| `npm run format` | Prettier |

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
| `PUBLIC_GA4_ID` | GA4 measurement ID. The script loads **only** after the visitor grants analytics consent. |
| `RESEND_API_KEY` | Resend API key. Required by `POST /api/contact`. |
| `CONTACT_TO_EMAIL` | Recipient of contact form submissions. Required. |
| `CONTACT_FROM_EMAIL` | Verified sender address. Required. |

If any of the three contact variables is missing, `POST /api/contact` responds `503` instead of failing silently.

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
> new deployments since 2025-09-01. Building on Vercel makes the local Node version irrelevant.
> `.nvmrc` and `package.json` → `engines` pin Node 20 for local work.

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
