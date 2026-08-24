> **Type:** Index (MOC) — **Scope:** Architecture — **Status:** Active
> **Part of:** [[index]]

# Architecture

How Code29 is built and why. Notes here explain the shape of the system; the *individual
choices* that produced that shape are logged one level down, in [[Decisions]].

## Child notes

| Note | What it covers | Status |
|---|---|---|
| [[tech-stack-decision]] | The stack layer by layer — Astro, Vue islands, FastAPI, Vercel — and the reasoning for each | Active |
| [[design]] | Design source of truth (Google Stitch project `code29_web`) and the UI decisions taken from it | Active |
| [[improvement-canon]] | The ten points of an AI-First SDLC: the guide for analysing a client project and the structure of the delivered report | Active |
| [[contact-chat-v1]] | The phased design of the contact chat, from static form to AI flow | History — superseded by [[0009-conversational-contact-agent]] |
| [[testing-strategy]] | What is tested at each level and which gates must stay green before a merge | Active |
| [[i18n]] | EN/ES client-side switcher, `translations.ts` as the single source of copy | Active |
| [[seo-and-discoverability]] | Metadata, sitemap, robots, OG assets and the tests that assert them | Active |
| [[sdd-landing-v1]] | Implementation plan of landing v1 and the status of each phase | In progress |

## Sub-hub

- [[Decisions]] — the ten ADRs, chronological, with their supersession chains

## References

- [[index]] — parent hub
- [[Requirements]] — what the product must do; this hub explains how it does it
- [[Protocols]] — how the work itself is run
