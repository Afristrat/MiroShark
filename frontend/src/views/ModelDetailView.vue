<template>
  <!--
    US-086 — Détail d'un modèle stratégique pré-calibré.
    Charge le JSON via import dynamique. Tokens --wi-* exclusifs.
    RTL via CSS logical properties.
  -->
  <div class="md-page" :lang="$i18n.locale">
    <header class="md-topbar">
      <router-link :to="{ name: 'Home' }" class="md-brand" :title="$t('nav.brand')">
        {{ $t('nav.brand') }}
      </router-link>
      <nav class="md-nav" :aria-label="$t('models.list.nav.ariaLabel')">
        <router-link :to="{ name: 'ModelsList' }" class="md-nav-link">
          {{ $t('models.detail.nav.backToList') }}
        </router-link>
        <router-link :to="{ name: 'Calibration' }" class="md-nav-link">
          {{ $t('models.list.nav.calibration') }}
        </router-link>
        <router-link :to="{ name: 'Quote' }" class="md-nav-cta">
          {{ $t('models.list.nav.quote') }}
        </router-link>
      </nav>
    </header>

    <main v-if="model" class="md-main">
      <!-- ───────────── 1. Hero ───────────── -->
      <section class="md-hero" :aria-labelledby="heroId">
        <div aria-hidden="true" class="md-hero-glow"></div>

        <div class="md-hero-pills">
          <span
            class="md-sector-pill"
            :class="`md-sector-pill--${model.sector}`"
          >
            {{ $t(`models.cards.sector.${model.sector}`) }}
          </span>
          <span class="md-brier-pill">
            <span class="md-brier-dot" aria-hidden="true">●</span>
            <span class="md-brier-label">{{ $t('models.list.brierShort') }}</span>
            <span class="md-brier-value">{{ brierLabel }}</span>
          </span>
        </div>

        <h1 :id="heroId" class="md-h1">
          {{ titleLocalized }}
        </h1>
        <p class="md-hero-sub">
          {{ subtitleLocalized }}
        </p>
      </section>

      <!-- ───────────── 2. Question de décision ───────────── -->
      <section class="md-decision" :aria-labelledby="decisionId">
        <div class="md-decision-inner">
          <span class="md-section-kicker">
            {{ $t('models.detail.section.decision.kicker') }}
          </span>
          <h2 :id="decisionId" class="md-decision-title">
            {{ $t('models.detail.section.decision.title') }}
          </h2>
          <blockquote class="md-decision-quote">
            <span class="md-decision-mark" aria-hidden="true">«</span>
            {{ decisionLocalized }}
            <span class="md-decision-mark" aria-hidden="true">»</span>
          </blockquote>
        </div>
      </section>

      <!-- ───────────── 3. Contexte ───────────── -->
      <section class="md-context" :aria-labelledby="contextId">
        <div class="md-context-head">
          <span class="md-section-kicker">
            {{ $t('models.detail.section.context.kicker') }}
          </span>
          <h2 :id="contextId" class="md-h2">
            {{ $t('models.detail.section.context.title') }}
          </h2>
        </div>
        <div class="md-context-body">
          <p
            v-for="(para, idx) in contextParagraphs"
            :key="idx"
            class="md-context-para"
          >
            {{ para }}
          </p>
        </div>
      </section>

      <!-- ───────────── 4. Agents simulés ───────────── -->
      <section class="md-agents" :aria-labelledby="agentsId">
        <div class="md-section-head">
          <span class="md-section-kicker">
            {{ $t('models.detail.section.agents.kicker') }}
          </span>
          <h2 :id="agentsId" class="md-h2">
            {{ $t('models.detail.section.agents.title') }}
          </h2>
          <p class="md-section-sub">
            {{ $t('models.detail.section.agents.subtitle') }}
          </p>
        </div>
        <div class="md-agents-grid">
          <article
            v-for="(agent, idx) in model.agents_simulated"
            :key="agent.role_key + idx"
            class="md-agent-card"
          >
            <span class="md-agent-num" aria-hidden="true">
              {{ String(idx + 1).padStart(2, '0') }}
            </span>
            <h3 class="md-agent-role">
              {{ agentRoleLabel(agent.role_key) }}
            </h3>
            <p class="md-agent-profile">
              {{ agent.profile[locale] || agent.profile.fr }}
            </p>
          </article>
        </div>
      </section>

      <!-- ───────────── 5. Insights clés ───────────── -->
      <section class="md-insights" :aria-labelledby="insightsId">
        <div class="md-section-head">
          <span class="md-section-kicker">
            {{ $t('models.detail.section.insights.kicker') }}
          </span>
          <h2 :id="insightsId" class="md-h2">
            {{ $t('models.detail.section.insights.title') }}
          </h2>
          <p class="md-section-sub">
            {{ $t('models.detail.section.insights.subtitle') }}
          </p>
        </div>
        <ul class="md-insights-list">
          <li
            v-for="(insight, idx) in insightsLocalized"
            :key="idx"
            class="md-insight"
          >
            <span class="md-insight-check" aria-hidden="true">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none">
                <path d="M3 8.5l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span class="md-insight-text">{{ insight }}</span>
          </li>
        </ul>
      </section>

      <!-- ───────────── 6. Cas d'usage décideurs ───────────── -->
      <section class="md-usecases" :aria-labelledby="usecasesId">
        <div class="md-section-head">
          <span class="md-section-kicker">
            {{ $t('models.detail.section.useCases.kicker') }}
          </span>
          <h2 :id="usecasesId" class="md-h2">
            {{ $t('models.detail.section.useCases.title') }}
          </h2>
          <p class="md-section-sub">
            {{ $t('models.detail.section.useCases.subtitle') }}
          </p>
        </div>
        <div class="md-usecases-grid">
          <article
            v-for="(uc, idx) in useCasesLocalized"
            :key="idx"
            class="md-usecase-card"
          >
            <span class="md-usecase-num" aria-hidden="true">
              0{{ idx + 1 }}
            </span>
            <p class="md-usecase-text">{{ uc }}</p>
          </article>
        </div>
      </section>

      <!-- ───────────── 7. CTA double ───────────── -->
      <section class="md-cta" :aria-labelledby="ctaId">
        <div class="md-cta-inner">
          <h2 :id="ctaId" class="md-cta-title">
            {{ $t('models.detail.section.cta.title') }}
          </h2>
          <p class="md-cta-sub">
            {{ $t('models.detail.section.cta.subtitle') }}
          </p>
          <div class="md-cta-row">
            <button
              type="button"
              class="md-btn md-btn--primary"
              @click="onOrderModel"
            >
              <span>{{ orderLabel }}</span>
              <span class="md-btn-arrow" aria-hidden="true">→</span>
            </button>
            <button
              type="button"
              class="md-btn md-btn--ghost"
              @click="onCustomRequest"
            >
              <span>{{ $t('models.detail.section.cta.customRequest') }}</span>
              <span class="md-btn-arrow" aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </section>

      <!-- ───────────── 8. Méthodologie ───────────── -->
      <section class="md-methodology" :aria-labelledby="methodologyId">
        <div class="md-methodology-inner">
          <span class="md-section-kicker">
            {{ $t('models.detail.section.methodology.kicker') }}
          </span>
          <h2 :id="methodologyId" class="md-methodology-title">
            {{ $t('models.detail.section.methodology.title') }}
          </h2>
          <p class="md-methodology-body">
            {{ $t('models.detail.section.methodology.body') }}
          </p>
          <div class="md-methodology-links">
            <router-link :to="{ name: 'Calibration' }" class="md-link-quiet">
              {{ $t('models.detail.section.methodology.calibrationLink') }} →
            </router-link>
            <router-link :to="{ name: 'ModelsList' }" class="md-link-quiet">
              {{ $t('models.detail.section.methodology.allModelsLink') }} →
            </router-link>
          </div>
        </div>
      </section>
    </main>

    <main v-else class="md-main md-not-found">
      <section class="md-empty">
        <h1 class="md-h1 md-empty-title">
          {{ $t('models.detail.notFound.title') }}
        </h1>
        <p class="md-empty-sub">
          {{ $t('models.detail.notFound.subtitle') }}
        </p>
        <router-link :to="{ name: 'ModelsList' }" class="md-btn md-btn--primary">
          <span>{{ $t('models.detail.notFound.backCta') }}</span>
          <span class="md-btn-arrow" aria-hidden="true">→</span>
        </router-link>
      </section>
    </main>

    <footer class="md-footer">
      <div class="md-footer-inner">
        <span class="md-footer-brand">{{ $t('nav.brand') }}</span>
        <span class="md-footer-tag">{{ $t('models.list.footer.tagline') }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

const props = defineProps({
  slug: { type: String, required: true },
})

// US-090 — Registry étendu via import.meta.glob (build-time, eager). Prend
// en charge les 18 modèles de la vitrine sans liste hardcodée à maintenir.
// L'eager glob est équivalent en performance à des imports nommés statiques :
// Vite tree-shake et bundle les JSON dans le chunk de la vue.
const _modulesGlob = import.meta.glob('../models/*.json', { eager: true })
const REGISTRY = Object.entries(_modulesGlob).reduce((acc, [path, mod]) => {
  const data = mod.default || mod
  if (data && typeof data.slug === 'string') {
    acc[data.slug] = data
  }
  return acc
}, {})

const { locale: i18nLocale, t } = useI18n()
const router = useRouter()

const locale = computed(() => {
  const l = i18nLocale.value
  return ['fr', 'en', 'ar'].includes(l) ? l : 'fr'
})

const model = computed(() => REGISTRY[props.slug] || null)

const heroId = 'md-hero-h'
const decisionId = 'md-decision-h'
const contextId = 'md-context-h'
const agentsId = 'md-agents-h'
const insightsId = 'md-insights-h'
const usecasesId = 'md-usecases-h'
const ctaId = 'md-cta-h'
const methodologyId = 'md-methodology-h'

const titleLocalized = computed(() => {
  if (!model.value) return ''
  return model.value.title[locale.value] || model.value.title.fr
})
const subtitleLocalized = computed(() => {
  if (!model.value) return ''
  return model.value.subtitle[locale.value] || model.value.subtitle.fr
})
const decisionLocalized = computed(() => {
  if (!model.value) return ''
  return model.value.decision_question[locale.value] || model.value.decision_question.fr
})
const contextParagraphs = computed(() => {
  if (!model.value) return []
  const raw = model.value.context_long[locale.value] || model.value.context_long.fr
  // Split sur les double-newlines pour garder une mise en page narrative aérée.
  return raw.split(/\n\n+/).map((p) => p.trim()).filter(Boolean)
})
const insightsLocalized = computed(() => {
  if (!model.value) return []
  return model.value.key_insights[locale.value] || model.value.key_insights.fr || []
})
const useCasesLocalized = computed(() => {
  if (!model.value) return []
  return (
    model.value.use_cases_decisionmakers[locale.value] ||
    model.value.use_cases_decisionmakers.fr ||
    []
  )
})
const orderLabel = computed(() => {
  if (!model.value) return ''
  return model.value.cta_label[locale.value] || model.value.cta_label.fr
})
const brierLabel = computed(() => {
  if (!model.value) return '—'
  const v = model.value.brier_illustrative
  if (typeof v !== 'number' || !Number.isFinite(v)) return '—'
  return v.toFixed(2)
})

// Mapping modèle → situation radio QuoteView (réutilise la mécanique US-085).
// US-090 — étendu aux 18 modèles. Le formulaire QuoteView expose trois
// situations : 'crisis' (arbitrage exécutif sous tension), 'policy' (parcours
// législatif ou réglementaire), 'campaign' (lancement, communication,
// adoption marché). On retombe sur la plus pertinente quand la sémantique
// du modèle est ambiguë.
const MODEL_TO_SITUATION = {
  // 5 modèles US-086 originaux
  'fusion-bancaire-mena': 'crisis',
  'crisis-drill-24h': 'crisis',
  'allocation-fonds-strategique': 'crisis',
  'stress-test-politique': 'policy',
  'lancement-diaspora-eu': 'campaign',
  // 13 modèles US-090
  'adcheck-pre-launch': 'campaign',
  'budget-loi-finances': 'policy',
  'campus-controversy': 'crisis',
  'implantation-startup': 'crisis',
  'corporate-crisis': 'crisis',
  'crypto-launch': 'campaign',
  'historical-whatif': 'policy',
  'pmf-startup-tech': 'campaign',
  'political-debate': 'policy',
  'primaires-parti-politique': 'policy',
  'product-announcement': 'campaign',
  'product-launch': 'campaign',
  'she-start-cohort': 'campaign',
}

function onOrderModel () {
  if (!model.value) return
  router.push({
    name: 'Quote',
    query: {
      model: model.value.slug,
      situation: MODEL_TO_SITUATION[model.value.slug] || '',
    },
  })
}

function onCustomRequest () {
  if (!model.value) return
  // Variante : on indique au prospect qu'il commande un modèle similaire personnalisé.
  // Le param ?customize=1 est lu côté QuoteView pour pré-remplir la zone libre.
  router.push({
    name: 'Quote',
    query: {
      model: model.value.slug,
      situation: MODEL_TO_SITUATION[model.value.slug] || '',
      customize: '1',
    },
  })
}

// Note : l'i18n key d'un agent est stockée sous models.detail.agents.roles.<role_key>.
// US-090 — Pour les 13 nouveaux modèles, les role_key ne sont pas tous présents
// dans les locales (la traduction des rôles spécifiques sera ajoutée au fil de
// l'exposition des modèles). Quand la clé n'existe pas, on retombe sur une
// transformation lisible du role_key lui-même (snake_case → mots capitalisés)
// pour ne jamais afficher une clé i18n brute à l'utilisateur final.
function agentRoleLabel (roleKey) {
  if (!roleKey) return ''
  const i18nKey = `models.detail.agents.roles.${roleKey}`
  const translated = t(i18nKey)
  // vue-i18n renvoie la clé littérale quand la traduction est manquante ;
  // dans ce cas on convertit le role_key en libellé lisible pour fallback.
  if (translated === i18nKey) {
    return roleKey
      .split(/[_\-]/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  }
  return translated
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════
   Styles — tokens --wi-* exclusifs. RTL via CSS logical props.
   ════════════════════════════════════════════════════════════ */
.md-page {
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ───── Topbar (mêmes patterns que ModelsListView) ───── */
.md-topbar {
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
.md-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: var(--wi-h3-size);
  color: var(--wi-on-bg);
  text-decoration: none;
  letter-spacing: -0.02em;
}
.md-nav {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
}
.md-nav-link {
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-size: var(--wi-body-md);
  font-weight: 500;
  padding-inline: var(--wi-space-xs);
  padding-block: 6px;
  border-radius: var(--wi-radius-sm);
  transition: color var(--ms-transition), background var(--ms-transition);
}
.md-nav-link:hover {
  color: var(--wi-primary);
  background: var(--wi-surface-container-low);
}
.md-nav-cta {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  padding-inline: var(--wi-space-sm);
  padding-block: 10px;
  border-radius: var(--wi-radius-interactive);
  font-weight: 600;
  font-size: var(--wi-body-md);
  text-decoration: none;
  box-shadow: var(--wi-shadow-sm);
}
.md-nav-cta:hover {
  background: var(--ms-orange-strong);
}
@media (max-width: 720px) {
  .md-topbar {
    padding-inline: var(--wi-space-sm);
  }
  .md-nav-link {
    display: none;
  }
}

/* ───── Main ───── */
.md-main {
  display: flex;
  flex-direction: column;
  padding-inline: var(--wi-space-md);
}

/* ───── Hero ───── */
.md-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: start;
  padding-block: var(--wi-space-xl);
  max-inline-size: 920px;
  margin-inline: auto;
  width: 100%;
  overflow: hidden;
}
.md-hero-glow {
  position: absolute;
  inset-block-start: -10%;
  inset-inline-start: 0;
  width: min(720px, 80%);
  height: 360px;
  background: radial-gradient(
    ellipse at center,
    var(--wi-primary-container) 0%,
    transparent 60%
  );
  opacity: 0.12;
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}
.md-hero > * {
  position: relative;
  z-index: 1;
}
.md-hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wi-space-xs);
  margin-block-end: var(--wi-space-md);
}
.md-sector-pill {
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
.md-sector-pill--banque {
  background: var(--wi-primary-soft);
  color: var(--wi-primary);
}
.md-sector-pill--crisis {
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
}
.md-sector-pill--investissement {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}
.md-sector-pill--politique {
  background: var(--wi-tertiary-container);
  color: var(--wi-on-tertiary-container);
}
.md-sector-pill--distribution {
  background: color-mix(in srgb, var(--wi-primary-container) 25%, var(--wi-surface));
  color: var(--wi-on-primary-container);
}
/* US-090 — secteurs étendus pour les 13 nouveaux modèles. Cohérent avec
   les classes de ModelsListView pour conserver la même grammaire visuelle. */
.md-sector-pill--communication {
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
}
.md-sector-pill--politique-publique {
  background: var(--wi-tertiary-container);
  color: var(--wi-on-tertiary-container);
}
.md-sector-pill--marketing-export {
  background: color-mix(in srgb, var(--wi-primary-container) 25%, var(--wi-surface));
  color: var(--wi-on-primary-container);
}
.md-sector-pill--startup-tech {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}
.md-sector-pill--crypto {
  background: color-mix(in srgb, var(--wi-secondary-container) 60%, var(--wi-surface));
  color: var(--wi-on-secondary-container);
}
.md-sector-pill--histoire-contrefactuel {
  background: color-mix(in srgb, var(--wi-tertiary-container) 60%, var(--wi-surface));
  color: var(--wi-on-tertiary-container);
}
.md-sector-pill--education {
  background: color-mix(in srgb, var(--wi-error-container) 50%, var(--wi-surface));
  color: var(--wi-on-error-container);
}
.md-sector-pill--programme-entrepreneurial {
  background: color-mix(in srgb, var(--wi-secondary-container) 40%, var(--wi-surface));
  color: var(--wi-on-secondary-container);
}
.md-brier-pill {
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
.md-brier-dot {
  color: var(--wi-secondary);
  font-size: 8px;
}
.md-brier-label {
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.md-brier-value {
  font-weight: 700;
  color: var(--wi-on-surface);
  font-variant-numeric: tabular-nums;
}

.md-h1 {
  font-family: var(--wi-font-heading);
  font-weight: var(--wi-h1-weight);
  font-size: clamp(34px, 5vw, 56px);
  line-height: 1.1;
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-bg);
  margin-block-end: var(--wi-space-md);
}
.md-hero-sub {
  font-size: clamp(17px, 1.6vw, 20px);
  line-height: 1.55;
  color: var(--wi-on-surface-variant);
  max-inline-size: 720px;
  margin: 0;
}

/* ───── Section commons ───── */
.md-section-head {
  margin-inline: auto;
  max-inline-size: 920px;
  margin-block-end: var(--wi-space-md);
}
.md-section-kicker {
  display: inline-block;
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wi-primary);
  margin-block-end: var(--wi-space-xs);
}
.md-h2 {
  font-family: var(--wi-font-heading);
  font-size: clamp(26px, 3vw, var(--wi-h2-size));
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-bg);
  margin: 0;
}
.md-section-sub {
  font-size: 16px;
  line-height: 1.6;
  color: var(--wi-on-surface-variant);
  max-inline-size: 720px;
  margin-block-start: var(--wi-space-xs);
}

/* ───── 2. Decision (terracotta) ───── */
.md-decision {
  padding-block: var(--wi-space-lg);
  max-inline-size: 1080px;
  margin-inline: auto;
  width: 100%;
}
.md-decision-inner {
  background: linear-gradient(
    135deg,
    var(--wi-surface-container-low) 0%,
    var(--wi-surface-container) 100%
  );
  border-inline-start: 4px solid var(--wi-primary);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg);
  box-shadow: var(--wi-shadow-md);
}
.md-decision-title {
  font-family: var(--wi-font-heading);
  font-size: clamp(22px, 2.4vw, 28px);
  font-weight: 600;
  color: var(--wi-on-bg);
  margin: 0 0 var(--wi-space-md);
  letter-spacing: -0.01em;
}
.md-decision-quote {
  font-family: var(--wi-font-heading);
  font-size: clamp(20px, 2vw, 24px);
  line-height: 1.4;
  color: var(--wi-primary);
  margin: 0;
  font-weight: 500;
  font-style: italic;
}
.md-decision-mark {
  color: var(--wi-primary-container);
  margin-inline: 4px;
}

/* ───── 3. Context — 2 colonnes desktop ───── */
.md-context {
  padding-block: var(--wi-space-lg);
  max-inline-size: 1080px;
  margin-inline: auto;
  width: 100%;
}
.md-context-head {
  margin-block-end: var(--wi-space-md);
}
.md-context-body {
  column-count: 1;
  column-gap: var(--wi-space-lg);
}
@media (min-width: 980px) {
  .md-context-body {
    column-count: 2;
  }
}
.md-context-para {
  font-size: 16px;
  line-height: 1.7;
  color: var(--wi-on-surface);
  margin: 0 0 var(--wi-space-md);
  break-inside: avoid;
}

/* ───── 4. Agents ───── */
.md-agents {
  padding-block: var(--wi-space-lg);
  max-inline-size: 1080px;
  margin-inline: auto;
  width: 100%;
}
.md-agents-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
}
@media (min-width: 720px) {
  .md-agents-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (min-width: 1080px) {
  .md-agents-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
.md-agent-card {
  position: relative;
  padding: var(--wi-space-md);
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-sm);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}
.md-agent-num {
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 700;
  color: var(--wi-primary);
  letter-spacing: 0.08em;
  font-variant-numeric: tabular-nums;
}
.md-agent-role {
  font-family: var(--wi-font-heading);
  font-size: 18px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--wi-on-surface);
  margin: 0;
}
.md-agent-profile {
  font-size: 14px;
  line-height: 1.55;
  color: var(--wi-on-surface-variant);
  margin: 0;
}

/* ───── 5. Insights ───── */
.md-insights {
  padding-block: var(--wi-space-lg);
  max-inline-size: 1080px;
  margin-inline: auto;
  width: 100%;
}
.md-insights-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: var(--wi-space-sm);
  max-inline-size: 920px;
  margin-inline: auto;
}
.md-insight {
  display: flex;
  align-items: flex-start;
  gap: var(--wi-space-sm);
  padding-block: var(--wi-space-xs);
  border-block-end: 1px dashed var(--wi-outline-variant);
}
.md-insight:last-child {
  border-block-end: none;
}
.md-insight-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
  margin-block-start: 3px;
}
.md-insight-text {
  font-size: 16px;
  line-height: 1.55;
  color: var(--wi-on-surface);
}

/* ───── 6. Use cases ───── */
.md-usecases {
  padding-block: var(--wi-space-lg);
  max-inline-size: 1080px;
  margin-inline: auto;
  width: 100%;
}
.md-usecases-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--wi-space-md);
}
@media (min-width: 720px) {
  .md-usecases-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
.md-usecase-card {
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}
.md-usecase-num {
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 700;
  color: var(--wi-primary);
  letter-spacing: 0.08em;
  font-variant-numeric: tabular-nums;
}
.md-usecase-text {
  font-size: 15px;
  line-height: 1.55;
  color: var(--wi-on-surface);
  margin: 0;
}

/* ───── 7. CTA ───── */
.md-cta {
  padding-block: var(--wi-space-xl);
  max-inline-size: 1080px;
  margin-inline: auto;
  width: 100%;
}
.md-cta-inner {
  background: linear-gradient(
    135deg,
    var(--wi-primary) 0%,
    var(--ms-orange-strong) 100%
  );
  color: var(--wi-on-primary);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg);
  text-align: center;
  box-shadow: var(--wi-shadow-lg);
}
.md-cta-title {
  font-family: var(--wi-font-heading);
  font-size: clamp(24px, 3vw, 32px);
  font-weight: 600;
  margin: 0 0 var(--wi-space-sm);
  letter-spacing: -0.01em;
  color: var(--wi-on-primary);
}
.md-cta-sub {
  font-size: 16px;
  line-height: 1.55;
  margin: 0 0 var(--wi-space-md);
  color: color-mix(in srgb, var(--wi-on-primary) 88%, transparent);
}
.md-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wi-space-sm);
  justify-content: center;
}
.md-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding-inline: var(--wi-space-md);
  padding-block: 14px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-heading);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  text-decoration: none;
  transition: transform var(--ms-transition), background var(--ms-transition),
              color var(--ms-transition), border-color var(--ms-transition);
  white-space: nowrap;
}
.md-btn--primary {
  background: var(--wi-bg);
  color: var(--wi-primary);
  box-shadow: var(--wi-shadow-md);
}
.md-btn--primary:hover {
  background: var(--wi-surface);
  transform: translateY(-2px);
}
.md-btn--ghost {
  background: transparent;
  color: var(--wi-on-primary);
  border-color: color-mix(in srgb, var(--wi-on-primary) 60%, transparent);
}
.md-btn--ghost:hover {
  background: color-mix(in srgb, var(--wi-on-primary) 12%, transparent);
  border-color: var(--wi-on-primary);
}
.md-btn-arrow {
  transition: transform var(--ms-transition);
}
.md-btn:hover .md-btn-arrow {
  transform: translateX(3px);
}
[dir="rtl"] .md-btn-arrow {
  transform: scaleX(-1);
}
[dir="rtl"] .md-btn:hover .md-btn-arrow {
  transform: scaleX(-1) translateX(3px);
}

/* ───── 8. Methodology ───── */
.md-methodology {
  padding-block: var(--wi-space-lg);
  max-inline-size: 1080px;
  margin-inline: auto;
  width: 100%;
}
.md-methodology-inner {
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg);
}
.md-methodology-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: 600;
  color: var(--wi-on-bg);
  margin: 0 0 var(--wi-space-sm);
  letter-spacing: -0.01em;
}
.md-methodology-body {
  font-size: 15px;
  line-height: 1.6;
  color: var(--wi-on-surface-variant);
  margin: 0 0 var(--wi-space-md);
}
.md-methodology-links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wi-space-md);
}
.md-link-quiet {
  color: var(--wi-on-primary-container);
  text-decoration: underline;
  text-underline-offset: 3px;
  font-weight: 600;
  font-size: 14px;
}
.md-link-quiet:hover {
  color: var(--wi-primary);
}

/* ───── Empty / not found ───── */
.md-not-found {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.md-empty {
  text-align: center;
  max-inline-size: 540px;
  margin-inline: auto;
}
.md-empty-title {
  font-size: clamp(28px, 4vw, 40px);
}
.md-empty-sub {
  font-size: 16px;
  color: var(--wi-on-surface-variant);
  margin-block-end: var(--wi-space-md);
}

/* ───── Footer ───── */
.md-footer {
  border-block-start: 1px solid var(--wi-outline-variant);
  padding-block: var(--wi-space-md);
  padding-inline: var(--wi-space-md);
  background: var(--wi-surface-container-low);
}
.md-footer-inner {
  max-inline-size: 1280px;
  margin-inline: auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-sm);
}
.md-footer-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--wi-on-bg);
}
.md-footer-tag {
  font-size: 13px;
  color: var(--wi-on-surface-variant);
}

@media (prefers-reduced-motion: reduce) {
  .md-btn,
  .md-btn-arrow,
  .md-nav-cta {
    transition: none;
  }
}
</style>
