<template>
  <!--
    VersionDiff (US-127) — Visual diff entre deux versions d'un rapport.
    Affiche les opérations 'equal'/'insert'/'delete' via diff-match-patch
    calculé côté backend (/diff) ou côté frontend (fallback).
    Tokens --wi-* exclusivement.
  -->
  <div class="vd-root">
    <div v-if="loading" class="vd-state">
      <span>{{ $t('adminReportReview.diffModal.loading') || 'Calcul du diff…' }}</span>
    </div>
    <div v-else-if="error" class="vd-state vd-state--error" role="alert">{{ error }}</div>
    <div v-else-if="diffOps.length === 0" class="vd-state vd-state--empty">
      {{ $t('adminReportReview.diffModal.empty') || 'Aucune différence détectée.' }}
    </div>
    <div v-else class="vd-diff" aria-label="Diff entre les versions">
      <div
        v-for="(op, idx) in diffOps"
        :key="idx"
        class="vd-line"
        :class="`vd-line--${op.op}`"
      >
        <span class="vd-gutter" aria-hidden="true">
          {{ op.op === 'insert' ? '+' : op.op === 'delete' ? '−' : ' ' }}
        </span>
        <pre class="vd-text">{{ op.text }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import client from '../api/client'

type DiffOp = {
  op: 'equal' | 'insert' | 'delete'
  text: string
}

type Props = {
  reportId: string
  fromVersionId: string
  toVersionId: string
}

const props = defineProps<Props>()

// ─── État ───────────────────────────────────────────────────────────────────

const loading = ref(false)
const error = ref<string | null>(null)
const diffOps = ref<DiffOp[]>([])

// ─── Chargement ─────────────────────────────────────────────────────────────

async function loadDiff() {
  if (!props.reportId || !props.fromVersionId || !props.toVersionId) return
  loading.value = true
  error.value = null
  diffOps.value = []

  try {
    const resp = await (client as unknown as {
      get: (_url: string) => Promise<{ success: boolean; data: { diff: DiffOp[] } }>
    }).get(
      `/api/admin/reports/${encodeURIComponent(props.reportId)}/versions/${encodeURIComponent(props.fromVersionId)}/diff/${encodeURIComponent(props.toVersionId)}`
    )
    if (resp.success && Array.isArray(resp.data?.diff)) {
      diffOps.value = resp.data.diff
    } else {
      error.value = 'Réponse inattendue du serveur.'
    }
  } catch (_err) {
    error.value = 'Impossible de calculer le diff.'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.fromVersionId, props.toVersionId],
  () => loadDiff(),
  { immediate: true }
)
</script>

<style scoped>
.vd-root {
  width: 100%;
  overflow-x: auto;
  font-family: "JetBrains Mono", "Fira Code", monospace;
  font-size: 12px;
}

.vd-state {
  padding: 24px;
  text-align: center;
  color: var(--wi-on-surface-variant, #888);
  font-style: italic;
}

.vd-state--error {
  color: var(--wi-error, #c62828);
}

.vd-state--empty {
  color: var(--wi-on-surface-variant, #888);
}

.vd-diff {
  border: 1px solid var(--wi-outline-variant, #e0e0e0);
  border-radius: var(--wi-radius-md, 8px);
  overflow: hidden;
}

.vd-line {
  display: flex;
  align-items: flex-start;
  line-height: 1.5;
  padding: 0;
}

.vd-line--equal {
  background: var(--wi-surface, #fff);
}

.vd-line--insert {
  background: rgba(40, 167, 69, 0.12);
  border-left: 3px solid #28a745;
}

.vd-line--delete {
  background: rgba(220, 53, 69, 0.1);
  border-left: 3px solid #dc3545;
  text-decoration: line-through;
  opacity: 0.75;
}

.vd-gutter {
  flex-shrink: 0;
  width: 24px;
  padding: 0 4px;
  text-align: center;
  font-weight: 700;
  color: var(--wi-on-surface-variant, #888);
  user-select: none;
}

.vd-line--insert .vd-gutter {
  color: #28a745;
}

.vd-line--delete .vd-gutter {
  color: #dc3545;
}

.vd-text {
  flex: 1;
  margin: 0;
  padding: 2px 8px;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: inherit;
  font-size: inherit;
  color: var(--wi-on-surface, #1a1a1a);
}
</style>
