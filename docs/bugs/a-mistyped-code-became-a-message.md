> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-30 — **Severity:** Medium
> **Part of:** [[Bugs]]

# A code with one digit too many stopped being a code

## Symptom

A visitor typing their verification code with the wrong number of digits was never told
the code was wrong. The bot answered by asking again for the email address it already
held — the one question it should never repeat.

Observed in production on 2026-08-30: the visitor typed `0101010`, seven digits.

## Root Cause

`BARE_CODE = /^\d{6}$/` demanded exactly six digits, so `readAnswer` classified anything
else as `kind: 'message'` and the reply travelled to `/conversation/turn` as free text.
With no verified address and `turns > 0`, `derive_next_step` correctly returned `email`,
and the model asked for the address again.

The rejection path existed and was correct (`contact-conversation.ts`, 400 →
`botCopy.codeRejected`, keeping `pendingEmail`). It simply never ran: the near-miss was
routed away one step earlier.

The logs show the shape of it — one `POST /verification/confirm` (the correct code) and,
before it, a `POST /conversation/turn` carrying what the visitor meant as a code.

## Fix

`BARE_CODE` becomes `/^\d{5,10}$/`: a run of digits while a verification is pending is a
*mistyped code*, not a new thing to say, and it must reach the endpoint that can call it
wrong. The floor of five keeps the opposite trap closed — `6` and `2024` stay answers.

Commit `6427682`, PR #51, COD-64.

## Affected Files

- `src/utils/contact-conversation.ts`

## Prevention

`contact-conversation.test.ts` covers digit runs of 5, 7 and 8 as codes while pending;
`6` and `2024` as messages while pending; and any run as a message when nothing is
pending.

The class of defect worth remembering: **a strict shape check silently rerouting input to
a different endpoint.** Nothing failed, nothing logged — the conversation just went
somewhere else.

## References

- [[0011-server-owned-conversation-script]] — the script this reply was routed against
- [[model-thinking-outlived-the-deadline]] — the other defect found in the same session
- [[Bugs]] — parent index
