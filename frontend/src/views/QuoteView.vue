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
        <span class="quote-back-arrow material-symbols-outlined" aria-hidden="true">arrow_back</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
    </header>

    <main class="quote-main">
      <!-- ───────────── Trust banner top (gris doux) ───────────── -->
      <div class="quote-trust-banner">
        <span class="material-symbols-outlined quote-trust-banner-icon" aria-hidden="true">verified_user</span>
        <span>{{ $t('quote.trustBanner') }}</span>
      </div>

      <!-- ───────────── Card centrée (parcours 3 temps A1-A8) ───────────── -->
      <section class="quote-card">
        <!-- Stepper 3 temps -->
        <ol
          class="quote-stepper"
          :aria-label="$t('quote.stepper.step', { current: Math.min(currentStep, 3), total: 3 })"
        >
          <li class="quote-stepper-line" aria-hidden="true"></li>
          <li
            v-for="i in 3"
            :key="i"
            class="quote-step"
            :class="{
              'quote-step--current': currentStep === i,
              'quote-step--done': currentStep > i,
            }"
            :aria-current="currentStep === i ? 'step' : false"
          >
            <span class="quote-step-circle">
              <span v-if="currentStep > i" class="material-symbols-outlined quote-step-check" aria-hidden="true">check</span>
              <span v-else>{{ i }}</span>
            </span>
            <span class="quote-step-label">{{ stepLabel(i) }}</span>
          </li>
        </ol>

        <!-- ───── Temps 1 — La décision (A1-A3) ───── -->
        <form
          v-if="currentStep === 1"
          class="quote-step-content"
          @submit.prevent="goToStep2"
        >
          <h2 class="quote-step-title">{{ $t('quote.temps1.title') }}</h2>
          <p class="quote-step-subtitle">{{ $t('quote.temps1.intro') }}</p>
          <p class="quote-reciprocity">{{ $t('quote.reciprocity.decision') }}</p>

          <label class="quote-field-stitch">
            <span class="quote-field-stitch-label">
              {{ $t('quote.temps1.a1.label') }}
              <span class="quote-required">*</span>
            </span>
            <textarea
              v-model.trim="form.a1_decision"
              class="quote-input-stitch quote-textarea"
              rows="2"
              maxlength="500"
              :placeholder="$t('quote.temps1.a1.placeholder')"
            ></textarea>
            <span class="quote-field-hint">{{ $t('quote.temps1.a1.hint') }}</span>
            <span v-if="form.a1_decision && !a1Valid" class="quote-field-error">
              {{ $t('quote.temps1.a1.invalid') }}
            </span>
          </label>

          <div class="quote-field-stitch">
            <span class="quote-field-stitch-label">
              {{ $t('quote.temps1.a2.label') }}
              <span class="quote-required">*</span>
            </span>
            <div
              v-for="(_opt, idx) in form.a2_options"
              :key="idx"
              class="quote-option-row"
            >
              <input
                v-model.trim="form.a2_options[idx]"
                type="text"
                class="quote-input-stitch"
                maxlength="200"
                :placeholder="$t('quote.temps1.a2.placeholder')"
              />
              <button
                v-if="form.a2_options.length > 2"
                type="button"
                class="quote-option-remove"
                :aria-label="$t('quote.temps1.a2.removeOption')"
                @click="removeOption(idx)"
              >
                <span class="material-symbols-outlined" aria-hidden="true">close</span>
              </button>
            </div>
            <button
              v-if="form.a2_options.length < 4"
              type="button"
              class="quote-secondary-btn quote-option-add"
              @click="addOption"
            >
              <span class="material-symbols-outlined" aria-hidden="true">add</span>
              {{ $t('quote.temps1.a2.addOption') }}
            </button>
            <span v-if="!a2Valid && a2Touched" class="quote-field-error">
              {{ $t('quote.temps1.a2.invalid') }}
            </span>
          </div>

          <div class="quote-field-row">
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">{{ $t('quote.temps1.a3.deadlineLabel') }}</span>
              <input
                v-model="form.a3_deadline_date"
                type="date"
                class="quote-input-stitch"
                :disabled="form.a3_overdue"
              />
            </label>
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">{{ $t('quote.temps1.a3.governanceLabel') }}</span>
              <select v-model="form.a3_governance" class="quote-input-stitch quote-select">
                <option value="">—</option>
                <option v-for="opt in governanceOptions" :key="opt" :value="opt">
                  {{ $t(`quote.temps1.a3.governance.${opt}`) }}
                </option>
              </select>
            </label>
          </div>

          <label class="quote-checkbox-inline">
            <input v-model="form.a3_overdue" type="checkbox" />
            <span>{{ $t('quote.temps1.a3.overdueLabel') }}</span>
          </label>

          <button type="submit" class="quote-cta" :disabled="!temps1Valid">
            <span>{{ $t('quote.actions.next') }}</span>
            <span class="material-symbols-outlined quote-cta-arrow" aria-hidden="true">arrow_forward</span>
          </button>
        </form>

        <!-- ───── Temps 2 — Le passé (A4-A5) ───── -->
        <form
          v-else-if="currentStep === 2"
          class="quote-step-content"
          @submit.prevent="goToStep3"
        >
          <h2 class="quote-step-title">{{ $t('quote.temps2.title') }}</h2>
          <p class="quote-step-subtitle">{{ $t('quote.temps2.intro') }}</p>
          <p class="quote-reciprocity">{{ $t('quote.reciprocity.past') }}</p>

          <div class="quote-field-stitch">
            <span class="quote-field-stitch-label">{{ $t('quote.temps2.a4.label') }}</span>
            <div class="quote-checkbox-group">
              <label
                v-for="opt in pastMethodOptions"
                :key="opt"
                class="quote-checkbox-chip"
                :class="{ 'quote-checkbox-chip--checked': form.a4_past_method.includes(opt) }"
              >
                <input
                  type="checkbox"
                  :checked="form.a4_past_method.includes(opt)"
                  @change="toggleInArray(form.a4_past_method, opt)"
                />
                <span>{{ $t(`quote.temps2.a4.options.${opt}`) }}</span>
              </label>
            </div>
          </div>

          <label class="quote-field-stitch">
            <span class="quote-field-stitch-label">{{ $t('quote.temps2.a5.label') }}</span>
            <textarea
              v-model.trim="form.a5_past_gap"
              class="quote-input-stitch quote-textarea"
              rows="2"
              maxlength="500"
              :placeholder="$t('quote.temps2.a5.placeholder')"
            ></textarea>
          </label>

          <div class="quote-actions-row">
            <button type="button" class="quote-secondary-btn" @click="goBack">
              {{ $t('quote.actions.back') }}
            </button>
            <button type="submit" class="quote-cta quote-cta--inline">
              <span>{{ $t('quote.actions.next') }}</span>
              <span class="material-symbols-outlined quote-cta-arrow" aria-hidden="true">arrow_forward</span>
            </button>
          </div>
        </form>

        <!-- ───── Temps 3 — L'enjeu et la matière (A6-A8) + identité ───── -->
        <form
          v-else-if="currentStep === 3"
          class="quote-step-content"
          @submit.prevent="submit"
        >
          <h2 class="quote-step-title">{{ $t('quote.temps3.title') }}</h2>
          <p class="quote-step-subtitle">{{ $t('quote.temps3.intro') }}</p>
          <p class="quote-reciprocity">{{ $t('quote.reciprocity.stakes') }}</p>

          <div class="quote-field-row">
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">{{ $t('quote.temps3.a6.budgetLabel') }}</span>
              <select v-model="form.a6_budget_bracket" class="quote-input-stitch quote-select">
                <option value="">—</option>
                <option v-for="opt in budgetOptions" :key="opt" :value="opt">
                  {{ $t(`quote.temps3.a6.budget.${opt}`) }}
                </option>
              </select>
            </label>
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">{{ $t('quote.temps3.a6.exposureLabel') }}</span>
              <select v-model="form.a6_exposure" class="quote-input-stitch quote-select">
                <option value="">—</option>
                <option v-for="opt in exposureOptions" :key="opt" :value="opt">
                  {{ $t(`quote.temps3.a6.exposure.${opt}`) }}
                </option>
              </select>
            </label>
          </div>

          <label class="quote-field-stitch">
            <span class="quote-field-stitch-label">{{ $t('quote.temps3.a6.jobsLabel') }}</span>
            <input
              v-model.number="form.a6_jobs"
              type="number"
              min="0"
              class="quote-input-stitch"
            />
          </label>

          <div class="quote-field-stitch">
            <span class="quote-field-stitch-label">
              {{ $t('quote.temps3.a7.countriesLabel') }}
              <span class="quote-required">*</span>
            </span>
            <div class="quote-checkbox-group">
              <label
                v-for="opt in countryOptions"
                :key="opt"
                class="quote-checkbox-chip"
                :class="{ 'quote-checkbox-chip--checked': form.a7_countries.includes(opt) }"
              >
                <input
                  type="checkbox"
                  :checked="form.a7_countries.includes(opt)"
                  @change="toggleInArray(form.a7_countries, opt)"
                />
                <span>{{ $t(`quote.temps3.a7.countries.${opt}`) }}</span>
              </label>
            </div>
          </div>

          <label class="quote-field-stitch">
            <span class="quote-field-stitch-label">
              {{ $t('quote.temps3.a7.segmentLabel') }}
              <span class="quote-required">*</span>
            </span>
            <input
              v-model.trim="form.a7_segment"
              type="text"
              class="quote-input-stitch"
              maxlength="200"
              :placeholder="$t('quote.temps3.a7.segmentPlaceholder')"
            />
            <span v-if="!a7Valid && a7Touched" class="quote-field-error">
              {{ $t('quote.temps3.a7.invalid') }}
            </span>
          </label>

          <div class="quote-field-stitch">
            <span class="quote-field-stitch-label">{{ $t('quote.temps3.a8.label') }}</span>
            <div class="quote-checkbox-group">
              <label
                v-for="opt in dataAssetOptions"
                :key="opt"
                class="quote-checkbox-chip"
                :class="{ 'quote-checkbox-chip--checked': form.a8_data_assets.includes(opt) }"
              >
                <input
                  type="checkbox"
                  :checked="form.a8_data_assets.includes(opt)"
                  @change="toggleInArray(form.a8_data_assets, opt)"
                />
                <span>{{ $t(`quote.temps3.a8.options.${opt}`) }}</span>
              </label>
            </div>
          </div>

          <hr class="quote-divider" />
          <p class="quote-step-subtitle">{{ $t('quote.temps3.identityIntro') }}</p>

          <div class="quote-field-row">
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">
                {{ $t('quote.temps3.identity.fullName.label') }}
                <span class="quote-required">*</span>
              </span>
              <input
                v-model.trim="form.full_name"
                type="text"
                class="quote-input-stitch"
                maxlength="100"
                dir="ltr"
                :placeholder="$t('quote.temps3.identity.fullName.placeholder')"
              />
            </label>

            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">
                {{ $t('quote.temps3.identity.email.label') }}
                <span class="quote-required">*</span>
              </span>
              <input
                v-model.trim="form.email"
                type="email"
                class="quote-input-stitch"
                dir="ltr"
                :placeholder="$t('quote.temps3.identity.email.placeholder')"
                :aria-invalid="form.email && !emailValid ? 'true' : 'false'"
              />
              <span v-if="form.email && !emailValid" class="quote-field-error">
                {{ $t('quote.temps3.identity.email.invalid') }}
              </span>
            </label>
          </div>

          <div class="quote-field-row">
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">
                {{ $t('quote.temps3.identity.company.label') }}
                <span class="quote-required">*</span>
              </span>
              <input
                v-model.trim="form.company"
                type="text"
                class="quote-input-stitch"
                maxlength="120"
                :placeholder="$t('quote.temps3.identity.company.placeholder')"
              />
            </label>

            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">{{ $t('quote.temps3.identity.role.label') }}</span>
              <input
                v-model.trim="form.role"
                type="text"
                class="quote-input-stitch"
                maxlength="80"
                :placeholder="$t('quote.temps3.identity.role.placeholder')"
              />
            </label>
          </div>

          <label class="quote-consent-stitch">
            <input v-model="form.consent_rgpd" type="checkbox" required />
            <span>
              {{ $t('quote.temps3.identity.consent.label') }}
              <span class="quote-required">*</span>
            </span>
          </label>

          <div class="quote-actions-row">
            <button
              type="button"
              class="quote-secondary-btn"
              @click="goBack"
              :disabled="submitting"
            >
              {{ $t('quote.actions.back') }}
            </button>
            <button
              type="submit"
              class="quote-cta quote-cta--inline"
              :disabled="!temps3Valid || submitting"
            >
              <span>{{ submitting ? $t('quote.actions.submitting') : $t('quote.actions.submit') }}</span>
              <span v-if="!submitting" class="material-symbols-outlined quote-cta-arrow" aria-hidden="true">arrow_forward</span>
            </button>
          </div>
        </form>

        <!-- ───── Confirmation (succès / erreur) ───── -->
        <div v-else-if="currentStep === 4" class="quote-step-content">
          <template v-if="submitError === null">
            <div class="quote-success">
              <div class="quote-success-icon">
                <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
              </div>
              <h2 class="quote-step-title">{{ $t('quote.step3.successTitle') }}</h2>
              <p class="quote-success-sub">{{ $t('quote.step3.successSubtitle') }}</p>
              <p v-if="quoteId" class="quote-success-id">
                <span class="quote-success-id-label">{{ $t('quote.step3.quoteIdLabel') }}</span>
                <code class="quote-success-id-value">{{ quoteId }}</code>
              </p>
              <router-link :to="{ name: 'Offers' }" class="quote-cta quote-cta--inline">
                {{ $t('quote.step3.backToOffers') }}
              </router-link>
            </div>
          </template>
          <template v-else>
            <div class="quote-error">
              <div class="quote-error-icon">
                <span class="material-symbols-outlined" aria-hidden="true">error</span>
              </div>
              <h2 class="quote-step-title">{{ $t('quote.step3.errorTitle') }}</h2>
              <p class="quote-success-sub">{{ submitError }}</p>
              <button type="button" class="quote-secondary-btn" @click="goBackToRetry">
                {{ $t('quote.step3.tryAgain') }}
              </button>
            </div>
          </template>
        </div>
      </section>

      <!-- ───────────── Trust signals (3 colonnes) ───────────── -->
      <section class="quote-trust-grid" aria-label="Trust signals">
        <div v-for="item in trustItems" :key="item.id" class="quote-trust-item">
          <span class="material-symbols-outlined quote-trust-item-icon" aria-hidden="true">{{ item.icon }}</span>
          <h5 class="quote-trust-item-title">{{ $t(`quote.trustSignals.${item.id}.title`) }}</h5>
          <p class="quote-trust-item-body">{{ $t(`quote.trustSignals.${item.id}.body`) }}</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { startIntakeSession, submitIntakeForm } from '../api/intake'
import { formatApiError } from '../utils/error-handler'

// ─── Parcours structuré « 3 temps » A1-A8 (US-IQ-01) ────────────────────
// Remplace l'ancien formulaire plat (situation + coordonnées) qui ne
// capturait aucun contexte de décision (incident q_f767321b, 2026-07-09).
// Étape 3 (l'enjeu et la matière) porte aussi l'identité — inchangée
// depuis toujours (docs/intake/07-legal §2) — car c'est l'écran de
// soumission qui crée effectivement le devis.

const governanceOptions = ['solo', 'comite_direction', 'conseil_administration', 'tutelle', 'investisseurs']
const pastMethodOptions = ['etude', 'conseil', 'sondage_interne', 'instinct', 'rien']
const budgetOptions = ['lt_1m', '1_10m', '10_100m', 'gt_100m']
const exposureOptions = ['interne', 'sectorielle', 'nationale', 'internationale']
const countryOptions = ['MA', 'DZ', 'TN', 'SN', 'CI', 'Other']
const dataAssetOptions = ['etudes', 'donnees_clients', 'verbatims', 'rien']

// Trust signals sous le form (3 colonnes) — inchangé.
const trustItems = [
  { id: 'multiAgent', icon: 'psychology' },
  { id: 'airGapped', icon: 'security' },
  { id: 'fastSetup', icon: 'bolt' },
]

const { t, locale } = useI18n()

const currentStep = ref(1)

const form = reactive({
  // Temps 1 — la décision (A1-A3)
  a1_decision: '',
  a2_options: ['', ''],
  a3_deadline_date: '',
  a3_overdue: false,
  a3_governance: '',
  // Temps 2 — le passé (A4-A5)
  a4_past_method: [],
  a5_past_gap: '',
  // Temps 3 — l'enjeu et la matière (A6-A8)
  a6_budget_bracket: '',
  a6_jobs: '',
  a6_exposure: '',
  a7_countries: [],
  a7_segment: '',
  a8_data_assets: [],
  // Identité (inchangée) — capturée sur l'écran de soumission.
  full_name: '',
  email: '',
  company: '',
  role: '',
  consent_rgpd: false,
})

const submitting = ref(false)
const submitError = ref(null) // null = succès, string = message d'erreur
const quoteId = ref('')
const a2Touched = ref(false)
const a7Touched = ref(false)

// ─── Validations — seuls A1/A2/A7 sont bloquants (AC US-IQ-01) ─────────
const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const emailValid = computed(() => emailRe.test(form.email))

const a1Valid = computed(() => form.a1_decision.trim().length >= 15)
const a2Valid = computed(() => form.a2_options.filter((o) => o.trim()).length >= 2)
const a7Valid = computed(() => form.a7_countries.length > 0 && form.a7_segment.trim().length > 0)

const temps1Valid = computed(() => a1Valid.value && a2Valid.value)
const temps3Valid = computed(
  () =>
    a7Valid.value &&
    !!form.full_name.trim() &&
    !!form.email.trim() &&
    emailValid.value &&
    !!form.company.trim() &&
    form.consent_rgpd === true,
)

// ─── Step labels (stepper) ───────────────────────────────────────────
function stepLabel(idx) {
  const keys = ['decision', 'past', 'stakes']
  return t(`quote.stepper.stepNames.${keys[idx - 1]}`)
}

// ─── Helpers champs dynamiques ────────────────────────────────────────
function addOption() {
  if (form.a2_options.length < 4) form.a2_options.push('')
}
function removeOption(idx) {
  if (form.a2_options.length > 2) form.a2_options.splice(idx, 1)
}
function toggleInArray(arr, val) {
  const idx = arr.indexOf(val)
  if (idx === -1) arr.push(val)
  else arr.splice(idx, 1)
}

// ─── Navigation ────────────────────────────────────────────────────────
function goToStep2() {
  a2Touched.value = true
  if (!temps1Valid.value) return
  currentStep.value = 2
}
function goToStep3() {
  currentStep.value = 3
}
function goBack() {
  if (currentStep.value > 1) currentStep.value -= 1
}
function goBackToRetry() {
  submitError.value = null
  currentStep.value = 3
}

// ─── Submit — démarre une session puis soumet le formulaire A1-A8 ─────
async function submit() {
  a7Touched.value = true
  if (!temps3Valid.value || submitting.value) return
  submitting.value = true
  submitError.value = null

  const brief = {
    decision: form.a1_decision.trim(),
    options: form.a2_options.map((o) => o.trim()).filter(Boolean),
    deadline: { date: form.a3_deadline_date || null, overdue: form.a3_overdue },
    governance: form.a3_governance || null,
    past_method: form.a4_past_method,
    past_gap: form.a5_past_gap.trim() || null,
    stakes:
      form.a6_budget_bracket && form.a6_exposure
        ? {
            budget_bracket: form.a6_budget_bracket,
            jobs: form.a6_jobs !== '' && form.a6_jobs !== null ? Number(form.a6_jobs) : null,
            exposure: form.a6_exposure,
          }
        : null,
    geo: form.a7_countries.map((c) => ({ country: c, segment: form.a7_segment.trim() })),
    data_assets: form.a8_data_assets,
  }

  const payload = {
    full_name: form.full_name.trim(),
    email: form.email.trim(),
    company: form.company.trim(),
    consent_rgpd: form.consent_rgpd,
    locale: locale.value || 'fr',
    brief,
  }
  if (form.role.trim()) payload.role = form.role.trim()

  try {
    const sessionRes = await startIntakeSession({ locale: locale.value || 'fr' })
    const sessionId = sessionRes?.data?.session_id
    const formRes = await submitIntakeForm(sessionId, payload)
    quoteId.value = formRes?.data?.quote_id || ''
    submitError.value = null
    currentStep.value = 4
  } catch (err) {
    const localised = formatApiError(err, t)
    submitError.value = localised || t('quote.step3.errorFallback')
    currentStep.value = 4
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   QUOTE — Parcours structuré « 3 temps » A1-A8 (US-IQ-01)
   ═══════════════════════════════════════════════════════════
   Réutilise les tokens `--stitch-*` (aliasés sur `--wi-*`, US-053)
   introduits par la refonte Stitch (US-025 v2). */

.quote-page {
  /* ── Alias --stitch-* → tokens globaux --wi-* (US-053) ── */
  --stitch-primary-container: var(--wi-primary-container);
  --stitch-primary: var(--wi-primary);
  --stitch-on-primary: var(--wi-on-primary);
  --stitch-on-primary-fixed: #370e00;
  --stitch-primary-fixed: #ffdbce;
  --stitch-surface: var(--wi-bg);
  --stitch-surface-container: var(--wi-surface-container);
  --stitch-surface-container-low: var(--wi-surface-container-low);
  --stitch-surface-container-lowest: var(--wi-surface);
  --stitch-surface-container-high: var(--wi-surface-container-high);
  --stitch-surface-container-highest: var(--wi-surface-container-highest);
  --stitch-on-surface: var(--wi-on-surface);
  --stitch-on-surface-variant: var(--wi-on-surface-variant);
  --stitch-outline: var(--wi-outline);
  --stitch-outline-variant: var(--wi-outline-variant);
  --stitch-secondary: var(--wi-secondary);
  --stitch-secondary-container: var(--wi-secondary-container);
  --stitch-error: var(--wi-error);
  --stitch-error-container: var(--wi-error-container);
  --stitch-on-error-container: var(--wi-on-error-container);

  --stitch-page-bg: var(--wi-bg);
  --stitch-input-bg: var(--wi-surface-container-low);
  --stitch-stepper-line: var(--wi-outline-variant);

  --stitch-shadow-card: var(--wi-shadow-ambient);
  --stitch-shadow-soft: var(--wi-shadow-sm);

  --stitch-font-display: var(--wi-font-heading);
  --stitch-font-body: var(--wi-font-body);

  min-height: 100vh;
  background: var(--stitch-page-bg);
  color: var(--stitch-on-surface);
  font-family: var(--stitch-font-body);
  font-size: 16px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.material-symbols-outlined {
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  user-select: none;
}

/* ── Top bar ────────────────────────────────────────── */
.quote-topbar {
  display: flex;
  align-items: center;
  padding: 16px 32px;
  padding-inline-end: 110px;
  border-bottom: 1px solid var(--stitch-stepper-line);
  background: var(--stitch-page-bg);
  position: sticky;
  top: 0;
  z-index: 50;
}

.quote-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--stitch-font-display);
  font-weight: 700;
  font-size: 18px;
  color: #4a4540;
  text-decoration: none;
  padding: 6px 12px;
  border-radius: var(--wi-radius-pill);
  transition: color 0.2s ease, background 0.2s ease;
}
.quote-back:hover {
  color: var(--stitch-primary-container);
  background: var(--stitch-surface-container-low);
}
.quote-back-arrow {
  font-size: 20px !important;
}
[dir="rtl"] .quote-back-arrow {
  transform: scaleX(-1);
}

/* ── Main wrapper ───────────────────────────────────── */
.quote-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ── Trust banner (mint icon, top) ──── */
.quote-trust-banner {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  background: var(--wi-bg);
  color: var(--stitch-on-surface-variant);
  padding: 10px 18px;
  border-radius: var(--wi-radius-md);
  border: 1px solid var(--stitch-outline-variant);
  font-family: var(--stitch-font-body);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 32px;
  max-width: 100%;
  text-align: start;
}
.quote-trust-banner-icon {
  font-size: 18px !important;
  font-variation-settings: 'FILL' 1 !important;
  color: var(--stitch-secondary);
  flex-shrink: 0;
}

/* ── Card centrée ────────────────────── */
.quote-card {
  width: 100%;
  max-width: 640px;
  background: var(--stitch-surface-container-lowest);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--stitch-shadow-card);
  padding: 48px;
  position: relative;
  overflow: visible;
}

@media (max-width: 640px) {
  .quote-card {
    padding: 32px 20px;
    border-radius: 20px;
  }
}

/* ── Stepper 3 temps ─ */
.quote-stepper {
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0;
  padding: 0 0 24px 0;
  margin: 0 0 32px 0;
  position: relative;
}

.quote-stepper-line {
  position: absolute;
  top: 20px;
  inset-inline-start: 20px;
  inset-inline-end: 20px;
  height: 1px;
  background: var(--stitch-outline-variant);
  z-index: 0;
  list-style: none;
  opacity: 0.4;
}

.quote-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  position: relative;
  z-index: 1;
  padding: 0;
  font-family: var(--stitch-font-body);
  font-size: 12px;
  font-weight: 500;
  color: var(--stitch-on-surface-variant);
  text-align: center;
  flex: 0 0 auto;
}

.quote-step-circle {
  width: 40px;
  height: 40px;
  border-radius: var(--wi-radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--stitch-font-body);
  font-size: 14px;
  font-weight: 700;
  border: 1px solid var(--stitch-outline-variant);
  background: var(--stitch-surface-container-highest);
  color: var(--stitch-on-surface-variant);
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.quote-step-check {
  font-size: 22px !important;
  color: var(--stitch-secondary);
  font-variation-settings: 'FILL' 1 !important;
}

.quote-step--current .quote-step-circle {
  background: var(--stitch-primary-container);
  border-color: var(--stitch-primary-container);
  color: var(--stitch-on-primary);
  box-shadow: 0 0 0 4px rgba(255, 133, 81, 0.18);
}
.quote-step--current .quote-step-label {
  color: var(--stitch-primary-container);
  font-weight: 700;
}

.quote-step--done .quote-step-circle {
  background: var(--wi-secondary-container);
  border-color: var(--wi-secondary-container);
  color: var(--stitch-secondary);
}

.quote-step-label {
  position: absolute;
  top: calc(100% + 8px);
  inset-inline-start: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  letter-spacing: 0.02em;
  white-space: nowrap;
  color: var(--stitch-on-surface-variant);
  font-family: var(--stitch-font-body);
  font-weight: 500;
}
[dir="rtl"] .quote-step-label {
  transform: translateX(50%);
}

@media (max-width: 480px) {
  .quote-step-label {
    font-size: 10px;
    letter-spacing: 0;
  }
}

/* ── Step content commun ────────────────────────────── */
.quote-step-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quote-step-title {
  font-family: var(--stitch-font-display);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.01em;
  color: var(--stitch-on-surface);
  margin: 0 0 8px 0;
  text-align: center;
}

.quote-step-subtitle {
  font-family: var(--stitch-font-body);
  font-size: 14px;
  line-height: 1.6;
  color: var(--stitch-on-surface-variant);
  margin: 0 0 4px 0;
  text-align: center;
}

/* Micro-copy de réciprocité — « pourquoi cette question » (AC US-IQ-01) */
.quote-reciprocity {
  font-family: var(--stitch-font-body);
  font-size: 12px;
  font-style: italic;
  line-height: 1.5;
  color: var(--stitch-secondary);
  background: var(--wi-secondary-container);
  border-radius: var(--wi-radius-md);
  padding: 8px 14px;
  margin: 0 0 16px 0;
  text-align: center;
}

@media (max-width: 480px) {
  .quote-step-title {
    font-size: 20px;
  }
}

/* ── Champs Stitch (input/textarea/select) ──────────── */
.quote-field-stitch {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.quote-field-stitch-label {
  font-family: var(--stitch-font-body);
  font-size: 12px;
  font-weight: 500;
  color: var(--stitch-on-surface-variant);
  padding-inline-start: 4px;
}

.quote-field-hint {
  font-family: var(--stitch-font-body);
  font-size: 11px;
  color: var(--stitch-outline);
  padding-inline-start: 4px;
}

.quote-required {
  color: var(--stitch-primary-container);
  margin-inline-start: 2px;
}

.quote-field-error {
  font-family: var(--stitch-font-body);
  font-size: 12px;
  color: var(--stitch-on-error-container);
  margin-top: 4px;
  padding-inline-start: 4px;
}

.quote-input-stitch {
  width: 100%;
  background: var(--stitch-input-bg);
  border: none;
  border-radius: var(--wi-radius-interactive);
  padding: 16px;
  font-family: var(--stitch-font-body);
  font-size: 16px;
  line-height: 1.5;
  color: var(--stitch-on-surface);
  transition: box-shadow 0.2s ease;
}
.quote-input-stitch::placeholder {
  color: var(--stitch-outline);
}
.quote-input-stitch:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--stitch-primary-container);
}
.quote-input-stitch:disabled {
  opacity: 0.5;
}

.quote-textarea {
  resize: vertical;
  font-family: inherit;
}

.quote-select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2357423a'%3e%3cpath d='M7 10l5 5 5-5z'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 16px center;
  background-size: 20px;
  padding-inline-end: 40px;
}
[dir="rtl"] .quote-select {
  background-position: left 16px center;
}

.quote-field-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
@media (min-width: 540px) {
  .quote-field-row {
    grid-template-columns: 1fr 1fr;
  }
}

/* ── A2 — liste d'options dynamique ──────────────────── */
.quote-option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.quote-option-row .quote-input-stitch {
  flex: 1;
}
.quote-option-remove {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--stitch-outline-variant);
  border-radius: var(--wi-radius-pill);
  color: var(--stitch-on-surface-variant);
  cursor: pointer;
}
.quote-option-remove:hover {
  border-color: var(--stitch-error);
  color: var(--stitch-error);
}
.quote-option-add {
  align-self: flex-start;
  margin-top: 8px;
  padding: 8px 16px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ── Groupes de cases à cocher (A4/A7/A8) ────────────── */
.quote-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}
.quote-checkbox-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--stitch-outline-variant);
  border-radius: var(--wi-radius-pill);
  background: var(--stitch-surface-container-lowest);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, color 0.2s ease;
}
.quote-checkbox-chip input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.quote-checkbox-chip--checked {
  border-color: var(--stitch-primary-container);
  background: var(--ms-orange-soft, rgba(255, 133, 81, 0.08));
  color: var(--stitch-primary-container);
  font-weight: 600;
}

.quote-checkbox-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--stitch-on-surface-variant);
  cursor: pointer;
}

.quote-divider {
  border: none;
  border-top: 1px solid var(--stitch-outline-variant);
  margin: 8px 0;
}

/* ── Consent (checkbox) ─────────────────────────────── */
.quote-consent-stitch {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: var(--stitch-input-bg);
  border-radius: 16px;
  padding: 16px;
  font-family: var(--stitch-font-body);
  font-size: 14px;
  line-height: 1.5;
  color: var(--stitch-on-surface-variant);
  cursor: pointer;
  margin-top: 8px;
}
.quote-consent-stitch input[type="checkbox"] {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  accent-color: var(--stitch-primary-container);
  cursor: pointer;
  flex-shrink: 0;
}

/* ── CTA principale + actions row ───────────────────── */
.quote-cta {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--stitch-primary-container);
  color: var(--stitch-on-primary);
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 16px;
  letter-spacing: 0.01em;
  padding: 16px 24px;
  border: none;
  border-radius: var(--wi-radius-interactive);
  cursor: pointer;
  transition: opacity 0.2s ease, transform 0.1s ease;
  box-shadow: 0 8px 20px rgba(255, 133, 81, 0.25);
  margin-top: 16px;
  text-decoration: none;
}
.quote-cta:hover:not(:disabled) {
  opacity: 0.95;
}
.quote-cta:active:not(:disabled) {
  transform: scale(0.99);
}
.quote-cta:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}
.quote-cta-arrow {
  font-size: 20px !important;
}
[dir="rtl"] .quote-cta-arrow {
  transform: scaleX(-1);
}

.quote-cta--inline {
  width: auto;
  flex: 1;
}

.quote-actions-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  align-items: stretch;
}

.quote-secondary-btn {
  flex: 0 0 auto;
  background: transparent;
  color: var(--stitch-on-surface-variant);
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 14px;
  padding: 14px 24px;
  border: 1.5px solid var(--stitch-stepper-line);
  border-radius: var(--wi-radius-interactive);
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease;
}
.quote-secondary-btn:hover:not(:disabled) {
  border-color: var(--stitch-primary-container);
  color: var(--stitch-primary-container);
}
.quote-secondary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Confirmation — success / error ───────────────────── */
.quote-success,
.quote-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  padding: 24px 0;
}

.quote-success-icon {
  width: 80px;
  height: 80px;
  border-radius: var(--wi-radius-pill);
  background: var(--ms-mint-soft);
  color: var(--stitch-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.quote-success-icon .material-symbols-outlined {
  font-size: 64px !important;
  font-variation-settings: 'FILL' 0 !important;
}

.quote-error-icon {
  width: 80px;
  height: 80px;
  border-radius: var(--wi-radius-pill);
  background: var(--stitch-error-container);
  color: var(--stitch-error);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.quote-error-icon .material-symbols-outlined {
  font-size: 48px !important;
  font-variation-settings: 'FILL' 1 !important;
}

.quote-success-sub {
  font-family: var(--stitch-font-body);
  font-size: 16px;
  line-height: 1.6;
  color: var(--stitch-on-surface-variant);
  margin: 0;
  max-width: 440px;
}

.quote-success-id {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--stitch-input-bg);
  border: 1px dashed var(--stitch-stepper-line);
  border-radius: var(--wi-radius-interactive);
  padding: 10px 16px;
  margin: 8px 0 16px 0;
  font-size: 13px;
  color: var(--stitch-on-surface-variant);
}
.quote-success-id-label {
  font-family: var(--stitch-font-body);
  font-weight: 500;
}
.quote-success-id-value {
  font-family: 'Space Mono', ui-monospace, monospace;
  font-size: 13px;
  color: var(--stitch-on-surface);
  background: transparent;
}

/* ── Trust signals (3 colonnes sous le form) ────────── */
.quote-trust-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 32px;
  width: 100%;
  max-width: 900px;
  margin: 64px auto 0 auto;
}
@media (min-width: 720px) {
  .quote-trust-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.quote-trust-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 16px;
  gap: 8px;
}

.quote-trust-item-icon {
  font-size: 32px !important;
  color: var(--stitch-primary-container);
  margin-bottom: 4px;
}

.quote-trust-item-title {
  font-family: var(--stitch-font-body);
  font-size: 16px;
  font-weight: 700;
  color: var(--stitch-on-surface);
  margin: 0;
}

.quote-trust-item-body {
  font-family: var(--stitch-font-body);
  font-size: 12px;
  line-height: 1.5;
  color: var(--stitch-on-surface-variant);
  margin: 0;
  max-width: 220px;
}

/* ── Mobile ─────────────────────────────────────────── */
@media (max-width: 480px) {
  .quote-main {
    padding: 24px 16px 48px;
  }
  .quote-actions-row {
    flex-direction: column-reverse;
  }
  .quote-secondary-btn {
    width: 100%;
  }
}
</style>
