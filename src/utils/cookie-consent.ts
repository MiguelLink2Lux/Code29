// Cookie consent service — stores and retrieves consent state from localStorage.
// Isolated from analytics: callers react to returned state, no GA4 dependency here.

export interface ConsentState {
  necessary: true
  analytics: boolean
  marketing: boolean
}

const STORAGE_KEY = 'cookie-consent'

const defaults: ConsentState = {
  necessary: true,
  analytics: false,
  marketing: false,
}

function safeRead(): ConsentState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as ConsentState
  } catch {
    return null
  }
}

function safeWrite(state: ConsentState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // localStorage unavailable (e.g. private mode with storage blocked) — silently skip
  }
}

export const ConsentService = {
  /** Returns stored consent or null if user has not decided yet. */
  get(): ConsentState | null {
    return safeRead()
  },

  /** Persists full consent (necessary + analytics + marketing). */
  acceptAll(): ConsentState {
    const state: ConsentState = { necessary: true, analytics: true, marketing: true }
    safeWrite(state)
    return state
  },

  /** Persists minimal consent (necessary only). */
  rejectAll(): ConsentState {
    const state: ConsentState = { ...defaults }
    safeWrite(state)
    return state
  },

  /** Returns true only when the user has already made a decision. */
  hasDecided(): boolean {
    return safeRead() !== null
  },
}
