<template>
  <div class="offers-page">
    <!-- ───────────── Top bar (retour vers /) ─────────────
         LanguageSwitcher est déjà mounté globalement par App.vue en
         widget flottant top-right (cf App.vue), on ne le rappelle pas ici. -->
    <header class="offers-topbar">
      <router-link to="/" class="offers-back" :title="$t('offers.nav.backTitle')">
        <span class="offers-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
    </header>

    <main class="offers-main">
      <!-- ───────────── Hero ───────────── -->
      <section class="offers-hero">
        <span class="offers-eyebrow">{{ $t('offers.eyebrow') }}</span>
        <h1 class="offers-headline">{{ $t('offers.hero.title') }}</h1>
        <p class="offers-sub">{{ $t('offers.hero.subtitle') }}</p>
      </section>

      <!-- ───────────── Cards (3 packages) ─────────────
           Le package « featured » (Crisis Drill) est légèrement plus grand
           sur desktop (scale 1.04 + bordure orange). Sur mobile (< 768px),
           la grille devient verticale et le scale du featured est neutralisé. -->
      <section class="offers-grid" aria-label="Packages Bassira">
        <article
          v-for="pkg in packages"
          :key="pkg.id"
          class="ms-card offers-card"
          :class="{ 'offers-card--featured': pkg.featured }"
        >
          <header class="offers-card-head">
            <span
              v-if="pkg.featured"
              class="ms-badge offers-featured-badge"
            >
              {{ $t('offers.featuredBadge') }}
            </span>
            <h2 class="offers-card-title">{{ $t(`offers.packages.${pkg.id}.name`) }}</h2>
            <p class="offers-card-tagline">
              {{ $t(`offers.packages.${pkg.id}.tagline`) }}
            </p>
          </header>

          <p class="offers-card-desc">
            {{ $t(`offers.packages.${pkg.id}.description`) }}
          </p>

          <div class="offers-card-section">
            <h3 class="offers-card-section-title">
              {{ $t('offers.labels.deliverable') }}
            </h3>
            <p class="offers-card-section-body">
              {{ $t(`offers.packages.${pkg.id}.deliverable`) }}
            </p>
          </div>

          <div class="offers-card-meta-row">
            <div class="offers-card-meta">
              <span class="offers-card-meta-label">{{ $t('offers.labels.delay') }}</span>
              <span class="offers-card-meta-value">
                {{ $t(`offers.packages.${pkg.id}.delay`) }}
              </span>
            </div>
            <div class="offers-card-meta">
              <span class="offers-card-meta-label">{{ $t('offers.labels.price') }}</span>
              <span class="offers-card-meta-value offers-card-meta-value--price">
                {{ pkg.priceMad.toLocaleString('fr-FR') }}&nbsp;MAD
                <span class="offers-card-meta-value-alt">
                  · {{ pkg.priceUsd.toLocaleString('en-US') }}&nbsp;USD
                </span>
              </span>
            </div>
          </div>

          <div class="offers-card-section">
            <h3 class="offers-card-section-title">
              {{ $t('offers.labels.useCases') }}
            </h3>
            <p class="offers-card-section-body offers-card-section-body--muted">
              {{ $t(`offers.packages.${pkg.id}.useCases`) }}
            </p>
          </div>

          <p
            v-if="pkg.id === 'crisisDrill'"
            class="offers-card-fineprint"
          >
            {{ $t('offers.fineprint.crisisDrill') }}
          </p>

          <div class="offers-card-cta-row">
            <button
              type="button"
              class="ms-btn ms-btn-primary ms-btn--full ms-btn--lg"
              @click="requestQuote(pkg)"
            >
              {{ $t('offers.cta.requestQuote') }}
              <span class="offers-cta-arrow" aria-hidden="true">→</span>
            </button>
          </div>
        </article>
      </section>

      <!-- ───────────── Help / contact strip ───────────── -->
      <section class="offers-help">
        <h2 class="offers-help-title">{{ $t('offers.help.title') }}</h2>
        <p class="offers-help-body">{{ $t('offers.help.body') }}</p>
        <a
          class="ms-btn ms-btn-ghost ms-btn--lg"
          :href="contactMailto"
        >
          {{ $t('offers.help.cta') }}
        </a>
      </section>

      <!-- ───────────── FAQ (4 questions) ───────────── -->
      <section class="offers-faq" aria-label="FAQ">
        <h2 class="offers-faq-title">{{ $t('offers.faq.title') }}</h2>
        <div class="offers-faq-list">
          <details
            v-for="key in faqKeys"
            :key="key"
            class="offers-faq-item"
          >
            <summary class="offers-faq-q">
              {{ $t(`offers.faq.items.${key}.question`) }}
            </summary>
            <p class="offers-faq-a">
              {{ $t(`offers.faq.items.${key}.answer`) }}
            </p>
          </details>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

// ─── Catalogue des 3 packages.
// Les libellés (name, tagline, description, deliverable, delay, useCases) sont
// i18n via la clé `offers.packages.<id>.*`. Les prix restent dans le code car
// ils ne sont pas traduits (MAD + USD, jamais EUR — règle Bassira).
const packages = [
  {
    id: 'crisisDrill',
    featured: true,
    priceMad: 12000,
    priceUsd: 1200,
  },
  {
    id: 'policyBrief',
    featured: false,
    priceMad: 25000,
    priceUsd: 2500,
  },
  {
    id: 'preLaunch',
    featured: false,
    priceMad: 8000,
    priceUsd: 800,
  },
]

const faqKeys = ['firstResults', 'sampleReport', 'regulatedSectors', 'customScope']

const router = useRouter()
const { t } = useI18n()

// Email de contact commercial — utilisé par le bouton « Discuter avec nous »
// et comme fallback si la route /devis (US-025) n'existe pas encore.
const CONTACT_EMAIL = 'contact@ai-mpower.com'
const contactMailto = computed(
  () => `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(t('offers.help.mailSubject'))}`
)

// CTA principal de chaque card. On tente d'aller vers la route nommée `Quote`
// (créée par US-025). Si elle n'est pas encore enregistrée dans le router,
// router.resolve() renvoie un match avec name=null → on bascule alors sur
// un mailto contextualisé au package. Aucune erreur n'est jetée à l'utilisateur.
function requestQuote(pkg) {
  const target = router.resolve({ name: 'Quote', query: { package: pkg.id } })
  const matched = target && target.matched && target.matched.length > 0
  if (matched) {
    router.push({ name: 'Quote', query: { package: pkg.id } })
    return
  }

  // Fallback mailto — pas de route /devis encore. On préremplit le sujet avec
  // le nom traduit du package pour que l'email arrive déjà qualifié.
  const subject = encodeURIComponent(
    t('offers.cta.mailSubject', { package: t(`offers.packages.${pkg.id}.name`) })
  )
  window.location.href = `mailto:${CONTACT_EMAIL}?subject=${subject}`
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   OFFERS — Direction Playful & Soft (US-023)
   ═══════════════════════════════════════════════════════════
   Tous les inset-* / margin-inline-* sont logical pour rester
   compatibles RTL (locale ar). Aucun left/right physique. */

.offers-page {
  min-height: 100vh;
  background: var(--ms-bg);
  color: var(--ms-text);
  font-family: var(--ms-font-body);
}

/* ── Top bar ────────────────────────────────────────── */
.offers-topbar {
  display: flex;
  align-items: center;
  padding: var(--ms-space-4) var(--ms-space-6);
  /* Réserve la place pour le LanguageSwitcher floating top-right
     (z-index 1500, top:12px). Cohérent avec Home.vue / CalibrationView.vue. */
  padding-inline-end: 110px;
  border-bottom: 1px solid var(--ms-border);
  background: var(--ms-bg);
}

.offers-back {
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
.offers-back:hover {
  color: var(--ms-orange);
  background: var(--ms-bg-muted);
}
.offers-back-arrow {
  font-size: 16px;
  line-height: 1;
  /* Inverser visuellement la flèche en RTL pour que le « retour » pointe
     toujours vers le bord d'origine (gauche en LTR, droite en RTL). */
}
[dir="rtl"] .offers-back-arrow {
  transform: scaleX(-1);
}

/* ── Main wrapper ───────────────────────────────────── */
.offers-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--ms-space-12) var(--ms-space-6);
}

/* ── Hero ───────────────────────────────────────────── */
.offers-hero {
  text-align: center;
  margin-bottom: var(--ms-space-12);
}

.offers-eyebrow {
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
  margin-bottom: var(--ms-space-5);
}

.offers-headline {
  font-family: var(--ms-font-display);
  font-size: clamp(28px, 4.4vw, 44px);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--ms-text);
  margin: 0 auto var(--ms-space-5) auto;
  max-width: 880px;
}

.offers-sub {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-lg);
  line-height: 1.55;
  color: var(--ms-text-muted);
  max-width: 720px;
  margin: 0 auto;
}

/* ── Cards grid ─────────────────────────────────────── */
.offers-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--ms-space-6);
  align-items: stretch;
  margin-bottom: var(--ms-space-12);
}

@media (min-width: 768px) {
  .offers-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: var(--ms-space-5);
    align-items: center;
  }
}

.offers-card {
  display: flex;
  flex-direction: column;
  padding: var(--ms-space-8) var(--ms-space-6);
  border-radius: var(--ms-radius-lg);
  transition: transform var(--ms-transition), box-shadow var(--ms-transition);
  position: relative;
  height: 100%;
}

.offers-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--ms-shadow-lg);
}

@media (min-width: 768px) {
  .offers-card--featured {
    transform: scale(1.04);
    border: 2px solid var(--ms-orange);
    box-shadow: var(--ms-shadow-orange);
    z-index: 1;
  }
  .offers-card--featured:hover {
    transform: scale(1.04) translateY(-3px);
  }
}

.offers-card-head {
  margin-bottom: var(--ms-space-4);
}

.offers-featured-badge {
  background: var(--ms-orange);
  color: var(--ms-text-on-color);
  margin-bottom: var(--ms-space-3);
}

.offers-card-title {
  font-family: var(--ms-font-display);
  font-size: var(--ms-text-2xl);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ms-text);
  margin: 0 0 var(--ms-space-2) 0;
  line-height: 1.2;
}

.offers-card-tagline {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-base);
  line-height: 1.45;
  color: var(--ms-text);
  font-style: italic;
  margin: 0;
}

.offers-card-desc {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-sm);
  line-height: 1.6;
  color: var(--ms-text-muted);
  margin: 0 0 var(--ms-space-5) 0;
}

.offers-card-section {
  margin-bottom: var(--ms-space-4);
}

.offers-card-section-title {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ms-text-muted);
  margin: 0 0 var(--ms-space-2) 0;
}

.offers-card-section-body {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-sm);
  line-height: 1.55;
  color: var(--ms-text);
  margin: 0;
}
.offers-card-section-body--muted {
  color: var(--ms-text-muted);
}

/* ── Meta row (delay + price) ───────────────────────── */
.offers-card-meta-row {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: var(--ms-space-3);
  padding: var(--ms-space-4) 0;
  margin: var(--ms-space-3) 0 var(--ms-space-4) 0;
  border-top: 1px solid var(--ms-border);
  border-bottom: 1px solid var(--ms-border);
}

.offers-card-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.offers-card-meta-label {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ms-text-muted);
}

.offers-card-meta-value {
  font-family: var(--ms-font-display);
  font-size: var(--ms-text-base);
  font-weight: 600;
  color: var(--ms-text);
  line-height: 1.3;
}

.offers-card-meta-value--price {
  font-size: var(--ms-text-lg);
  color: var(--ms-orange-strong);
}

.offers-card-meta-value-alt {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-xs);
  font-weight: 500;
  color: var(--ms-text-muted);
  white-space: nowrap;
}

.offers-card-fineprint {
  font-family: var(--ms-font-body);
  font-size: 11px;
  color: var(--ms-text-subtle);
  font-style: italic;
  margin: 0 0 var(--ms-space-3) 0;
  line-height: 1.4;
}

/* ── CTA row ────────────────────────────────────────── */
.offers-card-cta-row {
  margin-top: auto;
  padding-top: var(--ms-space-3);
}

.offers-cta-arrow {
  display: inline-block;
  margin-inline-start: 6px;
  transition: transform var(--ms-transition);
}
[dir="rtl"] .offers-cta-arrow {
  transform: scaleX(-1);
}
.ms-btn:hover .offers-cta-arrow {
  transform: translateX(2px);
}
[dir="rtl"] .ms-btn:hover .offers-cta-arrow {
  transform: scaleX(-1) translateX(2px);
}

/* ── Help / contact strip ───────────────────────────── */
.offers-help {
  text-align: center;
  background: var(--ms-bg-elevated);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-lg);
  padding: var(--ms-space-8) var(--ms-space-6);
  margin-bottom: var(--ms-space-12);
  box-shadow: var(--ms-shadow-sm);
}

.offers-help-title {
  font-family: var(--ms-font-display);
  font-size: var(--ms-text-2xl);
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 0 0 var(--ms-space-3) 0;
  color: var(--ms-text);
}

.offers-help-body {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-base);
  line-height: 1.55;
  color: var(--ms-text-muted);
  max-width: 560px;
  margin: 0 auto var(--ms-space-5) auto;
}

/* ── FAQ ────────────────────────────────────────────── */
.offers-faq {
  max-width: 820px;
  margin: 0 auto;
}

.offers-faq-title {
  font-family: var(--ms-font-display);
  font-size: var(--ms-text-2xl);
  font-weight: 700;
  letter-spacing: -0.01em;
  text-align: center;
  margin: 0 0 var(--ms-space-6) 0;
  color: var(--ms-text);
}

.offers-faq-list {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-3);
}

.offers-faq-item {
  background: var(--ms-bg-elevated);
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: var(--ms-space-4) var(--ms-space-5);
  box-shadow: var(--ms-shadow-xs);
  transition: box-shadow var(--ms-transition), border-color var(--ms-transition);
}
.offers-faq-item[open] {
  border-color: var(--ms-orange);
  box-shadow: var(--ms-shadow-sm);
}

.offers-faq-q {
  font-family: var(--ms-font-display);
  font-size: var(--ms-text-base);
  font-weight: 600;
  color: var(--ms-text);
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ms-space-3);
}
.offers-faq-q::-webkit-details-marker {
  display: none;
}
.offers-faq-q::after {
  content: '+';
  font-family: var(--ms-font-mono);
  font-size: 18px;
  color: var(--ms-orange);
  flex-shrink: 0;
  transition: transform var(--ms-transition);
}
.offers-faq-item[open] .offers-faq-q::after {
  content: '−';
}

.offers-faq-a {
  font-family: var(--ms-font-body);
  font-size: var(--ms-text-sm);
  line-height: 1.6;
  color: var(--ms-text-muted);
  margin: var(--ms-space-3) 0 0 0;
}

/* ── Mobile tweaks (< 768 px) ───────────────────────── */
@media (max-width: 767px) {
  .offers-main {
    padding: var(--ms-space-8) var(--ms-space-4);
  }
  .offers-card-meta-row {
    grid-template-columns: 1fr;
    gap: var(--ms-space-3);
  }
  .offers-help {
    padding: var(--ms-space-6) var(--ms-space-4);
  }
}
</style>
