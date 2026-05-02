<template>
  <div class="rev-page">
    <!-- ─── Top bar (back + project context) ─── -->
    <header class="rev-topbar">
      <router-link
        :to="{ name: 'Process', params: { projectId } }"
        class="rev-back"
        :title="$t('process.review.nav.backTitle')"
      >
        <span class="rev-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('process.review.nav.back') }}</span>
      </router-link>
      <div class="rev-step-pill">
        <span class="rev-step-num">1.5</span>
        <span class="rev-step-label">{{ $t('process.review.title') }}</span>
      </div>
    </header>

    <main class="rev-main">
      <!-- ─── Hero / explanation card ─── -->
      <section class="rev-hero">
        <h1 class="rev-headline">{{ $t('process.review.title') }}</h1>
        <p class="rev-help">{{ $t('process.review.helpText') }}</p>
        <div v-if="loading" class="rev-stats rev-stats--loading">
          <span class="rev-skeleton" aria-hidden="true"></span>
        </div>
        <div v-else class="rev-stats">
          <span class="rev-stat-item">
            <span class="rev-stat-num">{{ entities.length }}</span>
            <span class="rev-stat-label">{{ $t('process.review.stats.entities') }}</span>
          </span>
          <span class="rev-stat-sep" aria-hidden="true">·</span>
          <span class="rev-stat-item">
            <span class="rev-stat-num">{{ groupedTypes.length }}</span>
            <span class="rev-stat-label">{{ $t('process.review.stats.types') }}</span>
          </span>
          <span v-if="pendingOpsCount > 0" class="rev-stat-sep" aria-hidden="true">·</span>
          <span v-if="pendingOpsCount > 0" class="rev-stat-item rev-stat-item--pending">
            <span class="rev-stat-num">{{ pendingOpsCount }}</span>
            <span class="rev-stat-label">{{ $t('process.review.stats.pending') }}</span>
          </span>
          <span class="rev-stat-sep" aria-hidden="true">·</span>
          <span class="rev-stat-item rev-stat-item--valid">
            <span class="rev-stat-num">{{ validCount }}</span>
            <span class="rev-stat-label">{{ $t('process.review.badges.valid') }}</span>
          </span>
        </div>
      </section>

      <!-- ─── Error banner ─── -->
      <section v-if="errorMsg" class="rev-error" role="alert">
        <div class="rev-error-icon" aria-hidden="true">!</div>
        <div class="rev-error-body">
          <div class="rev-error-title">{{ $t('process.review.error.title') }}</div>
          <div class="rev-error-msg">{{ errorMsg }}</div>
        </div>
        <button class="rev-btn rev-btn--ghost rev-btn--sm" @click="fetchEntities">
          {{ $t('process.review.error.retry') }}
        </button>
      </section>

      <!-- ─── Loading skeleton ─── -->
      <section v-if="loading" class="rev-loading">
        <div class="rev-skeleton-block"></div>
        <div class="rev-skeleton-block"></div>
      </section>

      <!-- ─── Two-column workspace ─── -->
      <template v-else>
        <section v-if="entities.length === 0" class="rev-empty-hint">
          <div class="rev-empty-icon" aria-hidden="true">⚐</div>
          <p>{{ $t('process.review.empty') }}</p>
        </section>

        <div v-else class="rev-workspace">
          <!-- ─── Left column: filters + entity list (70%) ─── -->
          <div class="rev-list-col">
            <!-- Filter chips toolbar -->
            <div class="rev-filters">
              <div class="rev-chip-row">
                <button
                  type="button"
                  class="rev-chip"
                  :class="{ 'rev-chip--active': selectedType === 'all' }"
                  @click="selectedType = 'all'"
                >
                  <span aria-hidden="true">●</span>
                  {{ $t('process.review.filters.all') }}
                  <span class="rev-chip-count">{{ entities.length }}</span>
                </button>
                <button
                  v-for="group in groupedTypes"
                  :key="group.type"
                  type="button"
                  class="rev-chip"
                  :class="{ 'rev-chip--active': selectedType === group.type }"
                  @click="selectedType = group.type"
                >
                  <span aria-hidden="true">{{ typeIcon(group.type) }}</span>
                  {{ typeLabel(group.type) }}
                  <span class="rev-chip-count">{{ group.entities.length }}</span>
                </button>
              </div>
              <div class="rev-search">
                <span class="rev-search-icon" aria-hidden="true">⌕</span>
                <input
                  v-model.trim="searchQuery"
                  type="text"
                  class="rev-search-input"
                  :placeholder="$t('process.review.filters.searchPlaceholder')"
                />
              </div>
            </div>

            <!-- Entity list (scrollable) -->
            <div class="rev-list-scroll">
              <div v-if="filteredEntities.length === 0" class="rev-empty-list">
                <p>{{ $t('process.review.empty') }}</p>
              </div>
              <ul v-else class="rev-entity-list">
                <li
                  v-for="entity in filteredEntities"
                  :key="entity.uuid"
                  class="rev-entity-card"
                  :class="entityCardClasses(entity)"
                  @click="selectEntity(entity)"
                >
                  <div class="rev-entity-checkcol">
                    <input
                      type="checkbox"
                      class="rev-checkbox"
                      :checked="batchSelected.has(entity.uuid)"
                      :disabled="isDeleted(entity.uuid)"
                      :aria-label="entity.name"
                      @click.stop
                      @change="toggleBatch(entity)"
                    />
                    <span class="rev-status-chip" :class="`rev-status-chip--${statusOf(entity)}`">
                      {{ statusLabel(entity) }}
                    </span>
                  </div>
                  <div class="rev-entity-body">
                    <div class="rev-entity-head">
                      <div class="rev-entity-name">
                        <input
                          v-if="editingUuid === entity.uuid"
                          :ref="el => bindEditInput(el)"
                          v-model.trim="editingName"
                          class="rev-name-input"
                          type="text"
                          :maxlength="200"
                          :placeholder="entity.name"
                          @click.stop
                          @keydown.enter.prevent="commitRename(entity)"
                          @keydown.esc.prevent="cancelEdit"
                          @blur="commitRename(entity)"
                        />
                        <button
                          v-else
                          class="rev-name-btn"
                          type="button"
                          :title="$t('process.review.actions.rename')"
                          @click.stop="startEdit(entity)"
                        >
                          <span class="rev-name-text">{{ displayName(entity) }}</span>
                          <span
                            v-if="isRenamed(entity.uuid)"
                            class="rev-badge rev-badge--info"
                            :title="$t('process.review.badges.renamed')"
                          >
                            {{ $t('process.review.badges.renamed') }}
                          </span>
                          <span
                            v-if="isMerged(entity.uuid)"
                            class="rev-badge rev-badge--info"
                            :title="$t('process.review.badges.merged')"
                          >
                            {{ $t('process.review.badges.merged') }}
                          </span>
                        </button>
                      </div>
                      <div class="rev-entity-meta-right">
                        <span class="rev-entity-type">
                          <span aria-hidden="true">{{ typeIcon(getEntityType(entity)) }}</span>
                          {{ typeLabel(getEntityType(entity)) }}
                        </span>
                      </div>
                    </div>
                    <p class="rev-entity-snippet">
                      <span class="rev-entity-uuid ms-mono">{{ entity.uuid.slice(0, 8) }}</span>
                      <span class="rev-entity-dot" aria-hidden="true">·</span>
                      <span>{{ getEntityType(entity) }}</span>
                    </p>
                  </div>
                </li>
              </ul>
            </div>

            <!-- Add new entity (compact) -->
            <div class="rev-add-section">
              <details class="rev-add-details">
                <summary class="rev-add-summary">
                  <span aria-hidden="true">+</span>
                  {{ $t('process.review.add.newTypeTitle') }}
                </summary>
                <div class="rev-add-body">
                  <p class="rev-help-sm">{{ $t('process.review.add.newTypeHelp') }}</p>
                  <div class="rev-add-row">
                    <input
                      v-model.trim="newTypeName"
                      class="rev-input"
                      type="text"
                      :maxlength="200"
                      :placeholder="$t('process.review.add.namePlaceholder')"
                      @keydown.enter.prevent="addEntityWithCustomType"
                    />
                    <input
                      v-model.trim="newTypeType"
                      class="rev-input rev-input--narrow"
                      type="text"
                      :maxlength="60"
                      :placeholder="$t('process.review.add.typePlaceholder')"
                      @keydown.enter.prevent="addEntityWithCustomType"
                    />
                    <button
                      class="rev-btn rev-btn--secondary rev-btn--sm"
                      type="button"
                      :disabled="!canAddCustom"
                      @click="addEntityWithCustomType"
                    >
                      + {{ $t('process.review.add.button') }}
                    </button>
                  </div>
                  <ul v-if="additions.length" class="rev-additions">
                    <li
                      v-for="(add, idx) in additions"
                      :key="`${add.entity_type}-${idx}-${add.name}`"
                      class="rev-addition-row"
                    >
                      <span class="rev-badge rev-badge--success">+</span>
                      <span class="rev-addition-name">{{ add.name }}</span>
                      <span class="rev-addition-type ms-mono">{{ add.entity_type }}</span>
                      <button
                        class="rev-btn rev-btn--ghost rev-btn--sm"
                        type="button"
                        :title="$t('process.review.add.remove')"
                        @click="removeAddition(add)"
                      >
                        ✕
                      </button>
                    </li>
                  </ul>
                </div>
              </details>
            </div>
          </div>

          <!-- ─── Right column: detail panel (30%) ─── -->
          <aside class="rev-detail-col" :class="{ 'rev-detail-col--empty': !selectedEntity }">
            <template v-if="selectedEntity">
              <div class="rev-detail-head">
                <div class="rev-detail-head-titles">
                  <span class="rev-detail-eyebrow">{{ $t('process.review.panel.selected') }}</span>
                  <h2 class="rev-detail-title">{{ displayName(selectedEntity) }}</h2>
                </div>
                <button
                  class="rev-detail-close"
                  type="button"
                  :title="$t('process.review.panel.close')"
                  @click="selectedEntity = null"
                >
                  ✕
                </button>
              </div>

              <div class="rev-detail-body">
                <!-- Validation status segmented control -->
                <div class="rev-field">
                  <label class="rev-field-label">{{ $t('process.review.panel.status') }}</label>
                  <div class="rev-segmented">
                    <button
                      type="button"
                      class="rev-seg"
                      :class="{ 'rev-seg--active rev-seg--valid': statusOf(selectedEntity) === 'valid' }"
                      @click="setStatus(selectedEntity, 'valid')"
                    >
                      ✓ {{ $t('process.review.badges.valid') }}
                    </button>
                    <button
                      type="button"
                      class="rev-seg"
                      :class="{ 'rev-seg--active rev-seg--flagged': statusOf(selectedEntity) === 'flagged' }"
                      @click="setStatus(selectedEntity, 'flagged')"
                    >
                      ⚑ {{ $t('process.review.badges.flagged') }}
                    </button>
                    <button
                      type="button"
                      class="rev-seg"
                      :class="{ 'rev-seg--active rev-seg--removed': statusOf(selectedEntity) === 'removed' }"
                      @click="setStatus(selectedEntity, 'removed')"
                    >
                      ⊘ {{ $t('process.review.badges.removed') }}
                    </button>
                  </div>
                </div>

                <!-- Canonical name -->
                <div class="rev-field">
                  <label class="rev-field-label">{{ $t('process.review.panel.canonicalName') }}</label>
                  <input
                    type="text"
                    class="rev-input rev-input--full"
                    :class="{ 'rev-input--editing': editMode }"
                    :value="displayName(selectedEntity)"
                    :maxlength="200"
                    @focus="editMode = true"
                    @blur="onPanelNameBlur(selectedEntity, $event)"
                    @keydown.enter.prevent="onPanelNameEnter(selectedEntity, $event)"
                  />
                </div>

                <!-- Category + UUID row -->
                <div class="rev-field-row">
                  <div class="rev-field rev-field--grow">
                    <label class="rev-field-label">{{ $t('process.review.panel.category') }}</label>
                    <div class="rev-readonly-pill">
                      <span aria-hidden="true">{{ typeIcon(getEntityType(selectedEntity)) }}</span>
                      {{ getEntityType(selectedEntity) }}
                    </div>
                  </div>
                  <div class="rev-field rev-field--narrow">
                    <label class="rev-field-label">UUID</label>
                    <div class="rev-readonly-pill ms-mono">
                      {{ selectedEntity.uuid.slice(0, 8) }}
                    </div>
                  </div>
                </div>

                <!-- Merge target -->
                <div class="rev-field">
                  <label class="rev-field-label">{{ $t('process.review.panel.mergeInto') }}</label>
                  <select
                    class="rev-input rev-input--full"
                    :value="getMergeTarget(selectedEntity.uuid) || ''"
                    :disabled="isDeleted(selectedEntity.uuid)"
                    @change="onMergeChange(selectedEntity, $event)"
                  >
                    <option value="">{{ $t('process.review.panel.noMergeTarget') }}</option>
                    <option
                      v-for="other in mergeCandidatesFor(selectedEntity)"
                      :key="other.uuid"
                      :value="other.uuid"
                    >
                      {{ displayName(other) }}
                    </option>
                  </select>
                </div>

                <!-- Notes -->
                <div class="rev-field">
                  <label class="rev-field-label">{{ $t('process.review.panel.notes') }}</label>
                  <textarea
                    class="rev-input rev-input--full rev-textarea"
                    :class="{ 'rev-input--flagged': statusOf(selectedEntity) === 'flagged' }"
                    rows="3"
                    :placeholder="$t('process.review.panel.notesPlaceholder')"
                    :value="entityNotes[selectedEntity.uuid] || ''"
                    @input="onNotesInput(selectedEntity, $event)"
                  ></textarea>
                </div>
              </div>
            </template>

            <div v-else class="rev-detail-empty">
              <div class="rev-detail-empty-icon" aria-hidden="true">◎</div>
              <h3 class="rev-detail-empty-title">{{ $t('process.review.panel.noSelection') }}</h3>
              <p class="rev-detail-empty-help">{{ $t('process.review.panel.noSelectionHelp') }}</p>
            </div>
          </aside>
        </div>
      </template>

      <!-- ─── Sticky footer / batch actions ─── -->
      <footer class="rev-footer">
        <div class="rev-footer-left">
          <template v-if="batchSelected.size > 0">
            <span class="rev-footer-count">
              {{ $t('process.review.batch.selected', { count: batchSelected.size }) }}
            </span>
            <span class="rev-footer-sep" aria-hidden="true"></span>
            <button class="rev-batch-btn rev-batch-btn--valid" type="button" @click="batchValidate">
              <span aria-hidden="true">✓</span>
              {{ $t('process.review.actions.validate') }}
            </button>
            <button class="rev-batch-btn rev-batch-btn--flag" type="button" @click="batchFlag">
              <span aria-hidden="true">⚑</span>
              {{ $t('process.review.actions.flag') }}
            </button>
            <button class="rev-batch-btn rev-batch-btn--remove" type="button" @click="batchRemove">
              <span aria-hidden="true">⊘</span>
              {{ $t('process.review.actions.removeSelection') }}
            </button>
            <button class="rev-batch-btn" type="button" @click="batchSelected.clear()">
              {{ $t('process.review.actions.clearSelection') }}
            </button>
          </template>
          <template v-else>
            <span class="rev-footer-summary">
              <span class="rev-summary-pill rev-summary-pill--valid">
                {{ $t('process.review.summary.valid', { count: validCount }) }}
              </span>
              <span class="rev-summary-pill rev-summary-pill--flagged">
                {{ $t('process.review.summary.flagged', { count: flaggedCount }) }}
              </span>
              <span class="rev-summary-pill rev-summary-pill--removed">
                {{ $t('process.review.summary.removed', { count: removedCount }) }}
              </span>
              <span v-if="!canLaunch && !loading" class="rev-summary-warn">
                {{ $t('process.review.summary.minRequired') }}
              </span>
            </span>
          </template>
        </div>
        <div class="rev-footer-right">
          <button
            class="rev-btn rev-btn--ghost"
            type="button"
            :disabled="saving"
            @click="goBackToProcess"
          >
            {{ $t('process.review.actions.skip') }}
          </button>
          <button
            class="rev-btn rev-btn--launch"
            type="button"
            :disabled="saving || !canLaunch"
            @click="confirmAndContinue"
          >
            <span v-if="saving" class="rev-spinner" aria-hidden="true"></span>
            <span v-else aria-hidden="true">▶</span>
            <span>
              {{ saving
                ? $t('process.review.actions.saving')
                : $t('process.review.actions.launch') }}
            </span>
          </button>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  getProject,
  getGraphEntities,
  refineEntities
} from '../api/graph'
import { formatApiError } from '../utils/error-handler'

const props = defineProps({
  projectId: { type: String, required: true }
})

const router = useRouter()
const { t } = useI18n()

// ─── Server state ───────────────────────────────────────────────────────
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref('')
const projectData = ref(null)
const graphId = ref(null)
const entities = ref([]) // raw entity list { uuid, name, labels[] }

// ─── Pending diff (preserved from previous implementation) ────────────
const renames = reactive(new Map())     // uuid → newName
const merges = reactive(new Map())      // src_uuid → target_uuid
const deletes = reactive(new Set())     // uuid (« removed »)
const additions = ref([])               // [{ name, entity_type }]
const flags = reactive(new Set())       // uuid (status: flagged)
const entityNotes = reactive({})        // uuid → notes string

// ─── Inline edit state ─────────────────────────────────────────────────
const editingUuid = ref(null)
const editingName = ref('')
const editMode = ref(false)
let editInputEl = null

// ─── Filter / selection / batch ────────────────────────────────────────
const selectedType = ref('all')         // 'all' | type label
const searchQuery = ref('')
const selectedEntity = ref(null)
const batchSelected = reactive(new Set())

// ─── New entity inputs ─────────────────────────────────────────────────
const newEntityName = reactive({})
const newTypeName = ref('')
const newTypeType = ref('')

// ─── Helpers ───────────────────────────────────────────────────────────

function getEntityType(entity) {
  const labels = entity?.labels || []
  for (const l of labels) {
    if (l && l !== 'Entity' && l !== 'Node') return l
  }
  return t('process.review.misc.untyped')
}

function displayName(entity) {
  if (!entity) return ''
  if (renames.has(entity.uuid)) return renames.get(entity.uuid)
  return entity.name
}

function isRenamed(uuid) { return renames.has(uuid) }
function isDeleted(uuid) { return deletes.has(uuid) }
function isMerged(uuid) { return merges.has(uuid) }
function getMergeTarget(uuid) { return merges.get(uuid) }

function statusOf(entity) {
  if (!entity) return 'valid'
  if (deletes.has(entity.uuid)) return 'removed'
  if (flags.has(entity.uuid)) return 'flagged'
  return 'valid'
}

function statusLabel(entity) {
  const s = statusOf(entity)
  if (s === 'valid') return t('process.review.badges.valid')
  if (s === 'flagged') return t('process.review.badges.flagged')
  return t('process.review.badges.removed')
}

function entityCardClasses(entity) {
  return {
    'rev-entity-card--selected': selectedEntity.value && selectedEntity.value.uuid === entity.uuid,
    'rev-entity-card--valid': statusOf(entity) === 'valid',
    'rev-entity-card--flagged': statusOf(entity) === 'flagged',
    'rev-entity-card--removed': statusOf(entity) === 'removed',
    'rev-entity-card--merged': isMerged(entity.uuid)
  }
}

// Type label / icon mapping. Falls back to raw type for unknown labels so
// the analyst still sees something meaningful.
function typeLabel(type) {
  if (!type) return type
  const l = String(type).toLowerCase()
  if (l === 'person' || l === 'people') return t('process.review.filters.person')
  if (l === 'organization' || l === 'org' || l === 'company') return t('process.review.filters.organization')
  if (l === 'concept') return t('process.review.filters.concept')
  if (l === 'location' || l === 'place') return t('process.review.filters.location')
  return type
}

function typeIcon(type) {
  const l = String(type || '').toLowerCase()
  if (l === 'person' || l === 'people') return '👤'
  if (l === 'organization' || l === 'org' || l === 'company') return '🏢'
  if (l === 'concept') return '💡'
  if (l === 'location' || l === 'place') return '📍'
  return '◆'
}

const groupedTypes = computed(() => {
  const map = new Map()
  for (const e of entities.value) {
    const type = getEntityType(e)
    if (!map.has(type)) map.set(type, [])
    map.get(type).push(e)
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([type, list]) => ({ type, entities: list }))
})

const filteredEntities = computed(() => {
  let list = entities.value
  if (selectedType.value !== 'all') {
    list = list.filter(e => getEntityType(e) === selectedType.value)
  }
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(e => displayName(e).toLowerCase().includes(q))
  }
  return list
})

const validCount = computed(
  () => entities.value.filter(e => statusOf(e) === 'valid' && !isMerged(e.uuid)).length
        + additions.value.length
)
const flaggedCount = computed(() => entities.value.filter(e => statusOf(e) === 'flagged').length)
const removedCount = computed(() => deletes.size)

const pendingOpsCount = computed(
  () => renames.size + merges.size + deletes.size + additions.value.length + flags.size
)

const canLaunch = computed(() => validCount.value >= 3)

const canAddCustom = computed(
  () => !!(newTypeName.value && newTypeName.value.length
            && newTypeType.value && newTypeType.value.length)
)

function mergeCandidatesFor(entity) {
  if (!entity) return []
  const type = getEntityType(entity)
  return entities.value.filter(
    e => e.uuid !== entity.uuid
      && getEntityType(e) === type
      && !deletes.has(e.uuid)
  )
}

function additionsByType(type) {
  return additions.value.filter(a => a.entity_type === type)
}

// ─── Selection / batch ─────────────────────────────────────────────────

function selectEntity(entity) {
  selectedEntity.value = entity
  editMode.value = false
}

function toggleBatch(entity) {
  if (batchSelected.has(entity.uuid)) batchSelected.delete(entity.uuid)
  else batchSelected.add(entity.uuid)
}

function batchValidate() {
  for (const uuid of batchSelected) {
    flags.delete(uuid)
    deletes.delete(uuid)
  }
  batchSelected.clear()
}

function batchFlag() {
  for (const uuid of batchSelected) {
    if (deletes.has(uuid)) continue
    flags.add(uuid)
  }
  batchSelected.clear()
}

function batchRemove() {
  for (const uuid of batchSelected) {
    deletes.add(uuid)
    flags.delete(uuid)
    merges.delete(uuid) // cascade — a removed entity cannot be a merge source
  }
  batchSelected.clear()
}

// ─── Inline name edit (list) ───────────────────────────────────────────

function startEdit(entity) {
  editingUuid.value = entity.uuid
  editingName.value = displayName(entity)
  selectedEntity.value = entity
  editMode.value = true
  nextTick(() => {
    if (editInputEl && typeof editInputEl.focus === 'function') {
      editInputEl.focus()
      editInputEl.select && editInputEl.select()
    }
  })
}

function bindEditInput(el) {
  editInputEl = el
}

function cancelEdit() {
  editingUuid.value = null
  editingName.value = ''
  editInputEl = null
  editMode.value = false
}

function commitRename(entity) {
  if (editingUuid.value !== entity.uuid) return
  const next = (editingName.value || '').trim()
  const original = entity.name
  if (!next || next === original) {
    renames.delete(entity.uuid)
  } else {
    renames.set(entity.uuid, next.slice(0, 200))
  }
  editingUuid.value = null
  editingName.value = ''
  editInputEl = null
  editMode.value = false
}

// Public alias matching the spec (`renameEntity`)
function renameEntity(entity, newName) {
  const next = (newName || '').trim()
  if (!next || next === entity.name) {
    renames.delete(entity.uuid)
  } else {
    renames.set(entity.uuid, next.slice(0, 200))
  }
}

function onPanelNameBlur(entity, evt) {
  renameEntity(entity, evt.target.value)
  editMode.value = false
}

function onPanelNameEnter(entity, evt) {
  renameEntity(entity, evt.target.value)
  editMode.value = false
  evt.target.blur()
}

// ─── Merge / delete (panel + list) ─────────────────────────────────────

function onMergeChange(entity, evt) {
  const tgt = evt.target.value
  if (!tgt) {
    merges.delete(entity.uuid)
    return
  }
  if (tgt === entity.uuid) return
  merges.set(entity.uuid, tgt)
}

// Public alias matching the spec (`mergeEntities`)
function mergeEntities(srcEntity, targetUuid) {
  if (!targetUuid) {
    merges.delete(srcEntity.uuid)
    return
  }
  if (targetUuid === srcEntity.uuid) return
  merges.set(srcEntity.uuid, targetUuid)
}

// Public alias matching the spec (`deleteEntity`)
function deleteEntity(entity) {
  if (deletes.has(entity.uuid)) {
    deletes.delete(entity.uuid)
  } else {
    deletes.add(entity.uuid)
    merges.delete(entity.uuid)
    flags.delete(entity.uuid)
  }
}

function setStatus(entity, status) {
  if (!entity) return
  if (status === 'valid') {
    deletes.delete(entity.uuid)
    flags.delete(entity.uuid)
  } else if (status === 'flagged') {
    deletes.delete(entity.uuid)
    flags.add(entity.uuid)
  } else if (status === 'removed') {
    flags.delete(entity.uuid)
    deletes.add(entity.uuid)
    merges.delete(entity.uuid)
  }
}

// ─── Add / remove additions ────────────────────────────────────────────

function addEntity(typeOrPayload) {
  // Either called with a type (legacy newEntityName flow) or with a full payload.
  if (typeof typeOrPayload === 'string') {
    const type = typeOrPayload
    const name = (newEntityName[type] || '').trim()
    if (!name) return
    additions.value.push({ name: name.slice(0, 200), entity_type: type })
    newEntityName[type] = ''
    return
  }
  if (typeOrPayload && typeOrPayload.name && typeOrPayload.entity_type) {
    additions.value.push({
      name: String(typeOrPayload.name).slice(0, 200),
      entity_type: String(typeOrPayload.entity_type).slice(0, 60)
    })
  }
}

function addEntityWithCustomType() {
  if (!canAddCustom.value) return
  const cleanedType = newTypeType.value.replace(/[^A-Za-z0-9_]/g, '')
  if (!cleanedType) {
    errorMsg.value = t('process.review.validation.invalidType')
    return
  }
  additions.value.push({
    name: newTypeName.value.slice(0, 200),
    entity_type: cleanedType.slice(0, 60)
  })
  newTypeName.value = ''
  newTypeType.value = ''
  errorMsg.value = ''
}

function removeAddition(add) {
  const idx = additions.value.findIndex(
    a => a.name === add.name && a.entity_type === add.entity_type
  )
  if (idx >= 0) additions.value.splice(idx, 1)
}

function onNotesInput(entity, evt) {
  entityNotes[entity.uuid] = evt.target.value
}

// ─── Server I/O ────────────────────────────────────────────────────────

async function fetchEntities() {
  loading.value = true
  errorMsg.value = ''
  try {
    const projRes = await getProject(props.projectId)
    if (!projRes || !projRes.success) {
      errorMsg.value = (projRes && projRes.error) || t('process.review.error.projectNotFound')
      loading.value = false
      return
    }
    projectData.value = projRes.data
    graphId.value = projRes.data.graph_id

    if (!graphId.value) {
      errorMsg.value = t('process.review.error.graphNotBuilt')
      loading.value = false
      return
    }

    const res = await getGraphEntities(graphId.value, { enrich: false })
    if (res && res.success) {
      entities.value = (res.data && res.data.entities) || []
    } else {
      errorMsg.value = (res && res.error) || t('process.review.error.loadFailed')
    }
  } catch (err) {
    errorMsg.value = formatApiError(err, t) || t('process.review.error.loadFailed')
  } finally {
    loading.value = false
  }
}

// Backward-compatible alias used internally and by templates that may
// still call `loadEntities`.
const loadEntities = fetchEntities

function buildDiff() {
  return {
    renames: Array.from(renames.entries()).map(([uuid, newName]) => ({
      entity_uuid: uuid,
      new_name: newName
    })),
    merges: Array.from(merges.entries()).map(([src, tgt]) => ({
      src_uuid: src,
      target_uuid: tgt
    })),
    deletes: Array.from(deletes.values()).map(uuid => ({ entity_uuid: uuid })),
    additions: additions.value.slice()
  }
}

async function confirmAndContinue() {
  if (saving.value) return
  if (!canLaunch.value) return
  if (pendingOpsCount.value === 0) {
    goBackToProcess()
    return
  }
  if (!graphId.value) {
    errorMsg.value = t('process.review.error.graphNotBuilt')
    return
  }
  saving.value = true
  errorMsg.value = ''
  try {
    const diff = buildDiff()
    const res = await refineEntities(graphId.value, diff)
    if (res && res.success) {
      goBackToProcess()
    } else {
      errorMsg.value = (res && res.error) || t('process.review.error.saveFailed')
    }
  } catch (err) {
    errorMsg.value = formatApiError(err, t) || t('process.review.error.saveFailed')
  } finally {
    saving.value = false
  }
}

// Backward-compatible alias used by older templates / Playwright tests.
const saveAndContinue = confirmAndContinue

function goBackToProcess() {
  router.push({ name: 'Process', params: { projectId: props.projectId } })
}

// ─── Mount ─────────────────────────────────────────────────────────────

onMounted(fetchEntities)

// Expose the symbols required by the spec so external callers / tests can
// reach them via the component instance.
defineExpose({
  projectId: props.projectId,
  entities,
  filteredEntities,
  selectedEntity,
  selectedType,
  editMode,
  batchSelected,
  fetchEntities,
  loadEntities,
  renameEntity,
  mergeEntities,
  deleteEntity,
  addEntity,
  confirmAndContinue,
  saveAndContinue
})
</script>

<style scoped>
/* ═════════════════════════════════════════════════════════
   Layout root — Bassira Warm Intelligence palette
   ═════════════════════════════════════════════════════════ */
.rev-page {
  min-height: 100vh;
  background: var(--wi-bg);
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  display: flex;
  flex-direction: column;
}

/* ─── Top bar ─── */
.rev-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--wi-space-sm) var(--wi-space-md);
  border-bottom: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
}

.rev-back {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  text-decoration: none;
  color: var(--wi-on-surface-variant);
  font-weight: 600;
  font-size: var(--wi-label-sm);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  transition: color var(--ms-transition);
}
.rev-back:hover { color: var(--wi-primary); }
.rev-back-arrow { font-size: 18px; }

.rev-step-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  padding: 6px 14px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-primary-soft);
  color: var(--wi-primary);
  font-size: var(--wi-caption);
  font-weight: 700;
}
.rev-step-num {
  font-family: var(--ms-font-mono);
  font-weight: 700;
}

/* ─── Main scaffolding ─── */
.rev-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-md) var(--wi-space-md) calc(var(--wi-space-xl) + 80px);
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
}

.rev-hero {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  box-shadow: var(--wi-shadow-sm);
}

.rev-headline {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  margin: 0 0 var(--wi-space-xs);
  color: var(--wi-on-surface);
}

.rev-help {
  margin: 0 0 var(--wi-space-sm);
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
}

.rev-stats {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--wi-space-xs);
}
.rev-stats--loading { min-height: 24px; }

.rev-stat-item {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
}
.rev-stat-num {
  font-family: var(--ms-font-mono);
  font-weight: 700;
  font-size: 20px;
  color: var(--wi-on-surface);
}
.rev-stat-item--pending .rev-stat-num { color: var(--wi-primary-container); }
.rev-stat-item--valid .rev-stat-num { color: var(--wi-secondary); }

.rev-stat-label {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.rev-stat-sep {
  color: var(--wi-outline);
  margin-inline: 4px;
}

/* ─── Error banner ─── */
.rev-error {
  display: flex;
  align-items: flex-start;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-sm) var(--wi-space-md);
  background: var(--wi-error-container);
  border-radius: var(--wi-radius-md);
  color: var(--wi-on-error-container);
}
.rev-error-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--wi-on-error);
  color: var(--wi-error);
  font-weight: 800;
}
.rev-error-body { flex: 1; }
.rev-error-title { font-weight: 700; margin-bottom: 4px; }
.rev-error-msg { font-size: var(--wi-body-md); }

/* ─── Loading skeleton ─── */
.rev-loading { display: flex; flex-direction: column; gap: var(--wi-space-sm); }
.rev-skeleton-block {
  height: 80px;
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface-container);
  animation: rev-pulse 1.4s var(--ms-ease) infinite;
}
@keyframes rev-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
.rev-skeleton {
  display: inline-block;
  width: 120px;
  height: 18px;
  background: var(--wi-surface-container);
  border-radius: var(--wi-radius-sm);
}

/* ─── Empty hint ─── */
.rev-empty-hint {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-inline-start: 4px solid var(--wi-primary-container);
  border-radius: var(--wi-radius-md);
  padding: var(--wi-space-md);
  display: flex;
  align-items: flex-start;
  gap: var(--wi-space-sm);
}
.rev-empty-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--wi-primary-soft);
  color: var(--wi-on-primary-container);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.rev-empty-hint p {
  margin: 0;
  color: var(--wi-on-surface);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
}

/* ═════════════════════════════════════════════════════════
   Two-column workspace
   ═════════════════════════════════════════════════════════ */
.rev-workspace {
  display: grid;
  grid-template-columns: minmax(0, 70%) minmax(0, 30%);
  gap: var(--wi-space-sm);
  align-items: stretch;
  min-height: 540px;
}

/* ─── Left column ─── */
.rev-list-col {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--wi-shadow-sm);
}

/* Filters bar */
.rev-filters {
  padding: var(--wi-space-sm);
  border-bottom: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface-container-low);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-sm);
  flex-wrap: wrap;
}
.rev-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wi-space-xs);
  flex: 1;
  min-width: 0;
}

.rev-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--wi-radius-pill);
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--ms-transition);
}
.rev-chip:hover {
  border-color: var(--wi-primary-container);
  color: var(--wi-on-surface);
}
.rev-chip--active {
  background: var(--wi-primary-soft);
  border-color: var(--wi-primary-container);
  color: var(--wi-primary);
  font-weight: 700;
}
.rev-chip-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  padding: 1px 6px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container-high);
  font-family: var(--ms-font-mono);
  font-size: 10px;
  color: var(--wi-on-surface);
}
.rev-chip--active .rev-chip-count {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
}

.rev-search {
  position: relative;
  flex: 0 1 240px;
}
.rev-search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--wi-on-surface-variant);
  font-size: 14px;
}
.rev-search-input {
  width: 100%;
  padding: 6px 12px 6px 32px;
  border-radius: var(--wi-radius-pill);
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  outline: none;
  transition: border-color var(--ms-transition);
}
.rev-search-input:focus {
  border-color: var(--wi-primary-container);
  box-shadow: 0 0 0 2px var(--wi-primary-soft);
}

/* Entity list */
.rev-list-scroll {
  flex: 1;
  overflow-y: auto;
  padding: var(--wi-space-sm);
  background: var(--wi-bg);
}
.rev-empty-list {
  padding: var(--wi-space-md);
  text-align: center;
  color: var(--wi-on-surface-variant);
}

.rev-entity-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}

.rev-entity-card {
  display: flex;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-sm);
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  cursor: pointer;
  transition: all var(--ms-transition);
}
.rev-entity-card:hover {
  border-color: var(--wi-primary-container);
  box-shadow: var(--wi-shadow-sm);
}
.rev-entity-card--selected {
  border-color: var(--wi-primary);
  box-shadow: 0 0 0 2px var(--wi-primary-soft);
}
.rev-entity-card--flagged {
  border-inline-start: 4px solid var(--wi-primary-container);
  background: var(--wi-surface);
}
.rev-entity-card--removed {
  opacity: 0.65;
  background: var(--wi-surface-container-low);
}
.rev-entity-card--removed .rev-name-text {
  text-decoration: line-through;
  color: var(--wi-outline);
}
.rev-entity-card--merged {
  opacity: 0.85;
}

.rev-entity-checkcol {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding-top: 2px;
  width: 56px;
  flex-shrink: 0;
}
.rev-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--wi-primary);
}
.rev-checkbox:disabled { cursor: not-allowed; }

.rev-status-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: var(--wi-radius-sm);
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.rev-status-chip--valid {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}
.rev-status-chip--flagged {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
}
.rev-status-chip--removed {
  background: var(--wi-surface-container-high);
  color: var(--wi-outline);
}

.rev-entity-body { flex: 1; min-width: 0; }
.rev-entity-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--wi-space-xs);
  margin-bottom: 4px;
}

.rev-entity-name { flex: 1; min-width: 0; }
.rev-name-btn {
  background: none;
  border: 1px dashed transparent;
  padding: 4px 8px;
  border-radius: var(--wi-radius-sm);
  text-align: start;
  width: 100%;
  cursor: text;
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  font-family: inherit;
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  transition: border-color var(--ms-transition), background var(--ms-transition);
}
.rev-name-btn:hover,
.rev-name-btn:focus-visible {
  border-color: var(--wi-primary-container);
  background: var(--wi-primary-soft);
  outline: none;
}
.rev-name-text {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--wi-body-lg);
}

.rev-name-input {
  width: 100%;
  font-size: var(--wi-body-lg);
  padding: 6px 10px;
  border: 1px solid var(--wi-primary-container);
  border-radius: var(--wi-radius-sm);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  outline: none;
}
.rev-name-input:focus {
  box-shadow: 0 0 0 2px var(--wi-primary-soft);
}

.rev-entity-meta-right {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.rev-entity-type {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container);
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-caption);
  font-weight: 500;
}

.rev-entity-snippet {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}
.rev-entity-uuid { color: var(--wi-outline); }
.rev-entity-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--wi-outline-variant);
  display: inline-block;
}

/* Add new entity (collapsible) */
.rev-add-section {
  border-top: 1px solid var(--wi-outline-variant);
  padding: var(--wi-space-sm);
  background: var(--wi-surface-container-low);
}
.rev-add-details summary {
  cursor: pointer;
  font-weight: 600;
  font-size: var(--wi-label-sm);
  color: var(--wi-primary);
  list-style: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.rev-add-details summary::-webkit-details-marker { display: none; }
.rev-add-summary:hover { color: var(--wi-primary-container); }
.rev-add-body {
  margin-top: var(--wi-space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}
.rev-add-row {
  display: flex;
  gap: var(--wi-space-xs);
  align-items: center;
  flex-wrap: wrap;
}
.rev-help-sm {
  margin: 0;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}

/* ─── Inputs (shared) ─── */
.rev-input {
  flex: 1 1 200px;
  min-width: 0;
  padding: 8px 12px;
  border-radius: var(--wi-radius-md);
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  outline: none;
  transition: border-color var(--ms-transition), box-shadow var(--ms-transition);
}
.rev-input:focus {
  border-color: var(--wi-primary-container);
  box-shadow: 0 0 0 2px var(--wi-primary-soft);
}
.rev-input--full { flex: 1; width: 100%; }
.rev-input--narrow { flex: 0 1 160px; }
.rev-input--editing {
  border-color: var(--wi-primary-container);
  box-shadow: 0 0 0 2px var(--wi-primary-soft);
}
.rev-input--flagged {
  border-color: var(--wi-primary-container);
}
.rev-textarea {
  resize: vertical;
  min-height: 72px;
  font-family: var(--wi-font-body);
}

/* Additions list */
.rev-additions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rev-addition-row {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  padding: 6px 8px;
  background: var(--wi-secondary-container);
  border-radius: var(--wi-radius-sm);
}
.rev-addition-name {
  flex: 1;
  font-weight: 600;
  color: var(--wi-on-secondary-container);
}
.rev-addition-type {
  font-size: var(--wi-caption);
  color: var(--wi-on-secondary-container);
  opacity: 0.75;
}

/* Badges */
.rev-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.rev-badge--info {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
}
.rev-badge--success {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}

/* ═════════════════════════════════════════════════════════
   Right column — detail panel
   ═════════════════════════════════════════════════════════ */
.rev-detail-col {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--wi-shadow-sm);
}
.rev-detail-col--empty { background: var(--wi-surface-container-low); }

.rev-detail-head {
  padding: var(--wi-space-sm) var(--wi-space-md);
  border-bottom: 1px solid var(--wi-outline-variant);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--wi-space-sm);
}
.rev-detail-eyebrow {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  display: block;
  margin-bottom: 4px;
}
.rev-detail-title {
  font-family: var(--wi-font-heading);
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--wi-on-surface);
  word-break: break-word;
}
.rev-detail-close {
  background: none;
  border: none;
  font-size: 18px;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--wi-radius-sm);
  transition: all var(--ms-transition);
}
.rev-detail-close:hover {
  color: var(--wi-primary);
  background: var(--wi-primary-soft);
}

.rev-detail-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

.rev-field { display: flex; flex-direction: column; gap: 6px; }
.rev-field-row {
  display: flex;
  gap: var(--wi-space-sm);
}
.rev-field--grow { flex: 1; }
.rev-field--narrow { flex: 0 1 100px; }

.rev-field-label {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.rev-readonly-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: var(--wi-radius-md);
  background: var(--wi-surface-container);
  color: var(--wi-on-surface);
  font-size: var(--wi-body-md);
  font-weight: 500;
}

/* Segmented control */
.rev-segmented {
  display: flex;
  background: var(--wi-surface-container);
  border-radius: var(--wi-radius-md);
  padding: 4px;
  gap: 2px;
  border: 1px solid var(--wi-outline-variant);
}
.rev-seg {
  flex: 1;
  padding: 8px 10px;
  border: none;
  background: transparent;
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  cursor: pointer;
  border-radius: var(--wi-radius-sm);
  transition: all var(--ms-transition);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.rev-seg:hover { color: var(--wi-on-surface); }
.rev-seg--active {
  background: var(--wi-surface);
  box-shadow: var(--wi-shadow-sm);
}
.rev-seg--valid.rev-seg--active {
  color: var(--wi-secondary);
  border: 1px solid var(--wi-secondary-container);
}
.rev-seg--flagged.rev-seg--active {
  color: var(--wi-primary);
  border: 1px solid var(--wi-primary-container);
}
.rev-seg--removed.rev-seg--active {
  color: var(--wi-outline);
  border: 1px solid var(--wi-outline-variant);
}

/* Empty detail panel */
.rev-detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--wi-space-md);
  text-align: center;
  gap: var(--wi-space-xs);
}
.rev-detail-empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--wi-primary-soft);
  color: var(--wi-on-primary-container);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}
.rev-detail-empty-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  margin: 0;
  color: var(--wi-on-surface);
}
.rev-detail-empty-help {
  margin: 0;
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  max-width: 280px;
  line-height: var(--wi-body-md-leading);
}

/* ═════════════════════════════════════════════════════════
   Sticky footer / batch toolbar
   ═════════════════════════════════════════════════════════ */
.rev-footer {
  position: sticky;
  bottom: var(--wi-space-sm);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-sm) var(--wi-space-md);
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-lg);
  flex-wrap: wrap;
  z-index: var(--ms-z-sticky);
}

.rev-footer-left {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}

.rev-footer-count {
  font-weight: 700;
  color: var(--wi-primary);
  font-size: var(--wi-body-md);
}
.rev-footer-sep {
  width: 1px;
  height: 18px;
  background: var(--wi-outline-variant);
}

.rev-footer-summary {
  display: flex;
  align-items: center;
  gap: var(--wi-space-xs);
  flex-wrap: wrap;
  font-size: var(--wi-body-md);
}

.rev-summary-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  font-size: var(--wi-caption);
  font-weight: 600;
}
.rev-summary-pill--valid {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}
.rev-summary-pill--flagged {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
}
.rev-summary-pill--removed {
  background: var(--wi-surface-container-high);
  color: var(--wi-outline);
}

.rev-summary-warn {
  font-size: var(--wi-caption);
  color: var(--wi-on-primary-container);
  font-weight: 600;
  padding-inline-start: var(--wi-space-xs);
}

.rev-batch-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: var(--wi-radius-md);
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--ms-transition);
}
.rev-batch-btn:hover {
  background: var(--wi-surface-container);
  border-color: var(--wi-primary-container);
}
.rev-batch-btn--valid:hover {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
  border-color: var(--wi-secondary);
}
.rev-batch-btn--flag:hover {
  background: var(--wi-primary-container);
  color: var(--wi-on-primary);
  border-color: var(--wi-primary);
}
.rev-batch-btn--remove:hover {
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
  border-color: var(--wi-error);
}

.rev-footer-right {
  display: flex;
  gap: var(--wi-space-xs);
  align-items: center;
  flex-wrap: wrap;
}

/* ─── Buttons ─── */
.rev-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: var(--wi-radius-md);
  border: 1px solid transparent;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--ms-transition);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
}
.rev-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.rev-btn--ghost {
  background: transparent;
  border-color: var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
}
.rev-btn--ghost:hover:not(:disabled) {
  background: var(--wi-surface-container);
  color: var(--wi-on-surface);
}
.rev-btn--secondary {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}
.rev-btn--secondary:hover:not(:disabled) {
  filter: brightness(0.95);
}
.rev-btn--launch {
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
  font-weight: 700;
  letter-spacing: 0.01em;
  padding: 12px 22px;
  box-shadow: var(--wi-shadow-md);
}
.rev-btn--launch:hover:not(:disabled) {
  background: var(--wi-on-secondary-container);
  box-shadow: var(--wi-shadow-lg);
}
.rev-btn--sm {
  padding: 6px 10px;
  font-size: var(--wi-caption);
}

.rev-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: rev-spin 0.7s linear infinite;
}
@keyframes rev-spin { to { transform: rotate(360deg); } }

/* ═════════════════════════════════════════════════════════
   Responsive — collapse to single column under 960px
   ═════════════════════════════════════════════════════════ */
@media (max-width: 960px) {
  .rev-workspace {
    grid-template-columns: 1fr;
  }
  .rev-detail-col {
    min-height: 320px;
  }
}

@media (max-width: 720px) {
  .rev-topbar { padding: 12px 16px; }
  .rev-main { padding: 16px 12px calc(var(--wi-space-xl) + 100px); }
  .rev-headline { font-size: var(--wi-h3-size); }
  .rev-filters { flex-direction: column; align-items: stretch; }
  .rev-search { flex: 1 1 auto; }
  .rev-footer { flex-direction: column; align-items: stretch; }
  .rev-footer-right { justify-content: space-between; }
}
</style>
