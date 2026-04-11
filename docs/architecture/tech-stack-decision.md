# Code29 — Technical Stack Decision

> **Author:** Miguel Navarro Mantas
> **Date:** 2026-04-11
> **Status:** Approved — C29-8 closed
> **Original document:** `informe_tecnico_landing_cto.md`

---

## 1. Objective

Define the optimal technology architecture for a professional landing page positioning the profile as CTO and AI Developer, ensuring:

- High performance and SEO
- Future scalability
- AI system integration
- Clear separation of responsibilities

---

## 2. Architectural Decision

A decoupled architecture based on:

```
Frontend (Astro)
   ↓
Interactive components (Vue Islands)
   ↓
Backend API (FastAPI - Python) [Phase 2+]
   ↓
AI Services [Phase 3]
```

---

## 3. Technology Justification

### 3.1 Frontend: Astro

**Reasons:**
- Static generation → maximum speed
- SEO-optimized out of the box
- Minimal JavaScript sent to client
- Modern Islands architecture

**Key advantages:**
- Ultra-fast load — ideal for professional landing
- Selective Vue hydration only where needed

### 3.2 Interactivity: Vue 3

**Usage:** Dynamic components (cookie consent, contact form, v2 chatbot)

**Reason:** Loaded only where it adds value. Avoids penalizing global performance.

### 3.3 Backend: FastAPI (Python)

**Reasons:**
- High performance async framework
- Native AI/ML ecosystem (Anthropic SDK, LangChain, etc.)
- Scalable and modern — Pydantic for data validation

**Responsibilities:**
- Business logic
- AI integration (Claude API)
- Data processing and lead storage

### 3.4 TypeScript — Mandatory

Required across all layers (Astro + Vue) to enforce design token integrity and prevent visual drift.

---

## 4. Deployment Strategy

### Frontend (Astro)
- Platform: **Vercel**
- Type: Static (CDN)
- Deploy: Automatic CI/CD on push to `main`

### Backend (FastAPI) — Phase 2+
- Initial phase: **Render / Railway**
- Scaling: AWS + Docker

### Domain structure

```
www.dominio.com   → Frontend (Astro on Vercel)
api.dominio.com   → Backend (FastAPI)
```

---

## 5. Implementation Phases

### Phase 1 — Static Landing (current)
- Static Astro landing with Vue islands
- Contact form via **Vercel serverless function + Resend** (no FastAPI needed)
- Cookie consent system (GDPR compliant)
- Legal pages
- Deploy to Vercel

> **Note:** FastAPI is NOT introduced in Phase 1. A serverless function handles the contact form. This avoids operational overhead (CORS, separate domain, monitoring) before the AI backend is justified.

### Phase 2 — AI System Design + FastAPI Introduction
- Introduce FastAPI backend (`api.dominio.com`)
- Design and analysis of the AI analyzer system
- First API endpoints (contact form migrated, lead capture)
- Architecture and spec documents for the AI assistant (SDD cycle)
- No production AI features yet — design phase only

### Phase 3 — Full AI Implementation
- Complete, functional AI analyzer
- Conversational assistant (Claude API streaming)
- Lead capture with GDPR-compliant consent
- Document generation (PDF / structured Markdown)
- Full production deployment with monitoring

---

## 6. Scalability Strategy

- Total frontend/backend separation
- API versioning (`/api/v1/`)
- Independent evolution of AI services
- Prepared for:
  - Advanced chatbot (Phase 3)
  - AI Project Analyzer (Phase 3)

---

## 7. Testing Strategy

| Layer | Tools | Phase |
|-------|-------|-------|
| Vue components | Vitest + @testing-library/vue | Phase 1+ |
| E2E | Playwright | Phase 1+ |
| FastAPI endpoints | pytest + httpx | Phase 2+ |
| AI integration | pytest + respx (mock) | Phase 2+ |

See: [`docs/protocols/ai-agents.md`](../protocols/ai-agents.md) — test-engineer skill.

---

## 8. Conclusion

This architecture allows:

- Maximum performance from day one
- Scalability without critical refactoring
- Solid technical positioning as CTO

> This is not just a landing page — it is the foundation for an AI-powered services platform.

---

## References

- PRD: [docs/requirements/PRD.md](../requirements/PRD.md)
- Design system: [docs/architecture/design.md](design.md)
- Agent map: [docs/protocols/ai-agents.md](../protocols/ai-agents.md)
- Jira: C29-8 (closed), C29-10 (closed)
