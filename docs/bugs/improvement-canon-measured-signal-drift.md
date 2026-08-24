> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-23 — **Severity:** Medium
> **Part of:** [[Bugs]]

# The canon doc credited measured signals to points that never receive any

## Symptom

`docs/architecture/improvement-canon.md` claimed measured signals were *"strong evidence for
point 10 and circumstantial for 8 and 9"*, and the per-point Signal bullets described hosting
hints and `robots`/`sitemap` as measured evidence for points 8 and 9. `measured_evidence_for()`
routes nothing to those points.

This was not harmless prose: the first live API run acted on exactly that inference — see
[[sourced-but-irrelevant-evidence]].

## Root Cause

Documentation drift. The doc described an evidence-routing model that the code had never
implemented, and the model reading the doc inherited the wrong belief.

## Fix

Corrected six places in the canon doc: the Signal bullets of points 8 and 9, the point 10
bullet, the sequential/transversal glance table, the *"Signals: measured versus reported"*
section, the tri-state table and the generator rules. Added a generator rule making the routing
explicit: **a signal counts only for the point it actually evidences.**

Also unified the README's contact-flow step count at eleven and restored `observability` to the
step diagram, which had dropped it — the same omission ADR 0006 had already been corrected for
once.

## Affected Files

- `docs/architecture/improvement-canon.md`
- `README.md`

## Prevention

Only point 10 receives measured evidence, and only as `parcial`; every other point is decided on
reported evidence alone. The step list is verified against `src/utils/contact-chat-flow.ts`
rather than retyped.

## References

- [[Bugs]] — parent hub
- [[improvement-canon]] — the corrected document
- [[sourced-but-irrelevant-evidence]] — the code half of the same defect
