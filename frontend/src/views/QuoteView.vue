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

      <!-- ───────────── Card centrée (form 3 steps) ───────────── -->
      <section class="quote-card">
        <!-- Stepper 3 steps -->
        <ol
          class="quote-stepper"
          :aria-label="$t('quote.stepper.step', { current: currentStep, total: 3 })"
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

        <!-- ───── Step 1 — How can we help ? ───── -->
        <form
          v-if="currentStep === 1"
          class="quote-step-content"
          @submit.prevent="goToStep2"
        >
          <h2 class="quote-step-title">{{ $t('quote.step1.title') }}</h2>

          <div class="quote-radio-group">
            <label
              v-for="opt in situationOptions"
              :key="opt.id"
              class="quote-radio"
              :class="{ 'quote-radio--checked': form.situation === opt.id }"
            >
              <input
                type="radio"
                name="situation"
                :value="opt.id"
                v-model="form.situation"
                class="quote-radio-input"
              />
              <span class="quote-radio-bullet" aria-hidden="true">
                <span class="quote-radio-bullet-dot"></span>
              </span>
              <span class="quote-radio-content">
                <span class="quote-radio-title">{{ $t(`quote.step1.options.${opt.id}.title`) }}</span>
                <span class="quote-radio-sub">{{ $t(`quote.step1.options.${opt.id}.sub`) }}</span>
              </span>
            </label>
          </div>

          <label class="quote-field-stitch">
            <span class="quote-field-stitch-label">{{ $t('quote.step1.other.label') }}</span>
            <input
              v-model.trim="form.otherSituation"
              type="text"
              class="quote-input-stitch"
              :placeholder="$t('quote.step1.other.placeholder')"
              maxlength="200"
            />
          </label>

          <button
            type="submit"
            class="quote-cta"
            :disabled="!step1Valid"
          >
            <span>{{ $t('quote.actions.next') }}</span>
            <span class="material-symbols-outlined quote-cta-arrow" aria-hidden="true">arrow_forward</span>
          </button>
        </form>

        <!-- ───── Step 2 — Your context ───── -->
        <form
          v-else-if="currentStep === 2"
          class="quote-step-content"
          @submit.prevent="submit"
        >
          <h2 class="quote-step-title">{{ $t('quote.step2.title') }}</h2>
          <p class="quote-step-subtitle">{{ $t('quote.step2.subtitle') }}</p>

          <!-- Grid 2 colonnes : nom/email puis organisation/role -->
          <div class="quote-field-row">
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">
                {{ $t('quote.step2.fullName.label') }}
                <span class="quote-required">*</span>
              </span>
              <input
                v-model.trim="form.full_name"
                type="text"
                class="quote-input-stitch"
                maxlength="100"
                required
                dir="ltr"
                :placeholder="$t('quote.step2.fullName.placeholder')"
              />
            </label>

            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">
                {{ $t('quote.step2.email.label') }}
                <span class="quote-required">*</span>
              </span>
              <input
                v-model.trim="form.email"
                type="email"
                class="quote-input-stitch"
                required
                dir="ltr"
                :placeholder="$t('quote.step2.email.placeholder')"
                :aria-invalid="form.email && !emailValid ? 'true' : 'false'"
              />
              <span
                v-if="form.email && !emailValid"
                class="quote-field-error"
              >
                {{ $t('quote.step2.email.invalid') }}
              </span>
            </label>
          </div>

          <div class="quote-field-row">
            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">
                {{ $t('quote.step2.company.label') }}
                <span class="quote-required">*</span>
              </span>
              <input
                v-model.trim="form.company"
                type="text"
                class="quote-input-stitch"
                maxlength="120"
                required
                :placeholder="$t('quote.step2.company.placeholder')"
              />
            </label>

            <label class="quote-field-stitch">
              <span class="quote-field-stitch-label">{{ $t('quote.step2.role.label') }}</span>
              <input
                v-model.trim="form.role"
                type="text"
                class="quote-input-stitch"
                maxlength="80"
                :placeholder="$t('quote.step2.role.placeholder')"
              />
            </label>
          </div>

          <label class="quote-field-stitch">
            <span class="quote-field-stitch-label">{{ $t('quote.step2.deadline.label') }}</span>
            <select v-model="form.target_deadline" class="quote-input-stitch quote-select">
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

          <label class="quote-consent-stitch">
            <input
              v-model="form.consent_rgpd"
              type="checkbox"
              required
            />
            <span>
              {{ $t('quote.step2.consent.label') }}
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
              :disabled="!step2Valid || submitting"
            >
              <span>{{ submitting ? $t('quote.actions.submitting') : $t('quote.actions.submit') }}</span>
              <span v-if="!submitting" class="material-symbols-outlined quote-cta-arrow" aria-hidden="true">arrow_forward</span>
            </button>
          </div>
        </form>

        <!-- ───── Step 3 — Get matched (success / error) ───── -->
        <div v-else-if="currentStep === 3" class="quote-step-content">
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
              <router-link
                :to="{ name: 'Offers' }"
                class="quote-cta quote-cta--inline"
              >
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
              <button
                type="button"
                class="quote-secondary-btn"
                @click="goBackToStep2"
              >
                {{ $t('quote.step3.tryAgain') }}
              </button>
            </div>
          </template>
        </div>
      </section>

      <!-- ───────────── Trust signals (3 colonnes) ───────────── -->
      <section class="quote-trust-grid" aria-label="Trust signals">
        <div
          v-for="item in trustItems"
          :key="item.id"
          class="quote-trust-item"
        >
          <span class="material-symbols-outlined quote-trust-item-icon" aria-hidden="true">{{ item.icon }}</span>
          <h5 class="quote-trust-item-title">{{ $t(`quote.trustSignals.${item.id}.title`) }}</h5>
          <p class="quote-trust-item-body">{{ $t(`quote.trustSignals.${item.id}.body`) }}</p>
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

// ─── Step 1 — situation options du mockup Stitch ────────────────────────
// Chaque option a un id frontend (camelCase pour les clés i18n) et un id
// backend canonique pour le payload POST /api/quote (champ `package`).
const situationOptions = [
  { id: 'crisis', backendPackage: 'crisis_drill_24h' },
  { id: 'policy', backendPackage: 'policy_brief_stress' },
  { id: 'campaign', backendPackage: 'pre_launch_adcheck' },
]

// Liste des packages backend valides (alignée sur l'enum OpenAPI US-025
// + quote_service.py _VALID_PACKAGES). Le backend reste à 4 slugs.
const validBackendPackages = [
  'crisis_drill_24h',
  'policy_brief_stress',
  'pre_launch_adcheck',
  'custom',
]

// Mapping slug carousel 10-packages → slug backend canonique (4 valeurs).
// La précision (ex: "Cohort Replay") sera ajoutée en clair dans le
// payload `message`, pour ne pas perdre l'info au passage.
const CAROUSEL_TO_BACKEND = {
  pmf_discovery: 'pre_launch_adcheck',
  crisis_drill_24h: 'crisis_drill_24h',
  adcheck_lite: 'pre_launch_adcheck',
  adcheck_pro: 'pre_launch_adcheck',
  product_launch: 'pre_launch_adcheck',
  policy_stress: 'policy_brief_stress',
  cohort_replay: 'custom',
  crisis_watch: 'crisis_drill_24h',
  brand_pulse: 'pre_launch_adcheck',
  custom: 'custom',
}

const deadlineOptions = ['not_urgent', '1_month', '2_weeks', 'this_week']

// Trust signals sous le form (3 colonnes).
const trustItems = [
  { id: 'multiAgent', icon: 'psychology' },
  { id: 'airGapped', icon: 'security' },
  { id: 'fastSetup', icon: 'bolt' },
]

// ─── Mapping query ?package=… → préselection radio Step 1 ─────────────
// La page Offers émet par exemple ?package=crisis_drill_24h. On retrouve
// l'option radio correspondante pour pré-cocher Step 1. Les valeurs
// frontend OffersView (legacy : crisisDrill / policyBrief / preLaunch)
// sont aussi acceptées pour ne casser aucun lien existant.
const PACKAGE_TO_SITUATION = {
  // Carousel 10-packages (refonte L99) → mapping radio Step 1.
  // Les packages "Marketing" tombent sur 'campaign', les "Crisis" sur
  // 'crisis', les "Policy" sur 'policy'. PMF/Cohort/Custom → laissés sur
  // la radio par défaut (situation crisis) avec la précision en Step 2.
  crisis_drill_24h: 'crisis',
  crisis_watch: 'crisis',
  adcheck_lite: 'campaign',
  adcheck_pro: 'campaign',
  brand_pulse: 'campaign',
  product_launch: 'campaign',
  pmf_discovery: 'campaign',
  policy_stress: 'policy',
  cohort_replay: 'policy',
  // Legacy US-023
  policy_brief_stress: 'policy',
  pre_launch_adcheck: 'campaign',
  crisisDrill: 'crisis',
  policyBrief: 'policy',
  preLaunch: 'campaign',
}

const route = useRoute()
const { t, locale } = useI18n()

const currentStep = ref(1)

const form = reactive({
  // Step 1
  situation: 'crisis', // l'option par défaut, comme dans le mockup
  otherSituation: '',
  // Slug carousel d'origine (?package=…) — préservé pour préciser le pack
  // demandé dans `message`, indépendamment du mapping backend.
  carouselPackage: '',
  // Step 2
  full_name: '',
  email: '',
  company: '',
  role: '',
  target_deadline: '',
  consent_rgpd: false,
})

const submitting = ref(false)
const submitError = ref(null) // null = succès, string = message d'erreur
const quoteId = ref('')

// ─── Validations ───────────────────────────────────────────────────────
const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const emailValid = computed(() => emailRe.test(form.email))

// Step 1 : au moins une situation cochée. « other » suffit aussi car on a
// toujours une option par défaut, mais on garde la validation explicite.
const step1Valid = computed(
  () => !!form.situation || !!form.otherSituation,
)

const step2Valid = computed(
  () =>
    !!form.full_name &&
    !!form.email &&
    emailValid.value &&
    !!form.company &&
    form.consent_rgpd === true,
)

// ─── Step labels ──────────────────────────────────────────────────────
function stepLabel(idx) {
  const keys = ['situation', 'context', 'matched']
  return t(`quote.stepper.stepNames.${keys[idx - 1]}`)
}

// ─── Navigation ────────────────────────────────────────────────────────
function goToStep2() {
  if (!step1Valid.value) return
  currentStep.value = 2
}

function goBack() {
  if (currentStep.value > 1) currentStep.value -= 1
}

function goBackToStep2() {
  // Réessayer après une erreur backend : on revient à Step 2, le form
  // est conservé pour permettre à l'utilisateur d'ajuster s'il le veut.
  submitError.value = null
  currentStep.value = 2
}

// ─── Détermine le `package` backend à partir de Step 1 ────────────────
// crisis → crisis_drill_24h | policy → policy_brief_stress
// campaign → pre_launch_adcheck. Si l'utilisateur a écrit dans le champ
// otherSituation et n'a pas cliqué sur une radio standard, on bascule
// sur 'custom'. La radio par défaut est 'crisis', donc otherSituation
// non vide ne suffit pas à elle seule : on ne switch sur custom que si
// la radio n'a pas été modifiée ET que otherSituation est rempli.
function resolveBackendPackage() {
  // 1) Si on est arrivé via /offres avec un slug carousel, on le mappe
  //    vers les 4 slugs backend autorisés (CAROUSEL_TO_BACKEND).
  if (form.carouselPackage && CAROUSEL_TO_BACKEND[form.carouselPackage]) {
    return CAROUSEL_TO_BACKEND[form.carouselPackage]
  }
  // 2) Sinon on dérive de la radio Step 1.
  const opt = situationOptions.find((o) => o.id === form.situation)
  if (opt && opt.backendPackage) {
    return opt.backendPackage
  }
  return 'custom'
}

// ─── Submit ────────────────────────────────────────────────────────────
async function submit() {
  if (!step2Valid.value || submitting.value) return
  submitting.value = true
  submitError.value = null

  // Construit le message en concaténant la situation Stitch + l'éventuelle
  // précision saisie en Step 1 (champ otherSituation).
  // Si l'utilisateur est arrivé via le carousel /offres, on préfixe par le
  // nom du pack précis demandé pour que l'équipe sales le retrouve même
  // quand le slug carousel est mappé vers un slug backend canonique.
  const situationLabel = form.situation
    ? t(`quote.step1.options.${form.situation}.title`)
    : ''
  const messageParts = []
  if (form.carouselPackage) {
    // Tente d'utiliser le nom localisé i18n si dispo, fallback sur le slug.
    const pkgI18nKey = `offers.packages.${form.carouselPackage}.name`
    const pkgName = t(pkgI18nKey)
    const display = pkgName && pkgName !== pkgI18nKey ? pkgName : form.carouselPackage
    messageParts.push(`[Pack: ${display}]`)
  }
  if (situationLabel) messageParts.push(`[${situationLabel}]`)
  if (form.otherSituation) messageParts.push(form.otherSituation)
  const message = messageParts.join(' ').trim()

  const backendPackage = resolveBackendPackage()
  const safePackage = validBackendPackages.includes(backendPackage)
    ? backendPackage
    : 'custom'

  const payload = {
    full_name: form.full_name,
    email: form.email,
    company: form.company,
    package: safePackage,
    consent_rgpd: form.consent_rgpd,
    locale: locale.value || 'fr',
  }
  if (form.role) payload.role = form.role
  if (form.target_deadline) payload.target_deadline = form.target_deadline
  if (message) payload.message = message

  try {
    const res = await submitQuote(payload)
    quoteId.value = (res && res.data && res.data.quote_id) || ''
    submitError.value = null
    currentStep.value = 3
  } catch (err) {
    const localised = formatApiError(err, t)
    submitError.value = localised || t('quote.step3.errorFallback')
    currentStep.value = 3
  } finally {
    submitting.value = false
  }
}

// ─── Préselection radio depuis ?package=… (depuis OffersView) ─────────
// Mapping sector (US-085) → situation radio + package backend par défaut
const SECTOR_TO_SITUATION = {
  finance: 'crisis',
  energy: 'policy',
  politics: 'policy',
  retail: 'campaign',
  tech: 'campaign',
  industry: 'crisis',
  media: 'crisis',
  healthcare: 'policy',
  custom: '',
}

const VALID_SECTORS = Object.keys(SECTOR_TO_SITUATION)

onMounted(() => {
  // Pré-remplissage via ?package= (parcours depuis /offres carousel)
  const raw = (route.query?.package || '').toString().trim()
  if (raw && (CAROUSEL_TO_BACKEND[raw] || validBackendPackages.includes(raw))) {
    form.carouselPackage = raw
  }
  if (raw) {
    const situation = PACKAGE_TO_SITUATION[raw]
    if (situation) form.situation = situation
  }

  // Pré-remplissage via ?sector= et ?usecase= (depuis SectorUseCases sur /landing)
  const sector = (route.query?.sector || '').toString().trim()
  if (sector && VALID_SECTORS.includes(sector)) {
    const mappedSituation = SECTOR_TO_SITUATION[sector]
    if (mappedSituation) form.situation = mappedSituation

    // Récupère le use case spécifique depuis i18n et le pré-remplit
    // dans otherSituation pour donner du contexte au prospect.
    const usecaseIdx = parseInt((route.query?.usecase || '0').toString(), 10) || 0
    try {
      const sectorName = t(`sectors.${sector}.name`)
      const caseText = t(`sectors.${sector}.cases.${usecaseIdx}`)
      if (caseText && !caseText.startsWith('sectors.')) {
        form.otherSituation = `[${sectorName}] ${caseText}`
      }
    } catch (_) {
      // i18n key absent → silently ignore
    }
  }
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   QUOTE — Refonte fidèle au mockup Stitch (US-025 v2)
   ═══════════════════════════════════════════════════════════
   Source unique de vérité : stitch_bassira_simulation_pricing_page/
   bassira_devis_get_a_quote/code.html
   On utilise les variables `--stitch-*` scopées au composant pour
   reproduire la palette M3 du mockup, sans Tailwind. */

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
  /* Réserve la place pour le LanguageSwitcher floating top-right
     (z-index 1500) — cohérent avec OffersView / MethodologieView. */
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

/* ── Trust banner (mint icon, top — Stitch Step 1) ──── */
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
  /* Mint (--wi-secondary) — signal de protection souverain */
  color: var(--stitch-secondary);
  flex-shrink: 0;
}

/* ── Card centrée (form 3 steps) ────────────────────── */
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

/* ── Stepper 3 steps (rond + label, fidèle Stitch Step 2) ─ */
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

/* Track de fond inactif (gris warm) qui traverse tout le stepper */
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
  /* Pas de fond — la pastille couvre la ligne */
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
  /* Texte mint sur container mint clair */
  color: var(--stitch-secondary);
  font-variation-settings: 'FILL' 1 !important;
}

/* État courant : terracotta (--wi-on-primary-container) avec glow */
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

/* État done : mint (--wi-secondary-container) avec checkmark */
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
  margin: 0 0 16px 0;
  text-align: center;
}

@media (max-width: 480px) {
  .quote-step-title {
    font-size: 20px;
  }
}

/* ── Step 1 — radio cards ───────────────────────────── */
.quote-radio-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quote-radio {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: var(--stitch-surface-container-lowest);
  border: 1px solid var(--stitch-outline-variant);
  border-radius: var(--wi-radius-md);
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, border-left-width 0.2s ease;
}
.quote-radio:hover {
  border-color: var(--stitch-primary-container);
  background: var(--stitch-surface-container-low);
}
/* Sélection : border-left orange épaisse (3px) + fond orange soft */
.quote-radio--checked {
  border-color: var(--stitch-outline-variant);
  border-inline-start: 3px solid var(--stitch-primary-container);
  padding-inline-start: 22px; /* compense les +2px de border */
  background: var(--ms-orange-soft, rgba(255, 133, 81, 0.08));
}

.quote-radio-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.quote-radio-content {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.quote-radio-title {
  font-family: var(--stitch-font-body);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.4;
  color: var(--stitch-on-surface);
}

.quote-radio-sub {
  font-family: var(--stitch-font-body);
  font-size: 12px;
  line-height: 1.5;
  color: var(--stitch-on-surface-variant);
}

.quote-radio-bullet {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: var(--wi-radius-pill);
  border: 2px solid var(--stitch-stepper-line);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--stitch-surface-container-lowest);
  transition: background 0.2s ease, border-color 0.2s ease;
}
.quote-radio-bullet-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--wi-radius-pill);
  background: transparent;
  transition: background 0.2s ease;
}
.quote-radio--checked .quote-radio-bullet {
  border-color: var(--stitch-primary-container);
  background: var(--stitch-primary-container);
}
.quote-radio--checked .quote-radio-bullet-dot {
  background: var(--stitch-on-primary);
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

/* ── Step 3 — success / error ───────────────────────── */
.quote-success,
.quote-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  padding: 24px 0;
}

/* Success icon : cercle mint translucide 80px + check_circle 64px outline mint
   (fidèle au design Stitch "Demande envoyée") */
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
