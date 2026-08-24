> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-23 — **Severity:** High
> **Part of:** [[Bugs]]

# A sourced claim filed under the wrong canon point is still a false claim

## Symptom

The first live run of the canon report, about a real company, stated `Framework detected:
Next.js` as grounds for marking **point 8 (CI/CD) covered**, and used `HTTPS enabled` as the
**diagnosis for point 9 (living documentation)**. Every sentence carried a real source, so the
attribution guard passed. The report was still wrong about the lead.

A second defect surfaced in the same area: a present HSTS header resolved governance as
*covered* rather than *partial*.

## Root Cause

Phase D built a guard against **unsourced** claims and never considered **irrelevant** ones.
`build_canon_report` handed every "measurable" canon point (`_MEASURABLE_POINTS = {8, 9, 10}`)
the **entire** measured pool returned by `measured_evidence(site)`, with no notion of which
signal evidences which point.

The second defect was a boolean: `resolve_with_sources` read
`if any(partial) and not measured_items`, so *partial measured* evidence fell through to
`covered`. Measured evidence is more trustworthy than reported evidence — that does not make
weak evidence strong.

Both were unreachable under `httpx.MockTransport`: a mock returns whatever the test author
already believed.

## Fix

- `measured_evidence_for(point, signals)` routes each signal only to the point it genuinely
  evidences. Security signals reach point 10 (governance) only, flagged `partial=True`.
  Points 8 and 9 now receive **no** measured evidence: nothing on a home page proves that a
  pipeline exists or that documentation lives beside the code.
- `resolve_with_sources` now reads `if all(item.partial ...)` → `partial`, regardless of the
  source's kind.

Shipped in **PR #26**. Gates after: 407 backend tests passing, `ruff` clean.

## Affected Files

- `backend/app/services/evidence.py`
- `backend/app/services/canon_report.py`
- `backend/tests/test_evidence_sources.py`

## Prevention

- Relevance is asserted per point, not just attribution.
- The accusation guard (forbidden Spanish phrasings such as *"no tenéis"*, *"carecéis"* in the
  narrative of an unevaluated point) was verified to bite by planting
  `"No tenéis esto cubierto"` — it failed, naming the point.
- Standing lesson for this project's AI work: **attribution is necessary but not sufficient.**
  A claim needs a source *and* relevance to the point it resolves.

## References

- [[Bugs]] — parent hub
- [[improvement-canon]] — the canon whose points the evidence resolves
- [[0008-improvement-canon]] — the ADR that made the ten points the report structure
- [[0009-conversational-contact-agent]] — where the verifying agent lives
- [[improvement-canon-measured-signal-drift]] — the documentation half of the same defect
