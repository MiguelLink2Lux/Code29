import { describe, expect, it } from 'vitest'

import { translations } from '@/i18n/translations'

/**
 * ServicesSection builds its `data-i18n` keys by index
 * (`services.items.2.features.5`), and the language switcher resolves them at
 * runtime. So a feature that exists in one language and not the other does not
 * fail the build: it silently keeps the other language's text on screen after a
 * switch. These assertions are what make that impossible.
 */
const LOCALES = ['es', 'en'] as const

describe('services copy', () => {
  it('offers the same number of services in both languages', () => {
    expect(translations.services.es.items).toHaveLength(translations.services.en.items.length)
  })

  it('gives every service the same number of features in both languages', () => {
    const es = translations.services.es.items
    const en = translations.services.en.items

    es.forEach((service, index) => {
      expect(service.features.length, `service ${index} (${service.title})`).toBe(
        en[index].features.length,
      )
    })
  })

  it('numbers the tags consistently, even though their wording is translated', () => {
    // SERVICIO_01 / SERVICE_01: the label is translated on purpose. What must
    // match is the sequence, because the i18n keys are index-based.
    const numbers = (locale: 'es' | 'en') =>
      translations.services[locale].items.map((service) => service.tag.match(/\d+/)?.[0])

    expect(numbers('es')).toEqual(numbers('en'))
  })

  it('never ships an empty string', () => {
    for (const locale of LOCALES) {
      for (const service of translations.services[locale].items) {
        expect(service.title.trim(), `${locale} title`).not.toBe('')
        expect(service.description.trim(), `${locale} description`).not.toBe('')
        for (const feature of service.features) {
          expect(feature.trim(), `${locale} feature of ${service.title}`).not.toBe('')
        }
      }
    }
  })

  it('covers the canon: quality, environment, training and governance are named', () => {
    // The canon (docs/architecture/improvement-canon.md) is the analysis
    // instrument; the catalogue has to at least name what the report will
    // recommend, or a diagnosis ends in something the visitor cannot buy.
    const spanish = JSON.stringify(translations.services.es).toLowerCase()

    for (const topic of ['calidad', 'entorno', 'formación', 'gobernanza', 'revisión de código']) {
      expect(spanish, `missing from the catalogue: ${topic}`).toContain(topic)
    }
  })

  it('names the complete workflow, which is what the funnel sells', () => {
    const subheading = translations.services.es.subheading.toLowerCase()
    expect(subheading).toMatch(/flujo/)
  })
})
