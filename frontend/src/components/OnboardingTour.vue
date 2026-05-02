<template>
  <!--
    OnboardingTour — US-060
    Tour guidé 4 étapes pour l'utilisateur solo (Strategy Analyst, MENA/Europe).
    Apparait au premier visit (flag localStorage: bassira_onboarding_done).
    Spotlight + tooltip ancré. 100 % piloté par tokens --wi-* / --ms-*.

    Étape 1 : .console-section (zone upload — la graine)
    Étape 2 : .input-wrapper / .code-input (textarea simulation_requirement)
    Étape 3 : .ss-wrap (ScenarioSuggestions)
    Étape 4 : .start-engine-btn (bouton Lancer)
  -->
  <Teleport to="body">
    <div
      v-if="visible"
      class="onb-root"
      role="dialog"
      aria-modal="true"
      :aria-label="$t('onboarding.ariaLabel')"
      @keydown.esc="skip"
      tabindex="-1"
      ref="rootEl"
    >
      <!-- Backdrop avec spotlight (clip-path) -->
      <div
        class="onb-backdrop"
        :style="backdropStyle"
        @click="skip"
        aria-hidden="true"
      ></div>

      <!-- Halo lumineux autour de la cible (purement visuel) -->
      <div
        v-if="targetRect"
        class="onb-halo"
        :style="haloStyle"
        aria-hidden="true"
      ></div>

      <!-- Beacon pulsant centré sur la cible -->
      <div
        v-if="targetRect"
        class="onb-beacon"
        :style="beaconStyle"
        aria-hidden="true"
      >
        <span class="onb-beacon-ring"></span>
        <span class="onb-beacon-dot"></span>
      </div>

      <!-- Tooltip ancré -->
      <div
        class="onb-tooltip"
        :style="tooltipStyle"
        :class="{ 'onb-tooltip--final': step === 4 }"
        role="document"
      >
        <!-- Progress bar -->
        <div class="onb-progress" aria-hidden="true">
          <div
            class="onb-progress-fill"
            :style="{ width: `${(step / 4) * 100}%` }"
          ></div>
        </div>

        <div class="onb-body">
          <div class="onb-counter">
            <span class="onb-counter-label">{{ $t('onboarding.stepLabel') }}</span>
            <span class="onb-counter-pill">{{ step }} / 4</span>
          </div>

          <h3 class="onb-title">{{ $t(`onboarding.step${step}.title`) }}</h3>
          <p class="onb-desc">
            {{ targetMissing ? $t(`onboarding.step${step}.bodyMissing`) : $t(`onboarding.step${step}.body`) }}
          </p>
          <p v-if="hintKey && !targetMissing" class="onb-hint">
            <span class="onb-hint-icon" aria-hidden="true">✦</span>
            {{ $t(hintKey) }}
          </p>

          <div class="onb-actions">
            <button
              type="button"
              class="onb-skip"
              @click="skip"
            >
              {{ $t('onboarding.skip') }}
            </button>
            <div class="onb-actions-right">
              <button
                v-if="step > 1"
                type="button"
                class="onb-btn onb-btn--ghost"
                @click="prev"
              >
                {{ $t('onboarding.prev') }}
              </button>
              <button
                v-if="step === 1"
                type="button"
                class="onb-btn onb-btn--mint"
                :disabled="exampleLoading"
                @click="loadExample"
              >
                <span v-if="!exampleLoading">{{ $t('onboarding.startExample') }}</span>
                <span v-else>{{ $t('onboarding.startExampleLoading') }}</span>
              </button>
              <button
                v-if="step < 4"
                type="button"
                class="onb-btn onb-btn--primary"
                @click="next"
              >
                {{ $t('onboarding.next') }}
              </button>
              <button
                v-else
                type="button"
                class="onb-btn onb-btn--primary"
                @click="finish"
              >
                {{ $t('onboarding.finish') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { getTemplate } from '../api/templates'
import { setPendingTemplate } from '../store/pendingUpload'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // Sélecteurs CSS pour chaque étape (avec fallbacks raisonnables).
  selectors: {
    type: Object,
    default: () => ({
      step1: '.upload-zone',
      step2: '.input-wrapper',
      step3: '.ss-wrap',
      step4: '.start-engine-btn',
    })
  },
  // ID du template d'exemple à charger via "Lancer un exemple".
  exampleTemplateId: { type: String, default: 'budget_loi_finances' },
  storageKey: { type: String, default: 'bassira_onboarding_done' },
})

const emit = defineEmits(['update:modelValue', 'finished', 'skipped'])

const router = useRouter()

const visible = ref(false)
const step = ref(1)
const targetRect = ref(null)
const targetMissing = ref(false)  // true quand le sélecteur est défini mais l'élément n'existe pas dans le DOM
const exampleLoading = ref(false)
const rootEl = ref(null)

// Synchroniser visibilité avec v-model parent
watch(() => props.modelValue, (val) => { visible.value = val }, { immediate: true })
watch(visible, (v) => emit('update:modelValue', v))

// Hint key existe seulement pour les 4 étapes (champ optionnel)
const hintKey = computed(() => `onboarding.step${step.value}.hint`)

const currentSelector = computed(() => {
  const map = props.selectors
  return map[`step${step.value}`] || null
})

// Polling RAF jusqu'à ce que le rect de l'élément soit stable sur 2 frames
// consécutives — détection fiable de la fin du scroll smooth, sans timeout
// magique. Plafond à ~30 frames (~500ms à 60fps) pour ne jamais bloquer.
const _waitForStableRect = (el) => new Promise((resolve) => {
  let prev = el.getBoundingClientRect()
  let stableCount = 0
  let frames = 0
  const tick = () => {
    frames += 1
    const cur = el.getBoundingClientRect()
    const dx = Math.abs(cur.top - prev.top) + Math.abs(cur.left - prev.left)
    if (dx < 0.5) {
      stableCount += 1
    } else {
      stableCount = 0
    }
    prev = cur
    if (stableCount >= 2 || frames >= 30) {
      resolve(cur)
    } else {
      requestAnimationFrame(tick)
    }
  }
  requestAnimationFrame(tick)
})

// Calcul du rect de la cible — mis à jour à chaque step + resize
const measureTarget = async () => {
  await nextTick()
  const sel = currentSelector.value
  if (!sel) {
    targetRect.value = null
    targetMissing.value = false
    return
  }
  const el = document.querySelector(sel)
  if (!el) {
    // Cible définie mais absente du DOM (ex. .ss-wrap conditionné par v-if).
    // On bascule en mode "centré + message contextuel" via targetMissing.
    targetRect.value = null
    targetMissing.value = true
    return
  }
  targetMissing.value = false
  // Scroll smooth pour amener la cible en vue avant mesure
  try {
    el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  } catch (_) {
    el.scrollIntoView()
  }
  // Attendre que le rect soit stable (fin du scroll smooth) avant de mesurer
  const r = await _waitForStableRect(el)
  targetRect.value = {
    top: r.top,
    left: r.left,
    width: r.width,
    height: r.height,
    bottom: r.bottom,
    right: r.right,
  }
}

// Spotlight via clip-path — on découpe un rect arrondi dans le backdrop
const backdropStyle = computed(() => {
  if (!targetRect.value) {
    return { background: 'rgba(36, 25, 21, 0.62)' }
  }
  const padding = 12
  const r = targetRect.value
  const t = Math.max(0, r.top - padding)
  const l = Math.max(0, r.left - padding)
  const b = Math.min(window.innerHeight, r.bottom + padding)
  const right = Math.min(window.innerWidth, r.right + padding)
  // clip-path en polygon avec un trou rectangulaire (4 coins externes + 4 internes)
  const clip = `polygon(
    0 0,
    100% 0,
    100% 100%,
    0 100%,
    0 ${t}px,
    ${l}px ${t}px,
    ${l}px ${b}px,
    ${right}px ${b}px,
    ${right}px ${t}px,
    0 ${t}px
  )`
  return {
    background: 'rgba(36, 25, 21, 0.62)',
    clipPath: clip,
    WebkitClipPath: clip,
  }
})

const haloStyle = computed(() => {
  if (!targetRect.value) return { display: 'none' }
  const padding = 8
  const r = targetRect.value
  return {
    top: `${r.top - padding}px`,
    left: `${r.left - padding}px`,
    width: `${r.width + padding * 2}px`,
    height: `${r.height + padding * 2}px`,
  }
})

const beaconStyle = computed(() => {
  if (!targetRect.value) return { display: 'none' }
  const r = targetRect.value
  // Beacon en haut-gauche du rect cible
  return {
    top: `${r.top - 12}px`,
    left: `${r.left - 12}px`,
  }
})

// Calcul de la position du tooltip — idéalement à droite, sinon en bas
const tooltipStyle = computed(() => {
  const tooltipW = 380
  const tooltipH = 240 // estimation, peu importe pour le calcul
  const margin = 16

  // Étape 4 = celebration centrée
  if (!targetRect.value || step.value === 4) {
    return {
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
    }
  }

  const r = targetRect.value
  const vw = window.innerWidth
  const vh = window.innerHeight

  // Espace disponible à droite, en bas, à gauche
  const rightSpace = vw - r.right - margin
  const bottomSpace = vh - r.bottom - margin
  const leftSpace = r.left - margin

  let top, left
  if (rightSpace >= tooltipW + 16) {
    // À droite
    left = r.right + margin
    top = Math.max(margin, Math.min(r.top, vh - tooltipH - margin))
  } else if (bottomSpace >= tooltipH + 16) {
    // En bas
    top = r.bottom + margin
    left = Math.max(margin, Math.min(r.left, vw - tooltipW - margin))
  } else if (leftSpace >= tooltipW + 16) {
    // À gauche
    left = r.left - tooltipW - margin
    top = Math.max(margin, Math.min(r.top, vh - tooltipH - margin))
  } else {
    // En haut (fallback)
    top = Math.max(margin, r.top - tooltipH - margin)
    left = Math.max(margin, Math.min(r.left, vw - tooltipW - margin))
  }
  return {
    top: `${top}px`,
    left: `${left}px`,
    width: `${tooltipW}px`,
  }
})

// Navigation
const next = () => {
  if (step.value < 4) {
    step.value += 1
    measureTarget()
  } else {
    finish()
  }
}
const prev = () => {
  if (step.value > 1) {
    step.value -= 1
    measureTarget()
  }
}
const skip = () => {
  markDone()
  visible.value = false
  emit('skipped')
}
const finish = () => {
  markDone()
  visible.value = false
  emit('finished')
}
const markDone = () => {
  try {
    localStorage.setItem(props.storageKey, '1')
  } catch (_) {
    // localStorage indisponible (Safari private mode) → ignore silencieusement
  }
}

// "Lancer un exemple" — pré-charge le template budget_loi_finances et navigue
const loadExample = async () => {
  if (exampleLoading.value) return
  exampleLoading.value = true
  try {
    const res = await getTemplate(props.exampleTemplateId)
    if (res?.success && res.data) {
      setPendingTemplate(
        res.data.simulation_requirement,
        res.data.seed_document,
        res.data.name
      )
      markDone()
      visible.value = false
      router.push({ name: 'Process', params: { projectId: 'new' } })
      return
    }
    // Échec backend → on n'avance pas, on log silencieusement
    // (bouton "Suivant" reste accessible)
    console.warn('[OnboardingTour] template fetch failed', res?.error)
  } catch (err) {
    console.warn('[OnboardingTour] template fetch error', err?.message)
  } finally {
    exampleLoading.value = false
  }
}

// Reposition au resize / scroll (debounced via rAF)
let rafId = null
const onReposition = () => {
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = null
    if (!visible.value) return
    const sel = currentSelector.value
    if (!sel) return
    const el = document.querySelector(sel)
    if (!el) return
    const r = el.getBoundingClientRect()
    targetRect.value = {
      top: r.top, left: r.left, width: r.width, height: r.height,
      bottom: r.bottom, right: r.right,
    }
  })
}

onMounted(() => {
  if (visible.value) {
    measureTarget()
    nextTick(() => rootEl.value?.focus())
  }
  window.addEventListener('resize', onReposition, { passive: true })
  window.addEventListener('scroll', onReposition, { passive: true, capture: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onReposition)
  window.removeEventListener('scroll', onReposition, { capture: true })
  if (rafId) cancelAnimationFrame(rafId)
})

// Quand le tour devient visible, mesurer
watch(visible, (v) => {
  if (v) {
    step.value = 1
    nextTick(() => {
      measureTarget()
      rootEl.value?.focus()
    })
  }
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   OnboardingTour — Warm Intelligence palette (--wi-*)
   ═══════════════════════════════════════════════════════════ */

.onb-root {
  position: fixed;
  inset: 0;
  z-index: 1500;
  pointer-events: none;
  outline: none;
}

.onb-backdrop {
  position: absolute;
  inset: 0;
  pointer-events: auto;
  transition: clip-path var(--ms-transition-slow, 300ms ease);
}

.onb-halo {
  position: absolute;
  border-radius: var(--wi-radius-card, 24px);
  border: 2px solid var(--wi-primary-container, var(--ms-orange));
  box-shadow:
    0 0 0 4px rgba(255, 133, 81, 0.18),
    var(--wi-shadow-lg, var(--ms-shadow-lg));
  pointer-events: none;
  transition:
    top var(--ms-transition, 200ms ease),
    left var(--ms-transition, 200ms ease),
    width var(--ms-transition, 200ms ease),
    height var(--ms-transition, 200ms ease);
}

/* Beacon pulsant — type Material onboarding */
.onb-beacon {
  position: absolute;
  width: 24px;
  height: 24px;
  pointer-events: none;
}
.onb-beacon-ring,
.onb-beacon-dot {
  position: absolute;
  inset: 0;
  border-radius: 50%;
}
.onb-beacon-ring {
  background: var(--wi-primary-container, var(--ms-orange));
  opacity: 0.55;
  animation: onb-ping 1.8s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}
.onb-beacon-dot {
  background: var(--wi-primary, var(--ms-orange-strong, #a13f0f));
  border: 2px solid var(--wi-surface, #fff);
  width: 18px;
  height: 18px;
  margin: 3px;
  box-shadow: var(--wi-shadow-sm);
}
@keyframes onb-ping {
  0%   { transform: scale(0.85); opacity: 0.7; }
  70%  { transform: scale(1.6); opacity: 0; }
  100% { transform: scale(1.6); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .onb-beacon-ring { animation: none; }
}

/* ── Tooltip ── */
.onb-tooltip {
  position: absolute;
  pointer-events: auto;
  background: var(--wi-surface, var(--ms-bg-elevated, #fff));
  color: var(--wi-on-surface, var(--ms-text));
  border: 1px solid var(--wi-outline-variant, var(--ms-border));
  border-radius: var(--wi-radius-card, 24px);
  box-shadow: var(--wi-shadow-lg, var(--ms-shadow-lg));
  overflow: hidden;
  font-family: var(--wi-font-body, var(--ms-font-body));
  transition:
    top var(--ms-transition-slow, 300ms ease),
    left var(--ms-transition-slow, 300ms ease);
}

.onb-tooltip--final {
  width: min(440px, calc(100vw - 32px)) !important;
  text-align: center;
  background: linear-gradient(
    180deg,
    var(--wi-surface-container-low, #fff1ec) 0%,
    var(--wi-surface, #fff) 100%
  );
}

.onb-progress {
  height: 3px;
  background: var(--wi-surface-container-highest, var(--ms-bg-muted));
}
.onb-progress-fill {
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--wi-primary-container, var(--ms-orange)) 0%,
    var(--wi-primary, #a13f0f) 100%
  );
  transition: width var(--ms-transition, 200ms ease);
}

.onb-body {
  padding: 22px 24px 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.onb-counter {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--wi-font-body, var(--ms-font-body));
  font-size: var(--wi-caption, 12px);
  font-weight: 500;
}
.onb-counter-label {
  color: var(--wi-on-surface-variant, var(--ms-text-muted));
  text-transform: uppercase;
  letter-spacing: 0.12em;
}
.onb-counter-pill {
  background: var(--wi-secondary-container, #98f2be);
  color: var(--wi-on-secondary-container, #067148);
  padding: 2px 10px;
  border-radius: var(--wi-radius-pill, 9999px);
  font-weight: 700;
  font-feature-settings: 'tnum';
}

.onb-title {
  font-family: var(--wi-font-heading, var(--ms-font-display));
  font-size: var(--wi-h3-size, 24px);
  font-weight: var(--wi-h3-weight, 500);
  line-height: var(--wi-h3-leading, 1.3);
  margin: 0;
  color: var(--wi-on-surface, var(--ms-text));
}

.onb-desc {
  font-size: var(--wi-body-md, 16px);
  line-height: var(--wi-body-md-leading, 1.6);
  color: var(--wi-on-surface-variant, var(--ms-text-muted));
  margin: 0;
}

.onb-hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--wi-on-secondary-container, #067148);
  background: var(--wi-secondary-container, rgba(0, 109, 68, 0.08));
  padding: 10px 12px;
  border-radius: var(--wi-radius-interactive, 12px);
  margin: 0;
}
.onb-hint-icon {
  color: var(--wi-secondary, #006d44);
  font-size: 14px;
  flex-shrink: 0;
  line-height: 1.5;
}

.onb-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
  border-top: 1px solid var(--wi-outline-variant, var(--ms-border));
  padding-top: 14px;
}
.onb-actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.onb-skip {
  background: transparent;
  border: none;
  color: var(--wi-on-surface-variant, var(--ms-text-muted));
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  padding: 6px 4px;
  text-decoration: underline;
  text-decoration-color: var(--wi-outline, var(--ms-border-strong));
  text-underline-offset: 3px;
  transition: color var(--ms-transition-fast, 150ms ease);
}
.onb-skip:hover {
  color: var(--wi-on-surface, var(--ms-text));
}

.onb-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--wi-radius-pill, 9999px);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--ms-transition-fast, 150ms ease);
  white-space: nowrap;
}
.onb-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.onb-btn--primary {
  background: var(--wi-primary-container, var(--ms-orange));
  color: var(--wi-on-primary, #fff);
  box-shadow: var(--ms-shadow-orange, 0 6px 18px rgba(255, 133, 81, 0.28));
}
.onb-btn--primary:hover:not(:disabled) {
  background: var(--wi-primary, #a13f0f);
}

.onb-btn--ghost {
  background: transparent;
  color: var(--wi-on-surface, var(--ms-text));
  border-color: var(--wi-outline, var(--ms-border-strong));
}
.onb-btn--ghost:hover:not(:disabled) {
  background: var(--wi-surface-container-low, var(--ms-bg-muted));
}

.onb-btn--mint {
  background: var(--wi-secondary-container, #98f2be);
  color: var(--wi-on-secondary-container, #067148);
  border-color: var(--wi-secondary, #006d44);
}
.onb-btn--mint:hover:not(:disabled) {
  background: var(--wi-secondary, #006d44);
  color: var(--wi-on-secondary, #fff);
}

/* ── RTL : on inverse l'alignement actions-right ── */
:global([dir="rtl"]) .onb-actions-right {
  justify-content: flex-start;
}

/* ── Responsive ── */
@media (max-width: 640px) {
  .onb-tooltip {
    width: calc(100vw - 24px) !important;
    left: 12px !important;
    right: 12px;
  }
  .onb-body { padding: 18px 18px 14px 18px; }
  .onb-actions { flex-direction: column; align-items: stretch; gap: 12px; }
  .onb-actions-right { justify-content: center; }
}
</style>
