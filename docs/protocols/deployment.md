> **Type:** Protocol — **Status:** Active
> **Part of:** [[Protocols]]

# Deployment and Post-Deploy Verification

## Purpose

Two Vercel projects serve this repository ([[0004-backend-deploy-provider]]), and
the failures that actually happen are **configuration** failures: a variable that never
reached a build, a key the provider rejects. None of them fail a test suite, and several of
them are invisible in the HTML. This protocol says where things run, which variables each
project needs, and how a deployment is verified from the outside.

## When to Apply

After every production deploy, and before declaring any contact-flow work done.

## Topology

| Project | Root directory | Serves | Origin |
|---|---|---|---|
| Frontend | `.` | Astro landing + the contact island | `https://code29.dev` |
| Backend | `backend/` | FastAPI, `/api/v1/*` | `https://api.code29.dev` |

Both deploy by Git integration: a merge to `main` publishes production, a PR publishes a
preview. There is no deploy workflow in GitHub Actions and none is needed.

The backend answers on its own domain, `api.code29.dev`, rather than on the project's
`*.vercel.app` origin. The reason is that the frontend compiles the value in: a bundle that
names a Vercel project URL has to be rebuilt if that project is ever renamed or replaced,
whereas a domain we own can be repointed.

`backend/vercel.json` carries no rewrite, deliberately. A catch-all rewrite to `/api/index`
is not transparent: the function then receives that literal path for every request and
FastAPI answers 404 to all of its routes, `/docs` included, while serving them perfectly
under uvicorn.

## Environment variables

Frontend — `PUBLIC_*` variables are **inlined into the compiled bundle** at build time. An
absent one is invisible in the HTML and only shows up as a broken chat, so both are verified
by reading the shipped chunk.

| Variable | Value | Symptom when missing |
|---|---|---|
| `PUBLIC_API_BASE_URL` | `https://api.code29.dev` | The chat calls `http://localhost:8000` from the visitor's browser |
| `PUBLIC_TURNSTILE_SITE_KEY` | public half of the Turnstile key | `TurnstileNotConfigured` → the chat says "el servicio no está disponible" |
| `PUBLIC_SITE_URL` | `https://code29.dev` | Canonical URLs and `og:image` fall back to the default origin |

Backend — every contact-flow variable is required together; a partial set answers 503 by
design rather than half-working.

| Variable | Purpose |
|---|---|
| `CONTACT_TOKEN_SECRET` | Signs verification codes, access tokens and conversation envelopes. 32+ chars, a hard boot failure in production if shorter |
| `RESEND_API_KEY` | Sends the verification code and the report |
| `CONTACT_FROM_EMAIL` | Verified sender. **Must belong to the verified domain** |
| `CONTACT_TO_EMAIL` | Mailbox that receives the owner copy of every lead |
| `TURNSTILE_SECRET_KEY` | Private half of the human check. Pairs with `PUBLIC_TURNSTILE_SITE_KEY` on the frontend: both halves come from **one** Cloudflare widget, and a real site key with a test secret verifies nothing |
| `GEMINI_API_KEY` | Optional. Present → a model conducts the conversation; absent → the deterministic stub does |
| `REPORT_GENERATOR` | `stub` or `gemini`. `gemini` without a key refuses rather than emailing a template as if a model wrote it |

**`GEMINI_API_KEY` is declared in exactly one place: `ReportDeliverySettings`.** Both the
report generator and the conversation extractor read it from there. Do not add the field to
`Settings` — two sources for one key is what caused
[[gemini-extractor-never-wired]].

## Verification

    node scripts/verify-deployment.mjs --site https://code29.dev --api https://api.code29.dev

Required checks failing exits non-zero; optional ones report as `warn` because they depend on
configuration only the owner can complete. What the contact-flow checks mean:

| Check | Red means |
|---|---|
| `PUBLIC_API_BASE_URL reached the build` | The bundle still contains `localhost:8000` — set it on the frontend project and redeploy |
| `PUBLIC_TURNSTILE_SITE_KEY reached the build` | No site key compiled in; every code request will answer "unavailable" |
| `the conversation is model-driven` | The stub is answering: `GEMINI_API_KEY` is absent or the model rejected the request |
| `contact flow is configured` (503) | Backend variables still missing |
| `the mail provider accepts our sends` (502) | The flow is configured and **Resend refused**. The reason is in the backend logs |

## Diagnosing a refused email

A refused send is a 502 to the visitor with a deliberately uniform message. The reason is
logged, never returned: `verification email refused: mail transport rejected the message with
403 (validation_error: …)`. Only Resend's own `name` and `message` fields are kept, truncated
to 300 characters, with the recipients censored out — a delivery error reaches logs, and the
address is personal data.

Usual causes, in the order worth checking: `CONTACT_FROM_EMAIL` outside the verified domain ·
an API key scoped to a different domain · the account still in sandbox, which only delivers
to the account's own address.

## Turnstile: never ship the test keys to production

Cloudflare publishes a key pair that approves every token by design — site key
`1x00000000000000000000AA`, secret `1x0000000000000000000000000000000AA`. They are the right
thing in Preview and Development, because a preview lives on `*.vercel.app` and that hostname
cannot be claimed in a Turnstile widget.

In Production they are an open door. `/contact/verification/request` mails a code to any address
the caller names, and with no store there is no per-address limit, so this challenge is the only
thing standing between that endpoint and being an email amplifier — which costs the domain its
sending reputation, not just money.

How to tell from outside, in one request: post a made-up token.

    curl -X POST https://api.code29.dev/api/v1/contact/verification/request \
      -H 'Content-Type: application/json' \
      -d '{"email":"nobody@example.com","turnstileToken":"dummy"}'

**403 means the gate is real.** Anything else — 502, 200 — means the token was accepted, and the
test secret is live.

## References

- [[Protocols]] — parent hub
- [[0004-backend-deploy-provider]] — why two projects
- [[gemini-extractor-never-wired]] — the defect this verification now catches
- [[0009-conversational-contact-agent]] — what the contact flow does
