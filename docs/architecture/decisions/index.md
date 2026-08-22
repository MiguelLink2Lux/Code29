# Architecture Decision Records — Index

Chronological log of significant architecture decisions (MADR format).

| ADR | Title | Status |
|-----|-------|--------|
| [[0001-backend-repo-structure]] | Backend lives in a monorepo `backend/` folder | Accepted |
| [[0002-fastapi-as-backend-framework]] | FastAPI (+ Pydantic) as the backend framework | Accepted |
| [[0003-api-versioning-strategy]] | URL path API versioning (`/api/v1`) | Accepted |
| [[0004-backend-deploy-provider]] | Backend deploys on Vercel as a second project (root `backend/`) | Accepted |
| [[0006-guided-ai-contact-flow]] | Guided AI contact flow with stateless email verification | Accepted |
| [[0007-gemini-over-rest]] | Gemini reached over the REST API, not the Genkit SDK (partially supersedes 0005) | Accepted |

> ADR 0005 (Genkit on Python, embedded in the backend) is reserved by a change in flight and
> is intentionally absent from the table until that record lands. When it does, its status is
> **partially superseded by [[0007-gemini-over-rest]]**: the AI layer still lives inside the
> FastAPI backend, but the model is reached over REST instead of through the Genkit SDK.

## References

- [[tech-stack-decision]]
- [[contact-chat-v1]]
