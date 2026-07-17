<template>
  <!--
    AdminReportReviewView (US-127) — Page /admin/reports/:id/review (super-admin).

    Layout split 50/50 :
      - Gauche : iframe PDF preview (debounced 2s post-save)
      - Droite : tree sections (AdminReportTree) + TiptapEditor ou RawMdEditor

    Toolbar :
      - Rephrase with AI  → POST /api/report/chat
      - Compare versions  → modal VersionDiff
      - Toggle Raw/Rich   → bascule entre RawMdEditor et TiptapEditor
      - Save version      → POST /api/admin/reports/<id>/versions + comment

    Tokens --wi-* exclusivement. i18n FR/EN/AR.
  -->
  <div class="arr-page" :dir="$i18n.locale === 'ar' ? 'rtl' : 'ltr'">
<!-- Topbar ────────────────────────────────────────────────────────────── -->
    <header class="arr-topbar">
      <router-link to="/admin/branding" class="arr-back">
        ← {{ $t('nav.brand') || 'BASSIRA' }}
      </router-link>

      <div class="arr-topbar-center">
        <span class="arr-report-id">{{ reportId }}</span>
        <span
          v-if="workflowState"
          class="arr-state-pill"
          :class="`arr-state-pill--${workflowState.toLowerCase()}`"
        >
          {{ $t(`adminReportReview.workflow.${workflowState}`) || workflowState }}
        </span>
      </div>

      <div class="arr-topbar-actions">
        <!-- Toggle raw / rich -->
        <button
          type="button"
          class="arr-btn arr-btn--ghost"
          :title="rawMode ? $t('adminReportReview.richEditor') : $t('adminReportReview.rawMarkdown')"
          @click="rawMode = !rawMode"
        >
          {{ rawMode ? $t('adminReportReview.richEditor') || 'Éditeur riche' : $t('adminReportReview.rawMarkdown') || 'Markdown brut' }}
        </button>

        <!-- Rephrase AI -->
        <button
          type="button"
          class="arr-btn arr-btn--ghost"
          :disabled="rephrasing || !selectedText"
          :title="$t('adminReportReview.rephraseAI') || 'Reformuler avec l\'IA'"
          @click="rephraseSelected"
        >
          <span v-if="rephrasing">{{ $t('adminReportReview.rephrasing') || 'Reformulation…' }}</span>
          <span v-else>✦ {{ $t('adminReportReview.rephraseAI') || 'Reformuler IA' }}</span>
        </button>

        <!-- Compare versions -->
        <button
          type="button"
          class="arr-btn arr-btn--ghost"
          :disabled="versions.length < 2"
          :title="$t('adminReportReview.compareVersions') || 'Comparer les versions'"
          @click="showDiffModal = true"
        >
          {{ $t('adminReportReview.compareVersions') || 'Comparer' }}
        </button>

        <!-- Save version -->
        <button
          type="button"
          class="arr-btn arr-btn--primary"
          :disabled="saving"
          @click="showSaveModal = true"
        >
          {{ saving ? '…' : $t('adminReportReview.saveVersion') || 'Sauvegarder' }}
        </button>
      </div>
    </header>

    <!-- Notification barre ─────────────────────────────────────────────────── -->
    <transition name="arr-notif-slide">
      <div v-if="notification" class="arr-notif" :class="`arr-notif--${notification.type}`" role="alert">
        {{ notification.message }}
      </div>
    </transition>

    <!-- Loading / error état ──────────────────────────────────────────────── -->
    <div v-if="loading" class="arr-loading">
      {{ $t('adminReportReview.loading') || 'Chargement du rapport…' }}
    </div>
    <div v-else-if="loadError" class="arr-error" role="alert">
      {{ loadError }}
    </div>

    <!-- Split view ─────────────────────────────────────────────────────────── -->
    <div v-else class="arr-split">
<!-- Colonne gauche : PDF preview ────────────────────────────────────── -->
      <section class="arr-pdf-pane" :aria-label="$t('adminReportReview.pdfPreview') || 'Aperçu PDF'">
        <div class="arr-pdf-header">
          <span class="arr-pane-label">{{ $t('adminReportReview.pdfPreview') || 'Aperçu PDF' }}</span>
          <span v-if="pdfLoading" class="arr-pdf-loading">↻</span>
        </div>
        <div class="arr-pdf-embed">
          <iframe
            v-if="pdfUrl"
            :src="pdfUrl"
            class="arr-pdf-iframe"
            :title="$t('adminReportReview.pdfPreview') || 'Aperçu PDF'"
            loading="lazy"
          ></iframe>
          <div v-else class="arr-pdf-placeholder">
            <span>{{ $t('adminReportReview.pdfPreview') || 'Aperçu PDF' }}</span>
            <span class="arr-pdf-placeholder-sub">
              Sauvegardez une version pour régénérer l'aperçu PDF.
            </span>
          </div>
        </div>
      </section>

      <!-- Colonne droite : tree + éditeur ─────────────────────────────────── -->
      <section class="arr-editor-pane" :aria-label="$t('adminReportReview.editor') || 'Éditeur'">
<!-- Tree sections (1/4 de la hauteur) -->
        <div class="arr-tree-wrap">
          <AdminReportTree
            :sections="outline.sections || []"
            :active-index="activeSectionIndex"
            :comments="comments"
            @select-section="selectSection"
          />
        </div>

        <!-- Éditeur (3/4 de la hauteur) -->
        <div class="arr-editor-wrap">
          <div class="arr-editor-header">
            <span class="arr-pane-label">{{ $t('adminReportReview.editor') || 'Éditeur' }}</span>
            <span v-if="activeSectionTitle" class="arr-section-title">{{ activeSectionTitle }}</span>
          </div>

          <div class="arr-editor-content">
            <RawMdEditor
              v-if="rawMode"
              v-model="editorContent"
              class="arr-editor-inner"
            />
            <TiptapEditor
              v-else
              v-model="editorContent"
              :placeholder="$t('adminReportReview.editor') || 'Éditez le contenu…'"
              :report-id="reportId"
              class="arr-editor-inner"
            />
          </div>

          <!-- Zone commentaires ─────────────────────────────────────────────── -->
          <div class="arr-comments">
            <div class="arr-comments-header">
              <span class="arr-pane-label">{{ $t('adminReportReview.comments') || 'Annotations' }}</span>
              <span class="arr-comments-count">{{ openComments.length }}</span>
            </div>

            <div v-if="commentsLoading" class="arr-comments-state">…</div>
            <div v-else-if="openComments.length === 0" class="arr-comments-empty">
              {{ $t('adminReportReview.commentsEmpty') || 'Aucune annotation.' }}
            </div>
            <ul v-else class="arr-comments-list">
              <li
                v-for="c in openComments"
                :key="c.comment_id"
                class="arr-comment-item"
              >
                <span class="arr-comment-anchor">{{ c.paragraph_anchor }}</span>
                <p class="arr-comment-body">{{ c.body }}</p>
                <button
                  type="button"
                  class="arr-comment-resolve"
                  @click="resolveComment(c.comment_id)"
                >
                  {{ $t('adminReportReview.commentResolve') || 'Résoudre' }}
                </button>
              </li>
            </ul>

            <!-- Ajout d'un commentaire ──────────────────────────────────────── -->
            <div class="arr-comment-add">
              <input
                v-model="newCommentAnchor"
                type="text"
                class="arr-comment-anchor-input"
                placeholder="Ancre (ex: section-1)"
              />
              <textarea
                v-model="newCommentBody"
                class="arr-comment-textarea"
                rows="2"
                :placeholder="$t('adminReportReview.commentPlaceholder') || 'Votre annotation…'"
              ></textarea>
              <button
                type="button"
                class="arr-btn arr-btn--sm arr-btn--primary"
                :disabled="!newCommentBody.trim() || addingComment"
                @click="addComment"
              >
                {{ $t('adminReportReview.commentAdd') || 'Ajouter' }}
              </button>
            </div>
          </div>
        </div>
</section>
    </div>

    <!-- Modal : Sauvegarder la version ─────────────────────────────────────── -->
    <transition name="arr-modal-fade">
      <div v-if="showSaveModal" class="arr-modal-overlay" @click.self="showSaveModal = false">
        <div class="arr-modal" role="dialog" :aria-label="$t('adminReportReview.saveVersion')">
          <h2 class="arr-modal-title">{{ $t('adminReportReview.saveVersion') || 'Sauvegarder la version' }}</h2>
          <div class="arr-modal-field">
            <label class="arr-modal-label">
              {{ $t('adminReportReview.saveVersionComment') || 'Commentaire' }}
            </label>
            <input
              v-model="versionComment"
              type="text"
              class="arr-modal-input"
              :placeholder="$t('adminReportReview.saveVersionCommentPlaceholder') || 'Description…'"
            />
          </div>
          <div class="arr-modal-actions">
            <button type="button" class="arr-btn arr-btn--ghost" @click="showSaveModal = false">
              {{ $t('common.cancel') || 'Annuler' }}
            </button>
            <button type="button" class="arr-btn arr-btn--primary" :disabled="saving" @click="saveVersion">
              {{ saving ? '…' : $t('adminReportReview.saveVersion') || 'Sauvegarder' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Modal : Comparer les versions ──────────────────────────────────────── -->
    <transition name="arr-modal-fade">
      <div v-if="showDiffModal" class="arr-modal-overlay" @click.self="showDiffModal = false">
        <div class="arr-modal arr-modal--wide" role="dialog" :aria-label="$t('adminReportReview.diffModal.title')">
          <h2 class="arr-modal-title">{{ $t('adminReportReview.diffModal.title') || 'Différences' }}</h2>
          <div class="arr-modal-field arr-modal-field--row">
            <div>
              <label class="arr-modal-label">{{ $t('adminReportReview.diffModal.from') || 'Depuis' }}</label>
              <select v-model="diffFromId" class="arr-modal-select">
                <option v-for="v in versions" :key="v.version_id" :value="v.version_id">
                  V{{ v.version_number }} — {{ formatDate(v.created_at) }}
                </option>
              </select>
            </div>
            <div>
              <label class="arr-modal-label">{{ $t('adminReportReview.diffModal.to') || 'Vers' }}</label>
              <select v-model="diffToId" class="arr-modal-select">
                <option v-for="v in versions" :key="v.version_id" :value="v.version_id">
                  V{{ v.version_number }} — {{ formatDate(v.created_at) }}
                </option>
              </select>
            </div>
          </div>

          <div class="arr-diff-container" v-if="diffFromId && diffToId && diffFromId !== diffToId">
            <VersionDiff
              :report-id="reportId"
              :from-version-id="diffFromId"
              :to-version-id="diffToId"
            />
          </div>
          <p v-else class="arr-modal-hint">Sélectionnez deux versions différentes pour voir le diff.</p>

          <div class="arr-modal-actions">
            <button type="button" class="arr-btn arr-btn--primary" @click="showDiffModal = false">
              {{ $t('adminReportReview.diffModal.close') || 'Fermer' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import client from '../api/client'
import { chatWithReport } from '../api/report'
import AdminReportTree from '../components/AdminReportTree.vue'
import TiptapEditor from '../components/TiptapEditor.vue'
import RawMdEditor from '../components/RawMdEditor.vue'
import VersionDiff from '../components/VersionDiff.vue'

const route = useRoute()
const { t } = useI18n()

// ─── Paramètre de route ────────────────────────────────────────────────────

const reportId = computed(() => String(route.params.id || ''))

// ─── État de chargement ────────────────────────────────────────────────────

const loading = ref(true)
const loadError = ref<string | null>(null)

// ─── Données rapport ───────────────────────────────────────────────────────

const workflowState = ref<string | null>(null)
const outline = ref<{ sections: Array<{ title: string; anchor?: string; content?: string }> }>({ sections: [] })
const pdfUrl = ref<string | null>(null)
const pdfLoading = ref(false)

// ─── Éditeur ───────────────────────────────────────────────────────────────

const rawMode = ref(false)
const editorContent = ref('')
const activeSectionIndex = ref(0)
const rephrasing = ref(false)
const selectedText = ref('')  // sélection pour rephrase

// ─── Versions ──────────────────────────────────────────────────────────────

type VersionRow = {
  version_id: string
  version_number: number
  created_at: string
  comment: string | null
  markdown_content?: string
}

const versions = ref<VersionRow[]>([])
const saving = ref(false)
const versionComment = ref('')
const showSaveModal = ref(false)

// ─── Diff ──────────────────────────────────────────────────────────────────

const showDiffModal = ref(false)
const diffFromId = ref<string>('')
const diffToId = ref<string>('')

// ─── Commentaires ──────────────────────────────────────────────────────────

type CommentRow = {
  comment_id: string
  report_id: string
  paragraph_anchor: string
  body: string
  resolved: boolean
  created_at: string
}

const comments = ref<CommentRow[]>([])
const commentsLoading = ref(false)
const newCommentBody = ref('')
const newCommentAnchor = ref('')
const addingComment = ref(false)

// ─── Notifications ─────────────────────────────────────────────────────────

type Notif = { message: string; type: 'success' | 'error' }
const notification = ref<Notif | null>(null)
let _notifTimer: ReturnType<typeof setTimeout> | null = null

function notify(msg: string, type: 'success' | 'error' = 'success') {
  notification.value = { message: msg, type }
  if (_notifTimer !== null) clearTimeout(_notifTimer)
  _notifTimer = setTimeout(() => { notification.value = null }, 4000)
}

// ─── Computed ──────────────────────────────────────────────────────────────

const activeSectionTitle = computed(() => {
  const sections = outline.value.sections || []
  if (activeSectionIndex.value < sections.length) {
    return sections[activeSectionIndex.value]?.title || ''
  }
  return ''
})

const openComments = computed(() =>
  comments.value.filter((c) => !c.resolved)
)

// ─── Chargement initial ────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([
    loadWorkflowState(),
    loadReport(),
    loadVersions(),
    loadComments(),
  ])
  loading.value = false
})

async function loadWorkflowState() {
  try {
    const resp = await (client as unknown as {
      get: (url: string) => Promise<{ success: boolean; data: Record<string, unknown> }>
    }).get(`/api/admin/reports/${encodeURIComponent(reportId.value)}/state`)
    if (resp.success && resp.data) {
      workflowState.value = String(resp.data.state || '')
    }
  } catch (_) {
    // Non bloquant — l'état workflow est informatif
  }
}

async function loadReport() {
  try {
    const resp = await (client as unknown as {
      get: (url: string) => Promise<{ success?: boolean; outline?: { sections: Array<{ title: string; content?: string }> }; markdown_content?: string }>
    }).get(`/api/report/${encodeURIComponent(reportId.value)}`)

    if (resp?.outline?.sections) {
      outline.value = { sections: resp.outline.sections }
    }

    // Charger le contenu Markdown de la section active
    const sections = outline.value.sections || []
    if (sections.length > 0) {
      editorContent.value = sections[0]?.content || ''
    }
  } catch (_) {
    loadError.value = t('adminReportReview.notFound') || 'Rapport introuvable.'
  }
}

async function loadVersions() {
  try {
    const resp = await (client as unknown as {
      get: (url: string) => Promise<{ success: boolean; data: { versions: VersionRow[] } }>
    }).get(`/api/admin/reports/${encodeURIComponent(reportId.value)}/versions`)
    if (resp.success && resp.data) {
      versions.value = resp.data.versions || []
      // Pré-sélectionner les deux dernières versions pour le diff
      if (versions.value.length >= 2) {
        diffFromId.value = versions.value[1].version_id
        diffToId.value = versions.value[0].version_id
      } else if (versions.value.length === 1) {
        diffFromId.value = versions.value[0].version_id
        diffToId.value = versions.value[0].version_id
      }
    }
  } catch (_) {
    // Pas de versions encore — normal
  }
}

async function loadComments() {
  commentsLoading.value = true
  try {
    const resp = await (client as unknown as {
      get: (url: string) => Promise<{ success: boolean; data: { comments: CommentRow[] } }>
    }).get(`/api/admin/reports/${encodeURIComponent(reportId.value)}/comments`)
    if (resp.success && resp.data) {
      comments.value = resp.data.comments || []
    }
  } catch (_) {
    // Non bloquant
  } finally {
    commentsLoading.value = false
  }
}

// ─── Sélection de section ─────────────────────────────────────────────────

function selectSection(idx: number) {
  activeSectionIndex.value = idx
  const sections = outline.value.sections || []
  if (idx < sections.length) {
    editorContent.value = sections[idx]?.content || ''
    newCommentAnchor.value = sections[idx]?.anchor || `section-${idx}`
  }
}

// ─── Sauvegarde de version ────────────────────────────────────────────────

async function saveVersion() {
  if (!editorContent.value.trim()) return
  saving.value = true
  try {
    const resp = await (client as unknown as {
      post: (url: string, data: object) => Promise<{ success: boolean; data: { version: VersionRow } }>
    }).post(
      `/api/admin/reports/${encodeURIComponent(reportId.value)}/versions`,
      { markdown_content: editorContent.value, comment: versionComment.value || null }
    )
    if (resp.success && resp.data?.version) {
      versions.value.unshift(resp.data.version)
      notify(
        t('adminReportReview.saveVersionSuccess', { n: resp.data.version.version_number }) ||
        `Version ${resp.data.version.version_number} sauvegardée.`
      )
      versionComment.value = ''
      showSaveModal.value = false

      // Débounce 2s → rafraîchir PDF preview
      _schedulePdfRefresh()
    }
  } catch (_) {
    notify(t('adminReportReview.saveVersionError') || 'Impossible de sauvegarder la version.', 'error')
  } finally {
    saving.value = false
  }
}

// ─── PDF refresh debounced ────────────────────────────────────────────────

let _pdfTimer: ReturnType<typeof setTimeout> | null = null

function _schedulePdfRefresh() {
  if (_pdfTimer !== null) clearTimeout(_pdfTimer)
  pdfLoading.value = true
  _pdfTimer = setTimeout(() => {
    pdfUrl.value = `/api/admin/reports/${encodeURIComponent(reportId.value)}/pdf?t=${Date.now()}`
    pdfLoading.value = false
  }, 2000)
}

// ─── Rephrase avec IA ────────────────────────────────────────────────────

async function rephraseSelected() {
  const textToRephrase = selectedText.value || editorContent.value.substring(0, 500)
  if (!textToRephrase.trim()) return

  rephrasing.value = true
  try {
    const prompt = t('adminReportReview.rephrasePrompt') ||
      'Reformule ce paragraphe en conservant le sens exact :'

    const resp = await chatWithReport({
      simulation_id: reportId.value,
      message: `${prompt}\n\n${textToRephrase}`,
      chat_history: [],
    })

    if (resp?.response || resp?.data?.response) {
      const rephrased = resp?.response || resp?.data?.response
      // Remplace la sélection ou append en bas
      editorContent.value = editorContent.value.replace(
        textToRephrase,
        rephrased
      ) || `${editorContent.value}\n\n${rephrased}`
    }
  } catch (_) {
    notify(t('adminReportReview.rephraseError') || 'Impossible de reformuler.', 'error')
  } finally {
    rephrasing.value = false
  }
}

// ─── Commentaires ─────────────────────────────────────────────────────────

async function addComment() {
  if (!newCommentBody.value.trim()) return
  addingComment.value = true
  try {
    const resp = await (client as unknown as {
      post: (url: string, data: object) => Promise<{ success: boolean; data: { comment: CommentRow } }>
    }).post(
      `/api/admin/reports/${encodeURIComponent(reportId.value)}/comments`,
      { paragraph_anchor: newCommentAnchor.value, body: newCommentBody.value }
    )
    if (resp.success && resp.data?.comment) {
      comments.value.push(resp.data.comment)
      newCommentBody.value = ''
    }
  } catch (_) {
    notify('Impossible d\'ajouter l\'annotation.', 'error')
  } finally {
    addingComment.value = false
  }
}

async function resolveComment(commentId: string) {
  try {
    await (client as unknown as {
      patch: (url: string, data: object) => Promise<{ success: boolean }>
    }).patch(
      `/api/admin/reports/${encodeURIComponent(reportId.value)}/comments/${encodeURIComponent(commentId)}`,
      { resolved: true }
    )
    const c = comments.value.find((x) => x.comment_id === commentId)
    if (c) c.resolved = true
  } catch (_) {
    notify('Impossible de résoudre l\'annotation.', 'error')
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' })
  } catch (_) {
    return dateStr
  }
}
</script>

<style scoped>
/* ── Page ──────────────────────────────────────────────────────────────────── */

.arr-page {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  background: var(--wi-background, #f9f6f1);
  color: var(--wi-on-surface, #1a1a1a);
  overflow: hidden;
}

/* ── Topbar ────────────────────────────────────────────────────────────────── */

.arr-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 20px;
  height: 52px;
  border-bottom: 1px solid var(--wi-outline-variant, #e0e0e0);
  background: var(--wi-surface, #fff);
  flex-shrink: 0;
}

.arr-back {
  font-size: 12px;
  font-weight: 600;
  color: var(--wi-on-surface-variant, #888);
  text-decoration: none;
  letter-spacing: 0.05em;
  transition: color 0.15s;
}

.arr-back:hover {
  color: var(--wi-primary, #e06b2e);
}

.arr-topbar-center {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  justify-content: center;
}

.arr-report-id {
  font-size: 12px;
  font-family: monospace;
  color: var(--wi-on-surface-variant, #888);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arr-state-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: var(--wi-outline-variant, #e0e0e0);
  color: var(--wi-on-surface, #1a1a1a);
}

.arr-state-pill--draft { background: #e3f2fd; color: #1565c0; }
.arr-state-pill--in_review { background: #fff3e0; color: #e65100; }
.arr-state-pill--pending_approval { background: #fce4ec; color: #880e4f; }
.arr-state-pill--approved { background: #e8f5e9; color: #1b5e20; }
.arr-state-pill--delivered { background: #f3e5f5; color: #4a148c; }
.arr-state-pill--archived { background: #f5f5f5; color: #757575; }

.arr-topbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ── Boutons ────────────────────────────────────────────────────────────────── */

.arr-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: var(--wi-radius-sm, 6px);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s, opacity 0.15s;
  white-space: nowrap;
}

.arr-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.arr-btn--primary {
  background: var(--wi-primary, #e06b2e);
  color: var(--wi-on-primary, #fff);
}

.arr-btn--primary:hover:not(:disabled) {
  background: var(--wi-primary-dark, #c45a22);
}

.arr-btn--ghost {
  background: transparent;
  color: var(--wi-on-surface, #1a1a1a);
  border-color: var(--wi-outline-variant, #e0e0e0);
}

.arr-btn--ghost:hover:not(:disabled) {
  background: var(--wi-surface-container, #f5f5f5);
}

.arr-btn--sm {
  padding: 4px 8px;
  font-size: 11px;
}

/* ── Notification ─────────────────────────────────────────────────────────── */

.arr-notif {
  padding: 8px 20px;
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
}

.arr-notif--success {
  background: #e8f5e9;
  color: #1b5e20;
  border-bottom: 1px solid #a5d6a7;
}

.arr-notif--error {
  background: #fce4ec;
  color: #880e4f;
  border-bottom: 1px solid #f48fb1;
}

.arr-notif-slide-enter-active,
.arr-notif-slide-leave-active {
  transition: opacity 0.2s, max-height 0.2s;
  max-height: 50px;
  overflow: hidden;
}

.arr-notif-slide-enter-from,
.arr-notif-slide-leave-to {
  opacity: 0;
  max-height: 0;
}

/* ── États loading/error ─────────────────────────────────────────────────── */

.arr-loading,
.arr-error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--wi-on-surface-variant, #888);
  padding: 40px;
}

.arr-error {
  color: var(--wi-error, #c62828);
}

/* ── Split view ────────────────────────────────────────────────────────────── */

.arr-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  flex: 1;
  overflow: hidden;
}

/* ── Pane PDF ──────────────────────────────────────────────────────────────── */

.arr-pdf-pane {
  display: flex;
  flex-direction: column;
  border-inline-end: 1px solid var(--wi-outline-variant, #e0e0e0);
  overflow: hidden;
}

.arr-pdf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-bottom: 1px solid var(--wi-outline-variant, #e0e0e0);
  flex-shrink: 0;
  background: var(--wi-surface-container, #f5f5f5);
}

.arr-pdf-loading {
  font-size: 14px;
  color: var(--wi-primary, #e06b2e);
  animation: arr-spin 1s linear infinite;
}

@keyframes arr-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.arr-pdf-embed {
  flex: 1;
  overflow: hidden;
}

.arr-pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: var(--wi-surface, #fff);
}

.arr-pdf-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  color: var(--wi-on-surface-variant, #888);
}

.arr-pdf-placeholder-sub {
  font-size: 11px;
  text-align: center;
  max-width: 240px;
  line-height: 1.5;
}

/* ── Pane éditeur ──────────────────────────────────────────────────────────── */

.arr-editor-pane {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.arr-tree-wrap {
  flex-shrink: 0;
  height: 160px;
  overflow: hidden;
}

.arr-editor-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.arr-editor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-top: 1px solid var(--wi-outline-variant, #e0e0e0);
  border-bottom: 1px solid var(--wi-outline-variant, #e0e0e0);
  flex-shrink: 0;
  background: var(--wi-surface-container, #f5f5f5);
}

.arr-section-title {
  font-size: 11px;
  color: var(--wi-on-surface-variant, #888);
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arr-editor-content {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.arr-editor-inner {
  height: 100%;
}

/* ── Commentaires ──────────────────────────────────────────────────────────── */

.arr-comments {
  flex-shrink: 0;
  max-height: 240px;
  overflow-y: auto;
  border-top: 1px solid var(--wi-outline-variant, #e0e0e0);
  background: var(--wi-surface-container, #f5f5f5);
}

.arr-comments-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-bottom: 1px solid var(--wi-outline-variant, #e0e0e0);
}

.arr-comments-count {
  font-size: 10px;
  background: var(--wi-primary, #e06b2e);
  color: var(--wi-on-primary, #fff);
  border-radius: 10px;
  padding: 1px 5px;
  min-width: 16px;
  text-align: center;
}

.arr-comments-state,
.arr-comments-empty {
  padding: 8px 14px;
  font-size: 11px;
  color: var(--wi-on-surface-variant, #888);
  font-style: italic;
}

.arr-comments-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
}

.arr-comment-item {
  padding: 6px 14px;
  border-bottom: 1px solid var(--wi-outline-variant, #e0e0e0);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.arr-comment-anchor {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--wi-on-surface-variant, #888);
}

.arr-comment-body {
  font-size: 11px;
  color: var(--wi-on-surface, #1a1a1a);
  margin: 0;
  line-height: 1.4;
}

.arr-comment-resolve {
  align-self: flex-end;
  font-size: 10px;
  color: var(--wi-primary, #e06b2e);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 0;
  text-decoration: underline;
}

.arr-comment-add {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 14px;
  border-top: 1px solid var(--wi-outline-variant, #e0e0e0);
}

.arr-comment-anchor-input {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid var(--wi-outline-variant, #e0e0e0);
  border-radius: var(--wi-radius-sm, 4px);
  font-size: 11px;
  color: var(--wi-on-surface, #1a1a1a);
  background: var(--wi-surface, #fff);
  outline: none;
  font-family: monospace;
}

.arr-comment-textarea {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid var(--wi-outline-variant, #e0e0e0);
  border-radius: var(--wi-radius-sm, 4px);
  font-size: 11px;
  resize: none;
  color: var(--wi-on-surface, #1a1a1a);
  background: var(--wi-surface, #fff);
  outline: none;
  font-family: inherit;
}

.arr-comment-anchor-input:focus,
.arr-comment-textarea:focus {
  border-color: var(--wi-primary, #e06b2e);
}

/* ── Labels communs ─────────────────────────────────────────────────────────── */

.arr-pane-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--wi-on-surface-variant, #888);
}

/* ── Modales ────────────────────────────────────────────────────────────────── */

.arr-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.arr-modal {
  background: var(--wi-surface, #fff);
  border-radius: var(--wi-radius-lg, 12px);
  padding: 24px;
  width: min(480px, 90vw);
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.arr-modal--wide {
  width: min(840px, 95vw);
  max-height: 80vh;
  overflow-y: auto;
}

.arr-modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--wi-on-surface, #1a1a1a);
  margin: 0;
}

.arr-modal-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.arr-modal-field--row {
  flex-direction: row;
  gap: 16px;
}

.arr-modal-field--row > div {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.arr-modal-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--wi-on-surface-variant, #888);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.arr-modal-input,
.arr-modal-select {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--wi-outline-variant, #e0e0e0);
  border-radius: var(--wi-radius-sm, 6px);
  font-size: 13px;
  color: var(--wi-on-surface, #1a1a1a);
  background: var(--wi-surface, #fff);
  outline: none;
}

.arr-modal-input:focus,
.arr-modal-select:focus {
  border-color: var(--wi-primary, #e06b2e);
}

.arr-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.arr-modal-hint {
  font-size: 12px;
  color: var(--wi-on-surface-variant, #888);
  font-style: italic;
  margin: 0;
  text-align: center;
}

.arr-diff-container {
  max-height: 400px;
  overflow-y: auto;
}

.arr-modal-fade-enter-active,
.arr-modal-fade-leave-active {
  transition: opacity 0.2s;
}

.arr-modal-fade-enter-from,
.arr-modal-fade-leave-to {
  opacity: 0;
}

/* ── Responsive ────────────────────────────────────────────────────────────── */

@media (max-width: 768px) {
  .arr-split {
    grid-template-columns: 1fr;
    grid-template-rows: 40vh 1fr;
  }

  .arr-topbar-actions {
    gap: 4px;
  }

  .arr-btn {
    padding: 5px 8px;
    font-size: 11px;
  }
}
</style>
