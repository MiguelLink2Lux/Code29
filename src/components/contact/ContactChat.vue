<script setup lang="ts">
// Guided contact chat: renders one fixed step at a time over the state machine
// in src/utils/contact-chat.ts. This component owns presentation and the
// side-effect calls; it owns no flow logic and no validation rules.
//
// The API client and the Turnstile client arrive as props so the whole component
// is testable without network or third-party scripts (DIP, as the repo requires).
import { computed, onMounted, ref, watch } from 'vue'

import { translations, type Lang } from '@/i18n/translations'
import { type ContactApi, ContactApiError, createContactApi } from '@/utils/contact-api'
import { createContactChat } from '@/utils/contact-chat'
import { stepById } from '@/utils/contact-chat-flow'
import {
  createTurnstileClient,
  TurnstileNotConfigured,
  type TurnstileClient,
} from '@/utils/turnstile-client'

const props = defineProps<{
  api?: ContactApi
  turnstile?: TurnstileClient
}>()

const api = props.api ?? createContactApi()
const turnstile =
  props.turnstile ??
  createTurnstileClient((import.meta.env.PUBLIC_TURNSTILE_SITE_KEY as string) ?? '')

const currentLang = ref<Lang>('es')
const chat = createContactChat(currentLang.value)

// The chat state machine is deliberately framework-free, so it is not reactive.
// This counter is bumped after every mutation and read by the computeds below,
// which is what makes the template follow the flow without coupling
// contact-chat.ts to Vue.
const tick = ref(0)
const sync = () => {
  tick.value += 1
}

const draft = ref('')
const consentGiven = ref(false)
const errorMessage = ref('')
const busy = ref(false)
const finished = ref(false)
const turnstileHost = ref<HTMLElement | null>(null)

const copy = computed(() => translations.contactChat[currentLang.value])
const currentStepId = computed(() => {
  void tick.value
  return chat.state.currentStepId
})
const stepIndex = computed(() => {
  void tick.value
  return chat.state.progress.index
})
const step = computed(() => stepById(currentStepId.value))
const stepCopy = computed(() => copy.value.steps[currentStepId.value as keyof typeof copy.value.steps])
const progressLabel = computed(() =>
  copy.value.progress
    .replace('{index}', String(stepIndex.value + 1))
    .replace('{total}', String(chat.state.progress.total)),
)

/** Turns any failure into copy the visitor can act on. */
function describeError(error: unknown): string {
  if (error instanceof ContactApiError) {
    if (error.status === 403) return copy.value.errors.humanCheck
    if (error.status === 400) return copy.value.errors.codeRejected
    if (error.status === 401) return copy.value.errors.expired
    if (error.status === 503) return copy.value.errors.unavailable
    if (error.status === 0) return copy.value.errors.network
    return copy.value.errors.generic
  }

  // A missing site key is a deployment problem; telling the visitor to prove
  // they are human would send them in circles.
  if (error instanceof TurnstileNotConfigured) return copy.value.errors.unavailable

  // Any other Turnstile failure never reaches the backend: it is a human check.
  return copy.value.errors.humanCheck
}

async function sendVerificationCode(): Promise<void> {
  busy.value = true
  errorMessage.value = ''

  try {
    const token = await turnstile.getToken(turnstileHost.value ?? document.createElement('div'))
    await api.requestVerificationCode(chat.answerFor('email'), token)
  } catch (error) {
    errorMessage.value = describeError(error)
  } finally {
    busy.value = false
  }
}

async function confirmCode(code: string): Promise<boolean> {
  busy.value = true
  errorMessage.value = ''

  try {
    const token = await api.confirmVerificationCode(chat.answerFor('email'), code)
    chat.markEmailVerified(token)
    return true
  } catch (error) {
    errorMessage.value = describeError(error)
    return false
  } finally {
    busy.value = false
  }
}

async function deliverReport(): Promise<void> {
  busy.value = true
  errorMessage.value = ''

  try {
    await api.requestReport(chat.buildReportRequest(), chat.state.accessToken ?? '')
    finished.value = true
  } catch (error) {
    errorMessage.value = describeError(error)
  } finally {
    busy.value = false
  }
}

async function submit(): Promise<void> {
  if (busy.value) return

  const stepId = chat.state.currentStepId
  const value = step.value.kind === 'consent' ? String(consentGiven.value) : draft.value

  // The code step is the one place where advancing depends on the backend.
  if (stepId === 'code') {
    const validation = chat.answer(value)
    sync()
    if (!validation.ok) {
      errorMessage.value = copy.value.errors[validation.error]
      return
    }

    const confirmed = await confirmCode(value)
    if (!confirmed) {
      chat.back()
      sync()
      return
    }

    draft.value = ''
    return
  }

  const result = chat.answer(value)
  sync()

  if (!result.ok) {
    errorMessage.value = copy.value.errors[result.error]
    return
  }

  errorMessage.value = ''
  draft.value = ''

  if (chat.state.currentStepId === 'code' && !chat.state.emailVerified) {
    await sendVerificationCode()
  }

  if (chat.state.complete) {
    await deliverReport()
  }
}

function goBack(): void {
  errorMessage.value = ''
  chat.back()
  sync()
  draft.value = chat.answerFor(chat.state.currentStepId)
}

function selectOption(value: string): void {
  draft.value = value
}

onMounted(() => {
  // The switcher sets html[lang] before paint; follow it, then track changes.
  currentLang.value = document.documentElement.lang === 'en' ? 'en' : 'es'
  window.addEventListener('language-changed', (event) => {
    const detail = (event as CustomEvent<{ lang?: Lang }>).detail
    currentLang.value = detail?.lang === 'en' ? 'en' : 'es'
  })
  draft.value = chat.answerFor(chat.state.currentStepId)
})

watch(
  currentStepId,
  () => {
    consentGiven.value = chat.answerFor('consent') === 'true'
  },
)
</script>

<template>
  <div class="contact-chat">
    <div
      v-if="finished"
      class="contact-chat__done"
      role="status"
    >
      <p class="contact-chat__done-title">
        {{ copy.success.title }}
      </p>
      <p>{{ copy.success.body }}</p>
    </div>

    <template v-else>
      <p class="contact-chat__intro">
        {{ copy.intro }}
      </p>
      <p class="contact-chat__progress">
        {{ progressLabel }}
      </p>

      <form
        class="contact-chat__step"
        novalidate
        @submit.prevent="submit"
      >
        <p
          id="contact-chat-prompt"
          class="contact-chat__prompt"
        >
          {{ stepCopy.prompt }}
        </p>

        <!-- Choice steps: the four workflow questions -->
        <fieldset
          v-if="step.kind === 'choice'"
          class="contact-chat__options"
          aria-labelledby="contact-chat-prompt"
        >
          <label
            v-for="option in step.options"
            :key="option.value"
            class="contact-chat__option"
          >
            <input
              type="radio"
              name="choice"
              :value="option.value"
              :checked="draft === option.value"
              @change="selectOption(option.value)"
            >
            <span>{{ (stepCopy as { options: Record<string, string> }).options[option.labelKey] }}</span>
          </label>
        </fieldset>

        <!-- Consent step -->
        <label
          v-else-if="step.kind === 'consent'"
          class="contact-chat__consent"
        >
          <input
            v-model="consentGiven"
            type="checkbox"
          >
          <span>
            {{ (stepCopy as { label: string }).label }}
            <a href="/privacy-policy">{{ (stepCopy as { privacyLinkLabel: string }).privacyLinkLabel }}</a>
          </span>
        </label>

        <!-- Everything else is a single line of text -->
        <input
          v-else
          v-model="draft"
          class="contact-chat__input"
          type="text"
          :inputmode="step.kind === 'code' ? 'numeric' : 'text'"
          :placeholder="(stepCopy as { placeholder?: string }).placeholder ?? ''"
          :aria-label="stepCopy.prompt"
          :aria-invalid="Boolean(errorMessage)"
          autocomplete="off"
        >

        <p
          v-if="(stepCopy as { hint?: string }).hint"
          class="contact-chat__hint"
        >
          {{ (stepCopy as { hint?: string }).hint }}
        </p>

        <!-- Turnstile renders here, invisibly unless it needs interaction -->
        <div
          ref="turnstileHost"
          class="contact-chat__turnstile"
        />

        <p
          v-if="errorMessage"
          class="contact-chat__error"
          role="alert"
        >
          {{ errorMessage }}
        </p>

        <div class="contact-chat__actions">
          <button
            v-if="stepIndex > 0"
            type="button"
            class="contact-chat__btn contact-chat__btn--ghost"
            @click="goBack"
          >
            {{ copy.back }}
          </button>
          <button
            type="submit"
            class="contact-chat__btn contact-chat__btn--primary"
            :disabled="busy"
          >
            {{ busy ? copy.sending : copy.next }}
          </button>
        </div>
      </form>
    </template>
  </div>
</template>

<style scoped>
/* Terminal aesthetic, no border radius — see docs/architecture/design.md. */
.contact-chat {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--glass-bg);
  padding: var(--space-8);
}

.contact-chat__intro {
  color: var(--color-text-muted);
}

.contact-chat__progress {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  color: var(--color-primary);
}

.contact-chat__step {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.contact-chat__prompt {
  font-family: var(--font-display);
  font-size: 1.25rem;
  color: var(--color-text);
}

.contact-chat__input {
  background: transparent;
  border: none;
  border-bottom: var(--input-border-bottom);
  color: var(--color-text);
  padding: var(--space-2) 0;
  font-family: var(--font-body);
  font-size: 1rem;
}

.contact-chat__input:focus {
  outline: none;
  border-bottom: var(--input-border-focus);
}

.contact-chat__options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  border: none;
  padding: 0;
}

.contact-chat__option,
.contact-chat__consent {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  color: var(--color-text);
  cursor: pointer;
}

.contact-chat__hint,
.contact-chat__error {
  font-size: 0.875rem;
}

.contact-chat__hint {
  color: var(--color-text-muted);
}

.contact-chat__error {
  color: #ff7a7a;
}

.contact-chat__actions {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.contact-chat__btn {
  font-family: var(--font-display);
  letter-spacing: 0.08em;
  padding: var(--space-3) var(--space-6);
  cursor: pointer;
  border: none;
}

.contact-chat__btn--primary {
  background: var(--btn-gradient);
  box-shadow: var(--btn-glow);
  color: var(--color-base);
}

.contact-chat__btn--primary:disabled {
  opacity: 0.6;
  cursor: progress;
}

.contact-chat__btn--ghost {
  background: transparent;
  color: var(--color-text-muted);
}

.contact-chat__done-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  color: var(--color-primary);
}
</style>
