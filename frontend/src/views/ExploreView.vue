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

    <main class="main-content">
      <!-- ───────────── Hero & Search ───────────── -->
      <section class="explore-hero">
        <span class="hero-eyebrow">
          {{ verifiedOnly ? '📍 ' + $t('explore.header.verified') : '◎ ' + $t('explore.header.title') }}
        </span>
        <h1 class="hero-title">
          {{ verifiedOnly
            ? $t('explore.header.verified')
            : 'Simulations en cours et passées' }}
        </h1>
        <p class="hero-subtitle">
          <template v-if="verifiedOnly">
            Chaque carte est une simulation Bassira publique dont l'opérateur a
            confirmé l'issue réelle. Survolez l'étiquette pour la source,
            ouvrez-en une pour voir la formation du consensus, ou forkez-la
            pour tester la même population d'agents sur un nouveau scénario.
          </template>
          <template v-else>
            Chaque carte est une simulation Bassira réelle, publiée par un
            décideur. Ouvrez-en une pour voir la dérive des croyances, le
            réseau d'agents et l'issue prédite — ou forkez-la en un clic
            pour relancer votre propre variante.
          </template>
        </p>

        <!-- Search bar -->
        <div class="hero-search">
          <span class="hero-search-icon" aria-hidden="true">⌕</span>
          <input
            v-model="searchQuery"
            type="search"
            class="hero-search-input"
            :placeholder="$t('explore.filters.search')"
            :aria-label="$t('explore.filters.search')"
          />
        </div>
      </section>

      <!-- ───────────── Filters & Sort ───────────── -->
      <section class="filters-bar">
        <div class="filter-chips">
          <button
            class="cat-chip cat-chip-verified"
            :class="{ 'cat-chip-active': verifiedFilter }"
            @click="toggleVerifiedFilter"
            :disabled="loading"
            :title="verifiedFilter ? $t('explore.header.title') : $t('explore.header.verified')"
          >
            <span class="cat-chip-icon" aria-hidden="true">📍</span>
            <span>{{ $t('explore.filters.verified') }}</span>
          </button>

          <button
            v-for="cat in CATEGORIES"
            :key="cat.id"
            class="cat-chip"
            :class="['cat-chip-' + cat.id, { 'cat-chip-active': categoryFilter === cat.id }]"
            @click="toggleCategory(cat.id)"
            :title="cat.label"
          >
            <span class="cat-chip-icon" aria-hidden="true">{{ cat.glyph }}</span>
            <span>{{ cat.label }}</span>
          </button>
        </div>

        <div class="filters-right">
          <span class="stat-chip" v-if="!loading">
            <span class="stat-num">{{ total }}</span>
            <span class="stat-label">{{ verifiedOnly ? 'verified' : 'published' }}</span>
          </span>
          <span v-if="!verifiedOnly && !loading && items.length > 0" class="stat-chip">
            <span class="stat-num">{{ resolvedCount }}</span>
            <span class="stat-label">resolved</span>
          </span>

          <div class="sort-wrapper">
            <select
              v-model="sortBy"
              class="sort-select"
              :aria-label="$t('explore.filters.sortBy')"
            >
              <option value="recent">{{ $t('explore.filters.newest') }}</option>
              <option value="oldest">{{ $t('explore.filters.oldest') }}</option>
              <option value="popular">{{ $t('explore.filters.popular') }}</option>
            </select>
            <span class="sort-caret" aria-hidden="true">⌄</span>
          </div>

          <button
            class="refresh-btn"
            @click="refresh"
            :disabled="loading"
            :title="$t('common.retry')"
          >
            <span v-if="loading">…</span>
            <span v-else>↻</span>
          </button>
        </div>
      </section>

      <!-- Loading skeletons — uses .ms-skeleton (shimmer + reduced-motion
           handling) from src/styles/components.css. -->
      <section v-if="loading && items.length === 0" class="gallery-loading">
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
      </section>

      <!-- Error -->
      <section v-else-if="error" class="gallery-error">
        <div class="error-icon" aria-hidden="true">⚠</div>
        <div class="error-title">{{ $t('explore.error') }}</div>
        <div class="error-msg">{{ error }}</div>
        <button class="error-retry" @click="refresh">{{ $t('common.retry') }}</button>
      </section>

      <!-- Empty — illustré et inviting -->
      <section v-else-if="filteredItems.length === 0" class="gallery-empty">
        <div class="empty-illustration" aria-hidden="true">
          <span class="empty-glyph empty-glyph-1">◇</span>
          <span class="empty-glyph empty-glyph-2">◎</span>
          <span class="empty-glyph empty-glyph-3">◈</span>
        </div>
        <div class="empty-title">
          <template v-if="searchQuery || categoryFilter">
            Aucun résultat pour ces filtres
          </template>
          <template v-else>
            {{ $t('explore.empty') }}
          </template>
        </div>
        <div class="empty-msg">
          <template v-if="searchQuery || categoryFilter">
            Essayez d'élargir votre recherche ou
            <button class="inline-link inline-link-button" @click="clearFilters">
              réinitialisez les filtres
            </button>
            pour voir toutes les simulations publiées.
          </template>
          <template v-else-if="verifiedFilter">
            Une simulation rejoint cet espace dès qu'un opérateur confirme son
            issue depuis la fenêtre d'intégration. En attendant, parcourez
            toutes les simulations publiées sur
            <router-link to="/explore" class="inline-link">/explore</router-link>.
          </template>
          <template v-else>
            Bassira est en early access institutionnel. Les simulations
            publiques apparaîtront ici à mesure que nos partenaires acceptent
            de les rendre visibles. En attendant, parcourez nos cas d'usage
            par secteur ou demandez une démonstration ciblée sur votre
            scénario.
          </template>
        </div>
        <router-link
          v-if="!searchQuery && !categoryFilter"
          :to="verifiedFilter ? '/explore' : '/landing'"
          class="empty-cta"
        >
          {{ verifiedFilter ? 'Voir toutes les simulations →' : 'Voir les cas d\'usage par secteur →' }}
        </router-link>
        <button
          v-else
          class="empty-cta"
          @click="clearFilters"
        >
          Réinitialiser les filtres →
        </button>
      </section>

      <!-- Grid -->
      <section v-else class="gallery-grid">
        <article
          v-for="(item, idx) in filteredItems"
          :key="item.simulation_id"
          :ref="el => setGalleryCardRef(el, idx)"
          class="gallery-card ms-card"
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
            <span
              v-if="categoryOf(item)"
              class="card-category"
              :class="'card-category-' + categoryOf(item).id"
            >
              <span class="card-category-glyph" aria-hidden="true">
                {{ categoryOf(item).glyph }}
              </span>
              {{ categoryOf(item).label }}
            </span>

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
      </section>

      <!-- Load more -->
      <div v-if="filteredItems.length > 0 && hasMore" class="load-more-row">
        <button
          class="load-more-btn"
          @click="loadMore"
          :disabled="loadingMore"
        >
          <span v-if="loadingMore">{{ $t('explore.loading') }}</span>
          <span v-else>{{ $t('explore.loadMore') }} ({{ total - items.length }})</span>
        </button>
      </div>
    </main>

    <footer class="explore-footer">
      <span class="footer-line"></span>
      <span class="footer-text">
        Lancez une simulation, ouvrez la fenêtre d'intégration, activez « Public ».
      </span>
      <span class="footer-line"></span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

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

// ── Refonte Stitch : recherche, catégorie, tri ─────────────────────
// Filtrage / tri appliqués côté client sur les items déjà chargés.
// Le fetch backend reste piloté par verifiedFilter pour préserver la
// pagination existante.
const searchQuery = ref('')
const categoryFilter = ref('') // '' | 'crisis' | 'market' | 'policy' | 'decision'
const sortBy = ref('recent')   // 'recent' | 'oldest' | 'popular'

// Catégories alignées sur le design Stitch (4 chips colorés).
// Le glyphe ASCII évite la dépendance Material Symbols dans la vue.
const CATEGORIES = [
  { id: 'crisis',   label: 'Crisis',   glyph: '◬', match: /(crisis|crise|tension|conflict|conflit|guerre|attaque|sanction|embarg)/i },
  { id: 'market',   label: 'Market',   glyph: '▲', match: /(market|marché|prix|price|adoption|demand|offre|vente|stock|action|trade|tarif|inflation|petrole|pétrole|véhicule|vehicule|énerg|energ)/i },
  { id: 'policy',   label: 'Policy',   glyph: '§', match: /(policy|politique|réglementation|reglementation|loi|law|tax|taxe|cbam|carbone|fiscal|réforme|reforme|régulation|regulation)/i },
  { id: 'decision', label: 'Decision', glyph: '◇', match: /(decision|décision|stratégie|strategy|arbitrage|choix|allocation|priorit|gouvernance)/i },
]

const categoryOf = (item) => {
  const text = String(item?.scenario || '').toLowerCase()
  if (!text) return null
  for (const cat of CATEGORIES) {
    if (cat.match.test(text)) return cat
  }
  return null
}

const toggleCategory = (id) => {
  categoryFilter.value = categoryFilter.value === id ? '' : id
}

const clearFilters = () => {
  searchQuery.value = ''
  categoryFilter.value = ''
}

// Items affichés : items chargés filtrés par search + category, triés.
// On préserve la liste source `items` pour ne pas perturber pagination
// (`total - items.length` reste juste pour le bouton "Charger plus").
const filteredItems = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const cat = categoryFilter.value
  let result = items.value
  if (q) {
    result = result.filter((it) =>
      String(it.scenario || '').toLowerCase().includes(q),
    )
  }
  if (cat) {
    result = result.filter((it) => categoryOf(it)?.id === cat)
  }
  if (sortBy.value === 'oldest') {
    result = [...result].sort((a, b) =>
      String(a.created_at || '').localeCompare(String(b.created_at || '')),
    )
  } else if (sortBy.value === 'popular') {
    result = [...result].sort(
      (a, b) => (b.agent_count || 0) - (a.agent_count || 0),
    )
  }
  // 'recent' = ordre du backend (déjà trié desc) → pas de re-tri.
  return result
})

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
/* ═══════════════════════════════════════════════════════════
   ExploreView — Refonte Stitch « Bassira Galerie Explore »
   Tokens : --wi-* (Warm Intelligence) sur fond cream museum.
   Audience : prospect cold (LinkedIn / referral). Objectif
   cognitif : social proof + curiosité.
   ═══════════════════════════════════════════════════════ */
.explore-container {
  min-height: 100vh;
  background: var(--wi-bg);
  font-family: var(--wi-font-body);
  color: var(--wi-on-bg);
}

/* ── Nav (miroir de Home.vue US-044b, palette --wi-*) ── */
.navbar {
  height: 64px;
  background: rgba(255, 248, 246, 0.9);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  color: var(--wi-on-bg);
  border-bottom: 1px solid var(--wi-outline-variant);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--wi-space-md);
  position: sticky;
  top: 0;
  z-index: var(--ms-z-sticky, 950);
  /* Réserve la place du LanguageSwitcher floating top-right */
  padding-inline-end: 110px;
}

.nav-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  letter-spacing: -0.02em;
  font-size: 22px;
  color: var(--wi-on-bg);
  text-decoration: none;
  transition: color var(--ms-transition);
}
.nav-brand:hover { color: var(--wi-primary); }

.nav-links {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
}

.nav-link {
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 500;
  padding: 8px 14px;
  border-radius: var(--wi-radius-interactive);
  transition: color var(--ms-transition), background var(--ms-transition);
  background: transparent;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.nav-link:hover {
  color: var(--wi-on-bg);
  background: var(--wi-surface-container-low);
}
.nav-link.router-link-active {
  color: var(--wi-primary);
}

.github-link {
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 500;
  padding: 8px 14px;
  border-radius: var(--wi-radius-interactive);
  transition: color var(--ms-transition), background var(--ms-transition);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.github-link:hover {
  color: var(--wi-on-bg);
  background: var(--wi-surface-container-low);
}

.arrow { font-family: sans-serif; }

/* ── Main Content (max-width: container Stitch 1280px) ── */
.main-content {
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  padding: var(--wi-space-xl) var(--wi-gutter);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xl);
}

/* ── Hero & Search ── */
.explore-hero {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
  align-items: center;
  text-align: center;
  max-width: 768px;
  margin: 0 auto;
  padding-top: var(--wi-space-md);
}

.hero-eyebrow {
  font-family: var(--wi-font-body);
  font-size: var(--wi-label-sm);
  font-weight: 600;
  color: var(--wi-primary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.hero-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  font-weight: var(--wi-h1-weight);
  line-height: var(--wi-h1-leading);
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-on-bg);
  margin: 0;
}

.hero-subtitle {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-lg);
  line-height: var(--wi-body-lg-leading);
  color: var(--wi-on-surface-variant);
  margin: 0;
  max-width: 640px;
}

.hero-search {
  width: 100%;
  position: relative;
  margin-top: var(--wi-space-sm);
}

.hero-search-icon {
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--wi-outline);
  font-size: 20px;
  pointer-events: none;
}

.hero-search-input {
  width: 100%;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  padding: 16px 16px 16px 48px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-lg);
  color: var(--wi-on-surface);
  box-shadow: var(--wi-shadow-sm);
  transition: border-color var(--ms-transition), box-shadow var(--ms-transition);
}

.hero-search-input::placeholder {
  color: var(--wi-outline);
}

.hero-search-input:focus {
  outline: none;
  border-color: var(--wi-primary);
  box-shadow: 0 0 0 3px var(--wi-shadow-md), 0 0 0 3px rgba(161, 63, 15, 0.12);
}

/* ── Filters & Sort ── */
.filters-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--wi-space-sm);
  padding-bottom: var(--wi-space-sm);
  border-bottom: 1px solid var(--wi-outline-variant);
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* Catégories — chips bordurés colorés selon la nature du sujet.
   Couleurs alignées sur la spec : Crisis = terracotta clair (--wi-on-primary-container),
   Market = orange Bassira (--wi-primary-container), Policy = mint (--wi-secondary),
   Decision = charcoal (--wi-on-bg, inversion sur fond cream). */
.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--wi-surface);
  border: 1px solid currentColor;
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-body);
  font-size: var(--wi-label-sm);
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: background var(--ms-transition), color var(--ms-transition),
    transform var(--ms-transition-fast);
}

.cat-chip-icon {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1;
}

.cat-chip:hover { transform: translateY(-1px); }

.cat-chip-crisis   { color: var(--wi-on-primary-container); }
.cat-chip-market   { color: var(--wi-primary-container); }
.cat-chip-policy   { color: var(--wi-secondary); }
.cat-chip-decision { color: var(--wi-on-bg); }
.cat-chip-verified { color: var(--wi-primary); }

.cat-chip-crisis:hover   { background: rgba(109, 36, 0, 0.06); }
.cat-chip-market:hover   { background: rgba(255, 133, 81, 0.08); }
.cat-chip-policy:hover   { background: rgba(0, 109, 68, 0.06); }
.cat-chip-decision:hover { background: rgba(36, 25, 21, 0.06); }
.cat-chip-verified:hover { background: rgba(161, 63, 15, 0.06); }

/* Active : chip rempli avec sa couleur, texte cream pour contraste */
.cat-chip-active.cat-chip-crisis {
  background: var(--wi-on-primary-container);
  color: var(--wi-bg);
}
.cat-chip-active.cat-chip-market {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}
.cat-chip-active.cat-chip-policy {
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
}
.cat-chip-active.cat-chip-decision {
  background: var(--wi-on-bg);
  color: var(--wi-bg);
}
.cat-chip-active.cat-chip-verified {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
}

.cat-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.filters-right {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  flex-wrap: wrap;
}

.stat-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 6px 12px;
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
}

.stat-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  font-size: var(--wi-label-sm);
  color: var(--wi-primary);
}

.stat-label {
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  font-size: var(--wi-caption);
  letter-spacing: 0.04em;
}

.sort-wrapper {
  position: relative;
}

.sort-select {
  appearance: none;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  padding: 8px 36px 8px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface);
  cursor: pointer;
  transition: border-color var(--ms-transition);
}

.sort-select:focus {
  outline: none;
  border-color: var(--wi-primary);
}

.sort-caret {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--wi-outline);
  pointer-events: none;
  font-size: 16px;
}

.refresh-btn {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  transition: color var(--ms-transition), border-color var(--ms-transition),
    background var(--ms-transition);
}

.refresh-btn:hover:not(:disabled) {
  color: var(--wi-primary);
  border-color: var(--wi-primary);
  background: rgba(161, 63, 15, 0.04);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Loading skeleton ──
   Builds on `.ms-skeleton` from src/styles/components.css — that class
   already handles the shimmer keyframes + `prefers-reduced-motion` opt-out,
   so we only style sizes / layout here. */
.gallery-loading { margin-top: var(--wi-space-md); }

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--wi-gutter);
}

.skeleton-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  background: var(--wi-surface);
  overflow: hidden;
}

.skeleton-thumb {
  aspect-ratio: 1200 / 630;
  width: 100%;
}

.skeleton-body {
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
  flex: 1;
}

.skeleton-line { height: 14px; border-radius: 4px; }
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
  border-radius: 4px;
}

.skeleton-bar { height: 6px; width: 100%; border-radius: 3px; }

.skeleton-actions {
  display: flex;
  gap: var(--wi-space-xs);
  margin-top: auto;
  padding-top: var(--wi-space-xs);
}

.skeleton-btn { height: 36px; flex: 1; border-radius: var(--wi-radius-interactive); }

/* ── Error ── */
.gallery-error,
.gallery-empty {
  padding: var(--wi-space-xl) var(--wi-space-md);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  background: var(--wi-surface-container-low);
  text-align: center;
  max-width: 560px;
  margin: var(--wi-space-md) auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--wi-space-sm);
}

.error-icon {
  font-size: 36px;
  color: var(--wi-error);
}

.error-title,
.empty-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-bg);
  margin: 0;
}

.error-msg,
.empty-msg {
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  margin: 0;
  max-width: 440px;
}

/* Empty state illustré : trois glyphes flottants en gradient terracotta/cream
   pour une atmosphère « curiosity museum », jamais clinique. */
.empty-illustration {
  position: relative;
  width: 120px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-glyph {
  position: absolute;
  font-family: 'JetBrains Mono', monospace;
  font-size: 28px;
  line-height: 1;
  opacity: 0.7;
}

.empty-glyph-1 {
  color: var(--wi-primary);
  transform: translate(-32px, -8px) rotate(-12deg);
  font-size: 32px;
}
.empty-glyph-2 {
  color: var(--wi-primary-container);
  font-size: 44px;
  z-index: 1;
}
.empty-glyph-3 {
  color: var(--wi-secondary);
  transform: translate(36px, 12px) rotate(8deg);
  font-size: 26px;
}

.error-retry,
.empty-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 24px;
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: none;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: background var(--ms-transition), box-shadow var(--ms-transition),
    transform var(--ms-transition-fast);
}

.error-retry:hover,
.empty-cta:hover {
  background: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-md);
  transform: translateY(-1px);
}

/* ── Grid ── */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--wi-gutter);
}

@media (min-width: 1024px) {
  .gallery-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.gallery-card {
  /* .ms-card apporte background/border/shadow, on override en --wi-* */
  padding: 0;
  display: flex;
  flex-direction: column;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  overflow: hidden;
  box-shadow: var(--wi-shadow-sm);
  transition: transform var(--ms-transition), box-shadow var(--ms-transition),
    border-color var(--ms-transition);
  /* Initial state pour scroll-triggered fade-in (useScrollFadeIn) */
  opacity: 0;
}

.gallery-card.ms-anim-fade-in {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .gallery-card { opacity: 1; }
}

.gallery-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--wi-shadow-orange);
  border-color: rgba(255, 133, 81, 0.4);
}

.card-resolved {
  border-left: 4px solid var(--wi-secondary);
}

/* ── Thumbnail ── */
.card-thumb-link {
  display: block;
  position: relative;
  aspect-ratio: 1200 / 630;
  background: var(--wi-surface-container-highest);
  overflow: hidden;
}

.card-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform var(--ms-transition-slow);
}

.gallery-card:hover .card-thumb {
  transform: scale(1.03);
}

.card-thumb-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 55%,
    rgba(36, 25, 21, 0.12) 100%
  );
  pointer-events: none;
}

/* ── Card body ── */
.card-body {
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

/* Badge catégorie en haut de card — couleur dérivée du type détecté.
   Forme : pilule remplie, palette --wi-* (Crisis terracotta foncé,
   Market orange, Policy mint, Decision charcoal). */
.card-category {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--wi-radius-sm);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  width: fit-content;
}

.card-category-glyph {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1;
}

.card-category-crisis {
  background: rgba(109, 36, 0, 0.10);
  color: var(--wi-on-primary-container);
}
.card-category-market {
  background: rgba(255, 133, 81, 0.18);
  color: var(--wi-primary);
}
.card-category-policy {
  background: rgba(0, 109, 68, 0.12);
  color: var(--wi-secondary);
}
.card-category-decision {
  background: var(--wi-on-bg);
  color: var(--wi-bg);
}

.card-scenario {
  font-family: var(--wi-font-heading);
  font-size: 20px;
  line-height: 1.35;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--wi-on-bg);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: calc(20px * 1.35 * 2);
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
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-weight: 600;
  border-radius: var(--wi-radius-sm);
}

.pill-bullish {
  background: rgba(0, 109, 68, 0.12);
  color: var(--wi-secondary);
}

.pill-bearish {
  background: rgba(186, 26, 26, 0.12);
  color: var(--wi-error);
}

.pill-neutral {
  background: var(--wi-surface-container-high);
  color: var(--wi-on-surface-variant);
}

.pill-quality-excellent,
.pill-quality-good {
  background: rgba(0, 109, 68, 0.12);
  color: var(--wi-secondary);
}

.pill-quality-fair {
  background: rgba(255, 179, 71, 0.18);
  color: var(--ms-status-warning-text);
}

.pill-quality-poor {
  background: rgba(186, 26, 26, 0.12);
  color: var(--wi-error);
}

.pill-quality-unknown {
  background: var(--wi-surface-container-low);
  color: var(--wi-outline);
}

.pill-resolved {
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
}

.pill-status {
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface-variant);
}

/* Verified-prediction pills — credibility signal renforcé. */
.pill-verified {
  text-decoration: none;
  cursor: default;
  letter-spacing: 0.05em;
}

a.pill-verified { cursor: pointer; }
a.pill-verified:hover { filter: brightness(0.92); }

.pill-verified-correct {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
}

.pill-verified-incorrect {
  background: rgba(186, 26, 26, 0.16);
  color: var(--wi-error);
  outline: 1px solid rgba(186, 26, 26, 0.32);
  outline-offset: -1px;
}

.pill-verified-partial {
  background: rgba(255, 179, 71, 0.22);
  color: var(--ms-status-warning-text);
  outline: 1px solid rgba(255, 179, 71, 0.5);
  outline-offset: -1px;
}

/* Card-level accent strip — bordure gauche colorée selon l'outcome. */
.card-verified-correct {
  border-left: 4px solid var(--wi-primary-container);
}

.card-verified-incorrect {
  border-left: 4px solid var(--wi-error);
}

.card-verified-partial {
  border-left: 4px solid var(--wi-primary-container);
}

.inline-link {
  color: var(--wi-primary);
  text-decoration: none;
  font-weight: 600;
}

.inline-link:hover {
  text-decoration: underline;
}

.inline-link-button {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  font-size: inherit;
  cursor: pointer;
}

/* ── Consensus bar ── */
.consensus-bar {
  display: flex;
  height: 6px;
  background: var(--wi-surface-container-high);
  overflow: hidden;
  border-radius: 3px;
}

.bar-seg { height: 100%; transition: width 0.2s ease; }
.bar-bullish { background: var(--wi-secondary); }
.bar-neutral { background: var(--wi-outline); }
.bar-bearish { background: var(--wi-error); }

/* ── Metadata ── */
.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  flex-wrap: wrap;
  padding: 8px 0;
  border-top: 1px solid var(--wi-outline-variant);
  border-bottom: 1px solid var(--wi-outline-variant);
}

.meta-item {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}

.meta-label {
  text-transform: uppercase;
  color: var(--wi-outline);
  letter-spacing: 0.04em;
}

.meta-val {
  color: var(--wi-on-bg);
  font-weight: 600;
}

.meta-sep { color: var(--wi-outline); }
.meta-text { color: var(--wi-on-surface-variant); }

/* ── Actions : ghost terracotta border → fill on hover (spec) ── */
.card-actions {
  display: flex;
  gap: var(--wi-space-xs);
  margin-top: auto;
}

.action-btn {
  flex: 1;
  padding: 10px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 600;
  letter-spacing: 0.01em;
  text-decoration: none;
  text-align: center;
  border: 1px solid var(--wi-primary);
  border-radius: var(--wi-radius-interactive);
  background: transparent;
  color: var(--wi-primary);
  cursor: pointer;
  transition: background var(--ms-transition), color var(--ms-transition),
    border-color var(--ms-transition);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.action-view:hover {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border-color: var(--wi-primary);
}

.action-fork {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border-color: var(--wi-primary);
}

.action-fork:hover:not(:disabled) {
  background: var(--wi-on-primary-container);
  border-color: var(--wi-on-primary-container);
}

.action-fork:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fork-error {
  margin-top: 6px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-error);
  line-height: 1.4;
}

/* ── Load more ── */
.load-more-row {
  display: flex;
  justify-content: center;
  margin-top: var(--wi-space-md);
}

.load-more-btn {
  padding: 12px 28px;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 600;
  color: var(--wi-on-surface);
  cursor: pointer;
  transition: background var(--ms-transition), border-color var(--ms-transition),
    box-shadow var(--ms-transition);
}

.load-more-btn:hover:not(:disabled) {
  background: var(--wi-surface-container-high);
  border-color: var(--wi-primary);
  box-shadow: var(--wi-shadow-sm);
}

.load-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Footer ── */
.explore-footer {
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  padding: var(--wi-space-md) var(--wi-gutter) var(--wi-space-lg);
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
  color: var(--wi-outline);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
}

.footer-line {
  flex: 1;
  height: 1px;
  background: var(--wi-outline-variant);
}

.footer-text { white-space: nowrap; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .hero-title { font-size: 32px; }
  .hero-subtitle { font-size: var(--wi-body-md); }
  .main-content {
    padding: var(--wi-space-md) var(--wi-space-sm);
    gap: var(--wi-space-md);
  }
  .gallery-grid { grid-template-columns: 1fr; }
  .filters-bar { flex-direction: column; align-items: stretch; }
  .filters-right { justify-content: space-between; }
}
</style>
