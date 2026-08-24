// Transport to the FastAPI backend for the guided contact flow.
//
// The backend lives on its own Vercel project, so every call is cross-origin and
// `CORS_ORIGINS` there must name this site's origin. `fetch` is injected so the
// component and the tests never touch the network.
//
// SOLID: components depend on this abstraction, never on `fetch` directly.

import type { ReportRequest } from '@/utils/contact-chat'

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

    async requestReport(request: ReportRequest, accessToken: string): Promise<void> {
      await post('/api/v1/contact/report', request, accessToken)
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
    ): Promise<ConversationTurn> {
      const body: { message: string; envelope?: string } = { message }

      // Omitted rather than sent as null on the first turn: the backend treats
      // an absent envelope as "start a conversation".
      if (envelope) body.envelope = envelope

      const payload = await post('/api/v1/contact/conversation/turn', body, accessToken)

      return parseTurn(payload)
    },
  }
}

export interface ConversationTurn {
  reply: string
  envelope: string
  complete: boolean
  exhausted: boolean
  missing: string[]
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
  }
}

export type ContactApi = ReturnType<typeof createContactApi>
