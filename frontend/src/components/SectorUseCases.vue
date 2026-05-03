<template>
  <!--
    SectorUseCases — section CTAs par métier/secteur (US-085)
    8 secteurs ciblés MENA + Europe avec 2 use cases stratégiques par secteur.
    Au clic sur un use case → router vers /devis avec query params
    ?sector=X&usecase=Y pour pré-remplir le contexte du formulaire.
    Tokens --wi-* exclusifs.
  -->
  <section
    :id="anchorId"
    class="suc-section"
    :ref="el => sectionRoot = el"
    :aria-labelledby="`${anchorId}-title`"
  >
    <header class="suc-header">
      <span class="suc-eyebrow">{{ $t('sectors.eyebrow') }}</span>
      <h2 :id="`${anchorId}-title`" class="suc-title">{{ $t('sectors.title') }}</h2>
      <p class="suc-subtitle">{{ $t('sectors.subtitle') }}</p>
    </header>

    <div class="suc-grid">
      <article
        v-for="(s, idx) in sectors"
        :key="s.id"
        class="suc-card"
        :class="{ 'suc-card--featured': s.featured }"
      >
        <div class="suc-card-head">
          <span class="material-symbols-outlined suc-icon" aria-hidden="true">{{ s.icon }}</span>
          <h3 class="suc-card-title">{{ $t(`sectors.${s.id}.name`) }}</h3>
        </div>

        <p class="suc-card-tagline">{{ $t(`sectors.${s.id}.tagline`) }}</p>

        <ul class="suc-cases">
          <li
            v-for="caseIdx in 2"
            :key="caseIdx"
            class="suc-case"
          >
            <span class="suc-case-dot" aria-hidden="true">●</span>
            <span class="suc-case-text">{{ $t(`sectors.${s.id}.cases.${caseIdx - 1}`) }}</span>
          </li>
        </ul>

        <!-- US-087 — Double CTA card : « Voir le modèle » route vers
             /models?sector=X (US-086 gère le query param), « Demander une
             analyse personnalisée » conserve le tunnel commercial /devis
             avec pré-remplissage SECTOR_TO_SITUATION (mécanique US-085). -->
        <div class="suc-card-cta-row">
          <button
            type="button"
            class="suc-cta suc-cta--primary"
            :title="$t('sectors.cardCta.viewModelTitle')"
            @click="onViewModelCta(s.id)"
          >
            <span>{{ $t('sectors.cardCta.viewModel') }}</span>
            <span class="suc-cta-arrow" aria-hidden="true">→</span>
          </button>
          <button
            type="button"
            class="suc-cta suc-cta--ghost"
            :title="$t('sectors.cardCta.requestCustomTitle')"
            @click="onRequestCustomCta(s.id, 0)"
          >
            <span>{{ $t('sectors.cardCta.requestCustom') }}</span>
          </button>
          <span v-if="s.featured" class="suc-featured-badge">{{ $t('sectors.featuredBadge') }}</span>
        </div>
      </article>
    </div>

    <p class="suc-footer-note">
      {{ $t('sectors.footerNote') }}
      <button
        type="button"
        class="suc-custom-link"
        @click="onCustomCta"
      >
        {{ $t('sectors.customLink') }} →
      </button>
    </p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

defineProps({
  anchorId: { type: String, default: 'sectors' },
})

const router = useRouter()
const sectionRoot = ref(null)

// 8 secteurs MENA + Europe — icons via Material Symbols Outlined
const sectors = [
  { id: 'finance',      icon: 'account_balance', featured: true  },
  { id: 'energy',       icon: 'bolt',            featured: false },
  { id: 'politics',     icon: 'gavel',           featured: false },
  { id: 'retail',       icon: 'storefront',      featured: false },
  { id: 'tech',         icon: 'rocket_launch',   featured: false },
  { id: 'industry',     icon: 'precision_manufacturing', featured: false },
  { id: 'media',        icon: 'campaign',        featured: false },
  { id: 'healthcare',   icon: 'medical_services', featured: false },
]

// Map secteur → package recommandé (correspond aux IDs du carousel /offres)
const sectorPackageMap = {
  finance:    'crisis_drill_24h',
  energy:     'policy_brief_stress',
  politics:   'policy_brief_stress',
  retail:     'pre_launch_adcheck',
  tech:       'pre_launch_adcheck',
  industry:   'crisis_drill_24h',
  media:      'crisis_drill_24h',
  healthcare: 'policy_brief_stress',
}

// US-087 — CTA principal de chaque card : route vers /models?sector=<id>.
// La route /models (US-086, en parallèle) consomme ce query param pour
// filtrer la liste de modèles publics par secteur.
const onViewModelCta = (sectorId) => {
  router.push({
    path: '/models',
    query: { sector: sectorId },
  })
}

// US-087 — CTA secondaire : tunnel commercial /devis avec sector + usecase
// + package. Conserve la mécanique US-085 (SECTOR_TO_SITUATION dans QuoteView)
// pour pré-remplir le formulaire de devis personnalisé.
const onRequestCustomCta = (sectorId, caseIdx) => {
  router.push({
    name: 'Quote',
    query: {
      sector: sectorId,
      usecase: String(caseIdx),
      package: sectorPackageMap[sectorId] || '',
    },
  })
}

const onCustomCta = () => {
  router.push({ name: 'Quote', query: { sector: 'custom' } })
}
</script>

<style scoped>
.suc-section {
  padding-block: var(--wi-space-xl, 64px);
  padding-inline: var(--wi-space-md, 24px);
  background: var(--wi-bg, #fff8f6);
  border-block-start: 1px solid var(--wi-outline-variant);
}

.suc-header {
  text-align: center;
  max-width: 720px;
  margin-inline: auto;
  margin-block-end: var(--wi-space-lg, 40px);
}

.suc-eyebrow {
  display: inline-block;
  padding: 4px 12px;
  background: var(--wi-primary-soft, rgba(161, 63, 15, 0.08));
  color: var(--wi-primary);
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-radius: var(--wi-radius-pill);
  margin-block-end: var(--wi-space-sm, 16px);
}

.suc-title {
  font-family: var(--wi-font-heading);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--wi-on-bg);
  margin: 0 0 var(--wi-space-sm, 16px);
}

.suc-subtitle {
  font-family: var(--wi-font-body);
  font-size: 18px;
  font-weight: 400;
  line-height: 1.6;
  color: var(--wi-on-surface-variant);
  margin: 0;
}

.suc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--wi-space-md, 24px);
  max-width: 1280px;
  margin-inline: auto;
}

.suc-card {
  display: flex;
  flex-direction: column;
  background: var(--wi-surface, #ffffff);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card, 24px);
  padding: var(--wi-space-md, 24px);
  box-shadow: var(--wi-shadow-ambient);
  transition: transform 200ms var(--ms-ease, ease), box-shadow 200ms var(--ms-ease, ease);
}

.suc-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--wi-shadow-lg);
  border-color: var(--wi-primary-container);
}

.suc-card--featured {
  border-color: var(--wi-primary-container);
  border-width: 2px;
  background: linear-gradient(180deg, var(--wi-surface) 0%, var(--wi-surface-container-low) 100%);
}

.suc-card-head {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm, 16px);
  margin-block-end: var(--wi-space-sm, 16px);
}

.suc-icon {
  font-size: 32px;
  color: var(--wi-primary-container);
  font-variation-settings: 'FILL' 1, 'wght' 500;
}

.suc-card-title {
  font-family: var(--wi-font-heading);
  font-size: 22px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--wi-on-surface);
  margin: 0;
}

.suc-card-tagline {
  font-family: var(--wi-font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  margin: 0 0 var(--wi-space-md, 24px);
  line-height: 1.5;
}

.suc-cases {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--wi-space-md, 24px);
  flex: 1;
}

.suc-case {
  display: flex;
  gap: var(--wi-space-xs, 8px);
  align-items: flex-start;
  padding-block: var(--wi-space-xs, 8px);
  font-family: var(--wi-font-body);
  font-size: 14px;
  line-height: 1.5;
  color: var(--wi-on-surface);
  font-style: italic;
  border-block-end: 1px dashed var(--wi-outline-variant);
}

.suc-case:last-child { border-block-end: none; }

.suc-case-dot {
  color: var(--wi-secondary);
  font-size: 8px;
  margin-block-start: 7px;
  flex-shrink: 0;
}

.suc-case-text { flex: 1; }

.suc-card-cta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-start;
  gap: var(--wi-space-sm, 16px);
}

.suc-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: var(--wi-radius-interactive, 12px);
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 150ms var(--ms-ease, ease), transform 150ms var(--ms-ease, ease), color 150ms var(--ms-ease, ease), border-color 150ms var(--ms-ease, ease);
}

/* US-087 — Variante primaire : « Voir le modèle » (terracotta plein) */
.suc-cta--primary {
  background: var(--wi-on-primary-container);
  color: var(--wi-bg);
  border: 2px solid var(--wi-on-primary-container);
}
.suc-cta--primary:hover {
  background: var(--wi-primary);
  border-color: var(--wi-primary);
  transform: translateX(2px);
}

/* US-087 — Variante ghost : « Demander une analyse personnalisée » (outlined) */
.suc-cta--ghost {
  background: transparent;
  color: var(--wi-on-primary-container);
  border: 2px solid var(--wi-outline-variant);
}
.suc-cta--ghost:hover {
  background: var(--wi-primary-soft);
  border-color: var(--wi-primary);
  color: var(--wi-primary);
}

.suc-cta-arrow {
  display: inline-block;
  transition: transform 200ms var(--ms-ease, ease);
}

.suc-cta:hover .suc-cta-arrow { transform: translateX(3px); }

[dir="rtl"] .suc-cta-arrow { transform: scaleX(-1); }
[dir="rtl"] .suc-cta:hover .suc-cta-arrow { transform: scaleX(-1) translateX(3px); }
[dir="rtl"] .suc-cta:hover { transform: translateX(-2px); }

.suc-featured-badge {
  display: inline-block;
  padding: 4px 10px;
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-body);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.suc-footer-note {
  text-align: center;
  margin-block-start: var(--wi-space-lg, 40px);
  font-family: var(--wi-font-body);
  font-size: 15px;
  color: var(--wi-on-surface-variant);
}

.suc-custom-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--wi-on-primary-container);
  font-family: inherit;
  font-size: inherit;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color 150ms var(--ms-ease, ease);
}

.suc-custom-link:hover { color: var(--wi-primary); }

@media (max-width: 720px) {
  .suc-section { padding-block: var(--wi-space-lg, 40px); }
  .suc-grid { grid-template-columns: 1fr; }
  .suc-card-cta-row { flex-direction: column; align-items: stretch; }
  .suc-cta { justify-content: center; }
}

@media (prefers-reduced-motion: reduce) {
  .suc-card,
  .suc-cta,
  .suc-cta-arrow { transition: none; }
}
</style>
