<template>
  <div class="quote-page">
    <!-- Top bar : retour vers /offres. LanguageSwitcher est mounté
         globalement par App.vue en widget flottant top-right. -->
    <header class="quote-topbar">
      <router-link
        :to="{ name: 'Offers' }"
        class="quote-back"
        :title="$t('quote.nav.backTitle')"
      >
        <span class="quote-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
    </header>

    <main class="quote-main">
      <!-- ───────────── Hero ───────────── -->
      <section class="quote-hero">
        <span class="quote-eyebrow">{{ $t('quote.eyebrow') }}</span>
        <h1 class="quote-headline">{{ $t('quote.hero.title') }}</h1>
        <p class="quote-sub">{{ $t('quote.hero.subtitle') }}</p>
      </section>

      <!-- ───────────── Stepper visuel ─────────────
           4 dots, l'étape courante en orange, les complétées en mint. -->
      <ol
        class="quote-stepper"
        :aria-label="$t('quote.stepper.step', { current: currentStep, total: 4 })"
      >
        <li
          v-for="i in 4"
          :key="i"
          class="quote-step-dot"
          :class="{
            'quote-step-dot--current': currentStep === i,
            'quote-step-dot--done': currentStep > i,
          }"
          :aria-current="currentStep === i ? 'step' : false"
        >
          <span class="quote-step-num">{{ i }}</span>
          <span class="quote-step-label">{{ stepLabel(i) }}</span>
        </li>
      </ol>

      <!-- ───────────── Form card ───────────── -->
      <section class="ms-card quote-card">
        <!-- Step 1 — coordonnées -->
        <form
          v-if="currentStep === 1"
          class="quote-form"
          @submit.prevent="goNext"
        >
          <h2 class="quote-form-title">{{ $t('quote.step1.title') }}</h2>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step1.fullName.label') }}
              <span class="quote-required">*</span>
            </span>
            <input
              v-model.trim="form.full_name"
              class="ms-input"
              type="text"
              maxlength="100"
              required
              :placeholder="$t('quote.step1.fullName.placeholder')"
            />
          </label>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step1.email.label') }}
              <span class="quote-required">*</span>
            </span>
            <input
              v-model.trim="form.email"
              class="ms-input"
              type="email"
              required
              :placeholder="$t('quote.step1.email.placeholder')"
              :aria-invalid="form.email && !emailValid ? 'true' : 'false'"
            />
            <span
              v-if="form.email && !emailValid"
              class="quote-field-error"
            >
              {{ $t('quote.step1.email.invalid') }}
            </span>
          </label>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step1.company.label') }}
              <span class="quote-required">*</span>
            </span>
            <input
              v-model.trim="form.company"
              class="ms-input"
              type="text"
              maxlength="120"
              required
              :placeholder="$t('quote.step1.company.placeholder')"
            />
          </label>

          <label class="quote-field">
            <span class="quote-field-label">{{ $t('quote.step1.role.label') }}</span>
            <input
              v-model.trim="form.role"
              class="ms-input"
              type="text"
              maxlength="80"
              :placeholder="$t('quote.step1.role.placeholder')"
            />
          </label>

          <label class="quote-field">
            <span class="quote-field-label">{{ $t('quote.step1.phone.label') }}</span>
            <input
              v-model.trim="form.phone"
              class="ms-input"
              type="tel"
              maxlength="40"
              :placeholder="$t('quote.step1.phone.placeholder')"
            />
          </label>

          <div class="quote-actions quote-actions--end">
            <button
              type="submit"
              class="ms-btn ms-btn-primary ms-btn--lg"
              :disabled="!step1Valid"
            >
              {{ $t('quote.actions.next') }}
            </button>
          </div>
        </form>

        <!-- Step 2 — besoin -->
        <form
          v-else-if="currentStep === 2"
          class="quote-form"
          @submit.prevent="goNext"
        >
          <h2 class="quote-form-title">{{ $t('quote.step2.title') }}</h2>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step2.package.label') }}
              <span class="quote-required">*</span>
            </span>
            <select v-model="form.package" class="ms-select" required>
              <option
                v-for="opt in packageOptions"
                :key="opt"
                :value="opt"
              >
                {{ $t(`quote.step2.package.options.${opt}`) }}
              </option>
            </select>
          </label>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step2.volume.label') }}
            </span>
            <input
              v-model.number="form.expected_simulations_per_year"
              class="ms-input"
              type="number"
              min="1"
              max="100"
              :placeholder="$t('quote.step2.volume.placeholder')"
            />
          </label>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step2.deadline.label') }}
            </span>
            <select v-model="form.target_deadline" class="ms-select">
              <option value="">—</option>
              <option
                v-for="opt in deadlineOptions"
                :key="opt"
                :value="opt"
              >
                {{ $t(`quote.step2.deadline.options.${opt}`) }}
              </option>
            </select>
          </label>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step2.industry.label') }}
            </span>
            <select v-model="form.industry" class="ms-select">
              <option value="">—</option>
              <option
                v-for="opt in industryOptions"
                :key="opt"
                :value="opt"
              >
                {{ $t(`quote.step2.industry.options.${opt}`) }}
              </option>
            </select>
          </label>

          <fieldset class="quote-field quote-fieldset">
            <legend class="quote-field-label">
              {{ $t('quote.step2.geoFocus.label') }}
            </legend>
            <p class="quote-field-help">{{ $t('quote.step2.geoFocus.help') }}</p>
            <div class="quote-checkbox-grid">
              <label
                v-for="opt in geoOptions"
                :key="opt"
                class="quote-checkbox"
              >
                <input
                  type="checkbox"
                  :value="opt"
                  v-model="form.geo_focus"
                />
                <span>{{ $t(`quote.step2.geoFocus.options.${opt}`) }}</span>
              </label>
            </div>
          </fieldset>

          <div class="quote-actions">
            <button
              type="button"
              class="ms-btn ms-btn-secondary ms-btn--lg"
              @click="goBack"
            >
              {{ $t('quote.actions.back') }}
            </button>
            <button
              type="submit"
              class="ms-btn ms-btn-primary ms-btn--lg"
              :disabled="!step2Valid"
            >
              {{ $t('quote.actions.next') }}
            </button>
          </div>
        </form>

        <!-- Step 3 — message + RGPD -->
        <form
          v-else-if="currentStep === 3"
          class="quote-form"
          @submit.prevent="submit"
        >
          <h2 class="quote-form-title">{{ $t('quote.step3.title') }}</h2>

          <label class="quote-field">
            <span class="quote-field-label">
              {{ $t('quote.step3.message.label') }}
            </span>
            <textarea
              v-model="form.message"
              class="ms-input quote-textarea"
              maxlength="800"
              rows="6"
              :placeholder="$t('quote.step3.message.placeholder')"
            ></textarea>
            <span class="quote-field-counter">
              {{ $t('quote.step3.message.counter', { count: messageLength }) }}
            </span>
          </label>

          <label class="quote-checkbox quote-consent">
            <input
              type="checkbox"
              v-model="form.consent_rgpd"
              required
            />
            <span>
              {{ $t('quote.step3.consent.label') }}
              <span class="quote-required">*</span>
            </span>
          </label>

          <div class="quote-actions">
            <button
              type="button"
              class="ms-btn ms-btn-secondary ms-btn--lg"
              @click="goBack"
              :disabled="submitting"
            >
              {{ $t('quote.actions.back') }}
            </button>
            <button
              type="submit"
              class="ms-btn ms-btn-primary ms-btn--lg"
              :disabled="!step3Valid || submitting"
            >
              {{ submitting ? $t('quote.actions.submitting') : $t('quote.actions.submit') }}
            </button>
          </div>
        </form>

        <!-- Step 4 — success / error -->
        <div v-else-if="currentStep === 4" class="quote-result">
          <template v-if="submitError === null">
            <div class="quote-result-card quote-result-card--success">
              <div class="quote-result-icon" aria-hidden="true">✓</div>
              <h2 class="quote-result-title">
                {{ $t('quote.step4.successTitle') }}
              </h2>
              <p class="quote-result-sub">
                {{ $t('quote.step4.successSubtitle') }}
              </p>
              <p v-if="quoteId" class="quote-result-id">
                <span class="quote-result-id-label">
                  {{ $t('quote.step4.quoteIdLabel') }}
                </span>
                <code class="quote-result-id-value ms-mono">{{ quoteId }}</code>
              </p>
              <div class="quote-actions quote-actions--center">
                <router-link
                  :to="{ name: 'Offers' }"
                  class="ms-btn ms-btn-primary ms-btn--lg"
                >
                  {{ $t('quote.step4.backToOffers') }}
                </router-link>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="quote-result-card quote-result-card--error">
              <div class="quote-result-icon quote-result-icon--error" aria-hidden="true">!</div>
              <h2 class="quote-result-title">
                {{ $t('quote.step4.errorTitle') }}
              </h2>
              <p class="quote-result-sub">
                {{ submitError }}
              </p>
              <div class="quote-actions quote-actions--center">
                <button
                  type="button"
                  class="ms-btn ms-btn-secondary ms-btn--lg"
                  @click="goBackToStep3"
                >
                  {{ $t('quote.step4.tryAgain') }}
                </button>
              </div>
            </div>
          </template>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { submitQuote } from '../api/quote'
import { formatApiError } from '../utils/error-handler'

// ─── Constantes (alignées sur le backend US-025) ────────────────────────
const packageOptions = [
  'crisis_drill_24h',
  'policy_brief_stress',
  'pre_launch_adcheck',
  'custom',
]
const deadlineOptions = ['not_urgent', '1_month', '2_weeks', 'this_week']
const industryOptions = [
  'banking', 'telecom', 'government', 'ngo', 'marketing', 'media', 'other',
]
const geoOptions = ['MA', 'DZ', 'TN', 'SN', 'CI', 'Other']

// ─── Mapping query ?package=… → id frontend OffersView vers id backend ──
// La page Offers émet `crisisDrill` / `policyBrief` / `preLaunch` (camelCase
// pour les clés i18n) — on traduit vers les ids backend canoniques utilisés
// dans le payload + l'enum OpenAPI.
const PACKAGE_ALIAS_MAP = {
  crisisDrill: 'crisis_drill_24h',
  policyBrief: 'policy_brief_stress',
  preLaunch: 'pre_launch_adcheck',
}

const route = useRoute()
const { t, locale } = useI18n()

const currentStep = ref(1)

const form = reactive({
  full_name: '',
  email: '',
  company: '',
  role: '',
  phone: '',
  package: 'crisis_drill_24h',
  expected_simulations_per_year: null,
  target_deadline: '',
  industry: '',
  geo_focus: [],
  message: '',
  consent_rgpd: false,
})

const submitting = ref(false)
const submitError = ref(null) // null = pas encore d'erreur (Step 4 = succès)
const quoteId = ref('')

// ─── Computed validations ──────────────────────────────────────────────
const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const emailValid = computed(() => emailRe.test(form.email))

const step1Valid = computed(
  () =>
    !!form.full_name &&
    !!form.email &&
    emailValid.value &&
    !!form.company,
)

const step2Valid = computed(
  () => !!form.package && packageOptions.includes(form.package),
)

const step3Valid = computed(() => form.consent_rgpd === true)

const messageLength = computed(() => (form.message || '').length)

// ─── Step labels du stepper ────────────────────────────────────────────
function stepLabel(idx) {
  const keys = ['contact', 'need', 'message', 'done']
  return t(`quote.stepper.stepNames.${keys[idx - 1]}`)
}

// ─── Navigation ────────────────────────────────────────────────────────
function goNext() {
  if (currentStep.value === 1 && !step1Valid.value) return
  if (currentStep.value === 2 && !step2Valid.value) return
  currentStep.value += 1
}

function goBack() {
  if (currentStep.value > 1) currentStep.value -= 1
}

function goBackToStep3() {
  // Réessayer après une erreur backend : on revient au Step 3 avec form
  // pré-rempli (jamais reset) pour que l'utilisateur ajuste s'il veut.
  submitError.value = null
  currentStep.value = 3
}

// ─── Submit ────────────────────────────────────────────────────────────
async function submit() {
  if (!step3Valid.value || submitting.value) return
  submitting.value = true
  submitError.value = null

  // Construction du payload — on ne passe que les champs renseignés
  // pour ne pas pousser des chaînes vides au backend.
  const payload = {
    full_name: form.full_name,
    email: form.email,
    company: form.company,
    package: form.package,
    consent_rgpd: form.consent_rgpd,
    locale: locale.value || 'fr',
  }
  if (form.role) payload.role = form.role
  if (form.phone) payload.phone = form.phone
  if (
    form.expected_simulations_per_year !== null &&
    form.expected_simulations_per_year !== ''
  ) {
    payload.expected_simulations_per_year = Number(
      form.expected_simulations_per_year,
    )
  }
  if (form.target_deadline) payload.target_deadline = form.target_deadline
  if (form.industry) payload.industry = form.industry
  if (form.geo_focus && form.geo_focus.length) {
    payload.geo_focus = [...form.geo_focus]
  }
  if (form.message) payload.message = form.message

  try {
    const res = await submitQuote(payload)
    quoteId.value = (res && res.data && res.data.quote_id) || ''
    submitError.value = null
    currentStep.value = 4
  } catch (err) {
    // formatApiError gère error_code → traduction errors.* + fallback msg.
    const localised = formatApiError(err, t)
    submitError.value = localised || t('quote.step4.errorFallback')
    currentStep.value = 4
  } finally {
    submitting.value = false
  }
}

// ─── Préselection package depuis ?package=… ────────────────────────────
onMounted(() => {
  const raw = (route.query?.package || '').toString().trim()
  if (!raw) return
  const candidate = PACKAGE_ALIAS_MAP[raw] || raw
  if (packageOptions.includes(candidate)) {
    form.package = candidate
  }
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   QUOTE — Direction Playful & Soft (US-025)
   ═══════════════════════════════════════════════════════════
   RTL : tous les positionnements logiques (inset-inline-*,
   margin-inline-*, padding-inline-*). Pas de left/right physique. */

.quote-page {
  min-height: 100vh;
  background: var(--ms-bg);
  color: var(--ms-text);
  font-family: var(--ms-font-body);
}

/* ── Top bar ────────────────────────────────────────── */
.quote-topbar {
  display: flex;
  align-items: center;
  padding: var(--ms-space-4) var(--ms-space-6);
  /* Réserve la place pour le LanguageSwitcher floating top-right
     (z-index 1500, top:12px). Cohérent avec OffersView / CalibrationView. */
  padding-inline-end: 110px;
  border-bottom: 1px solid var(--ms-border);
  background: var(--ms-bg);
}

.quote-back {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  font-family: var(--ms-font-display);
  font-weight: 600;
  font-size: var(--ms-text-sm);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ms-text);
  text-decoration: none;
  padding: 6px 10px;
  border-radius: var(--ms-radius-pill);
  transition: color var(--ms-transition), background var(--ms-transition);
}
.quote-back:hover {
  color: var(--ms-orange);
  background: var(--ms-bg-muted);
}
.quote-back-arrow {
  font-size: 16px;
  line-height: 1;
}
[dir="rtl"] .quote-back-arrow {
  transform: scaleX(-1);
}

/* ── Main wrapper ───────────────────────────────────── */
.quote-main {
  max-width: 760px;
  margin: 0 auto;
  padding: var(--ms-space-12) var(--ms-space-6);
}

/* ── Hero ───────────────────────────────────────────── */
.quote-hero {
  text-align: center;
  margin-bottom: var(--ms-space-8);
}

.quote-eyebrow {
  display: inline-block;
  font-family: var(--ms-font-mono);
  font-size: var(--ms-text-xs);
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ms-orange);
  background: var(--ms-orange-soft);
  padding: 6px 14px;
  border-radius: var(--ms-radius-pill);
  margin-bottom: var(--ms-space-4);
}

.quote-headline {
  font-family: var(--ms-font-display);
  font-size: clamp(26px, 4vw, 38px);
  font-weight: 700;
  line-height: 1.18;
  letter-spacing: -0.02em;
  color: var(--ms-text);
  margin: 0 auto var(--ms-space-4) auto;
  max-width: 640px;
}

.quote-sub {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-base);
  line-height: 1.55;
  color: var(--ms-text-muted);
  max-width: 560px;
  margin: 0 auto;
}

/* ── Stepper ────────────────────────────────────────── */
.quote-stepper {
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ms-space-2);
  padding: 0;
  margin: 0 0 var(--ms-space-6) 0;
  position: relative;
}

.quote-step-dot {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  position: relative;
  font-family: var(--ms-font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ms-text-muted);
}
.quote-step-dot::before {
  content: '';
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--ms-bg-muted);
  border: 2px solid var(--ms-border);
  position: relative;
  z-index: 2;
  transition: background var(--ms-transition), border-color var(--ms-transition);
}
.quote-step-dot:not(:last-child)::after {
  /* Connecteur entre dots — barre logique pour rester RTL-safe. */
  content: '';
  position: absolute;
  top: 13px;
  inset-inline-start: 50%;
  width: 100%;
  height: 2px;
  background: var(--ms-border);
  z-index: 1;
}
.quote-step-num {
  position: absolute;
  top: 4px;
  font-family: var(--ms-font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--ms-text-muted);
  z-index: 3;
}
.quote-step-label {
  margin-top: 2px;
}
.quote-step-dot--current::before {
  background: var(--ms-orange);
  border-color: var(--ms-orange);
}
.quote-step-dot--current .quote-step-num {
  color: var(--ms-text-on-color, #fff);
}
.quote-step-dot--current {
  color: var(--ms-orange);
}
.quote-step-dot--done::before {
  background: var(--ms-mint, #5fc8a8);
  border-color: var(--ms-mint, #5fc8a8);
}
.quote-step-dot--done .quote-step-num {
  color: var(--ms-text-on-color, #fff);
}
.quote-step-dot--done:not(:last-child)::after {
  background: var(--ms-mint, #5fc8a8);
}

/* ── Form card ──────────────────────────────────────── */
.quote-card {
  padding: var(--ms-space-8) var(--ms-space-6);
  border-radius: var(--ms-radius-lg);
}

.quote-form {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-5);
}

.quote-form-title {
  font-family: var(--ms-font-display);
  font-size: var(--ms-text-xl);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ms-text);
  margin: 0 0 var(--ms-space-2) 0;
}

.quote-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quote-fieldset {
  border: none;
  padding: 0;
  margin: 0;
}

.quote-field-label {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ms-text-muted);
}

.quote-required {
  color: var(--ms-orange);
  margin-inline-start: 2px;
}

.quote-field-help {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-xs);
  color: var(--ms-text-subtle);
  margin: 0;
}

.quote-field-counter {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--ms-text-subtle);
  align-self: flex-end;
}

.quote-field-error {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-xs);
  color: var(--ms-rose, #d4564b);
}

.quote-textarea {
  resize: vertical;
  min-height: 120px;
  font-family: var(--ms-font-body);
}

/* ── Checkbox grid (geo focus) ─────────────────────── */
.quote-checkbox-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ms-space-2);
  margin-top: var(--ms-space-2);
}
@media (min-width: 540px) {
  .quote-checkbox-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.quote-checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-sm);
  color: var(--ms-text);
  cursor: pointer;
}
.quote-checkbox input[type='checkbox'] {
  /* Les inputs natifs gèrent l'état RTL automatiquement (mirroring CSS). */
  accent-color: var(--ms-orange);
  width: 16px;
  height: 16px;
}

.quote-consent {
  align-items: flex-start;
  gap: var(--ms-space-2);
  background: var(--ms-bg-muted);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: var(--ms-space-3) var(--ms-space-4);
  font-size: var(--ms-text-sm);
  line-height: 1.5;
}
.quote-consent input[type='checkbox'] {
  margin-top: 3px;
}

/* ── Actions row ────────────────────────────────────── */
.quote-actions {
  display: flex;
  justify-content: space-between;
  gap: var(--ms-space-3);
  margin-top: var(--ms-space-3);
}
.quote-actions--end {
  justify-content: flex-end;
}
.quote-actions--center {
  justify-content: center;
}

/* ── Result card (Step 4) ───────────────────────────── */
.quote-result {
  display: flex;
  justify-content: center;
}

.quote-result-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--ms-space-3);
  padding: var(--ms-space-8) var(--ms-space-6);
  border-radius: var(--ms-radius-lg);
  border: 1px solid transparent;
  width: 100%;
  max-width: 520px;
}

.quote-result-card--success {
  background: rgba(95, 200, 168, 0.08);
  border-color: var(--ms-mint, #5fc8a8);
}

.quote-result-card--error {
  background: rgba(212, 86, 75, 0.08);
  border-color: var(--ms-rose, #d4564b);
}

.quote-result-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--ms-font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--ms-text-on-color, #fff);
  background: var(--ms-mint, #5fc8a8);
  margin-bottom: var(--ms-space-2);
}
.quote-result-icon--error {
  background: var(--ms-rose, #d4564b);
}

.quote-result-title {
  font-family: var(--ms-font-display);
  font-size: var(--ms-text-2xl);
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--ms-text);
}

.quote-result-sub {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-base);
  line-height: 1.55;
  color: var(--ms-text-muted);
  margin: 0;
  max-width: 420px;
}

.quote-result-id {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  margin: var(--ms-space-2) 0;
  font-size: var(--ms-text-xs);
  color: var(--ms-text-muted);
}
.quote-result-id-label {
  font-family: var(--ms-font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.quote-result-id-value {
  background: var(--ms-bg-muted);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-sm);
  padding: 2px 8px;
  font-size: 12px;
}

/* ── Mobile tweaks (< 768 px) ───────────────────────── */
@media (max-width: 767px) {
  .quote-main {
    padding: var(--ms-space-6) var(--ms-space-4);
  }
  .quote-card {
    padding: var(--ms-space-6) var(--ms-space-4);
  }
  .quote-step-label {
    font-size: 9px;
    letter-spacing: 0.04em;
  }
}
</style>
