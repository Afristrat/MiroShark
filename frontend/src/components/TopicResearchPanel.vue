<template>
  <div v-if="shouldRender" class="trp-wrap">
    <!-- Header : label + status pill -->
    <div class="trp-head">
      <span class="trp-label">
        <span class="trp-dot" :class="{ 'trp-dot--pulse': isRunning }">◉</span>
        {{ $t('research.label') }}
        <span class="trp-sub">{{ statusLine }}</span>
      </span>
      <span
        v-if="cached"
        class="trp-cached-badge"
        :title="$t('research.subCached')"
      >{{ $t('research.subCached') }}</span>
    </div>

    <!-- État loading -->
    <div v-if="isLoading" class="trp-loading">
      <span class="trp-spinner"></span>
      {{ $t('research.loading') }}
    </div>

    <!-- État erreur -->
    <div v-else-if="isError" class="trp-error">
      ⚠ {{ $t(errorKey) }}
    </div>

    <!-- F3 mode dégradé : synthesizer indisponible → on affiche les
         scored_signals_top retournés par Kairos en fallback. -->
    <template v-else-if="isCompleted && isDegradedSynthesizer && scoredSignalsTop.length > 0">
      <div class="trp-degraded-banner" role="status">
        <span class="trp-degraded-icon">⚠</span>
        <p>
          {{ $t('research.degraded.synthesizerUnavailable', {
            reason: synthesizerFailureType || 'unknown',
            count: scoredSignalsTop.length,
          }) }}
        </p>
      </div>
      <h5 class="trp-degraded-heading">
        {{ $t('research.degraded.rawSignalsHeading', { count: scoredSignalsTop.length }) }}
      </h5>
      <ul class="trp-degraded-list">
        <li
          v-for="(sig, i) in scoredSignalsTop"
          :key="`raw-${sig.id || i}`"
          class="trp-degraded-item"
        >
          <div class="trp-degraded-item-head">
            <a
              v-if="sig.url"
              :href="sig.url"
              target="_blank"
              rel="noopener noreferrer"
              class="trp-degraded-item-title"
            >{{ sig.title || sig.url }}</a>
            <span v-else class="trp-degraded-item-title">{{ sig.title || '—' }}</span>
            <span
              v-if="typeof sig.score === 'number'"
              class="trp-degraded-score"
              :title="$t('research.degraded.scoreLabel')"
            >{{ sig.score }}</span>
          </div>
          <div class="trp-degraded-item-meta">
            <span v-if="sig.source" class="trp-degraded-source">{{ sig.source }}</span>
            <span v-if="sig.lang" class="trp-degraded-lang">{{ sig.lang }}</span>
            <span v-if="sig.url" class="trp-degraded-url" :title="sig.url">
              {{ truncateUrl(sig.url) }}
            </span>
          </div>
          <p v-if="sig.excerpt" class="trp-degraded-excerpt">{{ sig.excerpt }}</p>
        </li>
      </ul>
    </template>

    <!-- État completed : cards + verdict + coverage -->
    <template v-else-if="isCompleted && topics.length > 0">
      <div class="trp-grid">
        <article
          v-for="(topic, ti) in topics"
          :key="`${topic.label}-${ti}`"
          class="trp-card"
          :class="{ 'trp-card--devil': topic.is_devil_advocate }"
        >
          <header class="trp-card-head">
            <h4 class="trp-card-title">{{ topic.label }}</h4>
            <span
              v-if="topic.is_devil_advocate"
              class="trp-devil-badge"
            >{{ $t('research.devilAdvocate') }}</span>
          </header>

          <p v-if="topic.summary" class="trp-card-summary">{{ topic.summary }}</p>

          <!-- Variantes de brief : radio pills -->
          <div
            v-if="hasBriefVariants(topic)"
            class="trp-variants"
            role="radiogroup"
            :aria-label="topic.label"
          >
            <button
              v-for="(variant, vi) in topic.brief_variants"
              :key="`${ti}-${vi}`"
              type="button"
              class="trp-variant"
              :class="{ 'trp-variant--active': isVariantActive(ti, vi) }"
              :aria-checked="isVariantActive(ti, vi)"
              role="radio"
              @click="selectVariant(ti, vi)"
            >
              <span class="trp-variant-label">{{ briefVariantTitle(variant) }}</span>
              <span
                v-if="variant.framework_hint"
                class="trp-variant-framework"
              >{{ frameworkLabel(variant.framework_hint) }}</span>
            </button>
          </div>

          <footer class="trp-card-foot">
            <button
              v-if="activeVariantFor(ti)"
              type="button"
              class="trp-use-btn"
              @click="emitSelection(ti)"
            >
              {{ $t('research.useThisBrief') }}
              <span class="trp-arrow">→</span>
            </button>
            <span v-else class="trp-card-hint">
              {{ $t('research.noBriefSelected') }}
            </span>
            <button
              v-if="hasSources(topic)"
              type="button"
              class="trp-sources-btn"
              :aria-expanded="openSourcesIndex === ti"
              @click="toggleSources(ti)"
            >
              {{ openSourcesIndex === ti ? $t('research.hideSources') : $t('research.viewSources') }}
            </button>
          </footer>
        </article>
      </div>

      <!-- Footer : verdict + coverage gaps -->
      <div v-if="footerHasContent" class="trp-foot">
        <span
          v-if="verdict"
          class="trp-verdict"
          :class="`trp-verdict--${verdict}`"
        >{{ $t(`research.verdict.${verdict}`) }}</span>
        <span v-if="coverageGapsCount > 0" class="trp-coverage">
          {{ coverageGapsLabel }}
        </span>
      </div>
    </template>

    <!-- Sliding panel sources -->
    <transition name="trp-slide">
      <aside
        v-if="openSourcesIndex !== null && activeSources.length > 0"
        class="trp-sources-panel"
      >
        <header class="trp-sources-head">
          <h5>{{ $t('research.sourcesTitle') }}</h5>
          <button
            type="button"
            class="trp-sources-close"
            :aria-label="$t('research.hideSources')"
            @click="openSourcesIndex = null"
          >×</button>
        </header>
        <ul class="trp-sources-list">
          <li
            v-for="(src, si) in activeSources"
            :key="`src-${openSourcesIndex}-${si}`"
            class="trp-source-row"
          >
            <span class="trp-source-name">{{ src.source_name || src.name || src.url }}</span>
            <span
              v-if="typeof src.score === 'number'"
              class="trp-source-score"
              :title="src.score.toFixed(2)"
            >{{ src.score.toFixed(2) }}</span>
            <a
              v-if="src.url"
              :href="src.url"
              target="_blank"
              rel="noopener noreferrer"
              class="trp-source-url"
            >{{ truncateUrl(src.url) }}</a>
          </li>
        </ul>
      </aside>
    </transition>
  </div>
</template>

<script setup>
/**
 * US-B02 — TopicResearchPanel.
 *
 * Composant cards topics + brief_variants picker + sliding panel sources,
 * piloté par ConsoleView (US-B03). N'effectue PAS le polling lui-même :
 * il consomme `status` / `result` reçus en props et émet `select` quand
 * l'utilisateur choisit un brief à instancier en simulation.
 *
 * Émet :
 *   - `select` : { topic, variant, framework_hint, signals_refs }
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { researchErrorKeyForCode } from '../api/research'

const { t } = useI18n()

const props = defineProps({
  /** UUID Kairos — null tant que pas de POST envoyé. */
  sessionId: { type: String, default: null },
  /** Cycle d'état piloté par le parent. */
  status: {
    type: String,
    default: 'idle',
    validator: (v) =>
      ['idle', 'starting', 'running', 'completed', 'failed', 'timeout', 'error'].includes(v),
  },
  /** Payload Kairos complet quand status=completed. */
  result: { type: Object, default: null },
  /** Code d'erreur backend (KAIROS_TIMEOUT, …) à mapper en message. */
  errorCode: { type: String, default: null },
  /** Secondes écoulées depuis le lancement (affichage status pendant running). */
  elapsedSeconds: { type: Number, default: 0 },
  /** True si la réponse vient du cache 1h / 24h. */
  cached: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

// ─── Computed status ────────────────────────────────────────────────────────

const isRunning = computed(() => ['starting', 'running'].includes(props.status))
const isLoading = computed(() => isRunning.value)
const isCompleted = computed(() => props.status === 'completed')
const isError = computed(() => ['failed', 'timeout', 'error'].includes(props.status))

const shouldRender = computed(() => props.status !== 'idle')

// ─── Topics + result extraction ─────────────────────────────────────────────

const topics = computed(() => {
  const arr = props.result?.topics
  return Array.isArray(arr) ? arr : []
})

const totalSources = computed(() => {
  return topics.value.reduce((sum, t) => {
    const sigs = Array.isArray(t.key_signals) ? t.key_signals.length : 0
    return sum + sigs
  }, 0)
})

const verdict = computed(() => {
  const v = (props.result?.audit?.verdict || '').toLowerCase()
  return ['pass', 'warn', 'deepen', 'fail'].includes(v) ? v : null
})

const coverageGapsCount = computed(() => {
  const cm = props.result?.coverage_map
  if (!Array.isArray(cm)) return 0
  return cm.filter((row) => row && row.has_signal === false).length
})

const coverageGapsLabel = computed(() => {
  const n = coverageGapsCount.value
  if (n <= 0) return ''
  const key = n === 1 ? 'research.coverageGap' : 'research.coverageGapPlural'
  return t(key, { n })
})

const footerHasContent = computed(
  () => verdict.value || coverageGapsCount.value > 0,
)

// F3 mode dégradé synthesizer — quand quality_warning='synthesizer_unavailable'
// et que Kairos a retourné scored_signals_top en fallback.
const qualityWarning = computed(() => props.result?.quality_warning || null)
const isDegradedSynthesizer = computed(
  () => qualityWarning.value === 'synthesizer_unavailable',
)
const scoredSignalsTop = computed(() => {
  const arr = props.result?.scored_signals_top
  return Array.isArray(arr) ? arr : []
})
const synthesizerFailureType = computed(
  () => props.result?.synthesizer_failure_type || null,
)

// ─── Status line affichée à droite du label ─────────────────────────────────

const statusLine = computed(() => {
  switch (props.status) {
    case 'starting':
      return t('research.subStarting')
    case 'running':
      return t('research.subRunning', { elapsed: props.elapsedSeconds })
    case 'completed': {
      const verdictText = verdict.value ? t(`research.verdict.${verdict.value}`) : ''
      return t('research.subCompleted', {
        topics: topics.value.length,
        sources: totalSources.value,
        verdict: verdictText,
      })
    }
    case 'failed':
      return t('research.subFailed')
    case 'timeout':
      return t('research.subTimeout')
    case 'error':
    case 'idle':
    default:
      return ''
  }
})

// ─── Erreur ─────────────────────────────────────────────────────────────────

const errorKey = computed(() => researchErrorKeyForCode(props.errorCode))

// ─── Brief variants : selection state ───────────────────────────────────────

// Map "topicIndex" → "variantIndex actif". Permet à l'user de tester
// plusieurs angles avant de confirmer "Use this brief".
const activeVariantByTopic = ref({})

const isVariantActive = (ti, vi) => activeVariantByTopic.value[ti] === vi

const selectVariant = (ti, vi) => {
  activeVariantByTopic.value = { ...activeVariantByTopic.value, [ti]: vi }
}

const activeVariantFor = (ti) => {
  const vi = activeVariantByTopic.value[ti]
  if (vi === undefined) return null
  const variants = topics.value[ti]?.brief_variants
  return Array.isArray(variants) ? variants[vi] || null : null
}

const hasBriefVariants = (topic) =>
  Array.isArray(topic?.brief_variants) && topic.brief_variants.length > 0

const briefVariantTitle = (variant) => {
  if (!variant) return ''
  return variant.label || variant.title || variant.summary || ''
}

const frameworkLabel = (hint) => {
  if (!hint) return ''
  const norm = String(hint).toLowerCase()
  const known = ['crisis', 'market', 'policy', 'cerberus', 'decision']
  return known.includes(norm) ? t(`research.framework.${norm}`) : hint
}

// ─── Sources panel ──────────────────────────────────────────────────────────

const openSourcesIndex = ref(null)

const hasSources = (topic) =>
  Array.isArray(topic?.key_signals) && topic.key_signals.length > 0

const activeSources = computed(() => {
  if (openSourcesIndex.value === null) return []
  const t = topics.value[openSourcesIndex.value]
  return Array.isArray(t?.key_signals) ? t.key_signals : []
})

const toggleSources = (ti) => {
  openSourcesIndex.value = openSourcesIndex.value === ti ? null : ti
}

const truncateUrl = (url) => {
  if (!url) return ''
  try {
    const u = new URL(url)
    return u.hostname + (u.pathname && u.pathname !== '/' ? u.pathname : '')
  } catch {
    return url.length > 60 ? `${url.slice(0, 57)}…` : url
  }
}

// ─── Emit selection ─────────────────────────────────────────────────────────

const emitSelection = (ti) => {
  const topic = topics.value[ti]
  const variant = activeVariantFor(ti)
  if (!topic || !variant) return
  emit('select', {
    topic_label: topic.label,
    topic_summary: topic.summary,
    is_devil_advocate: !!topic.is_devil_advocate,
    brief_variant: variant,
    framework_hint: variant.framework_hint || null,
    signals_refs: Array.isArray(variant.signals_refs) ? variant.signals_refs : [],
  })
}

// ─── Reset sélection quand on charge un nouveau résultat ────────────────────

watch(
  () => props.result,
  () => {
    activeVariantByTopic.value = {}
    openSourcesIndex.value = null
  },
)
</script>

<style scoped>
/* ─── Warm Intelligence — TopicResearchPanel (US-B02) ─── */
.trp-wrap {
  margin-top: var(--wi-space-md);
  padding: var(--wi-space-md);
  background: var(--wi-bg);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  font-family: var(--wi-font-body);
  position: relative;
  box-shadow: var(--wi-shadow-sm);
}

/* ─── Header ─── */
.trp-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--wi-space-sm);
}

.trp-label {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-on-bg);
  display: flex;
  align-items: center;
  gap: 8px;
}

.trp-dot {
  color: var(--wi-primary-container);
  font-size: 14px;
  display: inline-block;
}

.trp-dot--pulse {
  animation: trp-pulse 1.4s ease-in-out infinite;
}

@keyframes trp-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.trp-sub {
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  margin-left: 4px;
}

.trp-cached-badge {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
}

/* ─── Loading state ─── */
.trp-loading {
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: var(--wi-space-sm);
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-md);
}

.trp-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--wi-primary-soft);
  border-top-color: var(--wi-primary-container);
  border-radius: 50%;
  display: inline-block;
  animation: trp-spin 0.8s linear infinite;
}

@keyframes trp-spin {
  to { transform: rotate(360deg); }
}

/* ─── Error state ─── */
.trp-error {
  font-size: var(--wi-body-md);
  color: var(--wi-on-error-container, #8b1f1f);
  padding: var(--wi-space-sm);
  background: var(--wi-error-container, #fbe9e9);
  border-radius: var(--wi-radius-md);
  border: 1px solid var(--wi-error, #d8696b);
}

/* ─── Grid + cards ─── */
.trp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--wi-space-sm);
}

.trp-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-sm);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: border-color var(--ms-transition),
              box-shadow var(--ms-transition),
              transform var(--ms-transition);
  box-shadow: var(--wi-shadow-sm);
}

.trp-card:hover {
  border-color: var(--wi-primary-container);
  transform: translateY(-2px);
  box-shadow: var(--wi-shadow-orange);
}

.trp-card--devil {
  border-color: var(--wi-primary-container);
  border-width: 2px;
  background: var(--wi-secondary-container, var(--wi-surface));
}

.trp-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.trp-card-title {
  font-family: var(--wi-font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--wi-on-surface);
  margin: 0;
  line-height: 1.3;
}

.trp-devil-badge {
  font-family: var(--wi-font-body);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--wi-on-primary);
  background: var(--wi-primary-container);
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  white-space: nowrap;
  flex-shrink: 0;
}

.trp-card-summary {
  font-size: 13px;
  line-height: 1.5;
  color: var(--wi-on-surface-variant);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ─── Variants pills ─── */
.trp-variants {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.trp-variant {
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  padding: 4px 10px;
  font-family: inherit;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background var(--ms-transition-fast),
              border-color var(--ms-transition-fast),
              color var(--ms-transition-fast);
}

.trp-variant:hover {
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}

.trp-variant--active {
  background: var(--wi-on-primary-container);
  color: var(--wi-on-primary);
  border-color: var(--wi-on-primary-container);
}

.trp-variant-label {
  font-weight: 600;
}

.trp-variant-framework {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  padding: 1px 6px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface-variant);
}

.trp-variant--active .trp-variant-framework {
  background: rgb(255 255 255 / 18%);
  color: var(--wi-on-primary);
}

/* ─── Footer card ─── */
.trp-card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-top: auto;
}

.trp-use-btn {
  background: transparent;
  border: 1px solid var(--wi-on-primary-container);
  color: var(--wi-on-primary-container);
  font-family: var(--wi-font-heading);
  font-size: var(--wi-caption);
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: background var(--ms-transition-fast),
              color var(--ms-transition-fast);
}

.trp-use-btn:hover {
  background: var(--wi-on-primary-container);
  color: var(--wi-on-primary);
}

.trp-arrow {
  font-size: 13px;
}

.trp-card-hint {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-style: italic;
}

.trp-sources-btn {
  background: transparent;
  border: none;
  color: var(--wi-on-surface-variant);
  font-family: inherit;
  font-size: var(--wi-caption);
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;
  padding: 0;
  transition: color var(--ms-transition-fast);
}

.trp-sources-btn:hover {
  color: var(--wi-on-primary-container);
}

/* ─── Footer verdict + coverage ─── */
.trp-foot {
  margin-top: var(--wi-space-sm);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.trp-verdict {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  text-transform: lowercase;
  padding: 3px 10px;
  border-radius: var(--wi-radius-pill);
  letter-spacing: 0.2px;
}

.trp-verdict--pass {
  background: var(--wi-success-container, #e2f2e0);
  color: var(--wi-on-success-container, #1e5a2a);
}

.trp-verdict--warn {
  background: var(--wi-warning-container, #fdf2dc);
  color: var(--wi-on-warning-container, #8a5a14);
}

.trp-verdict--deepen {
  background: var(--wi-primary-soft, #ffe3d6);
  color: var(--wi-on-primary-container, #b34a1f);
}

.trp-verdict--fail {
  background: var(--wi-error-container, #fbe9e9);
  color: var(--wi-on-error-container, #8b1f1f);
}

.trp-coverage {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-style: italic;
}

/* ─── Sources sliding panel ─── */
.trp-sources-panel {
  position: absolute;
  top: 0;
  inset-inline-end: 0;
  bottom: 0;
  width: min(340px, 90%);
  background: var(--wi-surface);
  border-inline-start: 1px solid var(--wi-outline-variant);
  border-radius: 0 var(--wi-radius-card) var(--wi-radius-card) 0;
  padding: var(--wi-space-sm);
  overflow-y: auto;
  z-index: 5;
  box-shadow: -8px 0 24px rgb(0 0 0 / 8%);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* RTL : la bordure et l'ombre se collent à gauche, le slide vient de gauche. */
:dir(rtl) .trp-sources-panel {
  border-radius: var(--wi-radius-card) 0 0 var(--wi-radius-card);
  box-shadow: 8px 0 24px rgb(0 0 0 / 8%);
}

.trp-sources-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trp-sources-head h5 {
  margin: 0;
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--wi-on-surface);
}

.trp-sources-close {
  background: transparent;
  border: none;
  font-size: 20px;
  line-height: 1;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  padding: 0 4px;
}

.trp-sources-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trp-source-row {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  column-gap: 8px;
  font-size: var(--wi-caption);
  padding: 8px;
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-md);
}

.trp-source-name {
  font-weight: 600;
  color: var(--wi-on-surface);
}

.trp-source-score {
  font-family: var(--wi-font-mono, monospace);
  color: var(--wi-on-primary-container);
  text-align: end;
}

.trp-source-url {
  grid-column: 1 / -1;
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  word-break: break-all;
}

.trp-source-url:hover {
  text-decoration: underline;
}

/* ─── Slide transition ─── */
.trp-slide-enter-active,
.trp-slide-leave-active {
  transition: transform var(--ms-transition), opacity var(--ms-transition);
}

.trp-slide-enter-from,
.trp-slide-leave-to {
  transform: translateX(20%);
  opacity: 0;
}

:dir(rtl) .trp-slide-enter-from,
:dir(rtl) .trp-slide-leave-to {
  transform: translateX(-20%);
}

/* ─── F3 Degraded mode (synthesizer_unavailable) ─── */
.trp-degraded-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: var(--wi-warning-container, #fdf2dc);
  color: var(--wi-on-warning-container, #8a5a14);
  border: 1px solid var(--wi-warning, #e6b350);
  border-radius: var(--wi-radius-md);
  margin-bottom: var(--wi-space-sm);
  font-size: var(--wi-body-md);
  line-height: 1.45;
}

.trp-degraded-banner p {
  margin: 0;
}

.trp-degraded-icon {
  font-size: 16px;
  line-height: 1;
}

.trp-degraded-heading {
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--wi-on-surface);
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.trp-degraded-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 480px;
  overflow-y: auto;
}

.trp-degraded-item {
  padding: 10px;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: border-color var(--ms-transition-fast);
}

.trp-degraded-item:hover {
  border-color: var(--wi-primary-container);
}

.trp-degraded-item-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.trp-degraded-item-title {
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--wi-on-surface);
  text-decoration: none;
  line-height: 1.3;
}

.trp-degraded-item-title:hover {
  color: var(--wi-on-primary-container);
  text-decoration: underline;
}

.trp-degraded-score {
  font-family: var(--wi-font-mono, monospace);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  flex-shrink: 0;
  padding: 1px 6px;
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-pill);
}

.trp-degraded-item-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  flex-wrap: wrap;
}

.trp-degraded-source {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-size: 10px;
  padding: 1px 6px;
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-pill);
}

.trp-degraded-lang {
  font-family: var(--wi-font-mono, monospace);
  font-size: 10px;
  text-transform: uppercase;
}

.trp-degraded-url {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-style: italic;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trp-degraded-excerpt {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.4;
  color: var(--wi-on-surface-variant);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
