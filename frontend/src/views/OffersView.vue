<template>
  <div class="offers-page">
    <!-- ───────────── Top bar ───────────── -->
    <header class="offers-topbar">
      <router-link to="/" class="offers-back" :title="$t('offers.nav.backTitle')">
        <span class="offers-back-arrow material-symbols-outlined" aria-hidden="true">arrow_back</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
    </header>

    <main class="offers-main">
      <!-- ───────────── Hero ───────────── -->
      <section class="offers-hero">
        <div aria-hidden="true" class="offers-hero-blob"></div>
        <span class="offers-pill">
          <span class="material-symbols-outlined offers-pill-icon" aria-hidden="true">bolt</span>
          {{ $t('offers.eyebrow') }}
        </span>
        <h1 class="offers-headline">{{ $t('offers.hero.title') }}</h1>
        <p class="offers-sub">{{ $t('offers.hero.subtitle') }}</p>
      </section>

      <!-- ───────────── Filter chips ───────────── -->
      <nav
        class="offers-chips"
        :aria-label="$t('offers.filters.ariaLabel')"
        role="tablist"
      >
        <button
          v-for="chip in chips"
          :key="chip.id"
          type="button"
          role="tab"
          :aria-selected="activeChip === chip.id"
          class="offers-chip"
          :class="{ 'offers-chip--active': activeChip === chip.id }"
          @click="setActiveChip(chip.id)"
        >
          <span v-if="chip.emoji" class="offers-chip-emoji" aria-hidden="true">{{ chip.emoji }}</span>
          <span>{{ $t(`offers.filters.${chip.id}`) }}</span>
        </button>
      </nav>

      <!-- ───────────── Carousel ─────────────
           Une seule liste DOM avec toutes les cards, le « track » se déplace
           via translateX. Sélecteur `.offers-card` conservé pour les tests
           Playwright existants. -->
      <section
        class="offers-carousel"
        :aria-label="$t('offers.carousel.ariaLabel')"
        @keydown.left.prevent="prev"
        @keydown.right.prevent="next"
        tabindex="0"
        ref="carouselEl"
      >
        <button
          type="button"
          class="offers-nav offers-nav--prev"
          :aria-label="$t('offers.carousel.prev')"
          :disabled="displayedPackages.length <= 1"
          @click="prev"
        >
          <span class="material-symbols-outlined" aria-hidden="true">chevron_left</span>
        </button>

        <div
          class="offers-track-viewport"
          @touchstart.passive="onTouchStart"
          @touchend="onTouchEnd"
        >
          <ul
            class="offers-track"
            :style="trackStyle"
          >
            <li
              v-for="(pkg, idx) in displayedPackages"
              :key="pkg.id"
              class="offers-slide"
              :class="{ 'offers-slide--active': idx === activeIndex }"
              :aria-hidden="idx === activeIndex ? 'false' : 'true'"
            >
              <article
                class="offers-card"
                :class="{
                  'offers-card--featured': pkg.featured,
                  'offers-card--active': idx === activeIndex,
                }"
                :data-package="pkg.id"
                :data-tier="pkg.tier"
              >
                <span v-if="pkg.featured" class="offers-most-chosen">
                  {{ $t('offers.featuredBadge') }}
                </span>

                <span class="offers-sector" :class="`offers-sector--${tierToTone(pkg.tier)}`">
                  <span class="offers-sector-dot" aria-hidden="true"></span>
                  {{ $t(`offers.packages.${pkg.id}.sectorBadge`) }}
                </span>

                <h3 class="offers-card-title">{{ $t(`offers.packages.${pkg.id}.name`) }}</h3>

                <p class="offers-card-delay">
                  <span class="material-symbols-outlined offers-card-delay-icon" aria-hidden="true">{{ pkg.delayIcon || 'schedule' }}</span>
                  {{ $t(`offers.packages.${pkg.id}.delay`) }}
                </p>

                <p class="offers-card-description">
                  {{ $t(`offers.packages.${pkg.id}.description`) }}
                </p>

                <!-- Toggle annuel / mensuel uniquement pour packages billing=monthly -->
                <div v-if="pkg.billing === 'monthly'" class="offers-billing-toggle">
                  <button
                    type="button"
                    class="offers-billing-btn"
                    :class="{ 'offers-billing-btn--active': billingMode[pkg.id] !== 'annual' }"
                    @click="setBillingMode(pkg.id, 'monthly')"
                  >
                    {{ $t('offers.billing.monthly') }}
                  </button>
                  <button
                    type="button"
                    class="offers-billing-btn"
                    :class="{ 'offers-billing-btn--active': billingMode[pkg.id] === 'annual' }"
                    @click="setBillingMode(pkg.id, 'annual')"
                  >
                    {{ $t('offers.billing.annual') }}
                    <span class="offers-billing-badge">
                      {{ $t('offers.billing.annualBadge', { months: pkg.annualDiscount || 2 }) }}
                    </span>
                  </button>
                </div>

                <!-- Selector variants si présent -->
                <label v-if="pkg.variants" class="offers-variant">
                  <span class="offers-variant-label">{{ $t(`offers.packages.${pkg.id}.variantsLabel`) }}</span>
                  <select
                    class="offers-variant-select"
                    :value="selectedVariant[pkg.id] || pkg.variants.options[0].value"
                    @change="setVariant(pkg.id, $event.target.value)"
                  >
                    <option
                      v-for="opt in pkg.variants.options"
                      :key="opt.value"
                      :value="opt.value"
                    >
                      {{ $t(`offers.packages.${pkg.id}.variantsOptions.${opt.value}`) }}
                    </option>
                  </select>
                </label>

                <div class="offers-card-price">
                  <template v-if="resolvedPrice(pkg).priceMAD !== null">
                    <span class="offers-card-price-mad">
                      {{ formatMad(resolvedPrice(pkg).priceMAD) }}
                      <span class="offers-card-price-currency">MAD</span>
                    </span>
                    <span class="offers-card-price-usd">
                      ${{ formatUsd(resolvedPrice(pkg).priceUSD) }}{{ pkg.billing === 'monthly' ? ` ${$t('offers.billing.suffix.' + (billingMode[pkg.id] === 'annual' ? 'annual' : 'monthly'))}` : '' }}
                    </span>
                  </template>
                  <template v-else>
                    <span class="offers-card-price-mad offers-card-price-mad--label">
                      {{ $t(`offers.packages.${pkg.id}.priceLabel`) }}
                    </span>
                  </template>
                </div>

                <hr class="offers-card-divider" />

                <ul class="offers-card-bullets">
                  <li
                    v-for="(_, i) in pkg.bulletsCount"
                    :key="i"
                    class="offers-card-bullet"
                  >
                    <span class="material-symbols-outlined offers-card-bullet-icon" aria-hidden="true">check_circle</span>
                    <span>{{ $t(`offers.packages.${pkg.id}.bullets.b${i + 1}`) }}</span>
                  </li>
                </ul>

                <p
                  v-if="pkg.fineprint"
                  class="offers-card-fineprint"
                >
                  {{ $t(`offers.packages.${pkg.id}.fineprint`) }}
                </p>

                <button
                  type="button"
                  class="offers-card-cta"
                  @click="onCtaClick(pkg)"
                >
                  {{ $t(`offers.packages.${pkg.id}.cta`) }}
                </button>
              </article>
            </li>
          </ul>
        </div>

        <button
          type="button"
          class="offers-nav offers-nav--next"
          :aria-label="$t('offers.carousel.next')"
          :disabled="displayedPackages.length <= 1"
          @click="next"
        >
          <span class="material-symbols-outlined" aria-hidden="true">chevron_right</span>
        </button>
      </section>

      <!-- Dots indicators -->
      <div
        v-if="displayedPackages.length > 1"
        class="offers-dots"
        role="tablist"
        :aria-label="$t('offers.carousel.dotsAriaLabel')"
      >
        <button
          v-for="(pkg, idx) in displayedPackages"
          :key="pkg.id"
          type="button"
          role="tab"
          :aria-selected="idx === activeIndex"
          :aria-label="$t('offers.carousel.dotLabel', { index: idx + 1, name: $t(`offers.packages.${pkg.id}.name`) })"
          class="offers-dot"
          :class="{ 'offers-dot--active': idx === activeIndex }"
          @click="goTo(idx)"
        ></button>
      </div>

      <!-- ───────────── FAQ ───────────── -->
      <section class="offers-faq" aria-label="FAQ">
        <h2 class="offers-section-title">{{ $t('offers.faq.title') }}</h2>
        <div class="offers-faq-list">
          <details
            v-for="key in faqKeys"
            :key="key"
            class="offers-faq-item"
          >
            <summary class="offers-faq-q">
              <span>{{ $t(`offers.faq.items.${key}.question`) }}</span>
              <span class="material-symbols-outlined offers-faq-chevron" aria-hidden="true">expand_more</span>
            </summary>
            <div class="offers-faq-a">{{ $t(`offers.faq.items.${key}.answer`) }}</div>
          </details>
        </div>
      </section>
    </main>

    <!-- ───────────── Pre-Footer CTA strip (rose pâle) ─────────────
         Conservé pour cohérence pricing-page : « Vous hésitez ? Parlons ».
         Préserve aussi la garantie tunnel-commercial.spec /offres → /devis. -->
    <section class="offers-cta-strip">
      <h3 class="offers-cta-strip-title">{{ $t('offers.help.title') }}</h3>
      <p class="offers-cta-strip-body">{{ $t('offers.help.body') }}</p>
      <router-link
        :to="{ name: 'Quote' }"
        class="offers-cta-strip-btn"
      >
        {{ $t('offers.help.cta') }}
      </router-link>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

// ════════════════════════════════════════════════════════════════════
// Catalogue 10 packages (data-driven)
// ════════════════════════════════════════════════════════════════════
// Le `id` correspond à la clé i18n offers.packages.<id>.* et au backend
// `package` slug (POST /api/quote). Les prix sont en JS — jamais traduits.
//
// Tiers :
//   discovery → mint
//   drill     → orange
//   stress    → warning (jaune-orangé)
//   twin      → violet
//   retainer  → teal
//   custom    → outline (gris neutre)
//
// `bulletsCount` permet de gérer un nombre de bullets variable par package
// tout en gardant des clés i18n stables b1..bN.
const packages = [
  // 🔍 Discovery
  {
    id: 'pmf_discovery',
    tier: 'discovery',
    delayIcon: 'schedule',
    priceMAD: 10000,
    priceUSD: 1000,
    bulletsCount: 6,
    fineprint: true,
  },
  // ⚡ Drill
  {
    id: 'crisis_drill_24h',
    tier: 'drill',
    featured: true,
    delayIcon: 'schedule',
    priceMAD: 20000,
    priceUSD: 2000,
    bulletsCount: 6,
    fineprint: true,
  },
  {
    id: 'adcheck_lite',
    tier: 'drill',
    delayIcon: 'schedule',
    priceMAD: 15000,
    priceUSD: 1500,
    bulletsCount: 6,
  },
  // 🎯 Stress
  {
    id: 'adcheck_pro',
    tier: 'stress',
    delayIcon: 'schedule',
    priceMAD: 28000,
    priceUSD: 2800,
    bulletsCount: 6,
    variants: {
      options: [
        { value: '3', priceMAD: 28000, priceUSD: 2800 },
        { value: '5', priceMAD: 42000, priceUSD: 4200 },
        { value: '8', priceMAD: 65000, priceUSD: 6500 },
      ],
    },
  },
  {
    id: 'product_launch',
    tier: 'stress',
    delayIcon: 'schedule',
    priceMAD: 42000,
    priceUSD: 4200,
    bulletsCount: 6,
  },
  {
    id: 'policy_stress',
    tier: 'stress',
    delayIcon: 'schedule',
    priceMAD: 75000,
    priceUSD: 7500,
    bulletsCount: 6,
  },
  // 🧬 Twin
  {
    id: 'cohort_replay',
    tier: 'twin',
    delayIcon: 'schedule',
    priceMAD: 110000,
    priceUSD: 11000,
    bulletsCount: 6,
    fineprint: true,
    variants: {
      options: [
        { value: '50', priceMAD: 110000, priceUSD: 11000 },
        { value: '80', priceMAD: 165000, priceUSD: 16500 },
        { value: '120', priceMAD: 240000, priceUSD: 24000 },
      ],
    },
  },
  // ♾️ Retainer
  {
    id: 'crisis_watch',
    tier: 'retainer',
    delayIcon: 'shield',
    priceMAD: 60000,
    priceUSD: 6000,
    billing: 'monthly',
    annualDiscount: 2,
    bulletsCount: 6,
    fineprint: true,
  },
  {
    id: 'brand_pulse',
    tier: 'retainer',
    delayIcon: 'monitoring',
    priceMAD: 45000,
    priceUSD: 4500,
    billing: 'monthly',
    annualDiscount: 2,
    bulletsCount: 6,
    fineprint: true,
  },
  // 🤝 Custom
  {
    id: 'custom',
    tier: 'custom',
    delayIcon: 'tune',
    priceMAD: null,
    priceUSD: null,
    bulletsCount: 6,
  },
]

// Filter chips — l'ordre est stable (les emojis sont stockés dans le composant
// pour rester proches du rendu, le label vient des locales).
const chips = [
  { id: 'all', emoji: null },
  { id: 'discovery', emoji: '🔍' },
  { id: 'drill', emoji: '⚡' },
  { id: 'stress', emoji: '🎯' },
  { id: 'twin', emoji: '🧬' },
  { id: 'retainer', emoji: '♾️' },
]

const tierToTone = (tier) => {
  switch (tier) {
    case 'discovery': return 'mint'
    case 'drill': return 'orange'
    case 'stress': return 'warning'
    case 'twin': return 'violet'
    case 'retainer': return 'teal'
    default: return 'outline'
  }
}

// FAQ — clés héritées de la version Stitch (US-023), alignées sur les locales.
const faqKeys = [
  'syntheticVsSurvey',
  'bindingDeliverable',
  'customizePersonas',
  'accuracy',
  'africaGroundedData',
  'enterpriseRetainers',
]

// ════════════════════════════════════════════════════════════════════
// State
// ════════════════════════════════════════════════════════════════════
const router = useRouter()
const { locale: i18nLocale } = useI18n()

const activeChip = ref('all')
const activeIndex = ref(0)
const carouselEl = ref(null)

// Toggle billing par package (Crisis Watch / Brand Pulse).
const billingMode = reactive({})
// Variants sélectionnées par package (Adcheck Pro / Cohort Replay).
const selectedVariant = reactive({})

const displayedPackages = computed(() => {
  if (activeChip.value === 'all') return packages
  return packages.filter((p) => p.tier === activeChip.value)
})

const trackStyle = computed(() => {
  // Chaque slide fait 100% / nbSlideVisible — desktop=3, tablet=1.5, mobile=1.
  // On translate par index courant. Le centrage vient du CSS (offset start).
  const offset = activeIndex.value * -100 // % par slide visible (1 sur mobile)
  return {
    transform: `translateX(${offset}%)`,
  }
})

function setActiveChip(id) {
  activeChip.value = id
  activeIndex.value = 0
}

function setBillingMode(packageId, mode) {
  billingMode[packageId] = mode
}

function setVariant(packageId, value) {
  selectedVariant[packageId] = value
}

function resolvedPrice(pkg) {
  // Variant override
  if (pkg.variants) {
    const value = selectedVariant[pkg.id] || pkg.variants.options[0].value
    const opt = pkg.variants.options.find((o) => o.value === value) || pkg.variants.options[0]
    return computeBilling(pkg, opt.priceMAD, opt.priceUSD)
  }
  return computeBilling(pkg, pkg.priceMAD, pkg.priceUSD)
}

function computeBilling(pkg, priceMAD, priceUSD) {
  if (priceMAD === null || priceMAD === undefined) {
    return { priceMAD: null, priceUSD: null }
  }
  // Annual mode : on facture (12 - annualDiscount) mois × prix mensuel,
  // ramené au mois équivalent affiché (priceMAD reste l'affichage mensuel
  // « lissé » : annual_total / 12). On affiche le prix mensuel équivalent.
  if (pkg.billing === 'monthly' && billingMode[pkg.id] === 'annual') {
    const months = 12 - (pkg.annualDiscount || 0)
    const annualTotal = priceMAD * months
    const annualTotalUsd = priceUSD * months
    return {
      priceMAD: Math.round(annualTotal / 12),
      priceUSD: Math.round(annualTotalUsd / 12),
    }
  }
  return { priceMAD, priceUSD }
}

function formatMad(value) {
  return value.toLocaleString(i18nLocale.value === 'ar' ? 'ar-MA' : 'fr-FR')
}

function formatUsd(value) {
  return value.toLocaleString('en-US')
}

// ════════════════════════════════════════════════════════════════════
// Carousel navigation
// ════════════════════════════════════════════════════════════════════
function goTo(idx) {
  if (idx < 0) idx = 0
  if (idx > displayedPackages.value.length - 1) idx = displayedPackages.value.length - 1
  activeIndex.value = idx
}

function next() {
  if (activeIndex.value < displayedPackages.value.length - 1) {
    activeIndex.value += 1
  }
}

function prev() {
  if (activeIndex.value > 0) {
    activeIndex.value -= 1
  }
}

// Touch swipe avec threshold 50 px.
let touchStartX = 0
function onTouchStart(e) {
  if (e.touches && e.touches[0]) {
    touchStartX = e.touches[0].clientX
  }
}
function onTouchEnd(e) {
  if (!e.changedTouches || !e.changedTouches[0]) return
  const dx = e.changedTouches[0].clientX - touchStartX
  if (Math.abs(dx) < 50) return
  // RTL inversion
  const isRtl = document.documentElement.getAttribute('dir') === 'rtl'
  if ((!isRtl && dx < 0) || (isRtl && dx > 0)) next()
  else prev()
}

// ════════════════════════════════════════════════════════════════════
// CTA → /devis (sauf custom → mailto)
// ════════════════════════════════════════════════════════════════════
function onCtaClick(pkg) {
  if (pkg.id === 'custom') {
    window.location.href = 'mailto:contact@ai-mpower.com?subject=' + encodeURIComponent('Demande sur-mesure Bassira')
    return
  }
  router.push({ name: 'Quote', query: { package: pkg.id } })
}

// Reset l'index si le filtre rétrécit la liste.
watch(displayedPackages, (list) => {
  if (activeIndex.value > list.length - 1) {
    activeIndex.value = Math.max(0, list.length - 1)
  }
})

// Clavier global pour la navigation pendant que la section est focus.
function onKeydown(e) {
  if (!carouselEl.value) return
  if (!carouselEl.value.contains(document.activeElement)) return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    prev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    next()
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   OFFERS — Carousel 10 packages (refonte L99)
   ═══════════════════════════════════════════════════════════
   Source unique de vérité Stitch :
   stitch_bassira_simulation_pricing_page/
   bassira_pricing_packages_simulation_solutions_2/code.html
   Palette M3 Stitch via variables locales --stitch-* scopées au composant. */

.offers-page {
  /* ── Alias --stitch-* → tokens globaux --wi-* (US-053) ──
     Les usages var(--stitch-*) dans ce composant sont conservés ;
     les valeurs sont désormais héritées des tokens globaux,
     ce qui active automatiquement le dark mode. */
  --stitch-primary-container: var(--wi-primary-container);
  --stitch-primary: var(--wi-primary);
  --stitch-on-primary: var(--wi-on-primary);
  --stitch-on-primary-fixed: #370e00;
  --stitch-on-primary-fixed-variant: #7f2b00;
  --stitch-primary-fixed: #ffdbce;
  --stitch-inverse-primary: var(--wi-inverse-primary);
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
  --stitch-tertiary-container: var(--wi-tertiary-container);
  --stitch-on-tertiary-container: var(--wi-on-tertiary-container);
  --stitch-secondary-fixed-dim: #7fd8a6;
  --stitch-on-secondary-fixed: #002111;

  /* Tiers tones additionnels */
  --stitch-warning-container: #ffd66b;
  --stitch-on-warning-container: #5c3d00;
  --stitch-violet-container: #c9b6ff;
  --stitch-on-violet-container: #2b1762;
  --stitch-outline-container: var(--wi-surface-container-high);
  --stitch-on-outline-container: var(--wi-on-surface-variant);

  --stitch-shadow-ambient: var(--wi-shadow-ambient);
  --stitch-shadow-soft: var(--wi-shadow-sm);
  --stitch-shadow-strong: var(--wi-shadow-lg);

  --stitch-font-display: var(--wi-font-heading);
  --stitch-font-body: var(--wi-font-body);

  min-height: 100vh;
  background: var(--stitch-surface);
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
.offers-topbar {
  display: flex;
  align-items: center;
  padding: 16px 32px;
  padding-inline-end: 110px;
  border-bottom: 1px solid #ebe5da;
  background: #fdfcfb;
  position: sticky;
  top: 0;
  z-index: 50;
}

.offers-back {
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
.offers-back:hover {
  color: var(--stitch-primary-container);
  background: var(--stitch-surface-container-low);
}
.offers-back-arrow {
  font-size: 20px !important;
}
[dir="rtl"] .offers-back-arrow {
  transform: scaleX(-1);
}

/* ── Main wrapper ───────────────────────────────────── */
.offers-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 32px;
}

/* ── Hero ───────────────────────────────────────────── */
.offers-hero {
  position: relative;
  text-align: center;
  padding: 80px 16px 48px;
  max-width: 880px;
  margin: 0 auto;
  overflow: hidden;
}

.offers-hero-blob {
  position: absolute;
  top: -96px;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  width: 500px;
  height: 500px;
  background: var(--stitch-primary-fixed);
  opacity: 0.3;
  filter: blur(48px);
  border-radius: var(--wi-radius-pill);
  z-index: -1;
  pointer-events: none;
  mix-blend-mode: multiply;
}

.offers-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--stitch-surface-container-high);
  color: var(--stitch-on-surface);
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  border: 1px solid var(--stitch-outline-variant);
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.01em;
  margin-bottom: 24px;
}
.offers-pill-icon {
  font-size: 18px !important;
}

.offers-headline {
  font-family: var(--stitch-font-display);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--stitch-on-surface);
  margin: 0 0 24px 0;
}

.offers-sub {
  font-family: var(--stitch-font-body);
  font-size: 18px;
  line-height: 1.6;
  font-weight: 400;
  color: var(--stitch-on-surface-variant);
  max-width: 640px;
  margin: 0 auto;
}

/* ── Filter chips ───────────────────────────────────── */
.offers-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin: 0 auto 32px;
  max-width: 960px;
  padding: 0 8px;
}

.offers-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--stitch-surface-container);
  color: var(--stitch-on-surface);
  padding: 8px 16px;
  border-radius: var(--wi-radius-pill);
  border: 1px solid transparent;
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.1s ease;
  white-space: nowrap;
}
.offers-chip:hover {
  background: var(--stitch-surface-container-high);
}
.offers-chip:active {
  transform: scale(0.98);
}
.offers-chip--active {
  background: var(--stitch-primary-container);
  color: #ffffff;
  border-color: var(--stitch-primary-container);
}
.offers-chip-emoji {
  font-size: 14px;
  line-height: 1;
}

/* ── Carousel ───────────────────────────────────────── */
.offers-carousel {
  position: relative;
  margin: 0 auto;
  max-width: 1200px;
  padding: 32px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  outline: none;
}
.offers-carousel:focus-visible {
  outline: 2px solid var(--stitch-primary-container);
  outline-offset: 4px;
  border-radius: var(--wi-radius-card);
}

.offers-track-viewport {
  flex: 1;
  overflow: hidden;
  padding: 24px 0;
}

.offers-track {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  align-items: stretch;
  transition: transform 0.4s cubic-bezier(0.22, 0.61, 0.36, 1);
  will-change: transform;
}

.offers-slide {
  flex: 0 0 100%;
  padding: 0 12px;
  display: flex;
  align-items: stretch;
  transition: opacity 0.3s ease, transform 0.4s ease;
  opacity: 0.6;
}
.offers-slide--active {
  opacity: 1;
}

@media (min-width: 768px) {
  .offers-slide {
    flex-basis: 55%;
    transform: scale(0.92);
  }
  .offers-slide--active {
    transform: scale(1);
  }
}

@media (min-width: 1024px) {
  .offers-slide {
    flex-basis: 33.3333%;
  }
}

/* Nav prev/next ronds */
.offers-nav {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: var(--wi-radius-pill);
  border: 1px solid var(--stitch-outline-variant);
  background: var(--stitch-surface-container-lowest);
  color: var(--stitch-on-surface);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--stitch-shadow-soft);
  transition: background 0.2s ease, color 0.2s ease, opacity 0.2s ease, transform 0.1s ease;
  z-index: 2;
}
.offers-nav:hover:not(:disabled) {
  background: var(--stitch-primary-container);
  color: #ffffff;
  border-color: var(--stitch-primary-container);
}
.offers-nav:active:not(:disabled) {
  transform: scale(0.96);
}
.offers-nav:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.offers-nav .material-symbols-outlined {
  font-size: 24px !important;
}
[dir="rtl"] .offers-nav--prev .material-symbols-outlined,
[dir="rtl"] .offers-nav--next .material-symbols-outlined {
  transform: scaleX(-1);
}

/* ── Dots indicator ─────────────────────────────────── */
.offers-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 8px 0 32px;
}

.offers-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--wi-radius-pill);
  background: var(--stitch-outline-variant);
  border: none;
  padding: 0;
  cursor: pointer;
  transition: background 0.2s ease, width 0.2s ease;
}
.offers-dot:hover {
  background: var(--stitch-primary-fixed);
}
.offers-dot--active {
  background: var(--stitch-primary-container);
  width: 20px;
}

/* ── Card ───────────────────────────────────────────── */
.offers-card {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  background: var(--stitch-surface-container-lowest);
  border: 1px solid rgba(222, 192, 182, 0.3);
  border-radius: var(--wi-radius-card);
  padding: 32px;
  box-shadow: var(--stitch-shadow-ambient);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.offers-card--active {
  box-shadow: var(--stitch-shadow-strong);
}
.offers-card--featured {
  border-top: 8px solid var(--stitch-primary-container);
  padding-top: 28px;
}

/* Badge « Most chosen » floating au-dessus */
.offers-most-chosen {
  position: absolute;
  top: -16px;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  background: var(--stitch-primary-container);
  color: #ffffff;
  padding: 4px 16px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 12px;
  line-height: 1.2;
  letter-spacing: 0.01em;
  box-shadow: var(--stitch-shadow-soft);
  white-space: nowrap;
  z-index: 2;
}
[dir="rtl"] .offers-most-chosen {
  transform: translateX(50%);
}

/* Sector badge pill (couleur dot par tier) */
.offers-sector {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding: 4px 12px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 12px;
  line-height: 1.2;
  letter-spacing: 0.01em;
  margin-bottom: 16px;
}
.offers-sector-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--wi-radius-pill);
}
.offers-sector--orange {
  background: rgba(255, 181, 152, 0.2);
  color: var(--stitch-on-primary-fixed);
}
.offers-sector--orange .offers-sector-dot {
  background: var(--stitch-inverse-primary);
}
.offers-sector--teal {
  background: rgba(0, 185, 199, 0.2);
  color: var(--stitch-on-tertiary-container);
}
.offers-sector--teal .offers-sector-dot {
  background: var(--stitch-tertiary-container);
}
.offers-sector--mint {
  background: rgba(127, 216, 166, 0.2);
  color: var(--stitch-on-secondary-fixed);
}
.offers-sector--mint .offers-sector-dot {
  background: var(--stitch-secondary-fixed-dim);
}
.offers-sector--warning {
  background: rgba(255, 214, 107, 0.25);
  color: var(--stitch-on-warning-container);
}
.offers-sector--warning .offers-sector-dot {
  background: var(--stitch-warning-container);
}
.offers-sector--violet {
  background: rgba(201, 182, 255, 0.25);
  color: var(--stitch-on-violet-container);
}
.offers-sector--violet .offers-sector-dot {
  background: var(--stitch-violet-container);
}
.offers-sector--outline {
  background: rgba(216, 209, 203, 0.4);
  color: var(--stitch-on-outline-container);
}
.offers-sector--outline .offers-sector-dot {
  background: var(--stitch-outline);
}

.offers-card-title {
  font-family: var(--stitch-font-display);
  font-size: 24px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--stitch-on-surface);
  margin: 0 0 8px 0;
}

.offers-card-delay {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--stitch-font-body);
  font-size: 12px;
  font-weight: 500;
  color: var(--stitch-on-surface-variant);
  margin: 0 0 12px 0;
}
.offers-card-delay-icon {
  font-size: 16px !important;
}

.offers-card-description {
  font-family: var(--stitch-font-body);
  font-size: 14px;
  line-height: 1.55;
  color: var(--stitch-on-surface-variant);
  margin: 0 0 20px 0;
}

/* ── Billing toggle (Crisis Watch / Brand Pulse) ────── */
.offers-billing-toggle {
  display: inline-flex;
  background: var(--stitch-surface-container);
  border-radius: var(--wi-radius-pill);
  padding: 4px;
  margin-bottom: 16px;
  align-self: flex-start;
}
.offers-billing-btn {
  background: transparent;
  border: none;
  color: var(--stitch-on-surface-variant);
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background 0.2s ease, color 0.2s ease;
}
.offers-billing-btn--active {
  background: var(--stitch-surface-container-lowest);
  color: var(--stitch-on-surface);
  box-shadow: var(--stitch-shadow-soft);
}
.offers-billing-badge {
  background: var(--stitch-primary-container);
  color: #ffffff;
  border-radius: var(--wi-radius-pill);
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

/* ── Variant selector ───────────────────────────────── */
.offers-variant {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}
.offers-variant-label {
  font-family: var(--stitch-font-body);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--stitch-on-surface-variant);
}
.offers-variant-select {
  appearance: none;
  width: 100%;
  background: var(--stitch-surface-container-low);
  border: 1px solid var(--stitch-outline-variant);
  border-radius: var(--wi-radius-interactive);
  padding: 10px 36px 10px 14px;
  font-family: var(--stitch-font-body);
  font-size: 14px;
  color: var(--stitch-on-surface);
  cursor: pointer;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2357423a'%3e%3cpath d='M7 10l5 5 5-5z'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 12px center;
  background-size: 18px;
}
[dir="rtl"] .offers-variant-select {
  background-position: left 12px center;
  padding: 10px 14px 10px 36px;
}
.offers-variant-select:focus {
  outline: none;
  border-color: var(--stitch-primary-container);
  box-shadow: 0 0 0 2px rgba(255, 133, 81, 0.2);
}

/* ── Price block ────────────────────────────────────── */
.offers-card-price {
  margin-bottom: 24px;
}
.offers-card-price-mad {
  display: block;
  font-family: var(--stitch-font-display);
  font-size: 32px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.01em;
  color: var(--stitch-on-surface);
}
.offers-card-price-mad--label {
  font-size: 24px;
  color: var(--stitch-primary);
}
.offers-card-price-currency {
  font-family: var(--stitch-font-body);
  font-size: 16px;
  font-weight: 400;
  color: var(--stitch-on-surface-variant);
  margin-inline-start: 4px;
}
.offers-card-price-usd {
  display: block;
  font-family: var(--stitch-font-body);
  font-size: 14px;
  color: var(--stitch-outline);
  margin-top: 4px;
}

.offers-card-divider {
  border: none;
  height: 1px;
  background: rgba(222, 192, 182, 0.4);
  margin: 0 0 24px 0;
}

.offers-card-bullets {
  list-style: none;
  margin: 0 0 24px 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-grow: 1;
}
.offers-card-bullet {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-family: var(--stitch-font-body);
  font-size: 14px;
  line-height: 1.55;
  color: var(--stitch-on-surface-variant);
}
.offers-card-bullet-icon {
  flex-shrink: 0;
  font-size: 18px !important;
  color: var(--stitch-primary-container);
  margin-top: 2px;
}

.offers-card-fineprint {
  font-family: var(--stitch-font-body);
  font-size: 12px;
  font-style: italic;
  color: var(--stitch-outline);
  margin: 0 0 16px 0;
}

.offers-card-cta {
  width: 100%;
  background: var(--stitch-primary-container);
  color: #ffffff;
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.01em;
  padding: 14px 24px;
  border: none;
  border-radius: var(--wi-radius-interactive);
  cursor: pointer;
  transition: opacity 0.2s ease, transform 0.1s ease;
  margin-top: auto;
}
.offers-card-cta:hover {
  opacity: 0.92;
}
.offers-card-cta:active {
  transform: scale(0.98);
}

/* ── Section title (FAQ) ────────────────────────────── */
.offers-section-title {
  font-family: var(--stitch-font-display);
  font-size: 32px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.01em;
  text-align: center;
  margin: 0 0 48px 0;
  color: var(--stitch-on-surface);
}

/* ── FAQ ────────────────────────────────────────────── */
.offers-faq {
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 0 96px;
}

.offers-faq-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.offers-faq-item {
  background: var(--stitch-surface-container-lowest);
  border: 1px solid rgba(222, 192, 182, 0.3);
  border-radius: var(--wi-radius-interactive);
  box-shadow: var(--stitch-shadow-soft);
  overflow: hidden;
}

.offers-faq-q {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 24px;
  cursor: pointer;
  list-style: none;
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 16px;
  line-height: 1.4;
  color: var(--stitch-on-surface);
}
.offers-faq-q::-webkit-details-marker {
  display: none;
}

.offers-faq-chevron {
  flex-shrink: 0;
  color: var(--stitch-outline);
  transition: transform 0.2s ease;
  font-size: 24px !important;
}
.offers-faq-item[open] .offers-faq-chevron {
  transform: rotate(180deg);
}

.offers-faq-a {
  padding: 8px 24px 24px 24px;
  border-top: 1px solid rgba(222, 192, 182, 0.2);
  font-family: var(--stitch-font-body);
  font-size: 16px;
  line-height: 1.6;
  color: var(--stitch-on-surface-variant);
}

/* ── Pre-Footer CTA strip ───────────────────────────── */
.offers-cta-strip {
  background: var(--stitch-surface-container);
  border-top: 1px solid rgba(222, 192, 182, 0.3);
  padding: 96px 32px;
  text-align: center;
}

.offers-cta-strip-title {
  font-family: var(--stitch-font-display);
  font-size: 24px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--stitch-on-surface);
  margin: 0 0 16px 0;
}
.offers-cta-strip-body {
  font-family: var(--stitch-font-body);
  font-size: 18px;
  line-height: 1.6;
  color: var(--stitch-on-surface-variant);
  max-width: 560px;
  margin: 0 auto 32px auto;
}

.offers-cta-strip-btn {
  display: inline-block;
  background: transparent;
  color: var(--stitch-on-surface);
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.01em;
  padding: 14px 32px;
  border: 2px solid var(--stitch-outline);
  border-radius: var(--wi-radius-interactive);
  text-decoration: none;
  transition: border-color 0.2s ease, color 0.2s ease;
  cursor: pointer;
}
.offers-cta-strip-btn:hover {
  border-color: var(--stitch-primary-container);
  color: var(--stitch-primary-container);
}

/* ── Mobile tweaks ──────────────────────────────────── */
@media (max-width: 767px) {
  .offers-hero {
    padding: 48px 16px 24px;
  }
  .offers-main {
    padding: 0 12px;
  }
  .offers-carousel {
    padding: 16px 0;
  }
  .offers-card {
    padding: 24px;
  }
  .offers-section-title {
    font-size: 26px;
    margin-bottom: 32px;
  }
  .offers-faq {
    padding: 32px 0 64px;
  }
  .offers-cta-strip {
    padding: 64px 16px;
  }
  /* Sur mobile, on cache les boutons prev/next pour laisser place au swipe */
  .offers-nav {
    width: 40px;
    height: 40px;
  }
  .offers-nav .material-symbols-outlined {
    font-size: 20px !important;
  }
}
</style>
