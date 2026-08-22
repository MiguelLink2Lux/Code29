import { beforeEach, describe, expect, it } from 'vitest'

import { AnalyticsService } from '@/utils/analytics'
import { ConsentService } from '@/utils/cookie-consent'

const GA_ID = 'G-TESTID123'
const tagScript = () => document.querySelector<HTMLScriptElement>('script[data-ga4]')

beforeEach(() => {
  ConsentService.clear()
  document.querySelectorAll('script[data-ga4]').forEach((node) => node.remove())
  AnalyticsService.reset()
  window.dataLayer = []
})

describe('bootstrap', () => {
  it('does not load the Google tag when no decision has been made', () => {
    AnalyticsService.bootstrap(GA_ID)

    // Consent Mode's "denied" ping still reaches Google with the IP, the URL and
    // the user agent. Before a decision, nothing may be sent at all.
    expect(tagScript()).toBeNull()
  })

  it('declares consent as denied by default, before anything can load', () => {
    AnalyticsService.bootstrap(GA_ID)

    const consentDefault = window.dataLayer.find(
      (entry) => Array.isArray(entry) && entry[0] === 'consent' && entry[1] === 'default',
    ) as unknown[] | undefined

    expect(consentDefault).toBeTruthy()
    expect(consentDefault?.[2]).toMatchObject({ analytics_storage: 'denied' })
  })

  it('loads the tag for a returning visitor who already granted analytics', () => {
    ConsentService.acceptAll()

    AnalyticsService.bootstrap(GA_ID)

    expect(tagScript()).not.toBeNull()
    expect(tagScript()?.src).toContain(GA_ID)
  })

  it('stays silent for a returning visitor who refused analytics', () => {
    ConsentService.rejectAll()

    AnalyticsService.bootstrap(GA_ID)

    expect(tagScript()).toBeNull()
  })
})

describe('applyConsent', () => {
  it('loads the tag the moment analytics is granted', () => {
    AnalyticsService.bootstrap(GA_ID)
    expect(tagScript()).toBeNull()

    AnalyticsService.applyConsent({ necessary: true, analytics: true, marketing: false })

    expect(tagScript()).not.toBeNull()
  })

  it('never loads the tag when analytics is refused', () => {
    AnalyticsService.bootstrap(GA_ID)

    AnalyticsService.applyConsent({ necessary: true, analytics: false, marketing: true })

    expect(tagScript()).toBeNull()
  })

  it('loads the tag only once across repeated grants', () => {
    AnalyticsService.bootstrap(GA_ID)

    AnalyticsService.applyConsent({ necessary: true, analytics: true, marketing: false })
    AnalyticsService.applyConsent({ necessary: true, analytics: true, marketing: true })

    expect(document.querySelectorAll('script[data-ga4]')).toHaveLength(1)
  })

  it('still pushes the consent update so a loaded tag reacts', () => {
    AnalyticsService.bootstrap(GA_ID)
    const before = window.dataLayer.length

    AnalyticsService.applyConsent({ necessary: true, analytics: true, marketing: false })

    expect(window.dataLayer.length).toBeGreaterThan(before)
  })

  it('does nothing at all when no measurement id was configured', () => {
    // PUBLIC_GA4_ID unset: the site must work with analytics absent.
    AnalyticsService.applyConsent({ necessary: true, analytics: true, marketing: true })

    expect(tagScript()).toBeNull()
  })
})

describe('withdrawal', () => {
  it('pushes a denied update when consent is revoked', () => {
    AnalyticsService.bootstrap(GA_ID)
    AnalyticsService.applyConsent({ necessary: true, analytics: true, marketing: false })

    AnalyticsService.applyConsent({ necessary: true, analytics: false, marketing: false })

    const last = window.dataLayer.at(-1) as unknown[]
    expect(last[2]).toMatchObject({ analytics_storage: 'denied' })
  })
})
