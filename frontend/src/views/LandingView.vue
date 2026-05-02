<template>
  <div class="lp-page" :lang="$i18n.locale">
    <!-- ═══════════════════════════════════════════════════════════
         US-061 — Landing page SEO Bassira
         Cible : C-Level / Strategy Director MENA + Europe
         Audience cold (LinkedIn, Google) — 8 sec d'attention.
         Tokens : --wi-* (Warm Intelligence) + --ms-* (Playful & Soft).
         RTL : CSS logical properties (margin-inline, padding-inline).
         ═══════════════════════════════════════════════════════════ -->

    <!-- ───────────── Top bar minimaliste ───────────── -->
    <header class="lp-topbar">
      <router-link to="/" class="lp-brand" :title="$t('nav.brand')">
        {{ $t('nav.brand') }}
      </router-link>
      <nav class="lp-nav" :aria-label="$t('landing.nav.ariaLabel')">
        <router-link :to="{ name: 'Calibration' }" class="lp-nav-link">
          {{ $t('landing.nav.calibration') }}
        </router-link>
        <router-link :to="{ name: 'Offers' }" class="lp-nav-link">
          {{ $t('landing.nav.pricing') }}
        </router-link>
        <router-link :to="{ name: 'Quote' }" class="lp-nav-cta">
          {{ $t('landing.nav.demo') }}
        </router-link>
      </nav>
    </header>

    <main class="lp-main">
      <!-- ═══════════════════════════════════════════════════════
           1. HERO — 100vh, eyebrow + H1 + sub + 2 CTAs
           Formule H1 : outcome + timeframe + without painful thing.
           ═══════════════════════════════════════════════════════ -->
      <section class="lp-hero" :aria-label="$t('landing.hero.ariaLabel')">
        <div aria-hidden="true" class="lp-hero-glow"></div>

        <span class="lp-eyebrow">
          <span class="lp-eyebrow-arabic" aria-hidden="true">بصيرة</span>
          <span class="lp-eyebrow-dot" aria-hidden="true">·</span>
          <span>{{ $t('landing.hero.eyebrow') }}</span>
        </span>

        <h1 class="lp-h1">{{ $t('landing.hero.title') }}</h1>

        <p class="lp-hero-sub">{{ $t('landing.hero.subtitle') }}</p>

        <div class="lp-cta-row">
          <router-link
            :to="{ name: 'Quote' }"
            class="lp-btn lp-btn--primary"
            :aria-label="$t('landing.hero.ctaPrimary')"
          >
            <span>{{ $t('landing.hero.ctaPrimary') }}</span>
            <span class="lp-btn-arrow" aria-hidden="true">→</span>
          </router-link>

          <router-link
            :to="{ name: 'Explore' }"
            class="lp-btn lp-btn--ghost"
            :aria-label="$t('landing.hero.ctaSecondary')"
          >
            <span>{{ $t('landing.hero.ctaSecondary') }}</span>
            <span class="lp-btn-arrow" aria-hidden="true">→</span>
          </router-link>
        </div>

        <!-- Trust strip discrète sous les CTAs -->
        <p class="lp-hero-trust">{{ $t('landing.hero.trust') }}</p>
      </section>

      <!-- ═══════════════════════════════════════════════════════
           2. PAIN — 3 cards quote-format
           Chaque card : icône + douleur (italique, ton client) +
           pivot « Avec Bassira : » + solution concise.
           ═══════════════════════════════════════════════════════ -->
      <section class="lp-pains" :aria-labelledby="painsHeadingId">
        <div class="lp-section-head">
          <span class="lp-kicker">{{ $t('landing.pains.kicker') }}</span>
          <h2 :id="painsHeadingId" class="lp-h2">{{ $t('landing.pains.title') }}</h2>
        </div>

        <div class="lp-pain-grid">
          <article
            v-for="painKey in painKeys"
            :key="painKey"
            class="lp-pain-card"
          >
            <div class="lp-pain-icon" aria-hidden="true">
              <span class="material-symbols-outlined">{{ painIcons[painKey] }}</span>
            </div>
            <p class="lp-pain-quote">
              <span class="lp-pain-quote-mark" aria-hidden="true">«</span>
              {{ $t(`landing.pains.${painKey}.quote`) }}
              <span class="lp-pain-quote-mark" aria-hidden="true">»</span>
            </p>
            <div class="lp-pain-pivot">
              <span class="lp-pain-pivot-label">{{ $t('landing.pains.pivotLabel') }}</span>
              <p class="lp-pain-solution">{{ $t(`landing.pains.${painKey}.solution`) }}</p>
            </div>
          </article>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════
           3. PRODUCT — split layout
           Visuel à gauche (mock dashboard simplifié),
           3 capabilities à droite avec checkmarks mint.
           ═══════════════════════════════════════════════════════ -->
      <section class="lp-product" :aria-labelledby="productHeadingId">
        <div class="lp-product-grid">
          <!-- Visual / mock illustration -->
          <div class="lp-product-visual" aria-hidden="true">
            <div class="lp-mock">
              <div class="lp-mock-chrome">
                <span class="lp-mock-dot"></span>
                <span class="lp-mock-dot"></span>
                <span class="lp-mock-dot"></span>
                <span class="lp-mock-title">bassira · simulation</span>
              </div>
              <div class="lp-mock-body">
                <div class="lp-mock-row">
                  <span class="lp-mock-label">Brier score</span>
                  <span class="lp-mock-value lp-mock-value--mint">0.18</span>
                </div>
                <div class="lp-mock-bar">
                  <div class="lp-mock-bar-fill" style="--lp-fill: 82%"></div>
                </div>
                <div class="lp-mock-row">
                  <span class="lp-mock-label">Agents · Tier-1 banks · MENA</span>
                  <span class="lp-mock-value">5 132</span>
                </div>
                <div class="lp-mock-row">
                  <span class="lp-mock-label">Scenarios run</span>
                  <span class="lp-mock-value">10 248</span>
                </div>
                <div class="lp-mock-tags">
                  <span class="lp-mock-tag">geopolitics</span>
                  <span class="lp-mock-tag">FX</span>
                  <span class="lp-mock-tag">supply</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Capabilities -->
          <div class="lp-product-copy">
            <span class="lp-kicker">{{ $t('landing.product.kicker') }}</span>
            <h2 :id="productHeadingId" class="lp-h2">{{ $t('landing.product.title') }}</h2>
            <p class="lp-product-lead">{{ $t('landing.product.lead') }}</p>

            <ul class="lp-cap-list">
              <li
                v-for="capKey in capabilityKeys"
                :key="capKey"
                class="lp-cap"
              >
                <span class="lp-cap-check" aria-hidden="true">
                  <svg viewBox="0 0 16 16" width="14" height="14" fill="none">
                    <path d="M3 8.5l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </span>
                <div class="lp-cap-body">
                  <h3 class="lp-cap-title">{{ $t(`landing.product.${capKey}.title`) }}</h3>
                  <p class="lp-cap-desc">{{ $t(`landing.product.${capKey}.desc`) }}</p>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════
           4. PROOF — fond dark cinématique, Brier score 0.18
           ═══════════════════════════════════════════════════════ -->
      <section class="lp-proof" :aria-labelledby="proofHeadingId">
        <div class="lp-proof-inner">
          <span class="lp-kicker lp-kicker--on-dark">{{ $t('landing.proof.kicker') }}</span>
          <h2 :id="proofHeadingId" class="lp-h2 lp-h2--on-dark">
            {{ $t('landing.proof.title') }}
          </h2>

          <div class="lp-proof-figure">
            <div class="lp-proof-num">0.18</div>
            <div class="lp-proof-figure-meta">
              <span class="lp-proof-label">{{ $t('landing.proof.metric') }}</span>
              <span class="lp-proof-context">{{ $t('landing.proof.context') }}</span>
            </div>
          </div>

          <p class="lp-proof-body">{{ $t('landing.proof.body') }}</p>

          <router-link
            :to="{ name: 'Calibration' }"
            class="lp-btn lp-btn--ghost-dark"
          >
            <span>{{ $t('landing.proof.cta') }}</span>
            <span class="lp-btn-arrow" aria-hidden="true">→</span>
          </router-link>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════
           5. PRICING TEASER — 3 mini-cards prix
           ═══════════════════════════════════════════════════════ -->
      <section class="lp-pricing" :aria-labelledby="pricingHeadingId">
        <div class="lp-section-head">
          <span class="lp-kicker">{{ $t('landing.pricing.kicker') }}</span>
          <h2 :id="pricingHeadingId" class="lp-h2">{{ $t('landing.pricing.title') }}</h2>
          <p class="lp-section-sub">{{ $t('landing.pricing.subtitle') }}</p>
        </div>

        <div class="lp-pricing-grid">
          <article
            v-for="tier in pricingTiers"
            :key="tier.id"
            class="lp-price-card"
            :class="{ 'lp-price-card--featured': tier.featured }"
          >
            <div v-if="tier.featured" class="lp-price-flag">
              {{ $t('landing.pricing.featuredFlag') }}
            </div>
            <h3 class="lp-price-name">{{ $t(`landing.pricing.tiers.${tier.id}.name`) }}</h3>
            <p class="lp-price-tag">{{ $t(`landing.pricing.tiers.${tier.id}.tag`) }}</p>
            <div class="lp-price-amount">
              <span class="lp-price-from">{{ $t('landing.pricing.from') }}</span>
              <span class="lp-price-mad">{{ formatNumber(tier.priceMAD) }} MAD</span>
              <span class="lp-price-usd">/ ${{ formatNumber(tier.priceUSD) }} USD</span>
            </div>
            <p class="lp-price-blurb">{{ $t(`landing.pricing.tiers.${tier.id}.blurb`) }}</p>
          </article>
        </div>

        <div class="lp-pricing-cta">
          <router-link :to="{ name: 'Offers' }" class="lp-btn lp-btn--primary">
            <span>{{ $t('landing.pricing.cta') }}</span>
            <span class="lp-btn-arrow" aria-hidden="true">→</span>
          </router-link>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════
           6. FINAL CTA — full-width terracotta band
           ═══════════════════════════════════════════════════════ -->
      <section class="lp-final" :aria-labelledby="finalHeadingId">
        <div class="lp-final-inner">
          <h2 :id="finalHeadingId" class="lp-final-title">
            {{ $t('landing.finalCta.title') }}
          </h2>
          <p class="lp-final-sub">{{ $t('landing.finalCta.subtitle') }}</p>
          <router-link :to="{ name: 'Quote' }" class="lp-btn lp-btn--final">
            <span>{{ $t('landing.finalCta.cta') }}</span>
            <span class="lp-btn-arrow" aria-hidden="true">→</span>
          </router-link>
        </div>
      </section>
    </main>

    <!-- ───────────── Footer minimal ───────────── -->
    <footer class="lp-footer">
      <div class="lp-footer-inner">
        <span class="lp-footer-brand">{{ $t('nav.brand') }}</span>
        <span class="lp-footer-tag">{{ $t('landing.footer.tagline') }}</span>
        <nav class="lp-footer-nav" :aria-label="$t('landing.footer.navAria')">
          <router-link :to="{ name: 'Calibration' }" class="lp-footer-link">
            {{ $t('landing.nav.calibration') }}
          </router-link>
          <router-link :to="{ name: 'Offers' }" class="lp-footer-link">
            {{ $t('landing.nav.pricing') }}
          </router-link>
          <router-link :to="{ name: 'Quote' }" class="lp-footer-link">
            {{ $t('landing.nav.demo') }}
          </router-link>
        </nav>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

// ════════════════════════════════════════════════════════════════════
// Static data — IDs côté JS, copy côté i18n.
// ════════════════════════════════════════════════════════════════════

const { locale } = useI18n()

// Heading IDs uniques (a11y : aria-labelledby).
const painsHeadingId = 'lp-pains-h'
const productHeadingId = 'lp-product-h'
const proofHeadingId = 'lp-proof-h'
const pricingHeadingId = 'lp-pricing-h'
const finalHeadingId = 'lp-final-h'

// Pains : 3 cards. Icônes Material Symbols (chargées via index.html).
const painKeys = ['speed', 'blindspot', 'cost']
const painIcons = {
  speed: 'hourglass_empty',
  blindspot: 'visibility_off',
  cost: 'account_balance_wallet',
}

// Capabilities : 3 features clés.
const capabilityKeys = ['agents', 'calibrated', 'sovereign']

// Pricing teaser : 3 paliers, mêmes IDs que /offres pour cohérence.
const pricingTiers = [
  { id: 'discovery', priceMAD: 10000, priceUSD: 1000 },
  { id: 'drill', priceMAD: 20000, priceUSD: 2000, featured: true },
  { id: 'twin', priceMAD: 80000, priceUSD: 8000 },
]

// Format des nombres respectant la locale active (fr-FR, en-US, ar-MA).
const numberFormatter = computed(() => {
  const tag = locale.value === 'ar' ? 'ar-MA' : (locale.value === 'en' ? 'en-US' : 'fr-FR')
  return new Intl.NumberFormat(tag)
})
function formatNumber (n) {
  return numberFormatter.value.format(n)
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   LandingView — styles 100 % tokens (--wi-*, --ms-*).
   Aucun hex hardcodé. RTL via CSS logical properties.
   ═══════════════════════════════════════════════════════════ */

.lp-page {
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ───── Topbar ───── */
.lp-topbar {
  position: sticky;
  top: 0;
  z-index: var(--ms-z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-block: var(--wi-space-sm);
  padding-inline: var(--wi-space-lg);
  background: color-mix(in srgb, var(--wi-bg) 88%, transparent);
  backdrop-filter: blur(12px);
  border-block-end: 1px solid var(--wi-outline-variant);
}
.lp-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: var(--wi-h3-size);
  color: var(--wi-on-bg);
  text-decoration: none;
  letter-spacing: -0.02em;
}
.lp-nav {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
}
.lp-nav-link {
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-size: var(--wi-body-md);
  font-weight: 500;
  padding-inline: var(--wi-space-xs);
  padding-block: 6px;
  border-radius: var(--wi-radius-sm);
  transition: color var(--ms-transition), background var(--ms-transition);
}
.lp-nav-link:hover {
  color: var(--wi-primary);
  background: var(--wi-surface-container-low);
}
.lp-nav-cta {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  padding-inline: var(--wi-space-sm);
  padding-block: 10px;
  border-radius: var(--wi-radius-interactive);
  font-weight: 600;
  font-size: var(--wi-body-md);
  text-decoration: none;
  transition: background var(--ms-transition), transform var(--ms-transition);
  box-shadow: var(--wi-shadow-sm);
}
.lp-nav-cta:hover {
  background: var(--ms-orange-strong);
  transform: translateY(-1px);
}

/* Mobile : nav simplifiée */
@media (max-width: 720px) {
  .lp-topbar {
    padding-inline: var(--wi-space-sm);
  }
  .lp-nav-link {
    display: none;
  }
}

/* ───── Main wrapper ───── */
.lp-main {
  display: flex;
  flex-direction: column;
}

/* ═══════════════════════════════════════════════════════════
   1. HERO — 100vh, centré, eyebrow + H1 + sub + CTAs
   ═══════════════════════════════════════════════════════════ */
.lp-hero {
  position: relative;
  min-height: calc(100vh - 72px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding-inline: var(--wi-space-md);
  padding-block: var(--wi-space-xl);
  overflow: hidden;
}
.lp-hero-glow {
  position: absolute;
  inset-block-start: -20%;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  width: min(900px, 90%);
  height: 600px;
  background: radial-gradient(
    ellipse at center,
    var(--wi-primary-container) 0%,
    transparent 60%
  );
  opacity: 0.18;
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}
.lp-hero > * {
  position: relative;
  z-index: 1;
}

.lp-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  background: var(--ms-orange-soft);
  color: var(--wi-primary);
  padding-inline: var(--wi-space-sm);
  padding-block: 8px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-label-sm);
  letter-spacing: 0.02em;
  border: 1px solid color-mix(in srgb, var(--wi-primary) 18%, transparent);
  margin-block-end: var(--wi-space-md);
}
.lp-eyebrow-arabic {
  font-family: 'Tajawal', var(--wi-font-heading), sans-serif;
  font-weight: 700;
}
.lp-eyebrow-dot {
  opacity: 0.4;
}

.lp-h1 {
  font-family: var(--wi-font-heading);
  font-weight: var(--wi-h1-weight);
  font-size: clamp(36px, 5.6vw, 64px);
  line-height: 1.08;
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-bg);
  max-inline-size: 920px;
  margin-block-end: var(--wi-space-md);
  margin-inline: auto;
}
.lp-hero-sub {
  font-size: clamp(17px, 1.6vw, 20px);
  line-height: 1.55;
  color: var(--wi-on-surface-variant);
  max-inline-size: 660px;
  margin-block-end: var(--wi-space-lg);
  margin-inline: auto;
}

/* CTAs row */
.lp-cta-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--wi-space-sm);
  margin-block-end: var(--wi-space-md);
}
.lp-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  padding-inline: var(--wi-space-md);
  padding-block: 14px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-body-md);
  text-decoration: none;
  transition: transform var(--ms-transition), background var(--ms-transition),
              box-shadow var(--ms-transition), color var(--ms-transition);
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
}
.lp-btn-arrow {
  transition: transform var(--ms-transition);
}
[dir="rtl"] .lp-btn-arrow {
  transform: scaleX(-1);
}
.lp-btn:hover .lp-btn-arrow {
  transform: translateX(3px);
}
[dir="rtl"] .lp-btn:hover .lp-btn-arrow {
  transform: scaleX(-1) translateX(3px);
}

/* Primary CTA → terracotta deep (--wi-primary) */
.lp-btn--primary {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  box-shadow: var(--wi-shadow-md);
}
.lp-btn--primary:hover {
  background: var(--ms-orange-strong);
  transform: translateY(-2px);
  box-shadow: var(--wi-shadow-lg);
}

/* Ghost orange */
.lp-btn--ghost {
  background: transparent;
  color: var(--wi-primary);
  border-color: var(--wi-primary);
}
.lp-btn--ghost:hover {
  background: var(--ms-orange-soft);
  transform: translateY(-2px);
}

.lp-hero-trust {
  font-size: var(--wi-caption);
  color: var(--wi-outline);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-weight: 500;
}

/* ═══════════════════════════════════════════════════════════
   2. PAINS — 3 cards quote-format
   ═══════════════════════════════════════════════════════════ */
.lp-pains {
  background: var(--wi-surface-container-low);
  padding-block: var(--wi-space-xl);
  padding-inline: var(--wi-space-md);
}
.lp-section-head {
  max-inline-size: 900px;
  margin-inline: auto;
  text-align: center;
  margin-block-end: var(--wi-space-lg);
}
.lp-kicker {
  display: inline-block;
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-primary);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 600;
  margin-block-end: var(--ms-space-3);
}
.lp-kicker--on-dark {
  color: var(--ms-orange);
}
.lp-h2 {
  font-family: var(--wi-font-heading);
  font-weight: var(--wi-h2-weight);
  font-size: clamp(28px, 3.4vw, var(--wi-h2-size));
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-bg);
  margin-block-end: var(--ms-space-3);
}
.lp-h2--on-dark {
  color: var(--ms-bg);
}
.lp-section-sub {
  font-size: var(--wi-body-lg);
  color: var(--wi-on-surface-variant);
  max-inline-size: 620px;
  margin-inline: auto;
  line-height: 1.55;
}

.lp-pain-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--wi-space-md);
  max-inline-size: 1200px;
  margin-inline: auto;
}
.lp-pain-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  transition: transform var(--ms-transition), box-shadow var(--ms-transition),
              border-color var(--ms-transition);
}
.lp-pain-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--wi-shadow-md);
  border-color: color-mix(in srgb, var(--wi-primary) 35%, var(--wi-outline-variant));
}
.lp-pain-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--wi-radius-md);
  background: var(--ms-orange-soft);
  color: var(--wi-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.lp-pain-icon .material-symbols-outlined {
  font-size: 28px;
}
.lp-pain-quote {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-lg);
  line-height: 1.5;
  color: var(--wi-on-surface);
  font-weight: 500;
  font-style: italic;
}
.lp-pain-quote-mark {
  color: var(--wi-primary);
  font-style: normal;
  margin-inline: 2px;
}
.lp-pain-pivot {
  border-block-start: 1px solid var(--wi-outline-variant);
  padding-block-start: var(--wi-space-sm);
}
.lp-pain-pivot-label {
  display: inline-block;
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-secondary);
  background: var(--wi-secondary-container);
  padding-inline: var(--ms-space-2);
  padding-block: 3px;
  border-radius: var(--wi-radius-sm);
  letter-spacing: 0.04em;
  font-weight: 600;
  margin-block-end: var(--ms-space-2);
}
.lp-pain-solution {
  font-size: var(--wi-body-md);
  line-height: 1.55;
  color: var(--wi-on-surface);
}

/* ═══════════════════════════════════════════════════════════
   3. PRODUCT — split layout
   ═══════════════════════════════════════════════════════════ */
.lp-product {
  background: var(--wi-bg);
  padding-block: var(--wi-space-xl);
  padding-inline: var(--wi-space-md);
}
.lp-product-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wi-space-xl);
  max-inline-size: 1200px;
  margin-inline: auto;
  align-items: center;
}
@media (max-width: 900px) {
  .lp-product-grid {
    grid-template-columns: 1fr;
    gap: var(--wi-space-lg);
  }
}
.lp-product-visual {
  display: flex;
  align-items: center;
  justify-content: center;
}
.lp-mock {
  width: 100%;
  max-inline-size: 480px;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-lg);
  overflow: hidden;
}
.lp-mock-chrome {
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  padding-inline: var(--wi-space-sm);
  padding-block: var(--ms-space-3);
  background: var(--wi-surface-container);
  border-block-end: 1px solid var(--wi-outline-variant);
}
.lp-mock-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--wi-outline-variant);
}
.lp-mock-dot:nth-child(1) { background: var(--ms-rose); }
.lp-mock-dot:nth-child(2) { background: var(--ms-peach); }
.lp-mock-dot:nth-child(3) { background: var(--ms-mint); }
.lp-mock-title {
  margin-inline-start: auto;
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}
.lp-mock-body {
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
}
.lp-mock-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ms-space-3);
}
.lp-mock-label {
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
}
.lp-mock-value {
  font-family: var(--ms-font-mono);
  font-weight: 600;
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface);
}
.lp-mock-value--mint {
  color: var(--wi-secondary);
  font-size: var(--wi-h3-size);
}
.lp-mock-bar {
  height: 8px;
  background: var(--wi-surface-container-high);
  border-radius: var(--wi-radius-pill);
  overflow: hidden;
}
.lp-mock-bar-fill {
  height: 100%;
  width: var(--lp-fill, 80%);
  background: linear-gradient(90deg, var(--wi-primary-container), var(--wi-primary));
  border-radius: var(--wi-radius-pill);
}
.lp-mock-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ms-space-2);
  padding-block-start: var(--ms-space-2);
  border-block-start: 1px solid var(--wi-outline-variant);
}
.lp-mock-tag {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  padding-inline: var(--ms-space-2);
  padding-block: 3px;
  border-radius: var(--wi-radius-pill);
}

.lp-product-copy {
  display: flex;
  flex-direction: column;
}
.lp-product-lead {
  font-size: var(--wi-body-lg);
  line-height: 1.55;
  color: var(--wi-on-surface-variant);
  margin-block-end: var(--wi-space-md);
}
.lp-cap-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
}
.lp-cap {
  display: flex;
  align-items: flex-start;
  gap: var(--ms-space-3);
}
.lp-cap-check {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-block-start: 2px;
}
.lp-cap-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: 600;
  color: var(--wi-on-bg);
  margin: 0 0 4px;
}
.lp-cap-desc {
  font-size: var(--wi-body-md);
  line-height: 1.55;
  color: var(--wi-on-surface-variant);
  margin: 0;
}

/* ═══════════════════════════════════════════════════════════
   4. PROOF — fond dark cinématique
   #0f1117 = --ms-bg en dark mode → on l'utilise via var()
   ═══════════════════════════════════════════════════════════ */
.lp-proof {
  background: #0f1117; /* fond dark fixe — pas de switch theme ici */
  color: var(--ms-bg);
  padding-block: var(--wi-space-xl);
  padding-inline: var(--wi-space-md);
  position: relative;
  overflow: hidden;
}
.lp-proof::before {
  content: '';
  position: absolute;
  inset-block-start: -30%;
  inset-inline-end: -10%;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, var(--wi-primary) 0%, transparent 60%);
  opacity: 0.18;
  filter: blur(80px);
  pointer-events: none;
}
.lp-proof-inner {
  position: relative;
  max-inline-size: 900px;
  margin-inline: auto;
  text-align: center;
}
.lp-proof-figure {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--wi-space-md);
  margin-block: var(--wi-space-md);
  flex-wrap: wrap;
}
.lp-proof-num {
  font-family: var(--ms-font-mono);
  font-size: clamp(72px, 12vw, 144px);
  font-weight: 700;
  line-height: 1;
  color: var(--ms-orange);
  letter-spacing: -0.04em;
}
.lp-proof-figure-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: start;
}
.lp-proof-label {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: 600;
  color: var(--ms-bg);
}
.lp-proof-context {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: color-mix(in srgb, var(--ms-bg) 60%, transparent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-block-start: var(--ms-space-1);
}
.lp-proof-body {
  font-size: var(--wi-body-lg);
  line-height: 1.6;
  color: color-mix(in srgb, var(--ms-bg) 78%, transparent);
  max-inline-size: 640px;
  margin-inline: auto;
  margin-block-end: var(--wi-space-md);
}
.lp-btn--ghost-dark {
  background: transparent;
  color: var(--ms-orange);
  border-color: color-mix(in srgb, var(--ms-orange) 60%, transparent);
}
.lp-btn--ghost-dark:hover {
  background: color-mix(in srgb, var(--ms-orange) 15%, transparent);
  border-color: var(--ms-orange);
  transform: translateY(-2px);
}

/* ═══════════════════════════════════════════════════════════
   5. PRICING TEASER — 3 mini-cards
   ═══════════════════════════════════════════════════════════ */
.lp-pricing {
  background: var(--wi-surface-container-low);
  padding-block: var(--wi-space-xl);
  padding-inline: var(--wi-space-md);
}
.lp-pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--wi-space-md);
  max-inline-size: 1100px;
  margin-inline: auto;
}
.lp-price-card {
  position: relative;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-3);
  transition: transform var(--ms-transition), box-shadow var(--ms-transition),
              border-color var(--ms-transition);
}
.lp-price-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--wi-shadow-md);
}
.lp-price-card--featured {
  border-color: var(--wi-primary);
  border-width: 2px;
  box-shadow: var(--wi-shadow-md);
}
.lp-price-flag {
  position: absolute;
  inset-block-start: -12px;
  inset-inline-start: var(--wi-space-md);
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  padding-inline: var(--ms-space-3);
  padding-block: 4px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.lp-price-name {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: 600;
  color: var(--wi-on-bg);
  margin: 0;
}
.lp-price-tag {
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  margin: 0;
}
.lp-price-amount {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-block: var(--ms-space-2);
  border-block: 1px solid var(--wi-outline-variant);
}
.lp-price-from {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.lp-price-mad {
  font-family: var(--wi-font-heading);
  font-size: 28px;
  font-weight: 700;
  color: var(--wi-primary);
}
.lp-price-usd {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
}
.lp-price-blurb {
  font-size: var(--wi-body-md);
  line-height: 1.5;
  color: var(--wi-on-surface-variant);
  margin: 0;
}
.lp-pricing-cta {
  margin-block-start: var(--wi-space-lg);
  display: flex;
  justify-content: center;
}

/* ═══════════════════════════════════════════════════════════
   6. FINAL CTA — full-width terracotta band
   ═══════════════════════════════════════════════════════════ */
.lp-final {
  background: linear-gradient(135deg, var(--wi-primary) 0%, var(--wi-primary-container) 100%);
  padding-block: var(--wi-space-xl);
  padding-inline: var(--wi-space-md);
  position: relative;
  overflow: hidden;
}
.lp-final::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at 80% 20%,
    color-mix(in srgb, var(--wi-on-primary) 12%, transparent) 0%,
    transparent 50%
  );
  pointer-events: none;
}
.lp-final-inner {
  position: relative;
  max-inline-size: 900px;
  margin-inline: auto;
  text-align: center;
  color: var(--wi-on-primary);
}
.lp-final-title {
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: clamp(28px, 4vw, 44px);
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--wi-on-primary);
  margin: 0 0 var(--ms-space-3);
}
.lp-final-sub {
  font-size: var(--wi-body-lg);
  line-height: 1.55;
  color: color-mix(in srgb, var(--wi-on-primary) 88%, transparent);
  margin-block-end: var(--wi-space-md);
}
.lp-btn--final {
  background: var(--wi-on-primary);
  color: var(--wi-primary);
  font-size: var(--wi-body-lg);
  padding-inline: var(--wi-space-lg);
  padding-block: 16px;
  box-shadow: var(--wi-shadow-lg);
}
.lp-btn--final:hover {
  background: color-mix(in srgb, var(--wi-on-primary) 92%, var(--wi-primary));
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.25);
}

/* ═══════════════════════════════════════════════════════════
   Footer
   ═══════════════════════════════════════════════════════════ */
.lp-footer {
  background: var(--wi-surface-container);
  border-block-start: 1px solid var(--wi-outline-variant);
  padding-block: var(--wi-space-md);
  padding-inline: var(--wi-space-md);
}
.lp-footer-inner {
  max-inline-size: 1200px;
  margin-inline: auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-sm);
}
.lp-footer-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: var(--wi-h3-size);
  color: var(--wi-on-bg);
  letter-spacing: -0.02em;
}
.lp-footer-tag {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  letter-spacing: 0.04em;
}
.lp-footer-nav {
  display: flex;
  gap: var(--wi-space-sm);
}
.lp-footer-link {
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-size: var(--wi-body-md);
  transition: color var(--ms-transition);
}
.lp-footer-link:hover {
  color: var(--wi-primary);
}

/* ═══════════════════════════════════════════════════════════
   RTL specifics — Arabic typography tweaks
   ═══════════════════════════════════════════════════════════ */
[lang="ar"] .lp-h1,
[lang="ar"] .lp-h2,
[lang="ar"] .lp-final-title,
[lang="ar"] .lp-cap-title,
[lang="ar"] .lp-pain-quote {
  font-family: 'Tajawal', var(--wi-font-heading), sans-serif;
}
[lang="ar"] .lp-pain-quote {
  font-style: normal;
}

/* ═══════════════════════════════════════════════════════════
   Mobile fine-tuning
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 600px) {
  .lp-hero {
    padding-block: var(--wi-space-lg);
  }
  .lp-pains,
  .lp-product,
  .lp-pricing,
  .lp-final,
  .lp-proof {
    padding-block: var(--wi-space-lg);
  }
  .lp-cta-row {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    max-inline-size: 320px;
    margin-inline: auto;
  }
  .lp-btn {
    justify-content: center;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .lp-btn,
  .lp-pain-card,
  .lp-price-card,
  .lp-btn-arrow {
    transition: none;
  }
  .lp-btn:hover,
  .lp-pain-card:hover,
  .lp-price-card:hover {
    transform: none;
  }
}
</style>
