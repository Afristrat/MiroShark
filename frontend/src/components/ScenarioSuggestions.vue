<template>
  <transition name="ss-fade">
    <div v-if="shouldShow" class="ss-wrap">
      <div class="ss-head">
        <span class="ss-label">
          <span class="ss-dot">◈</span> {{ $t('scenarios.label') }}
          <span class="ss-sub">{{ statusLine }}</span>
        </span>
        <button
          v-if="!loading"
          class="ss-close"
          type="button"
          :title="$t('scenarios.dismissTitle')"
          @click="dismiss"
        >×</button>
      </div>

      <!-- Framework selector (collapsible, shown only when not loading) -->
      <details class="ss-framework-picker" v-if="!loading">
        <summary class="ss-framework-toggle">{{ $t('scenarios.frameworkLabel') }} : {{ frameworkLabel }}</summary>
        <div class="ss-framework-options">
          <button
            v-for="fw in availableFrameworks"
            :key="fw.id"
            type="button"
            class="ss-fw-btn"
            :class="{ 'ss-fw-btn--active': selectedFramework === fw.id }"
            @click="setFramework(fw.id)"
          >{{ fw.label }}</button>
        </div>
      </details>

      <div v-if="loading" class="ss-loading">
        <span class="ss-spinner"></span>
        {{ $t('scenarios.loading') }}
      </div>

      <div v-else-if="suggestions.length > 0" class="ss-cards">
        <div
          v-for="(s, idx) in suggestions"
          :key="idx"
          class="ss-card"
          :class="cardClass(s.label)"
        >
          <div class="ss-card-head">
            <span class="ss-badge" :class="badgeClass(s.label)">{{ labelText(s.label) }}</span>
            <span class="ss-range">{{ $t('scenarios.initialYes', { min: s.expected_yes_range[0], max: s.expected_yes_range[1] }) }}</span>
          </div>
          <div class="ss-question">{{ s.question }}</div>
          <div v-if="s.rationale" class="ss-rationale">{{ s.rationale }}</div>
          <button
            class="ss-use"
            type="button"
            @click="useSuggestion(s, idx)"
          >{{ $t('scenarios.useThis') }}</button>
        </div>
      </div>

      <div v-else-if="error" class="ss-error">
        {{ error }}
      </div>
    </div>
  </transition>
</template>

<script setup>
/**
 * ScenarioSuggestions
 *
 * Eliminates the blank-page problem at simulation setup. Given a preview of
 * the user's uploaded document(s) or fetched URL(s), this component calls
 * `/api/simulation/suggest-scenarios`, debounces, and renders up to three
 * prediction-market-style scenario cards. Clicking "Use this →" emits a
 * `use` event with the chosen question so the parent can fill its textarea.
 *
 * Designed to be completely non-blocking: if the LLM is unavailable, the
 * backend times out, or the response is malformed, the panel simply does
 * not appear — the form below continues to work exactly as before.
 */

import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { suggestScenarios } from '../api/simulation'

const { t } = useI18n()

const props = defineProps({
  textPreview: { type: String, default: '' },
  simulationPrompt: { type: String, default: '' },
  minChars: { type: Number, default: 120 },
  debounceMs: { type: Number, default: 800 }
})

const emit = defineEmits(['use', 'dismiss'])

const loading = ref(false)
const suggestions = ref([])
const error = ref('')
const dismissed = ref(false)
const lastPreview = ref('')
const debounceTimer = ref(null)
// Monotonic request counter so a late response from an outdated preview
// can't overwrite suggestions for the current preview.
const requestSeq = ref(0)

// --- Cerberus framework selector ---
const detectedFramework = ref('cerberus')
const selectedFramework = ref('auto')

const availableFrameworks = computed(() => [
  { id: 'auto',     label: t('scenarios.frameworkAuto') },
  { id: 'cerberus', label: t('scenarios.frameworkCerberus') },
  { id: 'market',   label: t('scenarios.frameworkMarket') },
  { id: 'decision', label: t('scenarios.frameworkDecision') },
  { id: 'crisis',   label: t('scenarios.frameworkCrisis') },
  { id: 'policy',   label: t('scenarios.frameworkPolicy') },
])

const frameworkLabel = computed(() => {
  const fw = availableFrameworks.value.find(f => f.id === selectedFramework.value)
  return fw ? fw.label : t('scenarios.frameworkAuto')
})

const setFramework = (id) => {
  selectedFramework.value = id
  dismissed.value = false
  if (lastPreview.value) fetchSuggestions(lastPreview.value)
}

// --- Label mapping for all 5 Cerberus frameworks ---
const _LABEL_KEY_MAP = {
  'Bull':         'scenarios.bull',
  'Bear':         'scenarios.bear',
  'Neutral':      'scenarios.neutral',
  'Challenger':   'scenarios.challenger',
  'Defender':     'scenarios.defender',
  'Arbiter':      'scenarios.arbiter',
  'Optimist':     'scenarios.optimist',
  'Skeptic':      'scenarios.skeptic',
  'Pragmatist':   'scenarios.pragmatist',
  'Amplifier':    'scenarios.amplifier',
  'Attenuator':   'scenarios.attenuator',
  'Moderator':    'scenarios.moderator',
  'Progressive':  'scenarios.progressive',
  'Conservative': 'scenarios.conservative',
  'Technocrat':   'scenarios.technocrat',
}

// Visual style mapping: each label maps to bull/bear/neutral CSS theme
const _LABEL_STYLE = {
  'Bull':         'bull',
  'Bear':         'bear',
  'Neutral':      'neutral',
  'Challenger':   'challenger',
  'Defender':     'defender',
  'Arbiter':      'neutral',
  'Optimist':     'bull',
  'Skeptic':      'bear',
  'Pragmatist':   'neutral',
  'Amplifier':    'bear',
  'Attenuator':   'bull',
  'Moderator':    'neutral',
  'Progressive':  'bull',
  'Conservative': 'bear',
  'Technocrat':   'neutral',
}

// Localized label for the scenario badge — falls back to the raw label if
// the API returns something we don't have a key for.
const labelText = (label) => {
  const key = _LABEL_KEY_MAP[label]
  return key ? t(key) : label
}

const cardClass = (label) => ({
  [`ss-card-${_LABEL_STYLE[label] || 'neutral'}`]: true,
})

const badgeClass = (label) => ({
  [`ss-badge-${_LABEL_STYLE[label] || 'neutral'}`]: true,
})

const shouldShow = computed(() => {
  if (dismissed.value) return false
  if (loading.value) return true
  if (error.value) return true
  return suggestions.value.length > 0
})

const statusLine = computed(() => {
  if (loading.value) return t('scenarios.subGenerating')
  if (suggestions.value.length > 0) return t('scenarios.subPick')
  return ''
})

// Build a rich simulation_requirement when the backend did not provide one.
const _FRAMEWORK_CTX = {
  'Challenger':   'Simuler les forces adversariales et les acteurs qui challengent le statu quo. ',
  'Defender':     'Simuler les acteurs qui soutiennent le statu quo et leurs arguments. ',
  'Arbiter':      "Simuler un ensemble équilibré d'acteurs pour atteindre une synthèse réaliste. ",
  'Bull':         'Simuler les acteurs optimistes et les forces de marché haussières. ',
  'Bear':         'Simuler les acteurs pessimistes et les pressions baissières. ',
  'Neutral':      'Simuler un marché équilibré avec les bulls, bears et observateurs neutres. ',
  'Optimist':     'Simuler les early adopters, champions internes et clients enthousiastes. ',
  'Skeptic':      "Simuler les résistances, freins à l'adoption et critiques structurels. ",
  'Pragmatist':   'Simuler un échantillon réaliste de parties prenantes avec des attitudes mixtes. ',
  'Amplifier':    'Simuler les médias, réseaux sociaux et acteurs qui amplifient la crise. ',
  'Attenuator':   'Simuler les communicants, alliés et voix modératrices qui cherchent à contenir la crise. ',
  'Moderator':    "Simuler l'ensemble des parties prenantes pour projeter la trajectoire réelle de la crise. ",
  'Progressive':  'Simuler les promoteurs de la réforme, société civile et experts favorables. ',
  'Conservative': 'Simuler les opposants, lobbys et acteurs du statu quo institutionnel. ',
  'Technocrat':   'Simuler les experts techniques, hauts fonctionnaires et négociateurs de compromis. ',
}

const buildSimRequirement = (question, rationale, label) => {
  const ctx = _FRAMEWORK_CTX[label] || ''
  return `${ctx}${question}${rationale ? ' ' + rationale : ''}`
}

const useSuggestion = (s, idx) => {
  const enrichedRequirement = s.simulation_requirement
    || buildSimRequirement(s.question, s.rationale, s.label)
  emit('use', {
    question: s.question,
    label: s.label,
    index: idx,
    simulationRequirement: enrichedRequirement,
  })
}

const dismiss = () => {
  dismissed.value = true
  suggestions.value = []
  error.value = ''
  emit('dismiss')
}

const fetchSuggestions = async (preview) => {
  const mySeq = ++requestSeq.value
  loading.value = true
  error.value = ''
  try {
    const res = await suggestScenarios({
      text_preview: preview,
      simulation_prompt: props.simulationPrompt || '',
      framework: selectedFramework.value,
    })
    // Only overwrite suggestions if this is still the latest call —
    // otherwise a stale slow response could wipe a fresh result.
    if (mySeq !== requestSeq.value) return
    if (!res || res.success === false) {
      suggestions.value = []
      return
    }
    const data = res.data || {}
    suggestions.value = Array.isArray(data.suggestions) ? data.suggestions : []
    if (data.framework) detectedFramework.value = data.framework
  } catch (_) {
    if (mySeq !== requestSeq.value) return
    // Treat failures as "no suggestions" — the underlying form still works.
    suggestions.value = []
  } finally {
    // Always clear loading on response. A newer in-flight request (if any)
    // set loading=true again when it was scheduled, so this won't mask it.
    if (mySeq === requestSeq.value) {
      loading.value = false
    }
  }
}

const schedule = (preview) => {
  if (debounceTimer.value) {
    clearTimeout(debounceTimer.value)
    debounceTimer.value = null
  }
  // Light loading state the moment a fetch is queued so the spinner reflects
  // the user's intent immediately, not 800ms later.
  loading.value = true
  debounceTimer.value = setTimeout(() => {
    fetchSuggestions(preview)
  }, props.debounceMs)
}

watch(
  () => props.textPreview,
  (next) => {
    const trimmed = (next || '').trim()
    if (trimmed.length < props.minChars) {
      suggestions.value = []
      loading.value = false
      error.value = ''
      lastPreview.value = ''
      if (debounceTimer.value) {
        clearTimeout(debounceTimer.value)
        debounceTimer.value = null
      }
      return
    }
    if (trimmed === lastPreview.value) return
    lastPreview.value = trimmed
    // Only un-dismiss if the preview actually changed (new document).
    dismissed.value = false
    schedule(trimmed)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  if (debounceTimer.value) clearTimeout(debounceTimer.value)
})
</script>

<style scoped>
.ss-wrap {
  margin-top: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: rgba(255, 107, 26, 0.05);
  border: 2px dashed rgba(255, 107, 26, 0.35);
  border-radius: 4px;
  font-family: var(--font-mono);
  position: relative;
}

.ss-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.ss-label {
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--color-orange);
  display: flex;
  align-items: center;
  gap: 8px;
}

.ss-dot {
  color: var(--color-orange);
  font-size: 12px;
}

.ss-sub {
  color: rgba(10, 10, 10, 0.45);
  font-size: 10px;
  letter-spacing: 1px;
  font-weight: normal;
}

.ss-close {
  background: none;
  border: none;
  color: rgba(10, 10, 10, 0.4);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
  transition: var(--transition-fast);
}

.ss-close:hover { color: var(--color-orange); }

.ss-loading {
  font-size: 11px;
  color: rgba(10, 10, 10, 0.55);
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 2px;
}

.ss-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid rgba(255, 107, 26, 0.25);
  border-top-color: var(--color-orange);
  border-radius: 50%;
  display: inline-block;
  animation: ss-spin 0.8s linear infinite;
}

@keyframes ss-spin {
  to { transform: rotate(360deg); }
}

.ss-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.ss-card {
  background: var(--color-white);
  border: 2px solid rgba(10, 10, 10, 0.08);
  border-radius: 4px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: var(--transition-fast);
}

.ss-card:hover { border-color: var(--color-orange); }
.ss-card-bull { border-left: 4px solid var(--color-green); }
.ss-card-bear { border-left: 4px solid var(--color-red); }
.ss-card-neutral { border-left: 4px solid var(--color-amber); }

.ss-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ss-badge {
  font-size: 9px;
  letter-spacing: 2px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 2px;
  font-weight: 600;
  color: var(--color-white);
}

.ss-badge-bull { background: var(--color-green); }
.ss-badge-bear { background: var(--color-red); }
.ss-badge-neutral {
  background: var(--color-amber);
  color: var(--color-black);
}

/* Cerberus framework badge variants */
.ss-badge-challenger { background: rgba(239, 68, 68, 0.15); color: #dc2626; }
.ss-badge-defender   { background: rgba(59, 130, 246, 0.15); color: #2563eb; }

/* Cerberus framework card left-border variants */
.ss-card-challenger { border-left: 4px solid #dc2626; }
.ss-card-defender   { border-left: 4px solid #2563eb; }

.ss-range {
  font-size: 10px;
  color: rgba(10, 10, 10, 0.55);
  letter-spacing: 0.5px;
}

.ss-question {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--color-black);
  line-height: 1.35;
}

.ss-rationale {
  font-size: 10px;
  color: rgba(10, 10, 10, 0.55);
  line-height: 1.4;
  letter-spacing: 0.2px;
}

.ss-use {
  align-self: flex-start;
  margin-top: 4px;
  background: transparent;
  border: 1px solid var(--color-orange);
  color: var(--color-orange);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 2px;
  cursor: pointer;
  transition: var(--transition-fast);
}

.ss-use:hover {
  background: var(--color-orange);
  color: var(--color-white);
}

.ss-error {
  font-size: 11px;
  color: var(--color-red);
  letter-spacing: 0.5px;
}

/* Panel enter/leave */
.ss-fade-enter-active,
.ss-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.ss-fade-enter-from,
.ss-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Framework picker */
.ss-framework-picker {
  margin-bottom: var(--space-sm);
}

.ss-framework-toggle {
  font-size: 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: rgba(10, 10, 10, 0.5);
  cursor: pointer;
  user-select: none;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 4px;
}

.ss-framework-toggle::-webkit-details-marker { display: none; }
.ss-framework-toggle::marker { display: none; }

.ss-framework-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.ss-fw-btn {
  background: transparent;
  border: 1px solid rgba(10, 10, 10, 0.15);
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: rgba(10, 10, 10, 0.55);
  padding: 3px 8px;
  cursor: pointer;
  transition: var(--transition-fast);
}

.ss-fw-btn:hover {
  border-color: var(--color-orange);
  color: var(--color-orange);
}

.ss-fw-btn--active {
  border-color: var(--color-orange);
  color: var(--color-orange);
  background: rgba(255, 107, 26, 0.06);
}
</style>
