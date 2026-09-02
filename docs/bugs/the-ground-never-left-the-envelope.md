> **Type:** Bug — **Status:** Fixed — **Date:** 2026-09-01 — **Severity:** High
> **Part of:** [[Bugs]]

# The ground the chat gathered never left the envelope

## Symptom

Leads received a report with a verdict of `no evaluado` on almost every canon point,
after a conversation in which they had answered how their team delivers, where its
context lives, how it uses AI and what governs its data. No error was raised, nothing
was logged, and the mail went out looking normal.

## Root Cause

`POST /api/v1/contact/report` opens the signed envelope and unpacks the facts it holds.
It unpacked four fields of eight — `contact_name`, `company`, `website`, `team` — and
the four optional facts added by COD-65 died on that line. The generator was handed a
company with no practice attached to it, so no point had evidence and the honest state
for each was `no evaluado`.

The failure is silent by construction: an absent fact is indistinguishable from a fact
the visitor declined to give, and the report is designed to say `no evaluado` rather
than guess. The safety property that keeps the report honest is exactly what hid the
defect.

## Fix

The four now travel to `_facts_payload` as `ground`, and the system instruction names
which canon points each field usually speaks to. The model does the splitting: one
answer ("PR obligatoria, deploy a mano") evidences several points at once, and the
backend could only dump the whole sentence under a point it picked itself — an
attribution nobody made. `TemplateCanonGenerator` accepts `ground` and ignores it,
which is what "the generator that runs without a key" means.

Commit `0bea657`, PR #54.

## Affected Files

- `backend/app/api/v1/contact_report.py` — unpacks all eight fields
- `backend/app/services/grounded_report.py` — `GROUND_POINTS`, `_clean_ground`, `_facts_payload`
- `backend/app/services/canon_report.py` — the stub's matching signature
- `backend/app/services/conversation.py` — `MAX_GROUND_CHARS`, a ceiling the fields lacked
- `backend/app/services/prompt_guard.py` — its docstring said the generator needed no filter

## Prevention

Ten tests, each seen failing first. Two of them are the ones that bite: the endpoint
must hand every optional fact to the generator, and the generated request body must
contain the visitor's words. A regression puts the report back to empty without any
other symptom, so the assertion has to be on the request itself, not on the response.

## References

- [[0007-gemini-over-rest]] — the security posture this changed
- [[0012-the-script-covers-the-canon]] — the four facts and why they exist
- Linear COD-67, COD-65, COD-42
