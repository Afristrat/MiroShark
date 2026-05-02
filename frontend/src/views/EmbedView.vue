<template>
  <!--
    EmbedView — Bassira Embed Widget
    ───────────────────────────────────────────────────────────────
    Refonte Stitch (US-053 Warm Intelligence) :
      - bandeau d'en-tête crème (--wi-bg) + wordmark BASSIRA
      - badge catégoriel (couleur dépendante de quality.health)
      - métrique-clé (Outfit 600, ~48px) + sparkline minimaliste
      - liste de 3 « key findings » dérivée de consensus / résolution
      - lien « View full simulation → »
      - footer crème « Powered by Bassira · بصيرة »
    Fonctionne dès 360 px, pensé pour l'intégration iframe (pas de
    scroll lock, overflow maîtrisé, max-width 600 px).
    Toute la logique data (simulationId, fetchData, refs) est
    préservée — seul le rendu visuel change.
  -->
  <div
    class="embed-widget"
    :class="[themeClass, { 'chart-only': chartOnly, 'compact': isCompact }]"
  >
    <div v-if="loading" class="embed-state">
      <div class="embed-spinner" aria-hidden="true"></div>
      <span>{{ $t('simulation.view.loading') }}</span>
    </div>

    <div v-else-if="error" class="embed-state embed-error">
      <span>{{ error }}</span>
      <a class="embed-link" :href="simulationUrl" target="_blank" rel="noopener">
        {{ $t('embed.openInNewTab') }} ↗
      </a>
    </div>

    <template v-else>
      <!-- Bandeau d'en-tête crème : wordmark BASSIRA + icône lien externe -->
      <header v-if="!chartOnly" class="embed-band embed-band--top">
        <span class="embed-wordmark">BASSIRA</span>
        <a
          class="embed-icon-link"
          :href="simulationUrl"
          target="_blank"
          rel="noopener"
          :aria-label="$t('embed.openInNewTab')"
        >
          <span class="material-symbols-outlined" aria-hidden="true">open_in_new</span>
        </a>
      </header>

      <!-- Corps : meta + titre + métrique + sparkline + findings + CTA -->
      <div class="embed-body">
        <div v-if="!chartOnly" class="embed-meta-row">
          <span v-if="categoryLabel" class="embed-badge" :class="`embed-badge--${categoryTone}`">
            {{ categoryLabel }}
          </span>
          <span class="embed-meta-id">{{ metaIdLabel }}</span>
        </div>

        <h2 v-if="!chartOnly" class="embed-title" :title="summary?.scenario">
          {{ scenarioTitle }}
        </h2>

        <!-- Carte métrique : %  dominant + libellé + sparkline -->
        <div class="embed-metric-card">
          <div class="embed-metric-text">
            <span class="embed-metric-value">{{ keyMetricValue }}</span>
            <span class="embed-metric-label">{{ keyMetricLabel }}</span>
          </div>
          <svg
            v-if="hasBelief"
            class="embed-sparkline"
            preserveAspectRatio="none"
            :viewBox="`0 0 ${SPARK_W} ${SPARK_H}`"
            role="img"
            :aria-label="chartAriaLabel"
          >
            <defs>
              <linearGradient :id="sparkGradientId" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="var(--wi-primary-container)" stop-opacity="0.45" />
                <stop offset="100%" stop-color="var(--wi-primary-container)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path
              v-if="sparkArea"
              :d="sparkArea"
              :fill="`url(#${sparkGradientId})`"
            />
            <polyline
              v-if="sparkLine"
              :points="sparkLine"
              fill="none"
              stroke="var(--wi-primary-container)"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <div v-else class="embed-sparkline-empty" aria-hidden="true">
            <span class="material-symbols-outlined">show_chart</span>
          </div>
        </div>

        <!-- Liste des key findings dérivée des données disponibles -->
        <ul v-if="!chartOnly && keyFindings.length" class="embed-findings">
          <li
            v-for="(finding, idx) in keyFindings"
            :key="idx"
            class="embed-finding"
            :class="`embed-finding--${finding.tone}`"
          >
            <span
              class="material-symbols-outlined embed-finding-icon"
              aria-hidden="true"
            >{{ finding.icon }}</span>
            <span class="embed-finding-text">{{ finding.text }}</span>
          </li>
        </ul>

        <!-- CTA texte « View full simulation → » -->
        <a
          v-if="!chartOnly"
          class="embed-cta"
          :href="simulationUrl"
          target="_blank"
          rel="noopener"
        >
          <span>{{ $t('embed.openInNewTab') }}</span>
          <span class="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
        </a>
      </div>

      <!-- Bandeau de pied crème : attribution Bassira + بصيرة -->
      <footer v-if="!chartOnly" class="embed-band embed-band--bottom">
        <span class="embed-attribution">
          Powered by Bassira
          <span class="embed-attribution-dot" aria-hidden="true">·</span>
          <span class="embed-attribution-arabic" lang="ar">بصيرة</span>
        </span>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getEmbedSummary } from '../api/simulation'

const { t } = useI18n()

const props = defineProps({
  simulationId: {
    type: String,
    default: ''
  }
})

const route = useRoute()
const simulationId = computed(() => props.simulationId || route.params.simulationId)

const theme = computed(() => (route.query.theme === 'dark' ? 'dark' : 'light'))
const themeClass = computed(() => `theme-${theme.value}`)
const chartOnly = computed(() => route.query.chart_only === 'true' || route.query.chart_only === '1')

// Sparkline viewBox dimensions (responsive via CSS).
const SPARK_W = 120
const SPARK_H = 40

const loading = ref(true)
const error = ref('')
const summary = ref(null)

// Identifiant unique du gradient SVG : évite les collisions quand
// plusieurs widgets co-existent sur la même page hôte.
const sparkGradientId = `bassira-spark-${Math.random().toString(36).slice(2, 9)}`

const scenarioTitle = computed(() => {
  const raw = (summary.value?.scenario || '').trim()
  if (!raw) return t('panels.history.noTitle')
  return raw.length > 90 ? raw.slice(0, 90).trimEnd() + '…' : raw
})

const simulationUrl = computed(() => {
  if (!simulationId.value) return '/'
  return `${window.location.origin}/simulation/${simulationId.value}/start`
})

const statusKey = computed(() => {
  if (!summary.value) return 'idle'
  const s = (summary.value.runner_status || summary.value.status || '').toLowerCase()
  if (s === 'completed' || s === 'finished' || s === 'stopped') return 'completed'
  if (s === 'running' || s === 'in_progress') return 'running'
  if (s === 'error' || s === 'failed') return 'failed'
  return 'idle'
})

const statusLabel = computed(() => {
  switch (statusKey.value) {
    case 'completed': return t('simulation.run.completed')
    case 'running': return t('simulation.run.running')
    case 'failed': return t('simulation.run.failed')
    default: return t('process.common.readyToLaunch')
  }
})

const hasBelief = computed(() => !!summary.value?.belief?.rounds?.length)

const finalBullish = computed(() => Math.round(summary.value?.belief?.final?.bullish ?? 0))
const finalNeutral = computed(() => Math.round(summary.value?.belief?.final?.neutral ?? 0))
const finalBearish = computed(() => Math.round(summary.value?.belief?.final?.bearish ?? 0))

// Stance dominante calculée sur l'état final : alimente la métrique-clé.
const dominantStance = computed(() => {
  if (!hasBelief.value) return null
  const bu = finalBullish.value
  const ne = finalNeutral.value
  const be = finalBearish.value
  if (bu >= ne && bu >= be) return { key: 'bullish', value: bu }
  if (be >= bu && be >= ne) return { key: 'bearish', value: be }
  return { key: 'neutral', value: ne }
})

const keyMetricValue = computed(() => {
  if (!hasBelief.value) {
    // Fallback : afficher la progression (round courant / total) si pas de belief.
    const total = summary.value?.total_rounds || 0
    const current = summary.value?.current_round || 0
    if (total > 0) return `${Math.round((current / total) * 100)}%`
    return '—'
  }
  return `${dominantStance.value?.value ?? 0}%`
})

const keyMetricLabel = computed(() => {
  if (!hasBelief.value) {
    if ((summary.value?.total_rounds || 0) > 0) return t('charts.common.round')
    return statusLabel.value
  }
  const k = dominantStance.value?.key
  if (k === 'bullish') return t('scenarios.bull')
  if (k === 'bearish') return t('scenarios.bear')
  return t('scenarios.neutral')
})

// Catégorie / badge : dérivée de quality.health (excellent/good/low) ou
// du statut runner. Donne le ton coloré du badge en haut du widget.
const categoryLabel = computed(() => {
  const h = (summary.value?.quality?.health || '').toLowerCase()
  if (h) return h.charAt(0).toUpperCase() + h.slice(1)
  return statusLabel.value
})

const categoryTone = computed(() => {
  const h = (summary.value?.quality?.health || '').toLowerCase()
  if (h === 'excellent') return 'mint'
  if (h === 'good') return 'peach'
  if (h === 'low' || h === 'poor') return 'terracotta'
  if (statusKey.value === 'failed') return 'terracotta'
  if (statusKey.value === 'running') return 'orange'
  return 'orange'
})

// Méta : ID raccourci + date de création (formattée yyyy-mm-dd → DD MMM YYYY).
const metaIdLabel = computed(() => {
  const id = (summary.value?.simulation_id || simulationId.value || '').toString()
  const shortId = id ? `SIM-${id.slice(0, 6).toUpperCase()}` : 'SIM-—'
  const date = (summary.value?.created_date || '').trim()
  if (!date) return shortId
  return `${shortId} · ${formatDate(date)}`
})

function formatDate(iso) {
  // iso : "YYYY-MM-DD" ou ISO complet ; on tolère un parse échoué.
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

const chartAriaLabel = computed(() => {
  if (!hasBelief.value) return 'No belief trajectory'
  return `Belief drift across ${summary.value.belief.rounds.length} rounds`
})

// Sparkline : on trace la trajectoire bullish (ou la stance dominante)
// sur la durée de la simulation. Une seule polyline + un fill dégradé.
const sparkSeries = computed(() => {
  if (!hasBelief.value) return []
  const k = dominantStance.value?.key || 'bullish'
  const series = summary.value.belief[k] || summary.value.belief.bullish || []
  return series.map((v) => Math.max(0, Math.min(100, Number(v) || 0)))
})

const sparkLine = computed(() => {
  const series = sparkSeries.value
  if (series.length === 0) return ''
  if (series.length === 1) {
    // Trace une ligne plate horizontale au lieu d'un point isolé.
    const y = (SPARK_H * (1 - series[0] / 100)).toFixed(2)
    return `0,${y} ${SPARK_W},${y}`
  }
  const xStep = SPARK_W / (series.length - 1)
  return series
    .map((v, i) => `${(i * xStep).toFixed(2)},${(SPARK_H * (1 - v / 100)).toFixed(2)}`)
    .join(' ')
})

const sparkArea = computed(() => {
  const series = sparkSeries.value
  if (series.length === 0) return ''
  if (series.length === 1) {
    const y = (SPARK_H * (1 - series[0] / 100)).toFixed(2)
    return `M 0,${y} L ${SPARK_W},${y} L ${SPARK_W},${SPARK_H} L 0,${SPARK_H} Z`
  }
  const xStep = SPARK_W / (series.length - 1)
  const top = series
    .map((v, i) => `${(i * xStep).toFixed(2)},${(SPARK_H * (1 - v / 100)).toFixed(2)}`)
    .join(' L ')
  return `M ${top} L ${SPARK_W},${SPARK_H} L 0,${SPARK_H} Z`
})

// Key findings : liste de 2-3 entrées dérivées des données disponibles
// (consensus, résolution, qualité, statut). Chaque entrée a un ton
// (success / warning / info) qui colore l'icône Material Symbols.
const keyFindings = computed(() => {
  const items = []
  const b = summary.value?.belief
  const r = summary.value?.resolution
  const q = summary.value?.quality

  if (b?.consensus_round && b?.consensus_stance) {
    items.push({
      tone: 'success',
      icon: 'check_circle',
      text: `Consensus ${b.consensus_stance} formé au round ${b.consensus_round}.`
    })
  } else if (b && b.rounds?.length) {
    items.push({
      tone: 'info',
      icon: 'trending_flat',
      text: `Aucun consensus majoritaire sur ${b.rounds.length} rounds.`
    })
  }

  if (r) {
    if (r.accuracy_score !== null && r.accuracy_score !== undefined) {
      if (r.accuracy_score >= 1.0) {
        items.push({
          tone: 'success',
          icon: 'check_circle',
          text: `Prédiction correcte — outcome réel : ${r.actual_outcome}.`
        })
      } else if (r.accuracy_score <= 0.0) {
        items.push({
          tone: 'warning',
          icon: 'warning',
          text: `Prédiction manquée — outcome réel : ${r.actual_outcome}.`
        })
      } else {
        items.push({
          tone: 'warning',
          icon: 'warning',
          text: `Résolution partielle — outcome réel : ${r.actual_outcome}.`
        })
      }
    } else if (r.actual_outcome) {
      items.push({
        tone: 'info',
        icon: 'info',
        text: `Outcome observé : ${r.actual_outcome}.`
      })
    }
  }

  if (q?.health) {
    const h = q.health.toLowerCase()
    if (h === 'excellent' || h === 'good') {
      items.push({
        tone: 'success',
        icon: 'check_circle',
        text: `Qualité simulation : ${q.health}.`
      })
    } else {
      items.push({
        tone: 'warning',
        icon: 'warning',
        text: `Vigilance qualité : ${q.health}.`
      })
    }
  }

  // Repli si la simulation est encore en cours / vide : on sert le statut.
  if (items.length === 0) {
    items.push({
      tone: 'info',
      icon: 'info',
      text: statusLabel.value
    })
  }

  return items.slice(0, 3)
})

const isCompact = computed(() => {
  // Détection iframe étroite — passe en mode compact sous 480 px de largeur.
  if (typeof window === 'undefined') return false
  return window.innerWidth < 480
})

const fetchData = async () => {
  if (!simulationId.value) {
    error.value = 'Missing simulation id'
    loading.value = false
    return
  }
  try {
    const res = await getEmbedSummary(simulationId.value)
    if (res?.success) {
      summary.value = res.data
    } else {
      error.value = res?.error || 'Failed to load simulation'
    }
  } catch (err) {
    error.value = err?.response?.data?.error || err?.message || 'Failed to load simulation'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
  // Hôte iframe : on neutralise les paddings/backgrounds résiduels du shell
  // applicatif pour que le widget s'affiche edge-to-edge sans halo.
  if (typeof document !== 'undefined') {
    document.body.style.margin = '0'
    document.body.style.padding = '0'
    document.documentElement.style.background = 'transparent'
    document.body.style.background = 'transparent'
  }
})
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════════
   EmbedView — alignement design Stitch « Bassira Embed Widget »
   Tokens utilisés : --wi-* (Warm Intelligence) + fallback --ms-*.
   ZÉRO hex hardcodé, responsive 360 px → 600 px.
   ════════════════════════════════════════════════════════════════ */
.embed-widget {
  box-sizing: border-box;
  width: 100%;
  max-width: 600px;
  min-height: 220px;
  margin: 0 auto;
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  display: flex;
  flex-direction: column;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  box-shadow: var(--wi-shadow-sm);
  overflow: hidden;
}

/* Variant chart-only : on retire les bandeaux et on resserre le padding. */
.embed-widget.chart-only {
  min-height: 120px;
  border-radius: var(--wi-radius-sm);
}

/* États (loading / error) */
.embed-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: var(--wi-space-xs);
  padding: var(--wi-space-md);
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
}

.embed-error {
  color: var(--wi-error);
}

.embed-spinner {
  width: 22px;
  height: 22px;
  border: 2px solid var(--wi-outline-variant);
  border-top-color: var(--wi-primary);
  border-radius: 50%;
  animation: embed-spin 0.9s linear infinite;
}

@keyframes embed-spin {
  to { transform: rotate(360deg); }
}

/* Bandeaux crème (header + footer) */
.embed-band {
  background: var(--wi-bg);
  padding: var(--wi-space-xs) var(--wi-space-sm);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--wi-outline-variant);
}

.embed-band--bottom {
  border-top: 1px solid var(--wi-outline-variant);
  border-bottom: none;
  justify-content: center;
}

.embed-wordmark {
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-caption);
  letter-spacing: 0.18em;
  color: var(--wi-on-bg);
  text-transform: uppercase;
}

.embed-icon-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--wi-outline);
  text-decoration: none;
  transition: color var(--ms-transition-fast, 150ms ease);
}

.embed-icon-link:hover,
.embed-icon-link:focus-visible {
  color: var(--wi-primary);
  outline: none;
}

.embed-icon-link .material-symbols-outlined {
  font-size: 18px;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}

.embed-attribution {
  font-family: var(--wi-font-heading);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--wi-outline);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.embed-attribution-dot {
  opacity: 0.6;
  letter-spacing: 0;
}

.embed-attribution-arabic {
  font-family: 'Tajawal', var(--wi-font-body);
  font-size: 12px;
  letter-spacing: 0;
  text-transform: none;
  color: var(--wi-on-bg);
}

/* Corps du widget */
.embed-body {
  padding: var(--wi-space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
}

.embed-widget.chart-only .embed-body {
  padding: var(--wi-space-xs);
  gap: var(--wi-space-xs);
}

/* Méta-row : badge + identifiant */
.embed-meta-row {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  flex-wrap: wrap;
}

.embed-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: var(--wi-radius-sm);
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.embed-badge--orange {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}

.embed-badge--mint {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}

.embed-badge--peach {
  background: var(--ms-peach-soft);
  color: var(--ms-status-warning-text);
}

.embed-badge--terracotta {
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
}

.embed-meta-id {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-outline);
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Titre H3 */
.embed-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  letter-spacing: -0.01em;
  color: var(--wi-on-surface);
  margin: 0;
}

.embed-widget.compact .embed-title {
  font-size: 20px;
}

/* Carte métrique : valeur + libellé + sparkline */
.embed-metric-card {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-sm);
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
}

.embed-metric-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.embed-metric-value {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  font-weight: 700;
  line-height: 1;
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-surface);
}

.embed-widget.compact .embed-metric-value {
  font-size: 36px;
}

.embed-metric-label {
  font-family: var(--wi-font-body);
  font-size: 13px;
  color: var(--wi-on-surface-variant);
  text-transform: capitalize;
}

.embed-sparkline {
  flex-shrink: 0;
  width: 128px;
  height: 48px;
}

.embed-widget.compact .embed-sparkline {
  width: 96px;
  height: 36px;
}

.embed-sparkline-empty {
  flex-shrink: 0;
  width: 128px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--wi-outline-variant);
}

.embed-sparkline-empty .material-symbols-outlined {
  font-size: 32px;
}

/* Liste key findings */
.embed-findings {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 14px;
  color: var(--wi-on-surface);
}

.embed-finding {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.5;
}

.embed-finding-icon {
  flex-shrink: 0;
  font-size: 18px;
  margin-top: 1px;
  font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}

.embed-finding--success .embed-finding-icon {
  color: var(--wi-secondary);
}

.embed-finding--warning .embed-finding-icon {
  color: var(--wi-primary);
}

.embed-finding--info .embed-finding-icon {
  color: var(--wi-tertiary);
}

.embed-finding--warning .embed-finding-text {
  color: var(--wi-on-surface-variant);
  font-style: italic;
}

.embed-finding-text {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

/* CTA texte « View full simulation → » */
.embed-cta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  align-self: flex-start;
  font-family: var(--wi-font-body);
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-on-primary-container);
  text-decoration: none;
  transition: color var(--ms-transition-fast, 150ms ease);
}

.embed-cta:hover,
.embed-cta:focus-visible {
  color: var(--wi-primary);
  outline: none;
}

.embed-cta .material-symbols-outlined {
  font-size: 16px;
  font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
  transition: transform var(--ms-transition-fast, 150ms ease);
}

.embed-cta:hover .material-symbols-outlined {
  transform: translateX(2px);
}

.embed-link {
  color: var(--wi-on-primary-container);
  font-weight: 600;
  text-decoration: none;
}

.embed-link:hover {
  text-decoration: underline;
}

/* ── Mode compact (largeur < 480 px) ── */
.embed-widget.compact .embed-band {
  padding: 6px var(--wi-space-sm);
}

.embed-widget.compact .embed-body {
  padding: var(--wi-space-sm);
  gap: 12px;
}

.embed-widget.compact .embed-metric-card {
  padding: 12px;
}

/* ── Responsive ≤ 360 px (limite basse iframe) ── */
@media (max-width: 360px) {
  .embed-widget {
    border-radius: 0;
  }

  .embed-title {
    font-size: 18px;
  }

  .embed-metric-card {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .embed-metric-value {
    font-size: 36px;
  }

  .embed-sparkline,
  .embed-sparkline-empty {
    width: 100%;
    height: 36px;
  }
}

/* ── RTL : direction inversée pour l'arabe ── */
:global([lang="ar"]) .embed-cta .material-symbols-outlined {
  transform: scaleX(-1);
}

:global([lang="ar"]) .embed-cta:hover .material-symbols-outlined {
  transform: scaleX(-1) translateX(2px);
}

/* ── Dark mode (US-027) ──
   Les tokens --wi-* sont déjà overridés via [data-theme="dark"] dans
   design-tokens.css ; rien à patcher ici, juste un léger ajustement
   d'opacité du wordmark pour rester lisible sur le surface sombre. */
.embed-widget.theme-dark .embed-wordmark {
  color: var(--wi-on-bg);
}
</style>
