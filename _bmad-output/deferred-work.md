- source_plan: `_bmad-output/plan-cod-36-astro-node24.md`
  summary: The Node major is pinned twice (.nvmrc for CI/verify:runtime, engines.node for Vercel) with nothing checking they match.
  evidence: Both pins existed before COD-36; verify:runtime compares only against .nvmrc, so an engines.node drift would surface only as a failed Vercel deploy.
- source_plan: `_bmad-output/plan-cod-36-astro-node24.md`
  summary: Code29 CLAUDE.md requires a Critical Section and SOLID Check in every plan; the BMad plan template has neither — reconcile the project rules with BMad.
  evidence: Quick review of COD-36 flagged the plan as breaking the CLAUDE.md "Critical Section (required in every plan)" and "SOLID Check" rules.
- source_plan: `_bmad-output/plan-cod-36-astro-node24.md`
  summary: tests/e2e/contact-conversation.spec.ts is timing-flaky — a different test fails in roughly 1 of 5 local full runs.
  evidence: 2026-10-04 local runs, full suite, 4 workers. Baseline 1ba5d5f on Node 20 — 1 failed run of 16 ("asks for the report once the email is verified"). COD-36 branch on Node 24 — 5 failed runs of 21, five different tests (address step, closing invitation, injection attempt, …). Pre-existing; Astro 5 may widen it (script hoisting / hydration timing). Sample too small to tell.
- source_plan: `_bmad-output/plan-cod-69-gemini-turn-failures.md`
  summary: Honour Gemini's `error.details[].retryDelay` on 429 instead of a fixed 1 s backoff.
  evidence: Unverified — Gemini usually returns the wait in the body, not a Retry-After header; confirm from a live 429 body in the new logs before changing.
- source_plan: `_bmad-output/plan-cod-69-gemini-turn-failures.md`
  summary: The deployment verifier judges the conversation from a single turn, so an intermittent failure can pass.
  evidence: Sampling several turns spends free-tier Gemini quota on every verification; decide alongside the paid-tier question.
