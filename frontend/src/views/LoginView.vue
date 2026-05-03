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
        <div class="auth-eyebrow">{{ $t('auth.login.eyebrow') }}</div>
        <h1 class="auth-title">{{ $t('auth.login.title') }}</h1>
        <p class="auth-subtitle">{{ $t('auth.login.subtitle') }}</p>

        <form class="auth-form" @submit.prevent="onSubmit" novalidate>
          <label class="auth-field">
            <span class="auth-field-label">{{ $t('auth.login.emailLabel') }}</span>
            <input
              v-model.trim="email"
              type="email"
              class="auth-input"
              :placeholder="$t('auth.login.emailPlaceholder')"
              :aria-label="$t('auth.login.emailLabel')"
              autocomplete="email"
              required
            />
          </label>

          <label class="auth-field">
            <span class="auth-field-label">{{ $t('auth.login.passwordLabel') }}</span>
            <input
              v-model="password"
              type="password"
              class="auth-input"
              :placeholder="$t('auth.login.passwordPlaceholder')"
              :aria-label="$t('auth.login.passwordLabel')"
              autocomplete="current-password"
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
            <span>{{ submitting ? $t('auth.login.submitting') : $t('auth.login.submit') }}</span>
            <span v-if="!submitting" class="material-symbols-outlined auth-cta-arrow" aria-hidden="true">arrow_forward</span>
          </button>
        </form>

        <p class="auth-footer">
          {{ $t('auth.login.signupHint') }}
          <router-link :to="{ name: 'Signup' }" class="auth-link">
            {{ $t('auth.login.signupLink') }}
          </router-link>
        </p>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const submitting = ref(false)
const errorMessage = ref('')

const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const canSubmit = computed(
  () => emailRe.test(email.value) && password.value.length >= 6
)

function localizeError(raw) {
  if (!raw) return t('auth.login.errors.generic')
  const lower = raw.toLowerCase()
  if (lower.includes('invalid login') || lower.includes('invalid credentials')) {
    return t('auth.login.errors.invalidCredentials')
  }
  if (lower.includes('email not confirmed')) {
    return t('auth.login.errors.emailNotConfirmed')
  }
  if (lower.includes('network') || lower.includes('failed to fetch')) {
    return t('auth.login.errors.network')
  }
  return raw
}

async function onSubmit() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const { error } = await auth.login(email.value, password.value)
    if (error) {
      errorMessage.value = localizeError(error)
      return
    }
    // Succès — redirection vers la cible demandée ou /client/dashboard.
    const redirectRaw = (route.query?.redirect || '').toString()
    const redirect = redirectRaw && redirectRaw.startsWith('/') ? redirectRaw : '/client/dashboard'
    router.push(redirect)
  } catch (err) {
    errorMessage.value = localizeError(err?.message || '')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   AUTH (Login + Signup) — palette Causse Warm Intelligence
   Tokens --wi-* exclusifs. Logical properties (inset-inline-*)
   pour préserver le RTL arabe. Mêmes tokens que QuoteView.
   ═══════════════════════════════════════════════════════════ */

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
  /* RTL : flèche miroir */
  transform: scaleX(1);
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
  max-width: 460px;
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

@media (max-width: 600px) {
  .auth-card {
    padding: var(--wi-space-lg) var(--wi-space-md);
  }
}
</style>
