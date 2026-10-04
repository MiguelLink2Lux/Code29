---
title: 'COD-69 — Conversation turns fail intermittently against Gemini; the verifier passes it'
type: 'bugfix'
ticket: ''
created: '2026-10-04'
status: 'built'
baseline_revision: '1eceba5a4aaa850945c29a19d9cdbd08d4e7e2e8'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** About one conversation turn in four answers 502 in production, so visitors starting the contact chat hit "No he podido procesar tu mensaje" at random. `scripts/verify-deployment.mjs` reports that state as a passing deploy and blames the stub (Linear COD-69, Urgent).

**Approach:** Make the turn's single call to Gemini survive the transient failures it actually meets — one retry within a bounded budget, with connect and read timeouts split — and log the provider's own error reason so the next failure is diagnosable. Make the verifier fail a deploy whose turn endpoint answers 502, with a message that tells a model failure from a missing model.

## Boundaries & Constraints

**Always:** A model failure stays a 502 — never a fallback reply (`conversation.py:206-212`). The visitor's text is never logged (`conversation.py:213`). At most one retry, and the whole turn (both attempts plus backoff) stays under 25 s so the visitor waits less than today's 30 s worst case. Turn-level behaviour verified with several consecutive calls, never one.

**Decisions:** Quota (2026-10-04, user): ship the retry and diagnostics now on the free tier; decide on a paid Gemini tier later, from what the new logs say about which limit is hit. Retry-After beyond the budget (2026-10-04, user, review pass 1): fail at once with no second call — "short fixed backoff" in the matrix applies only when no usable Retry-After is given. Plan kept whole despite exceeding the token target (single goal).

**Never:** No change to the report generator (`report_gemini.py`, `grounded_report.py`) — its single end-of-chat call is a different path. No stub fallback. No change to Gemini model, prompt or `thinkingLevel`. No billing / tier change from code.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Gemini 200 first try | Turn 200, one call | — |
| Transient overload | Gemini 503 then 200 | Turn 200, two calls | warning logged for the first failure |
| Rate limited | Gemini 429 then 200 | Turn 200, two calls | backoff honours `Retry-After` when it fits the budget, otherwise a short fixed backoff |
| Hang | read timeout then 200 | Turn 200, two calls, total < 25 s | — |
| Persistent failure | 503/429/timeout twice | `ModelUnavailable` → 502, no third call | log carries HTTP status and Gemini `error.status` (e.g. `RESOURCE_EXHAUSTED`), never visitor text |
| Non-transient refusal | Gemini 400/401/403 | `ModelUnavailable` → 502 immediately, no retry | — |
| Verifier, model ok | turn 200, `contact_name` not in `missing` | check passes | — |
| Verifier, stub | turn 200, `contact_name` in `missing` | check warns "no model configured" (non-blocking, as today) | — |
| Verifier, model failing | turn 502 (or any non-2xx) | check **fails**, exit code non-zero, message "the model failed (HTTP 502)" | — |

</frozen-after-approval>

## Code Map

- `backend/app/services/extraction.py:50-52` -- `REQUEST_TIMEOUT_SECONDS = 30.0`, shared on purpose with `report_gemini.py:45` ("one number for one provider"). The turn needs its own budget now; keep the report's constant untouched and give the extractor a named `httpx.Timeout(connect=…, read=…)` plus a total budget, with a comment saying why it diverges.
- `backend/app/services/extraction.py:229-239` -- the single `client.post`; `httpx.HTTPError` → `ModelUnavailable(type name)`; `response.is_error` → `ModelUnavailable(status)`. Wrap in a one-retry loop: retry on `httpx.TimeoutException`/`httpx.TransportError`, 429 and 503 (also 500/504); no retry on other 4xx. Parse Gemini's error body (`{"error": {"status": ..., "message": ...}}`) defensively into the exception message (status only, no echo of our payload).
- `backend/app/services/extraction.py` constructor (`:182`) already takes `transport`; add an injectable `sleep` (default `asyncio.sleep`) so tests do not wait.
- `backend/app/api/v1/conversation.py:203-218` -- already logs `type: message` at warning and maps to 502. No change needed beyond the richer message coming from the extractor.
- `backend/tests/test_extraction.py:128-216` -- existing `httpx.MockTransport` pattern; add the matrix cases here.
- `scripts/verify-deployment.mjs:235-252` -- the "model-driven" check reads `missing` regardless of HTTP status; a 502 body `{"detail": ...}` is reported as "the stub is answering". `record(name, ok, detail, blocking=true)` — the 4th arg `false` makes it a warning. Extract the decision into a pure function in a new `scripts/lib/conversation-check.mjs` (status, body → `{ok, blocking, detail}`) and call it from the script.
- `tests/scripts/` -- vitest already includes `tests/scripts/**/*.test.ts` (COD-36); add `conversation-check.test.ts` for the three verifier rows.
- Evidence (2026-10-04, against `code29-api.vercel.app`, `code29.dev` DNS is down — COD-70): burst of 12 turns → 7×502 in 0.4–1.5 s; 8 turns spaced 10 s → 2×502. Vercel logs: `model refused the request with 429` (×several) and `with 503` (×several); no timeouts seen today. The 2026-09-02 30 s hang (ReadTimeout) is the issue's original measurement.
- ADR 0009 §7 (`docs/architecture/decisions/0009-conversational-contact-agent.md:269-277`): the project is on Gemini's free tier (grounding 429 = entitlement).

## Tasks & Acceptance

**Execution:**
- [x] `backend/tests/test_extraction.py` -- RED first: one test per extractor matrix row (503→200, 429→200 with and without `Retry-After`, timeout→200, twice-failing → `ModelUnavailable` with status and `error.status` in the message and exactly two calls, 400 → no retry) -- regression for COD-69
- [x] `backend/app/services/extraction.py` -- split timeouts, one bounded retry on transient failures, provider reason in the error message, injectable sleep -- the fix
- [x] `tests/scripts/conversation-check.test.ts` -- RED first: the three verifier rows -- regression for the false "stub" diagnosis
- [x] `scripts/lib/conversation-check.mjs` + `scripts/verify-deployment.mjs` -- pure decision function; the script records it blocking on non-2xx -- the verifier fix

**Acceptance Criteria:**
- Given the backend suite, when `uv run pytest` runs, then every extractor matrix row has a passing test and nothing else regresses.
- Given the deployed preview of this branch, when 8 turns are sent 10 s apart, then none waits more than 25 s, and every non-200 left is a `RESOURCE_EXHAUSTED`-class quota refusal visible in the logs (not a hang, not an unexplained 502).
- Given a turn endpoint answering 502, when `node scripts/verify-deployment.mjs` runs against it, then it exits non-zero and names a model failure, not the stub.

## Implementation Notes

- Budget: `REQUEST_TIMEOUT = httpx.Timeout(20.0, connect=3.0)` per attempt (read 20 s, not 10: the COD-63 cold-start turn measured 16.8 s), `TURN_BUDGET_SECONDS = 24.0` for the whole turn enforced with `asyncio.timeout` around each attempt (httpx timeouts are per read, not per request), `RETRY_BACKOFF_SECONDS = 1.0`. Retryable: transport errors and 429/500/503/504.
- `Retry-After`: integer seconds honoured when wait + connect timeout still fits the budget; absent or HTTP-date form → fixed backoff; too large → fail fast with no second call (reconciles the matrix row with the Critical Section edge case).
- Error message keeps the old prefix `model refused the request with <code>` (existing log searches still match) and appends Gemini's `error.status` only when it is an `UPPER_SNAKE` enum; the provider's `message` prose is never included.
- The old test `test_it_matches_the_one_the_report_generator_uses` asserted the shared 30 s constant; it contradicts this plan's intent and was replaced by budget/split-timeout tests plus one pinning the report's 30 s.
- Verifier: `record()`'s 4th arg is named `required` in the script; the pure function returns `blocking` and the script passes it there. An unreachable turn endpoint (no status) is also blocking.
- Verification: backend `uv run pytest` 673 passed; `ruff check` clean; vitest 200 passed; eslint clean on touched files. `verify-deployment.mjs` against a local fake answering 502 on the turn → `FAIL the model failed (HTTP 502)`, exit 1. Acceptance criterion 2 (8 turns 10 s apart on the deployed preview) not run — needs a deploy of this branch.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — high 0 · medium 2 · low 2 · maybe-false 1 · deferred 3

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | Retry-After beyond budget fails fast, matrix row ambiguous | medium | intent_gap → resolved by user (a): fail fast, recorded in frozen Decisions | Matrix "otherwise a short fixed backoff" read two ways; code + test already implement (a) |
| 2 | Budget path (`asyncio.timeout` → "exceeded the turn budget"), retry on 500/504 and HTTP-date Retry-After untested | low | patch | No test reaches those branches; MockTransport raises instantly |
| 3 | Read timeout 10 s reintroduces COD-63: cold first turn measured 16.8 s (`docs/bugs/model-thinking-outlived-the-deadline.md`) | medium | patch | Non-streaming `generateContent` sends nothing until done; read 20 s + connect 3 s still fits the 24 s budget |
| 4 | 1 s backoff on 429 likely hits the same quota window; Gemini puts the delay in `error.details[].retryDelay` | maybe-false (medium) | defer | Needs a live 429 body to confirm; the new logs will show it |
| 5 | Verifier samples one turn, so an intermittent failure can still pass | medium | defer | Sampling N turns spends free-tier quota on every verification — separate decision |
| 6 | ADR 0007:80 and the COD-63 bug doc still state one 30 s deadline | low | defer → doc-guardian on completion | Docs owned by doc-guardian |

## Design Notes

### Critical Section

- **Conflict with existing logic:** `extraction.py` and `report_gemini.py` deliberately share one 30 s constant. The turn now gets its own budget; the comment must say the two diverge because a turn is interactive and the report is not. The report path is untouched.
- **Debt introduced:** retry logic lives in the extractor only; the report generator and grounded report keep their single call. A shared Gemini transport helper would remove the duplication but widens scope — deferred.
- **Side effects:** a retried 429 consumes one more request of the free-tier quota; with one retry max this at most doubles calls on failing turns. Logs gain the provider's error status — no visitor text, no API key.
- **Edge cases not covered:** sustained quota exhaustion (free-tier daily or per-minute cap) is not solvable in code — retries only absorb short bursts. A `Retry-After` larger than the remaining budget is not honoured; the turn fails fast instead.
- **Alternatives discarded:** stub fallback (violates the 502 invariant); two or more retries (turns a hang into 60–90 s); raising the timeout (the measured failures are fast refusals, a longer wait would not help); client-side retry in the Vue island (hides the cause and doubles visitor wait).

### SOLID Check

- **S:** retry policy is a small private helper inside the extractor, separate from payload building and parsing — no new responsibility leaks into `conversation.py`.
- **D:** the extractor already receives `transport`; adding an injectable `sleep` keeps it testable without real time. No violations found.
