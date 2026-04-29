<template>
  <div class="workbench-panel">
    <div class="scroll-container">
      <!-- Step 01: Ontology -->
      <div class="step-card" :class="{ 'active': currentPhase === 0, 'completed': currentPhase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">{{ $t('process.step1.ontology.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 0" class="badge success">{{ $t('process.common.completed') }}</span>
            <span v-else-if="currentPhase === 0" class="badge processing">{{ $t('process.common.generating') }}</span>
            <span v-else class="badge pending">{{ $t('process.common.waiting') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/graph/ontology/generate</p>
          <p class="description">
            {{ $t('process.step1.ontology.description') }}
          </p>

          <!-- Loading / Progress -->
          <div v-if="currentPhase === 0 && ontologyProgress" class="progress-section">
            <div class="spinner-sm"></div>
            <span>{{ ontologyProgress.message || $t('process.step1.ontology.analyzing') }}</span>
          </div>

          <!-- Detail Overlay -->
          <div v-if="selectedOntologyItem" class="ontology-detail-overlay">
            <div class="detail-header">
               <div class="detail-title-group">
                  <span class="detail-type-badge">{{ selectedOntologyItem.itemType === 'entity' ? $t('process.step1.ontology.entityBadge') : $t('process.step1.ontology.relationBadge') }}</span>
                  <span class="detail-name">{{ selectedOntologyItem.name }}</span>
               </div>
               <button class="close-btn" @click="selectedOntologyItem = null">×</button>
            </div>
            <div class="detail-body">
               <div class="detail-desc">{{ selectedOntologyItem.description }}</div>

               <!-- Attributes -->
               <div class="detail-section" v-if="selectedOntologyItem.attributes?.length">
                  <span class="section-label">{{ $t('process.step1.ontology.attributes') }}</span>
                  <div class="attr-list">
                     <div v-for="attr in selectedOntologyItem.attributes" :key="attr.name" class="attr-item">
                        <span class="attr-name">{{ attr.name }}</span>
                        <span class="attr-type">({{ attr.type }})</span>
                        <span class="attr-desc">{{ attr.description }}</span>
                     </div>
                  </div>
               </div>

               <!-- Examples (Entity) -->
               <div class="detail-section" v-if="selectedOntologyItem.examples?.length">
                  <span class="section-label">{{ $t('process.step1.ontology.examples') }}</span>
                  <div class="example-list">
                     <span v-for="ex in selectedOntologyItem.examples" :key="ex" class="example-tag">{{ ex }}</span>
                  </div>
               </div>

               <!-- Source/Target (Relation) -->
               <div class="detail-section" v-if="selectedOntologyItem.source_targets?.length">
                  <span class="section-label">{{ $t('process.step1.ontology.connections') }}</span>
                  <div class="conn-list">
                     <div v-for="(conn, idx) in selectedOntologyItem.source_targets" :key="idx" class="conn-item">
                        <span class="conn-node">{{ conn.source }}</span>
                        <span class="conn-arrow">→</span>
                        <span class="conn-node">{{ conn.target }}</span>
                     </div>
                  </div>
               </div>
            </div>
          </div>

          <!-- Generated Entity Tags -->
          <div v-if="projectData?.ontology?.entity_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">{{ $t('process.step1.ontology.generatedEntities') }}</span>
            <div class="tags-list">
              <span
                v-for="entity in projectData.ontology.entity_types"
                :key="entity.name"
                class="entity-tag clickable"
                @click="selectOntologyItem(entity, 'entity')"
              >
                {{ entity.name }}
              </span>
            </div>
          </div>

          <!-- Generated Relation Tags -->
          <div v-if="projectData?.ontology?.edge_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">{{ $t('process.step1.ontology.generatedRelations') }}</span>
            <div class="tags-list">
              <span
                v-for="rel in projectData.ontology.edge_types"
                :key="rel.name"
                class="entity-tag clickable"
                @click="selectOntologyItem(rel, 'relation')"
              >
                {{ rel.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Graph Build -->
      <div class="step-card" :class="{ 'active': currentPhase === 1, 'completed': currentPhase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">{{ $t('process.step1.graph.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 1" class="badge success">{{ $t('process.common.completed') }}</span>
            <span v-else-if="currentPhase === 1" class="badge processing">{{ buildProgress?.progress || 0 }}%</span>
            <span v-else class="badge pending">{{ $t('process.common.waiting') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/graph/build</p>
          <p class="description">
            {{ $t('process.step1.graph.description') }}
          </p>

          <!-- Stats Cards -->
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.nodes }}</span>
              <span class="stat-label">{{ $t('process.step1.graph.entityNodes') }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.edges }}</span>
              <span class="stat-label">{{ $t('process.step1.graph.relationEdges') }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.types }}</span>
              <span class="stat-label">{{ $t('process.step1.graph.schemaTypes') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: Refine context (US-039) -->
      <div class="step-card" :class="{ 'active': refineExpanded }">
        <div class="card-header refine-header" @click="toggleRefine" role="button" :aria-expanded="refineExpanded">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">{{ $t('process.step1.refineContext.title') }}</span>
            <span class="refine-optional">{{ $t('process.step1.refineContext.optional') }}</span>
          </div>
          <div class="step-status">
            <span v-if="refineSaving" class="badge processing">{{ $t('process.step1.refineContext.saving') }}</span>
            <span v-else-if="refineSavedAt" class="badge success">{{ $t('process.step1.refineContext.saved') }}</span>
            <span class="refine-toggle" aria-hidden="true">{{ refineExpanded ? '▼' : '▶' }}</span>
          </div>
        </div>

        <div v-show="refineExpanded" class="card-content refine-content">
          <p class="description">{{ $t('process.step1.refineContext.description') }}</p>

          <!-- key_actors -->
          <div class="refine-field">
            <label class="refine-label" :for="'rc-actors-' + uid">
              {{ $t('process.step1.refineContext.keyActors.label') }}
              <span class="refine-counter">{{ contextRefinement.key_actors.length }}/8</span>
            </label>
            <p class="refine-help">{{ $t('process.step1.refineContext.keyActors.help') }}</p>
            <div class="chip-row">
              <input
                :id="'rc-actors-' + uid"
                v-model="actorDraft"
                type="text"
                class="refine-input ms-input"
                :placeholder="$t('process.step1.refineContext.keyActors.placeholder')"
                maxlength="60"
                :disabled="contextRefinement.key_actors.length >= 8"
                @keydown.enter.prevent="addActor"
              />
              <button
                type="button"
                class="refine-add-btn ms-btn"
                :disabled="!canAddActor"
                @click="addActor"
              >{{ $t('process.step1.refineContext.add') }}</button>
            </div>
            <div v-if="contextRefinement.key_actors.length" class="chip-list">
              <span
                v-for="(actor, idx) in contextRefinement.key_actors"
                :key="actor + idx"
                class="chip"
                role="button"
                :title="$t('process.step1.refineContext.removeChip')"
                @click="removeActor(idx)"
              >
                {{ actor }}<span class="chip-x" aria-hidden="true">×</span>
              </span>
            </div>
          </div>

          <!-- geo_locale -->
          <div class="refine-field">
            <label class="refine-label" :for="'rc-geo-' + uid">
              {{ $t('process.step1.refineContext.geoLocale.label') }}
            </label>
            <p class="refine-help">{{ $t('process.step1.refineContext.geoLocale.help') }}</p>
            <select
              :id="'rc-geo-' + uid"
              v-model="contextRefinement.geo_locale"
              class="refine-select ms-select"
            >
              <option value="">{{ $t('process.step1.refineContext.geoLocale.empty') }}</option>
              <option value="MA">{{ $t('process.step1.refineContext.geoLocale.options.MA') }}</option>
              <option value="DZ">{{ $t('process.step1.refineContext.geoLocale.options.DZ') }}</option>
              <option value="TN">{{ $t('process.step1.refineContext.geoLocale.options.TN') }}</option>
              <option value="SN">{{ $t('process.step1.refineContext.geoLocale.options.SN') }}</option>
              <option value="CI">{{ $t('process.step1.refineContext.geoLocale.options.CI') }}</option>
              <option value="multi">{{ $t('process.step1.refineContext.geoLocale.options.multi') }}</option>
            </select>
          </div>

          <!-- time_horizon -->
          <div class="refine-field">
            <label class="refine-label" :for="'rc-time-' + uid">
              {{ $t('process.step1.refineContext.timeHorizon.label') }}
            </label>
            <p class="refine-help">{{ $t('process.step1.refineContext.timeHorizon.help') }}</p>
            <select
              :id="'rc-time-' + uid"
              v-model="contextRefinement.time_horizon"
              class="refine-select ms-select"
            >
              <option value="">{{ $t('process.step1.refineContext.timeHorizon.empty') }}</option>
              <option value="24h">{{ $t('process.step1.refineContext.timeHorizon.options.24h') }}</option>
              <option value="72h">{{ $t('process.step1.refineContext.timeHorizon.options.72h') }}</option>
              <option value="1w">{{ $t('process.step1.refineContext.timeHorizon.options.1w') }}</option>
              <option value="2w">{{ $t('process.step1.refineContext.timeHorizon.options.2w') }}</option>
              <option value="30d">{{ $t('process.step1.refineContext.timeHorizon.options.30d') }}</option>
              <option value="60d">{{ $t('process.step1.refineContext.timeHorizon.options.60d') }}</option>
            </select>
          </div>

          <!-- key_tensions -->
          <div class="refine-field">
            <label class="refine-label" :for="'rc-tensions-' + uid">
              {{ $t('process.step1.refineContext.keyTensions.label') }}
              <span class="refine-counter">{{ contextRefinement.key_tensions.length }}/200</span>
            </label>
            <p class="refine-help">{{ $t('process.step1.refineContext.keyTensions.help') }}</p>
            <textarea
              :id="'rc-tensions-' + uid"
              v-model="contextRefinement.key_tensions"
              class="refine-textarea ms-input"
              rows="3"
              maxlength="200"
              :placeholder="$t('process.step1.refineContext.keyTensions.placeholder')"
            ></textarea>
          </div>

          <!-- expected_stakeholders -->
          <div class="refine-field">
            <label class="refine-label" :for="'rc-stakeholders-' + uid">
              {{ $t('process.step1.refineContext.expectedStakeholders.label') }}
              <span class="refine-counter">{{ contextRefinement.expected_stakeholders.length }}/8</span>
            </label>
            <p class="refine-help">{{ $t('process.step1.refineContext.expectedStakeholders.help') }}</p>
            <div class="chip-row">
              <input
                :id="'rc-stakeholders-' + uid"
                v-model="stakeholderDraft"
                type="text"
                class="refine-input ms-input"
                :placeholder="$t('process.step1.refineContext.expectedStakeholders.placeholder')"
                maxlength="60"
                :disabled="contextRefinement.expected_stakeholders.length >= 8"
                @keydown.enter.prevent="addStakeholder"
              />
              <button
                type="button"
                class="refine-add-btn ms-btn"
                :disabled="!canAddStakeholder"
                @click="addStakeholder"
              >{{ $t('process.step1.refineContext.add') }}</button>
            </div>
            <div v-if="contextRefinement.expected_stakeholders.length" class="chip-list">
              <span
                v-for="(stk, idx) in contextRefinement.expected_stakeholders"
                :key="stk + idx"
                class="chip"
                role="button"
                :title="$t('process.step1.refineContext.removeChip')"
                @click="removeStakeholder(idx)"
              >
                {{ stk }}<span class="chip-x" aria-hidden="true">×</span>
              </span>
            </div>
          </div>

          <!-- Save row -->
          <div class="refine-actions">
            <button
              type="button"
              class="refine-save-btn ms-btn"
              :disabled="refineSaving || !canSaveRefinement"
              @click="saveContextRefinement"
            >
              <span v-if="refineSaving" class="spinner-sm"></span>
              {{ refineSaving ? $t('process.step1.refineContext.saving') : $t('process.step1.refineContext.save') }}
            </button>
            <button
              v-if="hasRefinementContent"
              type="button"
              class="refine-reset-btn ms-btn"
              :disabled="refineSaving"
              @click="resetRefinement"
            >{{ $t('process.step1.refineContext.reset') }}</button>
            <span v-if="refineError" class="refine-error">{{ refineError }}</span>
          </div>
        </div>
      </div>

      <!-- Step 04: Complete -->
      <div class="step-card" :class="{ 'active': currentPhase === 2, 'completed': currentPhase >= 2 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">04</span>
            <span class="step-title">{{ $t('process.step1.complete.title') }}</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase >= 2" class="badge accent">{{ $t('process.common.readyToLaunch') }}</span>
          </div>
        </div>

        <div class="card-content">
          <p class="description">{{ $t('process.step1.complete.description') }}</p>

          <!-- Existing simulations -->
          <div v-if="existingSimulations.length > 0" class="existing-sims">
            <div
              v-for="sim in existingSimulations"
              :key="sim.simulation_id"
              class="sim-entry"
              @click="resumeSimulation(sim.simulation_id)"
            >
              <span class="sim-id mono">{{ sim.simulation_id }}</span>
              <span class="sim-status" :class="sim.status">{{ sim.status }}</span>
              <span class="sim-arrow">→</span>
            </div>
          </div>

          <div class="sim-settings">
            <label class="sim-setting-row" for="market-count-select">
              <span class="sim-setting-label">{{ $t('process.step1.complete.predictionMarkets') }}</span>
              <select
                id="market-count-select"
                class="sim-setting-select"
                v-model.number="marketCount"
                :disabled="creatingSimulation"
                :title="$t('process.step1.complete.marketCountTitle')"
              >
                <option v-for="n in 5" :key="n" :value="n">
                  {{ n }} {{ n === 1 ? $t('process.step1.complete.marketSingular') : $t('process.step1.complete.marketPlural') }}
                </option>
              </select>
            </label>
          </div>

          <button
            class="action-btn"
            :disabled="currentPhase < 2 || creatingSimulation"
            @click="handleEnterEnvSetup"
          >
            <span v-if="creatingSimulation" class="spinner-sm"></span>
            {{ creatingSimulation ? $t('process.step1.complete.creating') : (existingSimulations.length > 0 ? $t('process.step1.complete.newSimulation') : $t('process.step1.complete.enterSetup')) }}
          </button>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs" :class="{ collapsed: dashboardCollapsed }">
      <div class="log-header" @click="dashboardCollapsed = !dashboardCollapsed">
        <span class="log-title">{{ $t('process.common.systemDashboard') }} <span class="log-toggle">{{ dashboardCollapsed ? '▲' : '▼' }}</span></span>
        <span class="log-id">{{ projectData?.project_id || $t('process.common.noProject') }}</span>
      </div>
      <div v-show="!dashboardCollapsed" class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { createSimulation, listSimulations } from '../api/simulation'
import service from '../api'
import { formatApiError } from '../utils/error-handler'

const router = useRouter()
const { t } = useI18n()

const props = defineProps({
  currentPhase: { type: Number, default: 0 },
  projectData: Object,
  ontologyProgress: Object,
  buildProgress: Object,
  graphData: Object,
  systemLogs: { type: Array, default: () => [] }
})

defineEmits(['next-step'])

const selectedOntologyItem = ref(null)
const logContent = ref(null)
const dashboardCollapsed = ref(true)
const creatingSimulation = ref(false)
const existingSimulations = ref([])
const marketCount = ref(3)

// US-039 — Refine context panel state
const uid = Math.random().toString(36).slice(2, 8)
const refineExpanded = ref(false)
const refineSaving = ref(false)
const refineSavedAt = ref(null)
const refineError = ref('')
const actorDraft = ref('')
const stakeholderDraft = ref('')

// Default empty payload — keeps type stable for backend (object, never null)
const emptyRefinement = () => ({
  key_actors: [],
  geo_locale: '',
  time_horizon: '',
  key_tensions: '',
  expected_stakeholders: []
})

const contextRefinement = reactive(emptyRefinement())

// Detect which preset template was used for the current project, based on the
// project name (TemplateGallery passes `full.name`, e.g. "Crisis Drill — 24h …",
// then MainView serializes it as the upload filename and project_name). We use
// keyword matching since the backend doesn't expose template_id explicitly.
const detectedTemplateId = computed(() => {
  const haystack = `${props.projectData?.name || ''} ${props.projectData?.simulation_requirement || ''}`.toLowerCase()
  if (!haystack.trim()) return null
  if (haystack.includes('crisis') && (haystack.includes('24h') || haystack.includes('24 heures'))) return 'crisis_24h_brand'
  if (haystack.includes('pmf') || haystack.includes('product-market fit') || haystack.includes('product market fit')) return 'pmf_startup_tech'
  if (haystack.includes('policy brief') || haystack.includes('note politique')) return 'policy_brief_stress'
  if (haystack.includes('adcheck') || haystack.includes('ad check') || haystack.includes('pre-launch') || haystack.includes('pre launch')) return 'adcheck_pre_launch'
  if (haystack.includes('product launch') || haystack.includes('lancement produit')) return 'product_launch_v2'
  return null
})

// Suggested defaults per template (per US-039 mapping table)
const TEMPLATE_DEFAULTS = {
  crisis_24h_brand:   { time_horizon: '24h', geo_locale: 'MA' },
  pmf_startup_tech:   { time_horizon: '30d', geo_locale: 'multi' },
  policy_brief_stress: { time_horizon: '1w',  geo_locale: 'multi' },
  adcheck_pre_launch: { time_horizon: '72h', geo_locale: 'multi' },
  product_launch_v2:  { time_horizon: '2w',  geo_locale: 'multi' }
}

// Apply template defaults — only when the field is still empty so we never
// overwrite a user choice. Triggered when projectData lands or template id changes.
const applyTemplateDefaults = () => {
  const tplId = detectedTemplateId.value
  if (!tplId) return
  const defaults = TEMPLATE_DEFAULTS[tplId]
  if (!defaults) return
  if (!contextRefinement.time_horizon && defaults.time_horizon) {
    contextRefinement.time_horizon = defaults.time_horizon
  }
  if (!contextRefinement.geo_locale && defaults.geo_locale) {
    contextRefinement.geo_locale = defaults.geo_locale
  }
}

// Storage key derived from project_id so refinements persist on reload but
// don't leak across projects.
const storageKey = computed(() => {
  const pid = props.projectData?.project_id
  return pid ? `bassira:context_refinement:${pid}` : null
})

const loadRefinementFromStorage = () => {
  if (!storageKey.value) return
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') {
      if (Array.isArray(parsed.key_actors)) contextRefinement.key_actors = parsed.key_actors.slice(0, 8)
      if (typeof parsed.geo_locale === 'string') contextRefinement.geo_locale = parsed.geo_locale
      if (typeof parsed.time_horizon === 'string') contextRefinement.time_horizon = parsed.time_horizon
      if (typeof parsed.key_tensions === 'string') contextRefinement.key_tensions = parsed.key_tensions.slice(0, 200)
      if (Array.isArray(parsed.expected_stakeholders)) contextRefinement.expected_stakeholders = parsed.expected_stakeholders.slice(0, 8)
      if (parsed._savedAt) refineSavedAt.value = parsed._savedAt
    }
  } catch (_) {
    // silently ignore corrupt storage
  }
}

const persistRefinementToStorage = () => {
  if (!storageKey.value) return
  try {
    localStorage.setItem(storageKey.value, JSON.stringify({
      ...contextRefinement,
      _savedAt: refineSavedAt.value
    }))
  } catch (_) {
    // quota or sandbox — keep in-memory state, don't surface
  }
}

const toggleRefine = () => {
  refineExpanded.value = !refineExpanded.value
}

// Chip handling — key_actors
const canAddActor = computed(() => {
  const v = actorDraft.value.trim()
  return v.length > 0 && v.length <= 60 && contextRefinement.key_actors.length < 8 && !contextRefinement.key_actors.includes(v)
})
const addActor = () => {
  if (!canAddActor.value) return
  contextRefinement.key_actors.push(actorDraft.value.trim())
  actorDraft.value = ''
}
const removeActor = (idx) => {
  contextRefinement.key_actors.splice(idx, 1)
}

// Chip handling — expected_stakeholders
const canAddStakeholder = computed(() => {
  const v = stakeholderDraft.value.trim()
  return v.length > 0 && v.length <= 60 && contextRefinement.expected_stakeholders.length < 8 && !contextRefinement.expected_stakeholders.includes(v)
})
const addStakeholder = () => {
  if (!canAddStakeholder.value) return
  contextRefinement.expected_stakeholders.push(stakeholderDraft.value.trim())
  stakeholderDraft.value = ''
}
const removeStakeholder = (idx) => {
  contextRefinement.expected_stakeholders.splice(idx, 1)
}

const hasRefinementContent = computed(() => (
  contextRefinement.key_actors.length > 0 ||
  contextRefinement.expected_stakeholders.length > 0 ||
  !!contextRefinement.geo_locale ||
  !!contextRefinement.time_horizon ||
  !!contextRefinement.key_tensions.trim()
))

const canSaveRefinement = computed(() => (
  !!props.projectData?.project_id && hasRefinementContent.value
))

const resetRefinement = () => {
  contextRefinement.key_actors = []
  contextRefinement.geo_locale = ''
  contextRefinement.time_horizon = ''
  contextRefinement.key_tensions = ''
  contextRefinement.expected_stakeholders = []
  actorDraft.value = ''
  stakeholderDraft.value = ''
  refineSavedAt.value = null
  refineError.value = ''
  if (storageKey.value) {
    try { localStorage.removeItem(storageKey.value) } catch (_) {}
  }
}

// Build the JSON payload sent to the backend. Empty fields are kept so the
// backend always receives the same shape (object, partials allowed).
const buildRefinementPayload = () => ({
  key_actors: [...contextRefinement.key_actors],
  geo_locale: contextRefinement.geo_locale || '',
  time_horizon: contextRefinement.time_horizon || '',
  key_tensions: (contextRefinement.key_tensions || '').trim(),
  expected_stakeholders: [...contextRefinement.expected_stakeholders]
})

const saveContextRefinement = async () => {
  if (!props.projectData?.project_id) return
  refineSaving.value = true
  refineError.value = ''
  const payload = {
    project_id: props.projectData.project_id,
    context_refinement: buildRefinementPayload(),
    refinement_only: true
  }
  try {
    const res = await service({
      url: '/api/graph/build',
      method: 'post',
      data: payload
    })
    const data = res?.data ?? res
    if (data && data.success === false) {
      // Backend may not yet support refinement_only — keep local state intact
      // but flag the error so the user knows it didn't reach the server.
      refineError.value = data.error || t('process.step1.refineContext.saveFailedFallback')
    } else {
      refineSavedAt.value = new Date().toISOString()
    }
  } catch (err) {
    // Same defensive behaviour : we still persist locally so the form state
    // isn't lost even if the optional backend hook is missing.
    refineError.value = err?.response?.data?.error || err?.message || t('process.step1.refineContext.saveFailedFallback')
  } finally {
    persistRefinementToStorage()
    refineSaving.value = false
  }
}

// Check for existing simulations for this project
const loadExistingSimulations = async () => {
  if (!props.projectData?.project_id) return
  try {
    const res = await listSimulations(props.projectData.project_id)
    if (res.success && res.data) {
      existingSimulations.value = res.data
    }
  } catch (err) {
    // silent
  }
}

onMounted(() => {
  loadExistingSimulations()
  loadRefinementFromStorage()
  applyTemplateDefaults()
})
watch(() => props.projectData?.project_id, () => {
  loadExistingSimulations()
  // New project landed → reset stale state then hydrate from storage + template
  refineSavedAt.value = null
  refineError.value = ''
  loadRefinementFromStorage()
  applyTemplateDefaults()
})

// Persist on every meaningful change (debounced via watch's flush:'post')
watch(
  () => [
    contextRefinement.key_actors.length,
    contextRefinement.expected_stakeholders.length,
    contextRefinement.geo_locale,
    contextRefinement.time_horizon,
    contextRefinement.key_tensions
  ],
  () => {
    persistRefinementToStorage()
  },
  { flush: 'post' }
)

const resumeSimulation = (simId) => {
  router.push({ name: 'Simulation', params: { simulationId: simId } })
}

// Enter agent setup - create simulation and navigate
const handleEnterEnvSetup = async () => {
  if (!props.projectData?.project_id || !props.projectData?.graph_id) {
    console.error('Missing project or graph information')
    return
  }

  creatingSimulation.value = true

  try {
    const simPayload = {
      project_id: props.projectData.project_id,
      graph_id: props.projectData.graph_id,
      enable_twitter: true,
      enable_reddit: true,
      enable_polymarket: true,
      polymarket_market_count: marketCount.value,
    }
    // US-039 — forward the refined context to downstream agent setup so a
    // template-only run still benefits from the user's locale / time horizon.
    // We send only when at least one field is set to keep the payload tidy.
    if (hasRefinementContent.value) {
      simPayload.context_refinement = buildRefinementPayload()
    }

    const res = await createSimulation(simPayload)

    if (res.success && res.data?.simulation_id) {
      // Navigate to simulation page
      router.push({
        name: 'Simulation',
        params: { simulationId: res.data.simulation_id }
      })
    } else {
      console.error('Failed to create simulation:', res.error)
      alert(t('process.step1.complete.createFailed', { error: res.error || t('process.step1.complete.unknownError') }))
    }
  } catch (err) {
    console.error('Simulation creation error:', err)
    // US-007: feed the localised, error_code-aware message into the existing
    // i18n template so codes like GRAPH_EMPTY (US-047) surface in fr/ar.
    alert(t('process.step1.complete.createError', { error: formatApiError(err, t) }))
  } finally {
    creatingSimulation.value = false
  }
}

const selectOntologyItem = (item, type) => {
  selectedOntologyItem.value = { ...item, itemType: type }
}

const graphStats = computed(() => {
  const nodes = props.graphData?.node_count || props.graphData?.nodes?.length || 0
  const edges = props.graphData?.edge_count || props.graphData?.edges?.length || 0
  const types = props.projectData?.ontology?.entity_types?.length || 0
  return { nodes, edges, types }
})

const formatDate = (dateStr) => {
  if (!dateStr) return '--:--:--'
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-US', { hour12: false }) + '.' + d.getMilliseconds()
}

// Auto-scroll logs
watch(() => props.systemLogs.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.workbench-panel {
  height: 100%;
  background-color: #FAFAFA;
  background-image:
    linear-gradient(rgba(10,10,10,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(10,10,10,0.03) 1px, transparent 1px);
  background-size: 22px 22px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.step-card {
  background: #FAFAFA;
  padding: 22px;
  border: 2px solid rgba(10,10,10,0.08);
  transition: all 0.3s ease;
  position: relative;
}

/* Corner markers: orange top-left, green bottom-right */
.step-card::before {
  content: '';
  position: absolute;
  top: 0;
  inset-inline-start: 0;
  width: 16px;
  height: 16px;
  border-top: 3px solid #FF6B1A;
  border-inline-start: 3px solid #FF6B1A;
}

.step-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  inset-inline-end: 0;
  width: 16px;
  height: 16px;
  border-bottom: 3px solid #43C165;
  border-inline-end: 3px solid #43C165;
}

.step-card.active {
  border-color: #FF6B1A;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 11px;
}

.step-num {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  color: rgba(10,10,10,0.12);
}

.step-card.active .step-num,
.step-card.completed .step-num {
  color: #0A0A0A;
}

.step-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.badge {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 4px 8px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
}

.badge.success { background: #43C165; color: #FAFAFA; }
.badge.processing { background: #FF6B1A; color: #FAFAFA; }
.badge.accent { background: #FF6B1A; color: #FAFAFA; }
.badge.pending { background: #F5F5F5; color: rgba(10,10,10,0.4); }

.api-note {
  font-family: var(--font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.4);
  margin-bottom: 8px;
}

.description {
  font-size: 12px;
  color: rgba(10,10,10,0.5);
  line-height: 1.5;
  margin-bottom: 22px;
}

/* Step 01 Tags */
.tags-container {
  margin-top: 11px;
  transition: opacity 0.3s;
}

.tags-container.dimmed {
    opacity: 0.3;
    pointer-events: none;
}

.tag-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 11px;
  color: rgba(10,10,10,0.4);
  margin-bottom: 8px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.entity-tag {
  background: #F5F5F5;
  border: 1px solid rgba(10,10,10,0.08);
  padding: 4px 10px;
  font-size: 11px;
  color: rgba(10,10,10,0.7);
  font-family: var(--font-mono);
  transition: all 0.2s;
}

.entity-tag.clickable {
    cursor: pointer;
}

.entity-tag.clickable:hover {
    background: rgba(10,10,10,0.12);
    border-color: rgba(10,10,10,0.2);
}

/* Ontology Detail Overlay */
.ontology-detail-overlay {
    position: absolute;
    top: 60px;
    inset-inline-start: 22px;
    inset-inline-end: 22px;
    bottom: 22px;
    background: rgba(250, 250, 250, 0.98);
    backdrop-filter: blur(4px);
    z-index: 10;
    border: 2px solid rgba(10,10,10,0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

.detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 11px 22px;
    border-bottom: 2px solid rgba(10,10,10,0.08);
    background: #FAFAFA;
}

.detail-title-group {
    display: flex;
    align-items: center;
    gap: 8px;
}

.detail-type-badge {
    font-family: var(--font-mono);
    font-size: 9px;
    font-weight: 700;
    color: #FAFAFA;
    background: #0A0A0A;
    padding: 2px 6px;
    text-transform: uppercase;
    letter-spacing: 3px;
}

.detail-name {
    font-size: 14px;
    font-weight: 700;
    font-family: var(--font-mono);
}

.close-btn {
    background: none;
    border: none;
    font-size: 18px;
    color: rgba(10,10,10,0.4);
    cursor: pointer;
    line-height: 1;
}

.close-btn:hover {
    color: rgba(10,10,10,0.7);
}

.detail-body {
    flex: 1;
    overflow-y: auto;
    padding: 22px;
}

.detail-desc {
    font-size: 12px;
    color: rgba(10,10,10,0.6);
    line-height: 1.5;
    margin-bottom: 22px;
    padding-bottom: 11px;
    border-bottom: 1px dashed rgba(10,10,10,0.08);
}

.detail-section {
    margin-bottom: 22px;
}

.section-label {
    display: block;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    color: rgba(10,10,10,0.4);
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 3px;
}

.attr-list, .conn-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.attr-item {
    font-size: 11px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: baseline;
    padding: 4px;
    background: #F5F5F5;
}

.attr-name {
    font-family: var(--font-mono);
    font-weight: 600;
    color: #0A0A0A;
}

.attr-type {
    color: rgba(10,10,10,0.4);
    font-size: 10px;
}

.attr-desc {
    color: rgba(10,10,10,0.5);
    flex: 1;
    min-width: 150px;
}

.example-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.example-tag {
    font-size: 11px;
    background: #FAFAFA;
    border: 1px solid rgba(10,10,10,0.12);
    padding: 3px 8px;
    color: rgba(10,10,10,0.5);
}

.conn-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    padding: 6px;
    background: #F5F5F5;
    font-family: var(--font-mono);
}

.conn-node {
    font-weight: 600;
    color: rgba(10,10,10,0.7);
}

.conn-arrow {
    color: rgba(10,10,10,0.2);
}

/* Step 02 Stats */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 11px;
  background: #F5F5F5;
  padding: 22px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #0A0A0A;
  font-family: var(--font-mono);
}

.stat-label {
  font-family: var(--font-mono);
  font-size: 9px;
  color: rgba(10,10,10,0.4);
  text-transform: uppercase;
  letter-spacing: 3px;
  margin-top: 4px;
  display: block;
}

/* Pre-launch simulation settings row (number of prediction markets, etc.) */
.sim-settings {
  margin-bottom: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(10, 10, 10, 0.08);
  background: rgba(10, 10, 10, 0.015);
  font-family: var(--font-mono);
}

.sim-setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sim-setting-label {
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: rgba(10, 10, 10, 0.55);
  font-weight: 600;
}

.sim-setting-select {
  background: var(--color-white);
  border: 1px solid rgba(10, 10, 10, 0.15);
  padding: 4px 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-black);
  cursor: pointer;
  outline: none;
  border-radius: 0;
}

.sim-setting-select:focus {
  border-color: var(--color-orange);
}

.sim-setting-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Step 03 Button */
.action-btn {
  width: 100%;
  background: #0A0A0A;
  color: #FAFAFA;
  border: none;
  padding: 14px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.action-btn:hover:not(:disabled) {
  opacity: 0.8;
}

.action-btn:disabled {
  background: rgba(10,10,10,0.2);
  cursor: not-allowed;
}

.existing-sims {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 11px;
}

.sim-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  border: 2px solid rgba(10,10,10,0.12);
  cursor: pointer;
  transition: all 0.15s;
  font-size: 11px;
}

.sim-entry:hover {
  background: #F5F5F5;
  border-color: rgba(10,10,10,0.7);
}

.sim-id {
  flex: 1;
  color: rgba(10,10,10,0.7);
  font-weight: 500;
}

.sim-status {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
  padding: 2px 6px;
  background: #F5F5F5;
  color: rgba(10,10,10,0.5);
}

.sim-status.ready, .sim-status.completed { color: #FAFAFA; background: #43C165; }
.sim-status.running { color: #FAFAFA; background: #FF6B1A; }
.sim-status.failed { color: #FAFAFA; background: #FF4444; }
.sim-status.paused, .sim-status.stopped { color: #0A0A0A; background: #FFB347; }

.sim-arrow {
  color: rgba(10,10,10,0.4);
  font-size: 12px;
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 11px;
  font-size: 12px;
  color: #FF6B1A;
  margin-bottom: 11px;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,107,26,0.3);
  border-top-color: #FF6B1A;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* System Logs */
.system-logs {
  background: #0A0A0A;
  color: rgba(250,250,250,0.8);
  padding: 22px;
  font-family: var(--font-mono);
  border-top: 2px solid rgba(250,250,250,0.08);
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid rgba(250,250,250,0.1);
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: rgba(250,250,250,0.4);
  text-transform: uppercase;
  letter-spacing: 3px;
  cursor: pointer;
  user-select: none;
}

.system-logs.collapsed .log-header {
  border-bottom: none;
  padding-bottom: 0;
  margin-bottom: 0;
}

.log-toggle {
  font-size: 8px;
  opacity: 0.5;
  margin-inline-start: 4px;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 80px;
  overflow-y: auto;
  padding-inline-end: 4px;
}

.log-content::-webkit-scrollbar {
  width: 4px;
}

.log-content::-webkit-scrollbar-thumb {
  background: rgba(250,250,250,0.15);
}

.log-line {
  font-size: 11px;
  display: flex;
  gap: 11px;
  line-height: 1.5;
}

.log-time {
  color: #FF6B1A;
  min-width: 75px;
}

.log-msg {
  color: rgba(250,250,250,0.6);
  word-break: break-all;
}

.log-id {
  color: #43C165;
}

/* ── US-039 — Refine context panel ── */
.refine-header {
  cursor: pointer;
  user-select: none;
}

.refine-optional {
  font-family: var(--font-mono);
  font-size: 9px;
  color: rgba(10,10,10,0.4);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-inline-start: 6px;
}

.refine-toggle {
  font-family: var(--font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.4);
  margin-inline-start: 8px;
}

.refine-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.refine-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.refine-label {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: rgba(10,10,10,0.7);
  text-transform: uppercase;
  letter-spacing: 2px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.refine-counter {
  font-family: var(--font-mono);
  font-size: 10px;
  color: rgba(10,10,10,0.4);
  font-weight: 500;
  letter-spacing: 1px;
}

.refine-help {
  font-size: 11px;
  color: rgba(10,10,10,0.5);
  margin: 0;
  line-height: 1.4;
}

.refine-input,
.refine-select,
.refine-textarea {
  background: var(--ms-bg, #FAFAFA);
  border: 1px solid rgba(10,10,10,0.15);
  padding: 8px 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ms-text, #0A0A0A);
  outline: none;
  border-radius: 0;
  width: 100%;
  box-sizing: border-box;
}

.refine-input:focus,
.refine-select:focus,
.refine-textarea:focus {
  border-color: var(--ms-orange, #FF6B1A);
}

.refine-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refine-textarea {
  resize: vertical;
  min-height: 60px;
  line-height: 1.4;
}

.chip-row {
  display: flex;
  gap: 6px;
  align-items: stretch;
  flex-wrap: wrap;
}

.chip-row .refine-input {
  flex: 1;
  min-width: 180px;
}

.refine-add-btn,
.refine-save-btn,
.refine-reset-btn {
  background: var(--ms-text, #0A0A0A);
  color: var(--ms-text-on-color, #FAFAFA);
  border: none;
  padding: 8px 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  cursor: pointer;
  transition: opacity 0.2s;
  border-radius: 0;
  white-space: nowrap;
}

.refine-add-btn:hover:not(:disabled),
.refine-save-btn:hover:not(:disabled),
.refine-reset-btn:hover:not(:disabled) {
  opacity: 0.85;
}

.refine-add-btn:disabled,
.refine-save-btn:disabled,
.refine-reset-btn:disabled {
  background: rgba(10,10,10,0.2);
  cursor: not-allowed;
}

.refine-reset-btn {
  background: transparent;
  color: rgba(10,10,10,0.6);
  border: 1px solid rgba(10,10,10,0.15);
}

.refine-reset-btn:hover:not(:disabled) {
  color: var(--ms-text, #0A0A0A);
  border-color: rgba(10,10,10,0.4);
  opacity: 1;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--ms-orange-soft, #FFE3D1);
  border: 1px solid var(--ms-orange, #FF6B1A);
  padding: 4px 10px;
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--ms-text, #0A0A0A);
  cursor: pointer;
  transition: all 0.15s;
  border-radius: 0;
}

.chip:hover {
  background: var(--ms-orange, #FF6B1A);
  color: var(--ms-text-on-color, #FAFAFA);
}

.chip-x {
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  margin-inline-start: 2px;
}

.refine-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  padding-top: 6px;
  border-top: 1px dashed rgba(10,10,10,0.08);
}

.refine-error {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ms-rose, #FF4444);
  flex: 1;
  min-width: 180px;
}

/* Mobile responsive */
@media (max-width: 600px) {
  .chip-row {
    flex-direction: column;
  }
  .chip-row .refine-input {
    min-width: 0;
  }
  .refine-add-btn,
  .refine-save-btn,
  .refine-reset-btn {
    width: 100%;
  }
  .refine-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
