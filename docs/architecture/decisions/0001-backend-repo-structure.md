> **Type:** Architecture · ADR — **Status:** Accepted — **Date:** 2026-06-19

# ADR 0001 — Backend lives in a monorepo `backend/` folder

- **Status:** Accepted
- **Date:** 2026-06-19
- **Deciders:** Miguel Navarro Mantas

## Context and Problem Statement

Phase 2 introduces a Python/FastAPI backend (`api.<domain>`) alongside the existing
Astro + Vue frontend (deployed on Vercel). We must decide where the backend code
lives relative to the frontend: a separate Git repository or the same repository.

## Decision Drivers

- Early-phase velocity — minimize coordination overhead while the API is small.
- Atomic cross-stack changes (frontend contract + backend endpoint in one commit).
- Clear deploy isolation — the backend must not interfere with the Vercel frontend build.

## Considered Options

1. **Monorepo** — FastAPI app in a `backend/` folder inside the Code29 repo.
2. **Separate repository** — a dedicated repo for the API with its own CI/CD.

## Decision Outcome

Chosen option: **Monorepo (`backend/` folder)**, because at this stage the
coordination cost of two repos outweighs its isolation benefits. Vercel builds only
the Astro frontend, so `backend/` is inert to the frontend deploy.

### Consequences

- Good: single clone, atomic cross-stack commits, one issue tracker, simpler local setup.
- Good: backend is invisible to the Vercel adapter — no frontend build impact.
- Bad: the repo mixes two toolchains (Node + Python); contributors need both.
- Bad: future CI must scope pipelines per path; deploy targets must filter `backend/`.
- Revisitable: if the backend grows independent release cadence, extraction to its own
  repo is a clean, additive migration.

## References

- [[tech-stack-decision]] — overall architecture and phases
- [[0002-fastapi-as-backend-framework]]
- [[0003-api-versioning-strategy]]
