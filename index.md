---
title: Code29 — Documentation Index
tags: [moc, index]
---

> **Type:** Index (MOC) — **Scope:** Whole project — **Status:** Active

# Code29 — Documentation Index

Root of the project's second brain. The vault is a three-level tree: this index → a hub per
category → the notes themselves. Nothing hangs loose; every note declares its parent with a
`**Part of:**` line, and that is what draws the clusters in the graph view.

Personal brand landing page positioning the profile as **CTO as a Service / AI Project
Manager**. Visual identity: *"The Neon Architect"*.

---

## Hubs

| Hub | What lives there |
|---|---|
| [[Requirements]] | What the product must do, and for whom |
| [[Architecture]] | How the system is built and why — 8 notes |
| [[Decisions]] | The ten ADRs, chronological, with their supersession chains |
| [[Protocols]] | How the work is run: SDD, Linear, agents |
| [[Bugs]] | Defects whose root cause is worth remembering |

Outside the tree, at repository root: [[README]] (stack, structure, how to run and test) and
[[CLAUDE]] (working conventions: language, workflow, commits, SOLID check).

---

## Entry points

Deliberate shortcuts — they skip the hubs on purpose.

| I want to… | Read in this order |
|---|---|
| Understand the project from zero | [[README]] → [[PRD]] → [[tech-stack-decision]] → [[design]] |
| Work on the contact flow | [[0009-conversational-contact-agent]] → [[improvement-canon]] → [[0008-improvement-canon]] → [[contact-chat-v1]] *(history)* |
| Know why something is the way it is | [[Decisions]] |
| Add code or open a PR | [[CLAUDE]] → [[testing-strategy]] → [[sdd-workflow]] → [[linear-claude-integration]] |
| Touch copy, routes or metadata | [[i18n]] → [[seo-and-discoverability]] |
| Understand a past defect | [[Bugs]] |

---

## Vault conventions

- **One parent per note.** Line 2 of every note is `> **Part of:** [[Hub]]`. A note without it
  is an orphan and will float unattached in the graph.
- **Every hub lists its children** in a table with a one-line description and a status. Adding a
  note means adding its row — the hub is the index, not this file.
- **Links are wikilinks** (`[[note-name]]`), resolved by file name. Do not replace them with
  relative Markdown links; the graph is built from wikilinks only.
- **Hubs are capitalised** (`Architecture.md`), notes are `kebab-case.md`. That is what makes a
  hub recognisable at a glance in the graph and in the switcher.
- **Status banner first.** `> **Type:** … — **Status:** …` on line 1, so state is visible without
  reading the body. A stale note is marked `Deprecated`, never deleted silently.
- **Colours** come from `.obsidian/graph.json` and match `src/styles/tokens.css`: hubs in
  primary cyan, ADRs purple, architecture dim cyan, protocols amber, requirements green, bugs
  red, root notes grey.
- **`docs/` is written by the `doc-guardian` agent only.**
