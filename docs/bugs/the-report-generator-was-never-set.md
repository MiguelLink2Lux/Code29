> **Type:** Bug — **Status:** Fixed — **Date:** 2026-09-02 — **Severity:** High
> **Part of:** [[Bugs]]

# The report generator was never switched on, and 26/26 checks agreed

## Symptom

Every report emailed from production was written by the deterministic stub, not by the
model. [[the-ground-never-left-the-envelope]] had already fixed the defect that emptied
the report — the four optional facts now reach `generate()` — and that fix was deployed
and correct. It simply never ran.

`node scripts/verify-deployment.mjs` reported **26/26 checks passed** throughout.

## Root Cause

`REPORT_GENERATOR` did not exist in the project's Production environment. Nine variables
were set and none was that one (`vercel env ls production --project code29-api`), so the
setting fell back to its default, `stub` (`backend/app/core/report_settings.py:29`).

Nothing detected it because nothing looks. The deployment verifier has no check for which
generator is active: a report is only produced at the end of a verified conversation,
behind Turnstile, so no probe reaches it.

## Fix

`REPORT_GENERATOR=gemini` added to Production as a **Config** value, followed by a
redeploy — a new variable is only picked up by a new deployment.

It was first created as a `Secret`, which is `vercel env add`'s default, and immediately
recreated with `--type config`. A Secret is hidden in the dashboard and unavailable to
`vercel env pull`: an unreadable configuration switch is precisely what let this go
unnoticed for two working days. Secrets are for credentials; `gemini` is a switch.

## Affected Files

No repository file changed. The fix lives in the Vercel project `code29-api`, Production
environment — which is the point: `docs/protocols/deployment.md` already listed the
variable, and a table is not an environment.

## Prevention

None yet, and that is the honest state.

The verifier cannot reach the generator without completing a gated conversation, so the
variable's presence stays unguarded. Two things reduce the exposure without closing it:
the value is now `Config` and therefore readable, and `REPORT_GENERATOR=gemini` refuses to
boot without `GEMINI_API_KEY` (`backend/app/api/v1/contact_report.py:210`) rather than
quietly emailing a template as if a model had written it.

What this bug shares with [[a-validator-ran-at-import-time]] is the shape, not the cause:
configuration that is correct in the repository and absent in the environment, with
nothing in between that compares the two.

## References

- [[the-ground-never-left-the-envelope]] — the fix whose effect this silence hid
- [[../protocols/deployment]] — the backend variable table
- [[Bugs]]
