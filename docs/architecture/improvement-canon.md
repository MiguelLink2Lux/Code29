> **Type:** Architecture — **Scope:** Contact-chat workflow report — **Status:** Active

# The Improvement Canon — ten points of an AI-First SDLC

Operational reference for the diagnosis the contact-chat report produces (COD-41, COD-42).
This is not marketing copy and not an inspirational list: it is the **structure the generated
report must follow**, the **signal that decides each point's state**, and the **service each
point sells**. Whoever implements the generator reads this document, not the chat transcript
it came from.

The rationale — why these ten and not another set — lives in
[[0008-improvement-canon]]. This document says *what* the canon is; the ADR says
*why*.

## Premise

Integrating AI into the software development lifecycle is **not writing code faster**. It is
optimising the whole value stream — from the moment a requirement is stated to the moment the
change is running in production and someone can tell whether it worked.

That distinction has a practical consequence: **automation amplifies whatever it is pointed
at**. Pointed at a disciplined flow it multiplies throughput; pointed at an ambiguous
backlog, an untested codebase or an unreviewed dependency tree it multiplies the disorder and
does it faster than a human could. A solid base is therefore not a prerequisite in the polite
sense — it is the thing that decides whether AI adoption pays off or accelerates the failure.

The canon is the description of that base, in the order it has to be built.

## How to read the canon

**Eight of the ten points are sequential.** They have real dependencies: you do not automate
deployment before you have tests to gate it, and you do not gate a merge on a review agent
before the work is broken into reviewable pieces. A diagnosis that recommends point 8 to a
lead who fails point 6 is recommending a faster way to ship regressions.

**Points 2 and 10 are transversal.** Training (2) and governance (10) are not steps that get
"finished" — they are permanent conditions, in force from before the first point and never
retired. Their numbering is kept so the canon stays stable and comparable, but a plan that
reads point 10 as *the last thing to do* has inverted it: governance is the precondition, not
the finishing touch. State this explicitly in any report or roadmap that orders the points.

**Every point carries a signal**, and signals come in two kinds:

| Kind | Source | Trust |
|---|---|---|
| **Measured** | `SiteSignals` — the lead's home page, fetched by `POST /api/v1/contact/site-analysis` | Objective. It is a fact about a page, and it is either present or absent. |
| **Reported** | An answer given in the chat flow | Self-declared. Reliable about intent, not about practice. |

Where neither is available, the point's state is **`no evaluado`** — never a negative
finding. See [Tri-state, and the honesty rule](#tri-state-and-the-honesty-rule).

---

## 1. Structured planning and deep context

Before automating anything, remove the ambiguity. AI output is bounded by the context it
receives: hyper-specific requirements, data schemas, architecture documentation. A vague
requirement does not produce a vague answer — it produces confidently generic code, or an
invented API that does not exist. The failure is silent, which is what makes it expensive.

What "deep context" means concretely: requirements specific enough that two engineers would
build the same thing; a written data schema; architecture documentation that is current
enough to be worth reading.

**Signal**

- *Reported* — are requirements written down before work starts, or does work start from a
  conversation? Is there architecture documentation, and was it updated this quarter?
- *Measured (weak)* — none directly. A public repository with an `openapi.json`, a README
  with an architecture section, or a docs site is circumstantial evidence, not a signal.

**Service:** CTO as a Service — *primary*. It is the offering that sells architecture
definition and roadmap. Análisis & Transformación IA is secondary (the diagnosis that
finds the gap).

---

## 2. Continuous team training · **TRANSVERSAL**

Not "does the team have licences" but "does the team know how to drive the tools". Two
distinct competences: using the assistants (GitHub Copilot, Cursor, Claude Code) and the
engineering above them — prompt engineering, agent architectures, knowing where the model's
competence ends. The skill being trained is *guiding* AI, *reading its output critically*,
and *recognising its limits*.

This is transversal: it is not completed, it is maintained. Tooling changes every few months
and a team trained on last year's workflow is a team with licences and no leverage.

**Signal**

- *Reported* — is there budgeted, recurring time for training, or is learning left to
  individual initiative? Does anyone own the practice? Can the team name what the tools are
  bad at?
- *Measured* — none. Training leaves no trace on a home page.

**Service:** Análisis & Transformación IA — *primary*. The offering explicitly includes
"capacitación del equipo en desarrollo asistido con IA".

---

## 3. Intelligent work management systems

Put agents inside the task manager, not beside it. Three concrete uses: automatic backlog
refinement, bottleneck prediction from historical velocity, and drafting user stories from
meeting notes. The point is that the system where work is tracked becomes a system that
*reasons about* the work, instead of a database someone updates by hand.

> **Revision (see ADR 0008).** The source list for this point cited "Jira, Linear or Asana".
> The tool is deliberately named generically here — the practice does not depend on the
> vendor. **In this project the task manager is Linear; Jira was retired on 2026-08-04**
> ([[linear-claude-integration]]). Citing Jira in our own canon contradicted our
> own documentation, which is exactly the kind of drift point 9 exists to prevent.

**Signal**

- *Reported* — is there a single task manager the whole team actually uses? Is any of it
  automated (refinement, triage, estimation), or is every ticket hand-written?
- *Measured* — none.

**Service:** AI Project Manager — *primary*. "Automatización de flujos de desarrollo" and
"orquestación de agentes autónomos" are literally this point.

---

## 4. AI-assisted development — the *engineer in the loop*

AI as accelerator, not replacement. The division of labour: repetitive work (scaffolding,
boilerplate, mechanical refactors) goes to the AI; business logic and architecture stay with
the engineers. The golden rule, non-negotiable: **the human developer is the final
accountable party for the code that reaches production.**

> **Revision (see ADR 0008).** Points 4 and 5 both described "how to work with AI" and
> overlapped. They are now separated by what each one actually governs: **point 4 is
> accountability** — who answers for the code that ships. **Point 5 is decomposition** — how
> the work is cut up. Same activity, two orthogonal properties, and a team can pass one while
> failing the other: an engineer who reviews everything but accepts thousand-line generations
> passes 4 and fails 5.

**Signal**

- *Reported* — is generated code read before it is merged, and by whom? Is there a stated
  rule about what AI is allowed to author unsupervised? Does anyone own the output — or is
  "the AI wrote it" an accepted explanation for a defect?
- *Measured* — none reliable. A `generator` meta tag or a framework hint says a scaffold was
  used, not who is accountable for it.

**Service:** Análisis & Transformación IA — *primary*. "Implementación del flujo AI-First" is
the delivery of this point.

---

## 5. Iterative, modular automation

Do not ask for a whole system in one request. Break the work into modular tasks —
*analyse → plan → implement → test* — so each step is debuggable on its own and errors are
caught where they are introduced instead of compounding through everything downstream.

The governing variable is **batch size**, and the property it buys is **verifiability**. A
small change with a passing test is a fact; a large change that "seems to work" is a
hypothesis. This is why the distinction from point 4 matters: accountability without
decomposition means a human accountable for a diff too large to actually review.

**Signal**

- *Reported* — is work broken into steps small enough to be verified separately, or does a
  feature arrive as one large change? Is there a plan before the code?
- *Measured (weak)* — public commit history granularity, where a repository is available.

**Service:** AI Project Manager — *primary*. It is the offering that sells workflow
orchestration and development-flow automation.

---

## 6. AI-guided testing (test-first)

Tests are the safety net of an automated flow — without them, automation is a faster route to
production for defects. AI applies at two levels: generating exhaustive cases, mocks and edge
cases; and assisted TDD, where the failing test is written first and the model produces the
code that makes it pass.

The order matters. A test written *after* the implementation, by the same agent that wrote
the implementation, tends to encode the bug as expected behaviour.

**Signal**

- *Reported* — **is there a test suite, and does it block the merge?** The second half is the
  real question: a suite nobody gates on is documentation, not a safety net. Is coverage
  known? Are edge cases written deliberately or discovered in production?
- *Measured* — none. Testing is invisible from outside.

**Service:** ⚠ **no clean fit — see [Where the canon exceeds the catalogue](#where-the-canon-exceeds-the-catalogue).**
The nearest is Análisis & Transformación IA (an AI-First flow includes its tests), but no
service on the site sells quality engineering or testing.

---

## 7. Code review as the first filter

Put agents on the pull requests as the first line of review: style, code smells, known
vulnerability patterns. Not to replace the human reviewer — to stop spending the human
reviewer on things a machine detects reliably, so their attention goes where a machine is
useless: architecture, logical security, business impact.

The gain is not speed, it is *reviewer attention reallocated*.

**Signal**

- *Reported* — **is review mandatory on pull requests, or can a change reach the main branch
  unreviewed?** Is any part of that review automated?
- *Measured (weak)* — for a public repository, branch protection is visible. For a private
  one, nothing.

**Service:** Automatización DevOps con IA — *primary, partial fit*. PR automation runs in the
CI pipeline the service sells, but the service copy never mentions code review. Recorded in
[Where the canon exceeds the catalogue](#where-the-canon-exceeds-the-catalogue).

---

## 8. CI/CD and predictive DevOps

AI inside the pipelines, not around them: real-time log analysis, anomaly detection *during*
the deploy (a latency spike, an error-rate change), automatic rollback on a detected
regression. The distinction from ordinary CI/CD is the word **predictive** — the pipeline
decides something, instead of only reporting.

The DORA metrics (deployment frequency, lead time for changes, change failure rate, time to
restore service) are the natural quantification of this point. They are a *signal for point
8*, not a substitute for the canon — see ADR 0008.

**Signal**

- *Reported* — **is there CI? Is deployment automated? Is rollback automated, or is it a
  human under pressure at 2am?** How is a regression detected — by monitoring or by a
  customer? DORA figures, if the lead has them.
- *Measured* — `server` and `framework_hint` headers hint at the hosting model; a managed
  platform (Vercel, Netlify, Cloudflare) implies some pipeline exists. Suggestive, not
  conclusive.

**Service:** Automatización DevOps con IA — *primary*. Exact match: "pipelines CI/CD
asistidos por IA", "automatización de despliegues y rollback", "observabilidad y alertado".

---

## 9. Living documentation and historical context

Automate documentation generation — API references, ADRs — from the commits, and store it in
a vector database (RAG) so future agents inherit the project's history instead of
rediscovering it. The problem being solved is that an agent with no memory of *why* a
decision was made will cheerfully undo it.

Two halves, worth separating: documentation that stays current because it is generated from
the code, and documentation that is *retrievable* by the agents that need it. The first
without the second is a folder nobody reads.

**Signal**

- *Reported* — is there a retrieval layer (vector store / RAG) the agents actually query?
- *Measured* — `robots_txt_present`, `sitemap_present`, a docs subdomain, an `openapi.json`:
  weak evidence that documentation is treated as an artefact. **Better signal, where a public
  repository exists: are there ADRs or versioned documentation living next to the code?**
  Documentation in a wiki drifts; documentation in the repository is reviewed with the diff
  that changes it.

**Service:** AI Project Manager — *primary, partial fit*. The RAG/vector-store half is an LLM
integration the service sells; the documentation-generation half belongs to CTO as a Service.
Recorded below.

---

## 10. Strict governance of data, secrets and dependencies · **TRANSVERSAL**

> **Revision (see ADR 0008).** The source point covered only privacy against public LLMs.
> That leaves out the supply chain, which is where most of the *exploitable* risk lives.
> Widened to three surfaces.

**a) Data and prompts.** Clear policy: never paste proprietary code, secrets or customer data
into free public LLMs. Use Enterprise tiers that guarantee **by contract** that inputs do not
train external models. "We told people to be careful" is not a policy.

**b) Secrets.** Secrets never live in the repository, never in a prompt, never in a log. The
scan that proves it runs in the pipeline, not in someone's memory.

**c) Dependencies.** The dependency tree is code you ship without reading. It needs a gate
that runs on every change, not an audit someone remembers to do.

> **Evidence from this project — why (c) is not theoretical.** Two failures found in Code29,
> both invisible until a gate went looking:
>
> 1. **`npm audit` reported 19 vulnerabilities, 2 of them critical**, and nobody was reading
>    it. The audit branch (PR #19, commit `8ab138b`) cut it to 6 with none critical and **no
>    breaking changes** — the fix was cheap; the *absence of anyone looking* was the defect.
> 2. **A runtime dependency vanished in a merge.** `pydantic[email]` disappeared from
>    `backend/pyproject.toml` while the lockfile and `requirements.txt` kept installing
>    `email-validator`. The deployed API worked perfectly; a fresh clone produced a backend
>    that raised on every request that validated an email address. The declared dependencies
>    and the installed ones had diverged, and every existing environment hid it.
>
> Neither was caught by review, by tests, or by the deploy. Both were caught the moment a gate
> was written that looked for them. This is the argument of the whole point: governance is a
> gate that runs, or it does not exist.

Transversal, and the most misread as sequential: numbering it tenth suggests you can start
the other nine without it. The opposite is true — every earlier point widens the surface this
one covers.

**Signal**

- *Reported* — **is there dependency scanning in the pipeline? Is there a written secrets
  policy?** Which AI tier is in use — free public or contracted Enterprise? Who signs off
  that customer data may reach a model?
- *Measured* — **HTTPS, and the security headers** (`Strict-Transport-Security`,
  `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`): the only externally verifiable governance evidence there is. Present
  headers mean someone configured them deliberately; a site on plain HTTP in 2026 is a
  finding on its own. Also: a `generator` tag exposing an outdated CMS version is a
  supply-chain signal visible from outside.

**Service:** CTO as a Service — *primary* (governance, due diligence, technical
accountability), with the pipeline-scanning half delivered by Automatización DevOps con IA.

---

## Sequential and transversal, at a glance

| # | Point | Nature | Primary service | Strongest signal |
|---|---|---|---|---|
| 1 | Structured planning and deep context | Sequential | CTO as a Service | Reported |
| 2 | Continuous team training | **Transversal** | Análisis & Transformación IA | Reported |
| 3 | Intelligent work management | Sequential | AI Project Manager | Reported |
| 4 | AI-assisted development (accountability) | Sequential | Análisis & Transformación IA | Reported |
| 5 | Iterative, modular automation (decomposition) | Sequential | AI Project Manager | Reported |
| 6 | AI-guided testing (test-first) | Sequential | ⚠ none — nearest Análisis & Transformación IA | Reported |
| 7 | Code review as the first filter | Sequential | Automatización DevOps con IA *(partial)* | Reported |
| 8 | CI/CD and predictive DevOps | Sequential | Automatización DevOps con IA | Reported + measured (weak) |
| 9 | Living documentation and historical context | Sequential | AI Project Manager *(partial)* | Reported + measured (weak) |
| 10 | Governance of data, secrets and dependencies | **Transversal** | CTO as a Service | Reported + **measured** |

Dependency order among the sequential eight: **1 → 3 → 4 → 5 → 6 → 7 → 8**, with 9 usable at
any point after 1 and most valuable once 7 exists (reviews are where decisions get recorded).
2 and 10 hold throughout.

## Signals: measured versus reported

Only two points have a genuinely **measured** signal — 8 (weakly, from hosting hints) and 10
(properly, from HTTPS and security headers). Point 9 gets weak measured evidence from
`robots.txt` / `sitemap.xml`. Everything else is **reported**, and reported signals are
self-declared: they describe what a lead believes about their process.

Two consequences for the generator:

1. **Never present a reported signal as a measurement.** "You told us there is no CI" and "we
   observed no CI" are different claims, and only one of them is defensible if challenged.
2. **The measured signals are the report's credibility.** They are the part a lead cannot
   dispute and did not supply. Lead with them.

### Available measured fields

From `SiteSignals` (`backend/app/services/site_analysis.py`), all of which the flow already
collects: `https`, `security_headers`, `redirect_hops`, `status_code`, `title`,
`meta_description`, `canonical_url`, `viewport_declared`, `lang_declared`,
`open_graph_present`, `generator`, `framework_hint`, `server`, `html_bytes`, `script_count`,
`stylesheet_count`, `image_count`, `robots_txt_present`, `sitemap_present`.

These measure a **home page**, not an engineering organisation. They are strong evidence for
point 10 and circumstantial for 8 and 9. They say nothing about points 1–7, and no amount of
HTML parsing will change that.

### The conversational gap

The chat flow currently asks **five** practice questions — `delivery`, `bugs`, `deploys`,
`security`, `observability` — matching the five `DiagnosisAxis` members. A ten-point canon
needs reported signals for ten points, and five of them have no question behind them today.

Two ways forward, and the choice belongs to whoever implements COD-42: extend the flow (more
questions, higher abandonment), or accept `no evaluado` on the unasked points. **Inventing a
state for an unasked question is not one of the options.**

## Tri-state, and the honesty rule

Every point resolves to exactly one of three states:

| State | Meaning | Requires |
|---|---|---|
| `cubierto` | Evidence the practice exists | A measured signal, or a clear reported answer |
| `parcial` | Evidence it exists partially or without a gate | A reported answer describing something incomplete |
| `no evaluado` | No evidence either way | Nothing was measured and nothing was asked |

`no evaluado` is a first-class outcome, not a fallback for laziness. A report that says "not
assessed — we did not ask" is more credible than one that infers a weakness from silence, and
it is the only defence against the structural risk of a fixed ten-point canon: **being obliged
to say something about every point, whether or not there is anything to say.** That risk is
named and accepted in ADR 0008.

Rules for the generator:

- No signal → `no evaluado`. Never `parcial` as a hedge.
- A measured signal outranks a reported one where both exist.
- The absence of evidence is never phrased as the presence of a problem.
- A recommendation attaches to a point's primary service, and only to a service the site
  actually sells.

## Where the canon exceeds the catalogue

Three points do not map cleanly onto the four services in `src/i18n/translations.ts`. This is
recorded rather than smoothed over, because a canon whose recommendations cannot be bought is
a product finding, not a documentation problem.

| Point | Fit | What is missing from the catalogue |
|---|---|---|
| **6 — AI-guided testing** | **None** | No service sells quality engineering, test strategy or QA automation. It is the most actionable diagnosis in the canon (a missing test suite is concrete, cheap to state, and expensive to ignore) and there is nothing to sell against it. The nearest offering, Análisis & Transformación IA, sells an AI-First flow that implies tests without naming them. |
| **7 — Code review as the first filter** | Partial | Automatización DevOps con IA sells CI/CD pipelines, which is where a review agent runs, but neither that service nor any other mentions code review or PR automation. |
| **9 — Living documentation** | Partial | Split across two services: the RAG/vector-store half fits AI Project Manager, the documentation-generation half fits CTO as a Service. Neither sells it as such. |

**Finding to route to product:** the canon recommends testing, review automation and living
documentation, and the site sells none of the three by name. Either the service copy grows to
cover them, or the report recommends work Code29 does not visibly offer — and a diagnosis that
ends in an unavailable recommendation is a worse lead than no diagnosis. Tracked outside this
document; not resolved here.

## Implementation status

**Nothing in this document is implemented.** COD-42 is in Backlog. The backend today has
`DiagnosisAxis` with five members (`ai_development`, `ai_quality`, `delivery_automation`,
`security_dependencies`, `observability`) in `backend/app/services/report.py`, and the report
generated from it — stub or Gemini — has five axes, not ten points. The canon replaces that
structure when COD-42 is implemented; see ADR 0008 for the consequence on ADR 0006.

## References

- [[0008-improvement-canon]] — why these ten points and not others
- [[0006-guided-ai-contact-flow]] — the flow that collects the reported signals; its report structure is superseded by 0008
- [[0007-gemini-over-rest]] — how the report is generated, and why model output is validated against enums
- [[contact-chat-v1]] — the phased design of the contact flow
- [[linear-claude-integration]] — Linear is the task manager; Jira was retired 2026-08-04
- [[index]] — ADR index
