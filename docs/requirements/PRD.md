# Code29 — Product Requirements Document (PRD)

> **Version:** 1.0  
> **Date:** 2026-04-11  
> **Owner:** Miguel Navarro Mantas  
> **Status:** Approved — pending implementation

---

## 1. Overview

**Product:** Personal brand landing page — positioned as CTO as a Service / AI Project Manager  
**Primary language:** Spanish  
**Tone & positioning:** "The Neon Architect" — direct, expert, disruptive, AI-first  
**Target audience:** Companies and startups seeking external technology leadership (CTO, AI PM)

---

## 2. Scope v1 — MVP

### 2.1 Landing Page (text-only)

Single Page Application with the following sections in order:

1. **Hero** — Main value proposition, CTA toward contact form
2. **Stats** — 4 key metrics: Speed, Efficiency, Scalability, Security
3. **Education & Stack** — AI Master's degree + tools and technologies
4. **Services** — CTO as a Service, AI Project Manager (description and value prop)
5. **Social Proof** — Client or project testimonials
6. **Contact** — Contact form with terminal aesthetic

**Content constraints:**
- No multimedia assets in the initial version (text and design system iconography only)
- All content in Spanish
- Must follow the Stitch design system faithfully (`code29_web`, project ID `3663672842421799446`)

### 2.2 Contact Form

The only interactive feature of the MVP.

**Fields:**
- Full name
- Company / organization
- Email address
- Message / description of need

**Behavior:**
- Client-side field validation (minimum: valid email, required fields)
- Terminal aesthetic (underline-only inputs, no border radius — per design system tokens)
- Submission states: loading, success, error
- Backend: **pending decision** (Formspree / Resend / own backend)

### 2.3 Cookie Notice and Configuration Selector

**GDPR requirements (mandatory for Spain/EU):**
- Banner shown on first visit before loading any non-essential cookies
- No analytics or marketing cookies activate before explicit consent
- Granular selector with at least three categories:
  - ✅ **Necessary** (always active, non-toggleable)
  - ⬜ **Analytics** (opt-in)
  - ⬜ **Marketing** (opt-in)
- Consent persisted in `localStorage`
- Direct link to Cookie Policy from the banner
- Option to review/change preferences at any time (accessible button in footer)

### 2.4 Legal Pages

The following pages are legally required and **not present in the current Stitch design** → must be added to the design before implementation:

| Page | Suggested route | Required by |
|------|----------------|-------------|
| Legal Notice / Terms of Use | `/legal-notice` | LSSI (Spain) |
| Privacy Policy | `/privacy-policy` | GDPR |
| Cookie Policy | `/cookies` | GDPR |
| Contact Form Data Policy | Inline or `/datos-contacto` | Recommended |

**Format:** Plain text pages, consistent with the design token system (same typography, palette, and spacing), no sidebar or complex navigation.

**Design note:** 4 additional screens with legal text layout must be created in Stitch before implementation begins.

---

## 3. Scope v2 — AI Assistant (future version, does not block MVP)

### 3.1 Description

Conversational AI assistant embedded in the landing that helps visitors assess their technology situation and prepares a personalized analysis document.

### 3.2 User Flow

1. User activates the assistant (dedicated button or section)
2. Assistant asks guided questions about the company's technology situation
3. On completion, generates a preliminary analysis document (summary + recommendations)
4. To access the full document, the user must:
   - Provide their email address
   - Accept the legal text for data transfer and use of the analysis
5. Document delivered by email or direct download

### 3.3 v2 Technical Requirements (to be detailed in v2 design phase)

- LLM backend: Claude API (Anthropic) — preferred
- Lead storage: email + timestamp + recorded consent
- Document generation: structured PDF or rendered Markdown
- Specific legal copy for data transfer in this context
- GDPR compliance for lead capture with explicit consent

---

## 4. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Core Web Vitals in green (LCP < 2.5s, CLS < 0.1, INP < 200ms) |
| **Accessibility** | WCAG 2.1 level AA minimum |
| **SEO** | Complete meta tags, Open Graph, Twitter Card, sitemap.xml, robots.txt |
| **Responsive** | Desktop-first (Stitch design), with functional mobile version |
| **Legal** | GDPR and LOPDGDD compliance (Spanish context) |
| **Security** | HTTPS, no sensitive data on client, anti-spam protection on form |

---

## 5. Pending Decisions

The following decisions must be made before or during MVP implementation:

| Decision | Options | Status |
|----------|---------|--------|
| Frontend stack | Astro / Next.js / Nuxt | ✅ Astro — C29-8 closed |
| Form backend | Formspree / Resend / own | ✅ Vercel Serverless + Resend — C29-9 closed |
| Hosting / deploy | Vercel / Netlify / other | ✅ Vercel — C29-10 closed |
| Domain | — | ⏳ Pending |
| Analytics | GA4 / Plausible / none | ✅ Google Analytics 4 (GA4) — C29-11 closed |

---

## 6. Design Dependencies

| Element | Status in Stitch | Action required |
|---------|-----------------|-----------------|
| Main landing (6 sections) | ✅ Designed (~31 screens) | None |
| Contact form | ✅ Designed | None |
| Cookie notice | ❓ To verify | Confirm or design |
| Legal Notice page | ❌ Not designed | Add to Stitch |
| Privacy Policy page | ❌ Not designed | Add to Stitch |
| Cookie Policy page | ❌ Not designed | Add to Stitch |
| AI Assistant (v2) | ❌ Not designed | Design in v2 |

---

## 7. References

- Design system: [docs/architecture/design.md](../architecture/design.md)
- Stitch project: `code29_web` (ID `3663672842421799446`)
- Project conventions: [CLAUDE.md](../../CLAUDE.md)
