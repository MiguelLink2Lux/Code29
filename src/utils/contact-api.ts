// Transport to the FastAPI backend for the guided contact flow.
//
// The backend lives on its own Vercel project, so every call is cross-origin and
// `CORS_ORIGINS` there must name this site's origin. `fetch` is injected so the
// component and the tests never touch the network.
//
// SOLID: components depend on this abstraction, never on `fetch` directly.


const DEFAULT_BASE_URL = 'http://localhost:8000'

export interface ContactApiEnv {
  PUBLIC_API_BASE_URL?: string
}

export class ContactApiError extends Error {
  constructor(
    message: string,
    /** HTTP status, or 0 when the request never got an answer. */
    public readonly status: number,
  ) {
    super(message)
    this.name = 'ContactApiError'
  }
}

export function resolveApiBaseUrl(env: ContactApiEnv = import.meta.env as ContactApiEnv): string {
  const configured = env.PUBLIC_API_BASE_URL?.trim()

  if (!configured) return DEFAULT_BASE_URL

  if (!/^https?:\/\//i.test(configured)) {
    throw new Error(
      `PUBLIC_API_BASE_URL must be an absolute URL including the scheme, got: ${configured}`,
    )
  }

  return configured.replace(/\/+$/, '')
}

interface ContactApiOptions {
  baseUrl?: string
  fetchImpl?: typeof fetch
}

export function createContactApi(options: ContactApiOptions = {}) {
  const baseUrl = options.baseUrl ?? resolveApiBaseUrl()
  const fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis)

  async function post(path: string, body: unknown, token?: string): Promise<unknown> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }

    // The token is a credential: it belongs in the header, not the payload.
    if (token) headers.Authorization = `Bearer ${token}`

    let response: Response

    try {
      response = await fetchImpl(`${baseUrl}${path}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      })
    } catch (error) {
      // A dead backend, CORS refusal or offline client all land here as a
      // TypeError; callers need one error type to reason about.
      throw new ContactApiError(
        error instanceof Error ? error.message : 'Network request failed',
        0,
      )
    }

    let payload: unknown = null

    try {
      payload = await response.json()
    } catch {
      payload = null
    }

    if (!response.ok) {
      const detail =
        payload && typeof payload === 'object' && 'detail' in payload
          ? String((payload as { detail: unknown }).detail)
          : `Request failed with status ${response.status}`

      throw new ContactApiError(detail, response.status)
    }

    return payload
  }

  return {
    async requestVerificationCode(email: string, turnstileToken: string): Promise<void> {
      await post('/api/v1/contact/verification/request', { email, turnstileToken })
    },

    async confirmVerificationCode(email: string, code: string): Promise<string> {
      const payload = await post('/api/v1/contact/verification/confirm', { email, code })
      const token =
        payload && typeof payload === 'object' && 'accessToken' in payload
          ? String((payload as { accessToken: unknown }).accessToken)
          : ''

      if (!token) {
        throw new ContactApiError('The backend confirmed without returning a token', 502)
      }

      return token
    },

    /**
     * Asks the backend to generate and email the report.
     *
     * Only the envelope travels: the facts live inside its signature, so a
     * client cannot put someone else's company into a report we sign. Consent
     * is explicit here because the backend refuses without it.
     */
    async requestConversationReport(envelope: string, accessToken: string): Promise<void> {
      await post(
        '/api/v1/contact/report',
        {
          envelope,
          locale: 'es',
          consent: { privacy_accepted: true, report_accepted: true },
        },
        accessToken,
      )
    },

    /**
     * Advance the conversation by one turn.
     *
     * The envelope is the whole server-side state: it comes back signed and must
     * be returned as-is on the next turn. The access token is a credential and
     * travels in the header — it is what makes the conversation completable.
     */
    async takeConversationTurn(
      message: string,
      envelope?: string,
      accessToken?: string,
      lang: string = 'es',
    ): Promise<ConversationTurn> {
      const body: { message: string; envelope?: string; lang: string } = { message, lang }

      // Omitted rather than sent as null on the first turn: the backend treats
      // an absent envelope as "start a conversation".
      if (envelope) body.envelope = envelope

      const payload = await post('/api/v1/contact/conversation/turn', body, accessToken)

      return parseTurn(payload)
    },
  }
}

/**
 * What the server says comes next. The client renders this; it never computes
 * it — the script order is the server's, and splitting it across layers is what
 * made the chat ask for the email address last.
 */
export const NEXT_STEPS = ['message', 'email', 'code', 'closing', 'blocked'] as const

export type NextStep = (typeof NEXT_STEPS)[number]

export interface ConversationTurn {
  reply: string
  envelope: string
  complete: boolean
  exhausted: boolean
  missing: string[]
  nextStep: NextStep
  blocked: boolean
}

/** A turn without an envelope cannot be continued, so it is refused outright. */
function parseTurn(payload: unknown): ConversationTurn {
  if (!payload || typeof payload !== 'object') {
    throw new ContactApiError('The backend returned no turn', 502)
  }

  const turn = payload as Record<string, unknown>

  if (typeof turn.envelope !== 'string' || !turn.envelope) {
    throw new ContactApiError('The backend answered without a conversation envelope', 502)
  }

  return {
    reply: typeof turn.reply === 'string' ? turn.reply : '',
    envelope: turn.envelope,
    complete: turn.complete === true,
    exhausted: turn.exhausted === true,
    missing: Array.isArray(turn.missing) ? turn.missing.map(String) : [],
    // Defaulted, not required. The frontend and the backend are separate Vercel
    // projects and do not deploy at the same instant: for the length of that
    // window a new client talks to a backend that has never heard of these
    // fields, and the chat must degrade to its previous behaviour rather than
    // break on a missing key. An unrecognised value is treated the same way —
    // the response is data from the network, not an instruction to obey.
    nextStep: NEXT_STEPS.includes(turn.next_step as NextStep)
      ? (turn.next_step as NextStep)
      : 'message',
    blocked: turn.blocked === true,
  }
}

export type ContactApi = ReturnType<typeof createContactApi>
