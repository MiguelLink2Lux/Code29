> **Type:** Protocol — **Status:** Active
> **Part of:** [[Protocols]]

# Code29 — Linear ↔ Claude Code Integration

## Purpose

Define how tasks of the Code29 project are tracked in Linear when working with Claude Code.
Linear is the **only** task manager for this project. Jira was retired on 2026-08-04 — it is not
queried, not updated, and not cited (see [Jira integration (deprecated)](jira-claude-integration.md)).

## When to Apply

Whenever a task is created, started, linked to a branch or PR, or closed for this project.

## Workspace

| Field | Value |
|-------|-------|
| Workspace | `linear.app/code29` |
| Team | `Code29` |
| Issue prefix | `COD` |

MCP tools (`mcp__linear__*`) are deferred — load their schemas with `ToolSearch` before calling them,
e.g. `select:mcp__linear__save_issue,mcp__linear__list_issues,mcp__linear__get_issue`.

## Rules

### Statuses (team Code29)

| Status | Type | When |
|--------|------|------|
| `Backlog` | backlog | Created, not planned yet |
| `Todo` | unstarted | Planned, ready to start |
| `In Progress` | started | Set **before** writing any code |
| `Done` | completed | Work committed and verified |
| `Canceled` / `Duplicate` | — | Discarded |

The team has no `In Review` status: an issue waiting on a PR stays `In Progress` until the PR is
merged and verified, then moves straight to `Done`.

### Lifecycle

1. Issue created from an **approved plan** (never invented from scratch, never without user approval).
2. On starting work → status `In Progress`, `assignee: me`.
3. Branch created off `main` (see [Commits](#format--example) and the global `git-flow` skill).
4. Commit proposed to the user → approved → committed. PR opened when the work needs review.
5. Once merged and verified → status `Done`, with a comment pointing at the commit or PR.

Never close an issue the user has not accepted.

### Branch and PR linking

| Case | Branch | How the issue is linked |
|------|--------|-------------------------|
| Scoped task with its own issue | `<type>/COD-XX-short-description` (e.g. `chore/COD-29-linear-not-jira`) | The issue key is in the branch name; the PR body cites the issue URL |
| Several issues in one development | `feature/<slug-of-the-development>` | Each issue cites the branch in a comment |
| Small adjustment, no branch | Commit straight to `main` | The issue key goes in the commit body |

Ignore the `gitBranchName` Linear suggests (`user/cod-xx-…`) — the repo convention above wins.

### Ticket reference convention

- Full key in text: `COD-29`
- Markdown link: `[COD-29](https://linear.app/code29/issue/COD-29)`
- Commit body (optional): `Closes COD-29`
- **Never** in the commit subject line — atomic commits may cover partial ticket work.

## Format / Example

Commit format used in this project:

```
<type>: <short description>

<optional body>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `test`

Full cycle of a task:

```
1. Linear: COD-29 → In Progress, assignee me
2. Plan proposed → user approves
3. git checkout -b chore/COD-29-linear-not-jira origin/main
4. Work task by task
5. Commit proposed → approved → committed → PR opened
6. Merged and verified → Linear: COD-29 → Done + comment with the PR URL
```

## References

- Project conventions: [CLAUDE.md](../../CLAUDE.md)
- SDD ↔ Linear integration: [docs/protocols/sdd-workflow.md](sdd-workflow.md)
- Agent map: [docs/protocols/ai-agents.md](ai-agents.md)
- Deprecated predecessor: [docs/protocols/jira-claude-integration.md](jira-claude-integration.md)
