---
title: 'C29-8 — REPORT_GENERATOR=gemini fails every report: the grounding flag was lost'
type: 'bugfix'
ticket: 'C29-8 (Plane)'
created: '2026-11-13'
status: 'built'
baseline_revision: '82d1abc'
route: 'quick'
risk: 'low'
review: 'quick'
context: []
---

## Intent

**Problem:** `get_report_generator` (`backend/app/api/v1/contact_report.py:212`) builds
`GroundedCanonGenerator(api_key=..., grounding=settings.gemini_grounding)`, but the constructor
(`backend/app/services/grounded_report.py:233`) has no `grounding` parameter. With
`REPORT_GENERATOR=gemini` every report request raises `TypeError` and answers 500. Reproduced on
2026-11-13 by calling `get_report_generator` with `report_generator='gemini'`.

**Root cause:** `f2c94ca` added `grounding: bool = False` to the generator, the opt-in branch in
`generate()`, and `TestGroundingOptOut`. A later merge (around `0bea657`, which rewrote `generate()`
to carry `ground`) kept the call site and dropped the generator half and its tests. No test builds
the real generator through `get_report_generator`, so the suite stayed green.

**Approach:** Bring back the generator half of `f2c94ca` on top of today's `generate()`, keeping
`ground` and `transcript`. Restore its tests and add the missing wiring test.

## Changes

1. `grounded_report.py` — add the `grounding: bool = False` constructor parameter. In `generate()`,
   send the request without grounding when the flag is off; when it is on, attempt grounding and keep
   today's degrade path.
2. `tests/test_grounded_generator.py` — the tests that assert grounded behaviour (tool declared,
   cited claims, `:grounded` name, every degradation case) pass `grounding=True` explicitly. Restore
   `TestGroundingOptOut` (off by default → no `tools`; on → `google_search`; off →
   `ungrounded` in the name).
3. `tests/test_cutover_wiring.py` (or `test_contact_report_endpoint.py`) — new tests: with
   `REPORT_GENERATOR=gemini` and a key, `get_report_generator` returns a `GroundedCanonGenerator`,
   and its grounding follows `GEMINI_GROUNDING`. This is the test that would have caught the bug.

Out of scope: `GEMINI_MODEL` being unread (finding 2). It disappears with the move to Ollama, so it
is not fixed here.

## Verification

- `uv run ruff check` and `uv run pytest` in `backend/` (677 tests today, plus the new ones).
- The reproduction command builds the generator without error.

## Critical Section

- **Code conflicts:** `generate()` has changed since `f2c94ca` (`ground`, `transcript`), so the
  branch is rewritten by hand, not cherry-picked. The degradation tests must explicitly enable the
  flag; otherwise they would pass by accident, because degradation is never attempted.
- **Bad practices or debt:** none added. The generator code is short-lived: part 2 (Ollama) replaces
  it. It is still worth fixing, because production uses it until then.
- **Side effects:** none of the 10 canon points changes. Behaviour change in production: with
  `GEMINI_GROUNDING` absent, the report skips the grounded call that always got a 429. That is a
  saved round trip, and it is what `f2c94ca` already intended.
- **Edge cases:** `GEMINI_GROUNDING=true` on a key without a paid tier → 429 → degrades (already
  covered). `grounding=True` with `degrade_without_grounding=False` → `GroundingUnavailable`
  (already covered).
- **Alternatives discarded:** (a) removing `grounding=` from the call site — that would make the
  generator always try grounding, against `f2c94ca` and the docs; (b) waiting for the migration to
  Ollama — that would leave `REPORT_GENERATOR=gemini` broken in the meantime.

## SOLID Check

- **S:** the generator still has a single reason to change (talking to the model); the flag is
  configuration injected through the constructor.
- **O / L / I:** the generator's public interface does not change; the new parameter is optional
  and defaults to off.
- **D:** the route still builds the generator from settings in a single place
  (`get_report_generator`).

No violations identified.

## Delivery

Branch `fix/C29-8-grounding-flag-lost` off `main`. One atomic commit:
`fix: restore the grounding flag the report generator lost (C29-8)`. Push and PR only with
approval.
