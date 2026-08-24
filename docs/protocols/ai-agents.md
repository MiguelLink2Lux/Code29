# Code29 — AI Agent Map

> Last updated: 2026-04-11
> **Part of:** [[Protocols]]

This document defines the AI agents (Claude Code skills) active in the Code29 project, their responsibilities, trigger conditions, and handoff protocols.

---

## Agent Roster

### doc-guardian — Documentation Authority
**Skill:** `~/.claude/skills/doc-guardian.md` (global)  
**Status:** ✅ Active

**Sole write access to:**
- `docs/` (all subdirectories)
- `CLAUDE.md` at project level
- Postman collections
- OpenAPI / Swagger specs
- Engram observations of type `architecture`, `bugfix`, `pattern`, `decision`

**Trigger:** End of session, or when any agent detects a documentation update is needed.  
**Handoff:** Other agents flag documentation needs; doc-guardian executes.

---

### arch-reviewer — Architecture Consistency Guardian
**Skill:** `.claude/skills/arch-reviewer.md` (project-level)  
**Status:** ✅ Active

**Responsibilities:**
- Verify PRD alignment for proposed changes
- Enforce design system tokens (0px radius, color palette, typography)
- Detect scope creep (v1 vs v2 boundary)
- Recommend SDD cycle when a change is structural

**Trigger:** When a new feature or structural change is proposed or implemented.  
**Output:** Structured review with PASS / FLAG / BLOCK per area.  
**Escalation:** Blocks proceed to user; SDD trigger opens a `/sdd-new` cycle.

---

### security-reviewer — Security and RGPD Compliance Auditor
**Skill:** `.claude/skills/security-reviewer.md` (project-level)  
**Status:** ✅ Active

**Responsibilities:**
- RGPD / LOPDGDD compliance (cookies, forms, lead capture)
- Form security (anti-spam, server-side validation, no secret exposure)
- HTTP security headers (CSP, HSTS, X-Frame-Options, etc.)
- Dependency security audit
- Secrets and configuration hygiene

**Trigger:** Contact form changes, cookie system changes, new dependencies, HTTP config, v2 lead capture design.  
**Severity levels:** CRITICAL (block) → HIGH → MEDIUM → LOW → INFO  
**Escalation:** CRITICAL findings block deployment.

---

### test-engineer — Unit and Integration Test Specialist
**Skill:** `.claude/skills/test-engineer.md` (project-level)  
**Status:** ✅ Active — stack confirmed (C29-8 closed)

**Responsibilities:**
- Write and maintain unit tests for Vue components and utilities
- Integration tests for the contact form submission flow
- E2E tests for critical user paths (cookie consent, form submission)
- Backend tests for FastAPI endpoints (Phase 2+)

**Stack:** Astro + Vue 3 (Vitest + @testing-library/vue + Playwright) / FastAPI Phase 2+ (pytest + httpx)
**Skill file:** `.claude/skills/test-engineer.md`

---

## Orchestration Protocol

```
User request
    │
    ├── Structural change? ──→ arch-reviewer first
    │       │
    │       └── SDD required? ──→ /sdd-new [change]
    │
    ├── Security-sensitive? ──→ security-reviewer
    │       │
    │       └── CRITICAL found? ──→ BLOCK + escalate to user
    │
    ├── Code implemented? ──→ test-engineer (when active)
    │
    └── Session closing? ──→ doc-guardian
```

---

## Handoff Rules

1. **arch-reviewer → doc-guardian**: If arch-reviewer identifies a missing architecture decision record, it notifies doc-guardian — it does NOT write to `docs/` directly.
2. **security-reviewer → doc-guardian**: Security findings that establish a pattern or decision are saved via doc-guardian.
3. **Any agent → orchestrator**: If a finding is outside the agent's scope, it returns to the orchestrator with a clear handoff note.
4. **No agent writes to `docs/` directly** — all documentation flows through doc-guardian.

---

## References

- PRD: [docs/requirements/PRD.md](../requirements/PRD.md)
- Design system: [docs/architecture/design.md](../architecture/design.md)
- Project conventions: [CLAUDE.md](../../CLAUDE.md)
