> **Type:** Protocol — **Status:** Deprecated
> **Part of:** [[Protocols]]

# Code29 — Jira ↔ Claude Code Integration (deprecated)

> **Version:** 1.0 | **Date:** 2026-04-11 | **Deprecated:** 2026-08-04
>
> **Jira was retired on 2026-08-04.** Nothing below is an active instruction — it is kept only as a
> historical record of how tasks were tracked before the migration, and to make legacy `C29-*` keys
> found in older docs readable. The active protocol is
> [Linear ↔ Claude Code Integration](linear-claude-integration.md).

This document defined the conventions for using the Atlassian MCP within Claude Code on the Code29 project.

---

## Connection Details

| Field | Value |
|-------|-------|
| Instance | `link2lux.atlassian.net` |
| Cloud ID | `fad37a44-5295-4394-ad85-bebf42b576a7` |
| Project key | `C29` |
| Project ID | `10100` |

---

## Workflow — Task Lifecycle

Every task follows this exact lifecycle when worked on with Claude Code:

```
1. Pick task from Jira board
2. → transition to En curso (id: 21)
3. Work on the task (plan → approve → execute)
4. → propose commit → user approves → commit
5. → transition to Finalizada (id: 31)
```

### Transition IDs

| Status | ID | When to use |
|--------|----|------------|
| Por hacer | `11` | Reset a task (rarely needed) |
| En curso | `21` | When starting work on a task |
| Finalizada | `31` | When commit is approved and created |

**Rule:** Always transition to En curso BEFORE writing any code. Always transition to Finalizada AFTER the commit is created, not before.

---

## Commit Format

Commits in Code29 do NOT include ticket references in the message (atomic commits may span partial ticket work). The ticket context lives in Jira.

**Format:**
```
<type>: <short description>

<optional body>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `test`

**Examples:**
```
feat: add cookie consent banner with granular selector
docs: add SDD workflow protocol and update CLAUDE.md
chore: define AI agent skills and protocols for Code29
fix: correct form validation on empty email field
```

**When to reference a ticket:** Only in PR descriptions or commit body when the change closes a specific ticket, not in the subject line.

---

## Ticket Reference Convention

When referencing a Jira ticket in text (docs, PR descriptions, comments):

- Use the full key: `C29-14`
- In markdown links: `[C29-14](https://link2lux.atlassian.net/browse/C29-14)`
- In commit body (optional): `Closes C29-14`

---

## Sprint Protocol

- Sprints are created and managed manually in Jira by the user
- Claude Code moves tasks between statuses but does NOT create or close sprints
- All tasks for the active sprint should be in the Jira board before work begins
- Backlog tasks are created via Claude Code MCP during planning sessions

---

## MCP Tools Used

| Tool | When |
|------|------|
| `getVisibleJiraProjects` | Session start — confirm project access |
| `getTransitionsForJiraIssue` | First use on a new project — discover transition IDs |
| `transitionJiraIssue` | Start and close every task |
| `createJiraIssue` | During planning sessions — create epics and tasks |
| `getJiraIssue` | Check task details or status |
| `addCommentToJiraIssue` | When a significant decision is made mid-task |

---

## References

- Active replacement: [docs/protocols/linear-claude-integration.md](linear-claude-integration.md)
- SDD integration: [docs/protocols/sdd-workflow.md](sdd-workflow.md)
- Agent map: [docs/protocols/ai-agents.md](ai-agents.md)
