<script setup lang="ts">
// The conversational contact island: a message thread instead of one step at a
// time, free text instead of closed options, and no step counter — the server
// decides when the conversation is done.
//
// It owns presentation and side-effect calls only. The flow rules, the budget
// and the privacy guarantees live in src/utils/contact-conversation.ts, which is
// framework-free and unit-tested without mounting anything.
//
// One composer serves the whole conversation. Verifying the address used to be
// a separate block of labelled fields beside the thread, which is what made the
// chat read as a form wearing a costume: the bot now asks for the address in its
// own voice, in the thread, and the visitor answers where they answer everything
// else. The address and the code are marked ephemeral by the module, so they are
// shown and never stored.
import { computed, nextTick, onMounted, ref, watch } from 'vue'

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
  /** Injectable so a test can pin the opening. */
  pickOpening?: (count: number) => number
}>()

const api = props.api ?? createContactApi()
const turnstile =
  props.turnstile ??
  createTurnstileClient((import.meta.env.PUBLIC_TURNSTILE_SITE_KEY as string) ?? '')

// Read before the conversation is created: the opening has to be in the
// visitor's language from the first paint.
const currentLang = ref<Lang>(
  typeof document !== 'undefined' && document.documentElement.lang === 'en' ? 'en' : 'es',
)

const copy = computed(() => translations.contactConversation[currentLang.value])

const chat = createConversation({
  api,
  openings: translations.contactConversation[currentLang.value].openings,
  ...(props.pickOpening ? { pickOpening: props.pickOpening } : {}),
})

// The conversation state is deliberately framework-free, so it is not reactive.
// This counter is bumped after every mutation and read by the computeds below,
// which is what makes the thread follow the flow without coupling the module to
// Vue.
const tick = ref(0)
const sync = () => {
  tick.value += 1
}

const draft = ref('')
const localError = ref<string | null>(null)
const thread = ref<HTMLElement | null>(null)
// Where Cloudflare mounts the challenge. It has to be a node that is actually in
// the document: a detached one makes Turnstile lose track of its own widget, and
// an interactive challenge rendered there would be unreachable for the visitor.
const turnstileHost = ref<HTMLElement | null>(null)

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

/**
 * What the composer is asking for right now. One source, derived from the
 * server's own answer about what it still needs — never set by the template.
 */
const mode = computed<'message' | 'email' | 'code'>(() => {
  void tick.value

  if (chat.state.pendingEmail !== null && !chat.state.emailVerified) return 'code'

  // Only when the address is the LAST thing missing. The server reports `email`
  // as missing from the very first turn — it cannot know it otherwise — so
  // asking on `includes` would demand the address before the conversation has
  // said anything, which is the questionnaire behaviour this replaces.
  const onlyTheAddressIsLeft =
    chat.state.missing.length === 1 && chat.state.missing[0] === 'email'

  if (onlyTheAddressIsLeft && !chat.state.emailVerified) return 'email'

  return 'message'
})

const composerId = computed(() =>
  mode.value === 'message' ? 'conversation-input' : `conversation-${mode.value}`,
)

const placeholder = computed(() => {
  if (mode.value === 'email') return copy.value.verify.emailPlaceholder
  if (mode.value === 'code') return copy.value.verify.codePlaceholder

  return copy.value.placeholder
})

const composerLabel = computed(() => {
  if (mode.value === 'email') return copy.value.verify.emailLabel
  if (mode.value === 'code') return copy.value.verify.codeLabel

  return copy.value.placeholder
})

const sendLabel = computed(() => {
  if (busy.value) return copy.value.sending
  if (mode.value === 'email') return copy.value.verify.request
  if (mode.value === 'code') return copy.value.verify.confirm

  return copy.value.send
})

const errorMessage = computed(() => {
  void tick.value
  const code = localError.value ?? chat.state.error

  if (!code) return ''

  const errors = copy.value.errors as Record<string, string>

  return errors[code] ?? errors.generic
})

// The bot asks for the address itself, once, the moment the server says it is
// the missing piece. Without this the composer would silently change shape and
// the visitor would have no idea why.
watch(mode, (next, previous) => {
  if (next === previous) return

  if (next === 'email') chat.pushEphemeral('bot', copy.value.verify.ask)
  if (next === 'code') chat.pushEphemeral('bot', copy.value.verify.askCode)

  sync()
})

// Follow the conversation. A thread that stays where it was is a thread the
// visitor has to scroll to read their own answer.
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (thread.value) thread.value.scrollTop = thread.value.scrollHeight
  },
)

async function submit(): Promise<void> {
  if (busy.value || complete.value) return

  const text = draft.value.trim()
  localError.value = null

  if (!text) {
    localError.value = 'empty'
    sync()
    return
  }

  if (mode.value === 'email') return submitEmail(text)
  if (mode.value === 'code') return submitCode(text)

  return submitMessage(text)
}

async function submitMessage(text: string): Promise<void> {
  // Checked here as well as in the module: no reason to spend a request to be
  // told what we already know.
  if (text.length > MAX_MESSAGE_LENGTH) {
    localError.value = 'tooLong'
    sync()
    return
  }

  // Started, then synced, then awaited: `send` flips `busy` synchronously, and
  // without this sync the typing indicator would only appear after the answer
  // it was meant to cover had already arrived.
  const pending = chat.send(text)
  draft.value = ''
  sync()
  await pending
  sync()

  // Completeness is the trigger, and the module refuses if the server has not
  // agreed — so calling it unconditionally is safe and never premature.
  await chat.deliverReport()
  sync()
}

async function submitEmail(address: string): Promise<void> {
  if (!turnstileHost.value) {
    // The host is unconditional in the template, so this is a bug on our side,
    // never something the visitor did.
    localError.value = 'unavailable'
    sync()
    return
  }

  try {
    const token = await turnstile.getToken(turnstileHost.value)
    await chat.requestCode(address, token)
    draft.value = ''
  } catch (error) {
    // A missing site key is a deployment problem: telling the visitor to prove
    // they are human would send them in circles.
    localError.value = error instanceof TurnstileNotConfigured ? 'unavailable' : 'humanCheck'
  } finally {
    sync()
  }
}

async function submitCode(code: string): Promise<void> {
  const pending = chat.confirmCode(code)
  draft.value = ''
  sync()
  await pending
  sync()

  if (chat.state.emailVerified) {
    chat.pushEphemeral('bot', copy.value.verify.verified)
    sync()
  }

  // Verifying the address is usually the last missing fact, so this is the
  // moment the report becomes possible.
  await chat.deliverReport()
  sync()
}

// Enter sends, Shift+Enter breaks the line — what every chat does, and the
// reason the composer is a textarea rather than a single-line input.
function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey) return

  event.preventDefault()
  void submit()
}

onMounted(() => {
  // The switcher sets html[lang] before paint; follow it, then track changes.
  window.addEventListener('language-changed', (event) => {
    const detail = (event as CustomEvent<{ lang?: Lang }>).detail
    currentLang.value = detail?.lang === 'en' ? 'en' : 'es'
  })
  sync()
})
</script>

<template>
  <div class="conversation">
    <!-- role="log" + aria-live: new bot messages are announced without stealing focus -->
    <ol
      ref="thread"
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

      <li
        v-if="busy"
        class="conversation__message conversation__message--bot conversation__message--typing"
      >
        <span class="conversation__who">{{ copy.assistant }}</span>
        <p
          class="conversation__typing"
          :aria-label="copy.typing"
        >
          <span class="conversation__dot" />
          <span class="conversation__dot" />
          <span class="conversation__dot" />
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
      @submit.prevent="submit"
    >
      <label
        class="conversation__sr-only"
        :for="composerId"
      >
        {{ composerLabel }}
      </label>
      <!--
        The id names what the field is asking for — conversation-email,
        conversation-code — which is what the end-to-end test addresses. The
        message mode keeps the name it always had.
      -->
      <textarea
        :id="composerId"
        v-model="draft"
        class="conversation__input"
        rows="1"
        :placeholder="placeholder"
        :inputmode="mode === 'code' ? 'numeric' : 'text'"
        :autocomplete="mode === 'email' ? 'email' : mode === 'code' ? 'one-time-code' : 'off'"
        :aria-invalid="Boolean(errorMessage)"
        @keydown="onKeydown"
      />
      <button
        type="submit"
        class="conversation__btn conversation__btn--primary"
        :disabled="busy"
      >
        {{ sendLabel }}
      </button>
    </form>

    <!--
      Always in the document, outside the v-if/v-else above: Turnstile needs a
      mounted node to render into, and when the challenge turns interactive the
      visitor has to be able to see and reach it.
    -->
    <div
      ref="turnstileHost"
      class="conversation__challenge"
    />

    <p
      v-if="mode === 'code'"
      class="conversation__hint"
    >
      {{ copy.verify.codeHint }}
    </p>

    <p
      v-if="emailVerified && mode === 'message'"
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

.conversation__thread {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 22rem;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.conversation__message {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--color-surface-1);
  /* Bubbles, not rows: each side keeps its own column so the thread reads as
     an exchange at a glance. */
  max-width: 85%;
}

.conversation__message--visitor {
  align-self: flex-end;
  border-right: 2px solid var(--color-surface-3);
  text-align: right;
}

.conversation__message--bot {
  align-self: flex-start;
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

.conversation__typing {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  min-height: 1.25rem;
}

.conversation__dot {
  width: 0.375rem;
  height: 0.375rem;
  background: var(--color-primary);
  opacity: 0.4;
  animation: conversation-blink 1.2s infinite ease-in-out;
}

.conversation__dot:nth-child(2) {
  animation-delay: 0.2s;
}

.conversation__dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes conversation-blink {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }
  40% {
    opacity: 1;
  }
}

/* Respect a visitor who asked the system for less motion. */
@media (prefers-reduced-motion: reduce) {
  .conversation__thread {
    scroll-behavior: auto;
  }

  .conversation__dot {
    animation: none;
    opacity: 0.6;
  }
}

.conversation__composer {
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
  flex-wrap: wrap;
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
  resize: none;
  /* Two lines at most before it scrolls: a composer that grows without limit
     pushes the conversation off screen. */
  max-height: 6rem;
}

.conversation__input:focus {
  outline: none;
  border-bottom: var(--input-border-focus);
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

/* With appearance: interaction-only the host stays empty on most visits, so it
   only claims space once Cloudflare actually puts a challenge in it. */
.conversation__challenge:not(:empty) {
  display: flex;
  justify-content: center;
  margin-top: 0.75rem;
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
