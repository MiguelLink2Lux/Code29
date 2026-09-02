> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-30 — **Severity:** Critical
> **Part of:** [[Bugs]]

# A validator ran at import time, so a short secret took the whole service down

## Symptom

2026-08-29/30: every route of the backend returned 500 `FUNCTION_INVOCATION_FAILED` —
`/api/v1/health` and `/docs` included, on both `api.code29.dev` and
`code29-api.vercel.app`. Twenty minutes earlier the deployment verifier had passed 26/26.

From outside, the diagnosis available was "everything is broken", which names nothing.

## Root Cause

`CONTACT_TOKEN_SECRET` had been set in Vercel two dozen characters short of its 32-character
minimum. `_require_strong_secret_in_production` raised, correctly — and `create_app()` runs at
module level, so the exception happened during import. The function never started, so there was
no HTTP layer left to answer with which variable was wrong.

The validator was right. **When** it failed was the defect: a value nobody could see turned into
a total, opaque outage, and the process knew the variable's name the whole time.

A second trigger of the same class: `GEMINI_GROUNDING` set to an empty string. `gemini_grounding`
is a `bool`, pydantic cannot coerce `""`, and the import dies the same way. In a panel like
Vercel's, leaving a field empty is what happens when someone saves a variable half-written; the
result should not be distinguishable from not having it at all.

### The diagnosis error, recorded on purpose

The first hypothesis was the correct one and was **discarded wrongly**. The local sweep set each
variable to an *empty* value, while the real fault was a *short* one — a case the sweep never
touched. The conclusion ("it is `GEMINI_GROUNDING`") was stated with confidence and was false.

A sweep that tests one way of being wrong does not rule out the others. Against a startup crash,
the production traceback is worth more than any reproduction: it names the variable.

## Fix

The weak-secret rule moved to `contact_flow_disabled_reason`, where every other configuration rule
already lives. The security property is unchanged — a weak secret must sign nothing — but now the
flow is disabled and its endpoints refuse with 503 before any signing path, instead of the process
refusing to start. Typed fields read `""` as absent. `/health` answers regardless.

Commit `4167678`.

## Affected Files

- `backend/app/main.py` — `create_app()` at module level, and the comment explaining why nothing
  in the settings layer may raise
- `backend/app/core/config.py` — the rule's new home
- `backend/tests/test_startup_resilience.py`

## Prevention

`tests/test_startup_resilience.py`, three classes and 46 tests:
`TestNothingInTheEnvironmentCanStopTheApp` boots the app with each variable emptied one at a time
and demands `/health` stay at 200; `TestAWeakSecretDisablesRatherThanCrashes` covers the value that
actually caused the outage; `TestEmptyMeansAbsent` covers the typed-field trigger.

The sweep is the only durable form of this guard, because the list of variables grows.

## References

- [[turnstile-test-key-in-production]] — the same mechanism, `contact_flow_disabled_reason`, used
  for a configuration that was present but wrong
- Linear COD-60, COD-58
