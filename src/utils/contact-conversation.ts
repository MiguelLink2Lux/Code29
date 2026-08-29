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

/** A verification code as the backend issues it: six digits, nothing else. */
const BARE_CODE = /^\d{6}$/

export interface Answer {
  kind: 'email' | 'code' | 'message'
  value: string
}

/**
 * What the visitor's reply actually is.
 *
 * There is one composer for the whole conversation — verification is not a step
 * the visitor is put through, it is something that happens while they talk — so
 * the reply has to be read rather than routed by whichever field was on screen.
 *
 * A six-digit number is only a code when a verification is **pending** and the
 * reply is **nothing but** those digits. Both halves matter: "somos 6 en el
 * equipo", "facturamos 384012 euros" and "en 2024" are things people say, and
 * swallowing one as a verification code would lose an answer and burn a code.
 *
 * An address wins over digits when a reply carries both: verifying is what
 * unblocks the report, and the code can be given again.
 */
export function readAnswer(
  text: string,
  { pendingEmail }: { pendingEmail: string | null },
): Answer {
  const trimmed = text.trim()
  const address = extractEmail(trimmed)

  if (address) return { kind: 'email', value: address }

  if (pendingEmail && BARE_CODE.test(trimmed)) return { kind: 'code', value: trimmed }

  return { kind: 'message', value: trimmed }
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
   * The conversation is over and the composer should go.
   *
   * NOT the same as `complete`. Since this cycle `complete` means "enough facts
   * to write the report", and the bot answers that by announcing the report and
   * inviting one last thing — so the chat outlives completeness by exactly one
   * message. It closes when that message is in, when the guard blocked it, or
   * when the turn budget ran out.
   */
  closed: boolean
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
  nextStep?: NextStep
  closingAnswered?: boolean
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
   * What the bot says when verification does not go through.
   *
   * Injected rather than imported: this module is framework-free and holds no
   * copy. It matters that these are *messages* and not error codes — a form
   * raises an alert under the field, a conversation says something and carries
   * on, and the difference is the whole point of this cycle.
   */
  botCopy?: { codeRejected: string[]; humanCheck: string[] }
  /**
   * The language the visitor is being spoken to in, travelling with every turn.
   *
   * Accepts a getter as well as a value, and the getter is the point: a value
   * is captured when the conversation is created, so a visitor who switches the
   * site to Spanish mid-conversation kept being answered in English. The
   * language is a property of the moment a turn is sent, not of the moment the
   * chat was built.
   */
  lang?: string | (() => string)
}

export function createConversation({
  api,
  openings = [],
  pickOpening = (count) => Math.floor(Math.random() * count),
  lang = 'es',
  botCopy = { codeRejected: [], humanCheck: [] },
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
  // Whether the closing invitation has already been answered. Persisted, or a
  // reload would re-open a conversation that had ended.
  let closingAnswered = restored?.closingAnswered ?? false
  let nextStep: NextStep = restored?.nextStep ?? (blocked ? 'blocked' : 'message')
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
      nextStep,
      closingAnswered,
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

  /**
   * Says a verification failure in the bot's voice instead of raising it.
   *
   * Ephemeral like the rest of the verification exchange: it is part of a
   * conversation about an address, and the address is not written down.
   */
  function say(pool: string[]): boolean {
    if (!pool.length) return false

    pushEphemeral('bot', pool[variantSeed % pool.length])

    return true
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
    get closed() {
      return blocked || exhausted || (nextStep === 'closing' && closingAnswered)
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

    // Held back while the bot is still waiting for one last thing. Sending the
    // report on sufficiency would make the invitation a lie: whatever they add
    // would arrive after the report it was meant to improve.
    if (nextStep === 'closing' && !closingAnswered) return

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

    // Whatever they send while the bot is waiting for "anything else" IS the
    // answer to that invitation. Recorded before the turn, so the state is
    // right even if the turn fails.
    if (nextStep === 'closing') closingAnswered = true

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
    // Persisted before the request, not after it. Waiting for the answer meant
    // a reload while the turn was in flight threw away what the visitor had
    // just written — their words are theirs the moment they send them.
    persist()
    busy = true
    error = null

    try {
      const turn = await api.takeConversationTurn(
        message,
        envelope,
        accessToken ?? undefined,
        typeof lang === 'function' ? lang() : lang,
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
      // email is wrong would send them in circles. Spoken rather than raised —
      // a transport failure still becomes an error, because a bot cannot
      // explain a dead network away in character.
      const humanCheckFailed = failure instanceof ContactApiError && failure.status === 403

      if (humanCheckFailed && say(botCopy.humanCheck)) {
        error = null
      } else {
        // With no copy to say it with, the typed code is still better than a
        // generic failure: `describe` has no mapping for 403 and would flatten
        // a human check into "something went wrong".
        error = humanCheckFailed ? 'humanCheck' : describe(failure)
      }
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
      // A wrong code is the one failure the visitor can fix by answering again,
      // so it stays in the conversation and `pendingEmail` is kept: the next
      // six digits are still read as a code.
      const codeRejected = failure instanceof ContactApiError && failure.status === 400

      if (codeRejected && say(botCopy.codeRejected)) {
        error = null
      } else {
        error = codeRejected ? 'codeRejected' : describe(failure)
      }
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
    closingAnswered = false
    nextStep = 'message'
    error = null
    accessToken = null
    pendingEmail = null
    clearPersisted()
  }

  return { state, send, requestCode, confirmCode, deliverReport, pushEphemeral, reset }
}

export type Conversation = ReturnType<typeof createConversation>
