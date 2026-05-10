<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ConsentService } from '@/utils/cookie-consent'

const emit = defineEmits<{
  'consent-granted': []
  'consent-denied': []
}>()

const visible = ref(false)

onMounted(() => {
  if (!ConsentService.hasDecided()) {
    visible.value = true
  }
})

function accept() {
  ConsentService.acceptAll()
  visible.value = false
  emit('consent-granted')
}

function reject() {
  ConsentService.rejectAll()
  visible.value = false
  emit('consent-denied')
}

const isEn = () => document.documentElement.lang === 'en'

const t = {
  title:       { es: 'Usamos cookies',    en: 'We use cookies' },
  description: {
    es: 'Utilizamos cookies de análisis para mejorar tu experiencia. Puedes aceptarlas o rechazarlas en cualquier momento.',
    en: 'We use analytics cookies to improve your experience. You can accept or reject them at any time.',
  },
  accept: { es: 'Aceptar todas',    en: 'Accept all' },
  reject: { es: 'Solo necesarias',  en: 'Necessary only' },
  more:   { es: 'Más información',  en: 'More information' },
}

function lang(key: keyof typeof t): string {
  return isEn() ? t[key].en : t[key].es
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
      <p id="cookie-title" class="cookie-banner__title">{{ lang('title') }}</p>
      <p class="cookie-banner__description">{{ lang('description') }}</p>
      <a href="/cookies" class="cookie-banner__link">{{ lang('more') }}</a>
      <div class="cookie-banner__actions">
        <button class="cookie-banner__btn cookie-banner__btn--secondary" @click="reject">
          {{ lang('reject') }}
        </button>
        <button class="cookie-banner__btn cookie-banner__btn--primary" @click="accept">
          {{ lang('accept') }}
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
  transition: opacity var(--transition-fast), box-shadow var(--transition-fast);
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
