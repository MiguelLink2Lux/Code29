# Skill Registry — Code29

> Generated: 2026-04-11 | Mode: engram

---

## Project-Level Skills (`.claude/skills/`)

| Skill | File | Trigger |
|-------|------|---------|
| `arch-reviewer` | `.claude/skills/arch-reviewer.md` | Structural change proposed or implemented; PRD/design token review |
| `security-reviewer` | `.claude/skills/security-reviewer.md` | Form changes, cookie system, new deps, HTTP config, lead capture |
| `test-engineer` | `.claude/skills/test-engineer.md` | Writing/reviewing tests — Vitest, Playwright (frontend), pytest (backend Phase 2+) |

---

## Global Skills (`~/.claude/skills/`)

### Documentation
| Skill | Trigger |
|-------|---------|
| `doc-guardian` | End of session; any docs/ or CLAUDE.md update needed |

### SDD Pipeline
| Skill | Command | Phase |
|-------|---------|-------|
| `sdd-init` | `/sdd-init` | Initialize SDD context |
| `sdd-explore` | `/sdd-explore <topic>` | Explore before proposing |
| `sdd-propose` | `/sdd-propose` | Create change proposal |
| `sdd-spec` | `/sdd-spec` | Write requirements + scenarios |
| `sdd-design` | `/sdd-design` | Architecture design |
| `sdd-tasks` | `/sdd-tasks` | Implementation task breakdown |
| `sdd-apply` | `/sdd-apply` | Implement tasks |
| `sdd-verify` | `/sdd-verify` | Validate implementation vs spec |
| `sdd-archive` | `/sdd-archive` | Archive completed change |

### UI / Frontend
| Skill | Trigger |
|-------|---------|
| `frontend-ui-ux-engineer` | UI/UX implementation without mockups |
| `ui-review` | Review/audit components against design conventions |

### Utilities
| Skill | Trigger |
|-------|---------|
| `skill-creator` | Creating new agent skills |

### Not applicable to this project
| Skill | Reason |
|-------|--------|
| `go-testing` | Go stack — Code29 uses Astro/Vue/FastAPI |
| `morning-report` | Link2Lux specific |

---

## Project Conventions Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Workflow, commit format, language rules, SDD quick ref |
| `docs/protocols/ai-agents.md` | Agent map, orchestration protocol, handoff rules |
| `docs/protocols/sdd-workflow.md` | SDD trigger conditions, phases, naming, Linear integration |
| `docs/protocols/linear-claude-integration.md` | Linear conventions: workspace, statuses, branch/PR linking |
| `docs/architecture/design.md` | Design system tokens (Neon Architect) |
| `docs/architecture/tech-stack-decision.md` | Stack decision: Astro+Vue+FastAPI+Vercel |
| `docs/requirements/PRD.md` | Product requirements v1 + v2 |
