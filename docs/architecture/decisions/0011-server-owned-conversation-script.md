> **Type:** Architecture · ADR — **Status:** Accepted — **Date:** 2026-08-29
> **Part of:** [[Decisions]]

# ADR 0011 — The server owns the conversation script, and the guard blocks conversations rather than people

- **Status:** Accepted
- **Date:** 2026-08-29
- **Deciders:** Miguel Navarro Mantas
- **Builds on:** [[0006-guided-ai-contact-flow]], [[0007-gemini-over-rest]], [[0009-conversational-contact-agent]]
- **Cycle:** `conversational-lead-capture-flow` (COD-52)

## Context and Problem Statement

[[0009-conversational-contact-agent]] replaced eleven fixed steps with a conversation, and
in doing so dissolved something the questionnaire had for free: **a single owner of the
order**. Afterwards the order lived in three places — the server's `missing`, the model's
prompt, and a `mode` computed in `ContactConversation.vue`.

Three owners cannot disagree quietly. The visible symptom was that the email address, the
one fact without which the report cannot be delivered at all, was requested **last**: the
component only switched to it once `missing` had shrunk to a single entry. The prompt, in
parallel, was forbidden from ever mentioning an address. Neither half was wrong on its own.

The second problem was that the extraction stage — the only place in the system where a
model reads visitor prose — had no defence against prompt injection beyond a sentence of
conduct inside the prompt it was defending.

## Decision

**1. `derive_next_step` on the backend is the single authority on the script.** It is a
pure function of (facts, verified address, turns, blocked), computed per turn and returned
as `next_step`. The client renders it. The model chooses wording only.

It is **derived, never sealed into the envelope**. A step sealed before the access token
existed goes stale the instant the address is verified — the exact trap `complete` already
fell into, which is why `deliverReport` had to consult `missing` instead of `complete`.

**2. Injection is filtered at the extraction surface only**, in `services/prompt_guard.py`,
following the shape already set by `services/url_guard.py`: own module, own exception,
tested in isolation, called by the endpoint **before** the model. The report generator keeps its own guarantee — it
never sees visitor prose (ADR 0007) — and is bounded *by construction*. The two mechanisms
are complementary. **Do not unify them:** doing so removes one of the two guarantees.

**3. Zero tolerance applies to the response, not to the threshold.** A detected attempt ends
the conversation with no warning and no second chance. Detection still requires an actual
attack shape — an imperative aimed at the system — not the mere appearance of words like
"prompt" or "system". Code29 sells to engineering teams: that is its leads' own vocabulary.

## Consequences

### The block ends a conversation, never a person

The backend keeps no store ([[0006-guided-ai-contact-flow]]), so nothing can remember a
visitor. `blocked` rides inside the HMAC signature, which stops it being *edited* — it does
not stop the envelope being *dropped*. A blocked visitor who reloads starts clean.

This is **specified behaviour, not a gap**. Anything stronger needs per-visitor state, which
would be a new ADR and a reversal of 0006. Do not read the reload as a defect and do not
present the guard as access control.

### A false positive is invisible

The same absence of a store means a legitimate lead who trips the guard leaves **no trace
anywhere** — no log, no counter, no alert. The lever if it ever happens is the guard's
threshold, and the only signal will be a human noticing.

### The model reports injection, and that is advice

`_ModelDelta.injection` is a second net. It is never the only control: asking the component
under attack to report the attack cannot be a control. The deterministic guard runs first
and short-circuits, so an injection is not paid for in tokens.

### Copy rotation costs one persisted seed

The verification messages are ephemeral by design — personal data is never written to
storage — so they re-render on reload. One seed persisted with the thread indexes every
pool, which keeps the bot's wording stable across a reload without persisting the messages.

## Compliance

- `derive_next_step` truth table, guard patterns and the eight non-blocking industry
  phrasings are asserted in `test_conversation_envelope.py` and `test_prompt_guard.py`.
- A spy asserts the guard runs **before** the extractor: a correct guard placed after the
  model would pass every unit test while defending nothing.
- E2E covers the early address and a blocked conversation, including that the notice never
  names what tripped the guard.

## References

- [[Decisions]] — parent index
- [[0006-guided-ai-contact-flow]] — the stateless design that bounds what blocking can mean
- [[0009-conversational-contact-agent]] — the cycle that dissolved the single owner
- [[turnstile-widget-outside-the-dom]] — same lesson on stubs and end-to-end observation
