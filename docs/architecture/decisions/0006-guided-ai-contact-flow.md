> **Type:** Architecture · ADR — **Status:** Accepted (report structure partially superseded by 0008) — **Date:** 2026-08-22

# ADR 0006 — Guided AI contact flow with stateless email verification

- **Status:** Accepted — **partially superseded by** [[0008-improvement-canon]]
- **Date:** 2026-08-22
- **Deciders:** Miguel Navarro Mantas

> **Scope of the supersession.** [[0008-improvement-canon]] replaces **the structure of the
> report's diagnosis only**: the five `DiagnosisAxis` members become the ten fixed points of
> [[improvement-canon]], each with an observable signal and a primary service. Everything else
> decided here stands unchanged — the fixed step flow and its order as an authorisation rule,
> stateless verification, the Turnstile gate, the SSRF-guarded site analysis, the
> facts-not-instructions contract with the model, and the privacy posture. Where this ADR says
> "four structured diagnosis axes" or "five axes", read the canon instead.

## Context and Problem Statement

Phase 3 of [[contact-chat-v1]] replaces the Phase 1 contact form with a conversational
capture flow whose payoff is a **generated workflow report**: the visitor answers questions
about how their team ships software, the backend measures objective signals from their home
page, and an AI-drafted diagnosis arrives by email.

That payoff is also the problem. Three of the steps are *expensive* in a way a contact form
never was:

1. Sending an email to an address the caller merely claims to own.
2. Making an outbound HTTP request to a URL a stranger typed — an SSRF primitive wearing the
   backend's network identity.
3. Calling a paid model to draft a document.

The backend, per [[0004-backend-deploy-provider]], runs as a Vercel serverless function: no
persistent process, no database, no cache, nothing to hold a rate-limit counter or a
one-time-code table. Every abuse control therefore has to work **without state**.

## Decision Drivers

- Nothing expensive may run for a visitor who has not proven control of an email address.
- No datastore. Adding one for a lead-capture flow is disproportionate at this stage, and the
  host does not offer a persistent process to talk to one efficiently.
- Prompt injection must be closed by design, not by filtering: the visitor's text reaches an
  LLM path.
- Lead data is PII. The less that is stored anywhere — browser, logs, email payload — the less
  there is to leak.
- One contact path and one email sender. The Phase 1 duplicate was already a source of drift.

## Considered Options

1. **Free-form chat driven by the model**, extracting fields from natural language.
2. **A fixed eleven-step flow** with per-step validation, where the model only *drafts the report*.
3. **Stateful verification** — store codes and rate-limit counters in a database or KV store.
4. **Stateless verification** — derive the code cryptographically, carry authorisation in a
   signed token.
5. **Keep the Phase 1 form alongside the chat** as a fallback path.

## Decision Outcome

### 1. The flow is fixed, and its order is an authorisation rule

Eleven steps, in this order, defined declaratively in `src/utils/contact-chat-flow.ts`:

```
name → company → email → code → delivery → bugs → deploys → security → observability
     → website → consent
```

*(Corrected 2026-08-23: this list previously read "ten steps" and omitted `observability`,
which `CONTACT_CHAT_STEPS` has always contained. The five practice steps —
`delivery`, `bugs`, `deploys`, `security`, `observability` — are the five `DiagnosisAxis`
members, replaced by the ten-point canon in [[0008-improvement-canon]].)*

Chosen over free-form chat (option 1): a deterministic sequence yields structured, comparable
answers, validates per step, and keeps the model out of the data-extraction path entirely.

The **order is load-bearing, not cosmetic**. Everything expensive sits *after* `code`:
`website` triggers the outbound fetch, `consent` triggers report generation and delivery. An
unverified visitor can reach nothing that costs money or makes a request on our behalf. Read
the step list as an access-control policy expressed as a UI.

### 2. Email verification is stateless

Chosen over option 3 (a store), accepting the consequences below.

- **The code is derived, not stored.** `derive_code()` in `backend/app/services/tokens.py`
  takes HMAC-SHA256 over `normalize_email(email) | time_bucket | purpose` with
  `CONTACT_TOKEN_SECRET`, and folds the digest into six decimal digits. The server recomputes
  and compares instead of remembering. `verify_code()` accepts the current 10-minute bucket
  **and the previous one**, so a visitor who receives the code a second before a boundary is
  not rejected — the real validity window is 10–20 minutes. Comparison uses
  `hmac.compare_digest`, so a wrong code leaks no positional hint.
- **Authorisation is a signed token.** A correct code is exchanged at
  `POST /api/v1/contact/verification/confirm` for `base64(payload).base64(HMAC)` carrying the
  verified address, a 30-minute expiry and a purpose. The downstream endpoints trust that
  token and nothing else — a report request whose body names a different address cannot
  redirect the email, because the recipient is read from the token.
- **Refusals are uniform.** Every rejected code returns the same body, so the endpoint does
  not become an oracle for which addresses exist. No address is ever written to a log.

### 3. Cloudflare Turnstile gates every outbound email

`POST /api/v1/contact/verification/request` verifies a Turnstile token **before** sending
anything. With no store there is no per-address counter and no per-IP counter, so without this
challenge the endpoint is an email amplifier: anyone could ask it to mail a code to any address,
repeatedly. Turnstile is the only abuse control standing there.

It **fails closed**. An outage, a non-200 response or an unparseable body raises
`TurnstileUnavailable`, which the endpoint turns into `503` — never into a permissive default.
`AlwaysPassVerifier` exists for tests only and cannot reach a production path: the factory
requires a secret.

### 4. The Phase 1 contact form is retired

Deleted, not deprecated: `src/components/contact/ContactForm.vue`,
`src/pages/api/contact.ts`, `src/utils/contact.ts` and their tests. Option 5 (keep both) was
rejected — two contact paths mean two payload shapes, two validation rules and two senders of
email drifting apart, which had already happened once.

One consequence is a real loss: the old form's **honeypot field is gone**. What replaces it is
stricter — a verified email address plus a Turnstile challenge — but it is a different control,
not the same one relocated. The backend is now the single email sender; the frontend holds no
Resend credentials at all.

### 5. The AI only drafts; it never parses the visitor

The generator port receives `ReportFacts`: the validated step answers plus `SiteSignals`
measured from the home page. There is **no field for free text instructions and no field for
an email address**. The visitor's prose can therefore never arrive as a prompt, and the one
piece of PII the flow holds never reaches the model. This bounds prompt injection structurally
instead of filtering for it.

Today the generator is a deterministic stub. `REPORT_GENERATOR=genkit` **raises**
(`UnusableReportGenerator`) unless the dependency and `GEMINI_API_KEY` are both present — it
never silently degrades to the stub, because shipping a template report while the operator
believes a model wrote it is worse than failing loudly.

### 6. Privacy posture

- In-progress answers live in **`sessionStorage`, deliberately not `localStorage`**: lead data
  dies with the tab.
- The access token is never persisted and never enters the transcript.
- The report request body carries no email address.
- Secrets are `SecretStr`, so a settings object reaching a log does not carry them along.
- No PII in logs — the site-analysis route logs the target *host*, never the full URL, since a
  URL can carry identifying query parameters.

### Consequences

**Accepted costs of statelessness**

- **A code cannot be revoked before its window expires**, and **single use cannot be
  enforced**. Both need a store. Within the 10–20 minute window a leaked code stays usable and
  is usable more than once.
- **No rate limiting per address.** Turnstile bounds automated abuse, but a human solving
  challenges can request codes for many addresses. There is no counter to consult.
- **A leaked `CONTACT_TOKEN_SECRET` forges both codes and tokens.** Rotation is the only
  remedy; it invalidates every outstanding code and token, which is the correct behaviour.
  Production boot fails on a secret shorter than 32 characters.

**Open security risks, named rather than smoothed over**

- **DNS rebinding.** `url_guard` resolves the hostname and requires every returned address to
  be publicly routable, but `httpx` resolves again when it connects. A hostname that answers
  with a public address on the first lookup and a private one on the second passes the guard.
  Closing this needs a pinned-IP connection, which is not implemented.
- **Ports 80/443 only.** This blocks the endpoint being used as a general port scanner, at the
  cost of legitimate sites on other ports being unanalysable.
- **The HTML is parsed with regular expressions**, not a parser. Signals can be missed or
  misread on unusual markup. Acceptable because every signal is advisory and a page that
  cannot be read is reported as "not analysed", never as a negative finding.

**Operational**

- **The flow is all-or-nothing per deployment.** `contact_flow_enabled` is true only when all
  five backend variables are set; otherwise the endpoints answer `503` rather than
  half-working. Local development needs no ceremony.
- **Two settings objects exist** (`Settings` and `ReportDeliverySettings`), an artifact of two
  phases being built in parallel. Merge task, tracked in the modules' own docstrings.
- **The report generator is a stub until `GEMINI_API_KEY` exists**, so Phase 3 is in progress,
  not complete.

## References

- [[contact-chat-v1]] — the phased design this ADR implements Phase 3 of
- [[0002-fastapi-as-backend-framework]] — the backend serving the flow
- [[0003-api-versioning-strategy]] — the `/api/v1` prefix the endpoints live under
- [[0004-backend-deploy-provider]] — the stateless serverless host that forces these choices
- [[testing-strategy]] — the four gates covering the flow
- [[0008-improvement-canon]] — the ten-point canon that supersedes this ADR's report structure
- [[improvement-canon]] — the canon itself: points, signals, service mapping
- [[index]] — ADR index
