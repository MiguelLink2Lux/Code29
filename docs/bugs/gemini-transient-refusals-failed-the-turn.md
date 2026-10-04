> **Type:** Bug — **Status:** Fixed — **Date:** 2026-10-04 — **Severity:** High
> **Part of:** [[Bugs]]

# One refusal from the model, and the turn gave up

## Symptom

About one conversation turn in four answered `502` — "No he podido procesar tu mensaje.
Inténtalo de nuevo." — and the same message usually worked when sent again. Measured on
2026-10-04 against `code29-api.vercel.app`: a burst of 12 turns gave 7×502, and 8 turns
spaced 10 s apart gave 2×502. The deployment verifier still reported the deploy as passing.

## Root Cause

Two defects, one in the backend and one in the check that should have caught it.

1. **The turn made exactly one call to Gemini.** Every failure became `ModelUnavailable` →
   `502` straight away. The failures were transient: the Vercel logs read
   `model refused the request with 429` (free-tier quota, see [[0009-conversational-contact-agent]] §7)
   and `with 503` (overload), each answered in 0.4–1.5 s, plus the 30 s read hang first
   measured on 2026-09-02. A second call would usually have succeeded.
2. **The verifier read the turn's body whatever its status.** `verify-deployment.mjs` decided
   "model-driven" from `missing` in the response. A 502 body (`{"detail": ...}`) has no
   `missing`, so the check reported *"the stub is answering — GEMINI_API_KEY is missing or
   rejected"* — a false diagnosis — and only as a warning, so the run still passed.

## Fix

Commit `f582565` (Linear COD-69):

- `backend/app/services/extraction.py` — one retry on transport errors and 429/500/503/504,
  inside a 24 s budget for the whole turn (connect 3 s, read 20 s per attempt). A
  `Retry-After` is honoured when it fits the budget; one that does not fails at once, since a
  second call would be refused again. Without `Retry-After` the backoff is 1 s. The error
  message names Gemini's `error.status` (e.g. `RESOURCE_EXHAUSTED`) — never the provider's
  prose and never the visitor's text. A model failure is still a 502, never a fallback reply.
- `scripts/lib/conversation-check.mjs` + `scripts/verify-deployment.mjs` — the status is read
  first: any non-2xx turn **fails** the run as "the model failed (HTTP n)"; only a 200 from the
  stub warns "no model configured".

## Affected Files

- `backend/app/services/extraction.py`
- `backend/tests/test_extraction.py`
- `scripts/lib/conversation-check.mjs` (new)
- `scripts/verify-deployment.mjs`
- `tests/scripts/conversation-check.test.ts` (new)

## Prevention

- `test_extraction.py` covers every case: 503→200, 429→200 with and without `Retry-After`
  (seconds and HTTP-date), 500/504→200, hang→200, a persistent failure stopping after exactly
  two calls, non-transient 4xx never retried, the turn budget cutting a slow attempt, and the
  visitor's words never reaching the log or the error.
- `conversation-check.test.ts` pins the verifier's three readings: model, stub, failure.
- The durable lessons: **a free-tier dependency refuses as a matter of course — design for one
  retry, not zero.** And **a check that reads a body without reading the status will
  misdiagnose the failure it exists to catch.**
- Still open: the 429 delay Gemini puts in `error.details[].retryDelay` is not read, the
  verifier samples one turn, and the paid-tier decision waits on the new logs.

## References

- [[model-thinking-outlived-the-deadline]] — the earlier deadline defect this budget must not reintroduce
- [[0007-gemini-over-rest]] — the request shape and timeouts
- [[0009-conversational-contact-agent]] — the free-tier entitlement behind the 429s
- [[Bugs]] — parent index
