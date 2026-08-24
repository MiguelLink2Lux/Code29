> **Type:** Architecture · ADR — **Status:** Accepted — **Date:** 2026-06-19
> **Part of:** [[Decisions]]

# ADR 0003 — URL path API versioning (`/api/v1`)

- **Status:** Accepted
- **Date:** 2026-06-19
- **Deciders:** Miguel Navarro Mantas

## Context and Problem Statement

The API will evolve (lead capture, AI assistant, document generation across phases).
We need a versioning scheme that lets the contract change without breaking existing
clients, decided before the first endpoint ships.

## Decision Drivers

- Explicit, discoverable versions for external clients.
- Simple routing and caching at the edge/proxy layer.
- Low friction to run multiple versions side by side.

## Considered Options

1. **URL path prefix** — `/api/v1/...`.
2. **Header versioning** — `Accept: application/vnd.code29.v1+json`.
3. **No versioning** — single evolving surface.

## Decision Outcome

Chosen option: **URL path prefix `/api/v1`**, because it is the most explicit and
operationally simple: routers mount under a prefix, proxies and caches key on the
path, and a future `/api/v2` can coexist without disturbing v1.

### Consequences

- Good: obvious in logs, docs, and curl; trivial to route via an aggregate `APIRouter(prefix="/api/v1")`.
- Good: edge caching and CORS rules key cleanly on the path.
- Bad: coarse-grained — a new version duplicates the surface rather than evolving fields.
- Neutral: clients must update the base path on a major bump (acceptable, that is the point).

## References

- [[tech-stack-decision]] — §6 Scalability Strategy already mandates `/api/v1/`
- [[0001-backend-repo-structure]]
- [[0002-fastapi-as-backend-framework]]
