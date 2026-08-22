// Loads the Cloudflare Turnstile widget and resolves a challenge token.
//
// Kept behind a port so the chat component can be tested without loading a
// third-party script, and so a missing site key degrades predictably instead of
// throwing inside a render.

const SCRIPT_URL = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
const SCRIPT_ID = 'cf-turnstile-script'

export class TurnstileNotConfigured extends Error {
  constructor() {
    super('PUBLIC_TURNSTILE_SITE_KEY is not configured')
    this.name = 'TurnstileNotConfigured'
  }
}

export interface TurnstileClient {
  /** Resolves a challenge token, or throws if the challenge cannot be completed. */
  getToken(container: HTMLElement): Promise<string>
}

interface TurnstileGlobal {
  render(
    container: HTMLElement,
    options: {
      sitekey: string
      callback: (token: string) => void
      'error-callback': () => void
      appearance?: string
    },
  ): string
}

declare global {
  interface Window {
    turnstile?: TurnstileGlobal
  }
}

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.turnstile) return resolve()

    const existing = document.getElementById(SCRIPT_ID)
    if (existing) {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('Turnstile failed to load')))
      return
    }

    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = SCRIPT_URL
    script.async = true
    script.defer = true
    script.addEventListener('load', () => resolve())
    script.addEventListener('error', () => reject(new Error('Turnstile failed to load')))
    document.head.appendChild(script)
  })
}

export function createTurnstileClient(siteKey: string): TurnstileClient {
  return {
    async getToken(container: HTMLElement): Promise<string> {
      if (!siteKey) {
        // Not the visitor's fault: the deployment is missing a key.
        throw new TurnstileNotConfigured()
      }

      await loadScript()

      if (!window.turnstile) {
        throw new Error('Turnstile did not initialise')
      }

      return new Promise<string>((resolve, reject) => {
        window.turnstile!.render(container, {
          sitekey: siteKey,
          appearance: 'interaction-only',
          callback: (token: string) => resolve(token),
          'error-callback': () => reject(new Error('Turnstile challenge failed')),
        })
      })
    },
  }
}
