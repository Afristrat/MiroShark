<template>
  <div class="rev-page">
    <!-- ─── Top bar (project + back link) ─── -->
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
      <!-- ─── Hero / explanation ─── -->
      <section class="rev-hero ms-card">
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
        </div>
      </section>

      <!-- ─── Error banner ─── -->
      <section v-if="errorMsg" class="rev-error" role="alert">
        <div class="rev-error-icon" aria-hidden="true">!</div>
        <div class="rev-error-body">
          <div class="rev-error-title">{{ $t('process.review.error.title') }}</div>
          <div class="rev-error-msg">{{ errorMsg }}</div>
        </div>
        <button class="ms-btn ms-btn-ghost ms-btn--sm" @click="loadEntities">
          {{ $t('process.review.error.retry') }}
        </button>
      </section>

      <!-- ─── Loading skeleton ─── -->
      <section v-if="loading" class="rev-loading">
        <div class="ms-skeleton rev-skeleton-block"></div>
        <div class="ms-skeleton rev-skeleton-block"></div>
      </section>

      <!-- ─── Entity groups (one card per entity_type) ─── -->
      <template v-else>
        <!-- Empty-state hint when the graph extracted nothing — keeps the
             "Add a brand-new type" block accessible so the user can recover. -->
        <section v-if="entities.length === 0" class="rev-empty-hint ms-card">
          <p>{{ $t('process.review.empty') }}</p>
        </section>
        <section
          v-for="group in groupedTypes"
          :key="group.type"
          class="rev-group ms-card"
          :aria-label="group.type"
        >
          <header class="rev-group-header">
            <h2 class="rev-group-title">
              <span class="rev-group-type">{{ group.type }}</span>
              <span class="rev-group-count">{{ group.entities.length }}</span>
            </h2>
          </header>

          <ul class="rev-entity-list">
            <li
              v-for="entity in group.entities"
              :key="entity.uuid"
              class="rev-entity-row"
              :class="{
                'rev-entity-row--deleted': isDeleted(entity.uuid),
                'rev-entity-row--merged': isMerged(entity.uuid),
                'rev-entity-row--renamed': isRenamed(entity.uuid)
              }"
            >
              <!-- Name : inline edit -->
              <div class="rev-entity-name">
                <input
                  v-if="editingUuid === entity.uuid"
                  :ref="el => bindEditInput(el)"
                  v-model.trim="editingName"
                  class="ms-input rev-name-input"
                  type="text"
                  :maxlength="200"
                  :placeholder="entity.name"
                  @keydown.enter.prevent="commitRename(entity)"
                  @keydown.esc.prevent="cancelEdit"
                  @blur="commitRename(entity)"
                />
                <button
                  v-else
                  class="rev-name-btn"
                  type="button"
                  :title="$t('process.review.actions.rename')"
                  @click="startEdit(entity)"
                >
                  <span class="rev-name-text">{{ displayName(entity) }}</span>
                  <span
                    v-if="isRenamed(entity.uuid)"
                    class="rev-badge rev-badge--info"
                    :title="$t('process.review.badges.renamed')"
                  >
                    {{ $t('process.review.badges.renamed') }}
                  </span>
                </button>
              </div>

              <!-- Inline actions -->
              <div class="rev-entity-actions">
                <!-- Merge -->
                <select
                  class="ms-select rev-merge-select"
                  :value="getMergeTarget(entity.uuid) || ''"
                  :disabled="isDeleted(entity.uuid)"
                  :aria-label="$t('process.review.actions.merge')"
                  @change="onMergeChange(entity, $event)"
                >
                  <option value="">{{ $t('process.review.actions.mergePlaceholder') }}</option>
                  <option
                    v-for="other in mergeCandidates(group, entity)"
                    :key="other.uuid"
                    :value="other.uuid"
                  >
                    {{ displayName(other) }}
                  </option>
                </select>

                <!-- Delete -->
                <button
                  class="ms-btn ms-btn--sm"
                  :class="isDeleted(entity.uuid) ? 'ms-btn-secondary' : 'ms-btn-ghost'"
                  type="button"
                  :title="$t('process.review.actions.delete')"
                  @click="toggleDelete(entity)"
                >
                  <span aria-hidden="true">{{ isDeleted(entity.uuid) ? '↺' : '✕' }}</span>
                  <span class="rev-action-label">
                    {{ isDeleted(entity.uuid)
                      ? $t('process.review.actions.undo')
                      : $t('process.review.actions.delete') }}
                  </span>
                </button>
              </div>
            </li>
          </ul>

          <!-- Add new entity in this group -->
          <div class="rev-add-row">
            <input
              v-model.trim="newEntityName[group.type]"
              class="ms-input rev-add-input"
              type="text"
              :maxlength="200"
              :placeholder="$t('process.review.add.placeholderInGroup', { type: group.type })"
              @keydown.enter.prevent="addEntity(group.type)"
            />
            <button
              class="ms-btn ms-btn-secondary ms-btn--sm"
              type="button"
              :disabled="!(newEntityName[group.type] && newEntityName[group.type].length)"
              @click="addEntity(group.type)"
            >
              + {{ $t('process.review.add.button') }}
            </button>
          </div>

          <!-- Pending additions for this type -->
          <ul v-if="additionsByType(group.type).length" class="rev-additions">
            <li
              v-for="(add, idx) in additionsByType(group.type)"
              :key="`${add.entity_type}-${idx}-${add.name}`"
              class="rev-addition-row"
            >
              <span class="rev-badge rev-badge--success">+</span>
              <span class="rev-addition-name">{{ add.name }}</span>
              <button
                class="ms-btn ms-btn-ghost ms-btn--sm"
                type="button"
                :title="$t('process.review.add.remove')"
                @click="removeAddition(add)"
              >
                ✕
              </button>
            </li>
          </ul>
        </section>

        <!-- Add a brand-new type bloc -->
        <section class="rev-group ms-card rev-new-type">
          <header class="rev-group-header">
            <h2 class="rev-group-title">
              <span class="rev-group-type">{{ $t('process.review.add.newTypeTitle') }}</span>
            </h2>
          </header>
          <p class="rev-help-sm">{{ $t('process.review.add.newTypeHelp') }}</p>
          <div class="rev-add-new-row">
            <input
              v-model.trim="newTypeName"
              class="ms-input rev-add-input"
              type="text"
              :maxlength="200"
              :placeholder="$t('process.review.add.namePlaceholder')"
              @keydown.enter.prevent="addEntityWithCustomType"
            />
            <input
              v-model.trim="newTypeType"
              class="ms-input rev-add-input rev-add-type-input"
              type="text"
              :maxlength="60"
              :placeholder="$t('process.review.add.typePlaceholder')"
              @keydown.enter.prevent="addEntityWithCustomType"
            />
            <button
              class="ms-btn ms-btn-secondary ms-btn--sm"
              type="button"
              :disabled="!canAddCustom"
              @click="addEntityWithCustomType"
            >
              + {{ $t('process.review.add.button') }}
            </button>
          </div>
        </section>
      </template>

      <!-- ─── Footer actions ─── -->
      <footer class="rev-footer">
        <div class="rev-footer-summary">
          <template v-if="pendingOpsCount > 0">
            <span class="rev-footer-pending">
              {{ $t('process.review.footer.pending', { count: pendingOpsCount }) }}
            </span>
          </template>
          <template v-else>
            <span class="rev-footer-empty">{{ $t('process.review.footer.noChanges') }}</span>
          </template>
        </div>
        <div class="rev-footer-actions">
          <button
            class="ms-btn ms-btn-ghost"
            type="button"
            :disabled="saving"
            @click="goBackToProcess"
          >
            {{ $t('process.review.actions.skip') }}
          </button>
          <button
            class="ms-btn ms-btn-primary"
            type="button"
            :disabled="saving || pendingOpsCount === 0"
            @click="saveAndContinue"
          >
            <span v-if="saving" class="rev-spinner" aria-hidden="true"></span>
            {{ saving
              ? $t('process.review.actions.saving')
              : $t('process.review.actions.saveAndContinue') }}
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

// ─── Pending diff ───────────────────────────────────────────────────────
// renames: Map<uuid, newName>
const renames = reactive(new Map())
// merges: Map<src_uuid, target_uuid>
const merges = reactive(new Map())
// deletes: Set<uuid>
const deletes = reactive(new Set())
// additions: Array<{ name, entity_type }>
const additions = ref([])

// ─── Inline edit state ─────────────────────────────────────────────────
const editingUuid = ref(null)
const editingName = ref('')
let editInputEl = null

// ─── New entity inputs ─────────────────────────────────────────────────
const newEntityName = reactive({}) // type → name
const newTypeName = ref('')
const newTypeType = ref('')

// ─── Helpers ───────────────────────────────────────────────────────────

function getEntityType(entity) {
  // Server returns labels excluding "Entity" already; fall back to first
  // custom label in any case.
  const labels = entity.labels || []
  for (const l of labels) {
    if (l && l !== 'Entity' && l !== 'Node') return l
  }
  return t('process.review.misc.untyped')
}

function displayName(entity) {
  if (renames.has(entity.uuid)) return renames.get(entity.uuid)
  return entity.name
}

function isRenamed(uuid) {
  return renames.has(uuid)
}

function isDeleted(uuid) {
  return deletes.has(uuid)
}

function isMerged(uuid) {
  return merges.has(uuid)
}

function getMergeTarget(uuid) {
  return merges.get(uuid)
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

const pendingOpsCount = computed(
  () => renames.size + merges.size + deletes.size + additions.value.length
)

const canAddCustom = computed(
  () => !!(newTypeName.value && newTypeName.value.length
            && newTypeType.value && newTypeType.value.length)
)

function mergeCandidates(group, entity) {
  return group.entities.filter(e => e.uuid !== entity.uuid && !deletes.has(e.uuid))
}

function additionsByType(type) {
  return additions.value.filter(a => a.entity_type === type)
}

// ─── Actions ───────────────────────────────────────────────────────────

function startEdit(entity) {
  editingUuid.value = entity.uuid
  editingName.value = displayName(entity)
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
}

function commitRename(entity) {
  if (editingUuid.value !== entity.uuid) return
  const next = (editingName.value || '').trim()
  const original = entity.name
  if (!next || next === original) {
    // Empty or unchanged → drop pending rename
    renames.delete(entity.uuid)
  } else {
    renames.set(entity.uuid, next.slice(0, 200))
  }
  editingUuid.value = null
  editingName.value = ''
  editInputEl = null
}

function onMergeChange(entity, evt) {
  const tgt = evt.target.value
  if (!tgt) {
    merges.delete(entity.uuid)
    return
  }
  if (tgt === entity.uuid) {
    return  // self-merge — sanitiser drops it anyway, but block at UI too
  }
  merges.set(entity.uuid, tgt)
}

function toggleDelete(entity) {
  if (deletes.has(entity.uuid)) {
    deletes.delete(entity.uuid)
  } else {
    deletes.add(entity.uuid)
    // Cascade: a deleted entity can no longer be a merge source
    merges.delete(entity.uuid)
  }
}

function addEntity(type) {
  const name = (newEntityName[type] || '').trim()
  if (!name) return
  additions.value.push({
    name: name.slice(0, 200),
    entity_type: type
  })
  newEntityName[type] = ''
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

// ─── Server I/O ────────────────────────────────────────────────────────

async function loadEntities() {
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
    // US-007: localised, error_code-aware fallback so codes like
    // STORAGE_UNAVAILABLE / MISSING_GRAPH_ID surface in fr/ar.
    errorMsg.value = formatApiError(err, t) || t('process.review.error.loadFailed')
  } finally {
    loading.value = false
  }
}

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

async function saveAndContinue() {
  if (saving.value) return
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

function goBackToProcess() {
  router.push({ name: 'Process', params: { projectId: props.projectId } })
}

// ─── Mount ─────────────────────────────────────────────────────────────

onMounted(loadEntities)
</script>

<style scoped>
.rev-page {
  min-height: 100vh;
  background: var(--ms-bg-muted, #fffaf3);
  color: var(--ms-text-primary, #1a1a1a);
  font-family: var(--ms-font-body);
  display: flex;
  flex-direction: column;
}

/* ─── Top bar ─── */
.rev-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-bottom: 1px solid var(--ms-border, rgba(0,0,0,0.08));
  background: var(--ms-bg, #fff);
}

.rev-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--ms-text-primary);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.rev-back:hover { color: var(--ms-orange); }
.rev-back-arrow { font-size: 18px; }

.rev-step-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--ms-orange-soft, #ffe7d2);
  color: var(--ms-orange, #e96a2a);
  font-size: 13px;
  font-weight: 700;
}

.rev-step-num {
  font-family: var(--ms-font-mono);
  font-weight: 700;
}

/* ─── Main layout ─── */
.rev-main {
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: 32px 24px 120px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.rev-hero {
  padding: 24px 28px;
}

.rev-headline {
  font-family: var(--ms-font-display, var(--ms-font-body));
  font-size: 28px;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.rev-help {
  margin: 0 0 16px;
  color: var(--ms-text-secondary, #555);
  font-size: 15px;
  line-height: 1.5;
}

.rev-stats {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
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
  color: var(--ms-text-primary);
}

.rev-stat-item--pending .rev-stat-num { color: var(--ms-orange); }

.rev-stat-label {
  font-size: 12px;
  color: var(--ms-text-secondary, #555);
  text-transform: uppercase;
  letter-spacing: 1.2px;
}

.rev-stat-sep {
  color: var(--ms-text-secondary, #999);
  margin-inline: 4px;
}

/* ─── Error banner ─── */
.rev-error {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px;
  background: var(--ms-rose, #ffe2e2);
  border-radius: var(--ms-radius-md, 12px);
  color: #8a1f1f;
}

.rev-error-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255,255,255,0.5);
  font-weight: 800;
}

.rev-error-body { flex: 1; }
.rev-error-title { font-weight: 700; margin-bottom: 4px; }
.rev-error-msg { font-size: 14px; }

/* ─── Loading skeleton ─── */
.rev-loading { display: flex; flex-direction: column; gap: 12px; }
.rev-skeleton-block { height: 80px; border-radius: 12px; }

/* ─── Empty state ─── */
.rev-empty {
  padding: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.rev-empty-hint {
  padding: 16px 20px;
  border-inline-start: 3px solid var(--ms-orange, #ff6f3c);
  background: var(--ms-rose, #fde8ec);
}
.rev-empty-hint p {
  margin: 0;
  color: var(--ms-text-primary, #1a1a1a);
  font-size: 14px;
  line-height: 1.5;
}

/* ─── Group card ─── */
.rev-group {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rev-group-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--ms-border, rgba(0,0,0,0.08));
  padding-bottom: 8px;
}

.rev-group-title {
  display: inline-flex;
  align-items: baseline;
  gap: 10px;
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.rev-group-type { color: var(--ms-text-primary); }

.rev-group-count {
  font-family: var(--ms-font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--ms-orange);
  background: var(--ms-orange-soft, #ffe7d2);
  padding: 2px 8px;
  border-radius: 999px;
}

/* ─── Entity row ─── */
.rev-entity-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.rev-entity-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--ms-border, rgba(0,0,0,0.05));
}

.rev-entity-row:last-child { border-bottom: none; }

.rev-entity-row--deleted .rev-name-text {
  text-decoration: line-through;
  color: var(--ms-text-secondary, #888);
}

.rev-entity-row--merged {
  opacity: 0.7;
}

.rev-entity-name {
  flex: 1;
  min-width: 0;
}

.rev-name-btn {
  background: none;
  border: 1px dashed transparent;
  padding: 6px 10px;
  border-radius: 8px;
  text-align: start;
  width: 100%;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: inherit;
  font-size: 15px;
  color: inherit;
  transition: border-color 120ms ease, background 120ms ease;
}

.rev-name-btn:hover,
.rev-name-btn:focus-visible {
  border-color: var(--ms-orange);
  background: var(--ms-orange-soft, #ffe7d2);
  outline: none;
}

.rev-name-text {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rev-name-input {
  width: 100%;
  font-size: 15px;
}

.rev-entity-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rev-merge-select {
  min-width: 180px;
  font-size: 13px;
}

.rev-action-label {
  margin-inline-start: 4px;
}

/* ─── Badges ─── */
.rev-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.rev-badge--info { background: var(--ms-peach, #ffe1c4); color: #7a4a1c; }
.rev-badge--success { background: var(--ms-mint, #d2f0d8); color: #1f5b30; }

/* ─── Add row ─── */
.rev-add-row,
.rev-add-new-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 8px;
}

.rev-add-input { flex: 1 1 200px; min-width: 0; }
.rev-add-type-input { flex: 0 1 160px; }

.rev-additions {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rev-addition-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: var(--ms-mint, #d2f0d8);
  border-radius: 8px;
}

.rev-addition-name {
  flex: 1;
  font-weight: 600;
  color: #1f5b30;
}

.rev-help-sm {
  margin: 0;
  font-size: 13px;
  color: var(--ms-text-secondary, #555);
}

.rev-new-type { background: var(--ms-cream, #fff7e8); }

/* ─── Footer ─── */
.rev-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: var(--ms-bg, #fff);
  border: 1px solid var(--ms-border, rgba(0,0,0,0.08));
  border-radius: var(--ms-radius-md, 12px);
  box-shadow: 0 -8px 30px -20px rgba(0,0,0,0.2);
  flex-wrap: wrap;
}

.rev-footer-summary { font-size: 14px; }
.rev-footer-pending { color: var(--ms-orange); font-weight: 700; }
.rev-footer-empty { color: var(--ms-text-secondary, #888); }

.rev-footer-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.rev-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: rev-spin 0.7s linear infinite;
  vertical-align: middle;
  margin-inline-end: 6px;
}

@keyframes rev-spin { to { transform: rotate(360deg); } }

/* ─── Skeleton fallback (in case .ms-skeleton not provided) ─── */
.rev-skeleton {
  display: inline-block;
  width: 120px;
  height: 18px;
  background: var(--ms-border, rgba(0,0,0,0.08));
  border-radius: 6px;
}

/* ─── Responsive ─── */
@media (max-width: 720px) {
  .rev-topbar { padding: 12px 16px; }
  .rev-main { padding: 20px 12px 140px; }
  .rev-entity-row { flex-direction: column; align-items: stretch; }
  .rev-entity-actions { justify-content: flex-end; }
  .rev-merge-select { min-width: 0; flex: 1; }
}
</style>
