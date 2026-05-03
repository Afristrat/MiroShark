<template>
  <div class="auth-page">
    <header class="auth-topbar">
      <router-link
        to="/"
        class="auth-back"
        :title="$t('nav.homeTitle')"
      >
        <span class="auth-back-arrow material-symbols-outlined" aria-hidden="true">arrow_back</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
    </header>

    <main class="auth-main">
      <section class="auth-card">
        <div class="auth-eyebrow">{{ $t('auth.signup.eyebrow') }}</div>
        <h1 class="auth-title">{{ $t('auth.signup.title') }}</h1>
        <p class="auth-subtitle">{{ $t('auth.signup.subtitle') }}</p>

        <!-- État succès : message d'attente d'invitation org -->
        <div v-if="signedUp" class="auth-success" role="status">
          <div class="auth-success-icon">
            <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
          </div>
          <h2 class="auth-success-title">{{ $t('auth.signup.successTitle') }}</h2>
          <p class="auth-success-body">
            {{ needsConfirmation ? $t('auth.signup.successBodyConfirm') : $t('auth.signup.successBodyPending') }}
          </p>
          <router-link :to="{ name: 'Login' }" class="auth-cta auth-cta--inline">
            <span>{{ $t('auth.signup.backToLogin') }}</span>
            <span class="material-symbols-outlined auth-cta-arrow" aria-hidden="true">arrow_forward</span>
          </router-link>
        </div>

        <!-- État formulaire -->
        <form v-else class="auth-form" @submit.prevent="onSubmit" novalidate>
          <label class="auth-field">
            <span class="auth-field-label">
              {{ $t('auth.signup.fullNameLabel') }}
              <span class="auth-required" aria-hidden="true">*</span>
            </span>
            <input
              v-model.trim="fullName"
              type="text"
              class="auth-input"
              :placeholder="$t('auth.signup.fullNamePlaceholder')"
              :aria-label="$t('auth.signup.fullNameLabel')"
              autocomplete="name"
              required
            />
          </label>

          <label class="auth-field">
            <span class="auth-field-label">
              {{ $t('auth.signup.organizationLabel') }}
              <span class="auth-required" aria-hidden="true">*</span>
            </span>
            <input
              v-model.trim="organization"
              type="text"
              class="auth-input"
              :placeholder="$t('auth.signup.organizationPlaceholder')"
              :aria-label="$t('auth.signup.organizationLabel')"
              autocomplete="organization"
              required
            />
          </label>

          <label class="auth-field">
            <span class="auth-field-label">
              {{ $t('auth.signup.emailLabel') }}
              <span class="auth-required" aria-hidden="true">*</span>
            </span>
            <input
              v-model.trim="email"
              type="email"
              class="auth-input"
              :placeholder="$t('auth.signup.emailPlaceholder')"
              :aria-label="$t('auth.signup.emailLabel')"
              autocomplete="email"
              required
            />
          </label>

          <label class="auth-field">
            <span class="auth-field-label">
              {{ $t('auth.signup.passwordLabel') }}
              <span class="auth-required" aria-hidden="true">*</span>
            </span>
            <input
              v-model="password"
              type="password"
              class="auth-input"
              :placeholder="$t('auth.signup.passwordPlaceholder')"
              :aria-label="$t('auth.signup.passwordLabel')"
              autocomplete="new-password"
              minlength="8"
              required
            />
            <span class="auth-field-hint">{{ $t('auth.signup.passwordHint') }}</span>
          </label>

          <label class="auth-field">
            <span class="auth-field-label">
              {{ $t('auth.signup.confirmLabel') }}
              <span class="auth-required" aria-hidden="true">*</span>
            </span>
            <input
              v-model="confirmPassword"
              type="password"
              class="auth-input"
              :placeholder="$t('auth.signup.confirmPlaceholder')"
              :aria-label="$t('auth.signup.confirmLabel')"
              autocomplete="new-password"
              required
            />
          </label>

          <p v-if="errorMessage" class="auth-error" role="alert">
            <span class="material-symbols-outlined auth-error-icon" aria-hidden="true">error</span>
            <span>{{ errorMessage }}</span>
          </p>

          <button
            type="submit"
            class="auth-cta"
            :disabled="!canSubmit || submitting"
          >
            <span>{{ submitting ? $t('auth.signup.submitting') : $t('auth.signup.submit') }}</span>
            <span v-if="!submitting" class="material-symbols-outlined auth-cta-arrow" aria-hidden="true">arrow_forward</span>
          </button>
        </form>

        <p v-if="!signedUp" class="auth-footer">
          {{ $t('auth.signup.loginHint') }}
          <router-link :to="{ name: 'Login' }" class="auth-link">
            {{ $t('auth.signup.loginLink') }}
          </router-link>
        </p>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const fullName = ref('')
const organization = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const errorMessage = ref('')
const signedUp = ref(false)
const needsConfirmation = ref(false)

const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const passwordsMatch = computed(() => password.value === confirmPassword.value)

const canSubmit = computed(
  () =>
    fullName.value.length >= 2 &&
    organization.value.length >= 2 &&
    emailRe.test(email.value) &&
    password.value.length >= 8 &&
    passwordsMatch.value
)

function localizeError(raw) {
  if (!raw) return t('auth.signup.errors.generic')
  const lower = raw.toLowerCase()
  if (lower.includes('already registered') || lower.includes('user already')) {
    return t('auth.signup.errors.alreadyRegistered')
  }
  if (lower.includes('weak password') || lower.includes('password should')) {
    return t('auth.signup.errors.weakPassword')
  }
  if (lower.includes('invalid email')) {
    return t('auth.signup.errors.invalidEmail')
  }
  if (lower.includes('network') || lower.includes('failed to fetch')) {
    return t('auth.signup.errors.network')
  }
  return raw
}

async function onSubmit() {
  if (!canSubmit.value || submitting.value) return
  if (!passwordsMatch.value) {
    errorMessage.value = t('auth.signup.errors.passwordsMismatch')
    return
  }
  submitting.value = true
  errorMessage.value = ''
  try {
    const { error, needsConfirmation: nc } = await auth.signup(
      email.value,
      password.value,
      {
        full_name: fullName.value,
        organization_name: organization.value
      }
    )
    if (error) {
      errorMessage.value = localizeError(error)
      return
    }
    signedUp.value = true
    needsConfirmation.value = !!nc
  } catch (err) {
    errorMessage.value = localizeError(err?.message || '')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
/* Reprise des mêmes styles que LoginView (tokens --wi-*).
   Ajouts : champ "required" + variantes success. */

.auth-page {
  min-height: 100vh;
  background: var(--wi-bg);
  color: var(--wi-on-surface);
  font-family: var(--wi-font-body);
  font-size: 16px;
  line-height: 1.6;
  display: flex;
  flex-direction: column;
}

.auth-topbar {
  display: flex;
  align-items: center;
  padding-block: var(--wi-space-md);
  padding-inline: var(--wi-space-lg);
}

.auth-back {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 8px 12px;
  border-radius: var(--wi-radius-pill);
  transition: background 160ms ease, color 160ms ease;
}

.auth-back:hover {
  background: var(--wi-surface-container-low);
  color: var(--wi-primary);
}

.auth-back-arrow {
  font-size: 18px;
}

[dir='rtl'] .auth-back-arrow {
  transform: scaleX(-1);
}

.auth-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--wi-space-lg) var(--wi-space-md);
}

.auth-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-ambient);
  padding: var(--wi-space-xl) var(--wi-space-lg);
  max-width: 520px;
  width: 100%;
}

.auth-eyebrow {
  display: inline-block;
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--wi-primary);
  background: var(--wi-primary-container-soft);
  border: 1px solid var(--wi-primary-container-edge);
  border-radius: var(--wi-radius-pill);
  padding: 6px 14px;
  margin-block-end: var(--wi-space-sm);
}

.auth-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-surface);
  margin-block-end: 8px;
}

.auth-subtitle {
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  margin-block-end: var(--wi-space-md);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
}

.auth-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.auth-field-label {
  font-size: var(--wi-label-sm);
  font-weight: var(--wi-label-sm-weight);
  letter-spacing: var(--wi-label-sm-tracking);
  color: var(--wi-on-surface-variant);
}

.auth-required {
  color: var(--wi-error);
  margin-inline-start: 4px;
}

.auth-field-hint {
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  margin-block-start: 4px;
}

.auth-input {
  appearance: none;
  width: 100%;
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  padding: 12px 14px;
  font-family: inherit;
  font-size: var(--wi-body-md);
  line-height: 1.4;
  transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.auth-input::placeholder {
  color: var(--wi-on-surface-variant);
  opacity: 0.6;
}

.auth-input:focus {
  outline: none;
  border-color: var(--wi-primary);
  background: var(--wi-surface);
  box-shadow: 0 0 0 3px var(--wi-primary-container-soft);
}

.auth-error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
  border-radius: var(--wi-radius-md);
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.4;
}

.auth-error-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-block-start: 1px;
}

.auth-cta {
  appearance: none;
  border: none;
  margin-block-start: var(--wi-space-xs);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-md);
  font-weight: 600;
  letter-spacing: 0.02em;
  border-radius: var(--wi-radius-pill);
  padding: 14px 24px;
  cursor: pointer;
  text-decoration: none;
  transition: background 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.auth-cta:hover:not(:disabled) {
  background: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-md);
}

.auth-cta:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.auth-cta--inline {
  align-self: flex-start;
  margin-block-start: var(--wi-space-md);
}

.auth-cta-arrow {
  font-size: 20px;
}

[dir='rtl'] .auth-cta-arrow {
  transform: scaleX(-1);
}

.auth-footer {
  margin-block-start: var(--wi-space-md);
  text-align: center;
  font-size: 14px;
  color: var(--wi-on-surface-variant);
}

.auth-link {
  color: var(--wi-primary);
  font-weight: 600;
  text-decoration: none;
  margin-inline-start: 4px;
}

.auth-link:hover {
  text-decoration: underline;
}

/* ── Success state ────────────────────────────────────────── */
.auth-success {
  text-align: center;
  padding-block: var(--wi-space-md);
}

.auth-success-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
  margin-block-end: var(--wi-space-sm);
}

.auth-success-icon .material-symbols-outlined {
  font-size: 36px;
}

.auth-success-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin-block-end: 8px;
}

.auth-success-body {
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  line-height: 1.6;
  max-width: 420px;
  margin: 0 auto var(--wi-space-md);
}

@media (max-width: 600px) {
  .auth-card {
    padding: var(--wi-space-lg) var(--wi-space-md);
  }
}
</style>
