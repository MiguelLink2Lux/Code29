# Code29 — SDD Workflow

> **Version:** 1.0 | **Date:** 2026-04-11 | **Status:** Active

Spec-Driven Development (SDD) is the structured planning methodology for Code29. It ensures every significant change is designed before it is implemented.

---

## When to Use SDD

### Always required (full cycle)
- Adding a new page or route (`/legal-notice`, `/privacy-policy`, etc.)
- Implementing the cookie consent system
- Building the contact form end-to-end
- Introducing FastAPI backend (Phase 2)
- Designing the AI analyzer system (Phase 2)
- Any v2 / Phase 3 feature (AI assistant, lead capture, document generation)

### Recommended (minimum: propose + spec + tasks)
- New Vue island component with business logic
- Changes to the contact form flow
- New API endpoint (Phase 2+)
- Cookie consent behavior changes

### Not required (use standard plan → code flow)
- CSS/styling changes within established tokens
- Content updates (copy, images)
- Dependency updates without API changes
- Bug fixes with clear root cause
- Documentation-only changes

---

## Phases — Code29 Usage

| Phase | Command | Required for | Output |
|-------|---------|-------------|--------|
| Explore | `/sdd-explore` | Complex or uncertain features | Exploration notes |
| Propose | `/sdd-propose` | All SDD changes | Proposal with scope + approach |
| Spec | `/sdd-spec` | All SDD changes | Requirements + scenarios |
| Design | `/sdd-design` | Structural changes | Architecture decisions |
| Tasks | `/sdd-tasks` | All SDD changes | Implementation checklist |
| Apply | `/sdd-apply` | Implementation phase | Code + progress tracking |
| Verify | `/sdd-verify` | After implementation | Validation report |
| Archive | `/sdd-archive` | After verification | Final archive |

### Fast-forward for well-understood changes

```
/sdd-ff [change-name]
```

Runs propose → spec → design → tasks in sequence. Use when the feature is clear and low-risk.

---

## Change Naming Convention

Format: `kebab-case`, descriptive, scoped to the feature.

| Change | Name |
|--------|------|
| Cookie consent banner | `cookie-consent-banner` |
| Contact form (full) | `contact-form-v1` |
| Legal pages | `legal-pages` |
| FastAPI setup | `fastapi-backend-setup` |
| AI analyzer design | `ai-analyzer-design` |
| Lead capture flow | `lead-capture-flow` |

**Rules:**
- No version numbers unless necessary (`-v1` only if a v2 is planned)
- No generic names (`feature`, `update`, `change`)
- Scope to the smallest coherent unit of work

---

## Engram Persistence

All SDD artifacts are stored in engram with this topic key format:

```
sdd/{change-name}/{artifact}
```

| Artifact | Topic key example |
|----------|------------------|
| Exploration | `sdd/cookie-consent-banner/explore` |
| Proposal | `sdd/cookie-consent-banner/proposal` |
| Spec | `sdd/cookie-consent-banner/spec` |
| Design | `sdd/cookie-consent-banner/design` |
| Tasks | `sdd/cookie-consent-banner/tasks` |
| Apply progress | `sdd/cookie-consent-banner/apply-progress` |
| Verify report | `sdd/cookie-consent-banner/verify-report` |

To retrieve a full artifact (search results are truncated):
1. `mem_search(query: "sdd/cookie-consent-banner/spec")` → get observation ID
2. `mem_get_observation(id: {id})` → full content

---

## Jira Integration

SDD and Jira serve different purposes — do not duplicate.

| Tool | Purpose |
|------|---------|
| **Jira** | Tracking: who, when, status, priority |
| **SDD** | Design: what, why, how, spec, validation |

**Protocol:**
1. Jira ticket created first (e.g., `C29-XX: Implement cookie consent`)
2. If SDD is required → transition Jira ticket to **En curso** → run `/sdd-new [change-name]`
3. SDD tasks checklist lives in engram — do NOT re-create as Jira subtasks
4. When SDD apply is complete → run `/sdd-verify` → transition Jira ticket to **Finalizada**
5. Run `/sdd-archive` to close the SDD cycle

---

## Example: Full SDD Cycle for Cookie Consent Banner

```
1. Jira: C29-XX created → transition to En curso

2. /sdd-new cookie-consent-banner
   → orchestrator runs: sdd-explore → sdd-propose

3. Review proposal → approve

4. /sdd-continue cookie-consent-banner
   → runs: sdd-spec → sdd-design → sdd-tasks

5. Review tasks → approve

6. /sdd-apply cookie-consent-banner
   → implement task by task, mark done in engram

7. /sdd-verify cookie-consent-banner
   → verify against spec scenarios

8. /sdd-archive cookie-consent-banner
   → archive all artifacts

9. Jira: transition to Finalizada
   → Propose commit → user approves → commit
```

---

## References

- Global SDD commands: `~/.claude/CLAUDE.md` → SDD Workflow section
- Agent map: [docs/protocols/ai-agents.md](ai-agents.md)
- PRD (scope reference): [docs/requirements/PRD.md](../requirements/PRD.md)
