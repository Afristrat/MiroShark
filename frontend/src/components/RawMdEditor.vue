<template>
  <!--
    RawMdEditor (US-127) — Wrapper CodeMirror 6 syntax highlighting GFM.
    Tokens --wi-* exclusivement. Hauteur 100% du parent.
  -->
  <div ref="rootEl" class="rme-root"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { EditorState } from '@codemirror/state'
import { EditorView, lineNumbers, highlightActiveLine, keymap } from '@codemirror/view'
import { markdown } from '@codemirror/lang-markdown'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'

type Props = {
  modelValue: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
})

const emit = defineEmits<{
  (_e: 'update:modelValue', _value: string): void
}>()

const rootEl = ref<HTMLElement | null>(null)
let view: EditorView | null = null

// ─── Theme minimal --wi-* ────────────────────────────────────────────────────

const _editorTheme = EditorView.theme({
  '&': {
    height: '100%',
    fontSize: '13px',
    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
    backgroundColor: 'var(--wi-surface, #fff)',
    color: 'var(--wi-on-surface, #1a1a1a)',
  },
  '.cm-scroller': {
    overflow: 'auto',
    height: '100%',
    lineHeight: '1.65',
  },
  '.cm-content': {
    padding: '12px 16px',
    caretColor: 'var(--wi-primary, #e06b2e)',
  },
  '.cm-line': {
    paddingLeft: '4px',
  },
  '&.cm-focused .cm-cursor': {
    borderLeftColor: 'var(--wi-primary, #e06b2e)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--wi-surface-container, #f5f5f5)',
    borderRight: '1px solid var(--wi-outline-variant, #e0e0e0)',
    color: 'var(--wi-on-surface-variant, #888)',
    fontSize: '11px',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'var(--wi-primary-container, #ffe8d0)',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(224, 107, 46, 0.05)',
  },
  '.cm-selectionBackground': {
    backgroundColor: 'var(--wi-primary-container, #ffe8d0) !important',
  },
  '&.cm-focused .cm-selectionBackground': {
    backgroundColor: 'rgba(224, 107, 46, 0.25) !important',
  },
})

// ─── Init CodeMirror ─────────────────────────────────────────────────────────

onMounted(() => {
  if (!rootEl.value) return

  const updateListener = EditorView.updateListener.of((update) => {
    if (update.docChanged) {
      emit('update:modelValue', update.state.doc.toString())
    }
  })

  view = new EditorView({
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        lineNumbers(),
        highlightActiveLine(),
        history(),
        markdown(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        _editorTheme,
        updateListener,
        EditorView.lineWrapping,
      ],
    }),
    parent: rootEl.value,
  })
})

// ─── Sync modelValue → view ───────────────────────────────────────────────────

watch(() => props.modelValue, (val) => {
  if (!view) return
  const current = view.state.doc.toString()
  if (val !== current) {
    view.dispatch({
      changes: { from: 0, to: current.length, insert: val },
    })
  }
})

// ─── Cleanup ─────────────────────────────────────────────────────────────────

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})
</script>

<style scoped>
.rme-root {
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--wi-outline-variant, #e0e0e0);
  border-radius: var(--wi-radius-md, 8px);
}

:deep(.cm-editor) {
  height: 100%;
}
</style>
