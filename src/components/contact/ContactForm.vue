<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { translations, type Lang } from '@/i18n/translations'
import {
  type ContactFormData,
  type ContactValidationCode,
  type ContactValidationErrors,
  hasContactValidationErrors,
  submitContactForm,
  validateContactForm,
} from '@/utils/contact'

type SubmissionState = 'idle' | 'loading' | 'success' | 'error'

const currentLang = ref<Lang>('es')
const submissionState = ref<SubmissionState>('idle')
const formError = ref('')

const form = reactive<ContactFormData>({
  fullName: '',
  company: '',
  email: '',
  message: '',
  website: '',
})

const fieldErrors = reactive<ContactValidationErrors>({})

const contactCopy = computed(() => translations.contact[currentLang.value])
const formCopy = computed(() => contactCopy.value.form)

function syncLang(): void {
  currentLang.value = document.documentElement.lang === 'en' ? 'en' : 'es'
}

function handleLanguageChange(event: Event): void {
  const detail = (event as CustomEvent<{ lang?: Lang }>).detail
  currentLang.value = detail?.lang === 'en' ? 'en' : 'es'
}

function setFieldError(field: keyof ContactValidationErrors, code?: ContactValidationCode): void {
  if (code) {
    fieldErrors[field] = code
    return
  }

  delete fieldErrors[field]
}

function applyValidation(errors: ContactValidationErrors): void {
  setFieldError('fullName', errors.fullName)
  setFieldError('company', errors.company)
  setFieldError('email', errors.email)
  setFieldError('message', errors.message)
  setFieldError('website', errors.website)
}

function getFieldMessage(field: keyof ContactValidationErrors): string {
  const code = fieldErrors[field]
  return code ? formCopy.value.validation[code] : ''
}

function clearFeedback(): void {
  if (submissionState.value === 'success' || submissionState.value === 'error') {
    submissionState.value = 'idle'
  }

  formError.value = ''
}

function handleFieldInput(field: keyof ContactFormData): void {
  clearFeedback()
  setFieldError(field)
}

async function handleSubmit(): Promise<void> {
  clearFeedback()
  const validationErrors = validateContactForm(form)
  applyValidation(validationErrors)

  if (hasContactValidationErrors(validationErrors)) {
    submissionState.value = 'error'
    formError.value = formCopy.value.validationSummary
    return
  }

  submissionState.value = 'loading'

  try {
    await submitContactForm(form)
    form.fullName = ''
    form.company = ''
    form.email = ''
    form.message = ''
    form.website = ''
    applyValidation({})
    submissionState.value = 'success'
  } catch (error) {
    submissionState.value = 'error'
    formError.value = error instanceof Error ? error.message : formCopy.value.errorFallback
  }
}

onMounted(() => {
  syncLang()
  window.addEventListener('language-changed', handleLanguageChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('language-changed', handleLanguageChange)
})
</script>

<template>
  <form
    class="contact-form"
    novalidate
    @submit.prevent="handleSubmit"
  >
    <div class="contact-form__grid">
      <label class="contact-form__field">
        <span class="contact-form__label">{{ formCopy.fullNameLabel }}</span>
        <input
          v-model="form.fullName"
          class="contact-form__input"
          type="text"
          name="fullName"
          :placeholder="formCopy.fullNamePlaceholder"
          autocomplete="name"
          :aria-invalid="Boolean(fieldErrors.fullName)"
          :aria-describedby="fieldErrors.fullName ? 'contact-fullName-error' : undefined"
          @input="handleFieldInput('fullName')"
        >
        <span
          v-if="fieldErrors.fullName"
          id="contact-fullName-error"
          class="contact-form__error"
        >
          {{ getFieldMessage('fullName') }}
        </span>
      </label>

      <label class="contact-form__field">
        <span class="contact-form__label">{{ formCopy.companyLabel }}</span>
        <input
          v-model="form.company"
          class="contact-form__input"
          type="text"
          name="company"
          :placeholder="formCopy.companyPlaceholder"
          autocomplete="organization"
          :aria-invalid="Boolean(fieldErrors.company)"
          :aria-describedby="fieldErrors.company ? 'contact-company-error' : undefined"
          @input="handleFieldInput('company')"
        >
        <span
          v-if="fieldErrors.company"
          id="contact-company-error"
          class="contact-form__error"
        >
          {{ getFieldMessage('company') }}
        </span>
      </label>

      <label class="contact-form__field contact-form__field--full">
        <span class="contact-form__label">{{ formCopy.emailLabel }}</span>
        <input
          v-model="form.email"
          class="contact-form__input"
          type="email"
          name="email"
          :placeholder="formCopy.emailPlaceholder"
          autocomplete="email"
          :aria-invalid="Boolean(fieldErrors.email)"
          :aria-describedby="fieldErrors.email ? 'contact-email-error' : undefined"
          @input="handleFieldInput('email')"
        >
        <span
          v-if="fieldErrors.email"
          id="contact-email-error"
          class="contact-form__error"
        >
          {{ getFieldMessage('email') }}
        </span>
      </label>

      <label class="contact-form__field contact-form__field--full">
        <span class="contact-form__label">{{ formCopy.messageLabel }}</span>
        <textarea
          v-model="form.message"
          class="contact-form__input contact-form__textarea"
          name="message"
          rows="5"
          :placeholder="formCopy.messagePlaceholder"
          :aria-invalid="Boolean(fieldErrors.message)"
          :aria-describedby="fieldErrors.message ? 'contact-message-error' : undefined"
          @input="handleFieldInput('message')"
        />
        <span
          v-if="fieldErrors.message"
          id="contact-message-error"
          class="contact-form__error"
        >
          {{ getFieldMessage('message') }}
        </span>
      </label>

      <label
        class="contact-form__honeypot"
        aria-hidden="true"
      >
        <span>Website</span>
        <input
          v-model="form.website"
          type="text"
          name="website"
          tabindex="-1"
          autocomplete="off"
          @input="handleFieldInput('website')"
        >
      </label>
    </div>

    <div
      v-if="submissionState === 'success'"
      class="contact-form__feedback contact-form__feedback--success"
      role="status"
    >
      <p class="contact-form__feedback-title">
        {{ formCopy.successTitle }}
      </p>
      <p>{{ formCopy.successMessage }}</p>
    </div>

    <div
      v-else-if="submissionState === 'error' && formError"
      class="contact-form__feedback contact-form__feedback--error"
      role="alert"
    >
      <p class="contact-form__feedback-title">
        {{ formCopy.errorTitle }}
      </p>
      <p>{{ formError }}</p>
    </div>

    <div class="contact-form__footer">
      <p class="contact-form__privacy">
        {{ formCopy.privacyPrefix }}
        <a href="/privacy-policy">{{ formCopy.privacyLinkLabel }}</a>
      </p>

      <button
        class="contact-form__submit"
        type="submit"
        :disabled="submissionState === 'loading'"
      >
        {{ submissionState === 'loading' ? formCopy.submitLoading : formCopy.submitIdle }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.contact-form {
  width: 100%;
  padding: var(--space-12);
  background: linear-gradient(180deg, rgba(42, 42, 43, 0.34), rgba(28, 27, 28, 0.42));
  box-shadow:
    var(--shadow-ambient),
    inset 0 0 0 1px rgba(229, 226, 227, 0.08);
  text-align: left;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.contact-form__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-6);
}

.contact-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.contact-form__field--full {
  grid-column: 1 / -1;
}

.contact-form__label {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--color-text);
  text-transform: uppercase;
}

.contact-form__input {
  width: 100%;
  padding: var(--space-3) 0;
  font-family: var(--font-body);
  font-size: 1rem;
  color: var(--color-text);
  background: transparent;
  border: none;
  border-bottom: var(--input-border-bottom);
  outline: none;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.contact-form__input::placeholder {
  color: var(--color-text-muted);
  opacity: 0.8;
}

.contact-form__input:focus {
  border-bottom: var(--input-border-focus);
  box-shadow: 0px 4px 8px rgba(0, 240, 255, 0.12);
}

.contact-form__textarea {
  resize: vertical;
  min-height: 9rem;
}

.contact-form__error {
  font-size: 0.875rem;
  color: #ff7a7a;
}

.contact-form__honeypot {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.contact-form__feedback {
  margin-top: var(--space-8);
  padding: var(--space-6);
  background: rgba(28, 27, 28, 0.6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.contact-form__feedback--success {
  color: var(--color-primary);
}

.contact-form__feedback--error {
  color: #ff9b9b;
}

.contact-form__feedback-title {
  font-family: var(--font-display);
  font-size: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.contact-form__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  flex-wrap: wrap;
  margin-top: var(--space-8);
}

.contact-form__privacy {
  max-width: 36rem;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--color-text-muted);
}

.contact-form__privacy a {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.contact-form__submit {
  min-width: 15rem;
  padding: var(--space-4) var(--space-8);
  font-family: var(--font-display);
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--color-base);
  background: var(--btn-gradient);
  border: none;
  box-shadow: var(--btn-glow);
  cursor: pointer;
  transition:
    opacity var(--transition-fast),
    box-shadow var(--transition-fast);
}

.contact-form__submit:hover:enabled {
  opacity: 0.92;
  box-shadow: 0px 0px 16px var(--color-primary);
}

.contact-form__submit:disabled {
  opacity: 0.5;
  cursor: progress;
}

@media (max-width: 720px) {
  .contact-form {
    padding: var(--space-8);
  }

  .contact-form__grid {
    grid-template-columns: 1fr;
  }

  .contact-form__footer {
    align-items: stretch;
  }

  .contact-form__submit {
    width: 100%;
  }
}

</style>
