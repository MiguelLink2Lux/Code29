/**
 * Reads one conversation turn the way the deployment verifier needs it: did a
 * model answer, did the stub answer, or did the model fail?
 *
 * Pure on purpose, so each case is testable without a deployment. The status is
 * read first: a 502 body carries no `missing` list, and reading it as one used
 * to report a failing model as "the stub is answering" (COD-69).
 *
 * @param {number | undefined} status HTTP status, or undefined if the request never got an answer.
 * @param {unknown} body The parsed JSON body, or null.
 * @returns {{ ok: boolean, blocking: boolean, detail: string }}
 */
export function conversationCheck(status, body) {
  if (status === undefined) {
    return { ok: false, blocking: true, detail: 'the turn endpoint did not answer' }
  }

  if (status < 200 || status >= 300) {
    return {
      ok: false,
      blocking: true,
      detail: `the model failed (HTTP ${status}) — check the backend logs for the provider's reason`,
    }
  }

  // The stub cannot read a name out of a sentence, so it still reports
  // contact_name as missing — which is what a deployment with no working
  // GEMINI_API_KEY looks like. Not blocking: the key is the owner's to set.
  const missing = Array.isArray(body?.missing) ? body.missing : null
  if (missing && !missing.includes('contact_name')) {
    return { ok: true, blocking: true, detail: 'the name was extracted from a sentence' }
  }

  return {
    ok: false,
    blocking: false,
    detail: 'no model configured — the stub is answering; GEMINI_API_KEY is missing or rejected',
  }
}
