<template>
  <!--
    AdminReportTree (US-127) — Arbre des sections du rapport avec indicateurs.
    Affiche outline.sections avec le compte de commentaires ouverts par section.
    Tokens --wi-* exclusivement. i18n FR/EN/AR.
  -->
  <nav class="art-root" :aria-label="$t('adminReportReview.sections') || 'Sections'">
    <div class="art-header">
      <span class="art-title">{{ $t('adminReportReview.sections') || 'Sections' }}</span>
      <span class="art-count">{{ sections.length }}</span>
    </div>

    <div v-if="sections.length === 0" class="art-empty">
      {{ $t('adminReportReview.sectionsEmpty') || 'Aucune section détectée.' }}
    </div>

    <ul v-else class="art-list" role="listbox">
      <li
        v-for="(section, idx) in sections"
        :key="idx"
        class="art-item"
        :class="{ 'is-active': activeIndex === idx }"
        role="option"
        :aria-selected="activeIndex === idx"
        tabindex="0"
        @click="$emit('select-section', idx)"
        @keydown.enter="$emit('select-section', idx)"
        @keydown.space.prevent="$emit('select-section', idx)"
      >
        <span class="art-item-index">{{ idx + 1 }}</span>
        <span class="art-item-title">{{ section.title || `Section ${idx + 1}` }}</span>
        <span
          v-if="commentCounts[idx] > 0"
          class="art-badge"
          :aria-label="`${commentCounts[idx]} annotation(s)`"
        >
          {{ commentCounts[idx] }}
        </span>
      </li>
    </ul>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type OutlineSection = {
  title: string
  anchor?: string
}

type Comment = {
  paragraph_anchor: string
  resolved: boolean
}

type Props = {
  sections: OutlineSection[]
  activeIndex: number
  comments: Comment[]
}

const props = withDefaults(defineProps<Props>(), {
  sections: () => [],
  activeIndex: 0,
  comments: () => [],
})

defineEmits<{
  (e: 'select-section', index: number): void
}>()

// Compte les commentaires non résolus par section (matching par index ou anchor)
const commentCounts = computed<number[]>(() => {
  return props.sections.map((section, idx) => {
    const anchor = section.anchor || `section-${idx}`
    return props.comments.filter(
      (c) => !c.resolved && (c.paragraph_anchor === anchor || c.paragraph_anchor === `section-${idx}`)
    ).length
  })
})
</script>

<style scoped>
.art-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--wi-surface-container, #f5f5f5);
  border-inline-end: 1px solid var(--wi-outline-variant, #e0e0e0);
  overflow: hidden;
}

.art-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 8px;
  border-bottom: 1px solid var(--wi-outline-variant, #e0e0e0);
  flex-shrink: 0;
}

.art-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--wi-on-surface-variant, #888);
}

.art-count {
  font-size: 10px;
  background: var(--wi-outline-variant, #e0e0e0);
  color: var(--wi-on-surface-variant, #888);
  border-radius: 10px;
  padding: 1px 6px;
}

.art-empty {
  padding: 16px 14px;
  font-size: 12px;
  color: var(--wi-on-surface-variant, #888);
  font-style: italic;
}

.art-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
  overflow-y: auto;
  flex: 1;
}

.art-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  cursor: pointer;
  transition: background 0.12s;
  border-radius: 0;
  outline: none;
}

.art-item:hover,
.art-item:focus-visible {
  background: var(--wi-surface, #fff);
}

.art-item.is-active {
  background: var(--wi-primary-container, #ffe8d0);
  border-inline-start: 3px solid var(--wi-primary, #e06b2e);
}

.art-item-index {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  color: var(--wi-on-surface-variant, #888);
  min-width: 18px;
}

.art-item-title {
  flex: 1;
  font-size: 12px;
  font-weight: 500;
  color: var(--wi-on-surface, #1a1a1a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.art-badge {
  flex-shrink: 0;
  background: var(--wi-primary, #e06b2e);
  color: var(--wi-on-primary, #fff);
  border-radius: 10px;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  min-width: 16px;
  text-align: center;
}
</style>
