---
title: Code29 — Documentation Index
tags: [moc, index]
---

> **Type:** Index (MOC) — **Scope:** Whole project — **Status:** Active

# Code29 — Documentation Index

Entry point of the project's second brain. Every note in the vault hangs from here, either
directly or one hop away. Open the graph view to see the same map spatially — colours are
defined in `.obsidian/graph.json`.

Personal brand landing page positioning the profile as **CTO as a Service / AI Project
Manager**. Visual identity: *"The Neon Architect"*.

---

## Entry points

| I want to… | Read in this order |
|---|---|
| Understand the project from zero | [[README]] → [[PRD]] → [[tech-stack-decision]] → [[design]] |
| Work on the contact flow | [[0009-conversational-contact-agent]] → [[improvement-canon]] → [[0008-improvement-canon]] → [[contact-chat-v1]] *(history)* |
| Know why something is the way it is | [[docs/architecture/decisions/index|Decision log]] |
| Add code or open a PR | [[CLAUDE]] → [[testing-strategy]] → [[sdd-workflow]] → [[linear-claude-integration]] |
| Touch copy, routes or metadata | [[i18n]] → [[seo-and-discoverability]] |

---

## Requirements

- [[PRD]] — product requirements: audience, scope, success criteria

## Architecture

- [[tech-stack-decision]] — the stack and the reasoning behind each layer
- [[design]] — design source of truth (Google Stitch) and UI decisions
- [[contact-chat-v1]] — the phased design of the contact chat; kept as history since the cutover of 2026-08-24
- [[improvement-canon]] — the ten points of an AI-First SDLC: analysis guide and structure of the delivered report
- [[testing-strategy]] — what is tested at each level and which gates must stay green
- [[i18n]] — EN/ES client-side switcher, single source of truth for copy
- [[seo-and-discoverability]] — metadata, sitemap, robots, OG assets
- [[sdd-landing-v1]] — implementation plan of landing v1, phase status

## Decisions (ADR)

Full chronological log with statuses: [[docs/architecture/decisions/index|Decision log]].

- [[0001-backend-repo-structure]] — backend lives in a monorepo `backend/` folder
- [[0002-fastapi-as-backend-framework]] — FastAPI (+ Pydantic) as the backend framework
- [[0003-api-versioning-strategy]] — URL path API versioning (`/api/v1`)
- [[0004-backend-deploy-provider]] — the backend deploys on Vercel as a second project
- [[0005-genkit-runtime]] — Genkit on Python, embedded in the backend *(partially superseded by 0007)*
- [[0006-guided-ai-contact-flow]] — guided AI contact flow with stateless email verification *(report structure partially superseded by 0008)*
- [[0007-gemini-over-rest]] — talk to Gemini over REST instead of the Genkit SDK
- [[0008-improvement-canon]] — ten fixed improvement points as the structure of the report
- [[0009-conversational-contact-agent]] — a model conducts the conversation, and every report claim carries its source *(live since 2026-08-24)*
- [[0010-snyk-dependency-scanning]] — Snyk scans npm and pip dependencies, outside the PR pipeline

## Protocols

- [[sdd-workflow]] — Spec-Driven Development: when it is mandatory and how a cycle runs
- [[linear-claude-integration]] — task tracking in Linear (team Code29, prefix `COD`)
- [[ai-agents]] — map of the agents and skills that operate on this repo
- [[jira-claude-integration]] — Jira integration, **deprecated** (Jira retired 2026-08-04), kept as history

## Project root

- [[README]] — stack, repository structure, how to run and test
- [[CLAUDE]] — working conventions: language, workflow, commits, SOLID check

---

## Vault conventions

- Links between notes are **wikilinks** (`[[note-name]]`), resolved by file name — that is what
  makes the graph connect. Do not replace them with relative Markdown links.
- Every new note is linked from this index in its section; a note that no one links to is a note
  nobody will find.
- Notes open with a status banner (`> **Type:** … — **Status:** …`) so the state is visible without
  reading the body.
- Documentation under `docs/` is written by the `doc-guardian` agent only.
