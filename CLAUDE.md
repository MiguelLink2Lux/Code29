# Code29 — Project Conventions

## Language

- Communication with the user: **Spanish**
- Code comments and commit messages: **English**

## Orchestrator — BMad

Every session in this project starts by loading the `bmad` skill: BMad is the orchestrator. It reads
the installed modules' help, recommends the next step, and routes each request to its `bmad-*` skill
or runs the sequence the user asks for. The generic orchestration rules of the global `CLAUDE.md` do
not apply here; Linear, Engram, `comms`, doc-guardian, the approvals below and the mandatory `model`
on every subagent still do. A `SessionStart` hook in `.claude/settings.json` injects this reminder.

## Method — BMad

This project runs on the **BMad Method**. It replaces the generic `workflow` skill and the SDD cycle.

| Situation | Skill |
|---|---|
| Any change to code, config or infrastructure | `bmad-build` — plan, approval checkpoint, implementation, review, commit |
| Work bigger than one session | `bmad-spec` first (plus `bmad-prd`, `bmad-ux` or `bmad-architecture` when the work needs them), then one `bmad-build` per slice |
| Reviewing a diff, PR or document | `bmad-review` / `bmad-code-review` |
| Unsure where to start | `bmad` |

Project policy is injected into `bmad-build` by the team override `_bmad/custom/bmad-build.toml`:
Spanish chat, the `COD` key in every commit and PR, the Critical Section and SOLID Check inside the
plan, approval before push / PR / merge, and Linear + doc-guardian on completion. Change policy there,
never by editing installed skills. Plans and deferred work live in `_bmad-output/`.

Unchanged by BMad:

- **Track tasks** with Linear (workspace `linear.app/code29`, team Code29, issue prefix `COD` — see [Linear integration](docs/protocols/linear-claude-integration.md))
- **Approval** — the plan is approved at the `bmad-build` checkpoint; push, PR and merge each need explicit approval, and the user merges
- **Documentation** — only doc-guardian writes `docs/` and this file

## Critical Section (required in every plan)

Every plan must include a risk analysis covering:

- Code conflicts with existing logic
- Bad practices or technical debt introduced
- Side effects on other modules or integrations
- Edge cases not covered by the plan
- Alternatives considered and why they were discarded

If no risks are identified, state it explicitly: "No critical risks identified."

## Commits

- Atomic commits — one logical change per commit
- Message format: `<type>: <short description>` (e.g. `feat: add user auth`, `fix: handle nil pointer in parser`)
- Never commit without user approval

## Code Style

- Comments in English, on non-obvious logic only
- Follow existing project conventions (naming, structure, formatting)
- No speculative abstractions — implement what is actually needed

## Design

UI design decisions, design system tokens, and source of truth:
→ [Design decisions & source](docs/architecture/design.md)
→ [Product Requirements Document](docs/requirements/PRD.md)
→ [Tech Stack Decision](docs/architecture/tech-stack-decision.md)

## SOLID Principles

SOLID compliance is **active and mandatory** across the entire project.

Before approving any plan, a **SOLID Check** section must be included identifying violations and the recommended fix.

| Principle | What to watch in Astro + Vue + TS |
|-----------|-----------------------------------|
| **S** — Single Responsibility | Vue components with one reason to change. No business logic mixed with presentation. |
| **O** — Open/Closed | Components extensible via props/slots, not by direct modification. |
| **L** — Liskov Substitution | Composables and base types must be substitutable by derived ones. |
| **I** — Interface Segregation | Small, specific TS interfaces. Minimal component props — no god-props. |
| **D** — Dependency Inversion | Business logic never depends on concrete implementations. External services (GA4, form backend, future FastAPI) accessed exclusively via abstractions in `src/utils/`. |

When a violation is detected: name the principle, explain the problem, propose the minimal fix.

## SDD Workflow — superseded

The SDD cycle is no longer used; structural changes go through `bmad-spec` and `bmad-build` (see
**Method — BMad** above). The protocol is kept as history: [SDD Workflow](docs/protocols/sdd-workflow.md).
