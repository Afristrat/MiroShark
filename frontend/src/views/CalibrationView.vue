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
              <option v-for="tpl in availableTemplates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
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

      <!-- ───────────── Sims à évaluer (US-046) ───────────── -->
      <!--
        Inbox layer wired to GET /api/calibration/simulations (US-045).
        Each card is a public sim the operator can mark inline; once a
        verdict is posted, the brier-score block at the top refreshes
        so the big number moves on the same page.
      -->
      <section class="calib-evaluables" :ref="el => setSectionRef(el, 4)" aria-label="Calibration inbox">
        <header class="calib-eval-head">
          <h2 class="calib-eval-title">{{ $t('calibration.evaluables.title') }}</h2>
          <p class="calib-eval-intro">{{ $t('calibration.evaluables.intro') }}</p>
        </header>

        <!-- Filtre rapide en pills -->
        <div class="calib-eval-pills" role="tablist" :aria-label="$t('calibration.evaluables.title')">
          <button
            v-for="opt in filterOptions"
            :key="opt.value"
            type="button"
            role="tab"
            class="calib-eval-pill"
            :class="{ 'calib-eval-pill--active': currentFilter === opt.value }"
            :aria-selected="currentFilter === opt.value"
            :disabled="evalLoading"
            @click="setFilter(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>

        <!-- Toast banner — fade-out CSS only, no toast lib -->
        <div
          v-if="toast.visible"
          class="calib-eval-toast"
          :class="`calib-eval-toast--${toast.kind}`"
          role="status"
        >
          {{ toast.message }}
        </div>

        <!-- Erreur de chargement -->
        <div v-if="evalError && !evalLoading" class="calib-eval-error" role="alert">
          <span class="calib-eval-error-icon" aria-hidden="true">⚠</span>
          <span>{{ $t('calibration.evaluables.errorLoad') }}</span>
          <button class="ms-btn ms-btn-ghost ms-btn--sm" @click="fetchEvaluables">
            {{ $t('common.retry') }}
          </button>
        </div>

        <!-- Loading skeleton -->
        <div v-if="evalLoading && evaluables.length === 0" class="calib-eval-loading">
          <div v-for="i in 3" :key="`sk${i}`" class="calib-eval-card calib-eval-card--skeleton">
            <div class="ms-skeleton calib-eval-skel-line calib-eval-skel-line--title"></div>
            <div class="ms-skeleton calib-eval-skel-line calib-eval-skel-line--body"></div>
            <div class="ms-skeleton calib-eval-skel-line calib-eval-skel-line--body"></div>
          </div>
        </div>

        <!-- Empty state -->
        <div
          v-else-if="!evalLoading && evaluables.length === 0 && !evalError"
          class="calib-eval-empty"
        >
          <span class="calib-eval-empty-icon" aria-hidden="true">○</span>
          <p>{{ $t('calibration.evaluables.empty') }}</p>
        </div>

        <!-- Liste des sims -->
        <ul v-else class="calib-eval-list">
          <li
            v-for="sim in evaluables"
            :key="sim.id"
            class="ms-card calib-eval-card"
            :class="{ 'calib-eval-card--saving': savingId === sim.id }"
          >
            <!-- Top row : title + badge + relative time -->
            <div class="calib-eval-card-top">
              <div class="calib-eval-card-titles">
                <h3 class="calib-eval-card-title">{{ sim.title }}</h3>
                <div class="calib-eval-card-meta">
                  <span
                    v-if="sim.template_name || sim.template_id"
                    class="ms-badge calib-eval-badge"
                  >
                    {{ sim.template_name || sim.template_id }}
                  </span>
                  <span class="calib-eval-card-date">{{ formatRelativeTime(sim.created_at) }}</span>
                </div>
              </div>
              <span
                v-if="sim.outcome"
                class="ms-badge calib-eval-current"
                :class="`calib-eval-current--${outcomeKindClass(sim.outcome)}`"
              >
                {{ $t('calibration.evaluables.currentOutcome') }} : {{ outcomeLabelText(sim.outcome) }}
              </span>
            </div>

            <!-- Body : snippet -->
            <p v-if="sim.summary_first_words" class="calib-eval-card-snippet">
              {{ sim.summary_first_words }}
            </p>

            <!-- Footer row : predicted % + 4 boutons + URL -->
            <div class="calib-eval-card-footer">
              <div class="calib-eval-actions">
                <span
                  v-if="Number.isFinite(sim.predicted_bullish_pct)"
                  class="calib-eval-pred ms-mono"
                  :title="$t('calibration.evaluables.predictedLabel')"
                >
                  {{ formatPredicted(sim.predicted_bullish_pct) }}
                </span>

                <div class="calib-eval-btns">
                  <button
                    class="ms-btn ms-btn--sm outcome-btn outcome-btn--called-it"
                    :class="{ 'outcome-btn--active': sim.outcome === 'correct' || sim.outcome === 'called_it' }"
                    :disabled="savingId === sim.id"
                    @click="markOutcome(sim, 'correct')"
                  >
                    {{ $t('calibration.evaluables.markCalledIt') }}
                  </button>
                  <button
                    class="ms-btn ms-btn--sm outcome-btn outcome-btn--partial"
                    :class="{ 'outcome-btn--active': sim.outcome === 'partial' }"
                    :disabled="savingId === sim.id"
                    @click="markOutcome(sim, 'partial')"
                  >
                    {{ $t('calibration.evaluables.markPartial') }}
                  </button>
                  <button
                    class="ms-btn ms-btn--sm outcome-btn outcome-btn--wrong"
                    :class="{ 'outcome-btn--active': sim.outcome === 'incorrect' || sim.outcome === 'wrong' }"
                    :disabled="savingId === sim.id"
                    @click="markOutcome(sim, 'incorrect')"
                  >
                    {{ $t('calibration.evaluables.markWrong') }}
                  </button>
                  <button
                    class="ms-btn ms-btn--sm ms-btn-ghost outcome-btn outcome-btn--na"
                    :disabled="savingId === sim.id"
                    @click="markOutcome(sim, null)"
                  >
                    {{ $t('calibration.evaluables.markNA') }}
                  </button>
                </div>
              </div>

              <input
                v-model="sim._urlDraft"
                type="url"
                class="ms-input calib-eval-url"
                :placeholder="$t('calibration.evaluables.urlPlaceholder')"
                :disabled="savingId === sim.id"
              />
            </div>
          </li>
        </ul>

        <!-- Pagination -->
        <nav v-if="evaluables.length > 0" class="calib-eval-pager" aria-label="Pagination">
          <button
            class="ms-btn ms-btn-ghost ms-btn--sm"
            :disabled="evalPagination.offset === 0 || evalLoading"
            @click="goPrev"
          >
            ← {{ $t('calibration.evaluables.previous') }}
          </button>
          <span class="calib-eval-pager-count ms-mono">
            {{ evalPagination.offset + 1 }}–{{ evalPagination.offset + evaluables.length }}
            / {{ evalPagination.total }}
          </span>
          <button
            class="ms-btn ms-btn-ghost ms-btn--sm"
            :disabled="!evalPagination.has_more || evalLoading"
            @click="goNext"
          >
            {{ $t('calibration.evaluables.next') }} →
          </button>
        </nav>
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
import { useI18n } from 'vue-i18n'
import api from '../api/index.js'
import { submitSimulationOutcome } from '../api/simulation.js'
import { useScrollFadeIn } from '../composables/useScrollFadeIn'
import { formatApiError } from '../utils/error-handler'

const { t } = useI18n()

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
    // US-007: surface localised, error_code-aware messages.
    error.value = formatApiError(err, t)
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
  // Le backend renvoie soit un array d'objets `[{id, name}, ...]` (forme
  // canonique depuis fix c8ec8fd), soit un array de strings legacy
  // `["id1", "id2"]` (avant fix). On normalise vers `[{id, name}]` dans
  // les deux cas pour que le <option> rende toujours le label humain.
  const d = data.value
  const raw = (d.filters && Array.isArray(d.filters.templates_available))
    ? d.filters.templates_available
    : (Array.isArray(d.templates_available) ? d.templates_available : [])
  return raw
    .filter(Boolean)
    .map((entry) => {
      if (typeof entry === 'string') return { id: entry, name: entry }
      if (entry && typeof entry === 'object' && entry.id) {
        return { id: String(entry.id), name: String(entry.name || entry.id) }
      }
      return null
    })
    .filter(Boolean)
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

// ─── Sims à évaluer (US-046) ────────────────────────────────────────────────
//
// Inbox layer wired to GET /api/calibration/simulations (US-045). On
// each verdict POST, we re-fetch /brier-score so the big number at the
// top of the page reflects the new sample. Optimistic UI : we mutate
// the local card immediately and revert on network error.

const filterOptions = computed(() => ([
  { value: 'pending',   label: t('calibration.evaluables.filterPending') },
  { value: 'evaluated', label: t('calibration.evaluables.filterEvaluated') },
  { value: 'all',       label: t('calibration.evaluables.filterAll') },
]))

const evaluables = ref([])
const evalLoading = ref(false)
const evalError = ref('')
const currentFilter = ref('pending')
const savingId = ref(null)

const evalPagination = reactive({
  limit: 20,
  offset: 0,
  total: 0,
  has_more: false,
})

const toast = reactive({
  visible: false,
  kind: 'success',  // 'success' | 'error'
  message: '',
})
let toastTimer = null

const showToast = (message, kind = 'success', durationMs = 3000) => {
  toast.message = message
  toast.kind = kind
  toast.visible = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.visible = false
  }, durationMs)
}

const fetchEvaluables = async () => {
  evalLoading.value = true
  evalError.value = ''
  try {
    const res = await api.get('/api/calibration/simulations', {
      params: {
        status: currentFilter.value,
        limit: evalPagination.limit,
        offset: evalPagination.offset,
      },
    })
    const payload = res && res.data ? res : null
    if (!payload) {
      evaluables.value = []
      return
    }
    // The backend wraps the list under data: [...] and the axios
    // interceptor returns response.data, so the items are at
    // payload.data and pagination at payload.pagination.
    const items = Array.isArray(payload.data) ? payload.data : []
    // Hydrate a per-card url draft buffer so the input keeps its value
    // through re-renders without leaking back into the canonical shape.
    evaluables.value = items.map((sim) => ({
      ...sim,
      _urlDraft: sim.outcome_url || '',
    }))
    if (payload.pagination) {
      evalPagination.limit    = payload.pagination.limit ?? evalPagination.limit
      evalPagination.offset   = payload.pagination.offset ?? evalPagination.offset
      evalPagination.total    = payload.pagination.total ?? 0
      evalPagination.has_more = !!payload.pagination.has_more
    }
  } catch (err) {
    evalError.value = formatApiError(err, t)
    evaluables.value = []
  } finally {
    evalLoading.value = false
  }
}

const setFilter = (value) => {
  if (currentFilter.value === value) return
  currentFilter.value = value
  evalPagination.offset = 0
  fetchEvaluables()
}

const goPrev = () => {
  const next = Math.max(0, evalPagination.offset - evalPagination.limit)
  if (next === evalPagination.offset) return
  evalPagination.offset = next
  fetchEvaluables()
}

const goNext = () => {
  if (!evalPagination.has_more) return
  evalPagination.offset = evalPagination.offset + evalPagination.limit
  fetchEvaluables()
}

const _isValidEvidenceUrl = (url) => {
  if (!url) return true   // optional — empty is OK
  return url.startsWith('http://') || url.startsWith('https://')
}

const markOutcome = async (sim, label) => {
  // ``label === null`` → N/A button. We translate it to the soft-delete
  // semantics (``incorrect``) only if the operator confirms intent —
  // here we treat N/A as « ne fais rien si non évalué », so we simply
  // skip the POST when label is null AND the sim has no current
  // outcome. If it already has one, we still skip (no clean "delete
  // outcome" endpoint exists yet — documented in the report).
  if (label === null) {
    showToast(t('calibration.evaluables.toastSuccess'), 'success', 2000)
    return
  }

  const evidenceUrl = (sim._urlDraft || '').trim()
  if (evidenceUrl && !_isValidEvidenceUrl(evidenceUrl)) {
    showToast(t('calibration.evaluables.invalidUrl'), 'error', 3500)
    return
  }

  // Optimistic update — keep a snapshot to revert on error.
  const previousOutcome = sim.outcome
  const previousUrl = sim.outcome_url
  sim.outcome = label
  sim.outcome_url = evidenceUrl || null

  savingId.value = sim.id
  try {
    await submitSimulationOutcome(sim.id, {
      label,
      outcome_url: evidenceUrl,
    })
    showToast(t('calibration.evaluables.toastSuccess'), 'success')

    // If we're in « pending » filter, the just-marked sim no longer
    // belongs in the visible list — drop it locally so the operator
    // sees instant progress, then refresh the brier-score.
    if (currentFilter.value === 'pending') {
      evaluables.value = evaluables.value.filter((s) => s.id !== sim.id)
      evalPagination.total = Math.max(0, evalPagination.total - 1)
    }

    // Refresh the aggregated brier-score so the headline number moves.
    fetchData()
  } catch (err) {
    // Revert optimistic update on network failure.
    sim.outcome = previousOutcome
    sim.outcome_url = previousUrl
    const reason = formatApiError(err, t)
    showToast(t('calibration.evaluables.toastError') + (reason ? ` (${reason})` : ''), 'error', 4000)
  } finally {
    savingId.value = null
  }
}

// ── Helpers de présentation ────────────────────────────────────────────────

const outcomeKindClass = (label) => {
  if (label === 'correct' || label === 'called_it') return 'success'
  if (label === 'partial') return 'partial'
  if (label === 'incorrect' || label === 'wrong') return 'wrong'
  return 'neutral'
}

const outcomeLabelText = (label) => {
  if (label === 'correct' || label === 'called_it') return t('calibration.evaluables.markCalledIt')
  if (label === 'partial') return t('calibration.evaluables.markPartial')
  if (label === 'incorrect' || label === 'wrong') return t('calibration.evaluables.markWrong')
  return ''
}

const formatPredicted = (p) => {
  if (!Number.isFinite(p)) return '—'
  // p ∈ [0, 1] on the wire ; show as a percentage with 0 decimals.
  return `${Math.round(p * 100)}%`
}

const formatRelativeTime = (iso) => {
  if (!iso) return ''
  const ts = Date.parse(iso)
  if (Number.isNaN(ts)) return ''
  const diffMs = Date.now() - ts
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return t('calibration.evaluables.relativeTimeJustNow')
  if (diffMin < 60) return t('calibration.evaluables.relativeTimeMinutesAgo', { count: diffMin })
  const diffH = Math.round(diffMin / 60)
  if (diffH < 24) return t('calibration.evaluables.relativeTimeHoursAgo', { count: diffH })
  const diffD = Math.round(diffH / 24)
  return t('calibration.evaluables.relativeTimeDaysAgo', { count: diffD })
}

// ─── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(() => {
  fetchData()
  fetchEvaluables()
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
  color: var(--ms-status-success-text);
}
.cal-delta-chip--worse {
  background: var(--ms-peach-soft);
  color: var(--ms-status-warning-text);
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
  color: var(--ms-status-danger-text);
}
.cal-error-body { flex: 1; }
.cal-error-title {
  font-family: var(--ms-font-display);
  font-weight: 600;
  font-size: var(--ms-text-base);
  color: var(--ms-status-danger-text);
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

/* ═══════════════════════════════════════════════════════════
   « Sims à évaluer » (US-046)
   - Cards verticalement empilées (1 col), full-width mobile.
   - Boutons outcome avec couleurs --ms-mint / --ms-peach /
     --ms-rose / ghost via override sur .outcome-btn--*.
   - RTL-safe : on utilise inset-inline-* / margin-inline-* etc.
   ═══════════════════════════════════════════════════════════ */

.calib-evaluables {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-5);
}

.calib-eval-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.calib-eval-title {
  font-family: var(--ms-font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0;
  color: var(--ms-text);
}

.calib-eval-intro {
  font-size: 14px;
  color: var(--ms-text-muted);
  line-height: 1.55;
  margin: 0;
  max-width: 760px;
}

/* ── Pills filtre rapide ── */
.calib-eval-pills {
  display: flex;
  gap: var(--ms-space-2);
  flex-wrap: wrap;
}

.calib-eval-pill {
  font-family: var(--ms-font-body);
  font-size: 13px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: var(--ms-radius-pill);
  border: 1px solid var(--ms-border);
  background: var(--ms-bg-elevated);
  color: var(--ms-text-muted);
  cursor: pointer;
  transition: background var(--ms-transition), color var(--ms-transition),
              border-color var(--ms-transition), transform var(--ms-transition);
}
.calib-eval-pill:hover:not(:disabled) {
  border-color: var(--ms-orange);
  color: var(--ms-text);
}
.calib-eval-pill:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.calib-eval-pill--active {
  background: var(--ms-orange-soft);
  border-color: var(--ms-orange);
  color: var(--ms-text);
}

/* ── Toast banner ── */
.calib-eval-toast {
  padding: 10px 14px;
  border-radius: var(--ms-radius-md);
  font-size: 14px;
  font-weight: 500;
  animation: calibEvalToastIn 200ms ease-out;
}
.calib-eval-toast--success {
  background: var(--ms-mint-soft);
  color: var(--ms-status-success-text);
  border: 1px solid rgba(127, 216, 166, 0.35);
}
.calib-eval-toast--error {
  background: var(--ms-rose-soft);
  color: var(--ms-status-danger-text);
  border: 1px solid rgba(244, 132, 122, 0.35);
}
@keyframes calibEvalToastIn {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Erreur de chargement ── */
.calib-eval-error {
  display: flex;
  align-items: center;
  gap: var(--ms-space-3);
  padding: var(--ms-space-3) var(--ms-space-4);
  border-radius: var(--ms-radius-md);
  background: var(--ms-rose-soft);
  color: var(--ms-status-danger-text);
  font-size: 14px;
}
.calib-eval-error-icon {
  font-size: 18px;
}

/* ── Empty state ── */
.calib-eval-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: var(--ms-space-8);
  border: 1px dashed var(--ms-border);
  border-radius: var(--ms-radius-md);
  color: var(--ms-text-muted);
  font-size: 14px;
  text-align: center;
}
.calib-eval-empty-icon {
  font-size: 28px;
  color: var(--ms-orange);
}
.calib-eval-empty p { margin: 0; }

/* ── Loading skeleton cards ── */
.calib-eval-loading {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-3);
}
.calib-eval-skel-line {
  border-radius: var(--ms-radius-sm);
}
.calib-eval-skel-line--title {
  width: 60%;
  height: 18px;
  margin-bottom: 12px;
}
.calib-eval-skel-line--body {
  width: 100%;
  height: 12px;
  margin-bottom: 6px;
}

/* ── Liste de cards ── */
.calib-eval-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-4);
}

.calib-eval-card {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-3);
  padding: var(--ms-space-5);
  transition: transform var(--ms-transition), box-shadow var(--ms-transition);
}
.calib-eval-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--ms-shadow-md);
}
.calib-eval-card--saving {
  opacity: 0.7;
  pointer-events: none;
}
.calib-eval-card--skeleton:hover {
  transform: none;
}

.calib-eval-card-top {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ms-space-3);
  justify-content: space-between;
  align-items: flex-start;
}
.calib-eval-card-titles {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1 1 60%;
  min-width: 0;
}
.calib-eval-card-title {
  font-family: var(--ms-font-display);
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  color: var(--ms-text);
  line-height: 1.35;
  word-break: break-word;
}
.calib-eval-card-meta {
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  flex-wrap: wrap;
}
.calib-eval-badge {
  font-size: 11px;
  letter-spacing: 0.02em;
}
.calib-eval-card-date {
  font-size: 12px;
  color: var(--ms-text-subtle);
}

.calib-eval-current {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 4px 10px;
}
.calib-eval-current--success {
  background: var(--ms-mint-soft);
  color: var(--ms-status-success-text);
}
.calib-eval-current--partial {
  background: var(--ms-peach-soft);
  color: var(--ms-status-warning-text);
}
.calib-eval-current--wrong {
  background: var(--ms-rose-soft);
  color: var(--ms-status-danger-text);
}

.calib-eval-card-snippet {
  font-size: 14px;
  line-height: 1.55;
  color: var(--ms-text-muted);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.calib-eval-card-footer {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ms-space-3);
  align-items: center;
  justify-content: space-between;
}
.calib-eval-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ms-space-3);
  align-items: center;
}
.calib-eval-pred {
  font-size: 14px;
  font-weight: 600;
  color: var(--ms-text);
  padding: 4px 10px;
  background: var(--ms-bg-muted);
  border-radius: var(--ms-radius-sm);
  /* logical property for RTL safety */
  margin-inline-end: 4px;
}
.calib-eval-btns {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* Outcome buttons — spec couleurs : mint / peach / rose / ghost */
.outcome-btn {
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--ms-radius-pill);
  border: 1px solid transparent;
  cursor: pointer;
  transition: filter var(--ms-transition), transform var(--ms-transition),
              box-shadow var(--ms-transition);
}
.outcome-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.outcome-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--ms-shadow-sm);
}

.outcome-btn--called-it {
  background: var(--ms-mint);
  color: var(--ms-text);
  border-color: rgba(47, 122, 82, 0.18);
}
.outcome-btn--partial {
  background: var(--ms-peach);
  color: var(--ms-text);
  border-color: rgba(138, 86, 16, 0.18);
}
.outcome-btn--wrong {
  background: var(--ms-rose);
  color: var(--ms-text);
  border-color: rgba(161, 64, 58, 0.18);
}
.outcome-btn--na {
  background: transparent;
  color: var(--ms-text-muted);
}
.outcome-btn--active {
  filter: brightness(0.94);
  box-shadow: inset 0 0 0 2px rgba(0, 0, 0, 0.18);
}

.calib-eval-url {
  flex: 1 1 220px;
  min-width: 200px;
  font-size: 13px;
  /* RTL : forcer le texte à toujours partir du bord logique de début. */
  text-align: start;
}

/* ── Pager ── */
.calib-eval-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ms-space-3);
  padding-top: var(--ms-space-3);
}
.calib-eval-pager-count {
  font-size: 12px;
  color: var(--ms-text-muted);
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
  .calib-eval-title { font-size: 24px; }
  .calib-eval-card { padding: var(--ms-space-4); }
  .calib-eval-card-footer {
    align-items: stretch;
  }
  .calib-eval-url {
    width: 100%;
  }
  .calib-eval-btns {
    width: 100%;
  }
  .calib-eval-btns .outcome-btn {
    flex: 1 1 calc(50% - 3px);
  }
}
</style>
