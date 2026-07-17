<template>
  <div v-if="shouldRender" class="tt-wrap">
    <div class="tt-head">
      <span class="tt-label">
        <span class="tt-dot">◉</span> {{ $t('trending.label') }}
        <span class="tt-sub">{{ statusLine }}</span>
      </span>
      <button
        v-if="!loading"
        class="tt-refresh"
        type="button"
        :title="$t('trending.refreshTitle')"
        @click="refresh"
      >
↻
</button>
    </div>

    <div v-if="loading && items.length === 0" class="tt-loading">
      <span class="tt-spinner"></span>
      {{ $t('trending.loading') }}
    </div>

    <div v-else-if="items.length > 0" class="tt-grid">
      <button
        v-for="(item, idx) in items"
        :key="item.url"
        type="button"
        class="tt-card"
        :disabled="busy"
        :title="item.title"
        @click="select(item, idx)"
      >
        <div class="tt-card-head">
          <span class="tt-source">{{ item.source_name }}</span>
          <span v-if="item.published_at" class="tt-time">
            {{ relativeTime(item.published_at) }}
          </span>
        </div>
        <div class="tt-title">{{ item.title }}</div>
        <div class="tt-cta">
          <span class="tt-cta-text">{{ $t('trending.simulate') }}</span>
          <span class="tt-cta-arrow">→</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup>
/**
 * TrendingTopics
 *
 * Renders the 5 most recent items from a configurable list of RSS/Atom feeds
 * (Reuters tech, The Verge, Hacker News, CoinDesk by default — operator can
 * override with TRENDING_FEEDS). Each card is a one-click jumping-off point:
 * the parent receives a `select` event with the URL and is expected to
 * push it into the same fetch + scenario-suggest pipeline that powers the
 * URL Import box.
 *
 * Designed to be silently absent when nothing is available — if every feed
 * errors, the API returns an empty `items` array and this component renders
 * nothing rather than a broken-looking placeholder.
 */

import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getTrendingTopics } from '../api/simulation'

const { t } = useI18n()

const props = defineProps({
  // When true, the parent has an active fetch underway and we should
  // disable card clicks to avoid stacking concurrent URL fetches.
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

const items = ref([])
const loading = ref(false)
const fetchedAt = ref(null)
const cached = ref(false)
const errored = ref(false)

const shouldRender = computed(() => {
  if (loading.value) return true
  return items.value.length > 0
})

const statusLine = computed(() => {
  if (loading.value) return t('trending.subFetching')
  if (!fetchedAt.value) return ''
  const ago = relativeTime(fetchedAt.value)
  return cached.value
    ? t('trending.subCached', { ago })
    : t('trending.subRefreshed', { ago })
})

const relativeTime = (iso) => {
  if (!iso) return ''
  // Local var name shadowed `t` from useI18n() in earlier versions; renamed
  // to `ts` so the i18n translator stays accessible inside this function.
  const ts = Date.parse(iso)
  if (Number.isNaN(ts)) return ''
  const diffSec = Math.max(0, Math.floor((Date.now() - ts) / 1000))
  if (diffSec < 60) return t('trending.time.justNow')
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return t('trending.time.minAgo', { n: diffMin })
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return t('trending.time.hAgo', { n: diffHr })
  const diffDay = Math.floor(diffHr / 24)
  return t('trending.time.dAgo', { n: diffDay })
}

const load = async ({ force = false } = {}) => {
  loading.value = true
  errored.value = false
  // Vite serves the page before Flask is fully warm — a single fetch
  // on mount often returns nothing, leaving the panel empty until the
  // user manually refreshes. Retry a few times on cold boot.
  const delays = force ? [0] : [0, 750, 1500, 3000]
  try {
    for (let i = 0; i < delays.length; i++) {
      if (delays[i]) await new Promise(r => setTimeout(r, delays[i]))
      try {
        const res = await getTrendingTopics({ refresh: force })
        if (res && res.success !== false) {
          const data = res.data || {}
          const list = Array.isArray(data.items) ? data.items : []
          if (list.length > 0 || i === delays.length - 1) {
            items.value = list
            fetchedAt.value = data.fetched_at || new Date().toISOString()
            cached.value = !!data.cached
            return
          }
        }
      } catch (_) {
        if (i === delays.length - 1) {
          items.value = []
          errored.value = true
        }
      }
    }
  } finally {
    loading.value = false
  }
}

const refresh = () => {
  if (loading.value) return
  load({ force: true })
}

const select = (item, idx) => {
  if (props.busy) return
  emit('select', { url: item.url, title: item.title, source: item.source_name, index: idx })
}

onMounted(() => {
  load()
})
</script>

<style scoped>
/* ─── Warm Intelligence refresh (US-053) ───
   TrendingTopics : container cream avec header label « ◉ À la une »,
   grille cards warm avec line-clamp 2, CTA terracotta ghost,
   refresh button icon ghost. */
.tt-wrap {
  margin-top: var(--wi-space-md);
  padding: var(--wi-space-md);
  background: var(--wi-bg);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  font-family: var(--wi-font-body);
  position: relative;
  box-shadow: var(--wi-shadow-sm);
}

.tt-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--wi-space-sm);
}

.tt-label {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
  color: var(--wi-on-bg);
  display: flex;
  align-items: center;
  gap: 8px;
}

.tt-dot {
  color: var(--wi-primary-container);
  font-size: 14px;
}

.tt-sub {
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
}

.tt-refresh {
  background: transparent;
  border: 1px solid transparent;
  color: var(--wi-on-surface-variant);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--wi-radius-pill);
  transition: background var(--ms-transition-fast),
              color var(--ms-transition-fast);
}

.tt-refresh:hover {
  color: var(--wi-primary);
  background: var(--wi-surface-container-high);
}

.tt-loading {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  letter-spacing: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: var(--wi-space-sm);
  background: var(--wi-surface-container-low);
  border-radius: var(--wi-radius-md);
}

.tt-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--wi-primary-soft);
  border-top-color: var(--wi-primary-container);
  border-radius: 50%;
  display: inline-block;
  animation: tt-spin 0.8s linear infinite;
}

@keyframes tt-spin {
  to { transform: rotate(360deg); }
}

.tt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--wi-space-sm);
}

.tt-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-sm);
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
  text-align: start;
  font-family: inherit;
  transition: transform var(--ms-transition),
              box-shadow var(--ms-transition),
              border-color var(--ms-transition);
  min-height: 130px;
  box-shadow: var(--wi-shadow-sm);
}

.tt-card:hover:not(:disabled) {
  border-color: var(--wi-primary-container);
  transform: translateY(-2px);
  box-shadow: var(--wi-shadow-orange);
}

.tt-card:hover:not(:disabled) .tt-cta {
  background: var(--wi-on-primary-container);
  color: var(--wi-on-primary);
  border-color: var(--wi-on-primary-container);
}

.tt-card:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.tt-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-family: var(--wi-font-body);
}

.tt-source {
  font-weight: 500;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  letter-spacing: 0;
  text-transform: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60%;
}

.tt-time {
  font-size: var(--wi-caption);
  color: var(--wi-outline);
  letter-spacing: 0;
  text-transform: none;
  flex-shrink: 0;
}

.tt-title {
  font-family: var(--wi-font-body);
  font-weight: 600;
  font-size: 14px;
  color: var(--wi-on-surface);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.tt-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: auto;
  align-self: flex-start;
  font-family: var(--wi-font-heading);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
  color: var(--wi-on-primary-container);
  border: 1px solid var(--wi-on-primary-container);
  background: transparent;
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  transition: background var(--ms-transition-fast),
              color var(--ms-transition-fast),
              border-color var(--ms-transition-fast);
}

.tt-cta-arrow {
  font-family: var(--wi-font-body);
  font-size: 13px;
}
</style>
