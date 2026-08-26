> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-26 — **Severity:** High
> **Part of:** [[Bugs]]

# A guard that could never be true: the conversation always ran on the stub

## Symptom

The contact chat behaved like the eleven-step questionnaire that
[[0009-conversational-contact-agent]] retired: four fixed questions, in order,
ignoring what the visitor actually wrote. Sending `Hola, me llamo Miguel y trabajo en
Link2Lux` to the deployed backend answered `¿Cómo te llamas?` and still reported
`contact_name` as missing.

The visitor-facing complaint was not "the model is bad" but "the chat feels like a form" —
which was accurate: no model was reading it.

## Root Cause

`_build_extractor` in `backend/app/main.py` selected the extractor like this:

    key = settings.gemini_api_key.get_secret_value() if hasattr(settings, "gemini_api_key") else ""
    return GeminiFactExtractor(api_key=key) if key else StubFactExtractor()

`Settings` (`app/core/config.py`) never declared `gemini_api_key`, and its `model_config`
sets `extra="ignore"`. The `hasattr` was therefore **permanently false**, so the expression
resolved to `""` and every deployment fell back to `StubFactExtractor` — with or without a
key in the environment. The field exists only on `ReportDeliverySettings`, which feeds the
report generator, not the conversation.

Two properties made it invisible:

- **It degrades, it does not fail.** A stub conversation answers 200 to every turn. There is
  no error, no log line, and no failing request to notice.
- **Every test injected the extractor.** `create_app(fact_extractor=…)` is the supported test
  seam, so the whole suite exercised both extractors and none of it ever exercised the
  *selection* between them.

## Fix

`_build_extractor` takes no settings argument and reads the key from
`get_report_delivery_settings()` — the one place the field is declared. `Settings` does not
gain a duplicate field: two sources for one key is what produced the confusion.

Two tests now assert the selection itself: a configured `GEMINI_API_KEY` must yield
`GeminiFactExtractor`, an absent one `StubFactExtractor`.

Shipped in commit `1a2ab96`. Gates after: 501 backend tests passing, `ruff` clean.

## Affected Files

- `backend/app/main.py`
- `backend/tests/test_wiring.py`
- `scripts/verify-deployment.mjs` — the outside check that would have caught it

## Prevention

- The wiring is asserted, not just the collaborators. A dependency-injection seam hides the
  production default unless a test builds the app the way production does.
- `scripts/verify-deployment.mjs` now asks the deployed backend whether a model or the stub
  is answering, by sending a sentence a stub cannot parse and checking `missing`.
- Rule of thumb this cost us: **`hasattr` on a settings object is not a feature switch.** A
  typo'd or undeclared field silently becomes "off" for ever.

## References

- [[Bugs]] — parent index
- [[0009-conversational-contact-agent]] — the agent this defect quietly disabled
- [[0007-gemini-over-rest]] — where the model key is declared
- [[deployment]] — how to verify a deployment actually runs what it claims
