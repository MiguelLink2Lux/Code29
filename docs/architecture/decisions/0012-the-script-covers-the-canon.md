> **Type:** Architecture · ADR — **Status:** Accepted — **Date:** 2026-08-30
> **Part of:** [[Decisions]]

# ADR 0012 — The script asks what the report promises to assess, and the new ground is optional

- **Status:** Accepted
- **Date:** 2026-08-30
- **Deciders:** Miguel Navarro Mantas
- **Builds on:** [[0008-improvement-canon]], [[0009-conversational-contact-agent]], [[0011-server-owned-conversation-script]]
- **Issue:** COD-65

## Context and Problem Statement

[[0008-improvement-canon]] fixed the emailed report at ten points. The conversation
collected four facts — `company`, `contact_name`, `website`, `team` — and those four fed
none of them.

The arithmetic, verified point by point against `canon.py` and `evidence.py`:

| Points | Situation |
|--------|-----------|
| 1, 3, 5, 6, 7, 8, 9 | **Unreachable by construction.** No fact and no measured signal could ever evidence them |
| 2, 4 | Reachable only by accident, if the visitor happened to mention training or code ownership while describing their team |
| 10 | The one measured route — HTTPS and security headers — and permanently `partial`, never `covered` |

This was not a bug in the generator. A lead received, on 2026-08-30, a report with ten
lines of `[no evaluado]`, and that was the system working exactly as built.

The honest framing: **the report promised an assessment the conversation never gathered
the grounds for.** Either the promise shrinks or the script grows.

Two constraints made the obvious fix — "ask ten questions" — the wrong one:

- [[0009-conversational-contact-agent]] exists precisely to retire an eleven-step
  questionnaire. Ten questions would rebuild it with a chat skin.
- The turn budget is a cost ceiling, and every turn is a model call.

## Decision Drivers

- The report is the product. A report that assesses nothing is worse than no report,
  because it was promised and delivered empty.
- The extractor is forbidden from inferring what the visitor did not say
  ([[0007-gemini-over-rest]]), and that rule is not up for renegotiation — the code
  already records an attempt to infer a CI pipeline from a home page that produced
  "Framework detected: Next.js" as evidence.
- A visitor who will not describe their deployment pipeline is still a lead.

## Decision Outcome

**Four grouped questions**, asked once the required facts are held, each written to cover
several canon points at once:

| Fact | Question | Canon points |
|------|----------|--------------|
| `delivery` | How code reaches production — who reviews it, what has to pass, how it deploys, what happens when it breaks | 4, 6, 7, 8 |
| `context_home` | Where the project's context lives — requirements, architecture decisions, task tracking | 1, 3, 9 |
| `ai_practice` | How the team uses AI day to day, and whether it has been trained for it | 2, 5 |
| `governance` | Rules over data, secrets and third-party dependencies | 10 |

Grouped rather than atomised on purpose: one open question about a pipeline yields more
than three closed ones. The live conversation that prompted this ADR is the evidence —
asked about their team, the visitor volunteered unprompted that the software's users sit
in the same office and feedback is immediate.

`MAX_TURNS` moves 12 → 16. The ceiling exists to bound cost, so it moves with the script
deliberately, never as a side effect of adding a step.

### The new ground is optional, and that is load-bearing

`OPTIONAL_FACTS` is a separate tuple from `REQUIRED_FACTS`. The optional facts:

- never enter `missing_facts()` nor the `missing` field of the turn response;
- never gate `is_complete`;
- are asked only while turns remain, so an unanswered question cannot outlive the budget.

**Why `missing` in particular.** The client requests the report only when `missing` is
empty (`src/utils/contact-conversation.ts`). A fact nobody is obliged to answer, placed
in that list, would mean **no visitor ever receives a report** — silently, and for
everyone. This is the most expensive mistake the change could have made, and it has a
dedicated test rather than a comment.

## Consequences

**Good**

- Seven canon points move from structurally unreachable to answerable.
- A visitor who declines every optional question still finishes complete and still gets
  their report.
- The turn ceiling remains an explicit decision, asserted by a test that computes the
  worst case from the fact tuples rather than hardcoding a number.

**Bad, and accepted**

- Four more free-text answers per conversation is four more model calls, and four more
  openings for prompt injection — on ground (pipelines, tooling, prompts) where an
  attacker can hide instructions in plausible shop talk. The deterministic guard still
  runs **before** the model, with zero tolerance, and the model's own report of an attack
  remains advisory.
- Longer conversations risk abandonment. Unmeasured: the first real runs are the evidence.

**Still open**

This ADR covers **collecting** the ground. Two pieces remain before the report improves:

1. The facts must reach `_facts_payload` in `grounded_report.py` — today it passes only
   `contact_name`, `company`, `team` and the site signals.
2. `REPORT_GENERATOR` must be `gemini` in production. It defaults to `stub`, and unlike
   the extractor — which autodetects from the API key — the report generator requires the
   flag explicitly. With the key set and the flag absent, the conversation runs on the
   model while the report quietly falls back to the deterministic template, with no error
   anywhere. The only visible tell is the `template:canon` line in the emailed footer.

Until both are done, the script gathers ground that nothing reads.

## References

- [[0008-improvement-canon]] — the ten points this script now feeds
- [[0011-server-owned-conversation-script]] — `derive_next_step`, extended here
- [[0009-conversational-contact-agent]] — the questionnaire this must not become again
- [[Decisions]] — parent index
