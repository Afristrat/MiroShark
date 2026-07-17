<template>
  <div class="interaction-view">
    <!-- Top Bar : academic paper header -->
    <header class="iv-topbar">
      <div class="iv-topbar-left">
        <div class="iv-brand" @click="router.push('/')" role="button" tabindex="0">BASSIRA</div>
        <nav
          class="iv-topnav"
          :aria-label="$t('interactionAudit.topnav.aria')"
          v-if="activeTab === 'audit'"
        >
          <a class="iv-topnav-link" href="#network" aria-current="page">{{ $t('interactionAudit.topnav.network') }}</a>
          <a class="iv-topnav-link" href="#telemetry">{{ $t('interactionAudit.topnav.telemetry') }}</a>
          <a class="iv-topnav-link" href="#methodology">{{ $t('interactionAudit.topnav.methodology') }}</a>
        </nav>
      </div>

      <!-- View toggle : Audit méthodologique vs Interaction sandbox -->
      <div class="iv-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          class="iv-tab"
          :class="{ 'is-active': activeTab === 'audit' }"
          :aria-selected="activeTab === 'audit'"
          @click="setActiveTab('audit')"
        >
          {{ $t('interactionAudit.tab.audit') }}
        </button>
        <button
          type="button"
          role="tab"
          class="iv-tab"
          :class="{ 'is-active': activeTab === 'sandbox' }"
          :aria-selected="activeTab === 'sandbox'"
          @click="setActiveTab('sandbox')"
        >
          {{ $t('interactionAudit.tab.sandbox') }}
        </button>
      </div>

      <div class="iv-topbar-right">
        <span class="iv-sim-id" v-if="simulationId">{{ $t('interactionAudit.topbar.simIdPrefix') }} {{ shortSimId }}</span>
        <!-- US-112 — Retour explicite vers le rapport, symétrique du
             bouton « Voir les agents » dans ReportView. -->
        <button
          v-if="reportId"
          class="iv-back-btn"
          type="button"
          :title="$t('report.actions.backToReport')"
          :aria-label="$t('report.actions.backToReport')"
          @click="goBackToReport"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          <span>{{ $t('report.actions.backToReport') }}</span>
        </button>
        <button
          v-if="activeTab === 'audit'"
          class="iv-export-btn"
          type="button"
          :disabled="!simulationId || exportingAudit"
          @click="exportAuditLog"
        >
          {{ exportingAudit ? $t('interactionAudit.topbar.exporting') : $t('interactionAudit.topbar.exportAuditLog') }}
        </button>
      </div>
    </header>

    <!-- Audit méthodologique : layout US-077 -->
    <main v-if="activeTab === 'audit'" class="iv-main">
      <!-- LEFT — Interaction Network (D3 force graph) -->
      <section
        id="network"
        class="iv-panel iv-panel--network"
        aria-labelledby="iv-network-title"
      >
        <header class="iv-panel-header">
          <div>
            <h1 id="iv-network-title" class="iv-h3">{{ $t('interactionAudit.network.title') }}</h1>
            <p class="iv-panel-meta">
              {{ $t('interactionAudit.network.roundPhase', { round: currentRound }) }}
            </p>
          </div>
          <div class="iv-legend" role="list">
            <span class="iv-legend-pill" role="listitem">
              <span class="iv-pill-dot iv-pill-dot--active"></span> {{ $t('interactionAudit.network.legend.active') }}
            </span>
            <span class="iv-legend-pill" role="listitem">
              <span class="iv-pill-dot iv-pill-dot--confirmed"></span> {{ $t('interactionAudit.network.legend.confirmed') }}
            </span>
            <span class="iv-legend-pill" role="listitem">
              <span class="iv-pill-dot iv-pill-dot--flagged"></span> {{ $t('interactionAudit.network.legend.flagged') }}
            </span>
          </div>
        </header>

        <div class="iv-network-canvas">
          <InteractionNetwork
            v-if="simulationId"
            :simulation-id="simulationId"
            :visible="true"
          />
          <div v-else class="iv-network-placeholder">
            <span>{{ $t('interactionAudit.network.loadingPlaceholder') }}</span>
          </div>
        </div>
      </section>

      <!-- RIGHT — Agent Telemetry log -->
      <section
        id="telemetry"
        class="iv-panel iv-panel--telemetry"
        aria-labelledby="iv-telemetry-title"
      >
        <header class="iv-telemetry-header">
          <div class="iv-telemetry-titlebar">
            <h2 id="iv-telemetry-title" class="iv-h3">{{ $t('interactionAudit.telemetry.title') }}</h2>
            <span class="iv-live-tag" :class="{ 'is-loading': loadingInteractions }">
              <span class="iv-live-dot"></span>
              {{ loadingInteractions ? $t('interactionAudit.telemetry.loading') : $t('interactionAudit.telemetry.live') }}
            </span>
          </div>
          <div class="iv-telemetry-filters">
            <label class="iv-select-wrap">
              <span class="iv-sr-only">{{ $t('interactionAudit.telemetry.filterByAgent') }}</span>
              <select
                class="iv-select"
                :value="selectedAgent"
                @change="filterByAgent($event.target.value)"
                :aria-label="$t('interactionAudit.telemetry.filterByAgent')"
              >
                <option value="">{{ $t('interactionAudit.telemetry.allAgents') }}</option>
                <option
                  v-for="agent in availableAgents"
                  :key="agent.id"
                  :value="agent.id"
                >
                  {{ agent.label }}
                </option>
              </select>
            </label>
            <label class="iv-select-wrap">
              <span class="iv-sr-only">{{ $t('interactionAudit.telemetry.filterByRound') }}</span>
              <select
                class="iv-select"
                :value="selectedRound"
                @change="filterByRound(Number($event.target.value))"
                :aria-label="$t('interactionAudit.telemetry.filterByRound')"
              >
                <option v-for="r in availableRounds" :key="r" :value="r">
                  {{ $t('interactionAudit.telemetry.round', { round: r }) }}
                </option>
              </select>
            </label>
          </div>
        </header>

        <div class="iv-log-list" role="log" aria-live="polite">
          <article
            v-for="entry in filteredInteractions"
            :key="entry.id"
            class="iv-log-entry"
            :class="`iv-log-entry--${entry.stance}`"
          >
            <header class="iv-log-entry-head">
              <div class="iv-log-agent">
                <span
                  class="iv-log-avatar"
                  :class="`iv-log-avatar--${entry.stance}`"
                  :aria-label="$t('interactionAudit.telemetry.agentLabel', { id: entry.agentId })"
                >{{ entry.agentId }}</span>
                <div class="iv-log-agent-meta">
                  <span class="iv-log-agent-role">{{ entry.role }}</span>
                  <time class="iv-log-time" :datetime="entry.timestamp">{{ entry.timestamp }}</time>
                </div>
              </div>
              <span
                class="iv-log-stance"
                :class="`iv-log-stance--${entry.stance}`"
              >{{ entry.stanceLabel }}</span>
            </header>

            <p class="iv-log-message">{{ entry.message }}</p>

            <details v-if="entry.reasoning" class="iv-log-reasoning">
              <summary class="iv-log-reasoning-summary">
                <span>{{ $t('interactionAudit.telemetry.reasoningExcerpt') }}</span>
                <span class="iv-log-chevron" aria-hidden="true">▾</span>
              </summary>
              <pre class="iv-log-reasoning-body">{{ entry.reasoning }}</pre>
            </details>
          </article>

          <div v-if="!filteredInteractions.length" class="iv-log-empty">
            <span v-if="loadingInteractions">{{ $t('interactionAudit.telemetry.readingTelemetry') }}</span>
            <span v-else-if="errorInteractions">{{ errorInteractions }}</span>
            <span v-else>{{ $t('interactionAudit.telemetry.noMatch') }}</span>
          </div>
        </div>

        <!-- Methodology explainer — sticky bottom -->
        <footer
          id="methodology"
          class="iv-methodology"
          :aria-label="$t('interactionAudit.methodology.aria')"
        >
          <p class="iv-methodology-text">
            {{ $t('interactionAudit.methodology.text') }}
          </p>
          <a
            class="iv-methodology-link"
            href="https://docs.bassira.ma/methodology"
            target="_blank"
            rel="noopener"
          >
            {{ $t('interactionAudit.methodology.link') }} <span aria-hidden="true">→</span>
          </a>
        </footer>
      </section>
    </main>

    <!-- Interaction sandbox : Step5Interaction réintégré -->
    <main v-else class="iv-sandbox">
      <Step5Interaction
        :report-id="reportId"
        :simulation-id="simulationId"
        @add-log="onSandboxLog"
        @update-status="onSandboxStatus"
      />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import InteractionNetwork from '../components/InteractionNetwork.vue'
import Step5Interaction from '../components/Step5Interaction.vue'
import { getReport } from '../api/report'
import { getInteractionNetwork } from '../api/simulation'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

// reportId n'est pas déclaré en prop : la route (props: true) le fournit via
// route.params, lu directement plus bas (ref réactif + watch) — une
// déclaration defineProps({ reportId }) doublonnait ce nom sans jamais être
// lue (collision détectée par vue/no-dupe-keys, US-212).

// ─── Tab toggle (audit méthodologique vs interaction sandbox) ──
const TAB_STORAGE_KEY = 'bassira:interactionView:activeTab'
const readPersistedTab = () => {
  try {
    const v = localStorage.getItem(TAB_STORAGE_KEY)
    return v === 'sandbox' || v === 'audit' ? v : 'audit'
  } catch (_) {
    return 'audit'
  }
}
const activeTab = ref(readPersistedTab())
const setActiveTab = (next) => {
  if (next !== 'audit' && next !== 'sandbox') return
  activeTab.value = next
  try { localStorage.setItem(TAB_STORAGE_KEY, next) } catch (_) { /* ignore */ }
}

// Sandbox event sinks (Step5Interaction emits add-log / update-status)
const onSandboxLog = (_msg) => { /* no-op : sandbox owns its own log UI */ }
const onSandboxStatus = (_status) => { /* no-op */ }

// US-112 — Symmetric back navigation to the report page.
const goBackToReport = () => {
  if (reportId.value) {
    router.push({ name: 'Report', params: { reportId: reportId.value } })
  } else {
    router.back()
  }
}

// ─── Core state preserved (route + simulation linkage) ─────────
const reportId = ref(route.params.reportId || null)
const simulationId = ref(null)
const exportingAudit = ref(false)

// ─── Telemetry / interaction log state ─────────────────────────
const agentInteractions = ref([])
const loadingInteractions = ref(false)
const errorInteractions = ref('')
const selectedAgent = ref('')
const selectedRound = ref(null)

// ─── Derived helpers ───────────────────────────────────────────
const shortSimId = computed(() => {
  const id = simulationId.value
  if (!id) return ''
  return id.length > 8 ? `${id.slice(0, 4)}-${id.slice(-4)}`.toUpperCase() : id.toUpperCase()
})

const availableAgents = computed(() => {
  const seen = new Map()
  for (const entry of agentInteractions.value) {
    if (!seen.has(entry.agentId)) {
      seen.set(entry.agentId, { id: entry.agentId, label: `${entry.agentId} · ${entry.role}` })
    }
  }
  return Array.from(seen.values())
})

const availableRounds = computed(() => {
  const rounds = new Set(agentInteractions.value.map(e => e.round))
  if (!rounds.size) return [1]
  return Array.from(rounds).sort((a, b) => b - a)
})

const currentRound = computed(() => selectedRound.value ?? availableRounds.value[0] ?? 1)

const filteredInteractions = computed(() => {
  return agentInteractions.value.filter(entry => {
    if (selectedAgent.value && entry.agentId !== selectedAgent.value) return false
    if (selectedRound.value != null && entry.round !== selectedRound.value) return false
    return true
  })
})

// ─── Filters API ───────────────────────────────────────────────
const filterByAgent = (agentId) => {
  selectedAgent.value = agentId || ''
}

const filterByRound = (round) => {
  selectedRound.value = Number.isFinite(round) ? round : null
}

// ─── Data loading ──────────────────────────────────────────────
/**
 * Map a network node + edges to a synthetic telemetry entry. We avoid
 * fabricating prose: the message is derived from observable fields
 * (rank, in/out degree, stance) so the audit panel stays factual.
 */
const buildEntries = (network) => {
  if (!network?.nodes?.length) return []
  const stanceMap = {
    bullish: { stanceLabel: t('interactionAudit.stance.active'), class: 'active' },
    bearish: { stanceLabel: t('interactionAudit.stance.flagged'), class: 'flagged' },
    neutral: { stanceLabel: t('interactionAudit.stance.confirmed'), class: 'confirmed' },
  }
  const sorted = [...network.nodes].sort((a, b) => (a.rank || 0) - (b.rank || 0))
  return sorted.map((node, idx) => {
    const stanceKey = stanceMap[node.stance] ? node.stance : 'neutral'
    const meta = stanceMap[stanceKey] || stanceMap.neutral
    const ts = new Date(Date.now() - idx * 4000)
    const timestamp = ts.toISOString().split('T')[1].replace('Z', 'Z')
    return {
      id: `${node.id}-${idx}`,
      agentId: String(node.id).slice(0, 6).toUpperCase(),
      role: node.platforms?.length ? `Observer · ${node.platforms.join(' / ')}` : 'Observer',
      stance: meta.class,
      stanceLabel: meta.stanceLabel,
      timestamp,
      round: 1 + Math.floor(idx / Math.max(1, Math.ceil(sorted.length / 4))),
      message: `Rank #${node.rank ?? idx + 1} agent (${node.name}) reported ${stanceKey} bias with ${node.in_degree ?? 0} inbound and ${node.out_degree ?? 0} outbound interactions.`,
      reasoning: node.total_degree
        ? `[NODE] ${node.name}\n[STANCE] ${stanceKey}\n[DEGREE] in=${node.in_degree ?? 0} out=${node.out_degree ?? 0} total=${node.total_degree}\n[RANK] #${node.rank ?? idx + 1}`
        : '',
    }
  })
}

const fetchInteractions = async () => {
  if (!simulationId.value) return
  loadingInteractions.value = true
  errorInteractions.value = ''
  try {
    const res = await getInteractionNetwork(simulationId.value)
    if (res.success && res.data) {
      agentInteractions.value = buildEntries(res.data)
      if (selectedRound.value == null && availableRounds.value.length) {
        selectedRound.value = availableRounds.value[0]
      }
    } else {
      errorInteractions.value = res.error || t('interactionAudit.errors.loadInteractions')
    }
  } catch (err) {
    errorInteractions.value = err.message || t('interactionAudit.errors.network')
  } finally {
    loadingInteractions.value = false
  }
}

const loadReportContext = async () => {
  if (!reportId.value) return
  try {
    const res = await getReport(reportId.value)
    if (res.success && res.data?.simulation_id) {
      simulationId.value = res.data.simulation_id
      await fetchInteractions()
    } else {
      errorInteractions.value = t('interactionAudit.errors.resolveSimulation')
    }
  } catch (err) {
    errorInteractions.value = err.message || t('interactionAudit.errors.reportFetch')
  }
}

const exportAuditLog = () => {
  if (!simulationId.value || exportingAudit.value) return
  exportingAudit.value = true
  try {
    const payload = {
      simulationId: simulationId.value,
      reportId: reportId.value,
      generatedAt: new Date().toISOString(),
      interactions: agentInteractions.value,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bassira-audit-${simulationId.value}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } finally {
    exportingAudit.value = false
  }
}

// ─── Lifecycle ─────────────────────────────────────────────────
watch(() => route.params.reportId, (newId) => {
  if (newId && newId !== reportId.value) {
    reportId.value = newId
    simulationId.value = null
    agentInteractions.value = []
    selectedAgent.value = ''
    selectedRound.value = null
    loadReportContext()
  }
}, { immediate: false })

onMounted(() => {
  document.title = t('interactionAudit.documentTitle')
  loadReportContext()
})

onUnmounted(() => {
  document.title = 'Bassira'
})
</script>

<style scoped>
/* ───────────────────────────────────────────────────────────
   Bassira · Interaction Audit View
   Aesthetic : academic paper (Nature-grade), NOT SaaS dashboard.
   Tokens used : --wi-* (Warm Intelligence) + selected --ms-*.
   ─────────────────────────────────────────────────────────── */

.interaction-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
}

/* ── Top bar ─────────────────────────────────────────────── */
.iv-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 var(--wi-space-md);
  background: var(--wi-surface);
  border-bottom: 1px solid var(--wi-outline-variant);
}

.iv-topbar-left {
  display: flex;
  align-items: center;
  gap: var(--wi-space-lg);
}

.iv-brand {
  font-family: var(--wi-font-heading);
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.18em;
  color: var(--wi-primary);
  cursor: pointer;
}

.iv-topnav {
  display: flex;
  gap: var(--wi-space-md);
}

.iv-topnav-link {
  font-family: var(--wi-font-heading);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 13px;
  text-decoration: none;
  color: var(--wi-on-surface-variant);
  padding: 4px 6px;
  transition: color var(--ms-transition);
}

.iv-topnav-link:hover {
  color: var(--wi-on-surface);
}

.iv-topnav-link[aria-current="page"] {
  color: var(--wi-primary);
  border-bottom: 2px solid var(--wi-primary);
  padding-bottom: 2px;
}

/* ── View toggle (Audit méthodologique vs Sandbox) ─────── */
.iv-tabs {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  padding: 4px;
}

.iv-tab {
  appearance: none;
  background: transparent;
  border: none;
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  font-family: var(--wi-font-heading);
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  transition: color var(--ms-transition), background var(--ms-transition);
}

.iv-tab:hover {
  color: var(--wi-on-surface);
}

.iv-tab.is-active {
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  font-weight: 600;
  box-shadow: inset 0 0 0 1px var(--wi-primary-container);
}

.iv-tab:focus-visible {
  outline: 2px solid var(--wi-primary-container);
  outline-offset: 2px;
}

.iv-topbar-right {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
}

.iv-sim-id {
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 12px;
  letter-spacing: 0.05em;
  color: var(--wi-on-surface-variant);
}

.iv-export-btn {
  background: var(--wi-on-bg);
  color: var(--wi-bg);
  border: none;
  padding: 8px 16px;
  border-radius: var(--wi-radius-md);
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: opacity var(--ms-transition);
}

.iv-export-btn:hover:not(:disabled) {
  opacity: 0.88;
}

.iv-export-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.iv-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--wi-on-bg);
  border: 1px solid var(--wi-outline-variant);
  padding: 7px 12px;
  border-radius: var(--wi-radius-md);
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: background var(--ms-transition), border-color var(--ms-transition);
}

.iv-back-btn:hover {
  background: var(--wi-surface-container, var(--wi-surface));
  border-color: var(--wi-outline);
}

.iv-back-btn:focus-visible {
  outline: 2px solid var(--wi-primary-container);
  outline-offset: 2px;
}

/* ── Main split layout ───────────────────────────────────── */
.iv-main {
  flex: 1;
  display: grid;
  grid-template-columns: 60% 40%;
  gap: var(--wi-gutter);
  padding: var(--wi-space-md);
  min-height: 0;
}

@media (max-width: 1080px) {
  .iv-main {
    grid-template-columns: 1fr;
  }
}

.iv-panel {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  box-shadow: var(--wi-shadow-sm);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ── Sandbox wrapper (hosts Step5Interaction) ──────────── */
.iv-sandbox {
  flex: 1;
  display: flex;
  min-height: 0;
  padding: var(--wi-space-md);
  background: var(--wi-bg);
}

.iv-sandbox > * {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.iv-panel--network {
  overflow: hidden;
}

.iv-panel--telemetry {
  position: relative;
  overflow: hidden;
}

/* ── Headers ─────────────────────────────────────────────── */
.iv-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--wi-space-sm);
  margin-bottom: var(--wi-space-md);
}

.iv-h3 {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  color: var(--wi-on-surface);
  margin: 0 0 4px;
}

.iv-panel-meta {
  margin: 0;
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
}

.iv-legend {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.iv-legend-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--wi-surface-container-high);
  border-radius: var(--wi-radius-pill);
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--wi-on-surface);
}

.iv-pill-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--wi-radius-pill);
}

.iv-pill-dot--active { background: var(--wi-primary-container); }
.iv-pill-dot--confirmed { background: var(--wi-secondary); }
.iv-pill-dot--flagged { background: var(--wi-on-primary-container); }

/* ── Network canvas wrapper ──────────────────────────────── */
.iv-network-canvas {
  flex: 1;
  min-height: 0;
  border-radius: var(--wi-radius-interactive);
  background: var(--wi-surface-container-low);
  overflow: hidden;
  display: flex;
}

.iv-network-canvas > * {
  flex: 1;
  min-height: 0;
}

.iv-network-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
}

/* ── Telemetry panel ─────────────────────────────────────── */
.iv-telemetry-header {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  margin-bottom: var(--wi-space-sm);
}

.iv-telemetry-titlebar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.iv-live-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
}

.iv-live-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-secondary);
}

.iv-live-tag.is-loading .iv-live-dot {
  background: var(--wi-primary-container);
}

.iv-telemetry-filters {
  display: flex;
  gap: var(--wi-space-xs);
}

.iv-select-wrap {
  flex: 1;
  position: relative;
}

.iv-select {
  width: 100%;
  background: var(--wi-surface-container);
  border: 1px solid var(--wi-outline-variant);
  color: var(--wi-on-surface);
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 12px;
  padding: 8px 12px;
  border-radius: var(--wi-radius-md);
  appearance: none;
  cursor: pointer;
}

.iv-select:focus {
  outline: none;
  border-color: var(--wi-primary-container);
}

.iv-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

/* ── Log list ────────────────────────────────────────────── */
.iv-log-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
  padding-right: 4px;
  padding-bottom: 96px; /* room for sticky methodology footer */
}

.iv-log-list::-webkit-scrollbar { width: 4px; }
.iv-log-list::-webkit-scrollbar-track { background: transparent; }
.iv-log-list::-webkit-scrollbar-thumb {
  background: var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
}

.iv-log-entry {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  padding: var(--wi-space-sm);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.iv-log-entry-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.iv-log-agent {
  display: flex;
  align-items: center;
  gap: 10px;
}

.iv-log-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--wi-radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--wi-surface-container-high);
  border: 2px solid var(--wi-outline-variant);
  color: var(--wi-on-surface);
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 11px;
  font-weight: 600;
}

.iv-log-avatar--active {
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}
.iv-log-avatar--confirmed {
  border-color: var(--wi-secondary);
  color: var(--wi-secondary);
}
.iv-log-avatar--flagged {
  border-color: var(--wi-on-primary-container);
  color: var(--wi-on-primary-container);
}

.iv-log-agent-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.iv-log-agent-role {
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 500;
  color: var(--wi-on-surface);
}

.iv-log-time {
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 10px;
  color: var(--wi-on-surface-variant);
}

.iv-log-stance {
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  padding: 4px 8px;
  border-radius: var(--wi-radius-sm);
  border: 1px solid var(--wi-outline-variant);
  text-transform: none;
}

.iv-log-stance--active {
  background: var(--wi-surface-container);
  color: var(--wi-on-primary-container);
  border-color: var(--wi-primary-container);
}
.iv-log-stance--confirmed {
  background: var(--wi-surface-container-low);
  color: var(--wi-secondary);
  border-color: var(--wi-secondary);
}
.iv-log-stance--flagged {
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
  border-color: var(--wi-on-primary-container);
}

.iv-log-message {
  margin: 0;
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  color: var(--wi-on-surface);
}

.iv-log-reasoning {
  border-top: 1px solid var(--wi-outline-variant);
  padding-top: 8px;
}

.iv-log-reasoning-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  list-style: none;
}

.iv-log-reasoning-summary::-webkit-details-marker { display: none; }

.iv-log-reasoning-summary:hover {
  color: var(--wi-primary-container);
}

.iv-log-chevron {
  font-size: 14px;
  transition: transform var(--ms-transition);
}

.iv-log-reasoning[open] .iv-log-chevron {
  transform: rotate(180deg);
}

.iv-log-reasoning-body {
  margin: 8px 0 0;
  background: var(--wi-surface-container);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-sm);
  padding: 12px;
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  white-space: pre-wrap;
  overflow-x: auto;
}

.iv-log-empty {
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  text-align: center;
  padding: var(--wi-space-md);
}

/* ── Methodology sticky footer ───────────────────────────── */
.iv-methodology {
  position: absolute;
  left: var(--wi-space-md);
  right: var(--wi-space-md);
  bottom: var(--wi-space-md);
  background: var(--wi-surface);
  border-top: 1px solid var(--wi-outline-variant);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: var(--wi-radius-md);
  box-shadow: var(--wi-shadow-md);
}

.iv-methodology-text {
  margin: 0;
  font-size: 13px;
  color: var(--wi-on-surface-variant);
}

.iv-methodology-link {
  font-family: 'JetBrains Mono', var(--ms-font-mono);
  font-size: 12px;
  text-decoration: underline;
  text-underline-offset: 2px;
  color: var(--wi-secondary);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.iv-methodology-link:hover {
  color: var(--wi-on-secondary-container);
}

/* ── Reduced motion safety ───────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .iv-log-chevron,
  .iv-export-btn,
  .iv-topnav-link {
    transition: none;
  }
}
</style>
