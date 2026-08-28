> **Type:** Bug — **Status:** Fixed — **Date:** 2026-08-28 — **Severity:** High
> **Part of:** [[Bugs]]

# The human check was rendered where no human could reach it

## Symptom

Asking for the verification code logged, in the visitor's console:

    [Cloudflare Turnstile] Cannot find Widget cf-chl-widget-saifb,
    consider using turnstile.remove() to clean up a widget.

Most visits carried on regardless, which is why this survived a live run: with
`appearance: 'interaction-only'`, Turnstile usually decides silently and calls back
without ever drawing anything. The visitor sees nothing and notices nothing.

The failure only appears for the visitors Cloudflare *is* suspicious of — the exact
population the gate exists for. For them the challenge is drawn into a node that is
not in the page, so it cannot be seen, clicked or solved, and the flow stops at the
one step that has no alternative route.

## Root Cause

`ContactConversation.vue` passed a container it created and never mounted:

    const token = await turnstile.getToken(document.createElement('div'))

Turnstile renders into whatever element it is handed. Handed an orphan, it builds the
widget, loses track of it, and says so. `createTurnstileClient` also discarded the
`widgetId` that `render()` returns and never called `remove()`, so each retry stacked
another orphaned widget in the same place.

Why it was never caught: **`turnstile-client.ts` had no test file at all.** It was
written behind a port precisely so it could be tested without loading a third-party
script, and then no test was written. The component tests injected a stub whose
`getToken` resolved a fixed string, so nothing on either side of the port ever asserted
what was handed across it.

## Fix

The component owns a permanent `<div ref="turnstileHost">` outside the `v-if`/`v-else`
of the composer, so the host exists whenever a challenge can be asked for and is visible
when Cloudflare draws in it. `getToken` keeps the widget id and destroys the widget once
the challenge settles.

A second defect surfaced while fixing the first, and it is the one worth remembering.
The initial version removed the widget **inside** Cloudflare's callback:

    callback: (token) => { teardown(); resolve(token) }

Removing a widget from within its own callback throws, and the exception aborts the
callback before it ever resolves. The promise never settled, `requestCode` was never
called, and the code field never appeared. Two e2e caught it, reproducibly. No unit
test could: the stub does not raise what Cloudflare raises.

The teardown now runs **after** the promise settles, deferred, inside `try/catch`:
cleaning up is not allowed to fail a challenge the visitor already passed.

Shipped in commit `361da4e` (PR #39).

## Affected Files

- `src/utils/turnstile-client.ts` — `remove()` on the global, widget id kept, deferred teardown
- `src/utils/turnstile-client.test.ts` — **new**; the module had no tests
- `src/components/contact/ContactConversation.vue` — the mounted host, and the CSS that keeps
  it out of the layout while empty
- `src/components/contact/ContactConversation.test.ts` — the container reaching `getToken`
  must satisfy `isConnected`

## Prevention

- **A port written for testability that has no tests is worse than no port.** The
  indirection made the defect invisible from both sides: the component test asserted
  against a stub, and nothing asserted against the real adapter. The seam is where the
  test goes, not a substitute for one.
- **A stub cannot fail the way the real dependency fails.** The callback-throws defect
  was unreachable by any test built on a stub that never throws. Where a third party
  runs our code inside its own, an end-to-end check is not redundancy — it is the only
  observer.
- **Cleanup never belongs on the path to settling a promise.** Resolve first, tidy after.
  A teardown that can throw, placed before the resolve, converts a successful operation
  into one that hangs with no error anywhere.
- **A control that degrades only for suspicious visitors degrades invisibly.** Same shape
  as [[turnstile-test-key-in-production]]: the anti-abuse path is the one where "it worked
  when I tried it" proves the least, because the gate deliberately treats us differently
  from the traffic it is built to stop.

## References

- [[Bugs]] — parent index
- [[turnstile-test-key-in-production]] — the other half of this gate, and the same blind spot
- [[0009-conversational-contact-agent]] — the flow this step belongs to
- [[testing-strategy]] — where the unit/e2e boundary is meant to fall
