# Code29 — Project Conventions

## Language

- Communication with the user: **Spanish**
- Code comments and commit messages: **English**

## Workflow

1. **Propose a plan** before touching any file — describe the approach, affected files, and risks
2. **Wait for explicit approval** before writing any code
3. **Track tasks** with Jira (project C29 — see [Jira integration](docs/protocols/jira-claude-integration.md))
4. **Execute task by task** — mark each done before moving to the next
5. **Propose the commit** (message + files) and wait for approval before running it

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

## SDD Workflow

Spec-Driven Development is required for all structural changes. See full protocol:
→ [SDD Workflow](docs/protocols/sdd-workflow.md)

**Quick reference — SDD required when:**
- Adding a new page or route
- Implementing cookie consent, contact form, or legal pages
- Introducing FastAPI (Phase 2+)
- Any AI assistant or lead capture feature (Phase 2+)

**Not required for:** CSS changes, content updates, bug fixes, dependency updates.

**Start a new SDD cycle:** `/sdd-new [change-name]`
