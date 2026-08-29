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

import { ContactApiError, type ContactApi, type NextStep } from '@/utils/contact-api'

const STORAGE_KEY = 'contact-conversation'

/** Mirrors MAX_MESSAGE_CHARS in backend/app/services/conversation.py. */
export const MAX_MESSAGE_LENGTH = 1000

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i

/**
 * The same address shape, but looked for *inside* a sentence rather than matched
 * against a whole field. Deliberately stricter than the RFC — a local part, an
 * @, a domain with a dot and a TLD of two or more letters — so "link2lux.vip"
 * stays a website and does not become an address nobody typed.
 */
const EMAIL_IN_TEXT = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/

/**
 * The first address in a free-text message, lowercased, or null.
 *
 * Visitors answer "where should I send it?" the way people answer questions —
 * inside a sentence, not into a field. The backend cannot help here: it redacts
 * every address before anything else happens (ADR 0007) and must never hand one
 * back, so the address has to be recognised on this side or lost. It was lost.
 */
export function extractEmail(message: string): string | null {
  const found = message.match(EMAIL_IN_TEXT)

  return found ? found[0].toLowerCase() : null
}

export type MessageRole = 'visitor' | 'bot'

export interface ConversationMessage {
  role: MessageRole
  text: string
  /**
   * Shown in the thread, never written to storage.
   *
   * The verification exchange reads as part of the conversation — the visitor
   * types their address into the same composer as everything else — but the
   * address is personal data and the code is a credential. Marking the message
   * is what keeps them out of `sessionStorage`; filtering by content would let
   * through anything written in an unexpected shape.
   */
  ephemeral?: boolean
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
  /** What the server said to ask for next. Never computed here. */
  nextStep: NextStep
  /** The conversation was ended by the injection guard. */
  blocked: boolean
  /**
   * Picks the variant of every rotating message, once per conversation.
   *
   * One seed rather than a stored pick per pool: the verification messages are
   * ephemeral by design — they carry personal data and must not be persisted —
   * so they are re-rendered from scratch on every reload. Without a seed that
   * outlives them, their wording would change and the visitor would be talking
   * to a different bot after pressing F5.
   */
  variantSeed: number
}

interface PersistedShape {
  messages: ConversationMessage[]
  envelope?: string
  complete: boolean
  exhausted: boolean
  missing: string[]
  blocked?: boolean
  variantSeed?: number
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
  /**
   * Greetings to open with, one picked per conversation. They rotate so the
   * chat does not read as a recording, and the chosen one is persisted with the
   * thread: a greeting that changes on reload reads as a different bot.
   */
  openings?: string[]
  /** Index picker, injectable so tests are deterministic. */
  pickOpening?: (count: number) => number
  /**
   * The language the visitor is being spoken to in. Travels with every turn so
   * the model answers in it: the opening was already chosen from `html[lang]`
   * while the replies were hardcoded Spanish, which is how an English visitor
   * ended up being greeted in one language and answered in another.
   */
  lang?: string
}

export function createConversation({
  api,
  openings = [],
  pickOpening = (count) => Math.floor(Math.random() * count),
  lang = 'es',
}: ConversationOptions) {
  const restored = readPersisted()

  const messages: ConversationMessage[] = restored?.messages ?? []

  // Only on a fresh conversation: the bot speaks first, so the visitor answers
  // rather than facing an empty box and having to work out what to write.
  if (!messages.length && openings.length) {
    const index = Math.min(Math.max(pickOpening(openings.length), 0), openings.length - 1)
    messages.push({ role: 'bot', text: openings[index] })
  }
  let envelope = restored?.envelope
  let complete = restored?.complete ?? false
  let exhausted = restored?.exhausted ?? false
  let missing = restored?.missing ?? []
  let blocked = restored?.blocked ?? false
  let nextStep: NextStep = blocked ? 'blocked' : 'message'
  const variantSeed = restored?.variantSeed ?? Math.floor(Math.random() * 1_000_000)
  let busy = false
  let error: ConversationError | null = null

  // In memory only, both of them: the token is a credential and the address is
  // personal data. Neither is written to storage.
  let accessToken: string | null = null
  let pendingEmail: string | null = null
  //: True only once the backend confirms the report was generated and emailed.
  let delivered = false

  const persist = () =>
    writePersisted({
      // The single place the rule is applied, so no caller can forget it.
      messages: messages.filter((message) => !message.ephemeral),
      envelope,
      complete,
      exhausted,
      missing,
      blocked,
      variantSeed,
    })

  // Written at construction, not only after the first turn: the seed has to
  // outlive a reload that happens before the visitor has said anything, and the
  // opening message is already chosen by then.
  persist()

  /** Adds a message to the thread that must never survive a reload. */
  function pushEphemeral(role: MessageRole, text: string): void {
    messages.push({ role, text, ephemeral: true })
  }

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
    get nextStep() {
      return nextStep
    },
    get blocked() {
      return blocked
    },
    get variantSeed() {
      return variantSeed
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
    if (busy || delivered || blocked) return

    // Not `complete`: that flag was computed by the server on the previous turn,
    // before the token existed, so verifying the address last would leave it
    // false for ever and the report would never be asked for. `missing` is the
    // server's own answer about what it still needs, and confirmCode removes
    // 'email' from it — so an empty list plus a token means deliverable.
    if (!envelope || !accessToken || missing.length > 0) return

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

    // The conversation is over. The real refusal is the server's — the flag is
    // sealed inside the envelope's signature — so this only spares a request we
    // already know ends in 403.
    if (blocked) return

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
      const turn = await api.takeConversationTurn(
        message,
        envelope,
        accessToken ?? undefined,
        lang,
      )

      messages.push({ role: 'bot', text: turn.reply })
      envelope = turn.envelope
      complete = turn.complete
      exhausted = turn.exhausted
      missing = turn.missing
      nextStep = turn.nextStep
      blocked = turn.blocked
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
      // In the thread, because the visitor typed it into the conversation —
      // but ephemeral, because it is the one piece of personal data here.
      pushEphemeral('visitor', address)
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
      pushEphemeral('visitor', code.trim())
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
    blocked = false
    nextStep = 'message'
    error = null
    accessToken = null
    pendingEmail = null
    clearPersisted()
  }

  return { state, send, requestCode, confirmCode, deliverReport, pushEphemeral, reset }
}

export type Conversation = ReturnType<typeof createConversation>
