<template>
  <div class="replay-view">
    <!-- ─────────────────────────────────────────────────────────
         Top bar — Bassira Replay (Strategic Debrief)
         ───────────────────────────────────────────────────────── -->
    <header class="replay-topbar">
      <div class="replay-brand" @click="router.push('/')">
        <span class="brand-mark">Bassira</span>
        <span class="brand-suffix">Replay</span>
      </div>
      <div class="replay-topnav">
        <span class="topnav-link active">Timeline</span>
        <span class="topnav-link">Inflection Points</span>
        <span class="topnav-link">Round Analytics</span>
      </div>
      <button class="replay-back-btn" @click="goBack">
        <span aria-hidden="true">←</span>
        <span>{{ $t('simulation.replay.back') }}</span>
      </button>
    </header>

    <!-- ─────────────────────────────────────────────────────────
         Loading / Error states
         ───────────────────────────────────────────────────────── -->
    <div v-if="loading" class="replay-state">
      <div class="replay-pulse"></div>
      <span>{{ $t('simulation.replay.loading') }}</span>
    </div>

    <div v-else-if="error" class="replay-state replay-state-error">
      <span>{{ error }}</span>
      <button class="replay-back-btn" @click="router.push('/')">{{ $t('nav.brand') }}</button>
    </div>

    <!-- ─────────────────────────────────────────────────────────
         Main shell — sticky scrubber + canvas + side panel + footer controls
         ───────────────────────────────────────────────────────── -->
    <template v-else>
      <!-- Sticky timeline scrubber -->
      <section class="scrubber-band" aria-label="Timeline scrubber">
        <div class="scrubber-band-row">
          <div class="scrubber-round-display">
            <span class="scrubber-round-label">Round</span>
            <span class="scrubber-round-value">R-{{ currentRound }}</span>
            <span class="scrubber-round-total">/ {{ totalRounds }}</span>
          </div>

          <div class="scrubber-speed-pills" role="group" aria-label="Playback speed">
            <button
              v-for="(s, idx) in speeds"
              :key="s"
              class="speed-pill"
              :class="{ active: playbackSpeed === s }"
              @click="playbackSpeed = s"
            >
              <span>{{ s }}x</span>
              <span v-if="idx < speeds.length - 1" class="speed-pill-sep" aria-hidden="true"></span>
            </button>
          </div>
        </div>

        <!-- Timeline track with markers -->
        <div
          class="scrubber-track"
          ref="trackRef"
          @click="onTrackClick"
          @keydown="onTrackKeydown"
          tabindex="0"
          role="slider"
          :aria-valuemin="0"
          :aria-valuemax="totalRounds"
          :aria-valuenow="currentRound"
          aria-label="Round timeline scrubber"
        >
          <div class="scrubber-track-rail"></div>
          <div class="scrubber-track-fill" :style="{ width: progressPercent + '%' }"></div>

          <!-- Round markers (dots for calm, terracotta diamonds for inflection) -->
          <span
            v-for="m in trackMarkers"
            :key="m.round"
            class="scrubber-marker"
            :class="m.kind"
            :style="{ insetInlineStart: m.left + '%' }"
            :title="m.tooltip"
            aria-hidden="true"
          ></span>

          <!-- Current playhead -->
          <span
            class="scrubber-playhead"
            :style="{ insetInlineStart: progressPercent + '%' }"
            aria-hidden="true"
          ></span>

          <!-- Native range, transparent overlay for accessibility & drag -->
          <input
            type="range"
            class="scrubber-range-overlay"
            :min="0"
            :max="totalRounds"
            :value="currentRound"
            @input="onScrub"
            aria-label="Scrub timeline"
          />
        </div>
      </section>

      <!-- Canvas : narrative event + belief drift + side agent panel -->
      <section class="replay-canvas">
        <div class="canvas-center" ref="scrollContainer">
          <!-- Narrative event card — current round chapter -->
          <article class="narrative-card" :class="{ 'is-inflection': isInflectionRound }">
            <div class="narrative-card-bg" aria-hidden="true">
              <svg viewBox="0 0 120 120" width="120" height="120">
                <path d="M60 10 L100 30 L100 70 L60 110 L20 70 L20 30 Z"
                      fill="none" stroke="currentColor" stroke-width="2" />
              </svg>
            </div>

            <div class="narrative-card-meta">
              <span class="narrative-tag" :class="{ 'tag-inflection': isInflectionRound }">
                {{ isInflectionRound ? 'Inflection point' : 'Round chapter' }}
              </span>
              <span class="narrative-tag-time">R-{{ currentRound }} · {{ currentRoundClock }}</span>
            </div>

            <h2 class="narrative-card-title">{{ currentRoundTitle }}</h2>
            <p class="narrative-card-body">{{ currentRoundNarrative }}</p>

            <div v-if="currentRoundEvents.length" class="narrative-card-events">
              <span class="narrative-events-label">{{ currentRoundEvents.length }} events this round</span>
              <ul class="narrative-events-list">
                <li
                  v-for="ev in currentRoundEvents.slice(0, 4)"
                  :key="ev._uniqueId"
                  class="narrative-event-row"
                >
                  <span class="narrative-event-agent">{{ ev.agent_name || 'Agent' }}</span>
                  <span class="narrative-event-action">{{ getActionTypeLabel(ev.action_type) }}</span>
                  <span v-if="ev.action_args?.content" class="narrative-event-snippet">
                    {{ truncate(ev.action_args.content, 90) }}
                  </span>
                </li>
              </ul>
            </div>
          </article>

          <!-- Belief drift chart (live tracking with playhead) -->
          <article class="drift-card">
            <header class="drift-card-header">
              <h3 class="drift-card-title">Belief drift aggregate</h3>
              <span class="drift-card-status">
                <span class="drift-card-dot" aria-hidden="true"></span>
                Live tracking · R-{{ currentRound }}
              </span>
            </header>
            <div class="drift-card-chart-wrap">
              <BeliefDriftChart
                v-if="simulationId"
                :simulation-id="simulationId"
                :visible="true"
                class="drift-card-chart"
              />
            </div>
          </article>
        </div>

        <!-- Right side panel : agent states mini panel -->
        <aside class="agent-panel">
          <header class="agent-panel-header">
            <h3 class="agent-panel-title">Agent states</h3>
            <span class="agent-panel-count">{{ agentStates.length }} active</span>
          </header>
          <ul class="agent-list">
            <li
              v-for="agent in agentStates"
              :key="agent.id"
              class="agent-row"
            >
              <div class="agent-avatar">{{ agent.initial }}</div>
              <div class="agent-meta">
                <div class="agent-name">{{ agent.name }}</div>
                <div class="agent-tier">{{ agent.tier }}</div>
              </div>
              <span class="agent-mood" :class="`mood-${agent.mood}`">
                {{ agent.mood.toUpperCase() }}
              </span>
            </li>
            <li v-if="agentStates.length === 0" class="agent-row agent-row-empty">
              <span class="agent-meta">No agent activity yet on this round.</span>
            </li>
          </ul>
        </aside>
      </section>

      <!-- Footer : deliberate media controls + keyboard shortcuts hints -->
      <footer class="replay-footer">
        <div class="footer-controls">
          <button
            class="ctrl-btn ctrl-btn-secondary"
            @click="seekRelative(-1)"
            :disabled="currentRound <= 0"
            :aria-label="'Previous round'"
            title="Previous round"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
              <path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z" />
            </svg>
          </button>
          <button
            class="ctrl-btn ctrl-btn-primary"
            @click="togglePlay"
            :aria-label="isPlaying ? 'Pause' : 'Play'"
            :title="isPlaying ? 'Pause' : 'Play'"
          >
            <svg v-if="!isPlaying" viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
              <polygon points="6 4 20 12 6 20 6 4" />
            </svg>
            <svg v-else viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
              <rect x="6" y="5" width="4" height="14" />
              <rect x="14" y="5" width="4" height="14" />
            </svg>
          </button>
          <button
            class="ctrl-btn ctrl-btn-secondary"
            @click="seekRelative(1)"
            :disabled="currentRound >= totalRounds"
            :aria-label="'Next round'"
            title="Next round"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
              <path d="M13 6v12l8.5-6L13 6zm-.5 6L4 6v12l8.5-6z" />
            </svg>
          </button>
        </div>

        <div class="footer-stats">
          <span class="footer-stat">
            <span class="footer-stat-label">Events</span>
            <span class="footer-stat-value">{{ visibleActions.length }}</span>
            <span class="footer-stat-total">/ {{ allActions.length }}</span>
          </span>
          <span class="footer-stat-divider" aria-hidden="true"></span>
          <span class="footer-stat">
            <span class="footer-stat-label">𝕏</span>
            <span class="footer-stat-value">{{ visibleTwitterCount }}</span>
          </span>
          <span class="footer-stat">
            <span class="footer-stat-label">Reddit</span>
            <span class="footer-stat-value">{{ visibleRedditCount }}</span>
          </span>
          <span class="footer-stat">
            <span class="footer-stat-label">PM</span>
            <span class="footer-stat-value">{{ visiblePolymarketCount }}</span>
          </span>
        </div>

        <div class="footer-hints" aria-label="Keyboard shortcuts">
          <span class="hint-row">
            <kbd class="hint-kbd">Space</kbd>
            <span>Play / pause</span>
          </span>
          <span class="hint-row">
            <kbd class="hint-kbd">←</kbd>
            <kbd class="hint-kbd">→</kbd>
            <span>Seek timeline</span>
          </span>
        </div>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getRunStatusDetail } from '../api/simulation'
import { truncate } from '../utils/text'
import BeliefDriftChart from '../components/BeliefDriftChart.vue'

// eslint-disable-next-line no-unused-vars
const { t } = useI18n()
const route = useRoute()
const router = useRouter()

// ─── Reactive state ─────────────────────────────────────────────
// IMPORTANT — the following refs are part of the public contract and
// must keep these exact names: currentRound, totalRounds, isPlaying,
// playbackSpeed, simulationData, replayData, fetchReplay, scrubToRound.

const simulationId = ref(route.params.simulationId)
const loading = ref(true)
const error = ref(null)

const simulationData = ref(null)        // raw API payload (preserved)
const replayData = ref(null)            // alias kept for downstream consumers
const allActions = ref([])
const totalRounds = ref(0)
const currentRound = ref(0)
const isPlaying = ref(false)
const playbackSpeed = ref(1)            // renamed from `speed` → matches contract
const speeds = [0.5, 1, 1.5, 2]
const scrollContainer = ref(null)
const trackRef = ref(null)

let playInterval = null

const knownTypes = [
  'CREATE_POST', 'QUOTE_POST', 'REPOST', 'LIKE_POST', 'DISLIKE_POST',
  'CREATE_COMMENT', 'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS',
  'FOLLOW', 'MUTE', 'UPVOTE_POST', 'DOWNVOTE_POST', 'DO_NOTHING',
  'BUY_SHARES', 'SELL_SHARES', 'CREATE_MARKET', 'BROWSE_MARKETS',
  'VIEW_PORTFOLIO', 'COMMENT_ON_MARKET'
]

// ─── Derived collections ────────────────────────────────────────
const visibleActions = computed(() =>
  allActions.value.filter(a => a.round_num <= currentRound.value)
)

const visibleTwitterCount = computed(() =>
  visibleActions.value.filter(a => a.platform === 'twitter').length
)
const visibleRedditCount = computed(() =>
  visibleActions.value.filter(a => a.platform === 'reddit').length
)
const visiblePolymarketCount = computed(() =>
  visibleActions.value.filter(a => a.platform === 'polymarket').length
)

const progressPercent = computed(() => {
  if (totalRounds.value === 0) return 0
  return (currentRound.value / totalRounds.value) * 100
})

// Group all actions by round for narrative card.
const actionsByRound = computed(() => {
  const map = new Map()
  for (const a of allActions.value) {
    if (!map.has(a.round_num)) map.set(a.round_num, [])
    map.get(a.round_num).push(a)
  }
  return map
})

const currentRoundEvents = computed(() =>
  actionsByRound.value.get(currentRound.value) || []
)

// Inflection heuristic : a round is an "inflection point" if its
// volume of events is at least 1.5× the rolling average over the
// last 5 rounds. Fallback : first/last round.
const inflectionRounds = computed(() => {
  const counts = []
  for (let r = 0; r <= totalRounds.value; r++) {
    counts.push((actionsByRound.value.get(r) || []).length)
  }
  const flagged = new Set()
  for (let r = 1; r < counts.length; r++) {
    const window = counts.slice(Math.max(0, r - 5), r)
    if (window.length === 0) continue
    const avg = window.reduce((s, n) => s + n, 0) / window.length
    if (counts[r] >= avg * 1.5 && counts[r] >= 4) flagged.add(r)
  }
  if (totalRounds.value > 0) flagged.add(totalRounds.value)
  return flagged
})

const isInflectionRound = computed(() =>
  inflectionRounds.value.has(currentRound.value)
)

const currentRoundTitle = computed(() => {
  if (currentRound.value === 0) return 'Simulation initialised'
  if (isInflectionRound.value) return `Inflection at round ${currentRound.value}`
  return `Round ${currentRound.value} chapter`
})

const currentRoundNarrative = computed(() => {
  const events = currentRoundEvents.value
  if (events.length === 0) {
    return 'No agent activity recorded for this round. Scrub forward to reach the next chapter.'
  }
  const platforms = new Set(events.map(e => e.platform))
  const agents = new Set(events.map(e => e.agent_name).filter(Boolean))
  const platformList = Array.from(platforms).join(', ')
  return `${events.length} events from ${agents.size} agent${agents.size === 1 ? '' : 's'} across ${platformList}. ${
    isInflectionRound.value
      ? 'Volume spike detected — likely catalyst for downstream belief drift.'
      : 'Steady flow consistent with the prior trajectory.'
  }`
})

const currentRoundClock = computed(() => {
  const first = currentRoundEvents.value[0]
  return first ? formatTime(first.timestamp) : '—'
})

// ─── Track markers ──────────────────────────────────────────────
// Up to 8 markers spaced across the timeline. Inflection rounds
// render as terracotta diamonds, calm rounds as primary-container dots.
const trackMarkers = computed(() => {
  if (totalRounds.value === 0) return []
  const stepCount = Math.min(8, Math.max(2, totalRounds.value))
  const out = []
  for (let i = 1; i <= stepCount; i++) {
    const round = Math.round((i / stepCount) * totalRounds.value)
    const left = (round / totalRounds.value) * 100
    const isInflection = inflectionRounds.value.has(round)
    out.push({
      round,
      left,
      kind: isInflection ? 'marker-inflection' : 'marker-calm',
      tooltip: `Round ${round}${isInflection ? ' — inflection' : ''}`
    })
  }
  return out
})

// ─── Agent states mini panel ────────────────────────────────────
// Aggregates the most recent action per agent (up to current round)
// and derives a mood : bullish (post/buy), bearish (sell/dislike),
// calm (idle/follow), neutral (other).
const agentStates = computed(() => {
  const lastByAgent = new Map()
  for (const a of visibleActions.value) {
    const key = a.agent_id || a.agent_name
    if (!key) continue
    lastByAgent.set(key, a)
  }
  const arr = Array.from(lastByAgent.values()).slice(-8).reverse()
  return arr.map(a => {
    const name = a.agent_name || 'Agent'
    return {
      id: a.agent_id || name,
      name,
      initial: name[0]?.toUpperCase() || 'A',
      tier: platformTier(a.platform),
      mood: deriveMood(a.action_type)
    }
  })
})

function platformTier (platform) {
  if (platform === 'twitter') return 'Tier 1 social'
  if (platform === 'reddit') return 'Retail aggregate'
  if (platform === 'polymarket') return 'Market trader'
  return 'Generic agent'
}

function deriveMood (type) {
  if (['BUY_SHARES', 'CREATE_POST', 'QUOTE_POST', 'UPVOTE_POST'].includes(type)) return 'bullish'
  if (['SELL_SHARES', 'DISLIKE_POST', 'DOWNVOTE_POST', 'DISLIKE_COMMENT', 'MUTE'].includes(type)) return 'bearish'
  if (['DO_NOTHING', 'FOLLOW', 'BROWSE_MARKETS', 'VIEW_PORTFOLIO'].includes(type)) return 'calm'
  return 'neutral'
}

// ─── Data loading ───────────────────────────────────────────────
// Public name `fetchReplay` preserved for the contract. `loadData`
// kept as a thin alias so internal callers keep working.
const fetchReplay = async () => {
  loading.value = true
  error.value = null

  try {
    const detailRes = await getRunStatusDetail(simulationId.value)

    if (!detailRes.success || !detailRes.data) {
      error.value = 'Failed to load simulation data'
      return
    }

    simulationData.value = detailRes.data
    replayData.value = detailRes.data

    const actions = detailRes.data.all_actions || []
    if (actions.length === 0) {
      error.value = 'No actions found for this simulation'
      return
    }

    // Sort by round then timestamp
    actions.sort((a, b) => {
      if (a.round_num !== b.round_num) return a.round_num - b.round_num
      return new Date(a.timestamp) - new Date(b.timestamp)
    })

    // Mark round starts
    let prevRound = -1
    actions.forEach((action, i) => {
      action._uniqueId = action.id || `${action.timestamp}-${action.platform}-${action.agent_id}-${action.action_type}-${i}`
      if (action.round_num !== prevRound) {
        action._isRoundStart = true
        prevRound = action.round_num
      }
    })

    allActions.value = actions

    const maxRound = actions.length > 0 ? Math.max(...actions.map(a => a.round_num)) : 0
    totalRounds.value = detailRes.data.total_rounds || maxRound
    currentRound.value = 0
  } catch (err) {
    error.value = `Error: ${err.message}`
  } finally {
    loading.value = false
  }
}

const loadData = fetchReplay

// ─── Playback ───────────────────────────────────────────────────
const togglePlay = () => {
  if (isPlaying.value) pause()
  else play()
}

const play = () => {
  if (currentRound.value >= totalRounds.value) currentRound.value = 0
  isPlaying.value = true
  startPlayback()
}

const pause = () => {
  isPlaying.value = false
  stopPlayback()
}

const startPlayback = () => {
  stopPlayback()
  const interval = Math.max(100, 1000 / playbackSpeed.value)
  playInterval = setInterval(() => {
    if (currentRound.value >= totalRounds.value) {
      pause()
      return
    }
    currentRound.value++
  }, interval)
}

const stopPlayback = () => {
  if (playInterval) {
    clearInterval(playInterval)
    playInterval = null
  }
}

const onScrub = (e) => {
  scrubToRound(parseInt(e.target.value, 10))
}

// Public name `scrubToRound` preserved for the contract.
const scrubToRound = (round) => {
  const safe = Math.max(0, Math.min(totalRounds.value, Number.isFinite(round) ? round : 0))
  currentRound.value = safe
  if (isPlaying.value) {
    stopPlayback()
    startPlayback()
  }
}

const seekRelative = (delta) => scrubToRound(currentRound.value + delta)

const onTrackClick = (event) => {
  const el = trackRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  // Account for RTL (inset-inline-start) by computing relative to direction.
  const isRtl = getComputedStyle(el).direction === 'rtl'
  const x = event.clientX - rect.left
  const ratio = isRtl ? 1 - x / rect.width : x / rect.width
  scrubToRound(Math.round(ratio * totalRounds.value))
}

const onTrackKeydown = (event) => {
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    seekRelative(-1)
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    seekRelative(1)
  } else if (event.key === ' ' || event.code === 'Space') {
    event.preventDefault()
    togglePlay()
  }
}

// Document-level keyboard shortcuts (←/→ seek, Space play/pause).
// Skip when focus is in editable fields to avoid hijacking text input.
const onGlobalKeydown = (event) => {
  const target = event.target
  if (target && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))) {
    return
  }
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    seekRelative(-1)
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    seekRelative(1)
  } else if (event.key === ' ' || event.code === 'Space') {
    event.preventDefault()
    togglePlay()
  }
}

// Restart playback when speed changes
watch(playbackSpeed, () => {
  if (isPlaying.value) {
    stopPlayback()
    startPlayback()
  }
})

// Auto-scroll the narrative column as rounds advance during playback.
watch(currentRound, () => {
  nextTick(() => {
    const el = scrollContainer.value
    if (el && isPlaying.value) {
      el.scrollTo({ top: 0, behavior: 'smooth' })
    }
  })
})

const goBack = () => router.back()

// ─── Helpers ────────────────────────────────────────────────────
const getActionTypeLabel = (type) => {
  const labels = {
    'CREATE_POST': 'POST', 'REPOST': 'REPOST', 'LIKE_POST': 'LIKE',
    'CREATE_COMMENT': 'COMMENT', 'LIKE_COMMENT': 'LIKE', 'DISLIKE_POST': 'DISLIKE',
    'DISLIKE_COMMENT': 'DISLIKE', 'MUTE': 'MUTE', 'DO_NOTHING': 'IDLE',
    'FOLLOW': 'FOLLOW', 'SEARCH_POSTS': 'SEARCH', 'QUOTE_POST': 'QUOTE',
    'UPVOTE_POST': 'UPVOTE', 'DOWNVOTE_POST': 'DOWNVOTE',
    'BUY_SHARES': 'BUY', 'SELL_SHARES': 'SELL', 'CREATE_MARKET': 'NEW MARKET',
    'BROWSE_MARKETS': 'BROWSE', 'VIEW_PORTFOLIO': 'PORTFOLIO', 'COMMENT_ON_MARKET': 'COMMENT'
  }
  return labels[type] || type || 'UNKNOWN'
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
    })
  } catch { return '' }
}

// `knownTypes` kept exported via closure usage so eslint stays quiet.
void knownTypes

onMounted(() => {
  fetchReplay()
  window.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  stopPlayback()
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   ReplayView — Strategic Debrief
   Refonte alignée sur stitch_bassira_global_design_system /
   bassira_relecture_de_simulation_strat_gique. Tokens --wi-*
   (Warm Intelligence) pour l'expérience cinématique.
   ═══════════════════════════════════════════════════════════ */

.replay-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  overflow: hidden;
  font-family: var(--wi-font-body);
}

/* ─── Top bar ────────────────────────────────────────────── */
.replay-topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--wi-space-md);
  background: var(--wi-surface);
  border-bottom: 1px solid var(--wi-outline-variant);
  z-index: 30;
  flex-shrink: 0;
}

.replay-brand {
  display: flex;
  align-items: baseline;
  gap: var(--wi-space-xs);
  cursor: pointer;
  font-family: var(--wi-font-heading);
  letter-spacing: -0.01em;
}

.brand-mark {
  font-size: 20px;
  font-weight: 700;
  color: var(--wi-primary);
}

.brand-suffix {
  font-size: 14px;
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.replay-topnav {
  display: none;
  gap: var(--wi-space-md);
}

@media (min-width: 900px) {
  .replay-topnav { display: flex; }
}

.topnav-link {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  padding-bottom: 4px;
  border-bottom: 2px solid transparent;
  cursor: default;
  transition: color var(--ms-transition);
}

.topnav-link.active {
  color: var(--wi-primary);
  border-bottom-color: var(--wi-primary);
  font-weight: 600;
}

.replay-back-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  padding: 8px 16px;
  cursor: pointer;
  transition: all var(--ms-transition);
}

.replay-back-btn:hover {
  color: var(--wi-primary);
  border-color: var(--wi-primary);
  background: var(--wi-primary-soft);
}

/* ─── Loading / Error states ─────────────────────────────── */
.replay-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: var(--wi-space-md);
  font-family: var(--wi-font-heading);
  font-size: 13px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
}

.replay-state-error { color: var(--wi-error); }

.replay-pulse {
  width: 32px;
  height: 32px;
  border: 2px solid var(--wi-primary-container);
  border-radius: 50%;
  animation: wi-ripple 2s infinite;
}

@keyframes wi-ripple {
  0% { transform: scale(0.8); opacity: 1; }
  100% { transform: scale(2.4); opacity: 0; }
}

/* ─── Sticky timeline scrubber band ──────────────────────── */
.scrubber-band {
  background: var(--wi-surface);
  padding: var(--wi-space-md) var(--wi-space-lg) var(--wi-space-sm);
  border-bottom: 1px solid var(--wi-outline-variant);
  flex-shrink: 0;
  z-index: 20;
}

.scrubber-band-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-md);
  margin-bottom: var(--wi-space-md);
}

.scrubber-round-display {
  display: flex;
  align-items: baseline;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-heading);
}

.scrubber-round-label {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  margin-inline-end: 6px;
}

.scrubber-round-value {
  font-size: var(--wi-h1-size);
  font-weight: var(--wi-h1-weight);
  letter-spacing: var(--wi-h1-tracking);
  color: var(--wi-primary);
  line-height: 1;
}

.scrubber-round-total {
  font-size: 18px;
  font-weight: 500;
  color: var(--wi-on-surface-variant);
}

/* Speed pills — cream on warm container */
.scrubber-speed-pills {
  display: inline-flex;
  align-items: center;
  background: var(--wi-surface-container-high);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  padding: 4px 6px;
}

.speed-pill {
  position: relative;
  display: inline-flex;
  align-items: center;
  background: transparent;
  border: 0;
  font-family: var(--wi-font-heading);
  font-weight: 500;
  font-size: 13px;
  color: var(--wi-on-surface-variant);
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  transition: all var(--ms-transition);
}

.speed-pill.active {
  color: var(--wi-on-primary);
  background: var(--wi-primary);
  font-weight: 600;
  box-shadow: var(--wi-shadow-sm);
}

.speed-pill:not(.active):hover {
  color: var(--wi-primary);
}

.speed-pill-sep {
  position: absolute;
  inset-inline-end: -1px;
  top: 25%;
  width: 1px;
  height: 50%;
  background: var(--wi-outline-variant);
}

.speed-pill.active .speed-pill-sep,
.speed-pill:hover + .speed-pill .speed-pill-sep {
  background: transparent;
}

/* ─── Timeline track ─────────────────────────────────────── */
.scrubber-track {
  position: relative;
  height: 28px;
  display: flex;
  align-items: center;
  cursor: pointer;
  outline: none;
}

.scrubber-track:focus-visible .scrubber-track-rail {
  box-shadow: 0 0 0 3px var(--wi-primary-soft);
}

.scrubber-track-rail {
  position: absolute;
  inset-inline: 0;
  top: 50%;
  height: 8px;
  transform: translateY(-50%);
  background: var(--wi-surface-container-high);
  border-radius: var(--wi-radius-pill);
}

.scrubber-track-fill {
  position: absolute;
  inset-inline-start: 0;
  top: 50%;
  height: 8px;
  transform: translateY(-50%);
  background: linear-gradient(
    90deg,
    var(--wi-primary-container),
    var(--wi-primary)
  );
  border-radius: var(--wi-radius-pill) 0 0 var(--wi-radius-pill);
  transition: width 100ms linear;
  pointer-events: none;
}

.scrubber-marker {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  transform: translate(-50%, -50%);
  pointer-events: none;
  border: 2px solid var(--wi-surface);
  border-radius: 50%;
  box-shadow: var(--wi-shadow-sm);
}

.scrubber-marker.marker-calm {
  background: var(--wi-secondary);
}

.scrubber-marker.marker-inflection {
  width: 14px;
  height: 14px;
  background: var(--wi-on-primary-container);
  border-radius: 2px;
  transform: translate(-50%, -50%) rotate(45deg);
}

.scrubber-playhead {
  position: absolute;
  top: 50%;
  width: 18px;
  height: 18px;
  transform: translate(-50%, -50%);
  background: var(--wi-surface);
  border: 4px solid var(--wi-primary);
  border-radius: 50%;
  pointer-events: none;
  box-shadow: var(--wi-shadow-md);
  z-index: 3;
  transition: inset-inline-start 100ms linear;
}

.scrubber-range-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  cursor: pointer;
  opacity: 0;
  z-index: 4;
}

.scrubber-range-overlay::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 24px;
  height: 24px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.scrubber-range-overlay::-moz-range-thumb {
  width: 24px;
  height: 24px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

/* ─── Canvas (center column + side panel) ────────────────── */
.replay-canvas {
  flex: 1;
  display: flex;
  gap: var(--wi-gutter);
  padding: var(--wi-space-lg);
  padding-bottom: 96px; /* leave room for footer */
  overflow: hidden;
  min-height: 0;
}

.canvas-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--wi-outline-variant) transparent;
}

.canvas-center::-webkit-scrollbar { width: 6px; }
.canvas-center::-webkit-scrollbar-thumb {
  background: var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
}

/* ─── Narrative event card ───────────────────────────────── */
.narrative-card {
  position: relative;
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  border-inline-start: 4px solid var(--wi-primary-container);
  padding: var(--wi-space-lg);
  box-shadow: var(--wi-shadow-md);
  overflow: hidden;
}

.narrative-card.is-inflection {
  border-inline-start-color: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-lg);
}

.narrative-card-bg {
  position: absolute;
  top: var(--wi-space-md);
  inset-inline-end: var(--wi-space-md);
  color: var(--wi-primary);
  opacity: 0.06;
  pointer-events: none;
}

.narrative-card-meta {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
  margin-bottom: var(--wi-space-sm);
  position: relative;
  z-index: 1;
}

.narrative-tag {
  font-family: var(--wi-font-heading);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--wi-primary);
  background: var(--wi-primary-soft);
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
}

.narrative-tag.tag-inflection {
  color: var(--wi-on-primary-container);
  background: var(--wi-surface-container-high);
}

.narrative-tag-time {
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 500;
  color: var(--wi-on-surface-variant);
  margin-inline-start: auto;
  letter-spacing: 0.04em;
}

.narrative-card-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-surface);
  margin: 0 0 var(--wi-space-sm);
  position: relative;
  z-index: 1;
}

.narrative-card-body {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-lg);
  line-height: var(--wi-body-lg-leading);
  color: var(--wi-on-surface-variant);
  margin: 0 0 var(--wi-space-md);
  position: relative;
  z-index: 1;
}

.narrative-card-events {
  position: relative;
  z-index: 1;
  border-top: 1px solid var(--wi-outline-variant);
  padding-top: var(--wi-space-sm);
}

.narrative-events-label {
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  display: block;
  margin-bottom: var(--wi-space-xs);
}

.narrative-events-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.narrative-event-row {
  display: flex;
  align-items: baseline;
  gap: var(--wi-space-xs);
  font-size: 14px;
  color: var(--wi-on-surface);
}

.narrative-event-agent {
  font-family: var(--wi-font-heading);
  font-weight: 600;
  color: var(--wi-primary);
  min-width: 80px;
}

.narrative-event-action {
  font-family: var(--wi-font-heading);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container);
  padding: 2px 8px;
  border-radius: var(--wi-radius-sm);
  flex-shrink: 0;
}

.narrative-event-snippet {
  flex: 1;
  font-family: var(--wi-font-body);
  font-size: 13px;
  color: var(--wi-on-surface-variant);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ─── Belief drift card ──────────────────────────────────── */
.drift-card {
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  padding: var(--wi-space-md);
  box-shadow: var(--wi-shadow-sm);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  min-height: 320px;
}

.drift-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.drift-card-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin: 0;
}

.drift-card-status {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
}

.drift-card-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wi-secondary);
  box-shadow: 0 0 0 4px var(--wi-secondary-container);
}

.drift-card-chart-wrap {
  flex: 1;
  min-height: 240px;
  position: relative;
}

.drift-card-chart {
  width: 100%;
  height: 100%;
}

/* ─── Side agent panel ───────────────────────────────────── */
.agent-panel {
  width: 320px;
  flex-shrink: 0;
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  padding: var(--wi-space-md);
  box-shadow: var(--wi-shadow-sm);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  scrollbar-width: thin;
}

@media (max-width: 1100px) {
  .agent-panel { display: none; }
}

.agent-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--wi-space-sm);
  margin-bottom: var(--wi-space-sm);
  border-bottom: 1px solid var(--wi-outline-variant);
}

.agent-panel-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin: 0;
}

.agent-panel-count {
  font-family: var(--wi-font-heading);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container);
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
}

.agent-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}

.agent-row {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
  padding: 8px;
  border-radius: var(--wi-radius-interactive);
  transition: background var(--ms-transition);
}

.agent-row:hover {
  background: var(--wi-surface-container-low);
}

.agent-row-empty {
  color: var(--wi-on-surface-variant);
  font-size: 13px;
  font-style: italic;
}

.agent-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--wi-surface-container-high);
  color: var(--wi-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--wi-font-heading);
  font-size: 16px;
  font-weight: 600;
  flex-shrink: 0;
}

.agent-meta {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-tier {
  font-family: var(--wi-font-body);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
}

.agent-mood {
  font-family: var(--wi-font-heading);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.16em;
  padding: 4px 8px;
  border-radius: var(--wi-radius-sm);
  white-space: nowrap;
}

.mood-bullish {
  color: var(--wi-on-secondary-container);
  background: var(--wi-secondary-container);
}

.mood-bearish {
  color: var(--wi-on-error-container);
  background: var(--wi-error-container);
}

.mood-calm {
  color: var(--wi-on-tertiary-container);
  background: var(--wi-tertiary-container);
}

.mood-neutral {
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container-high);
}

/* ─── Footer (fixed media controls + hints) ──────────────── */
.replay-footer {
  position: absolute;
  bottom: 0;
  inset-inline: 0;
  height: 80px;
  background: var(--wi-surface);
  border-top: 1px solid var(--wi-outline-variant);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--wi-space-lg);
  gap: var(--wi-space-md);
  z-index: 25;
  box-shadow: var(--wi-shadow-ambient);
}

.footer-controls {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
}

.ctrl-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  cursor: pointer;
  transition: all var(--ms-transition);
  flex-shrink: 0;
}

.ctrl-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ctrl-btn-secondary {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--wi-surface-container-high);
  color: var(--wi-primary);
  border: 1px solid var(--wi-outline-variant);
}

.ctrl-btn-secondary:hover:not(:disabled) {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border-color: var(--wi-primary);
}

.ctrl-btn-primary {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--wi-on-primary-container);
  color: var(--wi-on-primary);
  box-shadow: var(--wi-shadow-md);
}

.ctrl-btn-primary:hover {
  background: var(--wi-primary);
}

.footer-stats {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
  font-family: var(--wi-font-heading);
}

.footer-stat {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
}

.footer-stat-label {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
}

.footer-stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--wi-primary);
}

.footer-stat-total {
  font-size: 13px;
  font-weight: 500;
  color: var(--wi-on-surface-variant);
}

.footer-stat-divider {
  width: 1px;
  height: 18px;
  background: var(--wi-outline-variant);
}

.footer-hints {
  display: flex;
  align-items: center;
  gap: var(--wi-space-md);
  font-family: var(--wi-font-body);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
}

@media (max-width: 900px) {
  .footer-hints { display: none; }
}

.hint-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.hint-kbd {
  font-family: var(--wi-font-heading);
  font-size: 11px;
  font-weight: 600;
  color: var(--wi-on-surface);
  background: var(--wi-surface-container);
  border: 1px solid var(--wi-outline-variant);
  border-bottom-width: 2px;
  border-radius: var(--wi-radius-sm);
  padding: 3px 7px;
  min-width: 22px;
  text-align: center;
}
</style>
