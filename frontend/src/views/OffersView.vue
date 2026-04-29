<template>
  <div class="offers-page">
    <!-- ───────────── Top bar (retour vers /) ─────────────
         LanguageSwitcher est mounté globalement par App.vue en widget
         flottant top-right. On expose juste un retour vers la home. -->
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

      <!-- ───────────── 3 cards (pricing) ─────────────
           Card du milieu (policyBrief) en featured : bord supérieur orange
           épais, badge « Le plus demandé » qui flotte au-dessus, légère
           translation verticale en desktop. -->
      <section class="offers-grid" aria-label="Packages Bassira">
        <article
          v-for="pkg in packages"
          :key="pkg.id"
          class="offers-card"
          :class="{ 'offers-card--featured': pkg.featured }"
        >
          <span
            v-if="pkg.featured"
            class="offers-most-chosen"
          >
            {{ $t('offers.featuredBadge') }}
          </span>

          <span
            class="offers-sector"
            :class="`offers-sector--${pkg.sectorTone}`"
          >
            <span class="offers-sector-dot" aria-hidden="true"></span>
            {{ $t(`offers.packages.${pkg.id}.sector`) }}
          </span>

          <h3 class="offers-card-title">{{ $t(`offers.packages.${pkg.id}.name`) }}</h3>

          <p class="offers-card-delay">
            <span class="material-symbols-outlined offers-card-delay-icon" aria-hidden="true">schedule</span>
            {{ $t(`offers.packages.${pkg.id}.delay`) }}
          </p>

          <div class="offers-card-price">
            <span class="offers-card-price-mad">
              {{ pkg.priceMad.toLocaleString('fr-FR') }}
              <span class="offers-card-price-currency">MAD</span>
            </span>
            <span class="offers-card-price-usd">${{ pkg.priceUsd.toLocaleString('en-US') }}</span>
          </div>

          <hr class="offers-card-divider" />

          <ul class="offers-card-bullets">
            <li
              v-for="i in 6"
              :key="i"
              class="offers-card-bullet"
            >
              <span class="material-symbols-outlined offers-card-bullet-icon" aria-hidden="true">check_circle</span>
              <span>{{ $t(`offers.packages.${pkg.id}.bullets.b${i}`) }}</span>
            </li>
          </ul>

          <button
            type="button"
            class="offers-card-cta"
            @click="requestQuote(pkg)"
          >
            {{ $t(`offers.packages.${pkg.id}.cta`) }}
          </button>
        </article>
      </section>

      <!-- ───────────── Trust strip (« Why our predictions land ») ───────────── -->
      <section class="offers-trust">
        <h2 class="offers-section-title">{{ $t('offers.trust.title') }}</h2>
        <div class="offers-trust-grid">
          <component
            v-for="item in trustItems"
            :key="item.id"
            :is="item.id === 'brier' ? 'router-link' : 'div'"
            :to="item.id === 'brier' ? '/calibration' : undefined"
            class="offers-trust-card"
            :class="{ 'offers-trust-card--link': item.id === 'brier' }"
          >
            <div class="offers-trust-icon">
              <span class="material-symbols-outlined" aria-hidden="true">{{ item.icon }}</span>
            </div>
            <h4 class="offers-trust-card-title">{{ $t(`offers.trust.items.${item.id}.title`) }}</h4>
            <p class="offers-trust-card-body">{{ $t(`offers.trust.items.${item.id}.body`) }}</p>
          </component>
        </div>
      </section>

      <!-- ───────────── FAQ (6 questions) ───────────── -->
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

    <!-- ───────────── Pre-Footer CTA (rose pâle) ───────────── -->
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
import { useRouter } from 'vue-router'

// ─── Catalogue des 3 packages — design Stitch fidèle.
// `id` correspond aux clés i18n offers.packages.<id>.*
// `priceMad` / `priceUsd` restent en JS (jamais traduits).
// `sectorTone` : 'orange' | 'teal' | 'mint' — palette du badge sector.
// `quotePackage` : id backend canonique pour POST /api/quote.
const packages = [
  {
    id: 'crisisDrill',
    featured: false,
    priceMad: 12000,
    priceUsd: 1200,
    sectorTone: 'orange',
    quotePackage: 'crisis_drill_24h',
  },
  {
    id: 'policyBrief',
    featured: true,
    priceMad: 35000,
    priceUsd: 3500,
    sectorTone: 'teal',
    quotePackage: 'policy_brief_stress',
  },
  {
    id: 'preLaunch',
    featured: false,
    priceMad: 20000,
    priceUsd: 2000,
    sectorTone: 'mint',
    quotePackage: 'pre_launch_adcheck',
  },
]

// Trust strip — 3 cartes alignées sur le mockup Stitch.
const trustItems = [
  { id: 'brier', icon: 'analytics' },
  { id: 'multiLocale', icon: 'translate' },
  { id: 'africaData', icon: 'public' },
]

// FAQ — 6 questions dans l'ordre exact du mockup Stitch.
const faqKeys = [
  'syntheticVsSurvey',
  'bindingDeliverable',
  'customizePersonas',
  'accuracy',
  'africaGroundedData',
  'enterpriseRetainers',
]

const router = useRouter()

// CTA principal de chaque card — push vers /devis avec le package préselectionné.
function requestQuote(pkg) {
  router.push({ name: 'Quote', query: { package: pkg.quotePackage } })
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   OFFERS — Refonte fidèle au mockup Stitch (US-023 v2)
   ═══════════════════════════════════════════════════════════
   Source unique de vérité : stitch_bassira_simulation_pricing_page/
   bassira_pricing_packages_simulation_solutions_2/code.html
   On n'utilise PAS Tailwind ; on reproduit la palette M3 Stitch
   via des variables locales `--stitch-*` scopées au composant. */

.offers-page {
  /* Variables Stitch locales — palette exacte du mockup. */
  --stitch-primary-container: #ff8551;
  --stitch-primary: #a13f0f;
  --stitch-on-primary: #ffffff;
  --stitch-on-primary-fixed: #370e00;
  --stitch-on-primary-fixed-variant: #7f2b00;
  --stitch-primary-fixed: #ffdbce;
  --stitch-inverse-primary: #ffb598;
  --stitch-surface: #fff8f6;
  --stitch-surface-container: #ffeae2;
  --stitch-surface-container-low: #fff1ec;
  --stitch-surface-container-lowest: #ffffff;
  --stitch-surface-container-high: #f9e4dd;
  --stitch-surface-container-highest: #f3ded7;
  --stitch-on-surface: #241915;
  --stitch-on-surface-variant: #57423a;
  --stitch-outline: #8a7269;
  --stitch-outline-variant: #dec0b6;
  --stitch-tertiary-container: #00b9c7;
  --stitch-on-tertiary-container: #00444a;
  --stitch-secondary-fixed-dim: #7fd8a6;
  --stitch-on-secondary-fixed: #002111;

  --stitch-shadow-ambient: 0 12px 32px rgba(74, 69, 64, 0.08);
  --stitch-shadow-soft: 0 1px 2px rgba(74, 69, 64, 0.05);

  --stitch-font-display: 'Outfit', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  --stitch-font-body: 'Manrope', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;

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
  /* Réserve la place pour le LanguageSwitcher floating top-right
     (z-index 1500) — cohérent avec Home.vue / CalibrationView.vue. */
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
  border-radius: 9999px;
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
}

/* ── Hero ───────────────────────────────────────────── */
.offers-hero {
  position: relative;
  text-align: center;
  padding: 96px 16px 64px;
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
  border-radius: 9999px;
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
  border-radius: 9999px;
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

/* ── Cards grid ─────────────────────────────────────── */
.offers-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 32px;
  align-items: stretch;
  margin: 0 auto 96px;
  max-width: 1200px;
}

@media (min-width: 768px) {
  .offers-grid {
    grid-template-columns: repeat(3, 1fr);
    align-items: stretch;
  }
}

.offers-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--stitch-surface-container-lowest);
  border: 1px solid rgba(222, 192, 182, 0.3);
  border-radius: 24px;
  padding: 32px;
  box-shadow: var(--stitch-shadow-ambient);
  height: 100%;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.offers-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(74, 69, 64, 0.12);
}

@media (min-width: 768px) {
  .offers-card--featured {
    border-top: 8px solid var(--stitch-primary-container);
    border-inline: 1px solid rgba(222, 192, 182, 0.3);
    border-bottom: 1px solid rgba(222, 192, 182, 0.3);
    transform: translateY(-16px);
  }
  .offers-card--featured:hover {
    transform: translateY(-20px);
  }
}
.offers-card--featured {
  /* Mobile : juste un liseré orange épais en haut. */
  border-top: 8px solid var(--stitch-primary-container);
  padding-top: 28px;
}

/* Badge « Most chosen » qui flotte au-dessus de la card featured. */
.offers-most-chosen {
  position: absolute;
  top: -16px;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  background: var(--stitch-primary-container);
  color: #ffffff;
  padding: 4px 16px;
  border-radius: 9999px;
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

/* Badge sector (pill avec dot coloré). */
.offers-sector {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding: 4px 12px;
  border-radius: 9999px;
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
  border-radius: 9999px;
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
  margin: 0 0 24px 0;
}
.offers-card-delay-icon {
  font-size: 16px !important;
}

.offers-card-price {
  margin-bottom: 32px;
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
  font-size: 16px;
  color: var(--stitch-outline);
  margin-top: 4px;
}

.offers-card-divider {
  border: none;
  height: 1px;
  background: rgba(222, 192, 182, 0.4);
  margin: 0 0 32px 0;
}

.offers-card-bullets {
  list-style: none;
  margin: 0 0 32px 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-grow: 1;
}
.offers-card-bullet {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-family: var(--stitch-font-body);
  font-size: 16px;
  line-height: 1.6;
  color: var(--stitch-on-surface-variant);
}
.offers-card-bullet-icon {
  flex-shrink: 0;
  font-size: 20px !important;
  color: var(--stitch-primary-container);
  margin-top: 2px;
}

.offers-card-cta {
  width: 100%;
  background: var(--stitch-primary-container);
  color: #ffffff;
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.01em;
  padding: 16px 24px;
  border: none;
  border-radius: 12px;
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

/* ── Section title commun (trust + faq) ─────────────── */
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

/* ── Trust strip ────────────────────────────────────── */
.offers-trust {
  background: var(--stitch-surface-container-low);
  margin: 0 -32px 0 -32px;
  padding: 80px 32px;
}
.offers-trust > .offers-section-title,
.offers-trust > .offers-trust-grid {
  max-width: 1100px;
  margin-inline: auto;
}

.offers-trust-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}
@media (min-width: 768px) {
  .offers-trust-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.offers-trust-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  background: var(--stitch-surface-container-lowest);
  border: 1px solid rgba(222, 192, 182, 0.2);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--stitch-shadow-soft);
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.offers-trust-card--link:hover {
  border-color: var(--stitch-primary-container);
  transform: translateY(-2px);
}

.offers-trust-icon {
  width: 48px;
  height: 48px;
  border-radius: 9999px;
  background: var(--stitch-surface-container-highest);
  color: var(--stitch-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  transition: background 0.2s ease, color 0.2s ease;
}
.offers-trust-icon .material-symbols-outlined {
  font-size: 24px !important;
}
.offers-trust-card--link:hover .offers-trust-icon {
  background: var(--stitch-primary-container);
  color: #ffffff;
}

.offers-trust-card-title {
  font-family: var(--stitch-font-body);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.01em;
  color: var(--stitch-on-surface);
  margin: 0 0 8px 0;
}
.offers-trust-card-body {
  font-family: var(--stitch-font-body);
  font-size: 12px;
  line-height: 1.5;
  color: var(--stitch-on-surface-variant);
  margin: 0;
}

/* ── FAQ ────────────────────────────────────────────── */
.offers-faq {
  max-width: 720px;
  margin: 0 auto;
  padding: 96px 0;
}

.offers-faq-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.offers-faq-item {
  background: var(--stitch-surface-container-lowest);
  border: 1px solid rgba(222, 192, 182, 0.3);
  border-radius: 12px;
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

/* ── Pre-Footer CTA strip (rose pâle) ───────────────── */
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
  border-radius: 12px;
  text-decoration: none;
  transition: border-color 0.2s ease, color 0.2s ease;
  cursor: pointer;
}
.offers-cta-strip-btn:hover {
  border-color: var(--stitch-primary-container);
  color: var(--stitch-primary-container);
}

/* ── Mobile tweaks (< 768 px) ───────────────────────── */
@media (max-width: 767px) {
  .offers-hero {
    padding: 64px 16px 32px;
  }
  .offers-main {
    padding: 0 16px;
  }
  .offers-grid {
    margin-bottom: 64px;
  }
  .offers-trust {
    margin: 0 -16px;
    padding: 64px 16px;
  }
  .offers-section-title {
    font-size: 26px;
    margin-bottom: 32px;
  }
  .offers-faq {
    padding: 64px 0;
  }
  .offers-cta-strip {
    padding: 64px 16px;
  }
  .offers-card {
    padding: 24px;
  }
}
</style>
