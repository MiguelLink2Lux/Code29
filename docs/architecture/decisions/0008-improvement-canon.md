> **Type:** Architecture · ADR — **Status:** Accepted — **Date:** 2026-08-23

# ADR 0008 — Ten fixed improvement points as the structure of the workflow report

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Miguel Navarro Mantas
- **Partially supersedes:** [[0006-guided-ai-contact-flow]] (the report's diagnosis structure)
- **Defines:** [[improvement-canon]]

> **Revision — 2026-08-23.** The decision (these ten points, in this order, two transversal) is
> unchanged. Its *justification* was corrected on two counts that the first version of this
> document got wrong:
>
> 1. **The canon is not a service catalogue.** The first version mapped each point to one of the
>    four services on the site and recorded the points that did not map as a product finding to
>    route. That framing is discarded. The canon is (a) the guide for analysing the client's
>    project and (b) the roadmap of the deliverable PDF. The point→service table and the section
>    "Where the canon exceeds the catalogue" are removed from [[improvement-canon]]: their
>    premise — that a point with no service behind it is a defect — is false. The commercial
>    objective is a **single** engagement, not ten sellable items.
> 2. **An absence of signal has commercial value.** The first version treated `no evaluado` as a
>    cost to be minimised and "five points will come back not assessed" as a risk of the design.
>    Inverted: a point the client never raises is a point they are not contemplating, which is
>    the opportunity the report exists to surface. The tri-state stays, as factual honesty; the
>    reading of an absence changes.
>
> Also recorded here for the first time: the deliverable is a **PDF**, not the email text
> delivered today. Pending work, tracked in Linear.

## Context and Problem Statement

The contact chat's payoff is a generated **workflow report** ([[0006-guided-ai-contact-flow]],
COD-41 / COD-42). The flow, the verification, the site analysis and the model connector all
exist. What does not exist is an answer to the question the report is supposed to answer:
**against what is a lead being diagnosed?**

Today the answer is `DiagnosisAxis` in `backend/app/services/report.py` — five members
(`ai_development`, `ai_quality`, `delivery_automation`, `security_dependencies`,
`observability`) that were chosen to match the five practice questions the chat happens to
ask. That is backwards: the questions were designed first and the diagnosis structure was
derived from them, so the report can only diagnose what the form already asked. It has no
independent claim to being the right set of things to look at.

A commercial diagnosis report needs a **reference model**: a fixed, defensible list of what a
software organisation should have in place to make AI adoption pay off, stable enough that two
leads' reports are comparable and specific enough that each finding names a concrete stage of
the workflow Code29 prepares. Choosing that list is the decision recorded here. The reference
model is an **analysis instrument and a roadmap**, not a catalogue of things to buy.

The chosen list — the premise, the ten points and their observable signals — is written out in
[[improvement-canon]]. This ADR argues for *why that list*.

## Decision Drivers

- **The report is a commercial diagnosis, not a maturity assessment.** Its job is to end in one
  actionable proposal: contracting the preparation of a complete AI-assisted development
  workflow — team training, environment preparation, and quality-criteria training and control.
  The points are how that proposal is argued, not a list of separate offers.
- **Comparability.** Two leads must be diagnosable against the same reference, or the report is
  an opinion piece and the pipeline has no aggregate signal.
- **Validatability.** Model output is untrusted and validated against Pydantic enums
  ([[0007-gemini-over-rest]]). The reference model has to be expressible as a closed enum.
- **Coverage of the value stream.** The premise of the canon is that AI optimises the whole
  flow, not the coding step. A reference that only covers coding contradicts its own premise.
- **Honesty under missing information.** A lead answers a handful of questions. Whatever is
  chosen must survive not knowing most of what it asks about — and must turn what the lead never
  mentioned into a subject worth raising, not into a gap to apologise for.

## Considered Options

1. **Ten fixed points — a canon of our own** (chosen).
2. **Adopt an existing framework:** DORA / DevOps Research, SPACE, CMMI, ISO/IEC 12207.
3. **Fewer points — keep five**, as `DiagnosisAxis` has today.
4. **More points, or a list assembled per client** from whatever the conversation surfaces.

## Decision Outcome

Chosen: **option 1** — a fixed canon of ten points, in a fixed order, with two of them marked
transversal. It becomes a backend enum of exactly ten members with a test pinning the order,
and it replaces `DiagnosisAxis`.

### Why not an existing framework (option 2)

This is the strongest alternative and the one worth arguing properly, because "invent your own
framework" is usually the wrong answer.

**DORA** measures four things: deployment frequency, lead time for changes, change failure
rate, and time to restore service. They are excellent and they are **metrics** — they tell you
how your delivery performs, not what to do about it. A lead scoring badly on change failure
rate learns that changes break; nothing in DORA says whether the missing piece is tests,
review, or rollback. Also, all four require data a lead does not have to hand and cannot
supply in a chat.

Where DORA does fit: as the **quantification of canon point 8** (CI/CD and predictive
DevOps). If a lead has DORA numbers, they are the best possible signal for that point. That is
a use of DORA inside the canon, not a replacement for it.

**SPACE** measures developer productivity across five dimensions — a research instrument for
studying teams over time, with survey-based dimensions (satisfaction, communication) that
cannot be sampled from a lead's home page or a ten-question chat.

**CMMI** and **ISO/IEC 12207** are process-maturity and lifecycle-process standards. They are
comprehensive, auditable, and describe process *maturity* rather than AI adoption — which is
the subject of the report. Diagnosing a lead at "CMMI level 2" is a statement no prospect acts
on, and it costs an audit to produce honestly.

The common failure across all four: **they are measurement or maturity frameworks, not
adoption plans.** A commercial diagnosis needs stages a reader can start on Monday, ordered into
a roadmap they can contract as one piece of work. None of these produce that, and bending one
until it does would leave a framework whose name no longer describes what we did with it.

Secondary reason, stated plainly: none of them covers AI-specific practice at all. Prompt
engineering, agent architecture, the engineer-in-the-loop accountability rule, LLM data
governance, RAG-backed project memory — none of it exists in DORA, SPACE, CMMI or 12207,
because they predate the problem. The canon's points 2, 3, 4, 9 and 10a have no counterpart in
any of them.

### Why ten, and not five (option 3)

Five is what exists and it is cheaper: five questions, a shorter report, less to write.

Ten wins on two grounds.

**Coverage.** The five current axes are all downstream of the keyboard —
development, quality, delivery, security, observability. They contain no point about
requirements and context before work starts (canon 1), none about the team's competence (2),
none about how work is managed (3), none about accountability for generated code (4), and none
about documentation and institutional memory (9). A report built on them tells a lead how their
pipeline looks and says nothing about the half of the value stream where, per the canon's own
premise, the returns are largest. Diagnosing only the automatable half of the SDLC, in a report
whose thesis is that AI optimises the whole SDLC, is a contradiction the reader can see.

**Sequence.** Ten points with an explicit dependency order (1 → 3 → 4 → 5 → 6 → 7 → 8, with 2
and 10 transversal) yield a *roadmap*, and a roadmap is what converts a diagnosis into an
engagement. Five unordered axes yield a scorecard. Sequence is also what stops the report
recommending automated deployment to a team with no tests.

The cost is real and accepted: a longer report, more to generate, more to validate, and a
higher risk that the reader skims. Mitigation is presentational — the report leads with the
measured findings and the points that are `cubierto`/`parcial`, and lists `no evaluado` points
compactly rather than padding them into paragraphs.

### Why not a variable list (option 4)

Assembling the list per client — asking what the lead cares about and diagnosing that — is
attractive: it always fits, and it never has to say "not assessed".

It is rejected because it destroys the two properties the report exists to have. **Two reports
are no longer comparable**, so there is no aggregate view of the pipeline and no way to learn
which findings actually convert. And a variable structure **cannot be validated**: the model's
output is trusted only because it is checked against a closed enum ([[0007-gemini-over-rest]]),
and an open list means accepting whatever axis the model invents — exactly the failure mode
that ADR's `ModelResponseInvalid` exists to prevent. A per-client list also has no defensible
authorship: it is whatever the conversation drifted toward.

### The revisions applied to the source list

The ten points came from a list Miguel wrote. Five changes were made in adopting it, and each
is marked in [[improvement-canon]] where it applies:

1. **Point 3 no longer names Jira.** The source cited "Jira, Linear or Asana". Jira was retired
   from this project on 2026-08-04 ([[linear-claude-integration]]); citing it in our own
   reference model contradicted our own documentation. The tool is now named generically, with
   Linear as this project's instance.
2. **Point 10 widened** from "data governance" to "data, secrets and **dependencies**". As
   written it covered only privacy against public LLMs and left out the supply chain, which is
   where most exploitable risk lives. Justified with evidence from this repository rather than
   from principle: `npm audit` sat at 19 vulnerabilities, 2 critical, unread until someone
   audited (PR #19, `8ab138b`, down to 6 and none critical, no breaking changes); and
   `pydantic[email]` disappeared from `backend/pyproject.toml` in a merge while the lockfile
   kept installing it, so the deployed API worked and a fresh clone was broken on every request
   validating an email. Neither was found by review, tests or deploy — both were found the
   moment a gate looked.
3. **Points 2 and 10 marked transversal.** The other eight are sequential with real
   dependencies. Training and governance are not steps that complete; numbering governance
   tenth implies the first nine can start without it, which inverts the truth. Numbering is
   kept for stability, the nature is stated explicitly.
4. **Points 4 and 5 disambiguated.** Both described "how to work with AI". They now split by
   what they govern: 4 is **accountability** (who answers for production code), 5 is
   **decomposition** (batch size and verifiability). Orthogonal, and independently failable.
5. **Every point carries an observable signal** — what to check to decide covered / partial /
   not assessed, split into signals *measured* from the lead's site and signals *reported* in
   the chat. This is the most consequential revision: without a signal per point the report is
   opinion rather than diagnosis, and the generator has nothing to validate against.

### Consequences

**Structural — this supersedes part of ADR 0006**

The canon becomes a `StrEnum` in the backend with **exactly ten members in canon order**, with
a test pinning both membership and order (order is load-bearing: it is the roadmap). It
**replaces `DiagnosisAxis`** and with it the five-axis report structure described in
[[0006-guided-ai-contact-flow]]. Everything else in 0006 — the step order as an authorisation
rule, stateless verification, the Turnstile gate, the SSRF guard, the privacy posture — stands
unchanged. Only the shape of the report's diagnosis changes.

`ServiceOffering` (four members) is **unchanged**, and the canon does not map onto it. The four
services are how the offering is presented on the site; the canon is how a client's project is
examined and how the resulting roadmap is ordered. No point→service correspondence is required
or asserted.

**The report gets longer, and the flow gets a gap**

The chat asks five practice questions. Ten points need reported signals for ten points, so
five points have no question behind them today. Either the flow grows — more questions, higher
abandonment — or those points come back `no evaluado`. That choice belongs to COD-42 and is not
decided here, and neither branch is a failure: unasked points are stages of the flow the client
has not raised, which is material for the proposal. What *is* decided: inventing a state for an
unasked question is not an option.

**Named risk: ten points always present invite a fabricated verdict**

This is the real cost of a fixed canon. A lead who answers five questions and has a home page
will not have supplied evidence for most of the ten points, and a fixed structure invites the
generator — human or model — to produce something for each slot anyway. A fabricated finding in
a commercial report is worse than a gap: it is a claim the prospect may know to be false, which
discredits the findings that were correct.

Note what the risk is *not*. It is not that points come back `no evaluado`; that is the expected
outcome and a useful one. A point the client never raised is a point outside how they work today
— the part of the workflow they are not contemplating, and therefore the part with the most to
gain from the engagement. The risk is only the fabrication.

Mitigation, in this order:

1. **A tri-state per point**: `cubierto` / `parcial` / `no evaluado`, with `no evaluado` a
   first-class outcome and not a hedge.
2. **Absence of evidence is rendered as an unbuilt stage of the flow, never as an observed
   defect.** "Nothing in the conversation covered a gated test suite, and building one is part of
   what we prepare" is legitimate; "you have no tests" when nobody asked is not.
3. **Measured signals outrank reported ones**, and the report leads with them — they are the part
   the lead did not supply and cannot dispute.
4. **`no evaluado` points are listed compactly**, not expanded into prose, so the report's length
   tracks the evidence available. Compact does not mean omitted: they are the roadmap's open
   stages.

**The deliverable is a PDF, and it does not exist yet**

The objective of the flow is a PDF the lead can keep and forward; the canon is its table of
contents. Today `render_report_email()` in `backend/app/services/mailer.py` sends the report as
plain text in an email. The PDF is pending work, tracked in Linear, and is recorded here as the
target state so no later reader mistakes the email body for the intended deliverable.

**Good — the canon is now a document, not a conversation**

The reference model is versioned next to the code that implements it, which is canon point 9
applied to the canon itself. A change to the diagnosis structure is now a reviewed diff.

## References

- [[improvement-canon]] — the canon itself: premise, ten points, signals, single commercial objective
- [[0006-guided-ai-contact-flow]] — the flow; its five-axis report structure is superseded here
- [[0007-gemini-over-rest]] — enum validation of model output, which the canon must fit
- [[contact-chat-v1]] — the phased design of the contact flow
- [[linear-claude-integration]] — Linear is the task manager; Jira retired 2026-08-04
- [[index]] — ADR index
