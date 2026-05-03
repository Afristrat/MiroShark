<template>
  <!--
    US-086 — Vitrine /models publique : 5 modèles stratégiques pré-calibrés.
    Cible C-level institutionnel MENA + Europe. Registre académique-stratégique.
    Tokens --wi-* exclusifs. RTL via CSS logical properties.
  -->
  <div class="ml-page" :lang="$i18n.locale">
    <header class="ml-topbar">
      <router-link :to="{ name: 'Home' }" class="ml-brand" :title="$t('nav.brand')">
        {{ $t('nav.brand') }}
      </router-link>
      <nav class="ml-nav" :aria-label="$t('models.list.nav.ariaLabel')">
        <router-link :to="{ name: 'Calibration' }" class="ml-nav-link">
          {{ $t('models.list.nav.calibration') }}
        </router-link>
        <router-link :to="{ name: 'Offers' }" class="ml-nav-link">
          {{ $t('models.list.nav.pricing') }}
        </router-link>
        <router-link :to="{ name: 'Quote' }" class="ml-nav-cta">
          {{ $t('models.list.nav.quote') }}
        </router-link>
      </nav>
    </header>

    <main class="ml-main">
      <section class="ml-hero" :aria-labelledby="heroHeadingId">
        <div aria-hidden="true" class="ml-hero-glow"></div>

        <span class="ml-eyebrow">
          <span class="ml-eyebrow-arabic" aria-hidden="true">بصيرة</span>
          <span class="ml-eyebrow-dot" aria-hidden="true">·</span>
          <span>{{ $t('models.list.hero.eyebrow') }}</span>
        </span>

        <h1 :id="heroHeadingId" class="ml-h1">
          {{ $t('models.list.hero.title') }}
        </h1>

        <p class="ml-hero-sub">
          {{ $t('models.list.hero.subtitle') }}
        </p>

        <p class="ml-hero-meta">
          {{ $t('models.list.hero.meta') }}
        </p>
      </section>

      <section
        class="ml-grid-section"
        :aria-labelledby="gridHeadingId"
      >
        <h2 :id="gridHeadingId" class="ml-sr-only">
          {{ $t('models.list.gridHeading') }}
        </h2>

        <div class="ml-grid">
          <article
            v-for="m in models"
            :key="m.slug"
            class="ml-card"
          >
            <header class="ml-card-head">
              <span
                class="ml-sector-pill"
                :class="`ml-sector-pill--${m.sector}`"
              >
                {{ $t(`models.cards.sector.${m.sector}`) }}
              </span>
              <span
                class="ml-brier-pill"
                :title="$t('models.list.brierTooltip')"
                :aria-label="$t('models.list.brierAriaLabel', { value: brierLabel(m.brier_illustrative) })"
              >
                <span class="ml-brier-dot" aria-hidden="true">●</span>
                <span class="ml-brier-label">{{ $t('models.list.brierShort') }}</span>
                <span class="ml-brier-value">{{ brierLabel(m.brier_illustrative) }}</span>
              </span>
            </header>

            <h3 class="ml-card-title">
              {{ m.title[locale] || m.title.fr }}
            </h3>

            <p class="ml-card-subtitle">
              {{ m.subtitle[locale] || m.subtitle.fr }}
            </p>

            <p class="ml-card-summary">
              {{ m.summary_short[locale] || m.summary_short.fr }}
            </p>

            <router-link
              :to="{ name: 'ModelDetail', params: { slug: m.slug } }"
              class="ml-card-cta"
              :aria-label="$t('models.list.cta.viewModelAria', { title: m.title[locale] || m.title.fr })"
            >
              <span>{{ $t('models.list.cta.viewModel') }}</span>
              <span class="ml-cta-arrow" aria-hidden="true">→</span>
            </router-link>
          </article>
        </div>
      </section>

      <section class="ml-trust" :aria-labelledby="trustHeadingId">
        <h2 :id="trustHeadingId" class="ml-trust-title">
          {{ $t('models.list.trust.title') }}
        </h2>
        <ul class="ml-trust-list">
          <li class="ml-trust-item">
            <span class="ml-trust-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none">
                <path d="M3 8.5l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span>{{ $t('models.list.trust.methodology') }}</span>
          </li>
          <li class="ml-trust-item">
            <span class="ml-trust-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none">
                <path d="M3 8.5l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span>{{ $t('models.list.trust.calibration') }}</span>
          </li>
          <li class="ml-trust-item">
            <span class="ml-trust-icon" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none">
                <path d="M3 8.5l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span>{{ $t('models.list.trust.sovereign') }}</span>
          </li>
        </ul>

        <div class="ml-trust-cta-row">
          <router-link :to="{ name: 'Calibration' }" class="ml-link-quiet">
            {{ $t('models.list.trust.calibrationLink') }} →
          </router-link>
          <router-link :to="{ name: 'Quote' }" class="ml-link-quiet">
            {{ $t('models.list.trust.customLink') }} →
          </router-link>
        </div>
      </section>
    </main>

    <footer class="ml-footer">
      <div class="ml-footer-inner">
        <span class="ml-footer-brand">{{ $t('nav.brand') }}</span>
        <span class="ml-footer-tag">{{ $t('models.list.footer.tagline') }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import fusionBancaireMena from '../models/fusion-bancaire-mena.json'
import crisisDrill24h from '../models/crisis-drill-24h.json'
import allocationFondsStrategique from '../models/allocation-fonds-strategique.json'
import stressTestPolitique from '../models/stress-test-politique.json'
import lancementDiasporaEu from '../models/lancement-diaspora-eu.json'

// Ordre sectoriel : finance institutionnelle → crise → fonds → politique → distribution.
// L'ordre est intentionnel : il guide un C-level depuis la régulation lourde (banque)
// vers les leviers opérationnels (lancement diaspora) en passant par les sujets de
// décision exécutive immédiate (crise, allocation, politique).
const models = [
  fusionBancaireMena,
  crisisDrill24h,
  allocationFondsStrategique,
  stressTestPolitique,
  lancementDiasporaEu,
]

const { locale: i18nLocale } = useI18n()
const locale = computed(() => {
  const l = i18nLocale.value
  return ['fr', 'en', 'ar'].includes(l) ? l : 'fr'
})

const heroHeadingId = 'ml-hero-h'
const gridHeadingId = 'ml-grid-h'
const trustHeadingId = 'ml-trust-h'

// Format Brier court (0.18) — typographie courte mais préfixée 0. pour rester lisible.
function brierLabel (value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return value.toFixed(2)
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════
   Styles — tokens --wi-* exclusifs. RTL via CSS logical props.
   ════════════════════════════════════════════════════════════ */
.ml-page {
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.ml-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* ───── Topbar ───── */
.ml-topbar {
  position: sticky;
  inset-block-start: 0;
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
.ml-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: var(--wi-h3-size);
  color: var(--wi-on-bg);
  text-decoration: none;
  letter-spacing: -0.02em;
}
.ml-nav {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
}
.ml-nav-link {
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-size: var(--wi-body-md);
  font-weight: 500;
  padding-inline: var(--wi-space-xs);
  padding-block: 6px;
  border-radius: var(--wi-radius-sm);
  transition: color var(--ms-transition), background var(--ms-transition);
}
.ml-nav-link:hover {
  color: var(--wi-primary);
  background: var(--wi-surface-container-low);
}
.ml-nav-cta {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  padding-inline: var(--wi-space-sm);
  padding-block: 10px;
  border-radius: var(--wi-radius-interactive);
  font-weight: 600;
  font-size: var(--wi-body-md);
  text-decoration: none;
  box-shadow: var(--wi-shadow-sm);
  transition: background var(--ms-transition), transform var(--ms-transition);
}
.ml-nav-cta:hover {
  background: var(--ms-orange-strong);
  transform: translateY(-1px);
}
@media (max-width: 720px) {
  .ml-topbar {
    padding-inline: var(--wi-space-sm);
  }
  .ml-nav-link {
    display: none;
  }
}

/* ───── Main ───── */
.ml-main {
  display: flex;
  flex-direction: column;
  padding-inline: var(--wi-space-md);
}

/* ───── Hero ───── */
.ml-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding-block: var(--wi-space-xl);
  max-inline-size: 920px;
  margin-inline: auto;
  overflow: hidden;
}
.ml-hero-glow {
  position: absolute;
  inset-block-start: -10%;
  inset-inline-start: 50%;
  transform: translateX(-50%);
  width: min(900px, 90%);
  height: 480px;
  background: radial-gradient(
    ellipse at center,
    var(--wi-primary-container) 0%,
    transparent 60%
  );
  opacity: 0.15;
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}
.ml-hero > * {
  position: relative;
  z-index: 1;
}
.ml-eyebrow {
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
.ml-eyebrow-arabic {
  font-family: 'Tajawal', var(--wi-font-heading), sans-serif;
  font-weight: 700;
}
.ml-eyebrow-dot {
  opacity: 0.4;
}
.ml-h1 {
  font-family: var(--wi-font-heading);
  font-weight: var(--wi-h1-weight);
  font-size: clamp(34px, 5vw, 56px);
  line-height: 1.1;
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-bg);
  margin-block-end: var(--wi-space-md);
  margin-inline: auto;
}
.ml-hero-sub {
  font-size: clamp(17px, 1.6vw, 20px);
  line-height: 1.55;
  color: var(--wi-on-surface-variant);
  max-inline-size: 660px;
  margin-block-end: var(--wi-space-sm);
  margin-inline: auto;
}
.ml-hero-meta {
  font-size: var(--wi-label-sm);
  color: var(--wi-outline);
  font-weight: 500;
  letter-spacing: 0.02em;
  margin-block-end: 0;
}

/* ───── Grid ───── */
.ml-grid-section {
  padding-block: var(--wi-space-lg);
  max-inline-size: 1280px;
  margin-inline: auto;
  width: 100%;
}
.ml-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
}
@media (min-width: 720px) {
  .ml-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (min-width: 1080px) {
  .ml-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.ml-card {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  box-shadow: var(--wi-shadow-ambient);
  transition: transform 200ms var(--ms-ease), box-shadow 200ms var(--ms-ease),
              border-color 200ms var(--ms-ease);
}
.ml-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--wi-shadow-lg);
  border-color: var(--wi-primary-container);
}

.ml-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-xs);
  flex-wrap: wrap;
}

.ml-sector-pill {
  display: inline-flex;
  align-items: center;
  padding-inline: 12px;
  padding-block: 4px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-heading);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
/* Couleurs sectorielles — chacune dérivée d'un token --wi-* existant. */
.ml-sector-pill--banque {
  background: var(--wi-primary-soft);
  color: var(--wi-primary);
}
.ml-sector-pill--crisis {
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
}
.ml-sector-pill--investissement {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}
.ml-sector-pill--politique {
  background: var(--wi-tertiary-container);
  color: var(--wi-on-tertiary-container);
}
.ml-sector-pill--distribution {
  background: color-mix(in srgb, var(--wi-primary-container) 25%, var(--wi-surface));
  color: var(--wi-on-primary-container);
}

.ml-brier-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-inline: 10px;
  padding-block: 4px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  font-family: var(--wi-font-heading);
  font-size: 11px;
  color: var(--wi-on-surface-variant);
}
.ml-brier-dot {
  color: var(--wi-secondary);
  font-size: 8px;
}
.ml-brier-label {
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.ml-brier-value {
  font-weight: 700;
  color: var(--wi-on-surface);
  font-variant-numeric: tabular-nums;
}

.ml-card-title {
  font-family: var(--wi-font-heading);
  font-size: clamp(20px, 1.7vw, 22px);
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.01em;
  color: var(--wi-on-surface);
  margin: 0;
}

.ml-card-subtitle {
  font-size: 15px;
  line-height: 1.5;
  color: var(--wi-on-surface-variant);
  margin: 0;
}

.ml-card-summary {
  font-size: 14px;
  line-height: 1.6;
  color: var(--wi-on-surface);
  margin: 0;
  font-style: italic;
  border-inline-start: 2px solid var(--wi-primary-container);
  padding-inline-start: var(--wi-space-sm);
  flex: 1;
}

.ml-card-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding-inline: 18px;
  padding-block: 10px;
  background: var(--wi-on-primary-container);
  color: var(--wi-bg);
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: background 150ms var(--ms-ease), transform 150ms var(--ms-ease);
}
.ml-card-cta:hover {
  background: var(--wi-primary);
  transform: translateX(2px);
}
.ml-cta-arrow {
  transition: transform 200ms var(--ms-ease);
}
[dir="rtl"] .ml-cta-arrow {
  transform: scaleX(-1);
}
.ml-card-cta:hover .ml-cta-arrow {
  transform: translateX(3px);
}
[dir="rtl"] .ml-card-cta:hover {
  transform: translateX(-2px);
}
[dir="rtl"] .ml-card-cta:hover .ml-cta-arrow {
  transform: scaleX(-1) translateX(3px);
}

/* ───── Trust strip ───── */
.ml-trust {
  margin-block: var(--wi-space-lg);
  padding-block: var(--wi-space-lg);
  padding-inline: var(--wi-space-md);
  max-inline-size: 1080px;
  margin-inline: auto;
  text-align: center;
  border-block-start: 1px solid var(--wi-outline-variant);
}
.ml-trust-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: 600;
  color: var(--wi-on-bg);
  margin: 0 0 var(--wi-space-md);
  letter-spacing: -0.01em;
}
.ml-trust-list {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--wi-space-md);
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--wi-space-md);
}
.ml-trust-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: var(--wi-on-surface-variant);
}
.ml-trust-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}

.ml-trust-cta-row {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--wi-space-md);
}
.ml-link-quiet {
  color: var(--wi-on-primary-container);
  text-decoration: underline;
  text-underline-offset: 3px;
  font-weight: 600;
  font-size: 14px;
  transition: color 150ms var(--ms-ease);
}
.ml-link-quiet:hover {
  color: var(--wi-primary);
}
[dir="rtl"] .ml-link-quiet::after {
  /* arrow direction handled by typography only */
}

/* ───── Footer ───── */
.ml-footer {
  border-block-start: 1px solid var(--wi-outline-variant);
  padding-block: var(--wi-space-md);
  padding-inline: var(--wi-space-md);
  background: var(--wi-surface-container-low);
}
.ml-footer-inner {
  max-inline-size: 1280px;
  margin-inline: auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-sm);
}
.ml-footer-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--wi-on-bg);
}
.ml-footer-tag {
  font-size: 13px;
  color: var(--wi-on-surface-variant);
}

@media (prefers-reduced-motion: reduce) {
  .ml-card,
  .ml-card-cta,
  .ml-cta-arrow,
  .ml-nav-cta {
    transition: none;
  }
}
</style>
