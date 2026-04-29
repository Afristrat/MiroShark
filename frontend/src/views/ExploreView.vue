<template>
  <div class="explore-container">
    <!-- Top Navigation Bar (mirrors Home.vue nav for visual consistency) -->
    <nav class="navbar">
      <router-link to="/" class="nav-brand" :title="$t('simulation.view.back')">BASSIRA</router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-link" :title="$t('simulation.view.back')">
          <span class="arrow">←</span> {{ $t('nav.brand') }}
        </router-link>
        <a
          href="https://github.com/aaronjmars/MiroShark"
          target="_blank"
          rel="noopener"
          class="github-link"
        >
          {{ $t('nav.github') }} <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- Header -->
      <header class="explore-header">
        <div class="tag-row">
          <span class="orange-tag">{{ verifiedOnly ? '📍 ' + $t('explore.header.verified') : '◎ ' + $t('explore.header.title') }}</span>
          <span class="meta-sep">·</span>
          <span class="meta-text">
            {{ verifiedOnly ? $t('explore.header.verified') : $t('explore.header.subtitle') }}
          </span>
        </div>
        <h1 class="page-title">{{ verifiedOnly ? $t('explore.header.verified') : $t('explore.header.title') }}</h1>
        <p class="page-subtitle">
          <template v-if="verifiedOnly">
            Each card is a public Bassira run whose operator marked the
            real-world outcome. Hover the badge for the source link, open
            one to see how the agent consensus formed, or fork it to test
            the same agent population on a fresh scenario.
          </template>
          <template v-else>
            Every card is a real Bassira run someone published. Open one to see
            the full belief drift, agent network, and prediction outcome — or fork
            it in one click and run your own variant with the same agent population.
          </template>
        </p>
        <div class="stats-row">
          <span class="stat-chip">
            <span class="stat-num">{{ loading ? '…' : total }}</span>
            <span class="stat-label">{{ verifiedOnly ? 'verified' : 'published' }}</span>
          </span>
          <span v-if="!verifiedOnly && !loading && items.length > 0" class="stat-chip">
            <span class="stat-num">{{ resolvedCount }}</span>
            <span class="stat-label">resolved</span>
          </span>
          <span v-if="!verifiedOnly && !loading && items.length > 0" class="stat-chip">
            <span class="stat-num">{{ verifiedCount }}</span>
            <span class="stat-label">verified</span>
          </span>

          <!-- Verified filter chip — toggles a `?verified=1` fetch + the
               /verified URL so the view is shareable. -->
          <button
            class="filter-chip"
            :class="{ 'filter-chip-active': verifiedFilter }"
            @click="toggleVerifiedFilter"
            :disabled="loading"
            :title="verifiedFilter ? $t('explore.header.title') : $t('explore.header.verified')"
          >
            <span class="filter-chip-icon">📍</span>
            <span>{{ $t('explore.filters.verified') }}</span>
          </button>

          <button
            class="refresh-btn"
            @click="refresh"
            :disabled="loading"
            :title="$t('common.retry')"
          >
            <span v-if="loading">…</span>
            <span v-else>↻ {{ $t('common.retry') }}</span>
          </button>
        </div>
      </header>

      <!-- Loading skeletons — uses .ms-skeleton (shimmer + reduced-motion
           handling) from src/styles/components.css. -->
      <div v-if="loading && items.length === 0" class="gallery-loading">
        <div class="loading-grid">
          <div v-for="n in 8" :key="n" class="skeleton-card" aria-hidden="true">
            <div class="ms-skeleton skeleton-thumb"></div>
            <div class="skeleton-body">
              <div class="ms-skeleton skeleton-line skeleton-line-title"></div>
              <div class="ms-skeleton skeleton-line skeleton-line-title-short"></div>
              <div class="skeleton-pills">
                <div class="ms-skeleton skeleton-pill"></div>
                <div class="ms-skeleton skeleton-pill"></div>
                <div class="ms-skeleton skeleton-pill"></div>
              </div>
              <div class="ms-skeleton skeleton-bar"></div>
              <div class="ms-skeleton skeleton-line skeleton-line-meta"></div>
              <div class="skeleton-actions">
                <div class="ms-skeleton skeleton-btn"></div>
                <div class="ms-skeleton skeleton-btn"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="gallery-error">
        <div class="error-icon">⚠</div>
        <div class="error-title">{{ $t('explore.error') }}</div>
        <div class="error-msg">{{ error }}</div>
        <button class="error-retry" @click="refresh">{{ $t('common.retry') }}</button>
      </div>

      <!-- Empty -->
      <div v-else-if="items.length === 0" class="gallery-empty">
        <div class="empty-icon">{{ verifiedFilter ? '📍' : '◇' }}</div>
        <div class="empty-title">
          {{ $t('explore.empty') }}
        </div>
        <div class="empty-msg">
          <template v-if="verifiedFilter">
            Once an operator marks a public simulation's real-world outcome
            from the Embed dialog, it shows up here. In the meantime, browse
            every published run on
            <router-link to="/explore" class="inline-link">/explore</router-link>.
          </template>
          <template v-else>
            Yours could be first. Run a simulation, click the share icon on the
            result page, toggle "Public" — it'll appear here within 30 seconds.
          </template>
        </div>
        <router-link
          :to="verifiedFilter ? '/explore' : '/'"
          class="empty-cta"
        >
          {{ verifiedFilter ? 'Browse all public sims →' : 'Run a simulation →' }}
        </router-link>
      </div>

      <!-- Grid -->
      <div v-else class="gallery-grid">
        <article
          v-for="(item, idx) in items"
          :key="item.simulation_id"
          :ref="el => setGalleryCardRef(el, idx)"
          class="gallery-card"
          :class="{
            'card-resolved': item.resolution_outcome,
            'card-verified-correct': item.outcome && item.outcome.label === 'correct',
            'card-verified-incorrect': item.outcome && item.outcome.label === 'incorrect',
            'card-verified-partial': item.outcome && item.outcome.label === 'partial',
          }"
        >
          <!-- Thumbnail: the server-rendered share card PNG -->
          <router-link
            :to="{ name: 'SimulationRun', params: { simulationId: item.simulation_id } }"
            class="card-thumb-link"
            :title="item.scenario || 'Open simulation'"
          >
            <img
              :src="shareCardSrc(item)"
              class="card-thumb"
              alt=""
              loading="lazy"
              @error="onThumbError($event, item)"
            />
            <div class="card-thumb-overlay"></div>
          </router-link>

          <!-- Body -->
          <div class="card-body">
            <h2 class="card-scenario" :title="item.scenario">
              {{ item.scenario || '(untitled scenario)' }}
            </h2>

            <div class="card-pills">
              <component
                v-if="item.outcome && item.outcome.label"
                :is="item.outcome.outcome_url ? 'a' : 'span'"
                :href="item.outcome.outcome_url || undefined"
                :target="item.outcome.outcome_url ? '_blank' : undefined"
                :rel="item.outcome.outcome_url ? 'noopener noreferrer' : undefined"
                class="pill pill-verified"
                :class="outcomePillClass(item.outcome.label)"
                :title="outcomePillTitle(item.outcome)"
                @click.stop
              >
                {{ outcomePillIcon(item.outcome.label) }}
                {{ outcomePillLabel(item.outcome.label) }}
              </component>
              <span
                v-if="item.quality_health"
                class="pill"
                :class="qualityPillClass(item.quality_health)"
                :title="'Quality health: ' + item.quality_health"
              >
                ◉ {{ item.quality_health }}
              </span>
              <span
                v-if="dominantStance(item)"
                class="pill"
                :class="stancePillClass(dominantStance(item).label)"
                :title="'Final consensus: ' + stanceTooltip(item)"
              >
                {{ stanceGlyph(dominantStance(item).label) }}
                {{ dominantStance(item).label }} {{ dominantStance(item).pct }}%
              </span>
              <span
                v-if="item.resolution_outcome"
                class="pill pill-resolved"
                :title="'Real-world outcome recorded: ' + item.resolution_outcome"
              >
                ✓ Resolved · {{ item.resolution_outcome }}
              </span>
              <span
                v-else
                class="pill pill-status"
                :title="'Runner status: ' + item.runner_status"
              >
                {{ formatStatus(item) }}
              </span>
            </div>

            <!-- Belief split bar -->
            <div v-if="item.final_consensus" class="consensus-bar" :title="stanceTooltip(item)">
              <div
                v-if="item.final_consensus.bullish > 0"
                class="bar-seg bar-bullish"
                :style="{ width: item.final_consensus.bullish + '%' }"
              ></div>
              <div
                v-if="item.final_consensus.neutral > 0"
                class="bar-seg bar-neutral"
                :style="{ width: item.final_consensus.neutral + '%' }"
              ></div>
              <div
                v-if="item.final_consensus.bearish > 0"
                class="bar-seg bar-bearish"
                :style="{ width: item.final_consensus.bearish + '%' }"
              ></div>
            </div>

            <div class="card-meta">
              <span class="meta-item">
                <span class="meta-label">Agents</span>
                <span class="meta-val">{{ item.agent_count || 0 }}</span>
              </span>
              <span class="meta-sep">·</span>
              <span class="meta-item">
                <span class="meta-label">Rounds</span>
                <span class="meta-val">
                  {{ item.current_round || 0 }}<span v-if="item.total_rounds">/{{ item.total_rounds }}</span>
                </span>
              </span>
              <span class="meta-sep">·</span>
              <span class="meta-item" :title="item.created_at">
                <span class="meta-val">{{ formatDate(item.created_at) }}</span>
              </span>
            </div>

            <!-- Actions -->
            <div class="card-actions">
              <router-link
                :to="{ name: 'SimulationRun', params: { simulationId: item.simulation_id } }"
                class="action-btn action-view"
              >
                Open →
              </router-link>
              <button
                class="action-btn action-fork"
                @click="forkAndOpen(item)"
                :disabled="forkingId === item.simulation_id"
                :title="'Copy this simulation\'s agents + config into a new run'"
              >
                <span v-if="forkingId === item.simulation_id">Forking…</span>
                <span v-else>Fork this →</span>
              </button>
            </div>
            <div
              v-if="forkErrors[item.simulation_id]"
              class="fork-error"
            >
              {{ forkErrors[item.simulation_id] }}
            </div>
          </div>
        </article>
      </div>

      <!-- Load more -->
      <div v-if="items.length > 0 && hasMore" class="load-more-row">
        <button
          class="load-more-btn"
          @click="loadMore"
          :disabled="loadingMore"
        >
          <span v-if="loadingMore">Loading…</span>
          <span v-else>Load more ({{ total - items.length }} remaining)</span>
        </button>
      </div>
    </div>

    <footer class="explore-footer">
      <span class="footer-line"></span>
      <span class="footer-text">
        Want yours here? Run a sim, open the Embed dialog, toggle "Public."
      </span>
      <span class="footer-line"></span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
import { useRouter } from 'vue-router'
import {
  getPublicSimulations,
  forkSimulation,
  getShareCardUrl,
} from '../api/simulation'
import { useScrollFadeIn } from '../composables/useScrollFadeIn'

const props = defineProps({
  // When true, the view boots in verified-only mode. Wired to the
  // `/verified` route; users on `/explore` can also flip it on via the
  // filter chip in the header.
  verifiedOnly: { type: Boolean, default: false },
})

const router = useRouter()

const items = ref([])
const total = ref(0)
const hasMore = ref(false)
const limit = 30
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const forkingId = ref('')
const forkErrors = ref({})
const verifiedFilter = ref(props.verifiedOnly)

// Refs for the gallery cards — populated via :ref callback so the scroll
// observer can fade each card in once it enters the viewport. Cleared on
// every refresh so stale entries from a previous page don't leak in.
const galleryCardRefs = ref([])
const setGalleryCardRef = (el, idx) => {
  if (el) galleryCardRefs.value[idx] = el
}
useScrollFadeIn(galleryCardRefs)

const resolvedCount = computed(
  () => items.value.filter((item) => item.resolution_outcome).length,
)

const verifiedCount = computed(
  () => items.value.filter((item) => item.outcome && item.outcome.label).length,
)

const shareCardSrc = (item) => {
  // The backend includes a relative ``share_card_url``. Resolve against
  // the SPA origin so the <img> works whether the frontend is served by
  // Flask in production or by Vite in dev (the dev server proxies /api).
  if (item.share_card_url) {
    if (item.share_card_url.startsWith('http')) return item.share_card_url
    return item.share_card_url
  }
  return getShareCardUrl(item.simulation_id)
}

const onThumbError = (event, item) => {
  // Hide broken images (e.g. if the simulation was unpublished between
  // fetch and image load) — fall back to a monochrome tile so the card
  // still lays out evenly.
  const img = event?.target
  if (!img || img.dataset.fellBack === '1') return
  img.dataset.fellBack = '1'
  img.style.display = 'none'
}

const dominantStance = (item) => {
  const c = item.final_consensus
  if (!c) return null
  const entries = [
    { label: 'Bullish', pct: c.bullish ?? 0 },
    { label: 'Neutral', pct: c.neutral ?? 0 },
    { label: 'Bearish', pct: c.bearish ?? 0 },
  ]
  entries.sort((a, b) => b.pct - a.pct)
  const top = entries[0]
  if (!top || top.pct <= 0) return null
  return { label: top.label, pct: Math.round(top.pct) }
}

const stanceGlyph = (label) => {
  if (label === 'Bullish') return '▲'
  if (label === 'Bearish') return '▼'
  return '●'
}

const stancePillClass = (label) => {
  if (label === 'Bullish') return 'pill-bullish'
  if (label === 'Bearish') return 'pill-bearish'
  return 'pill-neutral'
}

const stanceTooltip = (item) => {
  const c = item.final_consensus
  if (!c) return ''
  const b = (c.bullish ?? 0).toFixed(1)
  const n = (c.neutral ?? 0).toFixed(1)
  const be = (c.bearish ?? 0).toFixed(1)
  return `Bullish ${b}% · Neutral ${n}% · Bearish ${be}%`
}

const qualityPillClass = (health) => {
  const h = String(health || '').toLowerCase()
  if (h.startsWith('excel')) return 'pill-quality-excellent'
  if (h.startsWith('good')) return 'pill-quality-good'
  if (h.startsWith('fair')) return 'pill-quality-fair'
  if (h.startsWith('poor')) return 'pill-quality-poor'
  return 'pill-quality-unknown'
}

const formatStatus = (item) => {
  const status = item.runner_status || item.status || 'idle'
  return String(status).replace(/_/g, ' ')
}

const formatDate = (iso) => {
  if (!iso) return '—'
  // Keep it cheap — just the YYYY-MM-DD prefix from the ISO string.
  return String(iso).slice(0, 10)
}

const outcomePillLabel = (label) => {
  if (label === 'correct') return 'Verified'
  if (label === 'incorrect') return 'Called wrong'
  if (label === 'partial') return 'Partial'
  return ''
}

const outcomePillIcon = (label) => {
  if (label === 'correct') return '📍'
  if (label === 'incorrect') return '⚠'
  if (label === 'partial') return '◑'
  return ''
}

const outcomePillClass = (label) => {
  if (label === 'correct') return 'pill-verified-correct'
  if (label === 'incorrect') return 'pill-verified-incorrect'
  if (label === 'partial') return 'pill-verified-partial'
  return ''
}

const outcomePillTitle = (outcome) => {
  if (!outcome) return ''
  const summary = (outcome.outcome_summary || '').trim()
  const link = outcome.outcome_url ? ` — ${outcome.outcome_url}` : ''
  if (summary) return summary + link
  return outcomePillLabel(outcome.label) + link
}

const loadPage = async (offset = 0) => {
  const res = await getPublicSimulations({
    limit,
    offset,
    verifiedOnly: verifiedFilter.value,
  })
  if (!res?.success) {
    throw new Error(res?.error || 'Request failed')
  }
  return {
    data: res.data || [],
    total: Number.isFinite(res.total) ? res.total : (res.data?.length ?? 0),
    hasMore: !!res.has_more,
  }
}

const toggleVerifiedFilter = () => {
  verifiedFilter.value = !verifiedFilter.value
  // Keep the URL in lockstep with the filter so the page is shareable —
  // /verified for the curated hall, /explore for everything.
  if (verifiedFilter.value) {
    if (router.currentRoute.value.path !== '/verified') {
      router.replace({ name: 'Verified' })
    }
  } else if (router.currentRoute.value.path !== '/explore') {
    router.replace({ name: 'Explore' })
  }
  refresh()
}

watch(
  () => props.verifiedOnly,
  (next) => {
    if (verifiedFilter.value !== next) {
      verifiedFilter.value = next
      refresh()
    }
  },
)

const refresh = async () => {
  loading.value = true
  error.value = ''
  // Reset card refs so the observer doesn't try to fade in elements from
  // the previous page. The :ref callback will repopulate the array.
  galleryCardRefs.value = []
  try {
    const page = await loadPage(0)
    items.value = page.data
    total.value = page.total
    hasMore.value = page.hasMore
    forkErrors.value = {}
  } catch (err) {
    error.value =
      err?.response?.data?.error || err?.message || 'Failed to load gallery'
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  try {
    const page = await loadPage(items.value.length)
    const seen = new Set(items.value.map((item) => item.simulation_id))
    for (const incoming of page.data) {
      if (!seen.has(incoming.simulation_id)) items.value.push(incoming)
    }
    total.value = page.total
    hasMore.value = page.hasMore
  } catch (err) {
    error.value =
      err?.response?.data?.error || err?.message || 'Failed to load more'
  } finally {
    loadingMore.value = false
  }
}

const forkAndOpen = async (item) => {
  if (forkingId.value) return
  forkingId.value = item.simulation_id
  forkErrors.value = { ...forkErrors.value, [item.simulation_id]: '' }
  try {
    const res = await forkSimulation({
      parent_simulation_id: item.simulation_id,
    })
    if (!res?.success) {
      throw new Error(res?.error || 'Fork failed')
    }
    const newId = res.data?.simulation_id
    if (!newId) throw new Error('Fork did not return a simulation_id')
    router.push({ name: 'SimulationRun', params: { simulationId: newId } })
  } catch (err) {
    forkErrors.value = {
      ...forkErrors.value,
      [item.simulation_id]:
        err?.response?.data?.error || err?.message || 'Fork failed',
    }
  } finally {
    forkingId.value = ''
  }
}

onMounted(refresh)
</script>

<style scoped>
.explore-container {
  min-height: 100vh;
  background: var(--background);
  font-family: var(--font-display);
  color: var(--foreground);
}

/* ── Nav (refonte Playful & Soft, miroir de Home.vue US-044b) ── */
.navbar {
  height: 56px;
  background: var(--ms-bg, #FAF7F2);
  color: var(--ms-text, #2A2A35);
  border-bottom: 1px solid var(--ms-border, rgba(42, 42, 53, 0.08));
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--ms-space-6, 24px);
  /* Réserve la place du LanguageSwitcher floating top-right */
  padding-inline-end: 110px;
}

.nav-brand {
  font-family: var(--ms-font-display, 'Outfit'), sans-serif;
  font-weight: 600;
  letter-spacing: 0.06em;
  font-size: 16px;
  text-transform: uppercase;
  color: var(--ms-text, #2A2A35);
  text-decoration: none;
  transition: color 200ms;
}
.nav-brand:hover { color: var(--ms-orange, #FF8551); }

.nav-links {
  display: flex;
  align-items: center;
  gap: var(--ms-space-3, 12px);
}

.nav-link {
  color: var(--ms-text-muted, #6B6B7D);
  text-decoration: none;
  font-family: var(--ms-font-body, 'Manrope'), sans-serif;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 6px 12px;
  border-radius: var(--ms-radius-pill, 999px);
  transition: color 200ms, background 200ms;
  background: transparent;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.nav-link:hover {
  color: var(--ms-text, #2A2A35);
  background: var(--ms-bg-muted, #F2EEE6);
}
.nav-link.router-link-active {
  color: var(--ms-orange, #FF8551);
}

.arrow { font-family: sans-serif; }

/* ── Main Content ── */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-2xl) var(--space-lg) var(--space-xl);
}

/* ── Header ── */
.explore-header {
  margin-bottom: var(--space-xl);
  max-width: 780px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  font-family: var(--font-mono);
  font-size: 13px;
}

.orange-tag {
  background: var(--color-orange);
  color: var(--color-white);
  padding: 4px var(--space-sm);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 700;
}

.meta-sep { color: rgba(10, 10, 10, 0.35); }
.meta-text { color: rgba(10, 10, 10, 0.7); }

.page-title {
  font-family: var(--font-display);
  font-size: 52px;
  line-height: 1.1;
  margin-bottom: var(--space-md);
  letter-spacing: -0.5px;
}

.page-subtitle {
  font-size: 17px;
  line-height: 1.55;
  color: rgba(10, 10, 10, 0.7);
  margin-bottom: var(--space-lg);
}

.stats-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.stat-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 6px 12px;
  background: var(--color-gray);
  border: var(--border-light);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.5px;
}

.stat-num {
  font-weight: 700;
  font-size: 16px;
  color: var(--color-orange);
}

.stat-label {
  color: rgba(10, 10, 10, 0.5);
  text-transform: uppercase;
}

.refresh-btn {
  padding: 6px 12px;
  background: transparent;
  border: var(--border-medium);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.5px;
  color: rgba(10, 10, 10, 0.7);
  cursor: pointer;
  transition: var(--transition-fast);
}

.refresh-btn:hover:not(:disabled) {
  color: var(--color-orange);
  border-color: var(--color-orange);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Loading skeleton ──
   Builds on `.ms-skeleton` from src/styles/components.css — that class
   already handles the shimmer keyframes + `prefers-reduced-motion` opt-out,
   so we only style sizes / layout here. */
.gallery-loading { margin-top: var(--space-lg); }

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-md);
}

.skeleton-card {
  display: flex;
  flex-direction: column;
  border: var(--border-light);
  background: var(--color-white);
}

.skeleton-thumb {
  aspect-ratio: 1200 / 630;
  width: 100%;
  border-radius: 0;
}

.skeleton-body {
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  flex: 1;
}

.skeleton-line {
  height: 14px;
  border-radius: 3px;
}
.skeleton-line-title { width: 90%; height: 18px; }
.skeleton-line-title-short { width: 60%; height: 18px; }
.skeleton-line-meta { width: 70%; height: 11px; }

.skeleton-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.skeleton-pill {
  height: 18px;
  width: 64px;
  border-radius: 2px;
}

.skeleton-bar {
  height: 6px;
  width: 100%;
  border-radius: 3px;
}

.skeleton-actions {
  display: flex;
  gap: var(--space-xs);
  margin-top: auto;
  padding-top: var(--space-sm);
}

.skeleton-btn {
  height: 32px;
  flex: 1;
  border-radius: 2px;
}

/* ── Error ── */
.gallery-error,
.gallery-empty {
  padding: var(--space-2xl) var(--space-lg);
  border: var(--border-medium);
  text-align: center;
  max-width: 540px;
  margin: var(--space-xl) auto;
}

.error-icon,
.empty-icon {
  font-size: 32px;
  color: var(--color-orange);
  margin-bottom: var(--space-sm);
}

.error-title,
.empty-title {
  font-family: var(--font-display);
  font-size: 22px;
  margin-bottom: var(--space-sm);
}

.error-msg,
.empty-msg {
  color: rgba(10, 10, 10, 0.65);
  font-size: 15px;
  line-height: 1.5;
  margin-bottom: var(--space-md);
}

.error-retry,
.empty-cta {
  display: inline-block;
  padding: 10px 20px;
  background: var(--color-orange);
  color: var(--color-white);
  border: none;
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 1px;
  text-transform: uppercase;
  text-decoration: none;
  cursor: pointer;
  transition: var(--transition-fast);
}

.error-retry:hover,
.empty-cta:hover {
  background: var(--color-black);
}

/* ── Grid ── */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-md);
  margin-top: var(--space-md);
}

.gallery-card {
  background: var(--color-white);
  border: var(--border-light);
  display: flex;
  flex-direction: column;
  transition: var(--transition-medium);
  /* Initial state for the scroll-triggered fade-in. The
     `useScrollFadeIn` composable adds .ms-anim-fade-in once the card
     enters the viewport, which runs the global ms-fade-in keyframes. */
  opacity: 0;
}

.gallery-card.ms-anim-fade-in {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  /* Reduced-motion users get no animation — but they still need to see
     the cards, so force them visible up-front. */
  .gallery-card { opacity: 1; }
}

.gallery-card:hover {
  border-color: var(--color-orange);
  transform: translateY(-2px);
}

.card-resolved {
  border-inline-start: 3px solid var(--color-green);
}

/* ── Thumbnail ── */
.card-thumb-link {
  display: block;
  position: relative;
  aspect-ratio: 1200 / 630;
  background: var(--color-black);
  overflow: hidden;
}

.card-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: var(--transition-medium);
}

.gallery-card:hover .card-thumb {
  transform: scale(1.015);
}

.card-thumb-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 60%,
    rgba(10, 10, 10, 0.15) 100%
  );
  pointer-events: none;
}

/* ── Card body ── */
.card-body {
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  flex: 1;
}

.card-scenario {
  font-family: var(--font-display);
  font-size: 18px;
  line-height: 1.3;
  letter-spacing: -0.2px;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: calc(18px * 1.3 * 2);
}

.card-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  font-weight: 600;
  border-radius: 2px;
}

.pill-bullish {
  background: rgba(67, 193, 101, 0.15);
  color: #2a8545;
}

.pill-bearish {
  background: rgba(255, 68, 68, 0.14);
  color: #c52d2d;
}

.pill-neutral {
  background: rgba(10, 10, 10, 0.08);
  color: rgba(10, 10, 10, 0.7);
}

.pill-quality-excellent {
  background: rgba(67, 193, 101, 0.15);
  color: #2a8545;
}

.pill-quality-good {
  background: rgba(67, 193, 101, 0.1);
  color: #2a8545;
}

.pill-quality-fair {
  background: rgba(255, 179, 71, 0.18);
  color: #a66414;
}

.pill-quality-poor {
  background: rgba(255, 68, 68, 0.14);
  color: #c52d2d;
}

.pill-quality-unknown {
  background: rgba(10, 10, 10, 0.06);
  color: rgba(10, 10, 10, 0.5);
}

.pill-resolved {
  background: var(--color-green);
  color: var(--color-white);
}

.pill-status {
  background: rgba(10, 10, 10, 0.06);
  color: rgba(10, 10, 10, 0.55);
}

/* Verified-prediction pills — slightly stronger visual weight than the
   generic pills so the credibility signal lands at a glance. */
.pill-verified {
  text-decoration: none;
  cursor: default;
  letter-spacing: 0.6px;
}

a.pill-verified {
  cursor: pointer;
}

a.pill-verified:hover {
  filter: brightness(0.92);
}

.pill-verified-correct {
  background: var(--color-orange);
  color: var(--color-white);
}

.pill-verified-incorrect {
  background: rgba(255, 68, 68, 0.18);
  color: #c52d2d;
  outline: 1px solid rgba(255, 68, 68, 0.35);
  outline-offset: -1px;
}

.pill-verified-partial {
  background: rgba(255, 179, 71, 0.22);
  color: #8a4a0a;
  outline: 1px solid rgba(255, 179, 71, 0.5);
  outline-offset: -1px;
}

/* Card-level accent strip — same idea as .card-resolved (a thin coloured
   left border) but using the outcome palette so the verified hall reads
   at a glance even when scrolling fast. */
.card-verified-correct {
  border-inline-start: 3px solid var(--color-orange);
}

.card-verified-incorrect {
  border-inline-start: 3px solid var(--color-red);
}

.card-verified-partial {
  border-inline-start: 3px solid #f59e0b;
}

/* Filter chip in the stats row — toggles `?verified=1`. Active state
   leans on the brand orange so it reads as the primary call-to-action
   when an operator is hunting for credibility-anchored sims. */
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: var(--border-medium);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.5px;
  color: rgba(10, 10, 10, 0.7);
  cursor: pointer;
  transition: var(--transition-fast);
  text-transform: uppercase;
}

.filter-chip:hover:not(:disabled) {
  border-color: var(--color-orange);
  color: var(--color-orange);
}

.filter-chip-active {
  background: var(--color-orange);
  border-color: var(--color-orange);
  color: var(--color-white);
}

.filter-chip-active:hover:not(:disabled) {
  background: var(--color-black);
  border-color: var(--color-black);
  color: var(--color-white);
}

.filter-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filter-chip-icon {
  font-family: sans-serif;
}

.inline-link {
  color: var(--color-orange);
  text-decoration: none;
  font-weight: 600;
}

.inline-link:hover {
  text-decoration: underline;
}

/* ── Consensus bar ── */
.consensus-bar {
  display: flex;
  height: 6px;
  background: rgba(10, 10, 10, 0.06);
  overflow: hidden;
  border-radius: 3px;
}

.bar-seg { height: 100%; transition: width 0.2s ease; }
.bar-bullish { background: var(--color-green); }
.bar-neutral { background: rgba(10, 10, 10, 0.3); }
.bar-bearish { background: var(--color-red); }

/* ── Metadata ── */
.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: rgba(10, 10, 10, 0.55);
  letter-spacing: 0.3px;
  flex-wrap: wrap;
}

.meta-item {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}

.meta-label {
  text-transform: uppercase;
  color: rgba(10, 10, 10, 0.4);
}

.meta-val {
  color: rgba(10, 10, 10, 0.75);
  font-weight: 600;
}

/* ── Actions ── */
.card-actions {
  display: flex;
  gap: var(--space-xs);
  margin-top: auto;
  padding-top: var(--space-sm);
  border-top: 1px solid rgba(10, 10, 10, 0.06);
}

.action-btn {
  flex: 1;
  padding: 8px 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
  text-decoration: none;
  text-align: center;
  border: var(--border-light);
  background: transparent;
  color: rgba(10, 10, 10, 0.75);
  cursor: pointer;
  transition: var(--transition-fast);
  font-weight: 600;
}

.action-view:hover {
  background: var(--color-black);
  color: var(--color-white);
  border-color: var(--color-black);
}

.action-fork {
  background: var(--color-orange);
  color: var(--color-white);
  border-color: var(--color-orange);
}

.action-fork:hover:not(:disabled) {
  background: var(--color-black);
  border-color: var(--color-black);
}

.action-fork:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fork-error {
  margin-top: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: #c52d2d;
  line-height: 1.4;
}

/* ── Load more ── */
.load-more-row {
  display: flex;
  justify-content: center;
  margin-top: var(--space-xl);
}

.load-more-btn {
  padding: 12px 32px;
  background: transparent;
  border: var(--border-medium);
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: rgba(10, 10, 10, 0.75);
  cursor: pointer;
  transition: var(--transition-fast);
  font-weight: 600;
}

.load-more-btn:hover:not(:disabled) {
  background: var(--color-black);
  color: var(--color-white);
  border-color: var(--color-black);
}

.load-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Footer ── */
.explore-footer {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-lg);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: rgba(10, 10, 10, 0.4);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.5px;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: rgba(10, 10, 10, 0.08);
}

.footer-text { white-space: nowrap; }

/* ── Responsive ── */
@media (max-width: 720px) {
  .page-title { font-size: 36px; }
  .page-subtitle { font-size: 15px; }
  .main-content { padding: var(--space-xl) var(--space-md); }
  .gallery-grid { grid-template-columns: 1fr; }
}
</style>
