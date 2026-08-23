<script setup lang="ts">
// The conversational contact island: a message thread instead of one step at a
// time, free text instead of closed options, and no step counter — the server
// decides when the conversation is done.
//
// It owns presentation and side-effect calls only. The flow rules, the budget
// and the privacy guarantees live in src/utils/contact-conversation.ts, which is
// framework-free and unit-tested without mounting anything.
import { computed, onMounted, ref } from 'vue'

import { translations, type Lang } from '@/i18n/translations'
import { type ContactApi, createContactApi } from '@/utils/contact-api'
import { createConversation, MAX_MESSAGE_LENGTH } from '@/utils/contact-conversation'
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
const chat = createConversation({ api })

// The conversation state is deliberately framework-free, so it is not reactive.
// This counter is bumped after every mutation and read by the computeds below,
// which is what makes the thread follow the flow without coupling the module to
// Vue.
const tick = ref(0)
const sync = () => {
  tick.value += 1
}

const draft = ref('')
const emailDraft = ref('')
const codeDraft = ref('')
const localError = ref<string | null>(null)

const copy = computed(() => translations.contactConversation[currentLang.value])

const messages = computed(() => {
  void tick.value
  return chat.state.messages
})
const busy = computed(() => {
  void tick.value
  return chat.state.busy
})
const complete = computed(() => {
  void tick.value
  return chat.state.complete
})
const exhausted = computed(() => {
  void tick.value
  return chat.state.exhausted
})
const emailVerified = computed(() => {
  void tick.value
  return chat.state.emailVerified
})
const codeRequested = computed(() => {
  void tick.value
  return chat.state.pendingEmail !== null
})
const needsEmail = computed(() => {
  void tick.value
  return chat.state.missing.includes('email') && !chat.state.emailVerified
})

const errorMessage = computed(() => {
  void tick.value
  const code = localError.value ?? chat.state.error

  if (!code) return ''

  const errors = copy.value.errors as Record<string, string>

  return errors[code] ?? errors.generic
})

async function submitMessage(): Promise<void> {
  if (busy.value || complete.value) return

  const text = draft.value.trim()
  localError.value = null

  if (!text) {
    localError.value = 'empty'
    sync()
    return
  }

  // Checked here as well as in the module: no reason to spend a request to be
  // told what we already know.
  if (text.length > MAX_MESSAGE_LENGTH) {
    localError.value = 'tooLong'
    sync()
    return
  }

  await chat.send(text)
  draft.value = ''
  sync()

  // Completeness is the trigger, and the module refuses if the server has not
  // agreed — so calling it unconditionally is safe and never premature.
  await chat.deliverReport()
  sync()
}

async function requestCode(): Promise<void> {
  if (busy.value) return

  localError.value = null

  try {
    const token = await turnstile.getToken(document.createElement('div'))
    await chat.requestCode(emailDraft.value, token)
  } catch (error) {
    // A missing site key is a deployment problem: telling the visitor to prove
    // they are human would send them in circles.
    localError.value = error instanceof TurnstileNotConfigured ? 'unavailable' : 'humanCheck'
  } finally {
    sync()
  }
}

async function confirmCode(): Promise<void> {
  if (busy.value) return

  localError.value = null
  await chat.confirmCode(codeDraft.value)
  codeDraft.value = ''
  sync()

  // Verifying the address is usually the last missing fact, so this is the
  // moment the report becomes possible.
  await chat.deliverReport()
  sync()
}

onMounted(() => {
  // The switcher sets html[lang] before paint; follow it, then track changes.
  currentLang.value = document.documentElement.lang === 'en' ? 'en' : 'es'
  window.addEventListener('language-changed', (event) => {
    const detail = (event as CustomEvent<{ lang?: Lang }>).detail
    currentLang.value = detail?.lang === 'en' ? 'en' : 'es'
  })
  sync()
})
</script>

<template>
  <div class="conversation">
    <p
      v-if="!messages.length"
      class="conversation__intro"
    >
      {{ copy.intro }}
    </p>

    <!-- role="log" + aria-live: new bot messages are announced without stealing focus -->
    <ol
      v-if="messages.length"
      class="conversation__thread"
      role="log"
      aria-live="polite"
      :aria-label="copy.threadLabel"
    >
      <li
        v-for="(message, index) in messages"
        :key="index"
        :class="[
          'conversation__message',
          message.role === 'visitor'
            ? 'conversation__message--visitor'
            : 'conversation__message--bot',
        ]"
      >
        <span class="conversation__who">
          {{ message.role === 'visitor' ? copy.you : copy.assistant }}
        </span>
        <p class="conversation__text">
          {{ message.text }}
        </p>
      </li>
    </ol>

    <div
      v-if="complete"
      class="conversation__done"
      role="status"
    >
      <p class="conversation__done-title">
        {{ copy.done.title }}
      </p>
      <p>{{ exhausted ? copy.exhausted : copy.done.body }}</p>
    </div>

    <form
      v-else
      class="conversation__composer"
      novalidate
      @submit.prevent="submitMessage"
    >
      <label
        class="conversation__sr-only"
        for="conversation-input"
      >
        {{ copy.placeholder }}
      </label>
      <input
        id="conversation-input"
        v-model="draft"
        class="conversation__input"
        type="text"
        :placeholder="copy.placeholder"
        autocomplete="off"
        :aria-invalid="Boolean(errorMessage)"
      >
      <button
        type="submit"
        class="conversation__btn conversation__btn--primary"
        :disabled="busy"
      >
        {{ busy ? copy.sending : copy.send }}
      </button>
    </form>

    <!-- The verification thread, interleaved rather than a separate screen -->
    <section
      v-if="needsEmail && !complete"
      class="conversation__verify"
    >
      <p>{{ copy.verify.prompt }}</p>

      <div
        v-if="!codeRequested"
        class="conversation__verify-row"
      >
        <label
          class="conversation__label"
          for="conversation-email"
        >
          {{ copy.verify.emailLabel }}
        </label>
        <input
          id="conversation-email"
          v-model="emailDraft"
          class="conversation__input"
          type="email"
          :placeholder="copy.verify.emailPlaceholder"
          autocomplete="email"
        >
        <button
          type="button"
          class="conversation__btn"
          :disabled="busy"
          @click="requestCode"
        >
          {{ copy.verify.request }}
        </button>
      </div>

      <div
        v-else
        class="conversation__verify-row"
      >
        <label
          class="conversation__label"
          for="conversation-code"
        >
          {{ copy.verify.codeLabel }}
        </label>
        <input
          id="conversation-code"
          v-model="codeDraft"
          class="conversation__input"
          type="text"
          inputmode="numeric"
          :placeholder="copy.verify.codePlaceholder"
          autocomplete="one-time-code"
        >
        <button
          type="button"
          class="conversation__btn"
          :disabled="busy"
          @click="confirmCode"
        >
          {{ copy.verify.confirm }}
        </button>
        <p class="conversation__hint">
          {{ copy.verify.codeHint }}
        </p>
      </div>
    </section>

    <p
      v-if="emailVerified"
      class="conversation__verified"
    >
      {{ copy.verify.verified }}
    </p>

    <p
      v-if="errorMessage"
      class="conversation__error"
      role="alert"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>

<style scoped>
/* Terminal aesthetic, no border radius — see docs/architecture/design.md. */
.conversation {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--glass-bg);
  padding: var(--space-8);
  text-align: left;
}

.conversation__intro {
  color: var(--color-text-muted);
}

.conversation__thread {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 22rem;
  overflow-y: auto;
}

.conversation__message {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--color-surface-1);
}

.conversation__message--visitor {
  border-left: 2px solid var(--color-surface-3);
}

.conversation__message--bot {
  border-left: 2px solid var(--color-primary);
}

.conversation__who {
  font-family: var(--font-display);
  font-size: 0.6875rem;
  letter-spacing: 0.16em;
  color: var(--color-text-muted);
}

.conversation__text {
  color: var(--color-text);
  white-space: pre-wrap;
}

.conversation__composer,
.conversation__verify-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  flex-wrap: wrap;
}

.conversation__verify {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-4);
  color: var(--color-text-muted);
}

.conversation__input {
  flex: 1 1 12rem;
  background: transparent;
  border: none;
  border-bottom: var(--input-border-bottom);
  color: var(--color-text);
  padding: var(--space-2) 0;
  font-family: var(--font-body);
  font-size: 1rem;
}

.conversation__input:focus {
  outline: none;
  border-bottom: var(--input-border-focus);
}

.conversation__label {
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
}

.conversation__btn {
  font-family: var(--font-display);
  letter-spacing: 0.08em;
  padding: var(--space-3) var(--space-6);
  border: none;
  background: var(--color-surface-2);
  color: var(--color-text);
  cursor: pointer;
}

.conversation__btn--primary {
  background: var(--btn-gradient);
  box-shadow: var(--btn-glow);
  color: var(--color-base);
}

.conversation__btn:disabled {
  opacity: 0.6;
  cursor: progress;
}

.conversation__hint,
.conversation__verified {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.conversation__error {
  font-size: 0.875rem;
  color: #ff7a7a;
}

.conversation__done-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  color: var(--color-primary);
}

.conversation__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}
</style>
