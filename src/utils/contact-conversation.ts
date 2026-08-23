// State of the guided conversation, framework-free so it can be unit-tested
// without mounting a component. ContactConversation.vue is a thin renderer over
// this, exactly as the questionnaire's machine was.
//
// Three rules are enforced here rather than trusted to the component:
//
//  - the transcript lives in sessionStorage, so lead data dies with the tab;
//  - the access token is NEVER persisted and never leaves memory — it proves
//    email ownership, and the address it stands for is not written down either;
//  - the server decides `complete`. This module only reports what it was told,
//    because a client that decides it is finished is a client that can skip
//    verification.

import { ContactApiError, type ContactApi } from '@/utils/contact-api'

const STORAGE_KEY = 'contact-conversation'

/** Mirrors MAX_MESSAGE_CHARS in backend/app/services/conversation.py. */
export const MAX_MESSAGE_LENGTH = 1000

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i

export type MessageRole = 'visitor' | 'bot'

export interface ConversationMessage {
  role: MessageRole
  text: string
}

/**
 * Error codes, not sentences: the copy lives in translations.ts so the same
 * state can be rendered in either language.
 */
export type ConversationError =
  | 'empty'
  | 'tooLong'
  | 'expired'
  | 'retry'
  | 'unavailable'
  | 'network'
  | 'invalidEmail'
  | 'codeRejected'
  | 'humanCheck'
  | 'generic'

export interface ConversationState {
  messages: ConversationMessage[]
  envelope?: string
  complete: boolean
  exhausted: boolean
  missing: string[]
  busy: boolean
  error: ConversationError | null
  pendingEmail: string | null
  emailVerified: boolean
}

interface PersistedShape {
  messages: ConversationMessage[]
  envelope?: string
  complete: boolean
  exhausted: boolean
  missing: string[]
}

function readPersisted(): PersistedShape | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null

    const parsed = JSON.parse(raw) as PersistedShape

    return Array.isArray(parsed?.messages) ? parsed : null
  } catch {
    // Corrupted payload, private mode, or storage denied: start clean rather
    // than take the island down.
    return null
  }
}

function writePersisted(payload: PersistedShape): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    // Persistence is a convenience, never a requirement.
  }
}

function clearPersisted(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

/** Maps a transport failure to something the visitor can act on. */
function describe(error: unknown): ConversationError {
  if (error instanceof ContactApiError) {
    if (error.status === 401) return 'expired'
    if (error.status === 413) return 'tooLong'
    if (error.status === 502) return 'retry'
    if (error.status === 503) return 'unavailable'
    if (error.status === 0) return 'network'
  }

  return 'generic'
}

interface ConversationOptions {
  api: ContactApi
}

export function createConversation({ api }: ConversationOptions) {
  const restored = readPersisted()

  const messages: ConversationMessage[] = restored?.messages ?? []
  let envelope = restored?.envelope
  let complete = restored?.complete ?? false
  let exhausted = restored?.exhausted ?? false
  let missing = restored?.missing ?? []
  let busy = false
  let error: ConversationError | null = null

  // In memory only, both of them: the token is a credential and the address is
  // personal data. Neither is written to storage.
  let accessToken: string | null = null
  let pendingEmail: string | null = null
  //: True only once the backend confirms the report was generated and emailed.
  let delivered = false

  const persist = () =>
    writePersisted({ messages, envelope, complete, exhausted, missing })

  const state: ConversationState = {
    get messages() {
      return [...messages]
    },
    get envelope() {
      return envelope
    },
    get complete() {
      return complete
    },
    get exhausted() {
      return exhausted
    },
    get missing() {
      return [...missing]
    },
    get busy() {
      return busy
    },
    get error() {
      return error
    },
    get pendingEmail() {
      return pendingEmail
    },
    get emailVerified() {
      return accessToken !== null
    },
    get delivered() {
      return delivered
    },
  }

  /**
   * Asks the backend for the report. Without this the whole conversation
   * gathers facts and delivers nothing, which is worse than the questionnaire
   * it replaces.
   *
   * Only the envelope and the token travel: the facts live inside the
   * envelope's signature, so the client cannot claim someone else's company.
   */
  async function deliverReport(): Promise<void> {
    if (busy || delivered) return

    // The server decides completeness. Asking earlier would be asking for a
    // report about facts it has not accepted.
    if (!complete || !envelope || !accessToken) return

    busy = true
    error = null

    try {
      await api.requestConversationReport(envelope, accessToken)
      delivered = true
    } catch (failure) {
      // Never mark it delivered on failure: telling a visitor their report is
      // on the way when it is not is the one outcome with no recovery.
      error = describe(failure)
      delivered = false
    } finally {
      busy = false
      persist()
    }
  }

  async function send(text: string): Promise<void> {
    // One turn at a time: a double submit would spend two turns of the budget
    // and interleave two replies.
    if (busy) return

    const message = text.trim()

    if (!message) {
      error = 'empty'
      return
    }

    if (message.length > MAX_MESSAGE_LENGTH) {
      // Refused locally: the backend would answer 413, but spending a request to
      // learn what we already know is a wasted round trip.
      error = 'tooLong'
      return
    }

    messages.push({ role: 'visitor', text: message })
    busy = true
    error = null

    try {
      const turn = await api.takeConversationTurn(message, envelope, accessToken ?? undefined)

      messages.push({ role: 'bot', text: turn.reply })
      envelope = turn.envelope
      complete = turn.complete
      exhausted = turn.exhausted
      missing = turn.missing
      persist()
    } catch (failure) {
      error = describe(failure)

      // An expired conversation cannot be continued: drop the envelope so the
      // next message starts a fresh one instead of failing forever. The
      // visitor's own message stays on screen.
      if (error === 'expired') {
        envelope = undefined
        persist()
      }
    } finally {
      busy = false
    }
  }

  async function requestCode(email: string, turnstileToken: string): Promise<void> {
    const address = email.trim().toLowerCase()

    if (!EMAIL_REGEX.test(address)) {
      error = 'invalidEmail'
      return
    }

    busy = true
    error = null

    try {
      await api.requestVerificationCode(address, turnstileToken)
      pendingEmail = address
    } catch (failure) {
      // 403 is the human check, not a bad address: telling the visitor their
      // email is wrong would send them in circles.
      error = failure instanceof ContactApiError && failure.status === 403
        ? 'humanCheck'
        : describe(failure)
    } finally {
      busy = false
    }
  }

  async function confirmCode(code: string): Promise<void> {
    if (!pendingEmail) {
      error = 'invalidEmail'
      return
    }

    busy = true
    error = null

    try {
      accessToken = await api.confirmVerificationCode(pendingEmail, code)
      missing = missing.filter((item) => item !== 'email')
      persist()
    } catch (failure) {
      error =
        failure instanceof ContactApiError && failure.status === 400
          ? 'codeRejected'
          : describe(failure)
    } finally {
      busy = false
    }
  }

  function reset(): void {
    messages.length = 0
    envelope = undefined
    complete = false
    exhausted = false
    missing = []
    error = null
    accessToken = null
    pendingEmail = null
    clearPersisted()
  }

  return { state, send, requestCode, confirmCode, deliverReport, reset }
}

export type Conversation = ReturnType<typeof createConversation>
