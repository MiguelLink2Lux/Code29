> **Type:** Index (MOC) — **Scope:** Bug registry — **Status:** Active
> **Part of:** [[index]]

# Bugs

Registry of defects worth remembering: the ones whose **root cause** teaches something about
the system. A crash fixed by a typo does not belong here; a defect that a whole class of tests
could not have caught does.

Day-to-day tracking lives in Linear (`COD-*`, see [[linear-claude-integration]]). This registry
is the durable half: what was actually wrong, and what now prevents it.

## Child notes

| Bug | Area | Status | Date |
|---|---|---|---|
| [[sourced-but-irrelevant-evidence]] | Canon report — evidence routing | Fixed | 2026-08-23 |
| [[improvement-canon-measured-signal-drift]] | Documentation drift | Fixed | 2026-08-23 |
| [[gemini-extractor-never-wired]] | Contact conversation — extractor wiring | Fixed | 2026-08-26 |
| [[turnstile-test-key-in-production]] | Contact verification — anti-abuse gate | Fixed | 2026-08-27 |
| [[turnstile-widget-outside-the-dom]] | Contact verification — human check | Fixed | 2026-08-28 |
| [[model-thinking-outlived-the-deadline]] | Contact conversation — model deadline | Fixed | 2026-08-30 |
| [[a-mistyped-code-became-a-message]] | Contact verification — answer routing | Fixed | 2026-08-30 |
| [[a-validator-ran-at-import-time]] | Backend startup — configuration | Fixed | 2026-08-30 |
| [[the-ground-never-left-the-envelope]] | Canon report — facts routing | Fixed | 2026-09-01 |
| [[the-report-generator-was-never-set]] | Deployment — environment configuration | Fixed | 2026-09-02 |

## Convention

One file per bug, `kebab-case.md`, in this folder, following the entry template:

```markdown
> **Type:** Bug — **Status:** Fixed — **Date:** YYYY-MM-DD — **Severity:** High
> **Part of:** [[Bugs]]

# Short title in the imperative of what was wrong
## Symptom          — what was observed, from outside
## Root Cause       — why it happened, in the code
## Fix              — what changed, plus commit/PR
## Affected Files
## Prevention       — the test or guard that now bites
## References
```

## References

- [[index]] — parent hub
- [[testing-strategy]] — where the preventions land
- [[Protocols]] — the process that is supposed to catch these earlier
