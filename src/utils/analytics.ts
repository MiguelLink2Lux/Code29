// GA4 abstraction — Consent Mode v2.
// All callers depend on this interface, never on window.gtag directly (DIP).

import { ConsentService } from '@/utils/cookie-consent'
import type { ConsentState } from '@/utils/cookie-consent'

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
      ad_storage: 'granted',
      ad_user_data: 'granted',
      ad_personalization: 'granted',
    })
  },

  denyConsent(): void {
    gtag('consent', 'update', {
      analytics_storage: 'denied',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
    })
  },

  applyConsent(state: ConsentState): void {
    gtag('consent', 'update', {
      analytics_storage: state.analytics ? 'granted' : 'denied',
      ad_storage: state.marketing ? 'granted' : 'denied',
      ad_user_data: state.marketing ? 'granted' : 'denied',
      ad_personalization: state.marketing ? 'granted' : 'denied',
    })
  },

  /** Reads stored consent and applies it — call on page load for returning visitors. */
  restoreConsent(): void {
    const state = ConsentService.get()
    if (!state) return
    this.applyConsent(state)
  },
}
