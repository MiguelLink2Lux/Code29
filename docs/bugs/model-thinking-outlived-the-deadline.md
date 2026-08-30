> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-30 — **Severity:** Critical
> **Part of:** [[Bugs]]

# The model was thinking, and the deadline did not know it

## Symptom

Every message to the contact chat answered `502` after roughly twenty seconds.
`POST /api/v1/contact/conversation/turn` → `http=502 total=22.06s`, body
`{"detail":"No he podido procesar tu mensaje. Inténtalo de nuevo."}`. The chat was
unusable in production for every visitor, not for some.

`GET /api/v1/health` answered `200` in 0.58 s throughout: the function and the
deployment were healthy.

## Root Cause

`GeminiFactExtractor.extract()` sent no `thinkingConfig`, and `gemini-3.6-flash`
defaults to `thinkingLevel: "medium"` — documented behaviour of the Flash 3.x family,
and not what the previous model did. That reasoning did not fit inside
`REQUEST_TIMEOUT_SECONDS = 20.0`, so httpx raised `ReadTimeout`, which the endpoint
correctly converted into `ModelUnavailable` → `502`.

The decisive evidence was the clock, not the code: Vercel recorded
`Execution Duration: 20.04s` — the httpx timeout **to the centisecond**. An invalid key
or a retired model answers `4xx` in under a second; only a deadline produces its own
number back.

Two properties made this expensive to diagnose:

- **The default moved under us.** Nothing in the repository changed. A model provider
  changed what its model does when a field is omitted.
- **The 502 left no trace.** The runtime logs for that request contained the status code
  and nothing else — no exception class, no reason. The cause had to be inferred from
  the duration.

## Fix

- `generationConfig.thinkingConfig = {"thinkingLevel": "low"}` — the floor these models
  accept (`minimal` is refused on Flash 3.x, and `thinkingBudget` cannot travel with
  `thinkingLevel`: sending both is a `400`). Extraction reads facts out of one sentence;
  there is nothing there to reason about.
- `REQUEST_TIMEOUT_SECONDS` 20.0 → 30.0, matching the report generator. Two different
  deadlines against one provider were a coincidence, not a decision.
- The failure is now logged with its exception class before becoming a 502.

Commit `033f344`, PR #50, COD-63. Measured after deploy: `200` in 16.8 s (cold start),
then 2.05 s and 1.77 s.

## Affected Files

- `backend/app/services/extraction.py`
- `backend/app/api/v1/conversation.py`

## Prevention

- `test_extraction.py` asserts the payload carries `thinkingLevel: "low"` and no
  `thinkingBudget`, and that the extractor's deadline equals the report generator's.
- `test_conversation_turn_api.py` asserts a model failure logs its cause and still
  answers 502 — and that the visitor's own words never reach the log.
- The durable lesson: **when pinning a model, pin its reasoning level too.** A default
  is a decision someone else can change.

## References

- [[0007-gemini-over-rest]] — the request shape this amends
- [[a-mistyped-code-became-a-message]] — the other defect found in the same session
- [[Bugs]] — parent index
- [[testing-strategy]] — where the preventions land
