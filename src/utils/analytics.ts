// GA4 abstraction — Consent Mode v2.
// All callers depend on this interface, never on window.gtag directly (DIP).

import { ConsentService } from '@/utils/cookie-consent'

declare global {
  interface Window {
    dataLayer: unknown[]
    gtag: (...args: unknown[]) => void
  }
}

function gtag(...args: unknown[]): void {
  if (typeof window === 'undefined' || typeof window.gtag !== 'function') return
  window.gtag(...args)
}

export const AnalyticsService = {
  grantConsent(): void {
    gtag('consent', 'update', {
      analytics_storage: 'granted',
    })
  },

  denyConsent(): void {
    gtag('consent', 'update', {
      analytics_storage: 'denied',
    })
  },

  /** Reads stored consent and applies it — call on page load for returning visitors. */
  restoreConsent(): void {
    const state = ConsentService.get()
    if (!state) return
    state.analytics ? this.grantConsent() : this.denyConsent()
  },
}
