// GA4 abstraction — Consent Mode v2, with the tag loaded only after consent.
// All callers depend on this interface, never on window.gtag directly (DIP).
//
// Why the tag is not loaded up front: with Consent Mode set to "denied", GA4
// still sends a cookieless ping carrying the IP, the URL and the user agent
// before the visitor has decided anything. That is data leaving the browser
// without a legal basis, and it contradicts the banner we show. So the tag is
// injected at the moment analytics is granted, and never before.

import { ConsentService } from '@/utils/cookie-consent'
import type { ConsentState } from '@/utils/cookie-consent'

declare global {
  interface Window {
    dataLayer: unknown[]
    gtag: (...args: unknown[]) => void
  }
}

const DENIED = {
  analytics_storage: 'denied',
  ad_storage: 'denied',
  ad_user_data: 'denied',
  ad_personalization: 'denied',
} as const

let measurementId = ''
let tagLoaded = false

function gtag(...args: unknown[]): void {
  if (typeof window === 'undefined' || typeof window.gtag !== 'function') return
  window.gtag(...args)
}

/** Injects the Google tag. Idempotent: repeated grants must not stack scripts. */
function loadTag(): void {
  if (tagLoaded || !measurementId || typeof document === 'undefined') return

  const script = document.createElement('script')
  script.async = true
  script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`
  script.dataset.ga4 = measurementId
  document.head.appendChild(script)

  gtag('js', new Date())
  gtag('config', measurementId)

  tagLoaded = true
}

export const AnalyticsService = {
  /**
   * Prepares the dataLayer and declares consent denied, then loads the tag only
   * if the visitor had already granted analytics on a previous visit.
   */
  bootstrap(id: string): void {
    if (typeof window === 'undefined') return

    measurementId = id
    window.dataLayer = window.dataLayer || []

    if (typeof window.gtag !== 'function') {
      window.gtag = function gtagShim(...args: unknown[]) {
        // eslint-disable-next-line prefer-rest-params
        window.dataLayer.push(arguments.length === 1 ? args[0] : Array.from(arguments))
      } as Window['gtag']
    }

    // Declared before anything can load, so a later grant is an update and not
    // an unconsented default.
    gtag('consent', 'default', { ...DENIED, wait_for_update: 500 })

    this.restoreConsent()
  },

  grantConsent(): void {
    this.applyConsent({ necessary: true, analytics: true, marketing: true })
  },

  denyConsent(): void {
    this.applyConsent({ necessary: true, analytics: false, marketing: false })
  },

  applyConsent(state: ConsentState): void {
    gtag('consent', 'update', {
      analytics_storage: state.analytics ? 'granted' : 'denied',
      ad_storage: state.marketing ? 'granted' : 'denied',
      ad_user_data: state.marketing ? 'granted' : 'denied',
      ad_personalization: state.marketing ? 'granted' : 'denied',
    })

    if (state.analytics) loadTag()
  },

  /** Reads stored consent and applies it — call on page load for returning visitors. */
  restoreConsent(): void {
    const state = ConsentService.get()
    if (!state) return
    this.applyConsent(state)
  },

  /** Test seam: clears module state between cases. */
  reset(): void {
    measurementId = ''
    tagLoaded = false
  },
}
