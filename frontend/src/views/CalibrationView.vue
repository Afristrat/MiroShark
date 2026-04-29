<template>
  <div class="cal-page">
    <!-- Top bar : retour vers l'accueil. LanguageSwitcher est mounté
         globalement par App.vue en widget flottant top-right. -->
    <header class="cal-topbar">
      <router-link to="/" class="cal-back" :title="$t('calibration.nav.backTitle')">
        <span class="cal-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
    </header>

    <main class="cal-main">
      <!-- ───────────── Hero band ───────────── -->
      <section class="cal-hero" :ref="el => setSectionRef(el, 0)">
        <span class="cal-eyebrow">{{ $t('calibration.eyebrow') }}</span>
        <h1 class="cal-headline">{{ $t('calibration.hero.headline') }}</h1>
        <p class="cal-sub">{{ $t('calibration.hero.sub') }}</p>

        <div class="cal-big-row">
          <!-- Skeleton placeholder pendant le fetch initial -->
          <template v-if="loading && data === null">
            <div class="cal-big-skeleton-wrap">
              <div class="ms-skeleton cal-big-skeleton-num"></div>
              <div class="ms-skeleton cal-big-skeleton-chip"></div>
            </div>
          </template>

          <!-- Etat avec donnée -->
          <template v-else-if="data && data.brier !== null && data.brier !== undefined">
            <div class="cal-big-num ms-mono" :title="$t('calibration.hero.brierTitle')">
              {{ formatBrier(data.brier) }}
            </div>
            <div v-if="deltaChip" class="cal-delta-chip" :class="deltaChip.cls">
              <span class="cal-delta-arrow" aria-hidden="true">{{ deltaChip.arrow }}</span>
              <span class="ms-mono">{{ deltaChip.text }}</span>
            </div>
            <div class="cal-big-caption">
              <span class="cal-big-label">{{ $t('calibration.hero.label') }}</span>
              <span class="cal-big-help">{{ $t('calibration.hero.help') }}</span>
            </div>
          </template>

          <!-- Aucun verdict encore -->
          <template v-else-if="data">
            <div class="cal-big-num cal-big-num--empty ms-mono">—</div>
            <div class="cal-big-caption">
              <span class="cal-big-label">{{ $t('calibration.hero.label') }}</span>
              <span class="cal-big-help">{{ $t('calibration.empty.helper') }}</span>
            </div>
          </template>
        </div>
      </section>

      <!-- ───────────── Erreur réseau ───────────── -->
      <section v-if="error && !loading" class="cal-error" role="alert">
        <div class="cal-error-icon" aria-hidden="true">⚠</div>
        <div class="cal-error-body">
          <div class="cal-error-title">{{ $t('calibration.error.title') }}</div>
          <div class="cal-error-msg">{{ error }}</div>
        </div>
        <button class="ms-btn ms-btn-ghost ms-btn--sm" @click="refresh">
          {{ $t('common.retry') }}
        </button>
      </section>

      <!-- ───────────── Stats strip (4 cards) ───────────── -->
      <section class="cal-stats" :ref="el => setSectionRef(el, 1)" aria-label="Calibration stats">
        <!-- Total verified -->
        <article class="ms-card cal-stat-card">
          <div class="cal-stat-num ms-mono">
            <span v-if="loading && data === null" class="ms-skeleton cal-num-skel" aria-hidden="true"></span>
            <template v-else>{{ data ? data.n : 0 }}</template>
          </div>
          <div class="cal-stat-row">
            <span class="cal-stat-label">{{ $t('calibration.stats.total') }}</span>
          </div>
        </article>

        <!-- Called it -->
        <article class="ms-card cal-stat-card">
          <div class="cal-stat-num ms-mono">
            <span v-if="loading && data === null" class="ms-skeleton cal-num-skel" aria-hidden="true"></span>
            <template v-else>
              {{ outcomeCounts.called_it }}
              <span class="cal-stat-pct">{{ formatPct(outcomeCounts.called_it, data ? data.n : 0) }}</span>
            </template>
          </div>
          <div class="cal-stat-row">
            <span class="cal-stat-label">{{ $t('calibration.stats.calledIt') }}</span>
            <span class="ms-badge ms-badge-success">{{ $t('calibration.badges.success') }}</span>
          </div>
        </article>

        <!-- Partial -->
        <article class="ms-card cal-stat-card">
          <div class="cal-stat-num ms-mono">
            <span v-if="loading && data === null" class="ms-skeleton cal-num-skel" aria-hidden="true"></span>
            <template v-else>
              {{ outcomeCounts.partial }}
              <span class="cal-stat-pct">{{ formatPct(outcomeCounts.partial, data ? data.n : 0) }}</span>
            </template>
          </div>
          <div class="cal-stat-row">
            <span class="cal-stat-label">{{ $t('calibration.stats.partial') }}</span>
            <span class="ms-badge ms-badge-warning">{{ $t('calibration.badges.partial') }}</span>
          </div>
        </article>

        <!-- Wrong -->
        <article class="ms-card cal-stat-card">
          <div class="cal-stat-num ms-mono">
            <span v-if="loading && data === null" class="ms-skeleton cal-num-skel" aria-hidden="true"></span>
            <template v-else>
              {{ outcomeCounts.wrong }}
              <span class="cal-stat-pct">{{ formatPct(outcomeCounts.wrong, data ? data.n : 0) }}</span>
            </template>
          </div>
          <div class="cal-stat-row">
            <span class="cal-stat-label">{{ $t('calibration.stats.wrong') }}</span>
            <span class="ms-badge ms-badge-danger">{{ $t('calibration.badges.wrong') }}</span>
          </div>
        </article>
      </section>

      <!-- ───────────── Plot + filtres ───────────── -->
      <section class="cal-plot-grid" :ref="el => setSectionRef(el, 2)">
        <article class="ms-card cal-plot-card">
          <header class="cal-plot-head">
            <h2 class="cal-plot-title">{{ $t('calibration.plot.title') }}</h2>
            <p class="cal-plot-explainer">{{ $t('calibration.plot.explainer') }}</p>
          </header>

          <!-- Skeleton -->
          <div v-if="loading && data === null" class="cal-plot-skeleton">
            <div class="ms-skeleton cal-plot-skel-svg"></div>
          </div>

          <!-- État vide -->
          <div v-else-if="data && data.n === 0" class="cal-plot-empty">
            <div class="cal-plot-empty-icon" aria-hidden="true">◇</div>
            <div class="cal-plot-empty-title">{{ $t('calibration.empty.title') }}</div>
            <div class="cal-plot-empty-msg">{{ $t('calibration.empty.message') }}</div>
          </div>

          <!-- SVG scatter plot -->
          <div v-else-if="data" class="cal-plot-wrap" ref="plotWrap">
            <svg
              :viewBox="`0 0 ${plotW} ${plotH}`"
              class="cal-plot-svg"
              role="img"
              :aria-label="$t('calibration.plot.title')"
              @mousemove="onPlotMouseMove"
              @mouseleave="hideTooltip"
            >
              <!-- Grid -->
              <g class="cal-plot-grid-lines">
                <line
                  v-for="g in gridLines"
                  :key="`gx${g}`"
                  :x1="xScale(g)" :y1="padTop"
                  :x2="xScale(g)" :y2="padTop + innerH"
                />
                <line
                  v-for="g in gridLines"
                  :key="`gy${g}`"
                  :x1="padInline" :y1="yScale(g)"
                  :x2="padInline + innerW" :y2="yScale(g)"
                />
              </g>

              <!-- Axes -->
              <line
                class="cal-plot-axis"
                :x1="padInline" :y1="padTop + innerH"
                :x2="padInline + innerW" :y2="padTop + innerH"
              />
              <line
                class="cal-plot-axis"
                :x1="padInline" :y1="padTop"
                :x2="padInline" :y2="padTop + innerH"
              />

              <!-- Diagonale parfaite -->
              <line
                class="cal-plot-diagonal"
                :x1="xScale(0)" :y1="yScale(0)"
                :x2="xScale(1)" :y2="yScale(1)"
              />

              <!-- Tick labels -->
              <g class="cal-plot-ticks">
                <text
                  v-for="t in tickValues" :key="`tx${t}`"
                  :x="xScale(t)" :y="padTop + innerH + 18"
                  class="cal-tick cal-tick-x"
                >{{ t.toFixed(1) }}</text>
                <text
                  v-for="t in tickValues" :key="`ty${t}`"
                  :x="padInline - 8" :y="yScale(t) + 4"
                  class="cal-tick cal-tick-y"
                >{{ t.toFixed(1) }}</text>
              </g>

              <!-- Axis titles -->
              <text
                class="cal-axis-title"
                :x="padInline + innerW / 2"
                :y="plotH - 6"
                text-anchor="middle"
              >{{ $t('calibration.plot.xAxis') }}</text>
              <text
                class="cal-axis-title"
                :transform="`translate(14, ${padTop + innerH / 2}) rotate(-90)`"
                text-anchor="middle"
              >{{ $t('calibration.plot.yAxis') }}</text>

              <!-- Bullet points -->
              <g class="cal-plot-points">
                <circle
                  v-for="(b, idx) in plotPoints"
                  :key="`pt${idx}`"
                  :cx="xScale(b.predicted)"
                  :cy="yScale(b.observed)"
                  :r="bucketRadius(b.n)"
                  class="cal-plot-dot"
                  :data-bucket="b.bucket"
                  @mouseenter="showTooltip($event, b)"
                />
              </g>
            </svg>

            <!-- Tooltip -->
            <div
              v-if="tooltip.visible"
              class="cal-tooltip"
              :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
              role="tooltip"
            >
              <div class="cal-tooltip-row">
                <span class="cal-tooltip-key">{{ $t('calibration.tooltip.predicted') }}</span>
                <span class="cal-tooltip-val ms-mono">{{ tooltip.predicted }}</span>
              </div>
              <div class="cal-tooltip-row">
                <span class="cal-tooltip-key">{{ $t('calibration.tooltip.observed') }}</span>
                <span class="cal-tooltip-val ms-mono">{{ tooltip.observed }}</span>
              </div>
              <div class="cal-tooltip-row">
                <span class="cal-tooltip-key">{{ $t('calibration.tooltip.n') }}</span>
                <span class="cal-tooltip-val ms-mono">{{ tooltip.n }}</span>
              </div>
            </div>
          </div>
        </article>

        <!-- Filtres -->
        <aside class="ms-card cal-filters-card" aria-label="Filters">
          <h3 class="cal-filters-title">{{ $t('calibration.filters.title') }}</h3>

          <label class="cal-field">
            <span class="cal-field-label">{{ $t('calibration.filters.template') }}</span>
            <select v-model="filters.template" class="ms-select" :disabled="loading">
              <option value="">{{ $t('calibration.filters.allTemplates') }}</option>
              <option v-for="tpl in availableTemplates" :key="tpl" :value="tpl">{{ tpl }}</option>
            </select>
          </label>

          <label class="cal-field">
            <span class="cal-field-label">{{ $t('calibration.filters.from') }}</span>
            <input v-model="filters.from" type="date" class="ms-input" :disabled="loading" />
          </label>

          <label class="cal-field">
            <span class="cal-field-label">{{ $t('calibration.filters.to') }}</span>
            <input v-model="filters.to" type="date" class="ms-input" :disabled="loading" />
          </label>

          <p class="cal-filters-note">{{ $t('calibration.filters.publicOnly') }}</p>

          <div class="cal-filters-actions">
            <button
              class="ms-btn ms-btn-secondary ms-btn--sm"
              @click="applyFilters"
              :disabled="loading"
            >
              {{ $t('calibration.filters.apply') }}
            </button>
            <button
              class="ms-btn ms-btn-ghost ms-btn--sm"
              @click="resetFilters"
              :disabled="loading"
            >
              {{ $t('calibration.filters.reset') }}
            </button>
          </div>
        </aside>
      </section>

      <!-- ───────────── Methodology + CTA ───────────── -->
      <section class="cal-bottom-grid" :ref="el => setSectionRef(el, 3)">
        <article class="cal-method">
          <h2 class="cal-method-title">{{ $t('calibration.methodology.title') }}</h2>
          <p class="cal-method-p">{{ $t('calibration.methodology.p1') }}</p>
          <p class="cal-method-p">{{ $t('calibration.methodology.p2') }}</p>
          <p class="cal-method-p">{{ $t('calibration.methodology.p3') }}</p>
        </article>

        <aside class="ms-card cal-cta-card">
          <h2 class="cal-cta-title">{{ $t('calibration.cta.title') }}</h2>
          <p class="cal-cta-p">{{ $t('calibration.cta.body') }}</p>
          <router-link to="/devis" class="ms-btn cal-cta-btn">
            {{ $t('calibration.cta.button') }}
            <span class="cal-cta-arrow" aria-hidden="true">→</span>
          </router-link>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
/**
 * /calibration — page publique qui sert d'argument commercial : Brier
 * score agrégé sur les sims publiques marquées comme « verified » avec
 * un calibration plot D3-style (predicted vs observed) sur 10 buckets.
 *
 * Source de vérité backend : GET /api/calibration/brier-score.
 * Le shape est plat (PAS de wrapper data.outcomes) — on lit directement
 * les clés top-level n_called_it / n_partial / n_wrong / accuracy /
 * brier / calibration_plot. Le brief mentionnait un shape imbriqué qui
 * n'existe pas en l'état du backend ; on s'aligne sur le shape réel.
 *
 * Le delta_vs_previous_month n'est pas exposé par le backend
 * actuellement, donc le chip de variation est masqué tant que la
 * réponse ne le porte pas. Si le backend l'ajoute plus tard, le code
 * le détecte et l'affiche automatiquement.
 */
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api/index.js'
import { useScrollFadeIn } from '../composables/useScrollFadeIn'

// ─── Refs DOM pour le fade-in à mesure que l'utilisateur scrolle ───────────
const sectionRefs = ref([])
const setSectionRef = (el, idx) => {
  if (el) sectionRefs.value[idx] = el
}
useScrollFadeIn(sectionRefs)

const plotWrap = ref(null)

// ─── State ──────────────────────────────────────────────────────────────────
const data = ref(null)            // payload backend brut
const loading = ref(false)
const error = ref('')

const filters = reactive({
  template: '',
  from: '',
  to: '',
})

// ─── API ────────────────────────────────────────────────────────────────────
const fetchData = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (filters.template) params.template = filters.template
    if (filters.from) params.from = filters.from
    if (filters.to) params.to = filters.to
    const res = await api.get('/api/calibration/brier-score', { params })
    // L'intercepteur axios renvoie déjà res.data; on tolère les deux formes.
    const payload = res && res.data ? res.data : res
    data.value = payload
  } catch (err) {
    const msg = err && err.message ? err.message : String(err)
    error.value = msg
  } finally {
    loading.value = false
  }
}

const refresh = () => fetchData()

const applyFilters = () => fetchData()

const resetFilters = () => {
  filters.template = ''
  filters.from = ''
  filters.to = ''
  fetchData()
}

// ─── Données dérivées ───────────────────────────────────────────────────────

// Le backend expose les compteurs en "n_called_it / n_partial / n_wrong" et
// le brief parle de "outcomes.called_it / partial / wrong". On expose une
// structure unique qui supporte les deux variantes pour rester robuste si le
// backend évolue.
const outcomeCounts = computed(() => {
  if (!data.value) return { called_it: 0, partial: 0, wrong: 0 }
  const d = data.value
  // Préférence à la forme imbriquée si elle existe (forward-compat) puis fallback.
  const nested = d.outcomes && typeof d.outcomes === 'object' ? d.outcomes : null
  return {
    called_it: nested && Number.isFinite(nested.called_it) ? nested.called_it : (d.n_called_it || 0),
    partial:   nested && Number.isFinite(nested.partial)   ? nested.partial   : (d.n_partial   || 0),
    wrong:     nested && Number.isFinite(nested.wrong)     ? nested.wrong     : (d.n_wrong     || 0),
  }
})

const deltaChip = computed(() => {
  if (!data.value) return null
  // Backend ne porte pas encore ce champ : on le détecte si présent et on le
  // masque sinon (fail closed). Sources possibles : delta_vs_previous_month
  // (nom canonique du brief) ou delta_vs_previous (raccourci).
  const d = data.value
  const delta = (d.delta_vs_previous_month ?? d.delta_vs_previous)
  if (delta === null || delta === undefined || !Number.isFinite(delta)) return null
  if (delta === 0) {
    return {
      cls: 'cal-delta-chip--neutral',
      arrow: '→',
      text: delta.toFixed(2),
    }
  }
  // Brier : plus bas = mieux. Donc delta < 0 → mieux qu'avant → mint.
  // delta > 0 → moins bon → peach.
  const better = delta < 0
  return {
    cls: better ? 'cal-delta-chip--better' : 'cal-delta-chip--worse',
    arrow: better ? '↓' : '↑',
    text: (delta > 0 ? '+' : '') + delta.toFixed(2),
  }
})

const availableTemplates = computed(() => {
  if (!data.value) return []
  // Le brief mentionne data.filters.templates_available. On supporte aussi
  // une forme top-level pour rester souple.
  const d = data.value
  const list = (d.filters && Array.isArray(d.filters.templates_available))
    ? d.filters.templates_available
    : (Array.isArray(d.templates_available) ? d.templates_available : [])
  return list.filter(Boolean)
})

const plotPoints = computed(() => {
  if (!data.value || !Array.isArray(data.value.calibration_plot)) return []
  // On ne garde que les buckets qui ont au moins une observation : un cercle
  // sur un bucket vide trompe l'œil (suggère « 0 observed » alors qu'on n'a
  // simplement pas de données).
  return data.value.calibration_plot.filter((b) => {
    return b && Number.isFinite(b.n) && b.n > 0
       && Number.isFinite(b.predicted) && Number.isFinite(b.observed)
  })
})

// ─── Format helpers ─────────────────────────────────────────────────────────
const formatBrier = (b) => {
  if (b === null || b === undefined || !Number.isFinite(b)) return '—'
  return b.toFixed(2)
}

const formatPct = (count, total) => {
  if (!total || !Number.isFinite(count)) return ''
  const pct = (count / total) * 100
  // Une décimale tant qu'on n'est pas sur un round value.
  const rounded = Math.round(pct)
  return `(${rounded}%)`
}

// ─── Geometry du scatter ────────────────────────────────────────────────────
// Coordonnées en unités SVG ; le viewBox redimensionne pour rester
// responsive. Pas de getBoundingClientRect ⇒ le rendu reste correct quelle
// que soit la largeur d'écran.
const plotW = 760
const plotH = 560
const padTop = 28
const padBottom = 56
const padInline = 56
const innerW = plotW - padInline * 2
const innerH = plotH - padTop - padBottom

const tickValues = [0, 0.2, 0.4, 0.6, 0.8, 1]
const gridLines = [0.2, 0.4, 0.6, 0.8]

const xScale = (v) => padInline + v * innerW
const yScale = (v) => padTop + innerH - v * innerH

const bucketRadius = (n) => {
  // r = sqrt(n) * 2, clamp 4..20 (cf. brief). Min 4 pour que les buckets
  // peu nombreux restent cliquables.
  if (!Number.isFinite(n) || n <= 0) return 4
  const r = Math.sqrt(n) * 2
  return Math.max(4, Math.min(20, r))
}

// ─── Tooltip ────────────────────────────────────────────────────────────────
const tooltip = reactive({
  visible: false,
  x: 0,
  y: 0,
  predicted: '',
  observed: '',
  n: 0,
})

// On capture la position relative au container .cal-plot-wrap pour que le
// tooltip puisse être positionné en CSS pur (top-left + transform).
let lastMouse = { x: 0, y: 0 }

const onPlotMouseMove = (event) => {
  if (!plotWrap.value) return
  const rect = plotWrap.value.getBoundingClientRect()
  lastMouse = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  }
  if (tooltip.visible) {
    tooltip.x = lastMouse.x
    tooltip.y = lastMouse.y
  }
}

const showTooltip = (event, bucket) => {
  if (!plotWrap.value) return
  const rect = plotWrap.value.getBoundingClientRect()
  tooltip.x = event.clientX - rect.left
  tooltip.y = event.clientY - rect.top
  tooltip.predicted = bucket.predicted.toFixed(2)
  tooltip.observed = bucket.observed.toFixed(2)
  tooltip.n = bucket.n
  tooltip.visible = true
}

const hideTooltip = () => {
  tooltip.visible = false
}

// ─── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   /calibration — Playful & Soft, RTL-safe (logical props)
   ═══════════════════════════════════════════════════════════ */

.cal-page {
  min-height: 100vh;
  background: var(--ms-bg);
  color: var(--ms-text);
  font-family: var(--ms-font-body);
}

/* ── Top bar ── */
.cal-topbar {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--ms-space-6) var(--ms-space-6) 0;
}

.cal-back {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  font-family: var(--ms-font-display);
  font-weight: 600;
  font-size: var(--ms-text-base);
  color: var(--ms-text);
  text-decoration: none;
  padding: 8px 14px;
  border-radius: var(--ms-radius-pill);
  background: var(--ms-bg-elevated);
  box-shadow: var(--ms-shadow-sm);
  transition: transform var(--ms-transition), box-shadow var(--ms-transition);
}
.cal-back:hover {
  transform: translateY(-1px);
  box-shadow: var(--ms-shadow-md);
}
.cal-back-arrow {
  color: var(--ms-orange);
  font-weight: 700;
}

/* ── Main container ── */
.cal-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--ms-space-8) var(--ms-space-6) var(--ms-space-12);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-12);
}

/* ── Hero band ── */
.cal-hero {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-4);
  align-items: flex-start;
}

.cal-eyebrow {
  display: inline-block;
  background: var(--ms-orange-soft);
  color: var(--ms-text);
  padding: 4px 12px;
  border-radius: var(--ms-radius-pill);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.cal-headline {
  font-family: var(--ms-font-display);
  font-size: 48px;
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--ms-text);
}

.cal-sub {
  font-size: 17px;
  line-height: 1.55;
  color: var(--ms-text-muted);
  max-width: 720px;
  margin: 0;
}

.cal-big-row {
  display: flex;
  align-items: flex-end;
  gap: var(--ms-space-5);
  flex-wrap: wrap;
  margin-top: var(--ms-space-4);
}

.cal-big-num {
  font-family: var(--ms-font-display);
  font-size: 96px;
  font-weight: 600;
  line-height: 1;
  color: var(--ms-orange-strong);
  letter-spacing: -0.03em;
}

.cal-big-num--empty {
  color: var(--ms-text-subtle);
}

.cal-delta-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--ms-radius-pill);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 16px;
}
.cal-delta-chip--better {
  background: var(--ms-mint-soft);
  color: #2F7A52;
}
.cal-delta-chip--worse {
  background: var(--ms-peach-soft);
  color: #8A5610;
}
.cal-delta-chip--neutral {
  background: var(--ms-bg-muted);
  color: var(--ms-text-muted);
}
.cal-delta-arrow { font-weight: 700; }

.cal-big-caption {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}
.cal-big-label {
  font-family: var(--ms-font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--ms-text);
}
.cal-big-help {
  font-size: 13px;
  color: var(--ms-text-muted);
}

.cal-big-skeleton-wrap {
  display: flex;
  gap: var(--ms-space-4);
  align-items: flex-end;
}
.cal-big-skeleton-num {
  width: 220px;
  height: 86px;
  border-radius: var(--ms-radius-md);
}
.cal-big-skeleton-chip {
  width: 90px;
  height: 28px;
  border-radius: var(--ms-radius-pill);
  margin-bottom: 16px;
}

/* ── Erreur ── */
.cal-error {
  display: flex;
  align-items: center;
  gap: var(--ms-space-4);
  padding: var(--ms-space-4) var(--ms-space-5);
  background: var(--ms-rose-soft);
  border-radius: var(--ms-radius-md);
  border: 1px solid rgba(244, 132, 122, 0.35);
}
.cal-error-icon {
  font-size: 24px;
  color: #A1403A;
}
.cal-error-body { flex: 1; }
.cal-error-title {
  font-family: var(--ms-font-display);
  font-weight: 600;
  font-size: var(--ms-text-base);
  color: #A1403A;
}
.cal-error-msg {
  font-size: var(--ms-text-sm);
  color: var(--ms-text-muted);
  margin-top: 2px;
  word-break: break-word;
}

/* ── Stats strip ── */
.cal-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--ms-space-4);
}
.cal-stat-card {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-3);
}
.cal-stat-num {
  font-family: var(--ms-font-display);
  font-weight: 600;
  font-size: 36px;
  line-height: 1.1;
  color: var(--ms-text);
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.cal-stat-pct {
  font-size: 15px;
  font-weight: 500;
  color: var(--ms-text-muted);
}
.cal-stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ms-space-2);
}
.cal-stat-label {
  font-size: 13px;
  color: var(--ms-text-muted);
}
.cal-num-skel {
  display: inline-block;
  width: 80px;
  height: 36px;
}

/* ── Plot grid (plot + filters) ── */
.cal-plot-grid {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(0, 3fr);
  gap: var(--ms-space-6);
}

.cal-plot-card {
  padding: var(--ms-space-8);
  border-radius: var(--ms-radius-lg);
  box-shadow: var(--ms-shadow-md);
}
.cal-plot-head {
  margin-bottom: var(--ms-space-5);
}
.cal-plot-title {
  font-family: var(--ms-font-display);
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: var(--ms-text);
}
.cal-plot-explainer {
  font-size: 13px;
  color: var(--ms-text-muted);
  margin: 0;
  line-height: 1.55;
}

.cal-plot-skeleton {
  height: 600px;
}
.cal-plot-skel-svg {
  width: 100%;
  height: 100%;
  border-radius: var(--ms-radius-md);
}

.cal-plot-empty {
  height: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--ms-text-muted);
}
.cal-plot-empty-icon {
  font-size: 40px;
  color: var(--ms-orange);
}
.cal-plot-empty-title {
  font-family: var(--ms-font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--ms-text);
}
.cal-plot-empty-msg {
  font-size: 13px;
  text-align: center;
  max-width: 360px;
}

.cal-plot-wrap {
  position: relative;
  width: 100%;
}

.cal-plot-svg {
  width: 100%;
  height: auto;
  display: block;
  font-family: var(--ms-font-mono);
}

.cal-plot-grid-lines line {
  stroke: var(--ms-border);
  stroke-width: 1;
}
.cal-plot-axis {
  stroke: var(--ms-border-strong);
  stroke-width: 1.5;
}
.cal-plot-diagonal {
  stroke: var(--ms-text-subtle);
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
}
.cal-tick {
  fill: var(--ms-text-muted);
  font-size: 11px;
}
.cal-tick-x { text-anchor: middle; }
.cal-tick-y { text-anchor: end; }
.cal-axis-title {
  fill: var(--ms-text-muted);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  font-family: var(--ms-font-body);
}

.cal-plot-dot {
  fill: var(--ms-orange);
  fill-opacity: 0.85;
  stroke: var(--ms-bg-elevated);
  stroke-width: 1.5;
  cursor: pointer;
  transition: fill-opacity var(--ms-transition), transform var(--ms-transition);
}
.cal-plot-dot:hover {
  fill-opacity: 1;
}

/* Tooltip — on garde left:/top: en JS via :style car la position colle au
   curseur (pattern documenté dans PolymarketChart.vue). En LTR/RTL les
   coordonnées partent du même coin (top-left du plot wrap), pas de besoin
   de logical properties ici. */
.cal-tooltip {
  position: absolute;
  pointer-events: none;
  background: var(--ms-text);
  color: var(--ms-text-on-color);
  padding: 8px 12px;
  border-radius: var(--ms-radius-sm);
  box-shadow: var(--ms-shadow-md);
  font-size: 12px;
  z-index: 20;
  transform: translate(-50%, calc(-100% - 14px));
  min-width: 160px;
}
.cal-tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  line-height: 1.6;
}
.cal-tooltip-key {
  color: rgba(255, 255, 255, 0.7);
}
.cal-tooltip-val {
  color: var(--ms-text-on-color);
  font-weight: 600;
}

/* ── Filters card ── */
.cal-filters-card {
  padding: var(--ms-space-6);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-4);
  align-self: start;
}
.cal-filters-title {
  font-family: var(--ms-font-display);
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  color: var(--ms-text);
}
.cal-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cal-field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ms-text-muted);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.cal-filters-note {
  font-size: 12px;
  color: var(--ms-text-subtle);
  margin: 0;
  line-height: 1.5;
}
.cal-filters-actions {
  display: flex;
  gap: var(--ms-space-2);
  flex-wrap: wrap;
}

/* ── Methodology + CTA bottom ── */
.cal-bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ms-space-8);
}
.cal-method-title {
  font-family: var(--ms-font-display);
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 var(--ms-space-4) 0;
  letter-spacing: -0.01em;
  color: var(--ms-text);
}
.cal-method-p {
  font-size: 15px;
  line-height: 1.65;
  color: var(--ms-text-muted);
  margin: 0 0 var(--ms-space-3) 0;
}

.cal-cta-card {
  background: var(--ms-mint-soft);
  border-color: rgba(127, 216, 166, 0.35);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-3);
  padding: var(--ms-space-8);
  border-radius: var(--ms-radius-lg);
}
.cal-cta-title {
  font-family: var(--ms-font-display);
  font-size: 22px;
  font-weight: 600;
  color: var(--ms-text);
  margin: 0;
}
.cal-cta-p {
  font-size: 15px;
  line-height: 1.6;
  color: var(--ms-text);
  opacity: 0.78;
  margin: 0;
}
.cal-cta-btn {
  margin-top: var(--ms-space-2);
  background: var(--ms-mint);
  color: var(--ms-text);
  border: 1px solid rgba(47, 122, 82, 0.18);
  align-self: flex-start;
  box-shadow: var(--ms-shadow-sm);
}
.cal-cta-btn:hover {
  filter: brightness(1.04);
  transform: translateY(-1px);
  box-shadow: var(--ms-shadow-md);
}
.cal-cta-arrow {
  font-weight: 700;
}

/* ── Responsive ── */
@media (max-width: 960px) {
  .cal-plot-grid {
    grid-template-columns: 1fr;
  }
  .cal-bottom-grid {
    grid-template-columns: 1fr;
    gap: var(--ms-space-6);
  }
}

@media (max-width: 768px) {
  .cal-headline { font-size: 36px; }
  .cal-big-num { font-size: 64px; }
  .cal-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .cal-plot-card { padding: var(--ms-space-5); }
  .cal-plot-skeleton { height: 400px; }
  .cal-plot-empty { height: 340px; }
}
</style>
