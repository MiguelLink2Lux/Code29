> **Type:** Architecture · ADR — **Status:** Accepted — **Date:** 2026-06-19
> **Part of:** [[Decisions]]

# ADR 0002 — FastAPI (+ Pydantic) as the backend framework

- **Status:** Accepted
- **Date:** 2026-06-19
- **Deciders:** Miguel Navarro Mantas

## Context and Problem Statement

The Phase 2/3 backend must serve AI features (Claude API), validate structured data,
and scale with async I/O. We need to pick a Python web framework.

## Decision Drivers

- Async-first request handling for AI/streaming workloads.
- First-class data validation and typed contracts.
- Native AI/ML ecosystem fit (Genkit, provider SDKs, etc. — see [[0005-genkit-runtime]]).
- Auto-generated OpenAPI for client/contract tooling.

## Considered Options

1. **FastAPI** — async, Pydantic validation, automatic OpenAPI.
2. **Flask** — minimal, sync-first, validation/serialization bolted on.
3. **Django REST Framework** — batteries-included, ORM/admin, heavier and sync-oriented.

## Decision Outcome

Chosen option: **FastAPI with Pydantic**, because it provides async performance,
typed validation, and OpenAPI generation out of the box, and aligns with the Python
AI ecosystem the product targets in Phase 3.

### Consequences

- Good: async endpoints, Pydantic models, free OpenAPI docs at `/docs`.
- Good: settings via `pydantic-settings`; types enforce the design-token/contract integrity goal.
- Bad: fewer built-ins than Django (no ORM/auth/admin) — these are assembled as needed.
- Neutral: ties the backend to the Python 3.12 + uv toolchain (see pyproject).

## References

- [[tech-stack-decision]]
- [[0001-backend-repo-structure]]
- [[0003-api-versioning-strategy]]
- [[0005-genkit-runtime]] — supersedes the assumption of direct Anthropic SDK access
