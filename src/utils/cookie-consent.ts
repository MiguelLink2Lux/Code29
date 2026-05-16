// Cookie consent service — stores and retrieves consent state from localStorage.
// Isolated from analytics: callers react to returned state, no GA4 dependency here.

export interface ConsentState {
  necessary: true
  analytics: boolean
  marketing: boolean
}

const STORAGE_KEY = 'cookie-consent'

export function createDefaultConsentState(): ConsentState {
  return {
    necessary: true,
    analytics: false,
    marketing: false,
  }
}

function safeRead(): ConsentState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as ConsentState
  } catch (error) {
    console.warn('Cookie consent storage is unavailable for reads.', error)
    return null
  }
}

function safeWrite(state: ConsentState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch (error) {
    console.warn('Cookie consent storage is unavailable for writes.', error)
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
    const state = createDefaultConsentState()
    safeWrite(state)
    return state
  },

  /** Persists a custom set of cookie preferences. */
  save(state: ConsentState): ConsentState {
    const normalizedState: ConsentState = {
      necessary: true,
      analytics: state.analytics,
      marketing: state.marketing,
    }
    safeWrite(normalizedState)
    return normalizedState
  },

  /** Returns the default deny-all optional consent state. */
  defaults(): ConsentState {
    return createDefaultConsentState()
  },

  /** Clears the persisted consent state. Useful in tests only. */
  clear(): void {
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (error) {
      console.warn('Cookie consent storage is unavailable for clearing.', error)
    }
  },

  /** Returns true only when the user has already made a decision. */
  hasDecided(): boolean {
    return safeRead() !== null
  },
}
