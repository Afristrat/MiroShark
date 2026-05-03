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

        <!-- US-096 — providers alternatifs : Google OAuth + Magic Link.
             Google : redirige vers le consent screen Google puis retour
             auto via Supabase. Magic Link : email avec lien à usage unique. -->
        <div class="auth-divider" role="separator" aria-hidden="true">
          <span class="auth-divider-line"></span>
          <span class="auth-divider-label">{{ $t('auth.login.orSeparator') }}</span>
          <span class="auth-divider-line"></span>
        </div>

        <div class="auth-providers">
          <button
            type="button"
            class="auth-provider auth-provider--google"
            :disabled="oauthLoading || magicLoading || submitting"
            @click="onGoogle"
          >
            <svg class="auth-provider-icon" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.49h4.84c-.21 1.13-.84 2.08-1.79 2.72v2.27h2.9c1.7-1.56 2.69-3.86 2.69-6.64z"/>
              <path fill="#34A853" d="M9 18c2.43 0 4.46-.81 5.94-2.18l-2.9-2.27c-.81.54-1.83.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H1.01v2.34A8.997 8.997 0 0 0 9 18z"/>
              <path fill="#FBBC05" d="M3.97 10.71A5.41 5.41 0 0 1 3.69 9c0-.59.1-1.16.27-1.71V4.96H1.01A8.997 8.997 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3.01-2.33z"/>
              <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A8.997 8.997 0 0 0 1.01 4.96l2.96 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
            </svg>
            <span>{{ oauthLoading ? $t('auth.login.providers.googleLoading') : $t('auth.login.providers.google') }}</span>
          </button>

          <button
            type="button"
            class="auth-provider auth-provider--magic"
            :disabled="oauthLoading || magicLoading || submitting || !emailRe.test(email)"
            @click="onMagicLink"
          >
            <span class="material-symbols-outlined auth-provider-icon" aria-hidden="true">link</span>
            <span>{{ magicLoading ? $t('auth.login.providers.magicLoading') : $t('auth.login.providers.magic') }}</span>
          </button>
        </div>

        <p v-if="magicSent" class="auth-magic-sent" role="status">
          <span class="material-symbols-outlined" aria-hidden="true">mark_email_read</span>
          <span>{{ $t('auth.login.providers.magicSent', { email: email }) }}</span>
        </p>

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
import { supabase } from '../lib/supabase'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const submitting = ref(false)
const oauthLoading = ref(false)
const magicLoading = ref(false)
const magicSent = ref(false)
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

// Compute la cible de redirection après auth (utilisée par OAuth + Magic Link)
function getRedirectTarget() {
  const redirectRaw = (route.query?.redirect || '').toString()
  const path = redirectRaw && redirectRaw.startsWith('/') ? redirectRaw : '/client/dashboard'
  return `${window.location.origin}${path}`
}

// US-096 — Google OAuth via Supabase
async function onGoogle() {
  if (oauthLoading.value) return
  oauthLoading.value = true
  errorMessage.value = ''
  try {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: getRedirectTarget(),
      }
    })
    if (error) {
      errorMessage.value = localizeError(error.message || '')
      oauthLoading.value = false
    }
    // Si succès : redirection navigateur vers Google → pas de finally
  } catch (err) {
    errorMessage.value = localizeError(err?.message || '')
    oauthLoading.value = false
  }
}

// US-096 — Magic Link via Supabase signInWithOtp
async function onMagicLink() {
  if (magicLoading.value || !emailRe.test(email.value)) return
  magicLoading.value = true
  errorMessage.value = ''
  magicSent.value = false
  try {
    const { error } = await supabase.auth.signInWithOtp({
      email: email.value,
      options: {
        emailRedirectTo: getRedirectTarget(),
        // Ne pas créer le user automatiquement si inexistant — on force le
        // signup explicite via /signup pour collecter nom + organisation.
        shouldCreateUser: false,
      }
    })
    if (error) {
      const msg = error.message || ''
      if (msg.toLowerCase().includes('signups not allowed') || msg.toLowerCase().includes('not found')) {
        errorMessage.value = t('auth.login.errors.unknownEmail')
      } else {
        errorMessage.value = localizeError(msg)
      }
    } else {
      magicSent.value = true
    }
  } catch (err) {
    errorMessage.value = localizeError(err?.message || '')
  } finally {
    magicLoading.value = false
  }
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

/* ── US-096 — Providers alternatifs (Google + Magic Link) ── */
.auth-divider {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
  margin-block: var(--wi-space-md) var(--wi-space-sm);
  color: var(--wi-on-surface-variant);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.auth-divider-line {
  flex: 1;
  height: 1px;
  background: var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
}

.auth-providers {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
}

.auth-provider {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  border: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.18));
  font-family: var(--wi-font-body);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, transform 80ms ease;
}

.auth-provider:hover:not(:disabled) {
  background: var(--wi-surface-container-low);
  border-color: var(--wi-primary);
}

.auth-provider:active:not(:disabled) {
  transform: translateY(1px);
}

.auth-provider:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.auth-provider-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.auth-provider--magic .auth-provider-icon {
  color: var(--wi-primary);
}

.auth-magic-sent {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-block-start: var(--wi-space-sm);
  padding: 10px 14px;
  border-radius: var(--wi-radius-md);
  background: var(--wi-secondary-container, color-mix(in srgb, var(--wi-secondary, #006D44) 12%, var(--wi-surface)));
  color: var(--wi-on-secondary-container, var(--wi-secondary, #006D44));
  font-size: 14px;
  font-weight: 500;
}

.auth-magic-sent .material-symbols-outlined {
  font-size: 18px;
}
</style>
