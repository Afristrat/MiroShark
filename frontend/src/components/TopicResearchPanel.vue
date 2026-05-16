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
         scored_signals_top retournés par Kairos en fallback.
         US-B04.2 : checkboxes par source + toggle all + compose zone. -->
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

      <div class="trp-degraded-toolbar">
        <h5 class="trp-degraded-heading">
          {{ $t('research.degraded.rawSignalsHeading', { count: scoredSignalsTop.length }) }}
        </h5>
        <button
          type="button"
          class="trp-degraded-toggle-all"
          @click="toggleAllSources"
        >
          {{ allSourcesSelected
            ? $t('research.compose.deselectAllSources')
            : $t('research.compose.selectAllSources') }}
        </button>
      </div>

      <ul class="trp-degraded-list">
        <li
          v-for="(sig, i) in scoredSignalsTop"
          :key="`raw-${sig.url || sig.id || i}`"
          class="trp-degraded-item"
          :class="{ 'trp-degraded-item--unselected': sig.url && !isSourceSelected(sig.url) }"
        >
          <label class="trp-degraded-item-row">
            <input
              type="checkbox"
              class="trp-degraded-checkbox"
              :checked="!sig.url || isSourceSelected(sig.url)"
              :disabled="!sig.url"
              @change="sig.url && toggleSource(sig.url)"
            />
            <div class="trp-degraded-item-body">
              <div class="trp-degraded-item-head">
                <a
                  v-if="sig.url"
                  :href="sig.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="trp-degraded-item-title"
                  @click.stop
                >{{ sig.title || sig.url }} ↗</a>
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
            </div>
          </label>
        </li>
      </ul>

      <!-- Compose zone (mode dégradé) — réutilise les mêmes éléments que
           le mode complet, mais le content est tiré de selectedSignalsDetails. -->
      <section class="trp-compose">
        <header class="trp-compose-head">
          <h5 class="trp-compose-title">🧪 {{ $t('research.compose.heading') }}</h5>
          <span class="trp-compose-count">
            {{ $t('research.compose.sourcesSelectedCount', { n: selectedSourcesCount }) }}
          </span>
        </header>
        <p v-if="selectedSourcesCount === 0" class="trp-compose-empty">
          {{ $t('research.compose.emptyDegraded') }}
        </p>
        <template v-else>
          <textarea
            v-model="composedPromptEdited"
            class="trp-compose-textarea"
            :rows="composedTextareaRows"
            :aria-label="$t('research.compose.textareaAriaLabel')"
            data-testid="composed-prompt"
          ></textarea>
          <div class="trp-compose-actions">
            <button
              type="button"
              class="trp-compose-reset"
              :disabled="composedPromptEdited === composedPromptAuto"
              @click="resetComposedToAuto"
            >
              {{ $t('research.compose.reset') }}
            </button>
            <button
              type="button"
              class="trp-compose-insert"
              :disabled="!composedPromptEdited.trim()"
              data-testid="compose-insert-btn"
              @click="insertComposed"
            >
              {{ $t('research.compose.insertWithSources', { n: selectedSourcesCount }) }} →
            </button>
          </div>
        </template>
      </section>
    </template>

    <!-- État completed : topics + multi-select briefs + composition zone -->
    <template v-else-if="isCompleted && topics.length > 0">
      <p class="trp-instructions">
        {{ $t('research.compose.instructions') }}
      </p>

      <div class="trp-grid">
        <article
          v-for="(topic, ti) in topics"
          :key="`${topic.label}-${ti}`"
          class="trp-card"
          :class="{ 'trp-card--devil': isDevilTopic(topic) }"
        >
          <header class="trp-card-head">
            <h4 class="trp-card-title">{{ topic.label }}</h4>
            <span
              v-if="isDevilTopic(topic)"
              class="trp-devil-badge"
            >{{ $t('research.devilAdvocate') }}</span>
          </header>

          <p v-if="topic.summary" class="trp-card-summary">{{ topic.summary }}</p>

          <!-- Variantes de brief : multi-select checkboxes + texte intégral -->
          <ul
            v-if="hasBriefVariants(topic)"
            class="trp-variants-list"
            :aria-label="$t('research.compose.variantsAriaLabel', { topic: topic.label })"
          >
            <li
              v-for="(variant, vi) in topic.brief_variants"
              :key="`${ti}-${vi}`"
              class="trp-variant-item"
              :class="{ 'trp-variant-item--selected': isVariantSelected(ti, vi) }"
            >
              <label class="trp-variant-row">
                <input
                  type="checkbox"
                  class="trp-variant-checkbox"
                  :checked="isVariantSelected(ti, vi)"
                  @change="toggleVariant(ti, vi)"
                />
                <div class="trp-variant-body">
                  <div class="trp-variant-header">
                    <span
                      v-if="variant.framework_hint"
                      class="trp-variant-framework"
                    >{{ frameworkLabel(variant.framework_hint) }}</span>
                    <span class="trp-variant-charcount">
                      {{ variantBriefText(variant).length }} {{ $t('research.compose.charsAbbr') }}
                    </span>
                  </div>
                  <p class="trp-variant-brief">{{ variantBriefText(variant) }}</p>
                  <p
                    v-if="variant.rationale"
                    class="trp-variant-rationale"
                  >
                    <em>{{ $t('research.compose.rationaleLabel') }} : {{ variant.rationale }}</em>
                  </p>
                </div>
              </label>
            </li>
          </ul>

          <!-- Sources inline avec checkbox par source (US-B04.2) -->
          <details v-if="hasSources(topic)" class="trp-sources-inline" open>
            <summary>
              📎 {{ $t('research.compose.sourcesCount', { n: topic.key_signals.length }) }}
            </summary>
            <ul class="trp-sources-list">
              <li
                v-for="(src, si) in topic.key_signals"
                :key="`src-${ti}-${src.url || si}`"
                class="trp-source-row"
                :class="{ 'trp-source-row--unselected': src.url && !isSourceSelected(src.url) }"
              >
                <input
                  type="checkbox"
                  class="trp-source-checkbox"
                  :checked="!src.url || isSourceSelected(src.url)"
                  :disabled="!src.url"
                  :aria-label="src.source_name || src.url || ''"
                  @change="src.url && toggleSource(src.url)"
                />
                <img
                  v-if="src.url"
                  :src="faviconUrl(src.url)"
                  :alt="''"
                  class="trp-source-favicon"
                  loading="lazy"
                  width="16"
                  height="16"
                  @error="onFaviconError"
                />
                <span class="trp-source-name">{{ src.source_name || src.name || '—' }}</span>
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
                  :title="src.url"
                  @click.stop
                >{{ truncateUrl(src.url) }} ↗</a>
              </li>
            </ul>
          </details>
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

      <!-- Composition zone : preview éditable + insert -->
      <section class="trp-compose">
        <header class="trp-compose-head">
          <h5 class="trp-compose-title">
            🧪 {{ $t('research.compose.heading') }}
          </h5>
          <span class="trp-compose-count">
            {{ $t('research.compose.selectedCount', { count: selectedCount }) }}
            ·
            {{ $t('research.compose.sourcesSelectedCount', { n: selectedSourcesCount }) }}
          </span>
        </header>

        <p v-if="selectedCount === 0" class="trp-compose-empty">
          {{ $t('research.compose.empty') }}
        </p>

        <template v-else>
          <textarea
            v-model="composedPromptEdited"
            class="trp-compose-textarea"
            :rows="composedTextareaRows"
            :aria-label="$t('research.compose.textareaAriaLabel')"
            data-testid="composed-prompt"
          ></textarea>
          <div class="trp-compose-actions">
            <button
              type="button"
              class="trp-compose-reset"
              :disabled="composedPromptEdited === composedPromptAuto"
              @click="resetComposedToAuto"
            >
              {{ $t('research.compose.reset') }}
            </button>
            <button
              type="button"
              class="trp-compose-insert"
              :disabled="!composedPromptEdited.trim()"
              data-testid="compose-insert-btn"
              @click="insertComposed"
            >
              {{ $t('research.compose.insertWithSources', { n: selectedSourcesCount }) }} →
            </button>
          </div>
        </template>
      </section>
    </template>
  </div>
</template>

<script setup>
/**
 * US-B04 — TopicResearchPanel refondu (multi-select cross-topics).
 *
 * Workflow type NotebookLM :
 *   1. Le pipeline Kairos retourne N topics, chacun avec 1-3
 *      brief_variants.
 *   2. L'utilisateur visualise le TEXTE INTÉGRAL de chaque brief
 *      (200-300 chars) + sa rationale.
 *   3. Il coche les variants qu'il trouve pertinents (multi-select
 *      cross-topics — pas de limite « 1 par topic »).
 *   4. Une zone de composition assemble automatiquement les briefs
 *      sélectionnés en un prompt éditable.
 *   5. Bouton « Insérer dans la console » → émet `compose` event au
 *      parent (ConsoleView) qui remplace formData.simulationRequirement.
 *
 * Émet :
 *   - `compose` : { prompt, selections: [{topic, variant, framework_hint,
 *     signals_refs}] }
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { researchErrorKeyForCode } from '../api/research'

const { t } = useI18n()

const props = defineProps({
  sessionId: { type: String, default: null },
  status: {
    type: String,
    default: 'idle',
    validator: (v) =>
      ['idle', 'starting', 'running', 'completed', 'failed', 'timeout', 'error'].includes(v),
  },
  result: { type: Object, default: null },
  errorCode: { type: String, default: null },
  elapsedSeconds: { type: Number, default: 0 },
  cached: { type: Boolean, default: false },
})

const emit = defineEmits(['compose'])

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
  return topics.value.reduce((sum, topic) => {
    const sigs = Array.isArray(topic.key_signals) ? topic.key_signals.length : 0
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

// F3 mode dégradé synthesizer
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

// ─── Status line ────────────────────────────────────────────────────────────

const statusLine = computed(() => {
  switch (props.status) {
    case 'starting':
      return t('research.subStarting')
    case 'running':
      return t('research.subRunning', { elapsed: props.elapsedSeconds })
    case 'completed': {
      // US-B04.2 — status line dédiée mode dégradé : sinon afficher
      // "0 topics · 0 sources" alors qu'on a 30 signaux bruts à dispo
      // est trompeur (cf. session prod 2026-05-16).
      if (isDegradedSynthesizer.value) {
        return t('research.subDegradedCompleted', {
          count: scoredSignalsTop.value.length,
          reason: synthesizerFailureType.value || 'unknown',
        })
      }
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

const errorKey = computed(() => researchErrorKeyForCode(props.errorCode))

// ─── Helpers topics / variants ──────────────────────────────────────────────

const hasBriefVariants = (topic) =>
  Array.isArray(topic?.brief_variants) && topic.brief_variants.length > 0

const isDevilTopic = (topic) =>
  topic?.type === 'devil_advocate' || !!topic?.is_devil_advocate

const variantBriefText = (variant) => {
  if (!variant) return ''
  // Le contrat Kairos K05 expose `brief` (250-300 chars). On garde des
  // fallbacks défensifs au cas où un caller produit `summary` ou `label`.
  return variant.brief || variant.summary || variant.label || variant.title || ''
}

const frameworkLabel = (hint) => {
  if (!hint) return ''
  const norm = String(hint).toLowerCase()
  const known = ['crisis', 'market', 'policy', 'cerberus', 'decision']
  return known.includes(norm) ? t(`research.framework.${norm}`) : hint
}

const hasSources = (topic) =>
  Array.isArray(topic?.key_signals) && topic.key_signals.length > 0

// ─── Multi-select state ─────────────────────────────────────────────────────

// Set de clés "ti-vi" — un Set est immutable-friendly avec Vue 3 reactivity.
const selectedVariantKeys = ref(new Set())

// US-B04.2 — set d'URLs cochés. Partagé entre mode complet (sources de
// chaque topic) et mode dégradé (scored_signals_top). Permet une UX
// uniforme : « coche les sources que tu veux ingérer dans la simu ».
const selectedSourceUrls = ref(new Set())

const isSourceSelected = (url) => selectedSourceUrls.value.has(url)

const toggleSource = (url) => {
  if (!url) return
  const next = new Set(selectedSourceUrls.value)
  if (next.has(url)) next.delete(url)
  else next.add(url)
  selectedSourceUrls.value = next
}

const _allSourceUrls = computed(() => {
  if (isDegradedSynthesizer.value) {
    return scoredSignalsTop.value
      .map((s) => s.url)
      .filter(Boolean)
  }
  const out = []
  for (const topic of topics.value) {
    if (!Array.isArray(topic.key_signals)) continue
    for (const sig of topic.key_signals) {
      if (sig.url) out.push(sig.url)
    }
  }
  return out
})

const allSourcesSelected = computed(() => {
  const all = _allSourceUrls.value
  if (all.length === 0) return false
  return all.every((u) => selectedSourceUrls.value.has(u))
})

const toggleAllSources = () => {
  if (allSourcesSelected.value) {
    selectedSourceUrls.value = new Set()
  } else {
    selectedSourceUrls.value = new Set(_allSourceUrls.value)
  }
}

const selectedSignalsDetails = computed(() => {
  const urls = selectedSourceUrls.value
  if (urls.size === 0) return []
  const out = []
  if (isDegradedSynthesizer.value) {
    for (const sig of scoredSignalsTop.value) {
      if (sig.url && urls.has(sig.url)) out.push(sig)
    }
  } else {
    const seen = new Set()
    for (const topic of topics.value) {
      if (!Array.isArray(topic.key_signals)) continue
      for (const sig of topic.key_signals) {
        if (sig.url && urls.has(sig.url) && !seen.has(sig.url)) {
          seen.add(sig.url)
          out.push(sig)
        }
      }
    }
  }
  return out
})

const selectedSourcesCount = computed(() => selectedSignalsDetails.value.length)

const keyOf = (ti, vi) => `${ti}-${vi}`

const isVariantSelected = (ti, vi) => selectedVariantKeys.value.has(keyOf(ti, vi))

const toggleVariant = (ti, vi) => {
  const k = keyOf(ti, vi)
  const next = new Set(selectedVariantKeys.value)
  if (next.has(k)) next.delete(k)
  else next.add(k)
  selectedVariantKeys.value = next
}

const selectedCount = computed(() => selectedVariantKeys.value.size)

const selectedVariantsDetails = computed(() => {
  const out = []
  for (const k of selectedVariantKeys.value) {
    const idx = k.indexOf('-')
    if (idx < 0) continue
    const ti = Number(k.slice(0, idx))
    const vi = Number(k.slice(idx + 1))
    const topic = topics.value[ti]
    if (!topic) continue
    const variant = topic.brief_variants?.[vi]
    if (!variant) continue
    out.push({ ti, vi, topic, variant })
  }
  return out
})

// ─── Composition prompt ─────────────────────────────────────────────────────

/**
 * Compose le prompt. Deux modes :
 *   - Mode complet : briefs variants sélectionnés (existant US-B04)
 *   - Mode dégradé : signaux bruts sélectionnés (US-B04.2) — format
 *     Markdown listant title/source/url/excerpt pour donner du
 *     contexte au LLM en aval lors de la simulation.
 */
const composedPromptAuto = computed(() => {
  if (isDegradedSynthesizer.value) {
    const parts = selectedSignalsDetails.value.map((sig) => {
      const title = sig.title || sig.source || sig.url || '—'
      const meta = []
      if (sig.source) meta.push(`Source: ${sig.source}`)
      if (sig.lang) meta.push(`Lang: ${sig.lang}`)
      if (typeof sig.score === 'number') meta.push(`Score: ${sig.score}`)
      const metaLine = meta.length > 0 ? `\n${meta.join(' · ')}` : ''
      const excerpt = sig.excerpt ? `\n\n${sig.excerpt.trim()}` : ''
      const url = sig.url ? `\n\n${sig.url}` : ''
      return `## ${title}${metaLine}${url}${excerpt}`
    })
    return parts.join('\n\n---\n\n')
  }
  const parts = selectedVariantsDetails.value.map(({ topic, variant }) => {
    const fwk = variant.framework_hint ? ` [${frameworkLabel(variant.framework_hint)}]` : ''
    const head = `# ${topic.label}${fwk}`
    const body = variantBriefText(variant).trim()
    const rationale = variant.rationale ? `\n\n_Pourquoi cet angle : ${variant.rationale.trim()}_` : ''
    return `${head}\n\n${body}${rationale}`
  })
  return parts.join('\n\n---\n\n')
})

const composedPromptEdited = ref('')

// Quand l'auto-compose change (user coche/décoche), on PROPOSE la nouvelle
// version sans écraser une édition manuelle SAUF si l'edited est vide ou
// strictement identique à l'ancien auto. Cas typique : user édite le
// prompt après sélection, puis ajoute un brief → on append plutôt qu'on
// écrase.
let lastAuto = ''
watch(
  composedPromptAuto,
  (next) => {
    const prev = lastAuto
    lastAuto = next
    if (!composedPromptEdited.value || composedPromptEdited.value === prev) {
      composedPromptEdited.value = next
    }
    // Sinon : l'utilisateur a édité manuellement, on ne touche pas. Le
    // bouton « Régénérer auto » permet de revenir à la version computed.
  },
  { immediate: true },
)

const composedTextareaRows = computed(() => {
  const lines = composedPromptEdited.value.split('\n').length
  return Math.min(Math.max(lines + 1, 6), 20)
})

const resetComposedToAuto = () => {
  composedPromptEdited.value = composedPromptAuto.value
}

const insertComposed = () => {
  const prompt = composedPromptEdited.value.trim()
  if (!prompt) return
  // US-B04.2 — émet aussi `sources` (signaux cochés). Le parent
  // (ConsoleView) crée 1 urlDoc « Brief composé » + 1 urlDoc par source
  // → la simulation ingère vraiment les liens.
  emit('compose', {
    prompt,
    selections: selectedVariantsDetails.value.map(({ topic, variant }) => ({
      topic_label: topic.label,
      topic_summary: topic.summary,
      is_devil_advocate: isDevilTopic(topic),
      brief_variant: variant,
      framework_hint: variant.framework_hint || null,
      signals_refs: Array.isArray(variant.signals_refs) ? variant.signals_refs : [],
    })),
    sources: selectedSignalsDetails.value.map((sig) => ({
      url: sig.url || null,
      title: sig.title || null,
      source: sig.source || null,
      excerpt: sig.excerpt || null,
      lang: sig.lang || null,
      score: typeof sig.score === 'number' ? sig.score : null,
    })),
  })
}

// ─── Sources : favicon helper ──────────────────────────────────────────────

const faviconUrl = (url) => {
  try {
    const u = new URL(url)
    return `https://www.google.com/s2/favicons?domain=${u.hostname}&sz=32`
  } catch {
    return ''
  }
}

const onFaviconError = (e) => {
  // Cache l'image cassée plutôt que d'afficher un placeholder broken.
  e.target.style.visibility = 'hidden'
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

// ─── Reset quand nouveau résultat ───────────────────────────────────────────

watch(
  () => props.result,
  () => {
    selectedVariantKeys.value = new Set()
    composedPromptEdited.value = ''
    lastAuto = ''
    // US-B04.2 — option (c) : tout coché par défaut. L'user décoche
    // ce qu'il ne veut pas inclure dans la simulation.
    selectedSourceUrls.value = new Set(_allSourceUrls.value)
  },
  { immediate: true },
)
</script>

<style scoped>
/* ─── Warm Intelligence — TopicResearchPanel (US-B04 refonte) ─── */
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
  font-size: var(--wi-caption);
  font-weight: 500;
  margin-left: 4px;
}

.trp-cached-badge {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
}

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
  animation: trp-spin 0.8s linear infinite;
}

@keyframes trp-spin {
  to { transform: rotate(360deg); }
}

.trp-error {
  font-size: var(--wi-body-md);
  color: var(--wi-on-error-container, #8b1f1f);
  padding: var(--wi-space-sm);
  background: var(--wi-error-container, #fbe9e9);
  border-radius: var(--wi-radius-md);
  border: 1px solid var(--wi-error, #d8696b);
}

.trp-instructions {
  font-size: 13px;
  color: var(--wi-on-surface-variant);
  margin: 0 0 var(--wi-space-sm) 0;
  font-style: italic;
}

/* ─── Grid + cards ─── */
.trp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: var(--wi-space-sm);
  margin-bottom: var(--wi-space-md);
}

.trp-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-sm);
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: var(--wi-shadow-sm);
}

.trp-card--devil {
  border-color: var(--wi-primary-container);
  border-width: 2px;
  /* Pas de background coloré : on garde le surface dark theme et la
     bordure orange suffit à signaler le devil's advocate. */
  box-shadow: 0 0 0 1px rgb(255 133 81 / 25%) inset;
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
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  /* Badge vif orange + texte sombre — lisible sur dark theme. */
  background: var(--wi-primary-container);
  color: #1a1d27;
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
}

/* ─── Variants list (multi-select) ─── */
.trp-variants-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.trp-variant-item {
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface-container-low);
  transition: background var(--ms-transition-fast),
              border-color var(--ms-transition-fast);
}

.trp-variant-item:hover {
  border-color: var(--wi-primary-container);
}

.trp-variant-item--selected {
  /* Orange vif pour la bordure + tint visible sur dark theme. */
  border-color: var(--wi-primary-container);
  background: rgb(255 133 81 / 12%);
}

.trp-variant-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  padding: 10px;
  cursor: pointer;
  align-items: start;
}

.trp-variant-checkbox {
  margin-top: 2px;
  width: 18px;
  height: 18px;
  accent-color: var(--wi-on-primary-container);
  cursor: pointer;
}

.trp-variant-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.trp-variant-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.trp-variant-framework {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  /* Vif orange + texte dark theme bg pour lisibilité maximale. */
  background: var(--wi-primary-container);
  color: #1a1d27;
}

.trp-variant-charcount {
  font-size: 11px;
  color: var(--wi-outline, #8a90ad);
  font-family: var(--wi-font-mono, monospace);
}

.trp-variant-brief {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wi-on-surface);
}

.trp-variant-rationale {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: var(--wi-on-surface-variant);
}

/* ─── Sources inline (details/summary) ─── */
.trp-sources-inline {
  margin-top: 4px;
  font-size: 12px;
}

.trp-sources-inline summary {
  cursor: pointer;
  color: var(--wi-on-surface-variant);
  padding: 4px 0;
  user-select: none;
}

.trp-sources-inline summary:hover {
  color: var(--wi-primary-container);
}

.trp-sources-list {
  list-style: none;
  padding: 6px 0 0 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.trp-source-row {
  display: grid;
  grid-template-columns: 18px 16px 1fr auto;
  grid-template-areas:
    "cb fav name score"
    ". . url url";
  gap: 4px 8px;
  align-items: center;
  padding: 4px 6px;
  background: var(--wi-surface);
  border-radius: var(--wi-radius-sm, 6px);
  transition: opacity var(--ms-transition-fast);
}
.trp-source-row--unselected {
  opacity: 0.4;
}
.trp-source-checkbox {
  grid-area: cb;
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: var(--wi-primary-container);
  cursor: pointer;
}
.trp-source-checkbox:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.trp-source-favicon {
  grid-area: fav;
  flex-shrink: 0;
  /* Favicons Google sont conçus fond clair → padding blanc pour
     les rendre visibles sur dark theme. */
  background: white;
  border-radius: 2px;
  padding: 1px;
  box-sizing: content-box;
}

.trp-source-name {
  grid-area: name;
  font-weight: 600;
  color: var(--wi-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trp-source-score {
  grid-area: score;
  font-family: var(--wi-font-mono, monospace);
  color: var(--wi-primary-container);
  font-size: 11px;
  font-weight: 600;
}

.trp-source-url {
  grid-area: url;
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-size: 11px;
  word-break: break-all;
}

.trp-source-url:hover {
  text-decoration: underline;
  color: var(--wi-primary-container);
}

/* ─── Footer verdict + coverage ─── */
.trp-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: var(--wi-space-sm);
}

.trp-verdict {
  font-size: var(--wi-caption);
  font-weight: 700;
  text-transform: lowercase;
  padding: 3px 10px;
  border-radius: var(--wi-radius-pill);
}

/* Dark-theme aware : background tint + texte clair pour lisibilité. */
.trp-verdict--pass {
  background: rgb(81 200 120 / 18%);
  color: #6fdb96;
}

.trp-verdict--warn {
  background: rgb(255 196 81 / 18%);
  color: #ffc451;
}

.trp-verdict--deepen {
  background: rgb(255 133 81 / 18%);
  color: var(--wi-primary-container);
}

.trp-verdict--fail {
  background: rgb(255 100 100 / 18%);
  color: #ff8c8c;
}

.trp-coverage {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-style: italic;
}

/* ─── Composition zone ─── */
.trp-compose {
  border-top: 1px dashed var(--wi-outline-variant);
  padding-top: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.trp-compose-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.trp-compose-title {
  margin: 0;
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-on-surface);
}

.trp-compose-count {
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-mono, monospace);
}

.trp-compose-empty {
  font-size: 13px;
  color: var(--wi-on-surface-variant);
  font-style: italic;
  margin: 0;
  padding: var(--wi-space-sm);
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-md);
}

.trp-compose-textarea {
  width: 100%;
  font-family: var(--wi-font-mono, ui-monospace, monospace);
  font-size: 13px;
  line-height: 1.5;
  padding: 10px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  resize: vertical;
  min-height: 120px;
}

.trp-compose-textarea:focus {
  outline: none;
  border-color: var(--wi-on-primary-container);
  box-shadow: 0 0 0 3px var(--wi-primary-soft);
}

.trp-compose-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.trp-compose-reset,
.trp-compose-insert {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-caption);
  font-weight: 600;
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  transition: background var(--ms-transition-fast),
              color var(--ms-transition-fast);
}

.trp-compose-reset {
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
}

.trp-compose-reset:hover:not(:disabled) {
  border-color: var(--wi-on-surface);
  color: var(--wi-on-surface);
}

.trp-compose-reset:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.trp-compose-insert {
  /* CTA principal : orange vif + texte dark theme — bien contrasté. */
  background: var(--wi-primary-container);
  border: 1px solid var(--wi-primary-container);
  color: #1a1d27;
}

.trp-compose-insert:hover:not(:disabled) {
  filter: brightness(1.1);
  box-shadow: 0 2px 8px rgb(255 133 81 / 35%);
}

.trp-compose-insert:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ─── Mode dégradé (US-B04.2) ─── */
.trp-degraded-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  background: rgb(255 196 81 / 12%);
  border: 1px solid rgb(255 196 81 / 40%);
  border-radius: var(--wi-radius-md, 8px);
  margin-bottom: var(--wi-space-sm);
}
.trp-degraded-icon {
  font-size: 18px;
  flex-shrink: 0;
  color: #ffc451;
}
.trp-degraded-banner p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wi-on-surface);
}
.trp-degraded-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 10px;
}
.trp-degraded-heading {
  margin: 0;
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  color: var(--wi-on-surface);
}
.trp-degraded-toggle-all {
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  transition: border-color var(--ms-transition-fast), color var(--ms-transition-fast);
}
.trp-degraded-toggle-all:hover {
  border-color: var(--wi-primary-container);
  color: var(--wi-primary-container);
}
.trp-degraded-list {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--wi-space-md) 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 480px;
  overflow-y: auto;
}
.trp-degraded-item {
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md, 8px);
  transition: opacity var(--ms-transition-fast), border-color var(--ms-transition-fast);
}
.trp-degraded-item:hover {
  border-color: var(--wi-primary-container);
}
.trp-degraded-item--unselected {
  opacity: 0.45;
}
.trp-degraded-item-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  padding: 10px;
  cursor: pointer;
  align-items: start;
}
.trp-degraded-checkbox {
  margin-top: 3px;
  width: 16px;
  height: 16px;
  accent-color: var(--wi-primary-container);
  cursor: pointer;
  flex-shrink: 0;
}
.trp-degraded-item-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.trp-degraded-item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.trp-degraded-item-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--wi-on-surface);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
}
.trp-degraded-item-title:hover {
  color: var(--wi-primary-container);
  text-decoration: underline;
}
.trp-degraded-score {
  font-family: var(--wi-font-mono, monospace);
  font-size: 11px;
  color: var(--wi-primary-container);
  font-weight: 600;
  background: rgb(255 133 81 / 15%);
  padding: 1px 6px;
  border-radius: var(--wi-radius-pill);
}
.trp-degraded-item-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  flex-wrap: wrap;
}
.trp-degraded-source {
  font-weight: 600;
}
.trp-degraded-lang {
  background: var(--wi-surface);
  padding: 1px 6px;
  border-radius: var(--wi-radius-pill);
  text-transform: uppercase;
  font-size: 10px;
}
.trp-degraded-url {
  word-break: break-all;
  opacity: 0.7;
}
.trp-degraded-excerpt {
  margin: 4px 0 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--wi-on-surface-variant);
}
</style>
