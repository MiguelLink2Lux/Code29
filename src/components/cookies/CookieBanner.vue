<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import type { Lang } from '@/i18n/translations'
import { AnalyticsService } from '@/utils/analytics'
import { ConsentService, createDefaultConsentState, type ConsentState } from '@/utils/cookie-consent'

const emit = defineEmits<{
  'consent-granted': []
  'consent-denied': []
}>()

const visible = ref(false)
const preferencesOpen = ref(false)
const currentLang = ref<Lang>('es')
const formState = reactive<ConsentState>(createDefaultConsentState())

const copy = {
  es: {
    title: 'Usamos cookies',
    description:
      'Solo activamos analítica o marketing si lo autorizas expresamente. Puedes aceptar todo, quedarte solo con las necesarias o personalizar tus preferencias.',
    accept: 'Aceptar todas',
    reject: 'Solo necesarias',
    configure: 'Configurar',
    save: 'Guardar preferencias',
    more: 'Más información',
    preferencesTitle: 'Preferencias de cookies',
    preferencesDescription:
      'Las cookies necesarias siempre permanecen activas. Puedes activar o desactivar analítica y marketing cuando quieras.',
    necessaryLabel: 'Necesarias',
    necessaryHint: 'Siempre activas para el funcionamiento básico del sitio.',
    analyticsLabel: 'Analítica',
    analyticsHint: 'Miden uso y rendimiento para mejorar la web.',
    marketingLabel: 'Marketing',
    marketingHint: 'Permiten campañas y personalización publicitaria futura.',
  },
  en: {
    title: 'We use cookies',
    description:
      'We only enable analytics or marketing if you explicitly allow it. You can accept all, keep only the necessary ones, or customize your preferences.',
    accept: 'Accept all',
    reject: 'Necessary only',
    configure: 'Configure',
    save: 'Save preferences',
    more: 'More information',
    preferencesTitle: 'Cookie preferences',
    preferencesDescription:
      'Necessary cookies always stay active. You can enable or disable analytics and marketing whenever you want.',
    necessaryLabel: 'Necessary',
    necessaryHint: 'Always active for the basic operation of the site.',
    analyticsLabel: 'Analytics',
    analyticsHint: 'Measures usage and performance to improve the website.',
    marketingLabel: 'Marketing',
    marketingHint: 'Enables future campaigns and advertising personalization.',
  },
} as const

function syncLang(): void {
  currentLang.value = document.documentElement.lang === 'en' ? 'en' : 'es'
}

function t<Key extends keyof (typeof copy)['es']>(key: Key): string {
  return copy[currentLang.value][key]
}

function syncFormState(state?: ConsentState | null): void {
  const resolved = state ?? ConsentService.get() ?? createDefaultConsentState()
  formState.necessary = true
  formState.analytics = resolved.analytics
  formState.marketing = resolved.marketing
}

function openPreferences(): void {
  syncLang()
  syncFormState()
  visible.value = true
  preferencesOpen.value = true
}

function handleLanguageChange(event: Event): void {
  const detail = (event as CustomEvent<{ lang?: Lang }>).detail
  currentLang.value = detail?.lang === 'en' ? 'en' : 'es'
}

onMounted(() => {
  syncLang()

  if (ConsentService.hasDecided()) {
    AnalyticsService.restoreConsent()
  } else {
    syncFormState()
    visible.value = true
  }

  window.addEventListener('open-cookie-preferences', openPreferences)
  window.addEventListener('language-changed', handleLanguageChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('open-cookie-preferences', openPreferences)
  window.removeEventListener('language-changed', handleLanguageChange)
})

function accept() {
  const state = ConsentService.acceptAll()
  AnalyticsService.applyConsent(state)
  visible.value = false
  preferencesOpen.value = false
  emit('consent-granted')
}

function reject() {
  const state = ConsentService.rejectAll()
  AnalyticsService.applyConsent(state)
  visible.value = false
  preferencesOpen.value = false
  emit('consent-denied')
}

function savePreferences() {
  const state = ConsentService.save({
    necessary: true,
    analytics: formState.analytics,
    marketing: formState.marketing,
  })

  AnalyticsService.applyConsent(state)
  visible.value = false
  preferencesOpen.value = false
}
</script>

<template>
  <Transition name="banner">
    <div
      v-if="visible"
      class="cookie-banner"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cookie-title"
    >
      <p
        id="cookie-title"
        class="cookie-banner__title"
      >
        {{ t('title') }}
      </p>
      <p class="cookie-banner__description">
        {{ t('description') }}
      </p>
      <a
        href="/cookies"
        class="cookie-banner__link"
      >
        {{ t('more') }}
      </a>

      <section
        v-if="preferencesOpen"
        class="cookie-banner__preferences"
        aria-label="Cookie preferences"
      >
        <p class="cookie-banner__preferences-title">
          {{ t('preferencesTitle') }}
        </p>
        <p class="cookie-banner__preferences-copy">
          {{ t('preferencesDescription') }}
        </p>

        <label class="cookie-banner__option">
          <span class="cookie-banner__option-copy">
            <span class="cookie-banner__option-label">{{ t('necessaryLabel') }}</span>
            <span class="cookie-banner__option-hint">{{ t('necessaryHint') }}</span>
          </span>
          <input
            checked
            disabled
            type="checkbox"
          >
        </label>

        <label class="cookie-banner__option">
          <span class="cookie-banner__option-copy">
            <span class="cookie-banner__option-label">{{ t('analyticsLabel') }}</span>
            <span class="cookie-banner__option-hint">{{ t('analyticsHint') }}</span>
          </span>
          <input
            v-model="formState.analytics"
            type="checkbox"
          >
        </label>

        <label class="cookie-banner__option">
          <span class="cookie-banner__option-copy">
            <span class="cookie-banner__option-label">{{ t('marketingLabel') }}</span>
            <span class="cookie-banner__option-hint">{{ t('marketingHint') }}</span>
          </span>
          <input
            v-model="formState.marketing"
            type="checkbox"
          >
        </label>
      </section>

      <div class="cookie-banner__actions">
        <button
          class="cookie-banner__btn cookie-banner__btn--secondary"
          @click="reject"
        >
          {{ t('reject') }}
        </button>
        <button
          class="cookie-banner__btn cookie-banner__btn--secondary"
          type="button"
          @click="preferencesOpen = !preferencesOpen"
        >
          {{ t('configure') }}
        </button>
        <button
          v-if="preferencesOpen"
          class="cookie-banner__btn cookie-banner__btn--primary"
          type="button"
          @click="savePreferences"
        >
          {{ t('save') }}
        </button>
        <button
          v-else
          class="cookie-banner__btn cookie-banner__btn--primary"
          @click="accept"
        >
          {{ t('accept') }}
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.cookie-banner {
  position: fixed;
  bottom: var(--space-6);
  left: var(--space-4);
  right: var(--space-4);
  max-width: 40rem;
  margin-inline: auto;
  padding: var(--space-6);
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  box-shadow: var(--shadow-ambient);
  z-index: 999;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.cookie-banner__title {
  font-family: var(--font-display);
  font-size: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-primary);
  text-transform: uppercase;
}

.cookie-banner__description {
  font-family: var(--font-body);
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--color-text);
}

.cookie-banner__link {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  text-decoration: underline;
  text-underline-offset: 3px;
  width: fit-content;
  transition: color var(--transition-fast);
}

.cookie-banner__link:hover {
  color: var(--color-primary);
}

.cookie-banner__preferences {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-top: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.cookie-banner__preferences-title {
  font-family: var(--font-display);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-text);
  text-transform: uppercase;
}

.cookie-banner__preferences-copy {
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--color-text-muted);
}

.cookie-banner__option {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.cookie-banner__option-copy {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.cookie-banner__option-label {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-text);
  text-transform: uppercase;
}

.cookie-banner__option-hint {
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.cookie-banner__option input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--color-primary);
  margin-top: 0.125rem;
}

.cookie-banner__actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-top: var(--space-2);
}

.cookie-banner__btn {
  flex: 1;
  min-width: 9rem;
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-display);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  cursor: pointer;
  border: none;
  transition:
    opacity var(--transition-fast),
    box-shadow var(--transition-fast);
}

.cookie-banner__btn--primary {
  background: var(--btn-gradient);
  color: var(--color-base);
  box-shadow: var(--btn-glow);
}

.cookie-banner__btn--primary:hover {
  opacity: 0.88;
  box-shadow: 0px 0px 12px var(--color-primary);
}

.cookie-banner__btn--secondary {
  background: var(--color-surface-2);
  color: var(--color-text-muted);
}

.cookie-banner__btn--secondary:hover {
  color: var(--color-text);
  opacity: 0.85;
}

.banner-enter-active,
.banner-leave-active {
  transition: transform var(--transition-normal), opacity var(--transition-normal);
}

.banner-enter-from,
.banner-leave-to {
  transform: translateY(var(--space-4));
  opacity: 0;
}
</style>
