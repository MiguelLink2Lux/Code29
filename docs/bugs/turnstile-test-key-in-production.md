> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-27 — **Severity:** Critical
> **Part of:** [[Bugs]]

# The only anti-abuse gate ran on a key that approves everything

## Symptom

Nothing. That is the whole difficulty of this one: a production deployment whose human
verification approved every caller looked exactly like one whose verification worked.

It surfaced only when probed directly on 2026-08-26:

    curl -X POST https://api.code29.dev/api/v1/contact/verification/request \
      -H 'Content-Type: application/json' \
      -d '{"email":"nobody@example.com","turnstileToken":"dummy"}'
    → 502 {"detail":"Could not send the verification email. Try again shortly."}

A token that was never issued by anyone — the literal string `dummy` — **passed the challenge**.
The 502 is the giveaway: the request failed at the mail provider, which it can only reach *after*
the gate has let it through. A real secret answers 403 and never gets that far.

So the only thing preventing abuse was that sending happened to be broken. Fixing the mail path
would have opened the endpoint, and the fix and the exposure would have looked like the same
deploy succeeding.

## Root Cause

Two independent causes, and the second is the one worth remembering.

**The configuration was wrong.** Cloudflare's test pair — site key `1x00000000000000000000AA`,
secret `1x0000000000000000000000000000000AA` — was set in Vercel's Production environment. It is
the correct choice for Preview, whose deployments live on `*.vercel.app`, a hostname no Turnstile
widget can claim. It reached Production because the environment scoping was never narrowed.

**Nothing in the code could tell the two secrets apart.** `Settings.contact_flow_enabled` asked
only whether `TURNSTILE_SECRET_KEY` was *non-empty*. The test secret is non-empty, so by every
check the system had, the flow was fully configured. `HttpTurnstileVerifier` then did its job
correctly and faithfully: it asked Cloudflare, and Cloudflare — as documented — said yes.

The module's docstring already stated the invariant that was being violated:

> The verification-code endpoint can send mail to any address a caller names, and the stateless
> design (no store) has no per-address counter, so this challenge is what stops the endpoint
> being an email amplifier.

An invariant written in a docstring is a comment. Nothing executed it.

Why it stayed invisible:

- **It fails open, and open looks like working.** Every other misconfiguration in this flow
  degrades loudly — a missing variable is a 503, a refused send is a 502. This one returns 202
  and mails the code, which is the success path.
- **The frontend check could not see it.** `verify-deployment.mjs` already caught the *site* key
  by reading it out of the shipped bundle. The *secret* lives only in the backend environment and
  appears in no artifact, so no amount of inspection from outside reveals it — only the
  endpoint's own answer to a token it should reject.
- **The blast radius is reputational, not financial.** The cost is not Resend's invoice: it is
  thousands of unsolicited codes sent *from* `code29.dev` to addresses their owners never gave
  us, which is what moves a domain to spam folders and gets a sending account suspended.

## Fix

`TEST_SECRET_KEY` is now a named constant in `app/services/turnstile.py` — the module that owns
the gate — and `Settings` treats it as an absent secret when `APP_ENV` is production:

    if self.is_production and self.turnstile_runs_on_the_test_secret:
        return "TURNSTILE_SECRET_KEY is Cloudflare's test secret, which approves every token; …"

`contact_flow_enabled` is now derived from `contact_flow_disabled_reason`, one place that answers
*why* the flow is off and names the variable at fault. The endpoint refuses with 503 **before
reaching the mailer**. Preview and local work are untouched: there the test pair is the only
thing that can work.

The reason goes to the platform log, never into the response. A 503 that told an anonymous caller
which variable is missing would be a configuration oracle.

Shipped in commit `0b0b2b4` (PR #37). Gates after: 512 backend tests passing, 124 frontend,
`ruff` clean.

**This fix does not restore the flow.** It closes the door; the real widget secret still has to be
uploaded to Vercel before contact works again (COD-49).

## Affected Files

- `backend/app/core/config.py` — `contact_flow_disabled_reason`, the test-secret rule
- `backend/app/services/turnstile.py` — the constant, documented where the gate lives
- `backend/app/api/v1/contact.py` — the reason is logged, not returned
- `scripts/verify-deployment.mjs` — the outside check that would have caught it
- `backend/tests/test_contact_settings.py`, `backend/tests/test_contact_verification_api.py`

## Prevention

- **A test credential must be recognisable to the code, not only to the person who set it.**
  Every provider that publishes an always-passing key publishes a *fixed, known* one. Pin it as a
  constant and refuse it where it must not run. "Is it non-empty?" is not a configuration check
  for a security control.
- **An invariant in a docstring is not enforced.** `turnstile.py` described precisely the abuse
  this defect enabled, and had described it correctly for weeks. If a sentence in a comment states
  a rule the system depends on, something must assert it.
- `verify-deployment.mjs` now posts an invented token and requires a refusal. This is the only
  check in the suite that can see the backend secret at all, because it observes behaviour rather
  than configuration — the same lesson as [[gemini-extractor-never-wired]], where a wiring defect
  was invisible until something asked the deployment what it actually did.
- **A control that fails open needs a probe that fails closed.** For the checks that degrade
  loudly, absence is its own alarm; for this one, only an active attempt to get through counts as
  verification.

## References

- [[Bugs]] — parent index
- [[deployment]] — the Turnstile section, and how to read the one-request diagnosis
- [[gemini-extractor-never-wired]] — same shape: a silent default nothing asserted
- [[0006-guided-ai-contact-flow]] — the stateless design that leaves this gate alone
- [[0009-conversational-contact-agent]] — what the protected flow does
