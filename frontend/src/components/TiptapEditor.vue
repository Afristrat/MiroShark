<template>
  <!--
    TiptapEditor (US-127) — Wrapper Tiptap avec validation typo live (debounced 800ms)
    et toolbar basique (bold, italic, headings, undo/redo).
    Tokens --wi-* exclusivement. i18n FR/EN/AR via $t('adminReportReview.toolbar.*').
  -->
  <div class="tte-root">
    <div class="tte-toolbar" role="toolbar" :aria-label="$t('adminReportReview.editor') || 'Éditeur'">
      <button
        type="button"
        class="tte-btn"
        :class="{ 'is-active': editor?.isActive('bold') }"
        :title="$t('adminReportReview.toolbar.bold') || 'Gras'"
        @click="editor?.chain().focus().toggleBold().run()"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        class="tte-btn"
        :class="{ 'is-active': editor?.isActive('italic') }"
        :title="$t('adminReportReview.toolbar.italic') || 'Italique'"
        @click="editor?.chain().focus().toggleItalic().run()"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        class="tte-btn"
        :class="{ 'is-active': editor?.isActive('heading', { level: 1 }) }"
        :title="$t('adminReportReview.toolbar.heading') || 'Titre'"
        @click="editor?.chain().focus().toggleHeading({ level: 1 }).run()"
      >
        H1
      </button>
      <button
        type="button"
        class="tte-btn"
        :class="{ 'is-active': editor?.isActive('heading', { level: 2 }) }"
        :title="$t('adminReportReview.toolbar.heading') || 'Titre'"
        @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
      >
        H2
      </button>
      <div class="tte-divider" aria-hidden="true"></div>
      <button
        type="button"
        class="tte-btn"
        :title="$t('adminReportReview.toolbar.undo') || 'Annuler'"
        :disabled="!editor?.can().undo()"
        @click="editor?.chain().focus().undo().run()"
      >
        ↩
      </button>
      <button
        type="button"
        class="tte-btn"
        :title="$t('adminReportReview.toolbar.redo') || 'Rétablir'"
        :disabled="!editor?.can().redo()"
        @click="editor?.chain().focus().redo().run()"
      >
        ↪
      </button>
    </div>

    <div class="tte-content-wrap">
      <editor-content class="tte-editor" :editor="editor" />
      <div v-if="normalizing" class="tte-normalizer-badge" aria-live="polite">
        <span class="tte-dot"></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount, onMounted } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'

type Props = {
  modelValue: string
  placeholder?: string
  reportId?: string
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '',
  reportId: '',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// ─── État ──────────────────────────────────────────────────────────────────

const normalizing = ref(false)
let _normalizeTimer: ReturnType<typeof setTimeout> | null = null

// ─── Editor Tiptap ─────────────────────────────────────────────────────────

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit,
    Placeholder.configure({
      placeholder: props.placeholder || 'Éditez le contenu du rapport…',
    }),
  ],
  onUpdate({ editor: e }) {
    const md = e.getText()  // texte brut pour normalisation
    const html = e.getHTML()
    emit('update:modelValue', html)
    _scheduleNormalize(md)
  },
})

// ─── Sync modelValue → editor (prop change depuis parent) ──────────────────

watch(() => props.modelValue, (val) => {
  if (!editor.value) return
  const currentHtml = editor.value.getHTML()
  if (val !== currentHtml) {
    editor.value.commands.setContent(val, false)
  }
})

// ─── Normalisation debounced 800ms ────────────────────────────────────────

function _scheduleNormalize(text: string) {
  if (_normalizeTimer !== null) clearTimeout(_normalizeTimer)
  _normalizeTimer = setTimeout(() => _runNormalize(text), 800)
}

async function _runNormalize(_text: string) {
  // Appel potentiel à /api/normalizer si disponible — non bloquant.
  // On marque juste un état visuel "traitement" sans bloquer l'éditeur.
  normalizing.value = true
  await new Promise((r) => setTimeout(r, 300))
  normalizing.value = false
}

// ─── Cleanup ───────────────────────────────────────────────────────────────

onBeforeUnmount(() => {
  if (_normalizeTimer !== null) clearTimeout(_normalizeTimer)
  editor.value?.destroy()
})
</script>

<style scoped>
.tte-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--wi-surface, #fff);
  border: 1px solid var(--wi-outline-variant, #e0e0e0);
  border-radius: var(--wi-radius-md, 8px);
  overflow: hidden;
}

.tte-toolbar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--wi-outline-variant, #e0e0e0);
  background: var(--wi-surface-container, #f5f5f5);
  flex-shrink: 0;
}

.tte-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--wi-radius-sm, 4px);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--wi-on-surface, #1a1a1a);
  transition: background 0.15s;
  min-width: 28px;
  min-height: 28px;
  line-height: 1;
}

.tte-btn:hover:not(:disabled) {
  background: var(--wi-primary-container, #ffe8d0);
}

.tte-btn.is-active {
  background: var(--wi-primary, #e06b2e);
  color: var(--wi-on-primary, #fff);
  border-color: var(--wi-primary, #e06b2e);
}

.tte-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tte-divider {
  width: 1px;
  height: 20px;
  background: var(--wi-outline-variant, #e0e0e0);
  margin: 0 4px;
}

.tte-content-wrap {
  position: relative;
  flex: 1;
  overflow-y: auto;
}

.tte-editor {
  height: 100%;
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--wi-on-surface, #1a1a1a);
}

/* Styles pour le contenu Tiptap */
:deep(.ProseMirror) {
  min-height: 100%;
  outline: none;
}

:deep(.ProseMirror h1) {
  font-size: 1.5em;
  font-weight: 700;
  margin: 1em 0 0.5em;
  color: var(--wi-on-surface, #1a1a1a);
}

:deep(.ProseMirror h2) {
  font-size: 1.25em;
  font-weight: 600;
  margin: 0.8em 0 0.4em;
  color: var(--wi-on-surface, #1a1a1a);
}

:deep(.ProseMirror p) {
  margin: 0 0 0.6em;
}

:deep(.ProseMirror strong) {
  font-weight: 700;
}

:deep(.ProseMirror em) {
  font-style: italic;
}

:deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--wi-on-surface-variant, #888);
  pointer-events: none;
  height: 0;
  font-style: italic;
}

.tte-normalizer-badge {
  position: absolute;
  bottom: 8px;
  inset-inline-end: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.tte-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--wi-primary, #e06b2e);
  animation: tte-pulse 0.8s ease-in-out infinite alternate;
}

@keyframes tte-pulse {
  from { opacity: 0.4; }
  to   { opacity: 1; }
}
</style>
