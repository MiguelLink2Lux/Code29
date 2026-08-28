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
  /** Destroys a widget by the id `render` returned. */
  remove(widgetId: string): void
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
        // Cloudflare tracks widgets by the id `render` returns, and a challenge
        // is one-shot: without tearing it down, a visitor who retries stacks a
        // second widget into the same container and the first is orphaned.
        // Held in an object rather than a plain binding: the callbacks close
        // over it before `render` has returned the id, and a challenge that
        // resolves synchronously would otherwise read it before it exists.
        const widget: { id?: string } = {}

        // Deferred, and never on the path to settling the promise: Turnstile
        // invokes these callbacks from inside its own widget, and removing the
        // widget there throws — which would abort the callback before it ever
        // resolved. The settle happens first, the cleanup afterwards, and a
        // failure to clean up is not allowed to fail the challenge.
        const teardown = () => {
          setTimeout(() => {
            try {
              if (widget.id !== undefined) window.turnstile?.remove(widget.id)
            } catch {
              /* The widget is already gone, or Turnstile refused. Nothing to do. */
            }
          }, 0)
        }

        widget.id = window.turnstile!.render(container, {
          sitekey: siteKey,
          appearance: 'interaction-only',
          callback: (token: string) => {
            resolve(token)
            teardown()
          },
          'error-callback': () => {
            reject(new Error('Turnstile challenge failed'))
            teardown()
          },
        })
      })
    },
  }
}
